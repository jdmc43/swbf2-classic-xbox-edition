"""In-place, same-length ODF property patches of the PC side files (1.2 GB each; personal use).
Records every patched offset under ~/Documents/SWBF2-backups/sidepatch-<name>.json so it can be reverted.
A Steam "Verify integrity" also restores the originals.

PATCHES:
  rep_commando_pistol  GeometryName rep_weap_inf_smallpistol -> rep_weap_inf_pistol
      The PC re-release's HD commando/award pistol model has no HUD icon (the HUD can't draw it and the
      class has no HUDTag; SetClassProperty can't change either after load). The Xbox jet trooper carried
      the DC-17 blaster pistol, whose third-person model and icon this uses.

usage: sidepatch.py apply|revert|status [gamedata dir]
"""
import json, os, struct, sys

GAME = "C:/Program Files (x86)/Steam/steamapps/common/Star Wars Battlefront II Classic/GameData"
BACKUP = os.path.join(os.path.expanduser("~"), "Documents", "SWBF2-backups")

PATCHES = [
    ("rep_commando_pistol", "data/_lvl_pc/side/rep.lvl", "GeometryName",
     "rep_weap_inf_smallpistol", "rep_weap_inf_pistol"),
]


def fnv(s):
    h = 0x811C9DC5
    for c in s.lower().encode():
        h = ((h ^ c) * 16777619) & 0xFFFFFFFF
    return h


def find_all(buf, pat):
    out, i = [], buf.find(pat)
    while i >= 0:
        out.append(i)
        i = buf.find(pat, i + 1)
    return out


def main(cmd, game=GAME):
    for name, rel, prop, old, new in PATCHES:
        path = os.path.join(game, rel)
        o = old.encode() + b"\0"
        n = new.encode() + b"\0"
        assert len(n) <= len(o)
        n = n.ljust(len(o), b"\0")
        key = struct.pack("<I", fnv(prop))
        rec = os.path.join(BACKUP, "sidepatch-%s.json" % name)
        buf = open(path, "rb").read()
        olds = [i + 4 for i in find_all(buf, key + o)]
        news = [i + 4 for i in find_all(buf, key + n)]
        if cmd == "status":
            print("%s: %d original, %d patched" % (name, len(olds), len(news)))
        elif cmd == "apply":
            if not olds:
                print("%s: nothing to patch (%d already patched)" % (name, len(news)))
                continue
            done = json.load(open(rec))["offsets"] if os.path.exists(rec) else []
            json.dump({"file": path, "old": o.hex(), "new": n.hex(), "offsets": sorted(set(done + olds))},
                      open(rec, "w"))
            with open(path, "r+b") as f:
                for off in olds:
                    f.seek(off)
                    f.write(n)
            print("%s: patched %d" % (name, len(olds)))
        elif cmd == "revert":
            if not os.path.exists(rec):
                print("%s: no record" % name)
                continue
            r = json.load(open(rec))
            with open(path, "r+b") as f:
                for off in r["offsets"]:
                    f.seek(off)
                    if f.read(len(n)) == n:
                        f.seek(off)
                        f.write(o)
            os.remove(rec)
            print("%s: reverted %d" % (name, len(r["offsets"])))


if __name__ == "__main__":
    main(*sys.argv[1:3])
