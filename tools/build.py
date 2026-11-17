"""Build the Xbox Edition files from the player's own installs (used by the developer build and by the public
installer). Third-party scripts are never copied or rebuilt from source: their compiled chunks stay untouched
under another name and small wrapper chunks run them (ScriptCB_DoFile) with our code around them.

usage: build.py --rem <Remaster lvl dir> --remhud <Remaster hud_16x09.lvl>
                --game <GameData> --ctrl <controller patch GameData> --out <dir>
                [--xbox-ingame <Xbox ingame.lvl>] [--work <dir>] [--flags "<lua>"] [--probe]
  --rem      the Remaster's data\\_lvl_pc files (shell, ingame, common, core .lvl) as installed by the Remaster
  --game     GameData (side .lvl files and user_script_9.lvl are read from it)
  --ctrl     BAD-AL's controller patch, the GameData folder of its release GameData.7z
  --xbox-ingame  _LVL_XBOX\\ingame.lvl from the player's own Xbox disc: the Xbox HUD (optional)
out: data/_lvl_pc/{shell,ingame,common,core,xbring}.lvl, addon/000/{addme.script,core.lvl},
     remafonts.lvl, hud/hud_16x09{,_ia}.lvl (with --xbox-ingame), build.txt
"""
import argparse, os, shutil, struct, subprocess, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import munge, ucfb
from merge import Lvl, raw_items, unpad, write_lvl

PY = sys.executable
LOG = []


def log(s):
    LOG.append(s)
    print(s, flush=True)


def lua(*names):
    return "\n".join(open(os.path.join(ROOT, n), encoding="latin-1").read() for n in names)


def compile_into(lvl, name, source, work, why):
    """add scr_ <name> compiled from the Lua text after the renamed original"""
    p = os.path.join(work, "_" + name + ".lua")
    open(p, "w", encoding="latin-1").write(source)
    lvl.insert_after(None, ("scr_", name, 0), unpad(munge.scr_chunk(name, p)), why)


def wrap_script(lvl, name, before, after, work, why):
    """original chunk -> xbe_<name>; new <name> = before + ScriptCB_DoFile("xbe_<name>") + after"""
    orig = "xbe_" + name
    lvl.rename_script(name, orig)
    compile_into(lvl, name, before + '\nScriptCB_DoFile("%s")\n' % orig + after, work, why)


HOOKS = ("compat/console/title_hook.lua", "compat/console/pad_hook.lua")


def build(a):
    out, work = a.out, a.work or tempfile.mkdtemp(prefix="xbe_")
    lvl_out = os.path.join(out, "data", "_lvl_pc")
    for d in (lvl_out, os.path.join(out, "addon", "000"), work):
        os.makedirs(d, exist_ok=True)
    ctrl_lvl = os.path.join(a.ctrl, "data", "_lvl_pc")

    # 1. class table, skins, unit table, ring variants (all from the player's game files)
    side = os.path.join(a.game, "data", "_lvl_pc", "side")
    sides = os.path.join(work, "sides.json")
    with open(sides, "w") as f:
        subprocess.run([PY, os.path.join(HERE, "sideclasses.py")] +
                       [os.path.join(side, x) for x in sorted(os.listdir(side)) if x.lower().endswith(".lvl")],
                       stdout=f, check=True)
    skins = os.path.join(work, "skins.tsv")
    subprocess.run([PY, os.path.join(HERE, "skins.py"), os.path.join(a.game, "data", "_lvl_pc", "user_script_9.lvl"),
                    skins, os.path.join(work, "skins")], check=True)
    units = os.path.join(work, "units.lua")
    subprocess.run([PY, os.path.join(HERE, "gen_units.py"), sides, units], check=True)
    variants = os.path.join(work, "variants.lua")
    subprocess.run([PY, os.path.join(HERE, "xbring_variants.py"), a.game, sides, lvl_out, skins], check=True,
                   env=dict(os.environ, XBRING_VARIANTS_LUA=variants))
    log("ring variants: xbring.lvl")

    # 2. ingame.lvl: class picker around the untouched ifs_pc_spawnselect, hooks around game_interface
    ing = Lvl(os.path.join(a.rem, "ingame.lvl"))
    picker = ("compat/xboxpicker/buildscreen.lua", "compat/xboxpicker/xboxflow.lua", "compat/xboxpicker/cpselect.lua")
    after = lua(*picker) + "\n" + open(units, encoding="latin-1").read() + "\n" + \
        open(variants, encoding="latin-1").read() + "\n" + (a.flags or "") + "\n" + lua("compat/xboxpicker/ring.lua")
    if a.probe:
        after += "\n" + lua("compat/xboxpicker/probe.lua")
    wrap_script(ing, "ifs_pc_spawnselect", "", after, work, "Xbox class picker")
    ctrl_common = dict(raw_items(os.path.join(ctrl_lvl, "common.lvl"))[1])
    raw = ctrl_common[("tex_", "btna", 0)]
    kids = ucfb.read_chunks(raw, 8, len(raw))
    body = b"".join(munge.chunk(t, b"xbpick_btna\0" if t == b"NAME" else raw[s:e]) for t, s, e in kids)
    ing.insert_after(None, ("tex_", "xbpick_btna", 0), b"tex_" + struct.pack("<I", len(body)) + body, "Xbox A icon")
    wrap_script(ing, "game_interface", lua(*HOOKS), lua("compat/console/tail_game.lua"), work, "controller layer")
    open(os.path.join(lvl_out, "ingame.lvl"), "wb").write(write_lvl(ing.items))
    log("ingame.lvl")

    # 3. shell.lvl: hooks around the Remaster's shell_interface
    sh = Lvl(os.path.join(a.rem, "shell.lvl"))
    wrap_script(sh, "shell_interface", lua(*HOOKS), "", work, "controller layer")
    open(os.path.join(lvl_out, "shell.lvl"), "wb").write(write_lvl(sh.items))
    log("shell.lvl")

    # 4. common.lvl: the controller patch's console button/border/header textures
    cm = Lvl(os.path.join(a.rem, "common.lvl"))
    remc = dict(cm.items)
    n = 0
    for k, v in ctrl_common.items():
        if k[0] == "tex_" and remc.get(k) != v:
            (cm.replace if k in remc else (lambda kk, vv, w: cm.insert_after(None, kk, vv, w)))(k, v, "console texture")
            n += 1
    open(os.path.join(lvl_out, "common.lvl"), "wb").write(write_lvl(cm.items))
    log("common.lvl: %d console textures" % n)

    # 5. core.lvl: Xbox fonts (the controller patch's PC conversion) + controller hint texts; remafonts.lvl
    subprocess.run([PY, os.path.join(HERE, "xboxfonts.py"), a.rem, work], check=True,
                   env=dict(os.environ, SWBF2_CTRL=a.ctrl))
    subprocess.run([PY, os.path.join(HERE, "xboxtips.py"), os.path.join(work, "core.lvl"),
                    os.path.join(lvl_out, "core.lvl")], check=True)
    shutil.copy(os.path.join(work, "remafonts.lvl"), os.path.join(out, "remafonts.lvl"))
    log("core.lvl, remafonts.lvl")

    # 6. addon/000: the ALT Instant Action screen, its script untouched, wrapped
    ad = Lvl(os.path.join(a.ctrl, "addon", "000", "addme.script"))
    ad.rename_script("ifs_missionselect_console", "xbe_missionselect_console")
    compile_into(ad, "ifs_missionselect_console", lua("compat/console/alt_wrap.lua"), work, "ALT screen adjustments")
    open(os.path.join(out, "addon", "000", "addme.script"), "wb").write(write_lvl(ad.items))
    shutil.copy(os.path.join(a.ctrl, "addon", "000", "core.lvl"), os.path.join(out, "addon", "000", "core.lvl"))
    log("addon/000")

    # 7. Xbox HUD (only with the player's own Xbox ingame.lvl)
    if a.xbox_ingame:
        hd = os.path.join(out, "hud")
        os.makedirs(hd, exist_ok=True)
        xb = dict((k, v) for k, v in raw_items(a.xbox_ingame)[1] if k[0] == "hud_")
        h = Lvl(a.remhud)
        n = 0
        for i, (k, v) in enumerate(h.items):
            if k[0] == "hud_" and k in xb and b"3playerhud" not in v:  # the Remaster's 3-player HUD stays
                h.items[i][1] = xb[k]
                n += 1
        xbhud = os.path.join(work, "hud_16x09.xbox.lvl")
        open(xbhud, "wb").write(write_lvl(h.items))
        merged = os.path.join(work, "hud_16x09.merged.lvl")
        subprocess.run([PY, os.path.join(HERE, "hudmerge.py"), xbhud, a.remhud, merged], check=True)
        subprocess.run([PY, os.path.join(HERE, "hudfix.py"), merged, os.path.join(hd, "hud_16x09.lvl")], check=True)
        subprocess.run([PY, os.path.join(HERE, "hudfix.py"), merged, os.path.join(hd, "hud_16x09_ia.lvl")], check=True,
                       env=dict(os.environ, HUD_IA="1"))
        log("Xbox HUD: %d hud chunks from the Xbox disc" % n)
    else:
        log("Xbox HUD: skipped (no Xbox ingame.lvl)")
    open(os.path.join(out, "build.txt"), "w").write("\n".join(LOG) + "\n")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    for k in ("rem", "remhud", "game", "ctrl", "out"):
        p.add_argument("--" + k, required=True)
    p.add_argument("--xbox-ingame")
    p.add_argument("--work")
    p.add_argument("--flags")
    p.add_argument("--probe", action="store_true")
    build(p.parse_args())
