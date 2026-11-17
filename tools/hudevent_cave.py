"""Machine code for GetTimerRate (unused by all scripts) -> class picker helpers (personal use).
Lua: GetTimerRate(n [, k])
  130/131  hide/show the player 1 HUD map (object from 0x555870(0)): visible bit 8 of [map+0x194] - its display
           object at +0x180; the map's per-frame update 0x551420 only runs while it is set. Returns nothing.
  140      1 if the local player may spawn as the hero, else 0: calls the spawn display's own test 0x42b590
           ([0x1e2fd12] set -> 1; else hero rules on [0x1e62ee3], the player's team unlocked [0x1e62ee0 + team]
           and the hero assigned to this player [0x1e62ef0 + 4*team] == player index). Hero manager:
           UnlockHeroForTeam 0x58c2f0, unlock rule 0x44c960, accept 0x5cea70 (only for the offered player
           [0x1e62ec8 + 4*team]).
  141, k   may the local player take class k (engine class index of its team)? The spawn display's own test:
           0x61f380(k, &reason) on the player's stats (0x453530(player struct 0x429470(0x5b73b0(0)))).
           Returns allowed + 2*reason: 1 = allowed, 2 = needs more points (PointsToUnlock > score),
           0 = class full (Max units reached). This is what decides the "Get N more points to unlock!" text
           (0x429b17); reading that text's width can't tell it from "Unit Count: 2  Max: 4".
  other    nothing
Earlier versions also fired player-1 HUD events (1..63) and looked up interface objects by name: the spawn-screen
HUD ignored those, so they were dropped for space. Position independent (call/pop load delta; calls are
relative), so ASLR needs no relocations. Unpatched GetTimerRate returns one value for any argument; the 130/131
calls return none (detection).
"""
import struct

CAVE = 0x76A510
SLACK = 0xF0
L_STATE = 0x1E579A0
LUA_TONUMBER, LUA_PUSHNUMBER = 0x69AE10, 0x69C060
GET_MAP = 0x555870
CAN_BE_HERO = 0x42B590
LOCAL_PLAYER, PLAYER_STRUCT, PLAYER_STATS, CLASS_ALLOWED = 0x5B73B0, 0x429470, 0x453530, 0x61F380


def build(debug=0, near=None):
    """near: indices of the jumps that need the rel32 form (found by retrying)"""
    near = set() if near is None else near
    c = bytearray()
    va = lambda: CAVE + len(c)
    jumps = []  # (index, offset of the displacement, size, label)
    labels = {}

    def call(t):
        c.extend(b"\xE8" + struct.pack("<i", t - (va() + 5)))

    def j(op, label):  # jcc/jmp: short form unless this jump is known to need rel32
        o = op[0]
        idx = len(jumps)
        if idx in near:
            c.extend(b"\xE9" if o == 0xEB else bytes([0x0F, o + 0x10]))
            c.extend(b"\x00\x00\x00\x00")
            jumps.append((idx, len(c) - 4, 4, label))
        else:
            c.extend(bytes([o, 0]))
            jumps.append((idx, len(c) - 1, 1, label))

    def here(label):
        labels[label] = len(c)

    def lua_num(arg):  # lua_tonumber(L, arg) -> integer in eax (via [ebp-8])
        c.extend(bytes([0x6A, arg]))                       # push arg
        c.extend(b"\xFF\xB3" + struct.pack("<I", L_STATE))  # push [ebx+L]
        call(LUA_TONUMBER)
        c.extend(b"\x83\xC4\x08\xDB\x5D\xF8\x8B\x45\xF8")  # add esp,8; fistp [ebp-8]; mov eax,[ebp-8]

    c += b"\x55\x8B\xEC\x83\xEC\x08\x53\x56"        # push ebp; mov ebp,esp; sub esp,8; push ebx; push esi
    call(va() + 5)
    l1 = va()
    c += b"\x5B"                                    # L1: pop ebx
    c += b"\x81\xEB" + struct.pack("<I", l1)        # sub ebx, L1      (ebx = load delta)
    lua_num(1)
    # 130/131: map visibility
    c += b"\x3D\x82\x00\x00\x00"; j(b"\x7C", "done")    # cmp eax,130; jl done
    c += b"\x3D\x84\x00\x00\x00"; j(b"\x7D", "hero")    # cmp eax,132; jge hero
    c += b"\x33\xC9"                                # xor ecx,ecx       (player index 0)
    call(GET_MAP)
    c += b"\x85\xC0"; j(b"\x74", "done")            # test eax,eax; jz done
    c += b"\x8B\xF0"                                # mov esi,eax
    c += b"\x81\xA6\x94\x01\x00\x00\xFF\xFE\xFF\xFF"  # and dword [esi+194h],~100h   (hidden)
    c += b"\x80\x7D\xF8\x83"; j(b"\x75", "done")    # cmp byte [ebp-8],131; jne done
    c += b"\x81\x8E\x94\x01\x00\x00\x00\x01\x00\x00"  # or dword [esi+194h],100h      (shown)
    here("done")
    c += b"\x33\xC0"                                # xor eax,eax
    here("out")
    c += b"\x5E\x5B\x8B\xE5\x5D\xC3"                # pop esi; pop ebx; mov esp,ebp; pop ebp; ret
    here("hero")
    # 140: the spawn display's own hero test (returns al)
    c += b"\x3D\x8C\x00\x00\x00"; j(b"\x75", "class")  # cmp eax,140; jne class
    call(CAN_BE_HERO)
    c += b"\x0F\xB6\xC0"                            # movzx eax,al
    j(b"\xEB", "push")
    here("class")
    # 141, k: may the local player take class k
    c += b"\x3D\x8D\x00\x00\x00"; j(b"\x75", "done")  # cmp eax,141; jne done
    lua_num(2)                                      # [ebp-8] = k
    c += b"\x6A\x00"                                # push 0
    call(LOCAL_PLAYER)                              # player index of controller 0
    c += b"\x83\xC4\x04\x8B\xC8"                    # add esp,4; mov ecx,eax
    call(PLAYER_STRUCT)
    c += b"\x85\xC0"; j(b"\x74", "done")            # test eax,eax; jz done
    c += b"\x8B\xC8"                                # mov ecx,eax
    call(PLAYER_STATS)
    c += b"\x8B\xC8"                                # mov ecx,eax
    c += b"\x33\xD2\x89\x55\xFC"                    # xor edx,edx; mov [ebp-4],edx   (reason = 0)
    c += b"\x8D\x55\xFC\x52\xFF\x75\xF8"            # lea edx,[ebp-4]; push edx; push [ebp-8]
    call(CLASS_ALLOWED)                             # thiscall, ret 8
    c += b"\x0F\xB6\xC0"                            # movzx eax,al
    c += b"\x8B\x55\xFC\x03\xD2\x0B\xC2"            # mov edx,[ebp-4]; add edx,edx; or eax,edx
    here("push")
    c += b"\xF3\x0F\x2A\xC0\x51\xF3\x0F\x11\x04\x24"  # cvtsi2ss xmm0,eax; push ecx; movss [esp],xmm0
    c += b"\xFF\xB3" + struct.pack("<I", L_STATE)     # push [ebx+L]
    call(LUA_PUSHNUMBER)
    c += b"\x83\xC4\x08\xB8\x01\x00\x00\x00"          # add esp,8; mov eax,1
    j(b"\xEB", "out")
    for idx, o, size, label in jumps:
        d = labels[label] - (o + size)
        if size == 1:
            if not -128 <= d <= 127:
                return build(debug, near | {idx})
            c[o] = d & 0xFF
        else:
            struct.pack_into("<i", c, o, d)
    assert len(c) <= SLACK, len(c)
    return bytes(c)


if __name__ == "__main__":
    import sys
    from capstone import Cs, CS_ARCH_X86, CS_MODE_32
    code = build(int(sys.argv[1]) if len(sys.argv) > 1 else 0)
    print(len(code), "bytes")
    for i in Cs(CS_ARCH_X86, CS_MODE_32).disasm(code, CAVE):
        print("%08x  %-8s %s" % (i.address, i.mnemonic, i.op_str))
