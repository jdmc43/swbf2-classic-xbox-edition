
-- Xbox-style command post selection (personal use).
-- The PC engine only selects a spawn post by mouse click on the map, so for the controller the
-- script keeps its own list of friendly posts (left/right cycles it) and spawns the player at the
-- chosen post itself (SpawnCharacter at the post's spawn path, falling back to the post).

local function xbcp_try(f, ...)
	if not f then return nil end
	local r = { pcall(f, unpack(arg)) }
	if r[1] then return r[2], r[3] end
	return nil
end

-- every command post the mission registered (any objective table with .commandPosts),
-- plus cp1..cp24 as a fallback for missions that don't use the objective scripts
function xbcp_all()
	local names, seen = {}, {}
	local k, v
	for k, v in pairs(_G) do
		if type(v) == "table" and type(v.commandPosts) == "table" then
			local n, cp
			for n, cp in pairs(v.commandPosts) do
				local name = (type(cp) == "table" and cp.name) or (type(n) == "string" and n)
				if name and not seen[name] then seen[name] = 1 table.insert(names, name) end
			end
		end
	end
	if table.getn(names) == 0 then
		local i
		for i = 1, 24 do
			local name = "cp" .. i
			if xbcp_try(GetCommandPostTeam, name) ~= nil then table.insert(names, name) end
		end
	end
	-- map numbering follows the post names in order (cp1, cp2, cp3, cp4, cp6 ... -> 1..N)
	table.sort(names, function(a, b)
		local na, nb = tonumber(string.gsub(a, "%D", "")), tonumber(string.gsub(b, "%D", ""))
		if na and nb and na ~= nb then return na < nb end
		return a < b
	end)
	return names
end

function xbcp_friendly(team)
	local all = xbcp_all()
	local out = {}
	local i
	for i = 1, table.getn(all) do
		local t = xbcp_try(GetCommandPostTeam, all[i]) or xbcp_try(GetObjectTeam, all[i])
		if tonumber(t) == tonumber(team) then
			table.insert(out, { name = all[i], number = i })
		end
	end
	return out
end

-- spawn point for a post: its spawn path (common naming), else the post itself
function xbcp_matrix(name)
	local cands = { name .. "_spawn", name .. "spawn", name .. "_Spawn", string.upper(name) .. "_SPAWN",
	                name .. "_spawn1", name .. "_spawnpath", name .. "spawnpath" }
	local i
	for i = 1, table.getn(cands) do
		local m = xbcp_try(GetPathPoint, cands[i], 0)
		if m then return m, cands[i] end
	end
	local m = xbcp_try(GetEntityMatrix, name)
	if m then return m, name end
	return nil
end

function xbcp_spawn(name)
	local m, from = xbcp_matrix(name)
	if not m then return nil, "no spawn point" end
	local ok, err = pcall(SpawnCharacter, 0, m)
	return ok, from or tostring(err)
end

-- flashing marker on the chosen post on the HUD map (same call the conquest objective uses)
function xbcp_mark(team, name)
	if xbcp_marked and xbcp_marked ~= name then
		pcall(MapRemoveEntityMarker, xbcp_marked, xbcp_markedTeam)
		xbcp_marked = nil
	end
	if name and name ~= xbcp_marked and MapAddEntityMarker then
		local ok = pcall(MapAddEntityMarker, name, "hud_objective_icon_circle", 4.0, team, "YELLOW", true)
		if ok then xbcp_marked = name xbcp_markedTeam = team end
	end
end

function xbcp_unmark()
	if xbcp_marked then
		pcall(MapRemoveEntityMarker, xbcp_marked, xbcp_markedTeam)
		xbcp_marked = nil
	end
end
