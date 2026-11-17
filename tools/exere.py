"""Small static-analysis helpers for BattlefrontII.exe (personal use).
usage: re.py str <text>            find string VA(s)
       re.py xref <hexVA>          code locations that reference VA (imm32 operands)
       re.py dis <hexVA> [n]       disassemble n instructions at VA
       re.py func <hexVA>          disassemble from VA until ret (max 400)
       re.py calls <hexVA>         list call targets inside the function at VA
"""
import struct, sys
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

EXE = r"C:\Program Files (x86)\Steam\steamapps\common\Star Wars Battlefront II Classic\GameData\BattlefrontII.exe"
b = open(EXE, "rb").read()
pe = struct.unpack_from("<I", b, 0x3c)[0]
nsec = struct.unpack_from("<H", b, pe + 6)[0]
opt = struct.unpack_from("<H", b, pe + 20)[0]
BASE = struct.unpack_from("<I", b, pe + 24 + 28)[0]
secs = []
off = pe + 24 + opt
for i in range(nsec):
    n, vs, va, rs, ra = struct.unpack_from("<8sIIII", b, off + i * 40)
    secs.append((n.rstrip(b"\0").decode(), BASE + va, vs, ra, rs))


def va2off(v):
    for n, va, vs, ra, rs in secs:
        if va <= v < va + rs:
            return ra + (v - va)
    return None


def off2va(o):
    for n, va, vs, ra, rs in secs:
        if ra <= o < ra + rs:
            return va + (o - ra)
    return None


text = [s for s in secs if s[0] == ".text"][0]
TEXT = b[text[3]:text[3] + text[4]]
TVA = text[1]
md = Cs(CS_ARCH_X86, CS_MODE_32)
md.detail = False


def find_str(s):
    out = []
    needle = s.encode() + b"\0"
    i = b.find(needle)
    while i >= 0:
        if i == 0 or b[i - 1] == 0:
            out.append(off2va(i))
        i = b.find(needle, i + 1)
    return out


def xrefs(v):
    pat = struct.pack("<I", v)
    out = []
    i = TEXT.find(pat)
    while i >= 0:
        out.append(TVA + i)
        i = TEXT.find(pat, i + 1)
    return out


def dis(v, n=30):
    o = va2off(v)
    code = b[o:o + n * 15]
    res = []
    for ins in md.disasm(code, v):
        res.append(ins)
        if len(res) >= n:
            break
    return res


def func(v, maxn=400):
    out = []
    o = va2off(v)
    for ins in md.disasm(b[o:o + maxn * 15], v):
        out.append(ins)
        if ins.mnemonic in ("ret", "retn") or len(out) >= maxn:
            break
    return out


if __name__ == "__main__":
    cmd = sys.argv[1]
    if cmd == "str":
        for v in find_str(sys.argv[2]):
            print(hex(v))
    elif cmd == "xref":
        for v in xrefs(int(sys.argv[2], 16)):
            print(hex(v))
    elif cmd == "dis":
        for ins in dis(int(sys.argv[2], 16), int(sys.argv[3]) if len(sys.argv) > 3 else 30):
            print("%08x  %-8s %s" % (ins.address, ins.mnemonic, ins.op_str))
    elif cmd == "func":
        for ins in func(int(sys.argv[2], 16)):
            print("%08x  %-8s %s" % (ins.address, ins.mnemonic, ins.op_str))
    elif cmd == "calls":
        for ins in func(int(sys.argv[2], 16), 2000):
            if ins.mnemonic == "call":
                print("%08x  call %s" % (ins.address, ins.op_str))
