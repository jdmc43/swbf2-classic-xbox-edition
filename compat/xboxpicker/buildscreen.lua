-- Xbox-style class picker for the PC spawn screen (personal use).
-- Uses the Xbox ifs_charselect window geometry: one window on the right, class name in
-- the title bar, weapon list underneath. All engine slots are built with that geometry;
-- the flow script (xboxflow.lua) shows only the current one and parks the rest off-screen.
-- Each slot / the Spawn button gets a large click area, so a click (RT) or Enter
-- anywhere makes the engine select the shown class / spawn.
XBPICK_PARK = -10000

function ifs_pc_SpawnSelect_fnBuildScreen(this, mode)

	this.Info = NewIFContainer {
		ScreenRelativeX = 0.0,
		ScreenRelativeY = 0.0,
	}

	local w,h = ScriptCB_GetSafeScreenInfo()
	local MAX_CLASS_SLOTS = 10 -- must match MAX_CLASS_SLOTS in pcSpawnDisplay.h

	local fontsize = "gamefont_small"
	local smallfontsize = "gamefont_small"
	local screenWidth, screenHeight = ScriptCB_GetScreenInfo()
	if screenHeight >= 960 then
		fontsize = "gamefont_medium"
		smallfontsize = "gamefont_medium"
	end
	local lineH = ScriptCB_GetFontHeight(smallfontsize) + 2

	-- Xbox ifs_charselect window (mode 0): 0.55 of a 4:3 screen wide, box from
	-- titleBar + 20% to 80% of the height, right side of the screen.
	local titleBarHeight = 30
	-- measured on the Xbox screenshot (carasol.jpg): window x 0.58..0.93, title tab from y 0.235, box to 0.765
	-- (a ButtonWindow draws ~0.89 of its width, centred 0.025 left: parameters compensate)
	local winW = math.min(w * (XBPICK_WINW or 0.395), h * 0.733)
	local winY = titleBarHeight + (XBPICK_WINY or 0.21) * (h - titleBarHeight)
	local winH = (XBPICK_WINH or 0.55) * (h - titleBarHeight)
	local winR = w * (XBPICK_WINR or 0.9775)
	local cx = winR - winW * 0.5
	local cy = winY + winH * 0.5
	this.xb = { w = w, h = h, cx = cx, cy = cy, winW = winW, winH = winH }

	-- team icons / models (exe drives them; unchanged from PC)
	local sideh = h * 0.15
	local sidew = w * 0.1
	-- team emblem: top-right corner above the class window (Xbox class step has none in the middle)
	XBPICK_SIDEX = w * 0.885
	XBPICK_SIDEY = h * 0.105
	this.Info.SideIcon0 = NewBorderRect { ZPos = 190, x = XBPICK_SIDEX, y = XBPICK_SIDEY, width = sidew * 1.3, height = sideh * 0.7, alpha = 0, }
	this.Info.SideIcon1 = NewBorderRect { ZPos = 190, x = XBPICK_SIDEX, y = XBPICK_SIDEY, width = sidew * 1.3, height = sideh * 0.7, alpha = 0, }
	this.Info.SideModel0 = NewIFModel { x = 0.0, y = 0.0, scale = 1.0, OmegaY = -0.3, lighting = 1, ColorR = 76, ColorG = 180, ColorB = 255, }
	this.Info.SideModel1 = NewIFModel { x = 0.0, y = 0.0, scale = 1.0, OmegaY = -0.3, lighting = 1, ColorR = 76, ColorG = 180, ColorB = 255, }

	-- prompts, bottom right (Xbox helptext style)
	local okw = w * 0.14
	local okh = h * 0.035
	local okY = h * (XBPICK_OKY or 0.9376)
	local iconS = okh * 1.5
	local iconX = winR - iconS * 0.5
	local okX = iconX - iconS * 0.5 - 8 - okw * 0.5
	this.xb.okX = okX
	this.xb.okY = okY

	-- Spawn button (stage 2). Click area: everything right of the minimap, so the
	-- map stays clickable for choosing a command post.
	this.Info.Ok = NewPCIFButton {
		x = XBPICK_PARK,
		y = okY,
		btnw = okw,
		btnh = okh,
		font = "gamefont_medium",
		bg_width = okw,
		string = "ifs.SpawnDisplay.Spawn",
	}
	local mapRight = w * 0.45
	this.Info.Ok.label.fHotspotX = mapRight - okX
	this.Info.Ok.label.fHotspotY = -okY - h
	this.Info.Ok.label.fHotspotW = (w - mapRight) * 2
	this.Info.Ok.label.fHotspotH = h * 3

	this.Info.PromptA = NewIFImage {
		ZPos = 120,
		x = iconX,
		y = okY,
		localpos_l = -iconS * 0.5, localpos_t = -iconS * 0.5,
		localpos_r =  iconS * 0.5, localpos_b =  iconS * 0.5,
		texture = "xbpick_btna",
	}
	-- stage 1 prompt text ("Select Class"), same place as the Spawn button
	this.Info.PromptSel = NewIFText {
		x = iconX - iconS * 0.5 - 10 - okw * 2,
		y = okY - okh * 0.5 - 4,
		halign = "right", valign = "top",
		textw = okw * 2, texth = okh * 2,
		font = "gamefont_medium",
		ColorR = 255, ColorG = 255, ColorB = 255,
		flashy = 0, nocreatebackground = 1,
		string = "",
	}
	-- (B) Back, bottom left (Xbox helptext), shown in the post step
	local bX = w * 0.03 + iconS * 0.5
	this.Info.PromptB = NewIFImage {
		ZPos = 120,
		x = bX,
		y = okY,
		localpos_l = -iconS * 0.5, localpos_t = -iconS * 0.5,
		localpos_r =  iconS * 0.5, localpos_b =  iconS * 0.5,
		texture = "btnb",
	}
	this.Info.PromptBText = NewIFText {
		x = bX + iconS * 0.5 + 8,
		y = okY - okh * 0.5 - 4,
		halign = "left", valign = "top",
		textw = okw * 2, texth = okh * 2,
		font = "gamefont_medium",
		ColorR = 255, ColorG = 255, ColorB = 255,
		flashy = 0, nocreatebackground = 1,
		string = "Back",
	}
	-- class cycling hint above the window (Xbox: left/right on the d-pad)
	this.Info.PromptLR = NewIFText {
		x = cx - winW * 0.5,
		y = winY + winH + 6,
		halign = "hcenter", valign = "top",
		textw = winW, texth = ScriptCB_GetFontHeight(smallfontsize) + 4,
		font = smallfontsize,
		ColorR = 255, ColorG = 255, ColorB = 255,
		flashy = 0, nocreatebackground = 1,
		string = "",
	}

	-- unit count / reason text, under the window
	this.xb.ucX = cx - winW * 0.5 + 10
	this.xb.ucY = winY + 5
	this.Info.UnitCount = NewIFText {
		x = this.xb.ucX,
		y = this.xb.ucY,
		halign = "left",
		valign = "top",
		textw = winW - 20,
		texth = lineH * 2,
		font = smallfontsize,
		style = "shadow",
		ColorR = 255, ColorG = 255, ColorB = 255,
		flashy = 0,
	}

	-- hidden reference for the lock check: the engine writes "Get N more points to unlock!" instead of the
	-- unit count for a locked class - much wider (or two lines) than this text in the same font
	this.Info.XbMeasure = NewIFText {
		x = XBPICK_PARK, y = winY + 5,
		halign = "left", valign = "top",
		textw = winW - 20, texth = lineH * 2,
		font = smallfontsize, style = "shadow",
		flashy = 0, nocreatebackground = 1,
		string = "Unit Count: 000",
	}

	this.Info.Equip = NewIFText {
		x = cx - winW * 0.5 + 10,
		y = winY + 5 + lineH * 2,
		halign = "left", valign = "top",
		textw = winW - 20, texth = lineH + 4,
		font = smallfontsize,
		ColorR = 255, ColorG = 255, ColorB = 255,
		flashy = 0, nocreatebackground = 1,
		string = "",
	}
	this.xb.eqX = cx - winW * 0.5 + 10
	this.xb.eqY = winY + 5 + lineH * 2

	-- ring of unit models (Xbox carousel), centred where the engine draws its unit
	this.Ring = NewIFContainer { ScreenRelativeX = XBRING_SX or 0.42, ScreenRelativeY = 0.5, ZPos = 10 }
	local k
	for k = 1, 10 do
		this.Ring["u" .. k] = NewIFContainer {
			weapon = NewIFModel { alpha = 255, lighting = 1 },
			body = NewIFModel { depth = 0.004, alpha = 255, lighting = 1 },
		}
	end

	local i
	for i = 0,MAX_CLASS_SLOTS do
		local tag = string.format("SlotWindow%d",i)

		this.Info[tag] = NewButtonWindow {
			ZPos = 200,
			x = XBPICK_PARK,
			y = cy,
			width = winW,
			height = winH,
			titleText = "ifs.profile.list",
			font = fontsize,
			buttonHeightPad = 1,
			buttonGutter = 1,
			titleOffsetX = 5,
		}

		local tb = this.Info[tag].titleBarElement
		if tb then tb.textcolorr = 255 tb.textcolorg = 220 tb.textcolorb = 0 end

		-- click area covers the whole screen while this slot is shown
		this.Info[tag].bHotspot = 1
		this.Info[tag].fHotspotX = -w * 2
		this.Info[tag].fHotspotY = -h * 2
		this.Info[tag].fHotspotW = w * 4
		this.Info[tag].fHotspotH = h * 4

		-- weapon list: Xbox BoxText (left/top aligned, white)
		this.Info[tag].InfoText = NewIFText {
			x = -winW * 0.5 + 10,
			y = -winH * 0.5 + 5 + lineH * 3,
			halign = "left",
			valign = "top",
			textw = winW - 15,
			texth = winH - 10 - lineH * 3,
			font = smallfontsize,
			string = "InfoText",
			ColorR = 255, ColorG = 255, ColorB = 255,
			flashy = 0,
		}
	end
end

