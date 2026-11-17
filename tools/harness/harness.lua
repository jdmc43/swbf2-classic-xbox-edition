-- Offline test bench for SWBF2 (2005) interface scripts. Lua 5.0 (tools/lua50.exe).
-- usage: lua50 harness.lua <prep_dir> [steps...]
--   steps: boot | shell | ingame | frames=N | accept | back | start | up | down | left | right
--          push=<screen> | call=<global> | verbose | quiet | platform=<PC|XBox>
-- Engine functions are stand-ins (only for names the PC exe registers); screens are simulated.

local DIR = arg[1]
dofile(DIR .. "/engine_names.lua")

local VERBOSE = false
local TIME = 0
local STACK = {}
local SCREENS = {}
local ERRORS = 0
local PLATFORM = "PC"

local function out(...)
	local t = {}
	local i
	for i = 1, table.getn(arg) do t[i] = tostring(arg[i]) end
	io.write(table.concat(t, " "), "\n")
end

local function argstr(a)
	local t = {}
	local i
	for i = 1, table.getn(a) do
		local v = a[i]
		if type(v) == "string" then t[i] = string.format("%q", v) else t[i] = tostring(v) end
	end
	return table.concat(t, ", ")
end

local RECENT = {}
local function remember(s)
	table.insert(RECENT, s)
	if table.getn(RECENT) > 6 then table.remove(RECENT, 1) end
end

local function safecall(what, f, ...)
	local a = arg
	local ok, err = xpcall(function() return f(unpack(a)) end, debug.traceback)
	if not ok then
		ERRORS = ERRORS + 1
		local lines = {}
		local l
		for l in string.gfind(tostring(err), "[^\n]+") do
			if not string.find(l, "harness.lua") and not string.find(l, "tail call") and not string.find(l, "xpcall") then
				table.insert(lines, l)
			end
		end
		out("[ERROR] in " .. what .. ": " .. table.concat(lines, " | ", 1, math.min(4, table.getn(lines))))
		out("        recent engine calls: " .. table.concat(RECENT, "; "))
	end
	return ok
end

-- ---------------------------------------------------------------- engine stand-ins
local SPECIAL = {
	ScriptCB_GetPlatform = function() return PLATFORM end,
	ScriptCB_GetOnlineService = function() return "GameSpy" end,
	ScriptCB_GetLanguage = function() return "english", 0 end,
	ScriptCB_GetScreenInfo = function() return 1920, 1080, 1, 1.7777 end,
	ScriptCB_GetSafeScreenInfo = function() return 1728, 972, 1 end,
	ScriptCB_GetFontHeight = function() return 16 end,
	ScriptCB_GetNumControllers = function() return 1 end,
	ScriptCB_getlocalizestr = function(s) return s end,
	ScriptCB_tounicode = function(s) return s end,
	ScriptCB_ununicode = function(s) return s end,
	ScriptCB_usprintf = function(f) return f end,
	ScriptCB_random = function(a) return a or 0 end,
	ScriptCB_IsFileExist = function() return 0 end,
	ScriptCB_GetMissionTime = function() return TIME end,
	ScriptCB_GetCurrentProfileName = function() return "Player" end,
	ScriptCB_GetCurrentPCTitleVersion = function() return "test" end,
	ScriptCB_ShouldShowLegal = function() return 1 end,
}

local function default_return(name)
	local short = string.gsub(name, "^%w+_", "")
	if string.find(short, "^Is") or string.find(short, "^Has") or string.find(short, "^Should")
		or string.find(short, "^Can") or string.find(short, "^Check") or string.find(short, "^Did") then
		return nil
	end
	if string.find(short, "^Get") or string.find(short, "Num") or string.find(short, "Count") then
		return 0
	end
	return nil
end

local WATCH = { ScriptCB_PushScreen = 1, ScriptCB_PopScreen = 1, ScriptCB_SetIFScreen = 1,
	ReadDataFile = 1, ScriptCB_EnterMission = 1, ScriptCB_QuitToWindows = 1 }

local function make_stub(name)
	return function(...)
		local desc = name .. "(" .. argstr(arg) .. ")"
		remember(desc)
		if VERBOSE or WATCH[name] then out("  [call] " .. desc) end
		if SPECIAL[name] then return SPECIAL[name](unpack(arg)) end
		return default_return(name)
	end
end

-- ---------------------------------------------------------------- screen system
local function top() return STACK[table.getn(STACK)] end

local function resolve(name)
	local s = SCREENS[name]
	if not s and type(rawget(_G, name)) == "table" then s = rawget(_G, name) end
	return s
end

local function enter(name, bFwd)
	local s = resolve(name)
	if not s then
		ERRORS = ERRORS + 1
		out("[ERROR] screen '" .. tostring(name) .. "' was never registered (AddIFScreen)")
		return
	end
	out("[screen] -> " .. name .. "   (stack: " .. table.concat(STACK, " > ") .. ")")
	if s.Enter then safecall(name .. ".Enter", s.Enter, s, bFwd) end
end

local function leave(name, bFwd)
	local s = resolve(name)
	if s and s.Exit then safecall(name .. ".Exit", s.Exit, s, bFwd) end
end

SPECIAL.AddIFScreen = function(tbl, name)
	if VERBOSE then out("  [register] " .. tostring(name)) end
	SCREENS[name] = tbl
	if type(tbl) == "table" then tbl.__harness_name = name end
end
SPECIAL.ScriptCB_PushScreen = function(name)
	local cur = top()
	if cur then leave(cur, true) end
	table.insert(STACK, name)
	enter(name, true)
end
SPECIAL.ScriptCB_SetIFScreen = function(name)
	local cur = top()
	if cur then leave(cur, true) end
	STACK = { name }
	enter(name, true)
end
SPECIAL.ScriptCB_PopScreen = function(name)
	local cur = table.remove(STACK)
	if cur then leave(cur, nil) end
	if name and SCREENS[name] then
		while table.getn(STACK) > 0 and top() ~= name do table.remove(STACK) end
	end
	local nxt = top()
	if nxt then enter(nxt, nil) end
end

-- data files: check that every ReadDataFile path exists in the real game folder
SPECIAL.ReadDataFile = function(path)
	if type(path) ~= "string" or not GAMEDATA then return end
	local first = string.gsub(path, ";.*$", "")          -- "file.lvl;sub" -> "file.lvl"
	local rel = string.gsub(first, "\\", "/")
	local full
	if string.find(rel, "^%.%./%.%./") then
		full = GAMEDATA .. "/" .. string.sub(rel, 7)
	elseif string.find(rel, "^dc:") then
		return
	else
		full = GAMEDATA .. "/data/_lvl_pc/" .. rel
	end
	local f = io.open(full, "rb")
	if f then f:close() else
		ERRORS = ERRORS + 1
		out("[ERROR] ReadDataFile: file not found: " .. path .. "  (" .. full .. ")")
	end
end

-- ---------------------------------------------------------------- script loading
SPECIAL.ScriptCB_DoFile = function(name)
	local path = DIR .. "/scripts/" .. string.lower(name) .. ".luac"
	local chunk, err = loadfile(path)
	if not chunk then
		ERRORS = ERRORS + 1
		out("[ERROR] script '" .. tostring(name) .. "' not found in any loaded lvl")
		return
	end
	if VERBOSE then out("  [dofile] " .. name) end
	safecall("script " .. name, chunk)
end

setmetatable(_G, {
	__index = function(t, k)
		-- engine *variables* (gDemoBuild, ...) are off/nil in the retail game; only stub functions
		if type(k) == "string" and string.find(k, "^g[A-Z]") and not SPECIAL[k] then return nil end
		if SPECIAL[k] or ENGINE[k] then
			local f = make_stub(k)
			rawset(t, k, f)
			return f
		end
		return nil
	end,
	-- record screen tables when the scripts define their Lua-side AddIFScreen helper
	__newindex = function(t, k, v)
		if k == "AddIFScreen" and type(v) == "function" then
			local orig = v
			v = function(tbl, name, ...)
				if VERBOSE then out("  [register] " .. tostring(name)) end
				SCREENS[name] = tbl
				return orig(tbl, name, unpack(arg))
			end
		end
		rawset(t, k, v)
	end,
})
print = function(...) if VERBOSE then out("  [print] " .. argstr(arg)) end end

-- ---------------------------------------------------------------- steps
local INPUTS = { accept = "Input_Accept", back = "Input_Back", start = "Input_Start",
	up = "Input_GeneralUp", down = "Input_GeneralDown", left = "Input_GeneralLeft", right = "Input_GeneralRight" }

local function frames(n)
	local i
	for i = 1, n do
		TIME = TIME + 0.05
		local name = top()
		local s = name and SCREENS[name]
		if s and s.Update then
			if not safecall(name .. ".Update", s.Update, s, 0.05) then return end
		end
	end
end

local i
for i = 2, table.getn(arg) do
	local step = arg[i]
	local k, v = string.match and string.match(step, "^(%w+)=(.*)$")
	if not k then
		local a, b = string.find(step, "=")
		if a then k = string.sub(step, 1, a - 1); v = string.sub(step, a + 1) end
	end
	if step == "verbose" then VERBOSE = true
	elseif step == "quiet" then VERBOSE = false
	elseif k == "platform" then PLATFORM = v
	elseif step == "shell" or step == "boot" then
		out("== boot shell")
		ScriptCB_DoFile("shell_interface")
		if step == "boot" and not top() then ScriptCB_PushScreen("ifs_boot") end
	elseif step == "ingame" then
		out("== load ingame")
		ScriptCB_DoFile("game_interface")
	elseif k == "exec" then
		local f, e = loadstring(v)
		if f then safecall("exec", f) else out("[ERROR] exec: " .. tostring(e)) end
	elseif k == "frames" then frames(tonumber(v))
	elseif k == "push" then ScriptCB_PushScreen(v)
	elseif k == "call" then safecall(v, _G[v])
	elseif INPUTS[step] then
		local name = top()
		local s = name and resolve(name)
		out("[input] " .. step .. " on " .. tostring(name))
		if s and s[INPUTS[step]] then safecall(name .. "." .. INPUTS[step], s[INPUTS[step]], s)
		else out("  (screen has no " .. INPUTS[step] .. ")") end
	else
		out("unknown step " .. step)
	end
end
out(string.format("== done: top screen %s, %d error(s)", tostring(top()), ERRORS))
