"""Compile a .lua file into a SWBF2 'scr_' chunk (ScriptMunge equivalent).

scr_ { NAME <name\0>, INFO <01>, BODY <luac 5.0 bytecode, float numbers, source '=(none)'> }
"""
import os
import struct
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
LUAC = os.path.join(HERE, "luac50.exe")
HEADER_LEN = 4 + 1 + 1 + 8 + 4  # sig, ver, endian, 8 size bytes, test number


def chunk(tag, data):
    pad = (4 - len(data) % 4) % 4
    return tag + struct.pack("<I", len(data)) + data + b"\0" * pad


def compile_lua(src_path, strip=True):
    with tempfile.TemporaryDirectory() as td:
        out = os.path.join(td, "out.luac")
        args = [LUAC] + (["-s"] if strip else []) + ["-o", out, src_path]
        subprocess.run(args, check=True)
        bc = open(out, "rb").read()
    # replace main function source name with '=(none)' like ScriptMunge
    off = HEADER_LEN
    n = struct.unpack_from("<I", bc, off)[0]
    new = b"=(none)\0"
    # ScriptMunge stores the bytecode followed by one NUL byte
    return bc[:off] + struct.pack("<I", len(new)) + new + bc[off + 4 + n:] + b"\0"


def scr_chunk(name, src_path, strip=True):
    body = compile_lua(src_path, strip)
    inner = chunk(b"NAME", name.encode() + b"\0") + chunk(b"INFO", b"\x01") + chunk(b"BODY", body)
    return chunk(b"scr_", inner)


if __name__ == "__main__":
    name, src, out = sys.argv[1:4]
    open(out, "wb").write(scr_chunk(name, src))
