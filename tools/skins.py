"""Skin table of the Remaster's skin changer (personal use): runs its user_script_9 offline (tools/lua50.exe +
tools/skindump.lua with stub engine functions) for every string constant of the script as a skin name and keeps
the SetClassProperty calls of the real skin sets -> TSV lines  skin <TAB> class <TAB> property <TAB> value
(input of tools/xbring_variants.py; the class picker's ring shows the map's skins).
usage: skins.py <user_script_9.lvl> <out.tsv> [<work dir>]
"""
import os, re, subprocess, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from ucfb import read_chunks


def script_body(lvl, name):
    b = open(lvl, "rb").read()
    for t, a, z in read_chunks(b, 8, len(b)):
        if t != b"scr_":
            continue
        kids = read_chunks(b, a, z)
        n = next((b[x:y].split(b"\0")[0].decode() for tt, x, y in kids if tt == b"NAME"), "")
        if n == name:
            return next(b[x:y] for tt, x, y in kids if tt == b"BODY")
    raise SystemExit("no script %s in %s" % (name, lvl))


def main(lvl, out, work=None):
    work = os.path.abspath(work or tempfile.mkdtemp())
    lvl, out = os.path.abspath(lvl), os.path.abspath(out)
    os.makedirs(work, exist_ok=True)
    luac = os.path.join(work, "user_script_9.luac")
    open(luac, "wb").write(script_body(lvl, "user_script_9"))
    listing = subprocess.run([os.path.join(HERE, "luac50.exe"), "-l", luac], capture_output=True, text=True,
                             errors="replace").stdout
    names = sorted(set(re.findall(r'; "([^"\n]{1,40})"', listing)))
    nf = os.path.join(work, "skin_names.txt")
    open(nf, "w", newline="\n").write("\n".join(names) + "\n")
    raw = os.path.join(work, "skins_raw.tsv")
    subprocess.run([os.path.join(HERE, "lua50.exe"), os.path.join(HERE, "skindump.lua"), luac, nf, raw, "0"],
                   check=True, cwd=work)
    keep = [l for l in open(raw, encoding="latin-1") if l.count("\t") == 3 and "\tREAD\t" not in l
            and "\tERROR\t" not in l]
    open(out, "w", encoding="latin-1", newline="\n").writelines(keep)
    print("skins: %d sets, %d properties" % (len({l.split(chr(9))[0] for l in keep}), len(keep)))


if __name__ == "__main__":
    main(*sys.argv[1:4])
