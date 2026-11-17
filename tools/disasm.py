"""Disassemble scr_ chunks with luac50 -l and compare versions.

usage: disasm.py <lvl-label>=<path> ... -- name [name ...]
Prints, for every script name, the size of the instruction-level diff between versions and
the nearest UOP/ctrl source file.
"""
import difflib
import glob
import os
import re
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import munge  # noqa: E402
import ucfb  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def body_of(raw_chunk):
    buf = raw_chunk
    for t, a, b in ucfb.read_chunks(buf, 8, len(buf)):
        if t == b"BODY":
            return buf[a:b - 1]  # drop ScriptMunge trailing NUL
    raise ValueError("no BODY")


def listing(bytecode):
    with tempfile.NamedTemporaryFile(delete=False, suffix=".luac") as f:
        f.write(bytecode)
        p = f.name
    try:
        out = subprocess.run([munge.LUAC, "-l", "-p", p], capture_output=True, text=True,
                             errors="replace").stdout
    finally:
        os.unlink(p)
    lines = []
    for ln in out.splitlines():
        ln = re.sub(r"^\s*\d+\s+\[-\]\s+", "", ln)  # drop pc + line
        ln = re.sub(r"[0-9a-fA-F]{8}", "ADDR", ln)  # function addresses
        ln = re.sub(r"^(main|function) <[^>]*>", r"\1", ln)
        lines.append(ln.strip())
    return lines


def chunk_raw(path, name):
    buf, items = ucfb.load(path)
    for it in items:
        if it["tag"] == "scr_" and it["name"] == name:
            return buf[it["start"]:it["end"]]
    return None


def source_candidates(name):
    for d in ("src/uop/CustomLVL", "src/ctrl_repo"):
        for p in glob.glob(os.path.join(ROOT, d, "**", name + ".lua"), recursive=True):
            yield os.path.relpath(p, ROOT).replace("\\", "/"), p


def ndiff(a, b):
    return sum(1 for l in difflib.unified_diff(a, b, lineterm="", n=0)
               if l[:1] in "+-" and not l.startswith(("+++", "---")))


if __name__ == "__main__":
    sep = sys.argv.index("--")
    versions = dict(a.split("=", 1) for a in sys.argv[1:sep])
    for name in sys.argv[sep + 1:]:
        lst = {}
        for label, path in versions.items():
            raw = chunk_raw(path, name)
            if raw is not None:
                lst[label] = listing(body_of(raw))
        srcs = {}
        for rel, p in source_candidates(name):
            try:
                srcs[rel] = listing(munge.compile_lua(p)[:-1])
            except subprocess.CalledProcessError:
                pass
        print(f"== {name}  (instructions: " + ", ".join(f"{k}={len(v)}" for k, v in lst.items()) + ")")
        labels = list(lst)
        for i in range(len(labels)):
            for j in range(i + 1, len(labels)):
                print(f"   {labels[i]} vs {labels[j]}: {ndiff(lst[labels[i]], lst[labels[j]])} changed lines")
        for label in labels:
            if srcs:
                best = min(srcs, key=lambda s: ndiff(srcs[s], lst[label]))
                print(f"   nearest source to {label}: {best} ({ndiff(srcs[best], lst[label])} lines)")
