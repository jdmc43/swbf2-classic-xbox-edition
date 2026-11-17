"""List models in a .lvl (recursing into lvl_ sub-levels): segments' material names and textures.
usage: modlinfo.py <lvl> [name-substring]"""
import struct, sys
sys.path.insert(0, __import__('os').path.dirname(__file__))
from ucfb import read_chunks

def fnv(s):
    h = 0x811c9dc5
    for c in s.lower().encode('latin-1'): h = ((h ^ c) * 16777619) & 0xffffffff
    return h

def cstr(b): return b.split(b"\0")[0].decode("latin-1")

def walk_models(buf, start, end, out):
    for tag, s, e in read_chunks(buf, start, end):
        if tag == b"lvl_":
            walk_models(buf, s + 8, e, out)
        elif tag == b"ucfb":
            walk_models(buf, s, e, out)
        elif tag == b"modl":
            name = None; segs = []
            for t, a, z in read_chunks(buf, s, e):
                if t == b"NAME": name = cstr(buf[a:z])
                elif t == b"segm":
                    seg = {"mnam": None, "tex": []}
                    for t2, a2, z2 in read_chunks(buf, a, z):
                        if t2 == b"MNAM": seg["mnam"] = cstr(buf[a2:z2])
                        elif t2 == b"TNAM":
                            idx = struct.unpack_from("<I", buf, a2)[0]
                            seg["tex"].append((idx, cstr(buf[a2 + 4:z2])))
                    segs.append(seg)
            out.append((name, segs))

if __name__ == "__main__":
    buf = open(sys.argv[1], "rb").read()
    out = []
    walk_models(buf, 8, len(buf), out)
    flt = sys.argv[2] if len(sys.argv) > 2 else ""
    for name, segs in out:
        if flt in (name or ""):
            mats = sorted(set((s["mnam"], tuple(s["tex"])) for s in segs), key=str)
            print(name)
            for m, t in mats: print("   mat=%-28s fnv=%08x tex=%s" % (m, fnv(m) if m else 0, list(t)))
