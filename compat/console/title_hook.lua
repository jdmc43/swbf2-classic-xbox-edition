------------------------------------------------------------------
-- Console look (personal use): console title colour (yellow), as on Xbox/PS2 and in the
-- controller patch. interface_util sets PC titles to black; override right after it loads.
-- Note: pass exactly the received arguments on (the exe crashes on explicit trailing nils).
------------------------------------------------------------------
local xbc_DoFile = ScriptCB_DoFile
ScriptCB_DoFile = function(name, ...)
	local r = { xbc_DoFile(name, unpack(arg)) }
	if name == "interface_util" then
		gTitleTextColor = { 246, 235, 20 }
	end
	return unpack(r)
end

