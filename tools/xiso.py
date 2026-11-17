"""Read one file out of an Xbox disc image (XDVDFS; plain xiso or a full redump image with the video partition)
without extracting the whole disc (personal use).
usage: xiso.py <image.iso> <path inside, e.g. Data/_LVL_XBOX/ingame.lvl> <out file>
"""
import struct, sys

SECTOR = 2048
MAGIC = b"MICROSOFT*XBOX*MEDIA"
OFFSETS = (0, 0x18300000, 0xFD90000, 0x89D80000, 0x2080000)  # xiso, redump/XGD1, XGD2, XGD3, misc


def find_base(f):
    for base in OFFSETS:
        f.seek(base + 32 * SECTOR)
        if f.read(20) == MAGIC:
            return base
    raise SystemExit("not an Xbox disc image (no XDVDFS volume found)")


def read_dir(f, base, sector, size):
    f.seek(base + sector * SECTOR)
    data = f.read(size)
    entries = {}

    def walk(off):
        if off + 14 > len(data) or data[off:off + 2] == b"\xff\xff":
            return
        left, right, start, fsize, attr, nlen = struct.unpack_from("<HHIIBB", data, off)
        name = data[off + 14:off + 14 + nlen].decode("latin-1")
        entries[name.lower()] = (start, fsize, bool(attr & 0x10))
        if left:
            walk(left * 4)
        if right:
            walk(right * 4)
    walk(0)
    return entries


def extract(image, path, out):
    with open(image, "rb") as f:
        base = find_base(f)
        f.seek(base + 32 * SECTOR + 20)
        root, rsize = struct.unpack("<II", f.read(8))
        sector, size, is_dir = root, rsize, True
        for part in path.replace("\\", "/").strip("/").split("/"):
            if not is_dir:
                raise SystemExit("%s: not a folder" % part)
            e = read_dir(f, base, sector, size).get(part.lower())
            if not e:
                raise SystemExit("not on the disc: " + path)
            sector, size, is_dir = e
        f.seek(base + sector * SECTOR)
        with open(out, "wb") as o:
            left = size
            while left:
                b = f.read(min(left, 8 << 20))
                o.write(b)
                left -= len(b)
    return size


if __name__ == "__main__":
    print(extract(*sys.argv[1:4]), "bytes")
