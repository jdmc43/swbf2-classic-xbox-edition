#!/usr/bin/env bash
# Run the INSTALLED game windowed on monitor 2 (no file changes). steps: wait= shot= full= key=
cd ~/Downloads/swbf2-mods
label=$1; shift
W="python tools/winlaunch.py"
closegame() {
  if $W alive; then python -c "import ctypes; u=ctypes.windll.user32; u.PostMessageW(u.FindWindowW(None,'Star Wars Battlefront II'),0x10,0,0)"; fi
  for i in $(seq 1 25); do tasklist | grep -qi battlefront || return 0; sleep 1; done; return 1
}
trap closegame EXIT
closegame || { echo "game running, skipped"; trap - EXIT; exit 1; }
$W launch || exit 1
for step in "$@"; do
  $W alive || { echo "CRASH before $step"; exit 1; }
  case "$step" in
    wait=*) sleep "${step#wait=}" ;;
    shot=*) $W move >/dev/null; sleep 0.5; $W shot "shots/$label-${step#shot=}.png" 2 | grep -v "^saved" ;;
    full=*) $W move >/dev/null; sleep 0.5; $W shot "shots/$label-${step#full=}.png" 1 | grep -v "^saved" ;;
    chord=*) c="${step#chord=}"; python -c "
import sys,time; sys.path.insert(0,'tools'); import screen
screen.focus('Star Wars Battlefront II'); time.sleep(0.3); screen.chord('$c'.split('+')); time.sleep(0.5)" > /dev/null ;;
    key=*) k="${step#key=}"; python -c "
import sys,time; sys.path.insert(0,'tools'); import screen
screen.focus('Star Wars Battlefront II'); time.sleep(0.3); screen.key('$k'); time.sleep(0.8)" > /dev/null ;;
  esac
done
$W alive && echo "steps done (alive)" || echo "CRASH at end"
