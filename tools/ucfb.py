"""Minimal UCFB (.lvl) reader/writer for SWBF2 (2005).

Layout: 'ucfb' <u32 size> then child chunks: <4cc> <u32 size> <data> padded to 4 bytes.
Top-level items (scr_, tex_, Locl, lvl_, ...) usually contain a NAME sub-chunk.
"""
import hashlib
import struct
import sys

NAMED = {b"scr_", b"tex_", b"skel", b"modl", b"Locl", b"lvl_", b"entc", b"ordc", b"wpnc",
         b"expc", b"font", b"zaa_", b"zaf_", b"plan", b"PATH", b"cnfg", b"sanm", b"hud_", b"fx__"}


def read_chunks(buf, off=0, end=None):
    end = len(buf) if end is None else end
    out = []
    while off + 8 <= end:
        tag = buf[off:off + 4]
        size = struct.unpack_from("<I", buf, off + 4)[0]
        data_start = off + 8
        data_end = data_start + size
        if data_end > end:
            break
        out.append((tag, data_start, data_end))
        off = data_end + ((4 - size % 4) % 4)
    return out


def item_name(buf, tag, start, end):
    # lvl_ items: u32 name hash then u32 size then ucfb body
    if tag == b"lvl_":
        return "hash:%08x" % struct.unpack_from("<I", buf, start)[0]
    kids = read_chunks(buf, start, end)
    if tag in (b"entc", b"ordc", b"wpnc", b"expc"):
        for t, s, e in kids:
            if t == b"TYPE":
                return buf[s:e].split(b"\0")[0].decode("latin-1")
    for t, s, e in kids:
        if t == b"NAME":
            raw = buf[s:e]
            if e - s == 4:  # config chunks store a 32-bit name hash
                return "hash:%08x" % struct.unpack_from("<I", raw)[0]
            return raw.split(b"\0")[0].decode("latin-1")
    return "?"


def load(path):
    buf = open(path, "rb").read()
    assert buf[:4] == b"ucfb", path
    size = struct.unpack_from("<I", buf, 4)[0]
    items = []
    for tag, s, e in read_chunks(buf, 8, 8 + size):
        name = item_name(buf, tag, s, e)
        items.append({"tag": tag.decode("latin-1"), "name": name, "start": s - 8, "end": e,
                      "md5": hashlib.md5(buf[s - 8:e]).hexdigest()[:10], "size": e - s})
    return buf, items


def key(it, seen):
    k = (it["tag"], it["name"])
    n = seen.get(k, 0)
    seen[k] = n + 1
    return k + (n,)


def index(items):
    seen = {}
    return {key(it, seen): it for it in items}


if __name__ == "__main__":
    labels = sys.argv[1::2]
    paths = sys.argv[2::2]
    idx = [index(load(p)[1]) for p in paths]
    allkeys = []
    for d in idx:
        for k in d:
            if k not in allkeys:
                allkeys.append(k)
    base = idx[0]
    for k in allkeys:
        row = []
        for lab, d in zip(labels, idx):
            if k not in d:
                row.append(f"{lab}:-")
            elif k in base and d[k]["md5"] == base[k]["md5"]:
                row.append(f"{lab}:=")
            else:
                row.append(f"{lab}:{d[k]['md5'][:6]}")
        if any(not r.endswith(":=") for r in row[1:]) or k not in base:
            print(f"{k[0]:5} {k[1][:40]:40} #{k[2]}  " + "  ".join(row))
