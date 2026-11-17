"""Add the Remaster's per-weapon HUD mesh placements to the Xbox 1-player HUD (personal use).
The weapon icons (Model3D player1weapon1mesh / player1weapon2mesh) carry one override entry per weapon mesh
(hash 4b426ca0: Position/Rotation/Scale). The Xbox HUD only knows the stock weapons; the Remaster ships new
meshes (e.g. rep_weap_inf_dc17pistol = the commando pistol) whose icons then sit at the default placement,
far off. Copy every entry the Xbox list lacks from the Remaster HUD (same conventions, same group layout ~).
usage: hudmerge.py <xbox hud lvl> <remaster hud lvl> <out lvl>
"""
import os, struct, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ucfb import read_chunks
import hudtree as H

OVERRIDE = 0x4b426ca0
TARGETS = ("player1weapon1mesh", "player1weapon2mesh")
# entries whose Remaster placement lands far off in the Xbox layout: use the stock pistol's placement
FIX = {"rep_weap_inf_dc17pistol": {"Position": (-0.2316, 0.3591, 0.0073), "Scale": (1.0, 1.0, 1.0)}}


# weapon meshes with no entry in either HUD (they fall back to a far-off default): clone the faction pistol
CLONES = {
    "rep_weap_inf_smallpistol": ("rep_weap_inf_pistol", 1.3),   # Republic commando / award pistol
    "command_pistol": ("all_weap_inf_pistol", 1.0),              # Rebel commando / award pistol
    "all_weap_inf_han_pistol": ("all_weap_inf_pistol", 1.0),
    "all_weap_inf_defender": ("all_weap_inf_pistol", 1.0),
    "cis_weap_inf_pistol2": ("cis_weap_inf_pistol", 1.0),
    "gar_weap_inf_pistol": ("all_weap_inf_pistol", 1.0),
    # the icon entries are keyed by weapon CLASS name (stock weapons share it with their mesh)
    "rep_weap_inf_commando_pistol": ("rep_weap_inf_pistol", 1.3),
    "rep_weap_award_pistol": ("rep_weap_inf_pistol", 1.3),
    "all_weap_inf_commando_pistol": ("all_weap_inf_pistol", 1.0),
    "all_weap_award_pistol": ("all_weap_inf_pistol", 1.0),
    "cis_weap_inf_commando_pistol": ("cis_weap_inf_pistol", 1.0),
    "cis_weap_award_pistol": ("cis_weap_inf_pistol", 1.0),
    "imp_weap_inf_commando_pistol": ("imp_weap_inf_pistol", 1.0),
    "imp_weap_award_pistol": ("imp_weap_inf_pistol", 1.0),
    "all_weap_hero_hanpistol": ("all_weap_inf_pistol", 1.0),
    "all_weap_hero_targetpistol": ("all_weap_inf_pistol", 1.0),
    "gar_weap_inf_targetpistol": ("all_weap_inf_pistol", 1.0),
}


def label_data(name):
    n = name.encode() + b"\0"
    return struct.pack("<IBI", OVERRIDE, 1, 4) + struct.pack("<I", len(n)) + n


def scaled(sub, k):
    out = []
    for t, p in sub:
        if t == b"DATA" and struct.unpack_from("<I", p, 0)[0] == H.h20("Scale") and k != 1.0:
            d = bytearray(p)
            for i in range(3):
                struct.pack_into("<f", d, 5 + 4 * i, struct.unpack_from("<f", d, 5 + 4 * i)[0] * k)
            p = bytes(d)
        out.append([t, p])
    return out


def fix_entry(name, sub):
    for prop, vals in FIX.get(name, {}).items():
        for item in sub:
            if item[0] == b"DATA" and struct.unpack_from("<I", item[1], 0)[0] == H.h20(prop):
                d = bytearray(item[1])
                for i, v in enumerate(vals):
                    struct.pack_into("<f", d, 5 + 4 * i, v)
                item[1] = bytes(d)


def chunk(tag, data):
    return tag + struct.pack("<I", len(data)) + data + b"\0" * ((4 - len(data) % 4) % 4)


def tree(buf, a, z):
    """list of [tag, bytes] or [b'SCOP', subtree]"""
    out = []
    for t, x, y in read_chunks(buf, a, z):
        out.append([t, tree(buf, x, y) if t == b"SCOP" else buf[x:y]])
    return out


def ser(items):
    return b"".join(chunk(t, ser(p) if t == b"SCOP" else p) for t, p in items)


def label(data):
    if len(data) < 9:
        return None, None
    h, n = struct.unpack_from("<IB", data, 0)
    if n < 1:
        return h, None
    off = 5 + struct.unpack_from("<I", data, 5)[0]
    if off + 4 > len(data):
        return h, None
    ln = struct.unpack_from("<I", data, off)[0]
    if not (0 < ln < 200) or off + 4 + ln > len(data):
        return h, None
    return h, data[off + 4:off + 4 + ln - 1].decode("latin-1")


def find(items, name, path=()):
    """yield the SCOP subtree that belongs to the DATA element whose label is name"""
    for i, (t, p) in enumerate(items):
        if t == b"DATA" and label(p)[1] == name and i + 1 < len(items) and items[i + 1][0] == b"SCOP":
            yield items[i + 1][1]
        if t == b"SCOP":
            yield from find(p, name)


def overrides(scop):
    """[(mesh name, DATA bytes, SCOP subtree)] of the per-mesh entries in a weapon mesh element"""
    res = []
    for i, (t, p) in enumerate(scop):
        if t == b"DATA":
            h, nm = label(p)
            if h == OVERRIDE and nm and i + 1 < len(scop) and scop[i + 1][0] == b"SCOP":
                res.append((nm, p, scop[i + 1][1]))
    return res


def hud_items(path):
    buf = open(path, "rb").read()
    return buf, [[t, buf[a:z]] for t, a, z in read_chunks(buf, 8, len(buf))]


def is_1player(payload):
    return b"1playerhud" in payload[:80]


def main(xb_path, rem_path, out_path):
    xbuf, xitems = hud_items(xb_path)
    rbuf, ritems = hud_items(rem_path)
    rtree = tree([p for t, p in ritems if t == b"hud_" and is_1player(p)][0], 0,
                 len([p for t, p in ritems if t == b"hud_" and is_1player(p)][0]))
    out = b""
    for t, p in xitems:
        if t == b"hud_" and is_1player(p):
            xt = tree(p, 0, len(p))
            for target in TARGETS:
                xs = next(find(xt, target), None)
                rs = next(find(rtree, target), None)
                if xs is None or rs is None:
                    print("not found:", target)
                    continue
                have = {nm.lower() for nm, _, _ in overrides(xs)}
                added = []
                for nm, data, sub in overrides(rs):
                    if nm.lower() not in have:
                        fix_entry(nm, sub)
                        xs.append([b"DATA", data])
                        xs.append([b"SCOP", sub])
                        added.append(nm)
                if target == "player1weapon1mesh":
                    cur = {nm.lower(): sub for nm, _, sub in overrides(xs)}
                    for new, (src, k) in CLONES.items():
                        if new.lower() not in cur and src.lower() in cur:
                            xs.append([b"DATA", label_data(new)])
                            xs.append([b"SCOP", scaled(cur[src.lower()], k)])
                            added.append(new)
                print("%s: +%d %s" % (target, len(added), added[-8:]))
            p = ser(xt)
        out += chunk(t, p)
    open(out_path, "wb").write(b"ucfb" + struct.pack("<I", len(out)) + out)


if __name__ == "__main__":
    main(*sys.argv[1:4])
