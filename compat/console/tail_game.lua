
------------------------------------------------------------------
-- (appended to game_interface, after the user scripts ran; game_interface itself runs inside the
-- mission's ScriptInit, via ReadDataFile("ingame.lvl"))
-- The Remaster skin changer applies the map's skin (SetClassProperty ... OverrideTexture) in its
-- ScriptPostLoad wrapper. Wrap outside it: afterwards, load the class picker ring's re-textured
-- models for the final class looks.
------------------------------------------------------------------
if ScriptPostLoad and not xbring_postwrapped then
	xbring_postwrapped = 1
	local xbring_ScriptPostLoad = ScriptPostLoad
	ScriptPostLoad = function(...)
		local r = { xbring_ScriptPostLoad(unpack(arg)) }
		if xbring_loadvariants then
			local ok, err = pcall(xbring_loadvariants)
			if not ok then XBRING_VERR = tostring(err) end
		end
		return unpack(r)
	end
end
