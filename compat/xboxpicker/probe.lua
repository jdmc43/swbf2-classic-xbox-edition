
-- PROBE (debug build only): shows on screen what the engine tells the script, so we can
-- learn whether the selected class can be tracked and which inputs reach this screen.
xbp_events = {}
function xbp_log(s)
	table.insert(xbp_events, 1, s)
	while table.getn(xbp_events) > 8 do table.remove(xbp_events) end
end

local xbp_BuildScreen = ifs_pc_SpawnSelect_fnBuildScreen
ifs_pc_SpawnSelect_fnBuildScreen = function(this, mode)
	xbp_BuildScreen(this, mode)
	local w,h = ScriptCB_GetSafeScreenInfo()
	this.Dbg = NewIFContainer { ScreenRelativeX = 0.0, ScreenRelativeY = 0.0 }
	this.Dbg.Text = NewIFText {
		x = 10, y = 8, halign = "left", valign = "top",
		textw = w * 0.95, texth = h * 0.1,
		font = "gamefont_tiny", ColorR = 255, ColorG = 255, ColorB = 0,
		flashy = 0, nocreatebackground = 1, ZPos = 0,
	}

	local function wrap(name)
		local orig = this[name]
		this[name] = function(t, a, b, c)
			xbp_log(name .. (a ~= nil and ("(" .. tostring(a) .. ")") or ""))
			if orig then return orig(t, a, b, c) end
		end
	end
	wrap("Input_Accept") wrap("Input_Back") wrap("Input_Start") wrap("Input_Misc") wrap("Input_Misc2")
	wrap("Input_GeneralUp") wrap("Input_GeneralDown") wrap("Input_GeneralLeft") wrap("Input_GeneralRight")
	wrap("Input_LTrigger") wrap("Input_RTrigger") wrap("Input_KeyDown")

	local origMouse = this.HandleMouse
	this.HandleMouse = function(t, x, y)
		xbp_mx, xbp_my = x, y
		if origMouse then return origMouse(t, x, y) end
	end
end

local xbp_Update = ifs_pc_SpawnSelect.Update
ifs_pc_SpawnSelect.Update = function(this, fDt)
	xbp_Update(this, fDt)
	if not this.Dbg then return end
	local ok1, cls = pcall(GetCharacterClass, 0)
	local ok2, team = pcall(GetCharacterTeam, 0)
	local vis = ""
	local i
	for i = 0, 10 do
		local s = this.Info and this.Info["SlotWindow" .. i]
		if s then vis = vis .. ((IFObj_fnGetVis(s) and "1") or "0") else vis = vis .. "-" end
	end
	local line = string.format("PROBE cls=%s team=%s n=%s/%s vis=%s mouse=%s,%s cur=%s | %s",
		tostring(cls), tostring(team), tostring(GetTeamClassCount(1)), tostring(GetTeamClassCount(2)), vis,
		tostring(xbp_mx and math.floor(xbp_mx)), tostring(xbp_my and math.floor(xbp_my)), tostring(this.CurButton),
		table.concat(xbp_events, " "))
	if line ~= this.xbp_last then
		this.xbp_last = line
		IFText_fnSetUString(this.Dbg.Text, ScriptCB_tounicode(line))
	end
end

-- PROBE 2: capture class names from the mission's AddUnitClass calls (if this runs before the mission)
xbp_classes = xbp_classes or { [1] = {}, [2] = {} }
if AddUnitClass and not xbp_wrapped then
	xbp_wrapped = 1
	local xbp_AddUnitClass = AddUnitClass
	AddUnitClass = function(team, cls, a, b, c)
		if xbp_classes[team] then table.insert(xbp_classes[team], cls) end
		return xbp_AddUnitClass(team, cls, a, b, c)
	end
end

local xbp_Build2 = ifs_pc_SpawnSelect_fnBuildScreen
ifs_pc_SpawnSelect_fnBuildScreen = function(this, mode)
	xbp_Build2(this, mode)
	local prevKey = this.Input_KeyDown
	this.Input_KeyDown = function(t, key, a, b)
		if prevKey then prevKey(t, key, a, b) end
		local ok, cls = pcall(GetCharacterClass, 0)
		local _, team = pcall(GetCharacterTeam, 0)
		local n = GetTeamClassCount(team or 1) or 1
		cls = tonumber(cls) or 0
		local nxt = math.mod(cls + 1, math.max(n, 1))
		if key == 113 or key == 81 then -- q: select by index
			local r1, r2 = pcall(SelectCharacterClass, 0, nxt)
			xbp_log("SEL#" .. nxt .. ":" .. tostring(r1) .. "," .. tostring(r2))
		elseif key == 103 or key == 71 then -- g: move Spawn button under the cursor
			local w,h = ScriptCB_GetSafeScreenInfo()
			local r1, r2 = pcall(IFObj_fnSetPos, t.Info.Ok, w * 0.5, h * 0.5)
			xbp_log("OKMOVE:" .. tostring(r1) .. "," .. tostring(r2))
		elseif key == 101 or key == 69 then -- e: select by captured name
			local list = xbp_classes[team or 1] or {}
			local name = list[nxt + 1]
			local r1, r2 = pcall(SelectCharacterClass, 0, name)
			xbp_log("SELN:" .. tostring(name) .. ":" .. tostring(r1) .. "," .. tostring(r2))
		end
	end
end

local xbp_Update2 = ifs_pc_SpawnSelect.Update
ifs_pc_SpawnSelect.Update = function(this, fDt)
	xbp_Update2(this, fDt)
	if this.Dbg and not this.xbp_names_shown then
		this.xbp_names_shown = 1
		xbp_log("names1=" .. table.getn(xbp_classes[1]) .. ":" .. tostring(xbp_classes[1][1]) .. " names2=" .. table.getn(xbp_classes[2]))
	end
end

-- PROBE 3 (test only): giant Spawn button so a click anywhere spawns
if XBP_GIANT_OK then
	local xbp_Build3 = ifs_pc_SpawnSelect_fnBuildScreen
	ifs_pc_SpawnSelect_fnBuildScreen = function(this, mode)
		xbp_Build3(this, mode)
		local w,h = ScriptCB_GetSafeScreenInfo()
		this.Info.Ok.label.fHotspotW = w * 2
		this.Info.Ok.label.fHotspotH = h * 2
		this.Info.Ok.label.fHotspotX = -w
		this.Info.Ok.label.fHotspotY = -h
		this.Info.Ok.x = -10000 -- parked off-screen until G
	end
end

-- PROBE 4 (test only): does hovering a slot select it?
if XBP_HOVER then
	local xbp_Build4 = ifs_pc_SpawnSelect_fnBuildScreen
	ifs_pc_SpawnSelect_fnBuildScreen = function(this, mode)
		xbp_Build4(this, mode)
		local w,h = ScriptCB_GetSafeScreenInfo()
		local i
		for i = 0, 10 do
			local s = this.Info["SlotWindow" .. i]
			s.fHotspotX = -w * 2
			s.fHotspotY = -h * 2
			s.fHotspotW = w * 4
			s.fHotspotH = h * 4
		end
		local prev = this.Input_KeyDown
		this.Input_KeyDown = function(t, key, a, b)
			if prev then prev(t, key, a, b) end
			if key == 106 or key == 74 then -- j: keep only slot 2
				for i = 0, 10 do
					if i ~= 2 then IFObj_fnSetPos(t.Info["SlotWindow" .. i], -10000, 0) end
				end
				IFObj_fnSetPos(t.Info.SideIcon0, -10000, 0)
				IFObj_fnSetPos(t.Info.SideIcon1, -10000, 0)
				xbp_log("ONLY2")
			elseif key == 104 or key == 72 then -- h: slot 2 away, giant Spawn in
				IFObj_fnSetPos(t.Info["SlotWindow2"], -10000, 0)
				IFObj_fnSetPos(t.Info.Ok, w * 0.5, h * 0.5)
				xbp_log("OKIN")
			end
		end
	end
end

-- PROBE 5: ring skins - per team-1 class: ring mesh / captured tex1 (replaces the probe line)
local xbp_Update5 = ifs_pc_SpawnSelect.Update
ifs_pc_SpawnSelect.Update = function(this, fDt)
	xbp_Update5(this, fDt)
	if XBP_HUDEVERY and this.xbStage == 1 and GetTimerRate then
		if XBP_USEMHCP then MapHideCommandPosts(1) else GetTimerRate(XBP_HUDEVERY) end
		if XBP_HUDNAMES then
			local _, nm
			for _, nm in ipairs(XBP_HUDNAMES) do GetTimerRate(nm, 0) end
		end
	end
	if this.Dbg then
		local function nret(...) return arg.n end
		local l, t, r, b = IFText_fnGetDisplayRect(this.Info.UnitCount)
		local l0, t0, r0, b0 = IFText_fnGetDisplayRect(this.Info.XbMeasure)
		local lk = ""
		local i
		for i = 0, (this.xbN or 1) - 1 do lk = lk .. ((this.xbLock and this.xbLock[i]) and "L" or "-") end
		local s = string.format("UC %.0f,%.0f,%.0f,%.0f M %.0f,%.0f,%.0f,%.0f lk=%s scan=%s", l or -9, t or -9, r or -9, b or -9,
			l0 or -9, t0 or -9, r0 or -9, b0 or -9, lk, tostring(this.xbScan ~= nil)) .. " H" .. tostring(XBPICK_HUDEVOK) .. " n" .. tostring(GetTimerRate and nret(pcall(GetTimerRate, 0))) .. " st" .. tostring(this.xbStage) .. " V" .. tostring(XBRING_VNEED) .. " m" .. tostring(XBRING_VMISS) .. " e" .. tostring(XBRING_VERR) .. " w" .. tostring(xbring_postwrapped) .. " |"
		local k, cls
		for k, cls in ipairs((xbpick_classes and xbpick_classes[2]) or {}) do
			local c = string.lower(cls)
			if string.len(s) < 150 then
				s = s .. " " .. string.gsub(string.gsub(c, "^%a+_inf_", ""), "ep3_", "") .. "=" .. tostring(XBRING_VMESH and XBRING_VMESH[c])
					.. "/" .. tostring(XBRING_TEX1 and XBRING_TEX1[c])
			end
		end
		IFText_fnSetUString(this.Dbg.Text, ScriptCB_tounicode(s))
	end
end

-- PROBE 6: hero slot (XBP_HERO)
if XBP_HERO then
	local xbp_Update6 = ifs_pc_SpawnSelect.Update
	ifs_pc_SpawnSelect.Update = function(this, fDt)
		xbp_Update6(this, fDt)
		if not this.Dbg then return end
		local ok1, cls = pcall(GetCharacterClass, 0)
		local ok2, team = pcall(GetCharacterTeam, 0)
		local vis = ""
		local i
		for i = 0, 10 do
			local s = this.Info and this.Info["SlotWindow" .. i]
			if s then vis = vis .. ((IFObj_fnGetVis(s) and "1") or "0") else vis = vis .. "-" end
		end
		local sw = this.Info.SlotWindow10
		local function wd(o) if not o then return "-" end local l,t,r,b = IFText_fnGetDisplayRect(o) return string.format("%.0fx%.0f", (r or 0)-(l or 0), (b or 0)-(t or 0)) end
		local l9 = this.Info.SlotWindow0
		local okh, vh = pcall(GetTimerRate, 140)
		local lk = ""
		local k
		for k = 0, (this.xbN or 1) - 1 do lk = lk .. ((this.xbLock and this.xbLock[k]) and "L" or "-") end
		local lv = ""
		for k = 0, (this.xbN or 1) - 1 do local okv, v = pcall(GetTimerRate, 141, k) lv = lv .. tostring(v) end
		local s0 = "lv=" .. lv .. " lk=" .. lk .. " scan=" .. tostring(this.xbScan ~= nil) .. " CANHERO=" .. tostring(vh) .. " T10=" .. wd(sw and sw.titleBarElement) .. " I10=" .. wd(sw and sw.InfoText) .. " I0=" .. wd(l9 and l9.InfoText) .. " UC=" .. wd(this.Info.UnitCount) .. " "
		local s = s0 .. string.format("HERO h=%s/%s n=%s/%s vis=%s cls=%s team=%s xbN=%s idx=%s slots=%s",
			tostring(xbpick_heroes and xbpick_heroes[1]), tostring(xbpick_heroes and xbpick_heroes[2]),
			tostring(GetTeamClassCount(1)), tostring(GetTeamClassCount(2)), vis, tostring(cls), tostring(team),
			tostring(this.xbN), tostring(this.xbIdx), this.xbSlots and table.concat(this.xbSlots, ",") or "nil")
		IFText_fnSetUString(this.Dbg.Text, ScriptCB_tounicode(s))
	end
end
