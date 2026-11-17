
-- Xbox-style class picker flow (personal use).
-- Stage 1 (Xbox ifs_charselect): one class window; left/right cycles; confirm = click/Enter
--   (the shown slot's click area covers the screen, so the engine selects that class).
-- Stage 2 (Xbox ifs_mapselect): window hidden, Spawn prompt; click/Enter right of the map spawns,
--   clicks on the map still pick a command post; left/right goes back to stage 1.

-- class names in slot order, captured from the mission's AddUnitClass calls (for the 3D preview)
xbpick_classes = { [1] = {}, [2] = {} }
if AddUnitClass and not xbpick_wrapped then
	xbpick_wrapped = 1
	local xbpick_AddUnitClass = AddUnitClass
	AddUnitClass = function(team, cls, a, b, c)
		if xbpick_classes[team] then table.insert(xbpick_classes[team], cls) end
		return xbpick_AddUnitClass(team, cls, a, b, c)
	end
end

-- hero class per team, captured from the mission's SetHeroClass calls
xbpick_heroes = xbpick_heroes or {}
if SetHeroClass and not xbpick_herowrapped then
	xbpick_herowrapped = 1
	local xbpick_SetHeroClass = SetHeroClass
	SetHeroClass = function(team, cls, a, b, c)
		xbpick_heroes[team] = cls
		return xbpick_SetHeroClass(team, cls, a, b, c)
	end
end

local function xbpick_str(obj, s)
	if obj then IFText_fnSetUString(obj, ScriptCB_tounicode(s)) end
end

-- Xbox class step has no map: shrink the HUD while choosing a class, restore it for the spawn step
-- and whenever the screen closes (the original value is kept, never guessed).
function xbpick_hud(this, show)
	if not XBPICK_HUDHIDE or not ScriptCB_SetHUDScale or not ScriptCB_GetHUDScale then return end
	if show then
		if xbpick_hudSaved then
			pcall(ScriptCB_SetHUDScale, xbpick_hudSaved)
			xbpick_hudSaved = nil
		end
	else
		if not xbpick_hudSaved then
			local ok, v = pcall(ScriptCB_GetHUDScale)
			if ok and tonumber(v) then xbpick_hudSaved = tonumber(v) end
		end
		if xbpick_hudSaved then pcall(ScriptCB_SetHUDScale, XBPICK_HUDHIDE) end
	end
end

-- HUD map switch (patched exe, tools/hudevent_cave.py): GetTimerRate(130) hides the player 1 HUD map,
-- GetTimerRate(131) shows it. GetTimerRate is unused by every script; unpatched it returns a value, patched
-- none - used to detect the patch. (The HUD's map key and objective text are moved off screen in the HUD file.)
local function xbpick_nret(...) return arg.n end
if XBPICK_HUDEVOK == nil and GetTimerRate then
	XBPICK_HUDEVOK = (xbpick_nret(pcall(GetTimerRate, 0)) == 1) and 1 or false
end
-- GetTimerRate(140) (patched exe) = the spawn display's own test "the local player may spawn as the hero"
-- (hero rules on, the team's hero unlocked and handed to this player). The exe keeps the hero slot visible
-- all the time, so its visibility says nothing.
function xbpick_canhero()
	if not XBPICK_HUDEVOK then return nil end
	local ok, v = pcall(GetTimerRate, 140)
	return (ok and tonumber(v) == 1) and 1 or nil
end

function xbpick_hudev(n)
	if XBPICK_HUDEVOK then pcall(GetTimerRate, n) end
end

-- Xbox class step: no map, team emblem or Back prompt; they return for the post step.
function xbpick_hudstage(this)
	local post = (this.xbStage == 2)
	xbpick_hudev(post and 131 or 130)
	local k, o
	for k, o in ipairs({ this.Info.SideModel0, this.Info.SideModel1, this.Info.SideIcon0, this.Info.SideIcon1 }) do
		IFObj_fnSetVis(o, post)
	end
	if this.Info.PromptB then
		IFObj_fnSetVis(this.Info.PromptB, post)
		IFObj_fnSetVis(this.Info.PromptBText, post)
	end
end

function xbpick_layout(this)
	local xb = this.xb
	if not xb then return end
	xbpick_hudstage(this)
	if xbring_layout then xbring_layout(this) end
	local i
	for i = 0, 10 do
		local s = this.Info["SlotWindow" .. i]
		if s then
			if this.xbStage == 1 and i == xbpick_slot(this) then
				IFObj_fnSetPos(s, xb.cx, xb.cy)
			else
				IFObj_fnSetPos(s, XBPICK_PARK, xb.cy)
			end
		end
	end
	if this.Info.Equip then
		xbpick_str(this.Info.Equip, "Equipment:")
		if this.xbStage == 2 then
			IFObj_fnSetPos(this.Info.Equip, XBPICK_PARK, xb.eqY)
			IFObj_fnSetPos(this.Info.UnitCount, XBPICK_PARK, xb.ucY)
		else
			IFObj_fnSetPos(this.Info.Equip, xb.eqX, xb.eqY)
			IFObj_fnSetPos(this.Info.UnitCount, xb.ucX, xb.ucY)
		end
	end
	xbpick_hud(this, this.xbStage == 2)
	if this.xbStage ~= 2 and xbcp_unmark then xbcp_unmark() end
	if this.xbStage == 2 and this.xbCPs then
		-- controller post selection: our own prompt, the engine's Spawn button stays parked
		IFObj_fnSetPos(this.Info.Ok, XBPICK_PARK, xb.okY)
		IFObj_fnSetVis(this.Info.PromptSel, 1)
		xbpick_str(this.Info.PromptSel, "Spawn")
		local cp = this.xbCPs[this.xbCP]
		-- the map shows which post (flashing marker); its numbers don't follow the post names
		xbpick_str(this.Info.PromptLR, "<   Command Post   >")
		if cp and xbcp_mark then xbcp_mark(this.xbTeam or 1, cp.name) end
	elseif this.xbStage == 2 then
		IFObj_fnSetPos(this.Info.Ok, xb.okX, xb.okY)
		IFObj_fnSetVis(this.Info.PromptSel, nil)
		xbpick_str(this.Info.PromptLR, "")
	else
		IFObj_fnSetPos(this.Info.Ok, XBPICK_PARK, xb.okY)
		IFObj_fnSetVis(this.Info.PromptSel, 1)
		xbpick_str(this.Info.PromptSel, "Select Character")
		xbpick_str(this.Info.PromptLR, "")
	end
end

-- class index -> engine slot (the visible slots 0..9, in order)
function xbpick_slot(this)
	local slots = this.xbSlots
	if slots and slots[(this.xbIdx or 0) + 1] then return slots[this.xbIdx + 1] end
	return this.xbIdx or 0
end

-- class names in picker order (this.xbNames: the team's classes + the hero when available)
function xbpick_names(this)
	return this.xbNames or xbpick_classes[this.xbTeam or 1] or {}
end

function xbpick_preview(this)
	local list = xbpick_names(this)
	local name = list and list[(this.xbIdx or 0) + 1]
	if name then pcall(SelectCharacterClass, 0, name) end
end

-- the exe leaves the hero slot's texts at the template defaults: fill in the name and equipment
local function xbpick_loc(key)
	local ok, u = pcall(ScriptCB_getlocalizestr, key)
	if not ok or not u then return nil end
	local ok2, a = pcall(ScriptCB_ununicode, u)
	if not ok2 or type(a) ~= "string" or a == "" or string.sub(a, 1, 1) == "[" then return nil end
	return a
end

function xbpick_herotext(this, hero)
	local s = this.Info.SlotWindow10
	if not s or not hero then return end
	local lc = string.lower(hero)
	local _, _, side, rest = string.find(lc, "^(%a+)_(.+)$")
	local name = side and xbpick_loc("entity." .. side .. "." .. rest)
	if name and s.titleBarElement then IFText_fnSetUString(s.titleBarElement, ScriptCB_tounicode(name)) end
	local u = XBPICK_UNITS and XBPICK_UNITS[lc]
	if s.InfoText then
		local lines = {}
		local k, key
		for k, key in ipairs((u and u.e) or {}) do
			local w = xbpick_loc(key)
			if w then table.insert(lines, w) end
		end
		IFText_fnSetUString(s.InfoText, ScriptCB_tounicode(table.concat(lines, "\n")))
	end
end

function xbpick_init(this)
	local ok1, team = pcall(GetCharacterTeam, 0)
	team = tonumber(team) or 1
	local n = tonumber(GetTeamClassCount(team)) or 1
	if n < 1 then n = 1 end
	if n > 10 then n = 10 end
	local slots = {}
	local i
	-- slots 0..9: the classes the exe shows (slot 10 = hero, below)
	for i = 0, 9 do
		local s = this.Info["SlotWindow" .. i]
		if s and IFObj_fnGetVis(s) then table.insert(slots, i) end
	end
	if table.getn(slots) >= 1 and table.getn(slots) <= n then
		n = table.getn(slots)
	else
		slots = nil
	end
	-- the hero is the team's last class (GetTeamClassCount includes it). The exe offers it - as one more
	-- visible slot after the classes - only once this player earned and accepted it (in-game prompt):
	-- 0x42b590 via xbpick_canhero. Slot 10 (always visible, never filled) is only a fallback.
	local classes = xbpick_classes[team] or {}
	if table.getn(classes) > 0 and n > table.getn(classes) then n = table.getn(classes) end
	local names = {}
	for i = 1, n do names[i] = classes[i] end
	local hero = xbpick_heroes and xbpick_heroes[team]
	this.xbHeroOn = nil
	if hero and n < 10 and xbpick_canhero() then
		local hslot = (slots and slots[n + 1]) or 10
		if not slots then
			slots = {}
			for i = 0, n - 1 do slots[i + 1] = i end
		end
		while table.getn(slots) > n do table.remove(slots) end
		table.insert(slots, hslot)
		n = n + 1
		names[n] = hero
		this.xbHeroOn = 1
		if hslot == 10 then xbpick_herotext(this, hero) end
	elseif slots then
		while table.getn(slots) > n do table.remove(slots) end
	end
	this.xbNames = names
	this.xbSlots = slots
	local ok2, cls = pcall(GetCharacterClass, 0)
	cls = tonumber(cls) or 0
	if cls < 0 or cls >= n then cls = 0 end
	-- the hero was just accepted (in-game prompt): start on him, like the console; once per availability
	local pickHero = nil
	if this.xbHeroOn then
		if not xbpick_heroSeen then
			xbpick_heroSeen = 1
			cls = n - 1
			pickHero = 1
		end
	else
		xbpick_heroSeen = nil
	end
	this.xbTeam = team
	this.xbN = n
	this.xbIdx = cls
	this.xbStage = 1
	this.xbT = 0
	this.xbPending = nil
	this.xbSpawned = nil
	this.xbCPs = nil
	if xbring_init then xbring_init(this) end
	if pickHero then xbpick_preview(this) end
	-- which classes are locked (not enough points yet)
	this.xbLock = {}
	if XBPICK_HUDEVOK then
		xbpick_locks(this)
		if xbring_refresh then xbring_refresh(this) end
	else
		-- unpatched exe: preview each for a few frames and read the engine's text (see xbpick_islocked)
		this.xbScan = { k = 0, wait = 3 }
		xbpick_scanselect(this, 0)
	end
	xbpick_layout(this)
end

-- patched exe: GetTimerRate(141, k) = the spawn display's own test for engine class k (the team's classes in
-- order, the hero last): 1 allowed, 2 needs more points, 0 full. Returns whether anything changed.
function xbpick_locks(this)
	local changed = nil
	local k
	for k = 0, (this.xbN or 0) - 1 do
		local ok, v = pcall(GetTimerRate, 141, k)
		local lk = (ok and tonumber(v) == 2) and 1 or nil
		if lk ~= this.xbLock[k] then
			this.xbLock[k] = lk
			changed = 1
		end
	end
	return changed
end

function xbpick_scanselect(this, k)
	local list = xbpick_names(this)
	local name = list and list[k + 1]
	if name then pcall(SelectCharacterClass, 0, name) end
end

-- the engine writes "Get N more points to unlock!" into the unit count line for a locked class: much wider
-- than "Unit Count: 000" in the same font. NOT reliable: an unlocked points class shows "Unit Count: 2  Max: 4",
-- nearly as wide (201 vs 210) - only the fallback for an unpatched exe.
function xbpick_islocked(this)
	if not this.Info.XbMeasure then return nil end
	local l, t, r, b = IFText_fnGetDisplayRect(this.Info.UnitCount)
	local l0, t0, r0, b0 = IFText_fnGetDisplayRect(this.Info.XbMeasure)
	if not (l and l0) or l < 0 or r0 - l0 <= 0 then return nil end
	return (r - l) > (r0 - l0) * 1.2 -- measured: "Unit Count: 8" 126, lock text 210 (wrapped), reference 150
end

function xbpick_scanstep(this)
	local sc = this.xbScan
	if not sc then return end
	sc.wait = sc.wait - 1
	if sc.wait > 0 then return end
	this.xbLock[sc.k] = xbpick_islocked(this) and 1 or nil
	sc.k = sc.k + 1
	if sc.k < (this.xbN or 0) then
		xbpick_scanselect(this, sc.k)
		sc.wait = 3
	else
		this.xbScan = nil
		xbpick_preview(this) -- back to the class on screen
		if xbring_refresh then xbring_refresh(this) end
	end
end

function xbpick_enter_cps(this)
	this.xbCPs = nil
	if not xbcp_friendly then return end
	local ok, list = pcall(xbcp_friendly, this.xbTeam or 1)
	if ok and type(list) == "table" and table.getn(list) > 0 then
		-- keep the previous choice if that post is still ours
		local keep = 1
		local i
		for i = 1, table.getn(list) do
			if list[i].name == this.xbCPName then keep = i end
		end
		this.xbCPs = list
		this.xbCP = keep
	end
end

function xbpick_back(this)
	if this.xbStage == 2 then
		this.xbStage = 1
		this.xbPending = nil
		pcall(ScriptCB_SndPlaySound, "shell_menu_exit")
		xbpick_layout(this)
	end
end

function xbpick_cycle(this, dir)
	if not this.xbN then return end
	-- the d-pad press that accepted the hero in game (F1) can arrive here as the screen opens
	if this.xbStage == 1 and (this.xbT or 0) < 0.3 then return end
	if this.xbStage == 2 and this.xbCPs then
		local n = table.getn(this.xbCPs)
		this.xbCP = math.mod(this.xbCP - 1 + dir + n, n) + 1
		this.xbCPName = this.xbCPs[this.xbCP].name
	elseif this.xbStage == 2 then
		-- no post list (non-conquest modes): left/right returns to the class window
		this.xbStage = 1
		this.xbPending = nil
	else
		this.xbIdx = math.mod(this.xbIdx + dir + this.xbN, this.xbN)
		xbpick_preview(this)
		if xbring_select then xbring_select(this, dir) end
	end
	pcall(ScriptCB_SndPlaySound, "shell_select_change")
	xbpick_layout(this)
end

local xbpick_Enter = ifs_pc_SpawnSelect.Enter
ifs_pc_SpawnSelect.Enter = function(this, bFwd)
	xbpick_Enter(this, bFwd)
	xbpick_init(this)
end

local xbpick_Update = ifs_pc_SpawnSelect.Update
ifs_pc_SpawnSelect.Update = function(this, fDt)
	xbpick_Update(this, fDt)
	if not this.xbN then return end
	this.xbT = (this.xbT or 0) + (fDt or 0)
	if this.xbScan then xbpick_scanstep(this) end
	-- locks can change while the screen is open (points, class limits): re-read twice a second
	if XBPICK_HUDEVOK and this.xbLock and this.xbStage == 1 then
		this.xbLockT = (this.xbLockT or 0) + (fDt or 0)
		if this.xbLockT > 0.5 then
			this.xbLockT = 0
			if xbpick_locks(this) and xbring_refresh then xbring_refresh(this) end
		end
	end
	if this.xbStage ~= 2 then xbpick_hudev(130) end -- the engine may re-show the map: keep it hidden
	if xbring_update then xbring_update(this, fDt or 0) end
	-- test builds only: cycle by itself so no key presses are needed
	if XBPICK_AUTOTEST and this.xbStage == 1 then
		this.xbAutoT = (this.xbAutoT or 0) + (fDt or 0)
		if this.xbAutoT > XBPICK_AUTOTEST then
			this.xbAutoT = 0
			xbpick_cycle(this, 1)
		end
	end
	if this.xbPending then
		this.xbPending = this.xbPending - 1
		if this.xbPending <= 0 then
			this.xbPending = nil
			this.xbStage = 2
			xbpick_enter_cps(this)
			xbpick_layout(this)
		end
	end
	-- team switched with the team icons: start over with the new team's classes
	local ok, team = pcall(GetCharacterTeam, 0)
	if ok and tonumber(team) and tonumber(team) ~= this.xbTeam then
		xbpick_init(this)
	elseif this.xbStage == 1 and not this.xbScan and not this.xbPending and xbpick_heroes and xbpick_heroes[this.xbTeam or 1] then
		-- the hero became available (or was taken): rebuild the list and the ring
		local stale = this.xbHeroOn and this.xbSlots and this.xbSlots[this.xbN] == 10
			and this.Info["SlotWindow" .. (this.xbN - 1)] and IFObj_fnGetVis(this.Info["SlotWindow" .. (this.xbN - 1)])
		if xbpick_canhero() ~= this.xbHeroOn or stale then xbpick_init(this) end
	end
end

local xbpick_Accept = ifs_pc_SpawnSelect.Input_Accept
ifs_pc_SpawnSelect.Input_Accept = function(this, a, b)
	if xbpick_Accept then xbpick_Accept(this, a, b) end
	if not this.xbN then return end
	if (this.xbT or 0) < 0.5 then return end -- ignore the Enter that chose the team
	if this.xbStage == 1 and not this.xbPending then
		if this.xbLock and this.xbLock[this.xbIdx] then -- locked class: Xbox refuses it
			pcall(ScriptCB_SndPlaySound, "shell_menu_error")
			return
		end
		this.xbPending = 3 -- let the engine select the slot first
	elseif this.xbStage == 2 and this.xbCPs and not this.xbSpawned then
		local cp = this.xbCPs[this.xbCP]
		if cp and xbcp_spawn then
			if xbcp_unmark then xbcp_unmark() end
			local ok, info = xbcp_spawn(cp.name)
			if ok then
				this.xbSpawned = 1
			else
				-- could not spawn there: fall back to the engine's own Spawn button
				this.xbCPs = nil
				xbpick_layout(this)
			end
			if xbp_log then xbp_log("SPAWN " .. cp.name .. ":" .. tostring(ok) .. "," .. tostring(info)) end
		end
	end
end

ifs_pc_SpawnSelect.Input_GeneralLeft = function(this, bFromAI)
	xbpick_cycle(this, -1)
end
ifs_pc_SpawnSelect.Input_GeneralRight = function(this, bFromAI)
	xbpick_cycle(this, 1)
end

local xbpick_KeyDown = ifs_pc_SpawnSelect.Input_KeyDown
ifs_pc_SpawnSelect.Input_KeyDown = function(this, key, a, b)
	if xbpick_KeyDown then xbpick_KeyDown(this, key, a, b) end
	if key == 50 then xbpick_cycle(this, -1)       -- '2' = LB in the Steam layout
	elseif key == 49 then xbpick_cycle(this, 1)    -- '1' = RB
	elseif key == -59 then xbpick_cycle(this, -1)  -- F1 = d-pad left
	elseif key == -60 then xbpick_cycle(this, 1)   -- F2 = d-pad right
	elseif key == 99 or key == 67 or key == 8 then xbpick_back(this) -- 'c' (B button) / backspace
	end
end

local xbpick_Exit = ifs_pc_SpawnSelect.Exit
ifs_pc_SpawnSelect.Exit = function(this, bFwd)
	-- test builds only: die XBTEST_SUICIDE seconds after spawning (back to the class picker)
	if XBTEST_SUICIDE and CreateTimer and not xbt_suiTimer then
		xbt_suiTimer = CreateTimer("xbt_suicide")
		OnTimerElapse(function(t)
			pcall(KillObject, GetCharacterUnit(0))
			StopTimer(xbt_suiTimer)
		end, xbt_suiTimer)
	end
	-- test builds only: win the match XBTEST_WIN seconds after spawning (end-of-match screens)
	if XBTEST_WIN and CreateTimer and not xbt_winTimer then
		xbt_winTimer = CreateTimer("xbt_win")
		OnTimerElapse(function(t)
			local ok, team = pcall(GetCharacterTeam, 0)
			pcall(MissionVictory, tonumber(team) or 1)
			StopTimer(xbt_winTimer)
		end, xbt_winTimer)
		SetTimerValue(xbt_winTimer, XBTEST_WIN)
		StartTimer(xbt_winTimer)
	end
	if XBTEST_POINTS and AddFlagCapturePoints then
		local k
		for k = 1, XBTEST_POINTS do pcall(AddFlagCapturePoints, 0) end
	end
	if xbt_suiTimer then
		SetTimerValue(xbt_suiTimer, XBTEST_SUICIDE)
		StartTimer(xbt_suiTimer)
	end
	xbpick_hud(this, true)
	xbpick_hudev(131) -- never leave the gameplay minimap hidden
	if xbcp_unmark then xbcp_unmark() end
	if xbpick_Exit then return xbpick_Exit(this, bFwd) end
end

-- team emblem animation at the new position (same as PC, smaller, top-right)
function ifs_pc_spawnselect_animateicons(activeSide)
	local this = ifs_pc_SpawnSelect
	this.activeSide = activeSide
	local w,h = ScriptCB_GetSafeScreenInfo()
	local X = XBPICK_SIDEX or w * 0.885
	local Y = XBPICK_SIDEY or h * 0.105
	local s = w / 800 * 0.6
	local on, off = this.Info.SideModel0, this.Info.SideModel1
	if activeSide >= 0.5 then on, off = this.Info.SideModel1, this.Info.SideModel0 end
	AnimationMgr_AddAnimation(on, { fTotalTime = 0.75, fStartAlpha = 0.0, fEndAlpha = 1, fStartX = X, fEndX = X, fStartY = Y, fEndY = Y,
		fStartW = 0.25 * s, fStartH = 0.25 * s, fEndW = 0.5 * s, fEndH = 0.5 * s, })
	AnimationMgr_AddAnimation(off, { fTotalTime = 0.75, fStartAlpha = 1, fEndAlpha = 0.0, fStartX = X, fEndX = X, fStartY = Y, fEndY = Y,
		fStartW = 0.5 * s, fStartH = 0.5 * s, fEndW = 0.25 * s, fEndH = 0.25 * s, })
	IFModel_fnSetOmegaY(this.Info.SideModel0, -10)
	IFModel_fnSetOmegaY(this.Info.SideModel1, -10)
	this.IconModelFastMode = 1
end
