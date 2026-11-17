"""Xbox fonts (personal use). The controller patch's fonts are the genuine Xbox fonts (glyph tables are
byte-identical to the Xbox disc) already converted to PC texture format.
usage: xboxfonts.py <remaster_lvl_dir> <out_dir>
out/core.lvl             Remaster core with gamefont_large/medium/small (+tiny, super_tiny) = Xbox fonts
out/remafonts.lvl        the same fonts renamed gamefont_*_rema (+tiny, super_tiny), to replace
                         addon/Remaster/Fonts/arialblack_{default,2k,4k}.lvl
"""
import os, struct, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import munge, ucfb
from merge import Lvl, raw_items, write_lvl

rem, out = sys.argv[1:3]
os.makedirs(out, exist_ok=True)
ctrl = dict(raw_items(os.path.join(os.environ.get("SWBF2_CTRL") or "ctrl/GameData", "data", "_lvl_pc", "core.lvl"))[1])
FONTS = ["gamefont_large", "gamefont_medium", "gamefont_small", "gamefont_tiny", "gamefont_super_tiny"]


def rename_font(raw, old, new):
    """Rename a font chunk and its textures (NAME chunks at every level)."""
    def walk(buf, s, e):
        res = b""
        for t, a, b in ucfb.read_chunks(buf, s, e):
            d = buf[a:b]
            if t == b"NAME":
                n = d.split(b"\0")[0].decode("latin-1")
                if n.startswith(old):
                    n = new + n[len(old):]
                d = n.encode("latin-1") + b"\0"
            elif t in (b"FTEX", b"tex_"):
                d = walk(buf, a, b)
            res += munge.chunk(t, d)
        return res
    body = walk(raw, 8, len(raw))
    return raw[:4] + struct.pack("<I", len(body)) + body


core = Lvl(os.path.join(rem, "core.lvl"))
# only the fonts the Remaster's core.lvl already has; tiny/super_tiny come from the Remaster font file
# (defining a font twice leaves its text invisible)
for f in [f for f in FONTS if core.find(("font", f, 0)) is not None]:
    k = ("font", f, 0)
    if core.find(k) is not None:
        core.replace(k, ctrl[k], "Xbox font")
    else:
        core.insert_after(None, k, ctrl[k], "Xbox font")
open(os.path.join(out, "core.lvl"), "wb").write(write_lvl(core.items))

items = []
for f in FONTS:
    new = f + "_rema" if f in ("gamefont_large", "gamefont_medium", "gamefont_small") else f
    raw = ctrl[("font", f, 0)]
    if new != f:
        raw = rename_font(raw, f, new)
    items.append([("font", new, 0), raw])
open(os.path.join(out, "remafonts.lvl"), "wb").write(write_lvl(items))
print("built core.lvl + remafonts.lvl:", [i[0][1] for i in items])
