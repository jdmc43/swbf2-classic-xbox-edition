"""Patcher for BattlefrontII.exe (personal use). Verifies original bytes, keeps a backup of the
unmodified exe, and can apply/revert named patches.
usage: exepatch.py status | apply <name>... | revert <name>... | restore
"""
import hashlib, os, shutil, struct, sys

EXE = r"C:\Program Files (x86)\Steam\steamapps\common\Star Wars Battlefront II Classic\GameData\BattlefrontII.exe"
BACKUP = os.path.expanduser(r"~\Documents\SWBF2-backups\BattlefrontII.exe.orig")
ORIG_MD5 = "bd9f9ca3b311877308e8c26e155ab7e6"
BASE, TEXT_VA, TEXT_RAW = 0x400000, 0x1000, 0x400

# name: (VA, original bytes, patched bytes, description)
PATCHES = {
    "spawnmodel_cam": (0x42A806, bytes.fromhex("FF5054"), bytes.fromhex("909090"),
                       "skip spawn-display unit model camera/transform call"),
    "spawnmodel_upd": (0x42ABC7, bytes.fromhex("FF5048"), bytes.fromhex("83C404"),
                       "skip spawn-display unit model update (keeps the stack balanced)"),
    "spawnmodel_alpha1": (0x42AB80, bytes.fromhex("A047E17D00"), bytes.fromhex("B001909090"),
                          "spawn-display unit model colour: alpha 1 (branch 1)"),
    "spawnmodel_alpha2": (0x42AB99, bytes.fromhex("A057E17D00"), bytes.fromhex("B001909090"),
                          "spawn-display unit model colour: alpha 1 (branch 2)"),
    # the class picker's 3D ring replaces the engine's spawn unit: clear its visible flag (bit 8 of
    # [obj+0x14], what IFObj SetVisible writes) every frame. ecx = [edi+0x62c] here; replaces the
    # alpha byte load (alpha is irrelevant once hidden).
    # the class picker's 3D ring replaces the engine's spawn unit: every place that shows/enables the
    # unit model ([x+0x62c] vtbl+4 / vtbl+8 with 1) passes 0 instead
    "spawnmodel_novis1": (0x42BAC7, bytes.fromhex("6A01"), bytes.fromhex("6A00"),
                          "spawn-display unit model never shown: state change, show"),
    "spawnmodel_novis2": (0x42BAD4, bytes.fromhex("6A01"), bytes.fromhex("6A00"),
                          "spawn-display unit model never shown: state change, enable"),
    "spawnmodel_novis3": (0x42BEA6, bytes.fromhex("6A01"), bytes.fromhex("6A00"),
                          "spawn-display unit model never shown: state change 2, show"),
    "spawnmodel_novis4": (0x42BEB3, bytes.fromhex("6A01"), bytes.fromhex("6A00"),
                          "spawn-display unit model never shown: state change 2, enable"),
    "spawnmodel_novis5": (0x42C63F, bytes.fromhex("6A01"), bytes.fromhex("6A00"),
                          "spawn-display unit model never shown: class setup, show"),
    "spawnmodel_novis6": (0x42C64C, bytes.fromhex("6A01"), bytes.fromhex("6A00"),
                          "spawn-display unit model never shown: class setup, enable"),
    "spawnmodel_novis7": (0x42CB5D, bytes.fromhex("6A01"), bytes.fromhex("6A00"),
                          "spawn-display unit model never shown: model create, show"),
    "spawnmodel_novis8": (0x42CB6A, bytes.fromhex("6A01"), bytes.fromhex("6A00"),
                          "spawn-display unit model never shown: model create, enable"),
    "spawnmodel_hide1": (0x42AB80, bytes.fromhex("A047E17D00"), bytes.fromhex("806115FA90"),
                         "hide spawn-display unit model every frame, visible+enabled bits (branch 1)"),
    "spawnmodel_hide2": (0x42AB99, bytes.fromhex("A057E17D00"), bytes.fromhex("806115FA90"),
                         "hide spawn-display unit model every frame, visible+enabled bits (branch 2)"),
}

# HUD event hook: GetTimerRate(n) (unused by all scripts) -> fire player 1 HUD event n (see hudevent_cave.py)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hudevent_cave
_cave = hudevent_cave.build(int(os.environ.get("HUDEV_DEBUG") or 0))
PATCHES["hudevent_code"] = (hudevent_cave.CAVE, bytes(len(_cave)), _cave,
                            "HUD event function code in the .text slack")
PATCHES["hudevent_vsize"] = (0x258, bytes.fromhex("0B953600"), bytes.fromhex("00963600"),
                             ".text VirtualSize covers the slack (raw size)")
# registry pointer keeps its relocation entry: the loader must still rebase the new pointer
# GetTimerRate: unused by every script, in the mission function table (registered in the in-game Lua state)
PATCHES["hudevent_reg"] = (0x3E597C, struct.pack("<I", 0x58E230), struct.pack("<I", hudevent_cave.CAVE),
                           "GetTimerRate -> HUD event function", True)


# Default PC key bindings for NEW profiles (static initializer 0x4014d0 fills 5 tables, one per input mode, at
# 0x1f9a928 + mode*0x102, 3 u16 slots per control): Accept [PgUp, F1] -> [Left, F1], Decline [PgDn, F2] ->
# [Right, F2], strafe [A, Left] / [D, Right] lose the arrow, so the arrows answer the hero prompt like the
# controller d-pad (Steam sends F1/F2). Each patch is one immediate byte of a mov (never the address field).
# Existing profiles: tools/profkeys.py.
_KEYS = [
    (0x401588, 0xC9, 0xCB, "table0 Accept slot1 -> Left"),
    (0x40159A, 0xD1, 0xCD, "table0 Decline slot1 -> Right"),
    (0x4016F3, 0xCD, 0x00, "table0 strafe D: drop Right"),
    (0x4016FF, 0xCB, 0x00, "table0 strafe A: drop Left"),
    (0x4017F3, 0xC9, 0xCB, "table1 Accept slot1 -> Left"),
    (0x401805, 0xD1, 0xCD, "table1 Decline slot1 -> Right"),
    (0x401959, 0xCD, 0x00, "table1 strafe D: drop Right"),
    (0x401965, 0xCB, 0x00, "table1 strafe A: drop Left"),
    (0x401A5A, 0xC9, 0xCB, "table2 Accept slot1 -> Left"),
    (0x401A6C, 0xD1, 0xCD, "table2 Decline slot1 -> Right"),
    (0x401BC5, 0xCD, 0x00, "table2 strafe D: drop Right"),
    (0x401BD1, 0xCB, 0x00, "table2 strafe A: drop Left"),
    (0x401CC0, 0xC9, 0xCB, "table3 Accept slot1 -> Left"),
    (0x401CCC, 0xD1, 0xCD, "table3 Decline slot1 -> Right"),
    (0x401E14, 0xCD, 0x00, "table3 strafe D: drop Right"),
    (0x401E20, 0xCB, 0x00, "table3 strafe A: drop Left"),
    (0x401EE7, 0xC9, 0xCB, "table4 Accept slot1 -> Left"),
    (0x401EF9, 0xD1, 0xCD, "table4 Decline slot1 -> Right"),
    (0x40206F, 0xCD, 0x00, "table4 strafe D: drop Right"),
    (0x40207B, 0xCB, 0x00, "table4 strafe A: drop Left"),
]
for _i, (_va, _o, _n, _d) in enumerate(_KEYS):
    PATCHES["keys_%02d" % _i] = (_va, bytes([_o]), bytes([_n]), "default keys: " + _d)


# Inline text icons: the engine builds its {tag} icons from a 7-entry table at 0x7ec140 ({u16 char, u32 texture
# hash}; 0x529e0d count, read at 0x529e73 / 0x529e89): only {btna} draws. Move the table to the .rdata slack with
# all console button textures added, so tips can show B/X/Y/LB/RB/LT/RT/sticks/d-pad like {btna}.
def _h20(s):
    h = 0x811c9dc5
    for ch in s.encode():
        h = ((h ^ (ch | 0x20)) * 16777619) & 0xffffffff
    return h


ICON_TABLE_VA = 0x7DD6B0  # .rdata raw slack (VirtualSize raised to the raw size below)
_ICON_OLD = [(0x7FFF, 0x7F0688E4), (0x8100, 0x592F1C52), (0x8101, 0x7F0688E4), (0x8200, 0x00288768),
             (0x8201, 0xEE286B12), (0xC300, _h20("btna")), (0xC400, _h20("btna"))]
_ICON_NEW = ["btnb", "btnmisc", "btnmisc2", "btnr1", "btnr2", "btnl1", "btnl2", "btn_analog_l",
             "btn_analog_l_down", "btn_analog_r", "btn_analog_r_down", "btn_select", "btn_start",
             "btn_directional_pad", "btn_directional_pad_u", "btn_directional_pad_d", "btn_directional_pad_l",
             "btn_directional_pad_r"]
# the engine only handles its 7 icon slots (more entries break the glyph pages, even {btna}): keep the 7
# characters, but point the PC mouse/keyboard icon slots at console button textures
_ICON_SLOTS = ["btnb", "btnmisc", "btnmisc2", "btnr2", "btnl2", "btna", "btnr1"]
_ICONS = [(c, _h20(n)) for (c, _), n in zip(_ICON_OLD, _ICON_SLOTS)]
if os.environ.get("ICON_PROBE"):  # experiment: which input-code glyph each char draws ({j1}..{j15}, {k1}..{k5})
    _ICONS = _ICON_OLD + [(0xC300 + i, _h20("j%d" % i)) for i in range(1, 16)] + [(0xC400 + i, _h20("k%d" % i)) for i in range(1, 6)]
    _ICONS += [(0xC500, _h20("q0"))]
_ICON_BYTES = b"".join(struct.pack("<HHI", c, 0, h) for c, h in _ICONS)
_ICON_FILE = 0x369A00 + (ICON_TABLE_VA - 0x400000 - 0x36B000)
PATCHES["icons_rdata_vsize"] = (0x280, bytes.fromhex("A8260700"), bytes.fromhex("00280700"),
                                ".rdata VirtualSize covers its raw slack (icon table)")
PATCHES["icons_table"] = (_ICON_FILE, bytes(len(_ICON_BYTES)), _ICON_BYTES,
                          "text icon table: 7 slots -> B X Y RT LT A RB")
PATCHES["icons_count"] = (0x529E0D, bytes.fromhex("C7460407000000"),
                          bytes.fromhex("C74604") + struct.pack("<I", len(_ICONS)), "text icon count", True)
PATCHES["icons_addr1"] = (0x529E73, bytes.fromhex("668B04DD40C17E00"),
                          bytes.fromhex("668B04DD") + struct.pack("<I", ICON_TABLE_VA), "text icon table (chars)", True)
PATCHES["icons_addr2"] = (0x529E89, bytes.fromhex("8B04DD44C17E00"),
                          bytes.fromhex("8B04DD") + struct.pack("<I", ICON_TABLE_VA + 4), "text icon table (hashes)", True)


def off(va):
    if va < BASE:  # raw file offset (headers, .data)
        return va
    return va - BASE - TEXT_VA + TEXT_RAW


def reloc_entries(data, lo, hi):
    """File offsets of base-relocation entries whose 4 patched bytes overlap [lo, hi) (VAs).
    The exe is ASLR-enabled: the loader adds the load delta at every HIGHLOW entry, which would
    corrupt patched bytes that replaced an absolute address - those entries must be disabled."""
    pe = struct.unpack_from("<I", data, 0x3C)[0]
    opt = pe + 24
    rrva, rsz = struct.unpack_from("<II", data, opt + 96 + 5 * 8)
    nsec = struct.unpack_from("<H", data, pe + 6)[0]
    so = opt + struct.unpack_from("<H", data, pe + 20)[0]
    o = None
    for i in range(nsec):
        vs, va, rs, ra = struct.unpack_from("<IIII", data, so + i * 40 + 8)
        if va <= rrva < va + max(vs, rs):
            o = rrva - va + ra
    out, end = [], o + rsz
    while o < end:
        page, bsz = struct.unpack_from("<II", data, o)
        if bsz == 0:
            break
        for i in range((bsz - 8) // 2):
            e = struct.unpack_from("<H", data, o + 8 + i * 2)[0]
            t = BASE + page + (e & 0xFFF)
            if e >> 12 in (0, 3) and t + 4 > lo and t < hi and (e & 0xFFF or e >> 12 == 3):
                out.append(o + 8 + i * 2)
        o += bsz
    return out


def main():
    if not os.path.exists(BACKUP):
        os.makedirs(os.path.dirname(BACKUP), exist_ok=True)
        data = open(EXE, "rb").read()
        if hashlib.md5(data).hexdigest() != ORIG_MD5:
            sys.exit("exe is not the known original and no backup exists - refusing")
        shutil.copy2(EXE, BACKUP)
        print("backed up original exe to", BACKUP)
    cmd = sys.argv[1]
    data = bytearray(open(EXE, "rb").read())
    if cmd == "restore":
        shutil.copy2(BACKUP, EXE)
        print("original exe restored")
        return
    for name in (sys.argv[2:] if cmd in ("apply", "revert") else PATCHES):
        va, orig, new, desc = PATCHES[name][:4]
        keep_relocs = len(PATCHES[name]) > 4 and PATCHES[name][4]
        o = off(va)
        cur = bytes(data[o:o + len(orig)])
        state = "applied" if cur == new else "original" if cur == orig else "UNKNOWN " + cur.hex()
        rel = [] if keep_relocs or va < BASE else reloc_entries(data, va, va + len(orig))
        if cmd == "apply" and cur == orig:
            data[o:o + len(new)] = new
            for r in rel:  # IMAGE_REL_BASED_ABSOLUTE (skipped by the loader)
                struct.pack_into("<H", data, r, struct.unpack_from("<H", data, r)[0] & 0x0FFF)
            state = "-> applied"
        elif cmd == "revert" and cur == new:
            data[o:o + len(orig)] = orig
            for r in rel:  # back to IMAGE_REL_BASED_HIGHLOW
                struct.pack_into("<H", data, r, (struct.unpack_from("<H", data, r)[0] & 0x0FFF) | 0x3000)
            state = "-> reverted"
        rs = ",".join("%x" % struct.unpack_from("<H", data, r)[0] for r in rel)
        print("%-16s %08x %s  (%s) relocs[%s]" % (name, va, state, desc, rs))
    if cmd in ("apply", "revert"):
        open(EXE, "wb").write(data)


if __name__ == "__main__":
    main()
