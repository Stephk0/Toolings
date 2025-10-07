 ---------------------------------------------------------------------
-- Display Knot Points through SplineShape in Viewport
-- by Stephan Viranyi https://www.artstation.com/stephko
-- Feel free to share and extend to your wishes and msg me for any questions or feedback at stephko@viranyi.de
-- 2023
---------------------------------------------------------------------
	
macroScript DisplayKnotPointsInViewport
category:"ST3E_Inspection"
toolTip:"Display Knot Points"	
(



	--------------------
	-- settings
	-- user could set this, for now
	--------------------
	
	local markerColorDefault = white
	local markerColorSelected = red
	local markershape = #circle -- could be customizable
	
	--------------------
	-- internal
	--------------------

	--to prevent memory leak it is recommended to cache often used functions and vars. especially GW functions
	global toggleKnotMarkers = false -- global to save the toggle state in 0 = off, 1 = on
	local setTransform = gw.setTransform (Matrix3 1) --gw functions cached for reuse
	local updateScreen = gw.UpdateScreen() --gw functions cached for reuse
	local markerdisplay = gw.Marker --gw functions cached for reuse
	local nodeSelection -- selection of the node

	local markerColor = markerColorDefault -- default not selected color
	local knotpos -- temp knotpos variable
	local knotSelectionIndex = #() -- array of selected knotPoints
	local itemIndex = 0 -- temp selected knot index of selected knots 
	--------------------
	-- viewport feedback
	--------------------
	UnregisterRedrawViewsCallback GW_DisplayKnotpoints

	fn GW_DisplayKnotpoints =
	(
		nodeSelection = selection[1]
		--only on splines
		if nodeSelection != undefined and toggleKnotMarkers and (classOf nodeSelection.baseobject == SplineShape or classOf nodeSelection.baseobject == Line) do
		(
			--maxstuff for gw
			setTransform
			--for every spline in our splineshape
			for sp = 1 to numSplines nodeSelection do 
			(
				--get the selection as array per spline index
				knotSelectionIndex = getKnotSelection nodeSelection sp
				--per spline index and per knot do
				for knot = 1 to numKnots nodeSelection sp do
				(
					--get the position of the knot
					knotpos = getKnotPoint nodeSelection sp knot
					-- default to white color
					markerColor = markerColorDefault
					-- find if the current knot we are looping through is in the array of selected knots per spline
					itemIndex = findItem knotSelectionIndex knot
					-- itemIndex 0 is nothing selected, otherwise if in the list of selected knot the current knotindex is present > color it red, aka is selected
					if itemIndex != 0 and knotSelectionIndex[itemIndex] == knot do markerColor = markerColorSelected
					-- display final marker on the position of the knot in 3d space
					markerdisplay knotpos markershape color:markerColor
				)
			)
		updateScreen
		)	

	)
	--max stuff register callbacks
	UnregisterRedrawViewsCallback GW_DisplayKnotpoints
	registerRedrawViewsCallback GW_DisplayKnotpoints

	on isChecked do toggleKnotMarkers == true --Button checked state based on toggle
	
	on execute do toggleKnotMarkers = not toggleKnotMarkers 
	
)

