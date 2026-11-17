"""Parse munged SWBF2 HUD (hud_ chunk) config trees (personal use).
DATA = u32 property hash, u8 n, n x u32 values (float, or offset to a string from the value), strings:
u32 len + chars. SCOP = children of the previous DATA (element)."""
import struct, sys
sys.path.insert(0, __import__("os").path.dirname(__file__))
from ucfb import read_chunks

def h20(s):
    h = 0x811c9dc5
    for c in s.encode("latin-1"):
        h = ((h ^ (c | 0x20)) * 16777619) & 0xffffffff
    return h

PROPS = ["Position", "PositionSmall", "PositionLarge", "PositionSpawn", "Scale", "ScaleSmall", "ScaleLarge", "ScaleSpawn",
         "Group", "Text", "Bitmap", "Model3D", "Map", "Mesh", "BitmapRect", "Color", "Alpha", "ZOrder", "EventEnable",
         "EventDisable", "EventText", "TextStyle", "Font", "TextBreak", "Justification", "Viewport", "Rotation",
         "BackdropSmall", "BackdropSpawn", "BackdropLarge", "Mask", "TexCoords", "FileInfo", "ViewPort", "Viewports",
         "PropagateAlpha", "Size", "ColorFlash", "EventFlash", "Value", "Bar", "EventValue", "Animation", "Rect",
         "Model", "Offset", "Scale3D", "Height", "Width", "CustomColor", "EventPlay", "EventColor", "MeshList",
         "Transform", "EventTransform", "TextColor", "ProgressBar", "ColorEnable", "EventValueFraction", "Fraction"]
NAMES = {h20(p): p for p in PROPS}

class Node:
    def __init__(s, buf, a, z):
        s.buf, s.a, s.z = buf, a, z
        s.hash, = struct.unpack_from("<I", buf, a)
        n = buf[a + 4]
        s.n = n
        s.vals = []
        base = a + 5
        for i in range(n):
            off = base + i * 4
            raw, = struct.unpack_from("<I", buf, off)
            f, = struct.unpack_from("<f", buf, off)
            st = None
            p = off + raw
            if 0 < raw < (z - off) and p + 4 <= z:
                ln, = struct.unpack_from("<I", buf, p)
                if 0 < ln < 200 and p + 4 + ln <= z and buf[p + 4 + ln - 1] == 0:
                    st = buf[p + 4:p + 4 + ln - 1].decode("latin-1")
            s.vals.append((off, f, st))
        s.kids = []
    @property
    def name(s): return NAMES.get(s.hash, "%08x" % s.hash)
    def show(s):
        out = []
        for off, f, st in s.vals:
            out.append(repr(st) if st is not None else ("%.4f" % f))
        return "%s(%s)" % (s.name, ", ".join(out))

def parse(buf, a, z):
    nodes, last = [], None
    for t, x, y in read_chunks(buf, a, z):
        if t == b"DATA":
            last = Node(buf, x, y); nodes.append(last)
        elif t == b"SCOP" and last is not None:
            last.kids = parse(buf, x, y)
    return nodes

def huds(buf):
    for t, a, z in read_chunks(buf, 8, len(buf)):
        if t == b"hud_":
            kids = read_chunks(buf, a, z)
            yield a, z, parse(buf, a, z)

def dump(nodes, depth=0, flt=None, out=None):
    for n in nodes:
        print("  " * depth + n.show())
        dump(n.kids, depth + 1)

if __name__ == "__main__":
    buf = open(sys.argv[1], "rb").read()
    want = sys.argv[2] if len(sys.argv) > 2 else "1playerhud"
    for a, z, nodes in huds(buf):
        top = [n for n in nodes if n.vals and n.vals[0][2] == want]
        if top or any(want in (v[2] or "") for n in nodes for v in n.vals):
            dump(nodes)
            break
