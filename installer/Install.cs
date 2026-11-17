// Star Wars Battlefront II Classic - Xbox Edition mod: installer / uninstaller.
// Build: csc /out:Install.exe Install.cs   (.NET Framework 4, C# 5 - ships with Windows)
// Usage: Install.exe [install|uninstall] ["path\to\GameData"]
// Everything it changes is backed up first into GameData\XboxEdition_backup; uninstall puts it all back.
using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using System.Linq;
using System.Security.Cryptography;
using System.Text;
using Microsoft.Win32;

static class Installer
{
    const string GameDir = "Star Wars Battlefront II Classic";
    const string BackupName = "XboxEdition_backup";
    static string Root;       // ...\GameData
    static string Backup;     // ...\GameData\XboxEdition_backup
    static string Payload;    // next to Install.exe
    static string Here;       // folder of Install.exe
    static string FilesRoot;  // where the mod files come from: payload\files (prebuilt) or the build output
    static string CtrlArg, XboxArg;
    static List<string> Log = new List<string>();

    static int Main(string[] args)
    {
        var pos = new List<string>();
        for (int i = 0; i < args.Length; i++)
        {
            if (args[i] == "--ctrl" && i + 1 < args.Length) CtrlArg = args[++i];
            else if (args[i] == "--xbox" && i + 1 < args.Length) XboxArg = args[++i];
            else pos.Add(args[i]);
        }
        string mode = pos.Count > 0 ? pos[0].ToLowerInvariant() : "";
        string path = pos.Count > 1 ? pos[1] : null;
        Here = AppDomain.CurrentDomain.BaseDirectory;
        Payload = Path.Combine(Here, "payload");
        Console.WriteLine("Star Wars Battlefront II Classic - Xbox Edition");
        Console.WriteLine("===============================================");
        try
        {
            Root = path ?? FindGameData();
            if (Root == null)
            {
                Console.WriteLine("Could not find the game. Run:  Install.exe install \"<path to ...\\GameData>\"");
                return Done(1);
            }
            Backup = Path.Combine(Root, BackupName);
            Console.WriteLine("Game folder: " + Root);
            if (Process.GetProcessesByName("BattlefrontII").Length > 0)
            {
                Console.WriteLine("The game is running. Close it first.");
                return Done(1);
            }
            if (mode != "install" && mode != "uninstall")
            {
                Console.Write(Directory.Exists(Backup) ? "Installed. [U]ninstall, [R]einstall or [Q]uit? " : "[I]nstall or [Q]uit? ");
                string k = (Console.ReadLine() ?? "").Trim().ToLowerInvariant();
                mode = k == "u" ? "uninstall" : (k == "i" || k == "r") ? "install" : "";
                if (mode == "") return Done(0);
            }
            if (mode == "install") Install(); else Uninstall();
            return Done(0);
        }
        catch (Exception e)
        {
            Console.WriteLine();
            Console.WriteLine("ERROR: " + e.Message);
            Console.WriteLine("Nothing after this step was changed. Run the uninstaller to undo the steps before it.");
            return Done(1);
        }
    }

    static int Done(int code)
    {
        if (!Console.IsInputRedirected)
        {
            Console.WriteLine();
            Console.Write("Press Enter to close.");
            Console.ReadLine();
        }
        return code;
    }

    // ---------------------------------------------------------------- locate the game
    static string FindGameData()
    {
        var libs = new List<string>();
        foreach (string key in new[] { @"HKEY_CURRENT_USER\Software\Valve\Steam", @"HKEY_LOCAL_MACHINE\SOFTWARE\WOW6432Node\Valve\Steam" })
        {
            object v = Registry.GetValue(key, key.StartsWith("HKEY_CURRENT") ? "SteamPath" : "InstallPath", null);
            if (v != null) libs.Add(v.ToString().Replace('/', '\\'));
        }
        libs.Add(@"C:\Program Files (x86)\Steam");
        foreach (string steam in libs.ToArray())
        {
            string vdf = Path.Combine(steam, @"steamapps\libraryfolders.vdf");
            if (!File.Exists(vdf)) continue;
            foreach (string line in File.ReadAllLines(vdf))
            {
                string t = line.Trim();
                if (t.StartsWith("\"path\""))
                {
                    string[] parts = t.Split('"');
                    if (parts.Length >= 4) libs.Add(parts[3].Replace(@"\\", @"\"));
                }
            }
        }
        foreach (string lib in libs)
        {
            string g = Path.Combine(lib, @"steamapps\common", GameDir, "GameData");
            if (File.Exists(Path.Combine(g, "BattlefrontII.exe"))) return g;
        }
        return null;
    }

    // ---------------------------------------------------------------- helpers
    static string Md5(string file)
    {
        using (var md5 = MD5.Create())
        using (var s = File.OpenRead(file))
            return BitConverter.ToString(md5.ComputeHash(s)).Replace("-", "").ToLowerInvariant();
    }

    static byte[] Hex(string h)
    {
        var b = new byte[h.Length / 2];
        for (int i = 0; i < b.Length; i++) b[i] = Convert.ToByte(h.Substring(i * 2, 2), 16);
        return b;
    }

    static string Rel(string full) { return full.Substring(Root.Length).TrimStart('\\'); }

    static void BackupFile(string rel)
    {
        string src = Path.Combine(Root, rel), dst = Path.Combine(Backup, "files", rel);
        if (File.Exists(dst) || !File.Exists(src)) return;
        Directory.CreateDirectory(Path.GetDirectoryName(dst));
        File.Copy(src, dst);
    }

    static void Step(string s) { Console.WriteLine(" - " + s); }

    static string[] Lines(string name)
    {
        return File.ReadAllLines(Path.Combine(Payload, name)).Where(l => l.Trim() != "" && !l.StartsWith("#")).ToArray();
    }

    // ---------------------------------------------------------------- install
    static void Install()
    {
        if (!Directory.Exists(Path.Combine(Root, @"addon\Remaster")))
            throw new Exception("The Battlefront II Remaster (addon\\Remaster) is not installed. Install it first.");
        Directory.CreateDirectory(Backup);
        FilesRoot = Directory.Exists(Path.Combine(Payload, "files")) ? Path.Combine(Payload, "files") : BuildFromSources();
        string createdList = Path.Combine(Backup, "created.txt");
        string installedList = Path.Combine(Backup, "installed.txt");
        var installed = new Dictionary<string, string>(StringComparer.OrdinalIgnoreCase);
        if (File.Exists(installedList))
            foreach (string l in File.ReadAllLines(installedList)) { string[] x = l.Split('\t'); if (x.Length == 2) installed[x[0]] = x[1]; }
        var created = File.Exists(createdList) ? new HashSet<string>(File.ReadAllLines(createdList)) : new HashSet<string>();

        // 1. files (manifest: dest <TAB> payload file <TAB> md5 of the Remaster file it replaces, or "-")
        Console.WriteLine("Files:");
        bool warned = false;
        foreach (string line in Lines("files.txt"))
        {
            string[] f = line.Split('\t');
            string dest = Path.Combine(Root, f[0]);
            string source = Path.Combine(FilesRoot, f[1]);
            if (!File.Exists(source))
            {
                Step(f[0] + ": skipped (" + (f[1].StartsWith("hud") ? "no Xbox disc image - the Remaster HUD stays" : "not built") + ")");
                continue;
            }
            bool backedUp = File.Exists(Path.Combine(Backup, "files", f[0]));
            if (File.Exists(dest) && !backedUp && f[2] != "-" && Md5(dest) != f[2] && !warned)
            {
                Console.WriteLine("   note: " + f[0] + " is not the Remaster (Jan 2026) version - other mods or another");
                Console.WriteLine("         Remaster version may be installed. It is backed up and replaced anyway.");
                warned = true;
            }
            if (File.Exists(dest)) BackupFile(f[0]); else if (!backedUp) created.Add(f[0]);
            Directory.CreateDirectory(Path.GetDirectoryName(dest));
            File.Copy(source, dest, true);
            installed[f[0]] = Md5(dest);
            Step(f[0]);
        }
        File.WriteAllLines(createdList, created.ToArray());
        File.WriteAllLines(installedList, installed.Select(x => x.Key + "\t" + x.Value).ToArray());

        // 2. game exe
        Console.WriteLine("BattlefrontII.exe:");
        PatchExe();

        // 3. side data (rep.lvl commando pistol)
        Console.WriteLine("Side data:");
        foreach (string line in Lines("sidepatch.txt")) PatchSide(line.Split('\t'));

        // 4. profiles (hero prompt on the arrow keys)
        Console.WriteLine("Profiles (arrow keys answer the hero prompt):");
        string saves = Path.Combine(Root, "SaveGames");
        if (Directory.Exists(saves))
            foreach (string p in Directory.GetFiles(saves, "*.profile")) PatchProfile(p);

        // 5. Shader Patch: its scalable font replaces every font (the Xbox fonts) with Arial
        string yml = Path.Combine(Root, "shader patch.yml");
        if (File.Exists(yml))
        {
            string t = File.ReadAllText(yml);
            if (t.Contains("Scalable Fonts: yes"))
            {
                File.WriteAllText(yml, t.Replace("Scalable Fonts: yes", "Scalable Fonts: no"));
                File.WriteAllText(Path.Combine(Backup, "shaderpatch_fonts.txt"), "changed yes -> no");
                Console.WriteLine("Shader Patch:");
                Step("Scalable Fonts: no (keeps the Xbox fonts)");
            }
        }
        Console.WriteLine();
        Console.WriteLine("Installed. Backups: " + Backup);
        Console.WriteLine("Controller: see README.txt (Steam Input layout).");
    }

    // ---------------------------------------------------------------- build (public package)
    // The mod files are built here, on the player's PC, from their own Remaster install, BAD-AL's controller
    // patch release and (optional) their own Xbox disc image - nothing of those projects is in this package.
    const string CtrlUrl = "https://github.com/BAD-AL/data_UOP_controller_patch/releases/download/1.1/GameData.7z";
    static readonly string[] Baseline = {
        @"data\_lvl_pc\shell.lvl", @"data\_lvl_pc\ingame.lvl", @"data\_lvl_pc\common.lvl", @"data\_lvl_pc\core.lvl",
        @"addon\Remaster\HUD\hud_16x09.lvl" };
    static readonly string[] CtrlFiles = {
        @"GameData\data\_lvl_pc\common.lvl", @"GameData\data\_lvl_pc\core.lvl",
        @"GameData\addon\000\addme.script", @"GameData\addon\000\core.lvl" };

    static string Ask(string q)
    {
        if (Console.IsInputRedirected) return "";
        Console.Write(q);
        return (Console.ReadLine() ?? "").Trim().Trim('"');
    }

    static string Q(string s) { return "\"" + s + "\""; }

    static int Run(string exe, string args, string logFile)
    {
        var psi = new ProcessStartInfo(exe, args) { UseShellExecute = false, CreateNoWindow = true,
            RedirectStandardOutput = true, RedirectStandardError = true, WorkingDirectory = Here };
        using (var p = Process.Start(psi))
        {
            var err = p.StandardError.ReadToEndAsync();
            string o = p.StandardOutput.ReadToEnd();
            p.WaitForExit();
            File.AppendAllText(logFile, "> " + exe + " " + args + "\r\n" + o + err.Result + "\r\n");
            return p.ExitCode;
        }
    }

    static string FindCtrl(string temp)
    {
        var cands = new List<string>();
        if (CtrlArg != null) cands.Add(CtrlArg);
        cands.Add(Path.Combine(Here, "GameData.7z"));
        cands.Add(Path.Combine(Here, "GameData"));
        cands.Add(Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.UserProfile), "Downloads", "GameData.7z"));
        foreach (string c in cands)
        {
            if (Directory.Exists(c))
            {
                string g = File.Exists(Path.Combine(c, @"data\_lvl_pc\common.lvl")) ? c : Path.Combine(c, "GameData");
                if (File.Exists(Path.Combine(g, @"addon\000\addme.script"))) return g;
            }
            else if (File.Exists(c) && c.EndsWith(".7z", StringComparison.OrdinalIgnoreCase))
                return Extract7z(c, temp);
        }
        Console.WriteLine();
        Console.WriteLine("BAD-AL's controller patch is needed (its console textures, Xbox fonts and Instant Action screen):");
        Console.WriteLine("  " + CtrlUrl);
        string a = Ask("Download it now (GameData.7z, 720 MB)? [Y/n] ").ToLowerInvariant();
        if (a == "n" || Console.IsInputRedirected)
            throw new Exception("Put GameData.7z next to Install.exe (or in Downloads), or run: Install.exe install --ctrl <GameData.7z>");
        string dl = Path.Combine(temp, "GameData.7z");
        System.Net.ServicePointManager.SecurityProtocol |= (System.Net.SecurityProtocolType)3072; // TLS 1.2
        using (var wc = new System.Net.WebClient())
        {
            int last = -1;
            wc.DownloadProgressChanged += (s, e) =>
            {
                if (e.ProgressPercentage / 10 != last) { last = e.ProgressPercentage / 10; Console.Write(" " + e.ProgressPercentage + "%"); }
            };
            wc.DownloadFileTaskAsync(new Uri(CtrlUrl), dl).Wait();
            Console.WriteLine();
        }
        return Extract7z(dl, temp);
    }

    static string Extract7z(string archive, string temp)
    {
        string dst = Path.Combine(temp, "ctrl");
        string args = "x -y -o" + Q(dst) + " " + Q(archive) + " " + string.Join(" ", CtrlFiles.Select(Q).ToArray());
        if (Run(Path.Combine(Here, @"bin\7zr.exe"), args, Path.Combine(temp, "build.log")) != 0 ||
            !File.Exists(Path.Combine(dst, CtrlFiles[2])))
            throw new Exception("Could not unpack " + archive + " (is it BAD-AL's GameData.7z?)");
        return Path.Combine(dst, "GameData");
    }

    static string FindXboxIngame(string temp)
    {
        string x = XboxArg ?? Ask("Optional, for the Xbox HUD: drag your own Xbox disc image (.iso) here and press Enter (Enter = skip): ");
        if (x == "") return null;
        if (Directory.Exists(x))
        {
            foreach (string c in new[] { @"Data\_LVL_XBOX\ingame.lvl", @"_LVL_XBOX\ingame.lvl", "ingame.lvl" })
                if (File.Exists(Path.Combine(x, c))) return Path.Combine(x, c);
            Step("no Data\\_LVL_XBOX\\ingame.lvl in " + x);
            return null;
        }
        if (x.EndsWith(".lvl", StringComparison.OrdinalIgnoreCase) && File.Exists(x)) return x;
        string outp = Path.Combine(temp, "xbox_ingame.lvl");
        if (File.Exists(x) && Run(Py(), Q(Path.Combine(Here, @"build\tools\xiso.py")) + " " + Q(x) + " Data/_LVL_XBOX/ingame.lvl " + Q(outp),
                Path.Combine(temp, "build.log")) == 0) return outp;
        Step("could not read " + x + " as an Xbox disc image");
        return null;
    }

    static string Py() { return Path.Combine(Here, @"bin\python\python.exe"); }

    static string BuildFromSources()
    {
        string temp = Path.Combine(Path.GetTempPath(), "XboxEdition_build");
        if (Directory.Exists(temp)) Directory.Delete(temp, true);
        Directory.CreateDirectory(temp);
        string logFile = Path.Combine(temp, "build.log");
        Console.WriteLine("Build (from your own Remaster install and the controller patch):");
        // the Remaster's original files: from the backup when reinstalling over this mod
        string rem = Path.Combine(temp, "rem");
        Directory.CreateDirectory(rem);
        foreach (string rel in Baseline)
        {
            string b = Path.Combine(Backup, "files", rel), src = File.Exists(b) ? b : Path.Combine(Root, rel);
            if (!File.Exists(src)) throw new Exception("missing " + rel + " - is the Remaster installed?");
            File.Copy(src, Path.Combine(rem, Path.GetFileName(rel)), true);
        }
        string ctrl = FindCtrl(temp);
        Step("controller patch: " + ctrl);
        string xb = FindXboxIngame(temp);
        Step(xb != null ? "Xbox HUD: from your disc image" : "Xbox HUD: skipped (the Remaster HUD stays)");
        string outDir = Path.Combine(temp, "out");
        string args = Q(Path.Combine(Here, @"build\tools\build.py")) + " --rem " + Q(rem) + " --remhud " +
            Q(Path.Combine(rem, "hud_16x09.lvl")) + " --game " + Q(Root) + " --ctrl " + Q(ctrl) + " --out " + Q(outDir) +
            " --work " + Q(Path.Combine(temp, "work")) + (xb != null ? " --xbox-ingame " + Q(xb) : "");
        Step("building (about a minute)...");
        if (Run(Py(), args, logFile) != 0) throw new Exception("the build failed - see " + logFile);
        Step("built");
        return outDir;
    }

    // exe.txt: "orig <md5>", "patched <md5>", then "<file offset hex> <old hex> <new hex>" lines
    static void PatchExe()
    {
        string exe = Path.Combine(Root, "BattlefrontII.exe");
        string[] l = Lines("exe.txt");
        string orig = l[0].Split(' ')[1], patched = l[1].Split(' ')[1];
        string cur = Md5(exe);
        if (cur == patched) { Step("already patched"); return; }
        if (cur != orig)
        {
            Step("SKIPPED: unknown BattlefrontII.exe version (md5 " + cur + "), the game was probably updated.");
            Step("Without it: no locked-class silhouettes/hero checks/map hiding in the class picker, no inline");
            Step("button icons in hints, and new profiles keep the PC keys for the hero prompt.");
            return;
        }
        string keepExe = Path.Combine(Backup, "BattlefrontII.exe");
        if (!File.Exists(keepExe)) File.Copy(exe, keepExe);
        byte[] b = File.ReadAllBytes(exe);
        for (int i = 2; i < l.Length; i++)
        {
            string[] p = l[i].Split(' ');
            int off = Convert.ToInt32(p[0], 16);
            byte[] o = Hex(p[1]), n = Hex(p[2]);
            for (int k = 0; k < o.Length; k++)
                if (b[off + k] != o[k]) throw new Exception("BattlefrontII.exe: unexpected bytes at " + p[0]);
            Array.Copy(n, 0, b, off, n.Length);
        }
        File.WriteAllBytes(exe, b);
        if (Md5(exe) != patched) throw new Exception("BattlefrontII.exe: result check failed");
        Step("patched (" + (l.Length - 2) + " changes)");
    }

    // sidepatch.txt: "<file> <TAB> <old hex> <TAB> <new hex> <TAB> <description>" - every occurrence, same length;
    // the offsets are recorded so uninstall can put the original bytes back (no 1 GB copy)
    static void PatchSide(string[] p)
    {
        string file = Path.Combine(Root, p[0]);
        if (!File.Exists(file)) { Step(p[0] + ": not found, skipped"); return; }
        byte[] o = Hex(p[1]), n = Hex(p[2]);
        string rec = Path.Combine(Backup, "side_" + Path.GetFileName(p[0]) + "_" + p[1].Substring(0, 8) + ".txt");
        var offs = new List<long>();
        var already = 0;
        using (var fs = new FileStream(file, FileMode.Open, FileAccess.ReadWrite))
        {
            const int Chunk = 32 << 20;
            byte[] buf = new byte[Chunk + o.Length];
            long pos = 0;
            int carry = 0;
            while (true)
            {
                fs.Position = pos + carry;
                int got = fs.Read(buf, carry, Chunk);
                int len = carry + got;
                for (int i = 0; i + o.Length <= len; i++)
                {
                    if (Match(buf, i, o)) offs.Add(pos + i);
                    else if (Match(buf, i, n)) already++;
                }
                if (got == 0) break;
                int keep = Math.Min(o.Length - 1, len);
                Array.Copy(buf, len - keep, buf, 0, keep);
                pos += len - keep;
                carry = keep;
            }
            foreach (long off in offs) { fs.Position = off; fs.Write(n, 0, n.Length); }
        }
        if (offs.Count > 0)
        {
            var old = File.Exists(rec) ? File.ReadAllLines(rec).ToList() : new List<string> { p[0], p[1], p[2] };
            old.AddRange(offs.Select(x => x.ToString()));
            File.WriteAllLines(rec, old);
        }
        Step(p[3] + ": " + (offs.Count > 0 ? offs.Count + " patched" : already > 0 ? "already patched" : "nothing found"));
    }

    static bool Match(byte[] b, int i, byte[] p)
    {
        for (int k = 0; k < p.Length; k++) if (b[i + k] != p[k]) return false;
        return true;
    }

    // ---------------------------------------------------------------- profiles
    // u32 CRC-32/BZIP2 of the rest; key binding entries: 3 u16 slots (keyboard DIK in the low byte)
    static readonly ushort[][] KeyChanges = {
        new ushort[] { 0xC9, 0x3B, 0, 0xCB, 0x3B, 0 },   // Accept  PgUp,F1 -> Left,F1
        new ushort[] { 0xD1, 0x3C, 0, 0xCD, 0x3C, 0 },   // Decline PgDn,F2 -> Right,F2
        new ushort[] { 0x1E, 0xCB, 0, 0x1E, 0, 0 },      // strafe A,Left -> A
        new ushort[] { 0x20, 0xCD, 0, 0x20, 0, 0 },      // strafe D,Right -> D
    };

    // the checksum covers the 0x1100 bytes of profile data after it (larger profiles append a gamepad section)
    static uint Crc(byte[] b, int start)
    {
        uint crc = 0xFFFFFFFF;
        int end = Math.Min(b.Length, start + 0x1100);
        for (int i = start; i < end; i++)
        {
            crc ^= (uint)b[i] << 24;
            for (int k = 0; k < 8; k++) crc = (crc & 0x80000000) != 0 ? (crc << 1) ^ 0x04C11DB7 : crc << 1;
        }
        return crc ^ 0xFFFFFFFF;
    }

    static void PatchProfile(string path)
    {
        byte[] b = File.ReadAllBytes(path);
        string name = Path.GetFileName(path);
        if (b.Length < 8 || BitConverter.ToUInt32(b, 0) != Crc(b, 4)) { Step(name + ": unknown format, skipped"); return; }
        int n = 0;
        var offs = new List<KeyValuePair<int, int>>();   // offset, change index
        for (int ci = 0; ci < KeyChanges.Length; ci++)
        {
            ushort[] c = KeyChanges[ci];
            for (int i = 4; i + 6 <= Math.Min(b.Length, 4 + 0x1100); i += 2)
                if (BitConverter.ToUInt16(b, i) == c[0] && BitConverter.ToUInt16(b, i + 2) == c[1] && BitConverter.ToUInt16(b, i + 4) == c[2])
                {
                    for (int s = 0; s < 3; s++) { b[i + 2 * s] = (byte)c[3 + s]; b[i + 2 * s + 1] = (byte)(c[3 + s] >> 8); }
                    offs.Add(new KeyValuePair<int, int>(i, ci));
                    n++;
                }
        }
        if (n == 0) { Step(name + ": already set (or custom keys)"); return; }
        string keep = Path.Combine(Backup, "profiles", name);   // just in case; uninstall reverses the entries
        if (!File.Exists(keep)) { Directory.CreateDirectory(Path.GetDirectoryName(keep)); File.Copy(path, keep); }
        Array.Copy(BitConverter.GetBytes(Crc(b, 4)), 0, b, 0, 4);
        File.WriteAllBytes(path, b);
        File.AppendAllLines(Path.Combine(Backup, "profiles.txt"), offs.Select(x => name + "\t" + x.Key + "\t" + x.Value));
        Step(name + ": " + n + " bindings");
    }

    // ---------------------------------------------------------------- uninstall
    static void Uninstall()
    {
        if (!Directory.Exists(Backup)) { Console.WriteLine("Not installed (no " + BackupName + " folder)."); return; }
        var skipped = new List<string>();
        // files: put the originals back / remove added files - only where the mod's file is still in place
        var ours = new Dictionary<string, string>(StringComparer.OrdinalIgnoreCase);
        string installedList = Path.Combine(Backup, "installed.txt");
        if (File.Exists(installedList))
            foreach (string l in File.ReadAllLines(installedList)) { string[] x = l.Split('\t'); if (x.Length == 2) ours[x[0]] = x[1]; }
        Func<string, bool> stillOurs = rel => File.Exists(Path.Combine(Root, rel)) && ours.ContainsKey(rel) && Md5(Path.Combine(Root, rel)) == ours[rel];
        string createdList = Path.Combine(Backup, "created.txt");
        if (File.Exists(createdList))
            foreach (string rel in File.ReadAllLines(createdList))
                if (rel != "" && File.Exists(Path.Combine(Root, rel)))
                {
                    if (stillOurs(rel))
                    {
                        File.Delete(Path.Combine(Root, rel));
                        Step("removed " + rel);
                        string dir = Path.GetDirectoryName(Path.Combine(Root, rel)); // folders the install created
                        while (dir.Length > Root.Length && Directory.Exists(dir) && !Directory.EnumerateFileSystemEntries(dir).Any())
                        {
                            Directory.Delete(dir);
                            dir = Path.GetDirectoryName(dir);
                        }
                    }
                    else skipped.Add(rel);
                }
        string files = Path.Combine(Backup, "files");
        if (Directory.Exists(files))
            foreach (string f in Directory.GetFiles(files, "*", SearchOption.AllDirectories))
            {
                string rel = f.Substring(files.Length).TrimStart('\\');
                if (stillOurs(rel)) { File.Copy(f, Path.Combine(Root, rel), true); Step("restored " + rel); }
                else skipped.Add(rel);
            }
        // exe: only if it is still the patched one (a game update replaces it anyway)
        string exe = Path.Combine(Root, "BattlefrontII.exe"), keepExe = Path.Combine(Backup, "BattlefrontII.exe");
        if (File.Exists(keepExe))
        {
            if (Md5(exe) == Lines("exe.txt")[1].Split(' ')[1]) { File.Copy(keepExe, exe, true); Step("restored BattlefrontII.exe"); }
            else skipped.Add("BattlefrontII.exe");
        }
        // side data: original bytes back where the patched ones still are
        foreach (string rec in Directory.GetFiles(Backup, "side_*.txt"))
        {
            string[] l = File.ReadAllLines(rec);
            byte[] o = Hex(l[1]), n = Hex(l[2]);
            int k = 0;
            using (var fs = new FileStream(Path.Combine(Root, l[0]), FileMode.Open, FileAccess.ReadWrite))
                for (int i = 3; i < l.Length; i++)
                {
                    long off = long.Parse(l[i]);
                    byte[] cur = new byte[n.Length];
                    fs.Position = off;
                    fs.Read(cur, 0, cur.Length);
                    if (cur.SequenceEqual(n)) { fs.Position = off; fs.Write(o, 0, o.Length); k++; }
                }
            Step(l[0] + ": " + k + " restored");
        }
        // profiles: reverse just the changed key entries (keeps any progress made since)
        string plist = Path.Combine(Backup, "profiles.txt");
        if (File.Exists(plist))
            foreach (var g in File.ReadAllLines(plist).Where(x => x != "").Select(x => x.Split('\t')).GroupBy(x => x[0]))
            {
                string path = Path.Combine(Root, "SaveGames", g.Key);
                if (!File.Exists(path)) continue;
                byte[] b = File.ReadAllBytes(path);
                if (BitConverter.ToUInt32(b, 0) != Crc(b, 4)) { skipped.Add("SaveGames\\" + g.Key); continue; }
                int k = 0;
                foreach (string[] e in g)
                {
                    int i = int.Parse(e[1]);
                    ushort[] c = KeyChanges[int.Parse(e[2])];
                    bool cur = true;
                    for (int s2 = 0; s2 < 3; s2++) if (BitConverter.ToUInt16(b, i + 2 * s2) != c[3 + s2]) cur = false;
                    if (!cur) continue;
                    for (int s2 = 0; s2 < 3; s2++) { b[i + 2 * s2] = (byte)c[s2]; b[i + 2 * s2 + 1] = (byte)(c[s2] >> 8); }
                    k++;
                }
                Array.Copy(BitConverter.GetBytes(Crc(b, 4)), 0, b, 0, 4);
                File.WriteAllBytes(path, b);
                Step(g.Key + ": " + k + " bindings restored");
            }
        string yml = Path.Combine(Root, "shader patch.yml");
        if (File.Exists(Path.Combine(Backup, "shaderpatch_fonts.txt")) && File.Exists(yml))
        {
            File.WriteAllText(yml, File.ReadAllText(yml).Replace("Scalable Fonts: no", "Scalable Fonts: yes"));
            Step("Shader Patch: Scalable Fonts: yes");
        }
        if (skipped.Count > 0)
        {
            Console.WriteLine();
            Console.WriteLine("Left alone (changed since the install, e.g. by a game update or another mod):");
            foreach (string x in skipped) Step(x);
            Console.WriteLine("The originals are still in " + Backup);
            return;
        }
        Directory.Delete(Backup, true);
        Console.WriteLine();
        Console.WriteLine("Uninstalled - everything is back as before the install.");
    }
}
