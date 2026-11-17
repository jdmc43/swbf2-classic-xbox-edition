#!/usr/bin/env bash
# TEST build into xbox/build-skinprobe (personal use): tools/build.py with test switches given as Lua globals in
# XBRING_FLAGS (copied into the class picker script), e.g.
#   XBRING_FLAGS='XBP_HERO = 1
#   XBTEST_WIN = 5' tools/mkprobe.sh [probe|noprobe]
# probe = also the on-screen debug probe (compat/xboxpicker/probe.lua). Test switches (test builds only):
#   XBTEST_UNLOCK = 1      no points needed for any class        XBTEST_SUICIDE = s   die s seconds after spawning
#   XBTEST_POINTS = n      n flag captures for player 0 per spawn XBTEST_WIN = s       win the match after s seconds
#   XBP_HERO = 1           probe line: lock states / hero check
# Only ingame.lvl (+ core/common/xbring) is replaced; xbox/build-skinprobe/shell.lvl stays (an autostart shell,
# e.g. from tools/testshell.py herotest).
# Inputs: $SWBF2_REMASTER_LVL / $SWBF2_REMASTER_HUD (Remaster originals), $SWBF2_CTRL (controller patch GameData).
cd "$(dirname "$0")/.." || exit 1
G=${SWBF2_GAME:-"C:/Program Files (x86)/Steam/steamapps/common/Star Wars Battlefront II Classic/GameData"}
B=$(cygpath -m ~/Documents/SWBF2-backups)
R=${SWBF2_REMASTER_LVL:-$B/remaster-before-controller/data/_lvl_pc}
H=${SWBF2_REMASTER_HUD:-$B/remaster-hud-original/hud_16x09.lvl}
C=${SWBF2_CTRL:-ctrl/GameData}
P=""; [ "${1:-probe}" = probe ] && P="--probe"
python tools/build.py --rem "$R" --remhud "$H" --game "$G" --ctrl "$C" --out xbox/build-skinprobe-out \
  --work xbox/build-skinprobe-work --flags "${XBRING_FLAGS:-}" $P | tail -1 || exit 1
mkdir -p xbox/build-skinprobe
cp xbox/build-skinprobe-out/data/_lvl_pc/{ingame,core,common,xbring}.lvl xbox/build-skinprobe/
echo "built xbox/build-skinprobe (ingame, core, common, xbring)"
