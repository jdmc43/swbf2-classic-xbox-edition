------------------------------------------------------------------
-- Controller layer for the PC menus (personal use).
-- Steam Input sends keyboard/mouse: A = Space+Enter, B = Alt+C, d-pad = F1/F2/F4/R, left stick = WASD,
-- right stick = mouse. The PC menus are "focus follows mouse": gHandleMouse clears the focused button
-- every update, so keyboard/controller focus never sticks. This layer:
--  * pad mode: while the mouse doesn't move, skip gHandleMouse (controller focus stays); moving the
--    mouse (or the right stick) switches back to normal mouse behaviour
--  * on every screen/popup: C (B button) = Back, d-pad = directions, R = down
--  * ignores the Space "Misc" event that arrives with A's Enter (no double action)
-- Note: pass exactly the received arguments on (the exe crashes on explicit trailing nils).
------------------------------------------------------------------
xbc_pad = 1
xbc_frame = 0 -- advanced every frame by the mouse/update hooks below

local function xbc_now()
	if ScriptCB_GetMissionTime then
		local ok, t = pcall(ScriptCB_GetMissionTime)
		if ok and tonumber(t) then return tonumber(t) end
	end
	return 0
end

-- tab rows (Remaster/PC menus): X/Y = previous/next top tab, LB/RB = previous/next sub tab.
-- Never lands on the window's minimise/quit "tabs".
local XBC_SKIPTABS = { _tab_mini = 1, _tab_quit = 1 }
function xbc_tab(this, row, dir)
	local L = this._xbcLayouts and this._xbcLayouts[row + 1]
	local T = (row == 0) and this._Tabs or this["_Tabs" .. row]
	if type(L) ~= "table" or type(T) ~= "table" then return nil end
	local n = table.getn(L)
	if n < 2 then return nil end
	local cur = 0
	local i
	for i = 1, n do
		local tab = T[L[i].tag]
		if tab and tab.bSelected then cur = i end
	end
	local j
	for j = 1, n - 1 do
		local idx = math.mod(cur - 1 + dir * j + n * 4, n) + 1
		local tag = L[idx].tag
		local tab = T[tag]
		if tab and not XBC_SKIPTABS[tag] and not tab.hidden and not tab.bDimmed and IFObj_fnGetVis(tab) then
			xbc_pad = 1
			this.CurButton = tag
			if gCurScreenTable then gCurScreenTable.CurButton = tag end
			if this.Input_Accept then this:Input_Accept() end
			return 1
		end
	end
	return nil
end
local XBC_TABKEYS = { [113] = { 0, -1 }, [81] = { 0, -1 }, [101] = { 0, 1 }, [69] = { 0, 1 }, [50] = { 1, -1 }, [49] = { 1, 1 } }

local XBC_DIRS = { [-59] = "Input_GeneralLeft", [-60] = "Input_GeneralRight", [-62] = "Input_GeneralUp", [114] = "Input_GeneralDown" }

-- (re)wrap a screen's Input_KeyDown; mods sometimes replace it after the screen was created
function xbc_wrapkeys(t)
	if t.Input_KeyDown and t.Input_KeyDown == t.xbcKD then return end
	local kd = t.Input_KeyDown
	t.xbcKD = function(this, key, ...)
		if xbc_keylog then xbc_keylog(this, key) end -- debug probes only
		if key == 32 or key == 13 then xbc_keyF = xbc_frame end -- A (Space+Enter): keyboard accept
		if not gCurEditbox then
			-- A sends Space+Enter: Space arrives first and some screens accept on it, so A would
			-- act twice. In pad mode Enter does the accepting; Space is ignored.
			if key == 32 and xbc_pad then return end
			-- B button = Alt+C. 'c' is Back everywhere; on screens that ask for it (the console
			-- Instant Action screen) Alt is Back too, in case only one half arrives. One press = one Back.
			if key == 99 or key == 67 or (key == -56 and this.xbcAltBack) then
				xbc_pad = 1
				local bk = (key == -56) and "alt" or "c"
				if xbc_backF and xbc_frame - xbc_backF <= 6 and xbc_backK ~= bk then
					xbc_backF = nil -- the other half of the same press
					return
				end
				xbc_backF = xbc_frame
				xbc_backK = bk
				if this.Input_Back then this:Input_Back() end
				return
			end
			local tk = XBC_TABKEYS[key]
			if tk and xbc_tab(this, tk[1], tk[2]) then return end
			local dir = XBC_DIRS[key]
			if dir then
				xbc_pad = 1 -- a controller direction switches to pad mode even if the screen ignores it
				if this[dir] then this[dir](this) end
				return
			end
		end
		if kd then return kd(this, key, unpack(arg)) end
	end
	t.Input_KeyDown = t.xbcKD
end

function xbc_wrap(t, name)
	if type(t) ~= "table" or t.xbcWrapped then return end
	if name == "ifs_pc_SpawnSelect" then return end -- has its own controller handling
	t.xbcWrapped = 1
	if name == "ifs_missionselect_console" then
		t.xbcAltBack = 1
		-- it switches on console-style "read all controllers" input, which no other PC menu uses
		local en = t.Enter
		if en then
			t.Enter = function(this, ...)
				local r = { en(this, unpack(arg)) }
				if ScriptCB_ReadAllControllers then pcall(ScriptCB_ReadAllControllers, nil) end
				return unpack(r)
			end
		end
	end

	xbc_wrapkeys(t)

	local d
	for _, d in ipairs({ "Input_GeneralUp", "Input_GeneralDown", "Input_GeneralLeft", "Input_GeneralRight" }) do
		local f = t[d]
		if f then
			t[d] = function(this, ...)
				xbc_pad = 1
				return f(this, unpack(arg))
			end
		end
	end

	local acc = t.Input_Accept
	if acc then
		t.Input_Accept = function(this, ...)
			-- A sends Space+Enter and the engine can turn both into Accept in the same frame:
			-- act on the first one only (a second Accept within a few frames is dropped, once)
			if xbc_accF and xbc_frame - xbc_accF <= 4 and not xbc_accDup then
				xbc_accDup = 1
				return
			end
			xbc_accF = xbc_frame
			xbc_accDup = nil
			xbc_acceptT = xbc_now()
			-- focus follows the mouse: a cursor that drifted off the buttons clears the focus and A
			-- would do nothing. Not over a list either -> give A the last focused button back.
			if not this.CurButton and this.xbcLastBtn and xbc_keyF and xbc_frame - xbc_keyF <= 2
				and not gMouseListBox and not gMouseListBoxSlider
				and not gCurEditbox and not this.xbcNoRestore then
				xbc_pad = 1
				this.CurButton = this.xbcLastBtn
				if gCurScreenTable == this and SetCurButton then pcall(SetCurButton, this.xbcLastBtn) end
			end
			return acc(this, unpack(arg))
		end
	end
	-- Misc/Misc2 come from Space (A) and 1/2 (RB/LB) in the Steam layout: spurious in pad mode
	local m
	for _, m in ipairs({ "Input_Misc", "Input_Misc2" }) do
		local f = t[m]
		if f then
			t[m] = function(this, ...)
				if xbc_pad and not gCurEditbox then return end
				return f(this, unpack(arg))
			end
		end
	end
end

------------------------------------------------------------------
-- End-of-match stats on the controller (the PC screens only act on the button under the mouse): the
-- console behaviour these scripts were written for: A = the right button, B = the left one, shown with the
-- console icons. Team stats: A = Personal Stats of the selected player, B (or X) = Done; personal stats:
-- A = Career Stats (human players, else back), B = Back; career stats: A = Done, B = Back; awards: A = back.
------------------------------------------------------------------
local function xbc_iconlabel(btn, icon, key)
	if not btn or not RoundIFButtonLabel_fnSetUString or not ScriptCB_UnicodeStrCat then return end
	local ok, u = pcall(ScriptCB_getlocalizestr, key)
	if ok and u then
		pcall(RoundIFButtonLabel_fnSetUString, btn, ScriptCB_UnicodeStrCat(ScriptCB_tounicode(icon .. " "), u))
		if btn.label and IFText_fnSetTextBreak then pcall(IFText_fnSetTextBreak, btn.label, "none") end -- no wrap
	end
end

local function xbc_padaccept(t, fn)
	local acc = t.Input_Accept
	t.Input_Accept = function(this, ...)
		if xbc_pad and not this.CurButton and not gMouseListBox then
			if fn(this) then return end
		end
		if acc then return acc(this, unpack(arg)) end
	end
end

function xbc_statspad(name)
	local t = _G and _G[name]
	if type(t) ~= "table" or t.xbcStats then return end
	t.xbcStats = 1
	local en = t.Enter
	if name == "ifs_teamstats" then
		xbc_padaccept(t, function(this) this.CurButton = "details" end)
		local kd = t.Input_KeyDown
		t.Input_KeyDown = function(this, key, ...)
			if (key == 113 or key == 81) and xbc_pad and this.Input_Back then return this:Input_Back() end -- X (Q)
			if kd then return kd(this, key, unpack(arg)) end
		end
		t.Enter = function(this, ...)
			local r = {}
			if en then r = { en(this, unpack(arg)) } end
			xbc_iconlabel(this.quit, "{btnb}", "ifs.stats.done")
			xbc_iconlabel(this.buttonNextPage, "{btna}", "ifs.Stats.personalstatstitle")
			return unpack(r)
		end
	elseif name == "ifs_personalstats" then
		t.Enter = function(this, ...)
			local r = {}
			if en then r = { en(this, unpack(arg)) } end
			xbc_iconlabel(this.Helptext_Back, "{btnb}", "common.back")
			xbc_iconlabel(this.buttonsNextPage, "{btna}", "ifs.stats.careerstatstitle")
			return unpack(r)
		end
		xbc_padaccept(t, function(this)
			local ok, id = pcall(ScriptCB_GetPlayerIDAtRank, this.fTeam, this.fIdx)
			if ok and tonumber(id) and tonumber(id) >= 0 then
				this.CurButton = "nextPage"
			else
				this:Input_Back()
				return 1
			end
		end)
	elseif name == "ifs_careerstats" then
		t.Enter = function(this, ...)
			local r = {}
			if en then r = { en(this, unpack(arg)) } end
			xbc_iconlabel(this.Helptext_Back, "{btnb}", "common.back")
			xbc_iconlabel(this.quit, "{btna}", "ifs.stats.done")
			return unpack(r)
		end
		xbc_padaccept(t, function(this)
			if this.quit then this.CurButton = "quit" else this:Input_Back() return 1 end
		end)
	elseif name == "ifs_awardstats" then
		xbc_padaccept(t, function(this) this:Input_Back() return 1 end)
	end
end

local xbc_DoFile2 = ScriptCB_DoFile
ScriptCB_DoFile = function(name, ...)
	local r = { xbc_DoFile2(name, unpack(arg)) }
	if name == "ifs_teamstats" or name == "ifs_personalstats" or name == "ifs_careerstats" or name == "ifs_awardstats" then
		pcall(xbc_statspad, name)
	end
	if name == "interface_util" and AddIFScreen and not xbc_hookedAdd then
		xbc_hookedAdd = 1
		local add = AddIFScreen
		AddIFScreen = function(t, n, ...)
			pcall(xbc_wrap, t, n)
			return add(t, n, unpack(arg))
		end
		if CreatePopupInC then
			local pop = CreatePopupInC
			CreatePopupInC = function(t, n, ...)
				pcall(xbc_wrap, t, n)
				return pop(t, n, unpack(arg))
			end
		end
	elseif name == "ifelem_shellscreen" and gIFShellScreenTemplate_fnUpdate and not xbc_hookedUpd then
		xbc_hookedUpd = 1
		local upd = gIFShellScreenTemplate_fnUpdate
		gIFShellScreenTemplate_fnUpdate = function(this, ...)
			xbc_frame = xbc_frame + 1
			return upd(this, unpack(arg))
		end
	elseif name == "ifelem_tabmanager" and ifelem_tabmanager_Create and not xbc_hookedTabs then
		xbc_hookedTabs = 1
		local cr = ifelem_tabmanager_Create
		ifelem_tabmanager_Create = function(this, a0, a1, a2, a3)
			this._xbcLayouts = { a0, a1, a2, a3 }
			-- pass on exactly as many layouts as were given (no trailing nils)
			if a3 then return cr(this, a0, a1, a2, a3)
			elseif a2 then return cr(this, a0, a1, a2)
			elseif a1 then return cr(this, a0, a1)
			else return cr(this, a0) end
		end
	elseif name == "ifutil_mouse" and gHandleMouse and not xbc_hookedMouse then
		xbc_hookedMouse = 1
		local hm = gHandleMouse
		gHandleMouse = function(this, x, y, ...)
			xbc_frame = xbc_frame + 1
			if type(this) == "table" and this.xbcWrapped then
				xbc_wrapkeys(this)
				if this.CurButton then this.xbcLastBtn = this.CurButton end
			end
			if xbc_mx and x and y then
				-- small drift of the right stick (mouse) does not count as using the mouse
				if math.abs(x - xbc_mx) + math.abs(y - xbc_my) > 6 then xbc_pad = nil end
			end
			xbc_mx, xbc_my = x, y
			if xbc_pad then
				-- gHandleMouse would clear these every frame: stale mouse-over state would make A
				-- click a list/scrollbar the cursor once hovered instead of the focused item
				gMouseListBox = nil
				gMouseListBoxSlider = nil
				gMouseOverEditbox = nil
				return
			end
			return hm(this, x, y, unpack(arg))
		end
	end
	return unpack(r)
end

------------------------------------------------------------------
-- HUD variant: outside the campaign load hud_16x09_ia.lvl (no objective list: the Xbox class picker has
-- none, and Instant Action needs none). The Remaster reads its HUD through ReadDataFile from game_interface.
------------------------------------------------------------------
if ReadDataFile and not xbc_wrappedRDF then
	xbc_wrappedRDF = 1
	local xbc_RDF = ReadDataFile
	ReadDataFile = function(path, ...)
		if type(path) == "string" and string.find(string.lower(path), "hud\\hud_16x09%.lvl$") then
			local ok, camp = pcall(IsCampaign)
			if not (ok and camp) and ScriptCB_IsFileExist and ScriptCB_IsFileExist(string.gsub(path, "%.lvl$", "_ia.lvl")) ~= 0 then
				path = string.gsub(path, "%.lvl$", "_ia.lvl")
			end
		end
		return xbc_RDF(path, unpack(arg))
	end
end

------------------------------------------------------------------
-- Class model overrides (map/legion skins): the Remaster's skin changer and mission scripts call
-- SetClassProperty(class, "GeometryName", mesh). Remember them so the class picker's 3D ring shows
-- the same models as the map. Installed before user scripts / mission scripts run.
------------------------------------------------------------------
XBRING_GEOM = XBRING_GEOM or {}
XBRING_TEX1 = XBRING_TEX1 or {} -- OverrideTexture / OverrideTexture2 (skin changer colours)
XBRING_TEX2 = XBRING_TEX2 or {}
if SetClassProperty and not xbring_wrappedSCP then
	xbring_wrappedSCP = 1
	local xbring_SCP = SetClassProperty
	SetClassProperty = function(cls, prop, val, ...)
		if type(cls) == "string" and type(prop) == "string" and type(val) == "string" then
			local p = string.lower(prop)
			if p == "geometryname" then
				XBRING_GEOM[string.lower(cls)] = val
				XBRING_GEOMN = (XBRING_GEOMN or 0) + 1
			elseif p == "overridetexture" then
				XBRING_TEX1[string.lower(cls)] = val
			elseif p == "overridetexture2" then
				XBRING_TEX2[string.lower(cls)] = val
			end
		end
		return xbring_SCP(cls, prop, val, unpack(arg))
	end
end
