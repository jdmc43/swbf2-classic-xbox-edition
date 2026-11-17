"""TEST ONLY: build a test shell.lvl into xbox/build-<name>/ (personal use). Like the real build (tools/build.py)
the Remaster's shell_interface stays untouched (renamed xbe_shell_interface) and a wrapper runs
  controller hooks + tests/shells/<name>/before.lua + ScriptCB_DoFile("xbe_shell_interface") + tests/shells/<name>/tail.lua
Shells: alttest (opens the Instant Action ALT screen), herotest (autostart with IA heroes on),
herokeys (normal profile flow, then a match with IA heroes on).
usage: testshell.py <name>      Remaster lvl dir: $SWBF2_REMASTER_LVL or the backup in Documents
then:  tools/safetest.sh xbox/build-<name> <label> <steps...>   (copy ingame/core/xbring.lvl in as needed)
"""
import os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
from merge import Lvl, write_lvl
from build import wrap_script

REM = os.environ.get("SWBF2_REMASTER_LVL") or os.path.join(
    os.path.expanduser("~"), "Documents", "SWBF2-backups", "remaster-before-controller", "data", "_lvl_pc")


def read(p):
    p = os.path.join(ROOT, p)
    return open(p, encoding="latin-1").read() if os.path.exists(p) else ""


def main(name):
    src = os.path.join("tests", "shells", name)
    out = os.path.join(ROOT, "xbox", "build-" + name)
    os.makedirs(out, exist_ok=True)
    before = read("compat/console/title_hook.lua") + "\n" + read("compat/console/pad_hook.lua") + "\n" + \
        read(os.path.join(src, "before.lua"))
    sh = Lvl(os.path.join(REM, "shell.lvl"))
    wrap_script(sh, "shell_interface", before, read(os.path.join(src, "tail.lua")), out, "test shell")
    open(os.path.join(out, "shell.lvl"), "wb").write(write_lvl(sh.items))
    print("built", os.path.join(out, "shell.lvl"))


if __name__ == "__main__":
    main(sys.argv[1])
