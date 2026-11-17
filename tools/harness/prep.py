"""Prepare an offline test-bench run: extract compiled scripts from .lvl files and list which
globals the engine (exe) provides.

usage: prep.py <out_dir> <BattlefrontII.exe> <lvl> [<lvl> ...]     (later lvls override earlier)

out_dir/scripts/<name>.luac   - Lua 5.0 bytecode, runnable by tools/lua50.exe
out_dir/engine_names.lua      - ENGINE = { name = true, ... } (globals the exe registers)
"""
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import disasm  # noqa: E402
import ucfb  # noqa: E402


def main(out, exe, lvls):
    sdir = os.path.join(out, "scripts")
    os.makedirs(sdir, exist_ok=True)
    for f in os.listdir(sdir):
        os.remove(os.path.join(sdir, f))
    reads, writes, origin = set(), set(), {}
    for lvl in lvls:
        buf, items = ucfb.load(lvl)
        for it in items:
            if it["tag"] != "scr_":
                continue
            raw = buf[it["start"]:it["end"]]
            body = disasm.body_of(raw)
            open(os.path.join(sdir, it["name"].lower() + ".luac"), "wb").write(body)
            origin[it["name"].lower()] = os.path.basename(lvl)
            for ln in disasm.listing(body):
                m = re.search(r"(GETGLOBAL|SETGLOBAL)\s+\S+\s+\S+\s*;\s*(\w+)", ln)
                if m:
                    (reads if m.group(1) == "GETGLOBAL" else writes).add(m.group(2))
    strings = set(subprocess.run(["strings", "-n", "4", exe], capture_output=True, text=True,
                                 errors="replace").stdout.split())
    engine = sorted(n for n in reads if n in strings and not re.match(r"^(ifs_|g[A-Z])", n))  # Lua-side screens/variables are not engine functions
    unknown = sorted(n for n in reads - writes - set(engine)
                     if re.match(r"^(ScriptCB_|IF[A-Z][A-Za-z]*_|AddIFScreen|ReadDataFile)", n))
    with open(os.path.join(out, "engine_names.lua"), "w") as f:
        f.write("ENGINE = {\n")
        for n in engine:
            f.write(f'  ["{n}"] = true,\n')
        f.write("}\n")
    print(f"{len(origin)} scripts extracted, {len(engine)} engine globals used")
    if unknown:
        print("called but provided by NEITHER scripts nor exe (will error in game unless guarded):")
        for n in unknown:
            print("   ", n)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], sys.argv[3:])
