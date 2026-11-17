"""Hero Accept/Decline on the keyboard arrows (personal use): in a .profile's PC key bindings
  Accept  [PgUp, F1]  -> [Left, F1]       Decline [PgDn, F2] -> [Right, F2]
  strafe  [A, Left]   -> [A, -]           strafe  [D, Right] -> [D, -]
so Left/Right answer the hero prompt like the controller d-pad (Steam sends F1/F2 for it, unchanged) and no
longer strafe (A/D still do). Up/Down arrows are untouched.
Profile: u32 checksum = CRC-32/BZIP2 (poly 04C11DB7, init FFFFFFFF, not reflected, xorout FFFFFFFF) of the rest.
Key binding tables (5 copies, one per input mode): per control 3 u16 slots - two keyboard slots (low byte =
DirectInput key, high byte = mouse code) and a third that is NOT read as a keyboard key (tested: Left there
only strafed).
The original is copied to ~/Documents/SWBF2-backups/<name>.before-profkeys once; revert copies it back.
usage: profkeys.py status|apply|revert <profile>
"""
import os, shutil, struct, sys

PGUP, F1, PGDN, F2, LEFT, RIGHT, KEY_A, KEY_D = 0xC9, 0x3B, 0xD1, 0x3C, 0xCB, 0xCD, 0x1E, 0x20
BACKUP = os.path.join(os.path.expanduser("~"), "Documents", "SWBF2-backups")


def crc_bzip2(d):
    crc = 0xFFFFFFFF
    for x in d[:0x1100]:  # only the profile data (larger profiles append a gamepad section)
        crc ^= x << 24
        for _ in range(8):
            crc = ((crc << 1) ^ 0x04C11DB7) & 0xFFFFFFFF if crc & 0x80000000 else (crc << 1) & 0xFFFFFFFF
    return crc ^ 0xFFFFFFFF


def find(b, *slots):
    pat = struct.pack("<" + "H" * len(slots), *slots)
    out, i = [], b.find(pat)
    while i >= 0:
        out.append(i)
        i = b.find(pat, i + 1)
    return out


# (old slots, new slots) per entry
CHANGES = [
    ((PGUP, F1, 0), (LEFT, F1, 0)),
    ((PGDN, F2, 0), (RIGHT, F2, 0)),
    ((KEY_A, LEFT, 0), (KEY_A, 0, 0)),
    ((KEY_D, RIGHT, 0), (KEY_D, 0, 0)),
]


def main(cmd, path):
    b = bytearray(open(path, "rb").read())
    ok = struct.unpack_from("<I", b, 0)[0] == crc_bzip2(b[4:])
    print("checksum", "ok" if ok else "BAD")
    for old, new in CHANGES:
        print("  %-26s original x%d   changed x%d" % (old, len(find(b, *old)), len(find(b, *new))))
    if cmd == "status":
        return
    bk = os.path.join(BACKUP, os.path.basename(path) + ".before-profkeys")
    if cmd == "revert":
        shutil.copy2(bk, path)
        print("restored", bk)
        return
    if not ok:
        sys.exit("checksum mismatch - not touching it")
    n = 0
    for old, new in CHANGES:
        for o in find(b, *old):
            struct.pack_into("<HHH", b, o, *new)
            n += 1
    if not n:
        print("nothing to do")
        return
    if not os.path.exists(bk):
        shutil.copy2(path, bk)
        print("backup:", bk)
    struct.pack_into("<I", b, 0, crc_bzip2(b[4:]))
    open(path, "wb").write(b)
    print("apply: %d entries" % n)


if __name__ == "__main__":
    main(*sys.argv[1:3])
