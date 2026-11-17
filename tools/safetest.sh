#!/usr/bin/env bash
# wintest with a hard time limit; afterwards make sure the test game is gone and the final files are back
cd ~/Downloads/swbf2-mods
G="/c/Program Files (x86)/Steam/steamapps/common/Star Wars Battlefront II Classic/GameData"
RESTORE_DIR=xbox/final/data/_lvl_pc timeout 330 tools/wintest.sh "$@"; rc=$?
[ $rc = 124 ] && echo "TIMEOUT (test hung)"
if tasklist | grep -qi "BattlefrontII"; then
  python -c "import ctypes; u=ctypes.windll.user32; u.PostMessageW(u.FindWindowW(None,'Star Wars Battlefront II'),0x10,0,0)"
  sleep 8
  tasklist | grep -qi "BattlefrontII" && { taskkill //IM BattlefrontII.exe //F >/dev/null 2>&1; echo "killed hung test game"; sleep 3; }
fi
for f in shell ingame common core xbring; do cp xbox/final/data/_lvl_pc/$f.lvl "$G/data/_lvl_pc/$f.lvl"; done
