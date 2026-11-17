------------------------------------------------------------------
-- Instant Action (ALT) console screen of BAD-AL's controller patch (addon\000), run unchanged under the name
-- xbe_missionselect_console, with three adjustments made around it (no copy of its source needed):
--  * ScriptCB_SetSpectatorMode is not in the Steam exe: a no-op stand-in
--  * the screen had no background (black): the PC Instant Action background texture
--  * the Remaster rescales windows titled "ifs.missionselect.selectmode"/"selectera"/"playlist" (its own
--    screen); this screen's windows get a placeholder title while created, then their real one
------------------------------------------------------------------
if not ScriptCB_SetSpectatorMode then ScriptCB_SetSpectatorMode = function() end end

local XBE_TITLES = {
	["ifs.missionselect.selectmode"] = 1, ["ifs.missionselect.selectera"] = 1, ["ifs.missionselect.playlist"] = 1,
}
local xbe_NewIFShellScreen = NewIFShellScreen
local xbe_NewButtonWindow = NewButtonWindow

NewIFShellScreen = function(t)
	if type(t) == "table" and t.bAcceptIsSelect and t.movieBackground == "shell_main" and not t.bg_texture then
		t.bg_texture = "iface_bgmeta_space"
	end
	return xbe_NewIFShellScreen(t)
end

NewButtonWindow = function(t)
	local real = type(t) == "table" and XBE_TITLES[t.titleText] and t.titleText
	if real then t.titleText = "xbc_placeholder" end
	local w = xbe_NewButtonWindow(t)
	if real and type(w) == "table" and w.titleBarElement then w.titleBarElement.string = real end
	return w
end

ScriptCB_DoFile("xbe_missionselect_console")

NewIFShellScreen = xbe_NewIFShellScreen
NewButtonWindow = xbe_NewButtonWindow
