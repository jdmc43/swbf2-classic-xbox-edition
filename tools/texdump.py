"""Decode DXT1/DXT3 tex_ chunks (largest mip) into one PNG grid (personal use).
usage: texdump.py <lvl> <name-prefix> <out.png>"""
import struct, sys, os, zlib
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ucfb import read_chunks

def c565(c):
    return ((c >> 11) & 31) * 255 // 31, ((c >> 5) & 63) * 255 // 63, (c & 31) * 255 // 31

def dxt(data, w, h, fmt):
    px = [[(0, 0, 0, 0)] * w for _ in range(h)]
    bs = 16 if fmt == b"DXT3" else 8
    o = 0
    for by in range(0, h, 4):
        for bx in range(0, w, 4):
            blk = data[o:o + bs]; o += bs
            if len(blk) < bs: return px
            alpha = None
            if bs == 16:
                alpha = struct.unpack_from("<Q", blk, 0)[0]; blk = blk[8:]
            c0, c1, bits = struct.unpack_from("<HHI", blk, 0)
            p0, p1 = c565(c0), c565(c1)
            if c0 > c1 or bs == 16:
                pal = [p0, p1, tuple((2 * a + b) // 3 for a, b in zip(p0, p1)), tuple((a + 2 * b) // 3 for a, b in zip(p0, p1))]
            else:
                pal = [p0, p1, tuple((a + b) // 2 for a, b in zip(p0, p1)), (0, 0, 0)]
            for i in range(16):
                x, y = bx + i % 4, by + i // 4
                if x < w and y < h:
                    a = ((alpha >> (4 * i)) & 15) * 17 if alpha is not None else 255
                    px[y][x] = pal[(bits >> (2 * i)) & 3] + (a,)
    return px

def textures(path, prefix):
    buf = open(path, "rb").read()
    for t, a, z in read_chunks(buf, 8, len(buf)):
        if t != b"tex_": continue
        kids = read_chunks(buf, a, z)
        name = [buf[x:y].split(b"\0")[0].decode() for tt, x, y in kids if tt == b"NAME"][0]
        if not name.startswith(prefix): continue
        for tt, x, y in kids:
            if tt != b"FMT_": continue
            best = None
            def walk(s, e):
                nonlocal best
                for t2, x2, y2 in read_chunks(buf, s, e):
                    if t2 in (b"FACE", b"LVL_"): walk(x2, y2)
                    elif t2 == b"INFO" and y2 - x2 >= 8 and best is None:
                        pass
                    elif t2 == b"BODY":
                        best = best or (x2, y2)
            info = [buf[x2:y2] for t2, x2, y2 in read_chunks(buf, x, y) if t2 == b"INFO"][0]
            fmt = info[0:4]
            w, h = struct.unpack_from("<HH", info, 4)
            walk(x, y)
            if fmt in (b"DXT1", b"DXT3") and best:
                yield name, dxt(buf[best[0]:best[1]], w, h, fmt)
                break

def png(path, rows, w, h):
    raw = b"".join(b"\0" + bytes(c for p in r for c in p) for r in rows)
    def ch(t, d): return struct.pack(">I", len(d)) + t + d + struct.pack(">I", zlib.crc32(t + d) & 0xffffffff)
    open(path, "wb").write(b"\x89PNG\r\n\x1a\n" + ch(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 6, 0, 0, 0)) + ch(b"IDAT", zlib.compress(raw)) + ch(b"IEND", b""))

if __name__ == "__main__":
    items = list(textures(sys.argv[1], sys.argv[2]))
    S = 64; cols = 8
    W = cols * (S + 8); H = ((len(items) + cols - 1) // cols) * (S + 8)
    canvas = [[(60, 60, 60, 255)] * W for _ in range(H)]
    for i, (name, px) in enumerate(items):
        ox, oy = (i % cols) * (S + 8), (i // cols) * (S + 8)
        h, w = len(px), len(px[0])
        for y in range(S):
            for x in range(S):
                r, g, b, a = px[y * h // S][x * w // S]
                bg = canvas[oy + y][ox + x]
                canvas[oy + y][ox + x] = tuple((c * a + d * (255 - a)) // 255 for c, d in zip((r, g, b), bg[:3])) + (255,)
        print(i, name, w, h)
    png(sys.argv[3], canvas, W, H)
