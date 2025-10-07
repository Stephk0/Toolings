/*
-----------------------------------------------------------------------
-- Weld Borders
-----------------------------------------------------------------------
Weld Open Edges Borders. Finds first incoming Edit poly or jumps directly to lowest editable poly, selects open edges, converts it to verticies and opens the weld dialog
Very useful for when a split-apart model needs to be welded back / collapsed together.
*/


macroScript WeldBorders
	category:"ST3E_Editing"
	toolTip:"OP Weld Border Vertices"
	ButtonText:"WeldBrdVert"
	(
		-----------------------------------------------------------------------
		-- Weld Borders
		-----------------------------------------------------------------------
		-- go into modfy mode if not active, select open edges, convert to verts, open vert weld window
		-----------------------------------------------------------------------
		-- TODO: filter.epoly, get rid of $ sign

		on isEnabled return selection.count == 1
		
		on execute do
		(
			editPolyModIndex = 0
			
			if (currPanelMode != #modify) do max modify mode
			
			currentSelection = selection[1]

			-- if there is an edit poly ontop pick that
			for i = 1 to currentSelection.modifiers.count do
			(
				if (ClassOf currentSelection.modifiers[i] == Edit_Poly AND currentSelection.modifiers[i].enabled == true) then
				(
					editPolyModIndex = i
					exit
				)else(
					STOP
				)
			)
			-- first incoming edit poly
			if (editPolyModIndex > 0) then
			(
				-- select the incoming modifer
				modPanel.setCurrentObject currentSelection.modifiers[editPolyModIndex]	
				subobjectlevel = 3
				max select all
				currentSelection.modifiers[#Edit_Poly].ConvertSelection #Border #Vertex
				subobjectlevel = 1
				currentSelection.modifiers[#Edit_Poly].PopupDialog #WeldVertex
			)
			else if (ClassOf $.baseObject == Editable_Poly) then
			(
				modPanel.setCurrentObject $.baseObject node:$
				subobjectlevel = 3
				max select all
				currentSelection.EditablePoly.ConvertSelection #Border #Vertex
				subobjectlevel = 1
				currentSelection.EditablePoly.popupDialog #WeldSelected
			)

			
		)
		)

		

