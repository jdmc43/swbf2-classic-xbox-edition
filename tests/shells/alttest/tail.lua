
-- TEST ONLY: open the InstantAction (ALT) screen by itself
if ifs_sp_campaign and not xbt_altwrapped then
	xbt_altwrapped = 1
	local up = ifs_sp_campaign.Update
	ifs_sp_campaign.Update = function(this, fDt)
		if up then up(this, fDt) end
		xbt_altT = (xbt_altT or 0) + (fDt or 0)
		if not xbt_altdone and xbt_altT > 1.5 then
			xbt_altdone = 1
			this.CurButton = "spacetraining"
			this.Input_Accept(this)
		end
	end
end

-- TEST: movie playback experiment on the ALT screen
function xbt_movhook()
if ifs_missionselect_console and not xbt_movwrapped then
	xbt_movwrapped = 1
	local up = ifs_missionselect_console.Update
	ifs_missionselect_console.Update = function(this, fDt)
		if up then up(this, fDt) end
		xbt_mT = (xbt_mT or 0) + (fDt or 0)
		local step = math.floor(xbt_mT / 2.5)
		if step ~= xbt_mStep and step >= 1 and step <= 4 then
			xbt_mStep = step
			local names = { "cor1fly", "shell", "end1fly", "cor1fly" }
			local nm = names[step]
			local w, h = ScriptCB_GetScreenInfo()
			local r = ""
			if step == 4 then
				ScriptCB_CloseMovie()
				ScriptCB_OpenMovie("movies\shellfly.mvs", "")
				r = "reopen "
			end
			ScriptCB_StopMovie()
			local ok, e = pcall(ScriptCB_PlayMovie, nm, 1, "", 0, 0, w, h)
			xbt_mLog = (xbt_mLog or "") .. " " .. step .. ":" .. r .. nm .. "=" .. tostring(ok) .. "," .. tostring(e)
		end
		if xbt_mStep and this.InfoboxBot then
			IFText_fnSetString(this.InfoboxBot.Text1, (xbt_mLog or "") .. " pl=" .. tostring(ScriptCB_IsMoviePlaying()) .. " s=" .. tostring(gMovieStream))
		end
	end
end
end
