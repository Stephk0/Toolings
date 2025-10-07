 ---------------------------------------------------------------------
-- Display Knot Points through SplineShape in Viewport
-- by Stephan Viranyi https://www.artstation.com/stephko
-- Feel free to share and extend to your wishes and msg me for any questions or feedback at stephko@viranyi.de
-- 2023
---------------------------------------------------------------------
	
macroScript DisplayObjectNamesInViewport
category:"ST3E_Inspection"
toolTip:"Display Object Names In Viewport"	
(

	--------------------
	-- settings
	-- user could set this, for now
	--------------------
	
	local markerColorDefault = white
	local markerColorDefaultGroup = green
	local markerColorSelected = red
	local markershape = #Diamond -- could be customizable
	local pivotCrossSize = 200 -- could be customizable
	
	--------------------
	-- internal
	--------------------

	--to prevent memory leak it is recommended to cache often used functions and vars. especially GW functions
	global toggleObjectNames = false -- global to save the toggle state in 0 = off, 1 = on
	
	local setTransform = gw.setTransform (Matrix3 1) --gw functions cached for reuse
	local updateScreen = gw.UpdateScreen() --gw functions cached for reuse
	local gwText = gw.text --gw functions cached for reuse
	local markerdisplay = gw.Marker --gw functions cached for reuse
	local markerColor = markerColorDefault -- default not selected color
	--------------------
	-- viewport feedback
	--------------------
	UnregisterRedrawViewsCallback GW_DisplayObjectNames

	fn Draw3DCross pos rot size color =
	(
		markerColorArr = #(color as point3, color as point3)
		newDirX = [size,0,0] * inverse rot
		newDirY = [0,size,0] * inverse rot
		newDirZ = [0,0,size] * inverse rot
		gw.Polyline #( (pos + newDirX), (pos - newDirX) ) false rgb:markerColorArr
		gw.Polyline #( (pos + newDirY), (pos - newDirY) ) false rgb:markerColorArr
		gw.Polyline #( (pos + newDirZ), (pos - newDirZ) ) false rgb:markerColorArr

	)

	fn GW_DisplayObjectNames =
	(
		--toggle
		if toggleObjectNames do
		(
			--maxstuff for gw
			setTransform
			
			
			for obj in objects where not obj.isHiddenInVpt do
			(
				objPosTextOffset = obj.pos + [10,10,-40]
				
				markerColor = markerColorDefault

				-- if its a closed group
				if (isGroupHead obj and isOpenGroupHead obj == false) then
				(
					markerColor = markerColorDefaultGroup
					if (findItem (selection as array) obj != 0) then markerColor = markerColorSelected
					--draw only the name and pivot of the group if its closed
					Draw3DCross obj.pos obj.rotation pivotCrossSize markerColor
					gwText objPosTextOffset ("GROUP: " + obj.name as string + " @ Pos: " + (formattedPrint obj.pos format:"000.f") as string) color:markerColor
				)
				else if (isGroupHead obj == false and isGroupMember obj == false or (isOpenGroupMember obj) ) then
				(
					if obj.isselected then markerColor = markerColorSelected
					--draw all the name and pivot of the group if its closed
					Draw3DCross obj.pos obj.rotation pivotCrossSize markerColor
					gwText objPosTextOffset (obj.name as string + " @ Pos: " + (formattedPrint obj.pos format:"000.f") as string) color:markerColor
				)

				
			)

			
			updateScreen
		)	

	)
	--max stuff register callbacks
	UnregisterRedrawViewsCallback GW_DisplayObjectNames
	registerRedrawViewsCallback GW_DisplayObjectNames

	on isChecked do toggleObjectNames == true --Button checked state based on toggle
	
	on execute do toggleObjectNames = not toggleObjectNames 
	
)

