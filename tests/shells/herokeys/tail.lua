
-- TEST ONLY: after the profile is chosen, start Coruscant conquest with heroes on (unlock Always, Worst Player)
if ifs_sp_campaign and not xbt_herowrapped then
	xbt_herowrapped = 1
	local up = ifs_sp_campaign.Update
	ifs_sp_campaign.Update = function(this, fDt)
		if up then up(this, fDt) end
		xbt_hT = (xbt_hT or 0) + (fDt or 0)
		if not xbt_hdone and xbt_hT > 1.5 then
			xbt_hdone = 1
			local g = ScriptCB_GetNetGameDefaults()
			if type(g) == "table" then g.bHeroesEnabled = true ScriptCB_SetNetGameDefaults(g) end
			local p = ScriptCB_GetNetHeroDefaults()
			if type(p) == "table" then
				p.iHeroUnlock = 1 p.iHeroUnlockVal = 0 p.iHeroPlayer = 4 p.iHeroTeam = 3 p.iHeroRespawn = 1 p.iHeroRespawnVal = 0
				ScriptCB_SetNetHeroDefaults(p)
			end
			ScriptCB_ClearMissionSetup()
			ScriptCB_SetMissionNames("cor1c_con", nil)
			ScriptCB_SetPlayerSide(1, 0)
			ScriptCB_SetPlayerSide(1, 1)
			ScriptCB_EnterMission()
		end
	end
end
