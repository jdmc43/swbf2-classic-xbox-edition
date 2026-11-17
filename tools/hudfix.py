"""Make the Xbox 1-player HUD look on the PC 16:9 renderer like the Xbox widescreen HUD (personal use).

Measured (HUDEXAMPLE vs PC screenshots): the PC maps HUD y as  y_screen = A + B*y  (vertical safe-area squeeze),
leaves x alone, stretches 2D bitmaps to the 16:9 width, and draws 3D HUD meshes a bit larger. The reference shows
the authored positions with aspect-correct 2D elements. So, in place (float edits only, same sizes):
  top-level Position/PositionSmall:  y' = (y - A) / B ;  x' = 0.5 + (x - 0.5) * KX for centre elements
  nested Position offsets:           dx' = dx * KX ; dy' = dy / B          (not inside an adjusted scaled group)
  BitmapRect(w, h):                  w * KX, h / B
  Scale of a 2D group:               sx * KX, sy / B  (its whole subtree follows, so it is left alone)
  Scale of 3D meshes / the map:      * K3 (uniform)
usage: hudfix.py <in hud lvl> <out hud lvl>
"""
import struct, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hudtree as H

A, B = 0.058, 0.893
KX, K3 = 0.75, 0.79  # K3: minimap only (3D HUD meshes match the reference size)
CENTRE = (0.35, 0.65)
# positioned by the aim point / targets at run time: leave as authored
K_W2 = 0.78
K_INF = 0.55
PC_SMALL_TEXCOORDS = (0.248419, 0.564873, 0.470641, 0.787095)
# the Remaster ships its own hud_weapon2_backdrop model in this file, which does not draw as the Xbox
# grenade capsule: drop it so the stock model from ingame.lvl is used
DROP_MODELS = {"hud_weapon2_backdrop"}
BAR = 0x3bd46d91  # bar element (Bitmap fill driven by EventValue)
# spawn-screen clutter the Xbox class/post screens don't have (the picker shows its own prompts): off screen
OFFSCREEN = {"player1mapkey"}
if os.environ.get("HUD_IA"):  # Instant Action variant (pad_hook loads it outside the campaign): no objective list
    OFFSCREEN.add("player1objectives")
AIMED = {"player1reticule", "player1weapon1lockon", "player1weapon2lockon", "player1target"}

P = {n: H.h20(n) for n in ["Position", "PositionSmall", "PositionSpawn", "PositionLarge", "BitmapRect", "Scale",
                          "Group", "Bitmap", "Model3D", "Map", "Text", "Mesh"]}


def kind(n):
    for k in ("Group", "Bitmap", "Model3D", "Map", "Text"):
        if n.hash == P[k]:
            return k
    return "other"


def child(n, prop):
    return [k for k in n.kids if k.hash == P[prop]]


class Fix:
    def __init__(s, buf):
        s.buf = bytearray(buf)
        s.log = []
        s.k3 = 1.0

    def get(s, node, i):
        return struct.unpack_from("<f", s.buf, node.vals[i][0])[0]

    def put(s, node, i, v):
        struct.pack_into("<f", s.buf, node.vals[i][0], v)

    def pos_top(s, p, what):
        x, y = s.get(p, 0), s.get(p, 1)
        nx = 0.5 + (x - 0.5) * KX if CENTRE[0] < x < CENTRE[1] else x
        ny = (y - A) / B
        s.put(p, 0, nx); s.put(p, 1, ny)
        s.log.append("%s %s (%.4f,%.4f)->(%.4f,%.4f)" % (what, H.NAMES.get(p.hash), x, y, nx, ny))

    def elem(s, n, top, centre):
        """n: element node (has children). centre: inside a centre-anchored top-level element"""
        label = n.vals[0][2] if n.vals and n.vals[0][2] else H.NAMES.get(n.hash, "%08x" % n.hash)
        props = {}
        for k in n.kids:
            props.setdefault(k.hash, []).append(k)
        if n.hash == P["Map"]:
            for p in props.get(P["PositionSmall"], []):
                s.pos_top(p, label)
            for p in props.get(P["Scale"], []):
                for i in range(3): s.put(p, i, s.get(p, i) * K3)
            # the PC map_mask texture (ingame.lvl) has another atlas layout: use the PC HUD's coordinates
            for k in n.kids:
                if k.hash == H.h20("BackdropSmall"):
                    for t in k.kids:
                        if t.hash == H.h20("TexCoords"):
                            for i, v in enumerate(PC_SMALL_TEXCOORDS): s.put(t, i, v)
                            s.log.append("map BackdropSmall TexCoords -> PC")
            return
        for p in ([] if n.hash == BAR else props.get(P["Position"], [])):  # bar positions are anchors, not offsets
            if top:
                s.pos_top(p, label)
                x = s.get(p, 0)
                centre = CENTRE[0] < x < CENTRE[1]
            else:
                if centre:
                    s.put(p, 0, s.get(p, 0) * KX)
                s.put(p, 1, s.get(p, 1) / B)
        if label == "player1weapon2backdrop":
            # the PC hud_weapon2_backdrop mesh sits on the ammo row (the Xbox mesh has its geometry moved up a row):
            # place it on the grenade row - grenade count text y + the ammo capsule's offset from its text
            for p in props.get(P["Position"], []):
                s.put(p, 1, (0.2801 + (0.3562 - 0.3409)) / B)
                s.log.append("weapon2 backdrop moved to the grenade row")
        rects = props.get(P["BitmapRect"], [])
        for r in rects:
            s.put(r, 0, s.get(r, 0) * KX)
            s.put(r, 1, s.get(r, 1) / B)
        is3d = P["Mesh"] in props or n.hash == P["Model3D"]
        if s.k3 != 1.0:
            for p in props.get(P["Scale"], []):
                for i in range(3): s.put(p, i, s.get(p, i) * s.k3)
        if label == "player1weapon2group":  # grenade/2nd weapon icon: smaller, like the reference
            s.k3 = K_W2
        if label in ("player1weapon1ammoInfinite", "player1weapon2ammoInfinite"):
            # the PC hud_infinite_ammo_icon mesh is much larger than the Xbox one: number-sized again
            for p in props.get(P["Scale"], []):
                for i in range(3): s.put(p, i, s.get(p, i) * K_INF)
        sc = props.get(P["Scale"], [])
        if sc and not rects and not is3d and any(k.kids for k in n.kids):
            for p in sc:  # scaled 2D group: its subtree follows the scale
                s.put(p, 0, s.get(p, 0) * KX)
                s.put(p, 1, s.get(p, 1) / B)
            s.log.append("scaled group %s" % label)
            return
        saved = s.k3
        for k in n.kids:
            if k.kids:
                s.elem(k, False, centre)
        if label == "player1weapon2group":
            s.k3 = 1.0


def drop_models(buf):
    from ucfb import read_chunks
    keep = b""
    dropped = 0
    for t, a, z in read_chunks(buf, 8, len(buf)):
        name = None
        if t in (b"modl", b"skel", b"gmod", b"coll"):
            for tt, x, y in read_chunks(buf, a, z):
                if tt in (b"NAME", b"INFO"):
                    name = buf[x:y].split(b"\0")[0].decode("latin-1"); break
        if name in DROP_MODELS:
            dropped += 1
            continue
        keep += buf[a - 8:z] + b"\0" * ((4 - (z - a) % 4) % 4)
    print("dropped model chunks:", dropped)
    return b"ucfb" + struct.pack("<I", len(keep)) + keep


def main(src, dst):
    buf = open(src, "rb").read()
    f = Fix(buf)
    done = 0
    for a, z, nodes in H.huds(buf):
        if not any(n.vals and n.vals[0][2] == "1playerhud" for n in nodes):
            continue
        for n in nodes:
            lbl = n.vals[0][2] if n.vals and n.vals[0][2] else ""
            if lbl in AIMED:
                continue
            if lbl in OFFSCREEN:
                for k in n.kids:
                    if k.hash == P["Position"]:
                        f.put(k, 0, -2.0)
                        f.log.append("off screen: " + lbl)
                continue
            if kind(n) != "other" or (n.vals and n.vals[0][2] and n.vals[0][2].startswith("player1")):
                f.elem(n, True, False)
        done += 1
    out = drop_models(bytes(f.buf))
    open(dst, "wb").write(out)
    print("1playerhud fixed:", done, "| changes:", len(f.log))
    for l in f.log[:60]:
        print("  ", l)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
