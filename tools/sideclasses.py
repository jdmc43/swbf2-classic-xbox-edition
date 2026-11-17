"""Read class definitions (entc/wpnc) out of installed side .lvl files.
usage: sideclasses.py <side.lvl> [<side.lvl> ...]   -> prints JSON {class: {parent, props{name: [values]}}}
Property names are FNV-1a hashes in munged files; known names are resolved.
"""
import json, struct, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ucfb

KNOWN = ["GeometryName", "WeaponName", "AnimationName", "SkeletonName", "ClassLabel", "ClassParent",
         "GeometryLowRes", "FirstPerson", "HUDTag", "OrdnanceName", "SkeletonLowRes", "IconTexture",
         "WeaponAmmo", "AISizeType", "MapTexture", "GeometryAddon", "AttachToHardPoint", "FirstPersonFOV",
         "ComboAnimationBank", "PointsToUnlock", "OverrideTexture", "OverrideTexture2", "AnimatedAddon", "HealthTexture", "JetJump", "SoldierAnimation", "AnimationAddon"]


def fnv(s):
    h = 0x811C9DC5
    for c in s.lower().encode():
        h ^= c
        h = (h * 0x01000193) & 0xFFFFFFFF
    return h


NAMES = {fnv(n): n for n in KNOWN}


def walk(buf, start, end, out):
    for tag, s, e in ucfb.read_chunks(buf, start, end):
        if tag == b"lvl_":
            size = struct.unpack_from("<I", buf, s + 4)[0]
            walk(buf, s + 8, min(e, s + 8 + size), out)
        elif tag in (b"entc", b"wpnc", b"ordc"):
            cls = {"kind": tag.decode(), "parent": None, "props": {}}
            name = None
            for t, a, b in ucfb.read_chunks(buf, s, e):
                d = buf[a:b]
                if t == b"BASE":
                    cls["parent"] = d.split(b"\0")[0].decode("latin-1")
                elif t == b"TYPE":
                    name = d.split(b"\0")[0].decode("latin-1")
                elif t == b"PROP":
                    h = struct.unpack_from("<I", d)[0]
                    v = d[4:].split(b"\0")[0].decode("latin-1")
                    cls["props"].setdefault(NAMES.get(h, "0x%08x" % h), []).append(v)
            if name:
                out[name] = cls


out = {}
for p in sys.argv[1:]:
    buf = open(p, "rb").read()
    size = struct.unpack_from("<I", buf, 4)[0]
    walk(buf, 8, 8 + size, out)
json.dump(out, sys.stdout, indent=1)
