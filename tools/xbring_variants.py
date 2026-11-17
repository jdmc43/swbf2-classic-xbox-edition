"""Build re-textured model variants for the class picker's 3D ring (personal use).

The engine applies a class's OverrideTexture / OverrideTexture2 to the model segments whose material
is named "override_texture" / "override_texture2" (texture slot 0). The ring's interface models can
only show a mesh by name, so for every (mesh, tex1, tex2) combination a class can have - from the
classes' own definitions and from every Remaster skin-changer skin set - this writes a renamed copy
of the mesh with those textures baked in. Each copy is its own sub-level of xbring.lvl, so a mission
loads only the few it needs: ReadDataFile("xbring.lvl", "xbr...", ...).

usage: xbring_variants.py <GameData> <sides.json> <out_dir> <skins.tsv>...
out_dir/xbring.lvl, compat/xboxpicker/variants.lua (or $XBRING_VARIANTS_LUA)
"""
import json, os, struct, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ucfb import read_chunks


def h20(s):  # the engine's name hash (FNV-1a over c | 0x20)
    h = 0x811c9dc5
    for c in s.encode("latin-1"):
        h = ((h ^ (c | 0x20)) * 16777619) & 0xffffffff
    return h


def chunk(tag, data):
    return tag + struct.pack("<I", len(data)) + data + b"\0" * ((4 - len(data) % 4) % 4)


def cstr(b):
    return b.split(b"\0")[0].decode("latin-1")


game, sides_json, out_dir = sys.argv[1:4]
skin_files = sys.argv[4:]
d = json.load(open(sides_json))


def res(c, p):
    seen = 0
    while c in d and seen < 25:
        v = d[c]["props"].get(p)
        if v:
            return v[0]
        c = d[c]["parent"]
        seen += 1
    return None


# ---------------------------------------------------------------- combinations
combos = {}  # key -> (mesh, t1, t2)


def add(mesh, t1, t2):
    if not mesh or not (t1 or t2):
        return
    key = "%s|%s|%s" % (mesh.lower(), (t1 or "").lower(), (t2 or "").lower())
    combos.setdefault(key, (mesh, t1, t2))


for c in d:
    if d[c]["kind"] == "entc":
        add(res(c, "GeometryName"), res(c, "OverrideTexture"), res(c, "OverrideTexture2"))

skins = {}
for f in skin_files:
    for line in open(f, encoding="latin-1"):
        p = line.rstrip("\n").split("\t")
        if len(p) < 4 or p[1] in ("READ", "ERROR"):
            continue
        skins.setdefault(p[0], {}).setdefault(p[1].lower(), {})[p[2].lower()] = p[3]
for s, classes in skins.items():
    for c, props in classes.items():
        mesh = props.get("geometryname") or res(c, "GeometryName")
        add(mesh, props.get("overridetexture") or res(c, "OverrideTexture"),
            props.get("overridetexture2") or res(c, "OverrideTexture2"))

# ---------------------------------------------------------------- find source models
want = {m.lower() for m, _, _ in combos.values()}
models, gmods, skels = {}, {}, {}  # skel: the engine binds a model's skeleton by model name


def scan(buf, start, end):
    for tag, a, z in read_chunks(buf, start, end):
        if tag == b"lvl_":
            scan(buf, a + 8, z)
        elif tag == b"skel":
            for t, x, y in read_chunks(buf, a, z):
                if t == b"INFO":
                    n = cstr(buf[x:y]).lower()
                    if n in want:
                        skels.setdefault(n, buf[a:z])
                    break
        elif tag in (b"modl", b"gmod"):
            for t, x, y in read_chunks(buf, a, z):
                if t == b"NAME":
                    n = cstr(buf[x:y]).lower()
                    if n in want:
                        (models if tag == b"modl" else gmods).setdefault(n, buf[a:z])
                    break


side = os.path.join(game, "data", "_lvl_pc", "side")
files = [os.path.join(side, "Skinchanger", f) for f in sorted(os.listdir(os.path.join(side, "Skinchanger")))]
files += [os.path.join(side, f) for f in sorted(os.listdir(side))]
for f in files:
    if f.lower().endswith(".lvl") and os.path.isfile(f):
        buf = open(f, "rb").read()
        scan(buf, 8, len(buf))
        if want <= set(models) and want <= set(skels):
            break

# ---------------------------------------------------------------- variants
OT1, OT2 = h20("override_texture"), h20("override_texture2")


def variant_modl(body, vname, t1, t2):
    out = b""
    for t, a, z in read_chunks(body, 0, len(body)):
        data = body[a:z]
        if t == b"NAME":
            data = vname.encode() + b"\0"
        elif t == b"segm":
            kids = read_chunks(body, a, z)
            mnam = next((cstr(body[x:y]) for tt, x, y in kids if tt == b"MNAM"), "")
            tex = t1 if mnam and h20(mnam) == OT1 else t2 if mnam and h20(mnam) == OT2 else None
            if tex:
                seg = b""
                for tt, x, y in kids:
                    sd = body[x:y]
                    if tt == b"TNAM" and struct.unpack_from("<I", sd)[0] == 0:
                        sd = struct.pack("<I", 0) + tex.encode() + b"\0"
                    seg += chunk(tt, sd)
                data = seg
        out += chunk(t, data)
    return chunk(b"modl", out)


def variant_skel(body, vname):
    out = b""
    for t, a, z in read_chunks(body, 0, len(body)):
        data = body[a:z]
        if t == b"INFO":
            data = vname.encode() + b"\0" + data[len(data.split(b"\0")[0]) + 1:]
        out += chunk(t, data)
    return chunk(b"skel", out)


def variant_gmod(body, vname):
    out = b""
    for t, a, z in read_chunks(body, 0, len(body)):
        data = body[a:z]
        if t == b"NAME":
            data = vname.encode() + b"\0"
        elif t.startswith(b"LOD"):
            if t != b"LOD0":
                continue
            data = vname.encode() + b"\0" + data[len(data.split(b"\0")[0]) + 1:]
        out += chunk(t, data)
    return chunk(b"gmod", out)


lvls, table, missing, noskel = b"", [], set(), 0
for key in sorted(combos):
    mesh, t1, t2 = combos[key]
    src = models.get(mesh.lower())
    if src is None:
        missing.add(mesh)
        continue
    vname = "xbr%08x" % h20(key)
    sk = skels.get(mesh.lower())
    inner = variant_skel(sk, vname) if sk else b""
    noskel += 0 if sk else 1
    inner += variant_modl(src, vname, t1, t2)
    g = gmods.get(mesh.lower())
    inner += variant_gmod(g, vname) if g else b""
    lvls += chunk(b"lvl_", struct.pack("<II", h20(vname), len(inner)) + inner)
    table.append('\t["%s"] = "%s",' % (key, vname))

os.makedirs(out_dir, exist_ok=True)
open(os.path.join(out_dir, "xbring.lvl"), "wb").write(b"ucfb" + struct.pack("<I", len(lvls)) + lvls)
open(os.environ.get("XBRING_VARIANTS_LUA") or "compat/xboxpicker/variants.lua", "w").write(
    "-- generated by tools/xbring_variants.py: (mesh|tex1|tex2) -> re-textured copy in xbring.lvl\n"
    "XBRING_VARIANTS = {\n" + "\n".join(table) + "\n}\n")
print("combinations %d, variants %d, missing meshes %d %s" % (len(combos), len(table), len(missing), sorted(missing)[:8]))
print("xbring.lvl %.1f MB, variants without skeleton: %d" % (len(lvls) / 1e6, noskel))
