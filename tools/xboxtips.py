"""Controller tips (personal use): the PC localization hard-codes key names in hints ("Jetpack: [SPACE] twice
to activate"). The engine draws inline texture tags ("{btna}") like the Xbox version does, so replace every
known key name with the controller button that sends that key in the user's Steam Input layout ("Original Xbox
Controls"), drawn with the console button textures in common.lvl (Xbox One style icons).
Locl BODY entry: u32 hash, u16 size (bytes incl. this 6-byte header), UTF-16 string + NUL, padded to 4.
usage: xboxtips.py <pc core.lvl> <out core.lvl>
"""
import os, re, struct, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ucfb import read_chunks

# key -> texture of the controller button sending it (A/B = btna/btnb, X/Y = btnmisc/btnmisc2, LB/RB = btnl1/btnr1,
# LT/RT = btnl2/btnr2, sticks btn_analog_l/r, clicks *_down, View = btn_select, d-pad btn_directional_pad_*)
KEYMAP = {
    "SPACE": "btna", "SPACEBAR": "btna", "ENTER": "btna",
    "ALT": "btnb", "C": "btnb",
    "Q": "btnmisc", "E": "btnmisc2",
    "MOUSE BUTTON 1": "btnr2", "MOUSE BUTTON 2": "btnl2",
    "1": "btnr1",
    # the engine has 7 inline icon slots (exepatch icons_table: B X Y RT LT A RB) - the rest as text
    "2": "[LB]",
    "W": "[LEFT STICK]", "A": "[LEFT STICK]", "S": "[LEFT STICK]", "D": "[LEFT STICK]",
    "SHIFT": "[L3]", "Z": "[R3]", "M": "[BACK]",
    "F1": "[D-PAD LEFT]", "F2": "[D-PAD RIGHT]",
}
KEYTOKEN = re.compile(r"\[([A-Za-z0-9 ]+)\]")
WHEEL = re.compile(r"\[MOUSE WHEEL UP\] or \[MOUSE WHEEL DOWN\]", re.I)
LANGS = ("english", "uk_english")  # other languages translate the key names


def chunk(tag, data):
    return tag + struct.pack("<I", len(data)) + data + b"\0" * ((4 - len(data) % 4) % 4)


def parse_body(b):
    out, o = [], 0
    while o + 6 <= len(b):
        h, size = struct.unpack_from("<IH", b, o)
        if size < 6 or o + size > len(b):
            break
        s = b[o + 6:o + size].decode("utf-16-le", "replace").split("\0")[0]
        out.append((h, s))
        o += size
    return out


def build_body(entries):
    out = b""
    for h, s in entries:
        data = s.encode("utf-16-le") + b"\0\0"
        size = 6 + len(data)
        size += (4 - size % 4) % 4
        out += struct.pack("<IH", h, size) + data + b"\0" * (size - 6 - len(data))
    return out


def locls(buf):
    res = {}
    for t, a, z in read_chunks(buf, 8, len(buf)):
        if t == b"Locl":
            kids = read_chunks(buf, a, z)
            name = [buf[x:y].split(b"\0")[0].decode() for tt, x, y in kids if tt == b"NAME"][0]
            body = [buf[x:y] for tt, x, y in kids if tt == b"BODY"][0]
            res[name] = parse_body(body)
    return res


def controllerize(s):
    s = WHEEL.sub("{btnr1}", s)

    def rep(m):
        t = m.group(1).upper()
        if t not in KEYMAP:
            return m.group(0)
        v = KEYMAP[t]
        return "{%s}" % v if v.startswith("btn") else v
    return KEYTOKEN.sub(rep, s)


# whole strings replaced with the console text (same key)
OVERRIDE = {
    # hero offer: PC "You can now play as %s / Press 'Accept' (default [D-PAD LEFT]) or 'Decline' (...)" - the
    # Xbox HUD's prompt draws the d-pad with Yes/No under it itself
    0xADD5467C: "Play as %s?",
}


def main(pc_path, out_path):
    pc = open(pc_path, "rb").read()
    out = b""
    for t, a, z in read_chunks(pc, 8, len(pc)):
        if t != b"Locl":
            out += pc[a - 8:z] + b"\0" * ((4 - (z - a) % 4) % 4)
            continue
        kids = read_chunks(pc, a, z)
        name = [pc[x:y].split(b"\0")[0].decode() for tt, x, y in kids if tt == b"NAME"][0]
        entries = parse_body([pc[x:y] for tt, x, y in kids if tt == b"BODY"][0])
        n = 0
        if name in LANGS:
            for i, (h, s) in enumerate(entries):
                ns = OVERRIDE.get(h, controllerize(s))
                if ns != s:
                    entries[i] = (h, ns)
                    n += 1
                    if name == "english" and n <= 8:
                        print("  %r\n    -> %r" % (s[:80], ns[:80]))
        print("%-10s tips converted: %d" % (name, n))
        body = b""
        for tt, x, y in kids:
            body += chunk(tt, build_body(entries) if tt == b"BODY" else pc[x:y])
        out += chunk(b"Locl", body)
    open(out_path, "wb").write(b"ucfb" + struct.pack("<I", len(out)) + out)


if __name__ == "__main__":
    main(*sys.argv[1:3])
