"""Contact sheet of test screenshots (personal use): shots/<label>-<frame>.png side by side, downscaled.
usage: sheet.py <label> <frames, e.g. abc> <out.png> <scale>"""
import os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
from pngcrop import readpng, writepng

lab, frames, out, s = sys.argv[1], sys.argv[2], sys.argv[3], int(sys.argv[4])
ims = []
for n in frames:
    w, h, r = readpng(os.path.join(ROOT, "shots", "%s-%s.png" % (lab, n)))
    ims.append([bytes(b for i in range(0, w * 4, 4 * s) for b in row[i:i + 4]) for row in r[::s]])
H = min(len(i) for i in ims)
rows = [b"".join(im[y] for im in ims) for y in range(H)]
writepng(out, rows, len(rows[0]) // 4, H)
print(len(rows[0]) // 4, H)
