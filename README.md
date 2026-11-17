# Star Wars Battlefront II Classic – Xbox Edition

Make **Star Wars Battlefront II Classic** (Steam, 2024 update) with the **Battlefront II Remaster** look and play
like the original Xbox version with a controller: an Xbox class picker (3D carousel of the units, locked classes
as black silhouettes, the earned hero), Xbox fonts and widescreen HUD, console button icons, controller navigation
in the menus, the Instant Action console screen and controller-driven end-of-match stats.

**Players:** download the release package and read its README. It contains only this mod's code; the installer
builds the mod files on your PC from your own installs:

| Needed | Where |
|---|---|
| Star Wars Battlefront II Classic (Steam) | you own it |
| Battlefront II Remaster (Jan 2026) by Anakin | Nexus Mods / ModDB |
| UOP controller patch 1.1 (`GameData.7z`) by BAD-AL | https://github.com/BAD-AL/data_UOP_controller_patch (the installer can download it) |
| optional: your own Xbox *Star Wars Battlefront II* disc image | for the Xbox HUD |

## How it works

Nothing of the game, the Remaster or the controller patch is copied or rebuilt from source. `tools/build.py`
reads the player's files and keeps their compiled scripts untouched under another name (`xbe_*`), adding small
wrapper scripts that run them (`ScriptCB_DoFile`) with this mod's Lua around them:

- `compat/console/` – controller layer for the menus (`pad_hook.lua`), in-game additions (`tail_game.lua`),
  adjustments around the controller patch's Instant Action screen (`alt_wrap.lua`)
- `compat/xboxpicker/` – the Xbox class picker (`buildscreen.lua`, `xboxflow.lua`, `ring.lua`, `cpselect.lua`)
- class and skin tables are read from the player's side files and the Remaster's skin changer
  (`sideclasses.py`, `skins.py`), the carousel models re-textured per skin (`xbring_variants.py`)
- the Xbox HUD comes from the player's disc image (`xiso.py`) and is laid out for the PC (`hudmerge.py`, `hudfix.py`)
- `BattlefrontII.exe` patches (class lock / hero checks, map hiding, inline icons, default keys):
  `exepatch.py`, `hudevent_cave.py`; `rep.lvl` fix: `sidepatch.py`; profile keys: `profkeys.py`
- `installer/Install.cs` – installer/uninstaller (backs up everything it changes)

## Build the release package

```bash
python tools/exepatch.py apply <patches>     # on a stock Steam exe; package.py diffs it against the original
python tools/package.py 1.0 --public         # -> dist/SWBF2-XboxEdition-1.0-public.zip
```
`package.py` downloads the bundled tools (Python 3.12 embeddable, 7-Zip `7zr.exe`) from their official sites.

## Developing

`tools/build.py --rem <Remaster data\_lvl_pc> --remhud <Remaster hud_16x09.lvl> --game <GameData> --ctrl
<controller patch GameData> [--xbox-ingame <Xbox ingame.lvl>] --out <dir>` builds the files; `tools/safetest.sh`
runs the game windowed with test files and takes screenshots; `tools/mkprobe.sh` / `tools/testshell.py` build test
variants (see their headers).

## License

This mod's code: MIT (`LICENSE`). Bundled: Lua 5.0.2 (MIT), Python 3.12 (PSF), 7-Zip `7zr.exe` (LGPL) – see
`installer/THIRD-PARTY-NOTICES.txt`. Star Wars Battlefront II, the Battlefront II Remaster, the UOP controller
patch and the Unofficial Patch belong to their owners and are not part of this repository.

Credits: Battlefront II Remaster by Anakin and its contributors; UOP controller patch by BAD-AL; Unofficial Patch
by Zerted.
