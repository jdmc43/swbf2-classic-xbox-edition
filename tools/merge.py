"""Build Remaster-compatible versions of the UOP Controller Patch .lvl files.

Base = controller patch files. On top of that:
  * shell.lvl / ingame.lvl: the controller patch's shell_interface / game_interface are renamed
    to ctrl_shell_interface / ctrl_game_interface and replaced by small wrappers that load the
    Remaster hooks (addon/Remaster) and then run the controller patch scripts.
  * Remaster-only content (HD textures, mode/era icons, models, HUD configs, ...) is copied in.
  * core.lvl: gamefont_tiny / gamefont_super_tiny are removed so the Remaster's HD fonts load.

usage: merge.py <stock_lvl_dir> <ctrl_lvl_dir> <remaster_lvl_dir> <wrapper_src_dir> <out_dir>
"""
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import munge  # noqa: E402
import ucfb  # noqa: E402


def raw_items(path):
    buf, items = ucfb.load(path)
    out = []
    seen = {}
    for it in items:
        k = ucfb.key(it, seen)
        out.append([k, buf[it["start"]:it["end"]]])  # without padding; re-padded on write
    return buf, out


def unpad(chunk_bytes):
    size = struct.unpack_from("<I", chunk_bytes, 4)[0]
    return chunk_bytes[:8 + size]


def write_lvl(items):
    body = b"".join(munge.chunk(raw[:4], raw[8:]) for _, raw in items)
    return b"ucfb" + struct.pack("<I", len(body)) + body


def rename_scr(raw, new_name):
    kids = ucfb.read_chunks(raw, 8, len(raw))
    out = b""
    for t, a, b in kids:
        data = new_name.encode() + b"\0" if t == b"NAME" else raw[a:b]
        out += munge.chunk(t, data)
    return b"scr_" + struct.pack("<I", len(out)) + out


class Lvl:
    def __init__(self, path):
        self.orig, self.items = raw_items(path)
        assert write_lvl(self.items) == self.orig, f"round-trip mismatch: {path}"
        self.log = []

    def find(self, key):
        for i, (k, _) in enumerate(self.items):
            if k == key:
                return i
        return None

    def replace(self, key, raw, why):
        i = self.find(key)
        if i is None:
            raise KeyError(key)
        self.items[i][1] = raw
        self.log.append(f"replace {key[0]} {key[1]}: {why}")

    def insert_after(self, after_key, key, raw, why):
        i = self.find(after_key) if after_key else None
        pos = len(self.items) if i is None else i + 1
        self.items.insert(pos, [key, raw])
        self.log.append(f"add     {key[0]} {key[1]}: {why}")

    def remove(self, key, why):
        i = self.find(key)
        del self.items[i]
        self.log.append(f"remove  {key[0]} {key[1]}: {why}")

    def rename_script(self, old, new):
        key = ("scr_", old, 0)
        i = self.find(key)
        self.items[i] = [("scr_", new, 0), rename_scr(self.items[i][1], new)]
        self.log.append(f"rename  scr_ {old} -> {new}")


def overlay_remaster_only(out, stock_path, rem_path, skip=()):
    """Copy items the Remaster changed/added where the controller patch kept stock."""
    _, stock = raw_items(stock_path)
    _, rem = raw_items(rem_path)
    stock_d = dict((k, r) for k, r in stock)
    base_d = dict((k, r) for k, r in out.items)
    prev = None
    for k, r in rem:
        if k in skip:
            prev = k if out.find(k) is not None else prev
            continue
        s = stock_d.get(k)
        b = base_d.get(k)
        if r != s:  # Remaster changed or added this item
            if b is None:
                out.insert_after(prev, k, r, "Remaster addition")
            elif b == s:
                out.replace(k, r, "Remaster change (controller patch kept stock)")
            elif b != r:
                raise RuntimeError(f"unhandled conflict {k}")
        if out.find(k) is not None:
            prev = k
    # Items the Remaster deliberately removed (it ships replacements in addon/Remaster).
    rem_keys = set(k for k, _ in rem)
    for k, s in stock:
        if k in rem_keys or k in skip:
            continue
        i = out.find(k)
        if i is not None and out.items[i][1] == s:
            out.remove(k, "removed by Remaster (replacement loaded from addon/Remaster)")
    return out


def main(stock, ctrl, rem, wsrc, outdir):
    os.makedirs(outdir, exist_ok=True)
    report = []

    # ---- shell.lvl
    lvl = Lvl(os.path.join(ctrl, "shell.lvl"))
    lvl.rename_script("shell_interface", "ctrl_shell_interface")
    lvl.insert_after(("scr_", "ctrl_shell_interface", 0), ("scr_", "shell_interface", 0),
                     unpad(munge.scr_chunk("shell_interface", os.path.join(wsrc, "shell_interface.lua"))),
                     "compat wrapper (Remaster hook -> ctrl_shell_interface)")
    _, rem_items = raw_items(os.path.join(rem, "shell.lvl"))
    rem_d = dict(rem_items)
    lvl.replace(("tex_", "iface_bgmeta_space", 0), rem_d[("tex_", "iface_bgmeta_space", 0)],
                "Remaster HD texture")
    # Every script/mcfg conflict is plain UOP on the Remaster side (verified by disassembly),
    # so items the controller patch changed keep the controller patch version.
    stock_s = dict(raw_items(os.path.join(stock, "shell.lvl"))[1])
    ctrl_changed = {k for k, r in lvl.items if stock_s.get(k) != r}
    skip = ctrl_changed | {("scr_", "shell_interface", 0), ("scr_", "ifs_trailer", 0)}
    overlay_remaster_only(lvl, os.path.join(stock, "shell.lvl"), os.path.join(rem, "shell.lvl"),
                          skip=skip)
    report.append(("shell.lvl", lvl))

    # ---- common.lvl
    lvl = Lvl(os.path.join(ctrl, "common.lvl"))
    stock_c = dict(raw_items(os.path.join(stock, "common.lvl"))[1])
    ctrl_changed = {k for k, r in lvl.items if stock_c.get(k) != r}
    overlay_remaster_only(lvl, os.path.join(stock, "common.lvl"), os.path.join(rem, "common.lvl"),
                          skip=ctrl_changed)
    report.append(("common.lvl", lvl))

    # ---- core.lvl
    lvl = Lvl(os.path.join(ctrl, "core.lvl"))
    for f in ("gamefont_tiny", "gamefont_super_tiny"):
        lvl.remove(("font", f, 0), "Remaster loads HD version from addon/Remaster/Fonts")
    report.append(("core.lvl", lvl))

    # ---- ingame.lvl
    lvl = Lvl(os.path.join(ctrl, "ingame.lvl"))
    stock_i = dict(raw_items(os.path.join(stock, "ingame.lvl"))[1])
    ctrl_changed = {k for k, r in lvl.items if stock_i.get(k) != r}
    lvl.rename_script("game_interface", "ctrl_game_interface")
    lvl.insert_after(("scr_", "ctrl_game_interface", 0), ("scr_", "game_interface", 0),
                     unpad(munge.scr_chunk("game_interface", os.path.join(wsrc, "game_interface.lua"))),
                     "compat wrapper (Remaster ingame hook -> ctrl_game_interface)")
    overlay_remaster_only(lvl, os.path.join(stock, "ingame.lvl"), os.path.join(rem, "ingame.lvl"),
                          skip=ctrl_changed | {("scr_", "game_interface", 0)})
    report.append(("ingame.lvl", lvl))

    for name, l in report:
        data = write_lvl(l.items)
        open(os.path.join(outdir, name), "wb").write(data)
        print(f"== {name}: {len(data)} bytes, {len(l.log)} changes vs controller patch")
        for line in l.log:
            print("   " + line)


if __name__ == "__main__":
    main(*sys.argv[1:6])
