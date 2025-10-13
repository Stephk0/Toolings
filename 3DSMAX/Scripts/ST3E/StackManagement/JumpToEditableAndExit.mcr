macroScript JumpToEditableAndExit
	category:"ST3E_StackManagement"
	toolTip:"Jump / Open To Editable or Exit Editable"
	ButtonText:"JumpToEditableAndExit"
	(
		-----------------------------------------------------------------------
		-- Jump to Editable or exit editable
		-----------------------------------------------------------------------
		-- jumps to the next plausible editable content within the stack
		-- either Edit_Poly / Edit_Spline Modifier that is active
		-- or jump to base Editable Poly / Editable Spline / Primitive
		-- if we have a group it ungroups it
		-- if we are in any subobjectLevel, may it be editable or other modifiers exit out
		-- credit to Joao Sapiro Josue and Arthur Rosario for orignal concept and script
		-----------------------------------------------------------------------
		-- desired subobject level to jump to in category
		local subObjModeEP = 4 -- in edit poly jump to face
		local subObjModeES = 1 -- in edit spline jump to vertex
		
		local editModIndex = 0
		local isEditableLine = false
		local validCategory = false
		local currentSelection

		on execute do
		(
			
			--check if we have a group
			for obj in selection do 
			(
				if (isGroupHead obj == true and isOpenGroupHead obj == true) then (setGroupOpen obj false) -- close it if its a open group
				else if (isGroupHead obj == true and isOpenGroupHead obj == false) do (setGroupOpen obj true) -- open it if its a closed group
			) 

			--if we have a single object
			if selection.count == 1 do 
			(
				--switch into modify mode
				currPanelMode = getCommandPanelTaskMode()
				if (currPanelMode != #modify) do max modify mode
				
				--only works with one selection
				currentSelection = selection[1]
				--index of editable modifier with the stack
				editModIndex = 0
				
				--if deal with a editable spline
				isEditableLine = classof currentSelection.baseobject == SplineShape OR classof currentSelection.baseobject == Line
				--if deal with a primitive
				validCategory = currentSelection.category == #Standard_Primitives OR currentSelection.category == #Extended_Primitives OR (currentSelection.category == #Splines AND not isEditableLine)
				
				-- exit pivot mode if its active
				if maxops.pivotmode == #pivotonly then maxops.pivotmode = #none
				-- or if deal with primitive
				else if subObjectLevel == 0 and modPanel.getCurrentObject() == currentSelection.baseobject and validCategory then 
				(
					--...toggle between end result and "edit mode"
					showEndResult = not showEndResult
				)

				--if we are in any other subobject level / edit mode (including modifiers) simply exit out
				else if subObjectLevel != 0 then
				(
					subObjectLevel = 0
					showEndResult = on
				)
				-- otherwise if nothing is going on
				else
				(
					--go through all modifiers
					for i = 1 to currentSelection.modifiers.count do
					(
						--if there is an editable poly or spline, store the index and stop
						if ((ClassOf currentSelection.modifiers[i] == Edit_Poly OR ClassOf currentSelection.modifiers[i] == Edit_Spline) AND currentSelection.modifiers[i].enabled == true) then
						(
							editModIndex = i
							exit
						)
					)

					--disable end result, putting us in "edit" mode
					showEndResult = off
				
					--if there was not edit mod found, go to baselevel
					if editModIndex == 0 then 
					(
						modPanel.setCurrentObject currentSelection.baseObject node:currentSelection
						--if we have an editable object go into subobjectLevel
						if 		(ClassOf currentSelection.baseObject == Editable_Poly) 	then subObjectLevel = subObjModeEP
						else if (isEditableLine) then subObjectLevel = subObjModeES
						showEndResult = off
					)
					--otherwise select first found edit mod
					else 
					(
						modPanel.setCurrentObject currentSelection.modifiers[editModIndex] node:currentSelection
						if 		(ClassOf  currentSelection.modifiers[editModIndex] == Edit_Poly) 	then subObjectLevel = subObjModeEP
						else if (ClassOf  currentSelection.modifiers[editModIndex] == Edit_Spline)	then subObjectLevel = subObjModeES
						showEndResult = off
					)
				)
			)
		)
	)		
