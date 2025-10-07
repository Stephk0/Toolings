-- this needs to be in startup otherwise snap to center wont work
global X = 1
global Y = 2
global Z = 3

function CenterOnAxis axis =
(	
	if (selection.count > 1 OR subobjectLevel == 0) then
	(
		for obj in selection do
		(
			case axis of 
			(
				X:obj.pos.x = 0
				Y:obj.pos.y = 0
				Z:obj.pos.z = 0
			)
		)
	)
	else
	(
		with redraw off
		(
			--input axis
			axisp3 = case axis of 
			(
				X:[0,1,1]
				Y:[1,0,1]
				Z:[1,1,0]
			)
			--store the subobject level we are in
			prevSubobjectLevel = subObjectLevel
			--get our selected mesh
			selectedMesh = selection[1]
			-- get our active mod or editable poly object
			curmod = Filters.GetModOrObj()
			-- mark if we show the end result
			showEndResultOn = false
			-- mark if soft seleciton is on
			softSelectionActive = false

			if (showEndResult) then 
			(
				showEndResultOn = true
				showEndResult = false
			)
			
			if (not Filters.Is_This_EditPolyMod curmod and subObjectLevel > 1) then 
			(

				--TODO: spline implemation of edge to vert conversion
				--convert selection from any to vertex as we are in not in vert mode
				if (subObjectLevel == 2 OR subObjectLevel == 3) do curmod.ConvertSelection #Edge #Vertex
				if (subObjectLevel >= 4 ) do curmod.ConvertSelection #Face #Vertex
				--switch to vert mode to just deal with verts
				subObjectLevel = 1
			)
			

			--any kind of edit poly mod or base
			if (Filters.Is_EPoly()) then
			(
				
				-- store contrain if active
				constraintActive = 0
				--disable constrains if active and flag
				if (curmod.constrainType > 0) then
				(
					constraintActive = curmod.constrainType
					curmod.constrainType = 0
				)

				if (Filters.Is_This_EditPolyMod curmod) then
				(
					-- Wicked Edit_Poly behaviour: we need to set the coord system to world and then transform along transform axis. If we are in any other coord system it will "retransform" the scaling axis :(
					-- get the active refernce coordinate system to set it back later
					activeCoordSys = getRefCoordSys()
					-- set to world
					toolMode.coordsys #world
					--disable softSelection and flag
					if (curmod.useSoftSel) then 
					(
						softSelectionActive = true
						curmod.useSoftSel = false
					)
					-- simply scale to its pivot	
					curmod.ScaleSelection axisp3 axis:selectedMesh.transform
					curmod.Commit()
					-- restore soft selction if it was active		
					curmod.useSoftSel = softSelectionActive
					-- restore coord system
					setRefCoordSys activeCoordSys
					
					
				)
				else
				( 
					-- editable poly handles this differently as get and set vert are both local and we can just set them with no fuss (albeit it does consider constrains)
					
					for i in (polyop.getVertSelection selectedMesh) do
					(
						vertexPosition = (polyop.getVert curmod i) * axisp3
						--move the scaled verts to the pivot, for some reason editable polys internal zeropoint is not the pivot
						vertexPosition -= in coordsys local (selectedMesh.objectoffsetpos) * (1 - axisp3)
						polyop.setVert curmod i vertexPosition
					)

					
				)

				-- enable the constrain again
				curmod.constrainType = constraintActive
				
				
			)
			-- otherwise if its a spline
			else if (Filters.Is_EditSpline()) then
			(
				-------------------------
				-- todo: support for splines
				-------------------------
				--new_spline = $
				selKnotsArr = getKnotSelection selectedMesh 1
				for i in selKnotsArr.count do
				(
					knotpoint = getKnotPoint selectedMesh i selKnotsArr[i]
					print knotpoint
				)
				
			)

			-- restore edge mode if active for all types
			subObjectLevel = prevSubobjectLevel
			-- restore show end result
			showEndResult = showEndResultOn
		)
		
		
	)
	--redraw the views
	redrawViews()
)

	
	