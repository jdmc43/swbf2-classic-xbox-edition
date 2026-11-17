"""Build the distributable package (personal use): dist/SWBF2-XboxEdition/ + .zip
  Install.exe   installer/uninstaller (installer/Install.cs, built with the .NET Framework csc)
  README.txt
  payload/      files.txt, exe.txt, sidepatch.txt + files/...
Inputs: xbox/final (tools/assemble.py, no test flags), the stock exe backup + the patched installed exe
(tools/exepatch.py), the Remaster originals in ~/Documents/SWBF2-backups (for the "is this the Remaster file"
check). usage: package.py [version]
"""
import hashlib, os, shutil, struct, subprocess, sys, zipfile

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GAME = "C:/Program Files (x86)/Steam/steamapps/common/Star Wars Battlefront II Classic/GameData"
BK = os.path.join(os.path.expanduser("~"), "Documents", "SWBF2-backups")
FINAL = os.path.join(HERE, "xbox", "final")
VERSION = sys.argv[1] if len(sys.argv) > 1 else "1.0"
OUT = os.path.join(HERE, "dist", "SWBF2-XboxEdition")
CSC = r"C:\Windows\Microsoft.NET\Framework64\v4.0.30319\csc.exe"


def md5(p):
    return hashlib.md5(open(p, "rb").read()).hexdigest()


def fnv(s):
    h = 0x811C9DC5
    for c in s.lower().encode():
        h = ((h ^ c) * 16777619) & 0xFFFFFFFF
    return h


# dest (relative to GameData) -> (source, Remaster original it replaces or None)
REM = os.path.join(BK, "remaster-before-controller")
FILES = [
    ("data/_lvl_pc/shell.lvl", "data/_lvl_pc/shell.lvl", "data/_lvl_pc/shell.lvl"),
    ("data/_lvl_pc/ingame.lvl", "data/_lvl_pc/ingame.lvl", "data/_lvl_pc/ingame.lvl"),
    ("data/_lvl_pc/common.lvl", "data/_lvl_pc/common.lvl", "data/_lvl_pc/common.lvl"),
    ("data/_lvl_pc/core.lvl", "data/_lvl_pc/core.lvl", "data/_lvl_pc/core.lvl"),
    ("data/_lvl_pc/xbring.lvl", "data/_lvl_pc/xbring.lvl", None),
    ("addon/000/addme.script", "addon/000/addme.script", None),
    ("addon/000/core.lvl", "addon/000/core.lvl", None),
    ("addon/Remaster/HUD/hud_16x09.lvl", "hud/hud_16x09.lvl", "@hud"),
    ("addon/Remaster/HUD/hud_16x09_ia.lvl", "hud/hud_16x09_ia.lvl", None),
    ("addon/Remaster/Fonts/arialblack_default.lvl", "remafonts.lvl", "@font:arialblack_default.lvl"),
    ("addon/Remaster/Fonts/arialblack_2k.lvl", "remafonts.lvl", "@font:arialblack_2k.lvl"),
    ("addon/Remaster/Fonts/arialblack_4k.lvl", "remafonts.lvl", "@font:arialblack_4k.lvl"),
]


def original(spec):
    if spec is None:
        return "-"
    if spec == "@hud":
        p = os.path.join(BK, "remaster-hud-original", "hud_16x09.lvl")
    elif spec.startswith("@font:"):
        p = os.path.join(BK, "remaster-fonts-original", spec[6:])
    else:
        p = os.path.join(REM, spec)
    return md5(p) if os.path.exists(p) else "-"


def exe_diff():
    a = open(os.path.join(BK, "BattlefrontII.exe.orig"), "rb").read()
    b = open(os.path.join(GAME, "BattlefrontII.exe"), "rb").read()
    assert len(a) == len(b)
    runs, i = [], 0
    while i < len(a):
        if a[i] != b[i]:
            j = i
            while j < len(a) and a[j] != b[j]:
                j += 1
            runs.append((i, a[i:j], b[i:j]))
            i = j
        else:
            i += 1
    lines = ["orig " + hashlib.md5(a).hexdigest(), "patched " + hashlib.md5(b).hexdigest()]
    lines += ["%x %s %s" % (o, x.hex(), y.hex()) for o, x, y in runs]
    return lines


README = """Star Wars Battlefront II Classic - Xbox Edition  (version {ver})
==============================================================

The PC game played and presented like the original Xbox version, with a controller:
- Xbox class picker: a 3D carousel of the units, locked classes as black silhouettes,
  the hero when you earned and accepted him ("Play as ...?" - d-pad left / Left arrow = Yes)
- Xbox widescreen HUD, Xbox fonts, console button icons in the hints
- Instant Action (ALT) console map screen, controller navigation in the menus

REQUIREMENTS
- Star Wars Battlefront II Classic (Steam, 2024 update)
- The "Battlefront II Remaster" mod (Jan 2026 version) installed (GameData\\addon\\Remaster)
- A controller through Steam Input, layout below (keyboard + mouse still work)

INSTALL
1. Close the game. Extract this folder anywhere.
2. Run Install.exe and press I. It finds the game through Steam
   (or run:  Install.exe install "D:\\...\\Star Wars Battlefront II Classic\\GameData").
Everything it changes is backed up in GameData\\XboxEdition_backup.

UNINSTALL
Run Install.exe and press U. It puts back what it changed (your profiles keep their progress).
Steam's "Verify integrity of game files" also removes most of it (and the Remaster).

WHAT THE INSTALLER CHANGES
- Replaces data\\_lvl_pc\\shell.lvl, ingame.lvl, common.lvl, core.lvl; adds data\\_lvl_pc\\xbring.lvl
- addon\\000 (Instant Action ALT screen), addon\\Remaster\\HUD and \\Fonts files
- Patches BattlefrontII.exe (only the known Steam version, else skipped): class lock / hero checks for
  the carousel, hiding the map while choosing a class, more inline button icons, default keys
- data\\_lvl_pc\\side\\rep.lvl: the Republic commando pistol uses the DC-17 model (the HD one has no HUD icon)
- Every profile in SaveGames: Left/Right arrow answer the hero prompt (Accept/Decline; F1/F2 still work),
  so the arrows no longer strafe (A/D do). New profiles get the same keys.
- shader patch.yml (if Shader Patch is installed): Scalable Fonts: no (it would replace the Xbox fonts)

STEAM INPUT LAYOUT (game > Controller settings)
Start from the community layout "Original Xbox Controls" and make sure these keys are sent:
  A = Space + Enter     B = Left Alt + C      X = Q        Y = E
  D-pad: up F4, down R, left F1, right F2      LB = 2       RB = 1
  Left stick = WASD, click = Left Shift        Right stick = mouse
  RT = left mouse, LT = right mouse            Start = Esc  Back = M

INSTANT ACTION HEROES
Options on the Instant Action screen > Heroes. "Assign To: Best Player" counts the bots, so you may
rarely get the hero; "Worst Player" or a low points value helps.

CREDITS
Battlefront II Remaster by Anakin; Unofficial Patch / controller patch by BAD-AL (Instant Action ALT screen,
console button textures, Xbox fonts in PC format); Xbox HUD from the original Xbox release.
"""


def main():
    if os.path.exists(OUT):
        shutil.rmtree(OUT)
    pay = os.path.join(OUT, "payload")
    os.makedirs(pay)
    # dest <TAB> source, relative to the files root (payload\files prebuilt, or the installer's build output)
    man = ["# dest\tsource file\tmd5 of the Remaster file it replaces (- = none)"]
    for dest, src, orig in FILES:
        if not PUBLIC:
            d = os.path.join(pay, "files", src)
            if not os.path.exists(d):
                os.makedirs(os.path.dirname(d), exist_ok=True)
                shutil.copy(os.path.join(FINAL, src), d)
        man.append("%s\t%s\t%s" % (dest.replace("/", "\\"), src.replace("/", "\\"), original(orig)))
    if PUBLIC:
        public_parts()
    open(os.path.join(pay, "files.txt"), "w").write("\n".join(man) + "\n")
    ex = exe_diff()
    open(os.path.join(pay, "exe.txt"), "w").write("\n".join(ex) + "\n")
    old = struct.pack("<I", fnv("GeometryName")) + b"rep_weap_inf_smallpistol\0"
    new = struct.pack("<I", fnv("GeometryName")) + b"rep_weap_inf_pistol\0".ljust(len(old) - 4, b"\0")
    open(os.path.join(pay, "sidepatch.txt"), "w").write(
        "data\\_lvl_pc\\side\\rep.lvl\t%s\t%s\tcommando pistol model (rep.lvl)\n" % (old.hex(), new.hex()))
    open(os.path.join(OUT, "README.txt"), "w", newline="\r\n").write((README_PUBLIC if PUBLIC else README).format(ver=VERSION))
    src = os.path.join(HERE, "installer", "Install.cs")
    env = dict(os.environ, MSYS2_ARG_CONV_EXCL="*")
    subprocess.check_call([CSC, "-nologo", "-optimize", "-out:" + os.path.join(OUT, "Install.exe"), src], env=env)
    z = os.path.join(HERE, "dist", "SWBF2-XboxEdition-%s%s.zip" % (VERSION, "-public" if PUBLIC else ""))
    with zipfile.ZipFile(z, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
        for root, _, files in os.walk(OUT):
            for f in files:
                p = os.path.join(root, f)
                zf.write(p, os.path.join("SWBF2-XboxEdition", os.path.relpath(p, OUT)))
    print("exe changes:", len(ex) - 2)
    print("package:", OUT)
    print("zip:", z, os.path.getsize(z) // 1000000, "MB")


# ---------------------------------------------------------------- public package (builds on the player's PC)
BUILD_TOOLS = ["build.py", "sideclasses.py", "skins.py", "skindump.lua", "gen_units.py", "xbring_variants.py",
               "xboxfonts.py", "xboxtips.py", "hudmerge.py", "hudfix.py", "hudtree.py", "munge.py", "merge.py",
               "ucfb.py", "xiso.py", "luac50.exe", "lua50.exe"]
BUILD_LUA = ["compat/console/title_hook.lua", "compat/console/pad_hook.lua", "compat/console/tail_game.lua",
             "compat/console/alt_wrap.lua", "compat/xboxpicker/buildscreen.lua", "compat/xboxpicker/xboxflow.lua",
             "compat/xboxpicker/cpselect.lua", "compat/xboxpicker/ring.lua"]


DOWNLOADS = {  # bundled third-party tools, fetched from their official sites when missing
    "7zr.exe": "https://www.7-zip.org/a/7zr.exe",
    "python-embed.zip": "https://www.python.org/ftp/python/3.12.10/python-3.12.10-embed-amd64.zip",
}


def fetch_bins():
    import urllib.request
    d = os.path.join(HERE, "installer", "bin")
    os.makedirs(d, exist_ok=True)
    for name, url in DOWNLOADS.items():
        p = os.path.join(d, name)
        if not os.path.exists(p):
            print("downloading", url)
            urllib.request.urlretrieve(url, p)


def public_parts():
    fetch_bins()
    b = os.path.join(OUT, "build")
    os.makedirs(os.path.join(b, "tools"))
    for f in BUILD_TOOLS:
        shutil.copy(os.path.join(HERE, "tools", f), os.path.join(b, "tools", f))
    for f in BUILD_LUA:
        os.makedirs(os.path.join(b, os.path.dirname(f)), exist_ok=True)
        shutil.copy(os.path.join(HERE, f), os.path.join(b, f))
    bin_ = os.path.join(OUT, "bin")
    os.makedirs(bin_)
    shutil.copy(os.path.join(HERE, "installer", "bin", "7zr.exe"), bin_)
    with zipfile.ZipFile(os.path.join(HERE, "installer", "bin", "python-embed.zip")) as zf:
        zf.extractall(os.path.join(bin_, "python"))
    for f in ("LICENSE.txt", "NOTICE.txt", "THIRD-PARTY-NOTICES.txt"):
        shutil.copy(os.path.join(HERE, "installer", f), os.path.join(OUT, f))


README_PUBLIC = """Star Wars Battlefront II Classic - Xbox Edition  (version {ver})
==============================================================

The PC game played and presented like the original Xbox version, with a controller:
- Xbox class picker: a 3D carousel of the units, locked classes as black silhouettes, the hero when you
  earned and accepted him ("Play as ...?" - d-pad left / Left arrow = Yes)
- Xbox fonts, console button icons in the hints and on the end-of-match stats, the Xbox widescreen HUD
  (from your own Xbox disc, optional)
- Instant Action (ALT) console map screen, controller navigation in the menus

This package contains only this mod's own code. The installer builds the mod files on your PC from:
  1. Star Wars Battlefront II Classic (Steam, 2024 update)
       https://store.steampowered.com/app/6060/
  2. the "Battlefront II Remaster" by Anakin (Jan 2026) - download "Battlefront 2 Remaster Installer
     (Jan 2026)" from the Files tab and install it:
       https://www.nexusmods.com/battlefront2/mods/1191
  3. BAD-AL's "UOP controller patch" 1.1 - its GameData.7z (do not install it, the installer only reads it):
       https://github.com/BAD-AL/data_UOP_controller_patch/releases/tag/1.1
     The installer finds GameData.7z next to Install.exe or in your Downloads folder, or downloads it itself.
  4. optional: your own Xbox "Star Wars Battlefront II" disc image (.iso) - for the Xbox HUD

INSTALL
1. Install the Remaster. Close the game. Extract this folder anywhere.
2. Run Install.exe, press I, answer the questions (the build takes about a minute).
   Or:  Install.exe install ["...\\GameData"] [--ctrl GameData.7z] [--xbox "disc.iso"]
Everything it changes is backed up in GameData\\XboxEdition_backup.

UNINSTALL
Run Install.exe and press U. It puts back what it changed (your profiles keep their progress).

WHAT THE INSTALLER CHANGES
- data\\_lvl_pc\\shell.lvl, ingame.lvl, common.lvl, core.lvl (rebuilt from the Remaster's) and xbring.lvl (new)
- addon\\000 (the controller patch's Instant Action screen), addon\\Remaster\\Fonts, \\HUD (with a disc image)
- BattlefrontII.exe (only the known Steam version): class lock / hero checks for the carousel, hiding the
  map while choosing a class, more inline button icons, Left/Right arrows for the hero prompt in new profiles
- data\\_lvl_pc\\side\\rep.lvl: the Republic commando pistol uses the DC-17 model (the HD one has no HUD icon)
- every profile: Left/Right arrow answer the hero prompt (Accept/Decline; F1/F2 still work), A/D strafe
- shader patch.yml (if Shader Patch is installed): Scalable Fonts: no

STEAM INPUT LAYOUT (game > Controller settings)
Start from the community layout "Original Xbox Controls" and make sure these keys are sent:
  A = Space + Enter     B = Left Alt + C      X = Q        Y = E
  D-pad: up F4, down R, left F1, right F2      LB = 2       RB = 1
  Left stick = WASD, click = Left Shift        Right stick = mouse
  RT = left mouse, LT = right mouse            Start = Esc  Back = M

INSTANT ACTION HEROES
Instant Action options > Heroes. "Assign To: Best Player" counts the bots, so you rarely get the hero;
"Worst Player" or a low points value helps.

CREDITS
Battlefront II Remaster by Anakin and its contributors; UOP controller patch by BAD-AL; Unofficial Patch v1.3
by Zerted. This mod needs their work but does not contain it. This mod's code: Apache License 2.0
(LICENSE.txt, NOTICE.txt). Bundled tools: Python 3.12 (PSF license), 7-Zip 7zr.exe (LGPL), Lua 5.0.2 (MIT) -
see THIRD-PARTY-NOTICES.txt.
"""

PUBLIC = "--public" in sys.argv
if PUBLIC:
    sys.argv.remove("--public")
    VERSION = sys.argv[1] if len(sys.argv) > 1 else "1.0"
    OUT = os.path.join(HERE, "dist", "SWBF2-XboxEdition-public")

if __name__ == "__main__":
    main()
