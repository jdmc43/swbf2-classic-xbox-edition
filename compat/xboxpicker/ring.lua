
-- Xbox-style ring of units for the class picker (personal use).
-- Based on the Galactic Conquest unit carousel (ifs_freeform_purchase_unit): each class is an
-- animated IFModel (body + weapon on hp_weapons) placed on a circle; the ring turns so the
-- selected class stands in front.

XBRING_Y = XBRING_Y or -0.85        -- feet height
XBRING_Z = XBRING_Z or 6.4          -- ring centre distance from the camera
XBRING_BACK = XBRING_BACK or 1.6    -- ring radius
XBRING_FRONT = XBRING_FRONT or 2.6  -- selected unit steps forward to this radius
XBRING_DEPTH = XBRING_DEPTH or 0.002 -- IFModel draw depth: draws the ring in front of the engine's own spawn unit
XBRING_DIM = XBRING_DIM or 70 -- colour of the units that are not selected (Xbox: dark, far back)
XBRING_RX = XBRING_RX or 0.55       -- ellipse: sideways scale (keeps the ring behind the front unit, off the minimap)
XBRING_RZ = XBRING_RZ or 1.4        -- ellipse: depth scale
XBRING_XOFF = XBRING_XOFF or -0.4   -- sideways shift of the whole ring (the container position does not move 3D models)

XBRING_ANIMS = {
	rifle = { banks = { "human_0" },
		idle = { upper = "human_rifle_stand_idle_emote_full", lower = "human_rifle_stand_idle_emote_full" },
		sel = "human_rifle_stand_idle_lookaround_full" },
	bazooka = { banks = { "human_0", "human_2" },
		idle = { upper = "human_bazooka_stand_idle_emote", lower = "human_rifle_stand_idle_emote_full" },
		sel = "human_bazooka_stand_idle_lookaround" },
	marksperson = { banks = { "marksperson", "human_0" },
		idle = { upper = "human_rifle_stand_idle_emote_full", lower = "human_rifle_stand_idle_emote_full" },
		sel = "human_rifle_stand_idle_lookaround_full" },
	wookie = { banks = { "wookie", "human_0" },
		idle = { upper = "human_rifle_stand_idle_emote_full", lower = "human_rifle_stand_idle_emote_full" },
		sel = "human_rifle_stand_idle_lookaround_full" },
	bdroid = { banks = { "bdroid", "human_0" },
		idle = "human_rifle_stand_idle_emote_full",
		sel = "human_rifle_stand_idle_lookaround_full" },
	bdroid_bazooka = { banks = { "bdroid", "human_0", "human_2" },
		idle = { upper = "human_bazooka_stand_idle_emote", lower = "human_rifle_stand_idle_emote_full" },
		sel = "human_bazooka_stand_idle_lookaround" },
	sbdroid = { banks = { "sbdroid", "human_0" },
		idle = { upper = "sbdroid_rifle_stand_idle_emote", lower = "human_rifle_stand_idle_emote_full" },
		sel = "sbdroid_rifle_standalert_idle_emote" },
	magnaguard = { banks = { "magnaguard", "human_0" },
		idle = { upper = "human_rifle_stand_idle_emote_full", lower = "human_rifle_stand_idle_emote_full" },
		sel = "human_rifle_stand_idle_lookaround_full" },
	droideka = { banks = { "cis_walk_droideka" }, idle = "idle", sel = "idle" },
	-- lightsaber heroes (bank names/anim names verified against the zaa_ hashes: CRC-32/BZIP2 of the name;
	-- the bank's only standing animation is the idle emote)
	sabre = { banks = { "human_sabre", "human_0" },
		idle = "human_sabre_stand_idle_emote_full", sel = "human_sabre_stand_idle_emote_full" },
	doublesabre = { banks = { "human_doublesabre", "human_sabre", "human_0" },
		idle = "human_doublesabre_stand_idle_emote_full", sel = "human_doublesabre_stand_idle_emote_full" },
}
XBRING_ANIMS.wookie_bazooka = XBRING_ANIMS.wookie
XBRING_ANIMS.magnaguard_bazooka = XBRING_ANIMS.magnaguard
XBRING_ANIMS.marksperson_bazooka = XBRING_ANIMS.marksperson

XBRING_LIGHTING = {
	ambient = {
		top = { red = 0.35, green = 0.35, blue = 0.35 },
		bottom = { red = 0.25, green = 0.25, blue = 0.25 },
	},
	directional = {
		{ direction = { x = 0, y = -0.7, z = -0.7 }, color = { red = 1, green = 1, blue = 1 }, },
	},
}

-- feature switches (for crash bisecting): set to 1 in a test build to skip a feature
XBRING_NOANIM = XBRING_NOANIM
XBRING_NOATTACH = XBRING_NOATTACH
XBRING_NOLIGHT = XBRING_NOLIGHT

-- pass exactly the given arguments: the exe crashes on explicit trailing nils
local function xbcall(f, ...)
	if f then pcall(f, unpack(arg)) end
end
-- XBRING_ANIMSTEP (bisect): 1 = banks only, 2 = + set animation, 3 = + per-frame update/time/queue
XBRING_ANIMSTEP = XBRING_ANIMSTEP or 3
local function xbanim(f, ...)
	if not f or XBRING_NOANIM then return end
	local step = 3
	if f == ScriptCB_IFModel_SetAnimation or f == ScriptCB_IFModel_SetAnimationLooping then step = 2 end
	if XBRING_ANIMSTEP < step then return end
	pcall(f, unpack(arg))
end

local function xbring_anim_setup(entry)
	local e = entry.e
	local set = entry.set
	if ScriptCB_IFModel_SetAnimationBanks and not XBRING_NOANIM and XBRING_ANIMSTEP >= 1 then
		-- exact argument count (the exe may not like trailing nils)
		pcall(ScriptCB_IFModel_SetAnimationBanks, e.body.cp, unpack(set.banks))
	end
	xbanim(ScriptCB_IFModel_SetAnimationLooping, e.body.cp, 1)
	xbanim(ScriptCB_IFModel_SetAnimation, e.body.cp, set.idle, 0)
	local t = math.random()
	xbanim(ScriptCB_IFModel_SetAnimationTime, e.body.cp, t)
	entry.animReady = 1
end

local function xbring_anim(entry, which)
	if not entry.animReady then return end
	local body = entry.e.body
	local set = entry.set
	if which == "sel" then
		xbanim(ScriptCB_IFModel_SetAnimationLooping, body.cp, 1)
		xbanim(ScriptCB_IFModel_SetAnimation, body.cp, set.sel, 0.4)
		xbanim(ScriptCB_IFModel_SetAnimationTime, body.cp, 0)
		xbanim(ScriptCB_IFModel_QueueAnimation, body.cp, set.idle)
	else
		xbanim(ScriptCB_IFModel_SetAnimationLooping, body.cp, 1)
		xbanim(ScriptCB_IFModel_SetAnimation, body.cp, set.idle, 0.4)
	end
end

local function xbring_mark(this)
	local k, entry
	for k, entry in pairs(this.xbRing or {}) do
		local sel = (entry.idx == this.xbIdx)
		-- locked classes (not enough points yet) are black silhouettes, like on the Xbox
		local lk = (this.xbLock and this.xbLock[entry.idx]) and 1 or nil
		if sel ~= entry.sel or lk ~= entry.lk then
			local selChanged = (sel ~= entry.sel)
			entry.sel = sel
			entry.lk = lk
			entry.rT = sel and XBRING_FRONT or XBRING_BACK
			local c = (lk and 0) or (sel and 255) or XBRING_DIM
			xbcall(ScriptCB_IFObj_SetColor, entry.e.body.cp, c, c, c)
			if entry.e.weapon.cp then xbcall(ScriptCB_IFObj_SetColor, entry.e.weapon.cp, c, c, c) end
			if selChanged then xbring_anim(entry, sel and "sel" or "idle") end
		end
	end
end

function xbring_init(this)
	local ring = this.Ring
	if not ring then return end
	if not xbring_lit and ScriptCB_SetIFaceLighting and not XBRING_NOLIGHT then
		xbring_lit = 1
		pcall(ScriptCB_SetIFaceLighting, XBRING_LIGHTING)
	end
	local names = (xbpick_names and xbpick_names(this)) or xbpick_classes[this.xbTeam or 1] or {}
	local n = this.xbN or 1
	local sp = 2 * (math.pi or 3.14159265) / math.max(n, 1)
	this.xbRing = {}
	local k
	for k = 1, 10 do
		local e = ring["u" .. k]
		local idx = k - 1
		local name = (idx < n) and names[idx + 1]
		local u = name and XBPICK_UNITS and XBPICK_UNITS[string.lower(name)]
		if not u and name and XBRING_GEOM and XBRING_GEOM[string.lower(name)] then
			u = { b = XBRING_GEOM[string.lower(name)], a = "rifle" } -- class not in the table: model only
		end
		if e and u then
			-- map/legion skin: re-textured copy (xbring.lvl) if the class has texture overrides,
			-- else the model the skin changer or the mission set, else the class default
			local lname = string.lower(name)
			local body = (XBRING_VMESH and XBRING_VMESH[lname]) or (XBRING_GEOM and XBRING_GEOM[lname]) or u.b
			IFModel_fnSetMsh(e.body, body)
			if u.w then
				IFModel_fnSetMsh(e.weapon, u.w)
				if not e.attached and not XBRING_NOATTACH then
					e.attached = 1
					pcall(IFModel_fnAttachModel, e.body, e.weapon, "hp_weapons")
				end
			else
				IFModel_fnSetMsh(e.weapon, nil)
			end
			local set = XBRING_ANIMS[u.a] or XBRING_ANIMS.rifle
			if XBRING_DEPTH then pcall(IFModel_fnSetDepth, e.body, XBRING_DEPTH) pcall(IFModel_fnSetDepth, e.weapon, XBRING_DEPTH) end
			this.xbRing[k] = { e = e, idx = idx, a = idx * sp, r = XBRING_BACK, rT = XBRING_BACK, set = set, sel = nil, animWait = XBRING_ANIMDEFER or 6 }
		elseif e then
			IFObj_fnSetVis(e, nil)
		end
	end
	this.xbRingSp = sp
	this.xbRingOff = (this.xbIdx or 0) * sp
	this.xbRingOffT = this.xbRingOff
	xbring_mark(this)
	local entry
	for k, entry in pairs(this.xbRing) do entry.r = entry.rT end
	xbring_update(this, 0)
end

-- Re-textured model copies (xbring.lvl, one sub-level each) for classes with texture overrides
-- (class definition or skin changer). Loaded from the AddUnitClass hook: that runs while the
-- mission loads, after its sides were read and skinned - only the copies this mission needs.
XBRING_VMESH = XBRING_VMESH or {}
XBRING_VLOADED = XBRING_VLOADED or {}
function xbring_needvariant(cls)
	if type(cls) ~= "string" then return end
	local c = string.lower(cls)
	local u = XBPICK_UNITS and XBPICK_UNITS[c]
	local g = (XBRING_GEOM and XBRING_GEOM[c]) or (u and u.b)
	local t1 = (XBRING_TEX1 and XBRING_TEX1[c]) or (u and u.t1)
	local t2 = (XBRING_TEX2 and XBRING_TEX2[c]) or (u and u.t2)
	if not g or not (t1 or t2) then return end
	local key = string.lower(g) .. "|" .. string.lower(t1 or "") .. "|" .. string.lower(t2 or "")
	local v = XBRING_VARIANTS and XBRING_VARIANTS[key]
	if not v then
		XBRING_VMISS = (XBRING_VMISS or 0) + 1
		return
	end
	if not XBRING_VLOADED[v] then
		XBRING_VLOADED[v] = 1
		XBRING_VNEED = (XBRING_VNEED or 0) + 1
		-- skip the skin changer's ReadDataFile hook; exact argument count (no trailing nils)
		local rdf = OG_ReadDataFile or ReadDataFile
		rdf("xbring.lvl", v)
	end
	XBRING_VMESH[c] = v
end

-- after ScriptPostLoad: re-textured models for every class; test builds can unlock all classes
function xbring_loadvariants()
	if XBTEST_UNLOCK and SetClassProperty then -- test builds only: no points needed for any class
		local team, k, cls
		for team = 1, 2 do
			for k, cls in ipairs((xbpick_classes and xbpick_classes[team]) or {}) do
				pcall(SetClassProperty, cls, "PointsToUnlock", "0")
			end
		end
	end
	local team, k, cls
	for team = 1, 2 do
		for k, cls in ipairs((xbpick_classes and xbpick_classes[team]) or {}) do
			xbring_needvariant(cls)
		end
		if xbpick_heroes and xbpick_heroes[team] then xbring_needvariant(xbpick_heroes[team]) end
	end
end

function xbring_refresh(this)
	if this.xbRing then xbring_mark(this) end
end

function xbring_select(this, dir)
	if not this.xbRing then return end
	this.xbRingOffT = (this.xbRingOffT or 0) + dir * (this.xbRingSp or 1)
	xbring_mark(this)
end

function xbring_layout(this)
	local k, entry
	for k, entry in pairs(this.xbRing or {}) do
		-- XBRING_NOFRONT: the engine's own unit model (correct map skin) is the front unit
		IFObj_fnSetVis(entry.e, this.xbStage ~= 2 and not (XBRING_NOFRONT and entry.idx == this.xbIdx))
	end
end

function xbring_update(this, dt)
	if not this.xbRing or this.xbStage == 2 then return end
	local f = math.min(1, dt * 8)
	this.xbRingOff = this.xbRingOff + (this.xbRingOffT - this.xbRingOff) * f
	local k, entry
	for k, entry in pairs(this.xbRing) do
		entry.r = entry.r + (entry.rT - entry.r) * f
		local a = entry.a - this.xbRingOff
		local x = entry.r * math.sin(a) * XBRING_RX + XBRING_XOFF -- whole ring left of centre (Xbox: front unit at x 0.40)
		local z = -XBRING_Z + entry.r * math.cos(a) * XBRING_RZ
		IFModel_fnSetTranslation(entry.e.body, x, XBRING_Y, z)
		IFModel_fnSetRotation(entry.e.body, math.cos(0.5 * a), 0, math.sin(0.5 * a), 0)
		IFObj_fnSetZPos(entry.e.body, 200)
		if entry.animWait then
			entry.animWait = entry.animWait - 1
			if entry.animWait <= 0 then
				entry.animWait = nil
				xbring_anim_setup(entry)
				if entry.sel then xbring_anim(entry, "sel") end
			end
		elseif entry.animReady then
			xbanim(ScriptCB_IFModel_UpdateAnimation, entry.e.body.cp, dt)
		end
	end
end
