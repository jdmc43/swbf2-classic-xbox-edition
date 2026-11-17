#!/usr/bin/env bash
# Windowed, input-free test on monitor 2: install build dir lvls, launch, timed window screenshots, restore.
# usage: wintest.sh <build-dir> <label> step...   steps: wait=<s> shot=<name>
cd ~/Downloads/swbf2-mods
G="/c/Program Files (x86)/Steam/steamapps/common/Star Wars Battlefront II Classic/GameData"
R=${RESTORE_DIR:-~/Documents/SWBF2-backups/remaster-before-controller/data/_lvl_pc}
build=$1; label=$2; shift 2
W="python tools/winlaunch.py"
closegame() {
  if $W alive; then python -c "import ctypes; u=ctypes.windll.user32; u.PostMessageW(u.FindWindowW(None,'Star Wars Battlefront II'),0x10,0,0)"; fi
  for i in $(seq 1 25); do tasklist | grep -qi battlefront || return 0; sleep 1; done; return 1
}
files=$(cd "$build" && ls *.lvl)
restore() {
  closegame || { echo "WARNING: game still running, NOT restored"; return; }
  for f in $files; do cp "$R/$f" "$G/data/_lvl_pc/$f"; done
  echo "restored: $files"
}
FG=$($W fg)
trap 'restore; $W focus $FG' EXIT
closegame || { echo "game still running, skipped"; trap - EXIT; exit 1; }
for f in $files; do cp "$build/$f" "$G/data/_lvl_pc/$f"; done
$W launch || exit 1
for step in "$@"; do
  $W alive || { echo "CRASH before $step"; exit 1; }
  case "$step" in
    wait=*) sleep "${step#wait=}" ;;
    shot=*) $W move >/dev/null; sleep 0.5; $W shot "shots/$label-${step#shot=}.png" 2 | grep -v "^saved" ;;
    key=*) k="${step#key=}"; python -c "
import sys,time; sys.path.insert(0,'tools'); import screen
screen.focus('Star Wars Battlefront II'); time.sleep(0.3); screen.key('$k'); time.sleep(0.8)" > /dev/null ;;
    chord=*) c="${step#chord=}"; python -c "
import sys,time; sys.path.insert(0,'tools'); import screen
screen.focus('Star Wars Battlefront II'); time.sleep(0.3); screen.chord('$c'.split('+')); time.sleep(0.5)" > /dev/null ;;
    full=*) $W move >/dev/null; sleep 0.5; $W shot "shots/$label-${step#full=}.png" 1 | grep -v "^saved" ;;
  esac
done
$W alive && echo "steps done (alive)" || echo "CRASH at end"
