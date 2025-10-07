---TODOS:
-- sort node events so not all shit is called all the time if not neede. i.e. vert


macroScript MatIDToolbox
	category:"ST3E_Toolboxes"
	toolTip:"Material ID Toolbox"
	ButtonText:"MatIDToolbox"
(
	global selectionChangeCallback 			--registered callback
	global subselectionChangeCallback
	--con = dotNetClass "system.windows.Forms.Control"

	persistent global compactModeEnabled	
	persistent global lastHeightBeforeCompacting	
	-------------------------------------------------------
	---- persitent vars -----------------------------------
	-------------------------------------------------------	
	--persitent vars, TODO: replace with ini	
	persistent global disableAllFaceMode
	--rolled up bool to restore prev opened rollup states
	persistent global TransferRolledUp
	persistent global GetSelRolledUp
	persistent global SetMatRolledUp
	--generic material list length setting
	persistent global genericMaterialListLength
	--string auto copy
	persistent global autoCopyToClipboard
		
	-------------------------------------------------------
	---- cached material and list -------------------------
	-------------------------------------------------------			
	--list for materials, eihter generic or generated from material assigned to selection
	persistent global cachedMaterialList
	--material we test against so we only rebuild our material list when there is actually a different material
	persistent global cachedMaterial
		
	-------------------------------------------------------
	---- globally defined functions -----------------------
	-------------------------------------------------------	
	global EvaluateEditMode
	global ToggleCompactMode
	
	-------------------------------------------------------
	---- info transfer ------------------------------------
	-------------------------------------------------------
	local matIdString

	-------------------------------------------------------
	---- set mat ID UI ------------------------------------
	-------------------------------------------------------
	persistent global setMatIDcustomMatID

	local setMatMode 	= 1 						--0 = no selection 1 = EP , 2= Spline, 3= Edit Material Mod Value, 4= Add Material Mod
	local setMatEPMode 	= 1 						--1 = v , 2 = e, 3 = f, 4 =all

	local setMatModeColorEditPoly 	= [255,0,0] 	--when in edit poly
	local setMatModeColorSpline 	= [0,255,0]		--when in edit spline
	local setMatModeColorMatMod 	= [128,0,255]	--when in material modifier
	local setMatModeColorAddMatMod 	= [255,0,255]	--when about to add Material as modifier (ie neither ep nor mat modifier)
	--long descriptions
	local setMatModeTextEPVert		= "Face sharing Vert" 					--when in edit poly vert mode
	local setMatModeTextEPEdge 		= "Face sharing Edge" 					--when in edit poly edge mode
	local setMatModeTextEPFace 		= "Face Selection" 						--when in edit poly face mode
	local setMatModeTextEPFaceAll 	= "All Faces" 							--when in edit poly but no suboject mode or face selected	
	local setMatModeTextSpline 		= "Spline Selection" 					--when in spline poly
	local setMatModeTextAddMatMod 	= "New Material Modifier"				--when about to add Material as modifier (ie neither ep nor mat modifier)
	local setMatModeTextMatMod 		= "Material Modifer Value"				--when in material modfier
	local setMatModeTextNoSel		= "Nothing Selected"					--nothing selected
	
	--compact descriptions
	local setMatModeTextEPVertCompact		= "  \x25AA" 					--when in edit poly vert mode
	local setMatModeTextEPEdgeCompact 		= "  \x2044" 					--when in edit poly edge mode
	local setMatModeTextEPFaceCompact 		= "  \x2588" 					--when in edit poly face mode
	local setMatModeTextEPFaceAllCompact 	= "FA:" 						--when in edit poly but no suboject mode or face selected	
	local setMatModeTextSplineCompact 		= "Sp:" 						--when in spline poly
	local setMatModeTextAddMatModCompact 	= "+M"							--when about to add Material as modifier (ie neither ep nor mat modifier)
	local setMatModeTextMatModCompact 		= "M:"							--when in material modfier
	local setMatModeTextNoSelCompact		= "--"							--nothing selected
	-------------------------------------------------------
	---- window resize vars  ------------------------------
	-------------------------------------------------------
	local MIDToolbox
	local mainWindowDefaultWidth = 192
	local baseWindowHeight = 176 -- 24 px per line of rollout
	local currentWindowHeight = baseWindowHeight


	-------------------------------------------------------
	---- init main window  --------------------------------
	-------------------------------------------------------
	--if (MIDToolbox == undefined) do MIDToolbox = newRolloutFloater "Material ID Toolbox" mainWindowDefaultWidth baseWindowHeight
	
	-------------------------------------------------------
	---- init editor variables  ---------------------------
	-------------------------------------------------------
	
	fn InitEditorVars =
	(
		if lastHeightBeforeCompacting == undefined 	do lastHeightBeforeCompacting = baseWindowHeight
		if disableAllFaceMode == undefined 			do disableAllFaceMode = true
		if autoCopyToClipboard == undefined 		do autoCopyToClipboard = true
		if genericMaterialListLength == undefined 	do genericMaterialListLength = 32
		if setMatIDcustomMatID == undefined 		do setMatIDcustomMatID = 1
		if compactModeEnabled == undefined 			do compactModeEnabled = true
		if TransferRolledUp == undefined 			do TransferRolledUp = true
		if GetSelRolledUp == undefined 				do GetSelRolledUp = true
		if SetMatRolledUp == undefined 				do SetMatRolledUp = true
		
	)

	-------------------------------------------------------
	---- UI resize Window functions  ----------------------
	-------------------------------------------------------

	fn MainUI_ResizeWindow floaterRollout state =
	(
		--get current size	
		currentWindowHeight = MIDToolbox.size.y
		--expand height based on rolled up state
		if (floaterRollout != undefined) do if (state == true) then currentWindowHeight += floaterRollout.height else currentWindowHeight -= floaterRollout.height
		--if we are smaller than the base window height
		if (currentWindowHeight < baseWindowHeight) then currentWindowHeight = baseWindowHeight
		MIDToolbox.size.y = currentWindowHeight
	)
	
	fn MainUI_ClampWindow height =
	(
		if compactModeEnabled != true then
		(
		if (height < baseWindowHeight) then height = baseWindowHeight
		MIDToolbox.size.y = height
		)
	)
	
	fn MainUI_CompactModeWindow state =
	(

		if (state == true) then
		(
			MIDToolbox.size.y = 44
			MIDToolbox.lockheight = true
			MIDToolbox.lockwidth = true
		)
		else(
			MIDToolbox.lockheight = false
			MIDToolbox.size.y = lastHeightBeforeCompacting
		)
	)
	


	-------------------------------------------------------
	---- UI update material lists  ------------------------
	-------------------------------------------------------

	fn MaterialListUpdateUI mList =
	(
		if compactModeEnabled != true then
		(
		MIDToolbox.rollouts[3].lbx_MaterialsSetList.items = mList
		MIDToolbox.rollouts[4].lbx_setMaterialFromList.items = mList
		)
		MIDToolbox.rollouts[1].ddl_SetMatListCompact.items = mList
	)

	fn MaterialListFromGeneric =
	(
		cachedMaterialList = #()
		for i = 1 to genericMaterialListLength do
		(
			cachedMaterialList[i] = "[" + (formattedprint i format:"03d" ) + "]" + " Generic Material ID"
		)
		MaterialListUpdateUI (cachedMaterialList)
	)

	fn MaterialListFromMultiMaterial mat =
	(
		-- cache mat to test in update
		cachedMaterial = mat
		--clear list
		cachedMaterialList = #()
		-- when you find a multi material...
		if (classof mat == multimaterial) then
		(
			-- loop through the names
			for n=1 to mat.names.count do
			(
				--format from single digit to 3 digit ie 1 > 001
				local matIDNumberFormat = "[" +  (formattedprint n format:"03d" ) + "]"
				if mat.materiallist[n] != undefined then cachedMaterialList[n] = matIDNumberFormat + mat.materiallist[n].name
				else cachedMaterialList[n] = matIDNumberFormat + "Undefined Material"
			)
				MaterialListUpdateUI (cachedMaterialList)
			)
		else 
		(
		-- set generic list if there is no multimat
		 MaterialListFromGeneric()
		)
	)

	-------------------------------------------------------
	---- UI info transfer mat id string  ------------------
	-------------------------------------------------------


	fn GetMatIDString ep faces =
	(
		local matIDs = #()
		--limits to first 32 faces not 32 of selcted faces
		--faces.count = 32
		--perfomance optimzation, only collects the string for the first of defined selected faces in options
		--TODO: expose to settings
		
			local iterator = 0
			local iteratorLimit = 2000
			for face in faces while iterator <= iteratorLimit do
			(
				local faceMatID = ep.GetFaceMaterial face
				appendIfUnique matIDs faceMatID
				iterator += 1
			)
		
	
		return matIDs
	)

	fn MatInfoTransferSetMatIDString ep faces = 
	(
		-- printAllElements enables the array to be displayed in full not just 20 entries...
		
		matIdString = with printAllElements on (GetMatIDString ep faces) as string 
		matIdString =  trimLeft (trimRight (matIdString) ")") "#("
		matIdString =  substituteString matIdString " " ""
		--compact mode text field
		MIDToolbox.rollouts[1].edt_matIDString.text = matIdString
		--advanved mode text field
		if compactModeEnabled != true then MIDToolbox.rollouts[2].edt_matIDString.text = matIdString
		-- auto copy / copy to bg
		if autoCopyToClipboard then setclipboardText matIdString 
		
	)

	fn MatInfoSetMatIDStringMatModifierMode val = 
	(
		matIdString = val as string 
		MIDToolbox.rollouts[1].edt_matIDString.text = matIdString
		if compactModeEnabled != true then MIDToolbox.rollouts[2].edt_matIDString.text = matIdString
		if autoCopyToClipboard then setclipboardText (matIdString)
	)

	-------------------------------------------------------
	---- UI Set Mat  --------------------------------------
	-------------------------------------------------------

	fn SetMatUpdateSetCustomMatUI val = 
	(
		--set the interface button text to the current spinner value from settings
		if compactModeEnabled != true then MIDToolbox.rollouts[4].btn_setMatCustom.text = val as string
	)

	fn SetMatModeColorUI color = 
	(
		if compactModeEnabled != true then 
		(
		MIDToolbox.rollouts[4].lbl_currentSetMatMode.color = color
		)
		MIDToolbox.rollouts[1].lbl_currentSetMatModeCompact.color = color
	)

	fn SetMatModeTextUI text compactText = 
	(
		if compactModeEnabled != true then 
		(
		MIDToolbox.rollouts[4].lbl_currentSetMatMode.enabled = false
		MIDToolbox.rollouts[4].lbl_currentSetMatMode.text = ""
		MIDToolbox.rollouts[4].lbl_currentSetMatMode.text = text
		)
		MIDToolbox.rollouts[1].lbl_currentSetMatModeCompact.enabled = false
		MIDToolbox.rollouts[1].lbl_currentSetMatModeCompact.text = ""
		MIDToolbox.rollouts[1].lbl_currentSetMatModeCompact.text = compactText
		
		--MIDToolbox.rollouts[3].grp_setMatShift.text = "Shift ID: " + text
		--MIDToolbox.rollouts[3].grp_setMatSet.text = "Set ID: " + text
	)

	fn SetMatShiftButtonsToggle toggle = 
	(
		if compactModeEnabled != true then
		(
		MIDToolbox.rollouts[4].btn_setMatDecrement10.enabled = toggle
		MIDToolbox.rollouts[4].btn_setMatDecrement05.enabled = toggle	
		MIDToolbox.rollouts[4].btn_setMatDecrement01.enabled = toggle
		MIDToolbox.rollouts[4].btn_setMatIncrement01.enabled = toggle
		MIDToolbox.rollouts[4].btn_setMatIncrement05.enabled = toggle
		MIDToolbox.rollouts[4].btn_setMatIncrement10.enabled = toggle	
		)
		MIDToolbox.rollouts[1].btn_ShiftMatCompact.enabled = toggle
		MIDToolbox.rollouts[1].edt_matIDString.enabled = toggle	
		MIDToolbox.rollouts[1].btn_SelectFromSelectedMatID.enabled = toggle			
	)
	
	fn SetMatFeedbackSelectionUI modifierInput facelist = 
	(
		if compactModeEnabled != true then
		(
			local selectionIds = (GetMatIDString modifierInput facelist)
			if selectionIds.count > 1 then MIDToolbox.rollouts[4].lbx_setMaterialFromList.selection = 0
			else if selectionIds.count > 0 then MIDToolbox.rollouts[4].lbx_setMaterialFromList.selection =  selectionIds[1]
			else MIDToolbox.rollouts[4].lbx_setMaterialFromList.selection =  0
		)
	)

	fn SetMatFeedbackSelectionMatModeUI val = 
	(
		if compactModeEnabled != true then MIDToolbox.rollouts[4].lbx_setMaterialFromList.selection = val
	)

	-------------------------------------------------------
	---- select mat id string  ----------------------------
	-------------------------------------------------------
	fn selectFacesFromList selectedMatIDItems =
	(
		local selectedObj = selection[1]
		
		activeMod = Filters.GetModOrObj()
		if (Filters.Is_EPoly()) then
		(
			subobjectlevel = 4
			if (Filters.Is_This_EditPolyMod activeMod) then
			(	
				
				local clearSelectionOn = activeMod.selectByMaterialClear
				--repeat button op for every material ID
				for matID in selectedMatIDItems do
				(
					activeMod.selectByMaterialClear = false
					activeMod.selectByMaterialID = matID - 1
					activeMod.ButtonOp #SelectByMaterial
				)
				activeMod.selectByMaterialClear = clearSelectionOn
			)
			else
			(		
				local resultingFaces = #{}
				--select by material, store the resulting faces and accumulate if unique
				for matID in selectedMatIDItems do
				(
					activeMod.selectByMaterial matID
					local selectedFacesByMaterial = activeMod.GetSelection #Face as array
					
					for face in selectedFacesByMaterial do
					(
						appendIfUnique resultingFaces face
					)
				
				)
				activeMod.SetSelection #Face resultingFaces
			)
		)
	)
	
	-------------------------------------------------------
	---- Set / Shift Mat ID functions  ----------------------------
	-------------------------------------------------------		

	fn SetMatSetMaterialID modifierInput facelist id =
	(
		undo "Set Material ID" on
		(
			case ClassOf (modifierInput) of
			(
				Editable_Poly:
				(
					--completeredraw()
					--local prevFaceSel = modifierInput.GetSelection #Face
					modifierInput.GetSelection #Face
					--modifierInput.SetSelection #Face facelist
					modifierInput.setMaterialIndex id 1
					--modifierInput.SetSelection #Face prevFaceSel
					
				)
				Edit_Poly:
				(
					
					--local prevFaceSel = modifierInput.GetSelection #Face
					--modifierInput.SetSelection #Face facelist 
					modifierInput.SetOperation #SetMaterial
					modifierInput.materialIDToSet = id-1
					modifierInput.Commit ()
					--modifierInput.SetSelection #Face prevFaceSel
					
				)
				Materialmodifier:
				(
					modifierInput.materialID = id

				) 
			)
		)
		redrawViews()
	)

	fn SetMatShiftMaterialID modifierInput facelist shiftvalue =
	(
		undo "Shift Material ID" on
		(
			case ClassOf (modifierInput) of
			(
				Editable_Poly:
				(
					with redraw off
					(
						local prevFaceSel = modifierInput.GetSelection #Face
						for face in facelist do
						(
							modifierInput.SetSelection #Face #{face}
							local faceMatID = modifierInput.GetFaceMaterial face
							--check if face mat ID is not under 0 if we shift to left
							if (faceMatID + shiftvalue > 0) then modifierInput.setMaterialIndex (faceMatID + shiftvalue) 1
							else modifierInput.setMaterialIndex 1 1
						)
						modifierInput.SetSelection #Face prevFaceSel
					)
				)
				Edit_Poly:
				(
					with redraw off
					(
						local prevFaceSel = modifierInput.GetSelection #Face
						local prevSOLevel = modifierInput.GetMeshSelLevel() 
						for face in facelist do
						(
							modifierInput.SetEPolySelLevel #Face
							modifierInput.SetSelection #Face #{face}
							modifierInput.Select #Face #{face}
							--print ((modifierInput.GetSelection #Face) as string + " is the i face")
							local faceMatID = modifierInput.GetFaceMaterial face
							modifierInput.SetOperation #SetMaterial
							--check if face mat ID is not under 0 if we shift to left
							if (faceMatID + shiftvalue > 0) then modifierInput.materialIDToSet = faceMatID + shiftvalue - 1 else modifierInput.materialIDToSet = 0
							modifierInput.Commit ()
						)
						modifierInput.SetSelection #Face prevFaceSel
						modifierInput.SetEPolySelLevel prevSOLevel
					)
				)
				Materialmodifier:
				(
					if ( modifierInput.materialID + shiftvalue > 0) then modifierInput.materialID = modifierInput.materialID + shiftvalue else modifierInput.materialID = 1
				)
			)
		)
		redrawViews()
	)
	
	-------------------------------------------------------
	---- Selection Wrapper  -------------------------------
	-------------------------------------------------------	

	fn SelectionWrapper executeFunction modifierInput var =
	(
		-----------------------------------------------------
		--- Convert our selection , may it be vert, edge, face, spline segment, material modifer to compatible modes
		--- This will make integration easier as you just use the wrapper to pass your selection through and the wrapper will take care of the rest
		------------------------------------------------------
		case setMatMode of
		(		
			1:-- ep mode
			(
				local subObjectSelection = #{}
				case setMatEPMode of
				(			
					1:-- vert to face
					(
						local storedVertSelection = modifierInput.GetSelection #Vertex as bitarray
						--We have to check if our array exceeded (ie an vert was removed), since remove(backspace) signals the correct callback but ctrl+remove doenst and throws and error :(
						if (storedVertSelection.count <= modifierInput.GetNumVertices()) then
						( 
							if (Filters.Is_This_EditPolyMod modifierInput) then modifierInput.getFacesUsingVert subObjectSelection storedVertSelection
							else subObjectSelection = polyop.getFacesUsingVert modifierInput storedVertSelection		
						)
					)
					2:-- edge / border to face
					(
						local storedEdgeSelection = modifierInput.GetSelection #Edge as bitarray
						--We have to check if our array exceeded (ie an edge was removed), since remove(backspace) signals the correct callback but ctrl+remove doenst and throws and error :(
						if (storedEdgeSelection.count <= modifierInput.GetNumEdges()) then
						(  
							if (Filters.Is_This_EditPolyMod modifierInput) then modifierInput.getFacesUsingEdge subObjectSelection storedEdgeSelection
							else subObjectSelection = polyop.getFacesUsingEdge modifierInput storedEdgeSelection	
						)
					)
					-- straight
					3: subObjectSelection = modifierInput.GetSelection #Face as bitarray
					-- all faces, can be disabled since this op can be quite expensive if there is lots of faces
					4: subObjectSelection = #{1..modifierInput.GetNumFaces()}
				)
				-- check to make sure we dont pass empty facelist, might not be needed as we disable edit mode if no sel / incompatible
				if (subObjectSelection.count > 1) then
				(
				--execute function after selection transform
				if (var != undefined) then executeFunction modifierInput subObjectSelection var
				else executeFunction modifierInput subObjectSelection

				--MatInfoTransferSetMatIDString modifierInput subObjectSelection			
				)
			)
			-- splinemode
			2: print "spline edit mode"
			-- Edit material mod mode
			3:
			(
				executeFunction modifierInput undefined var
				MatInfoSetMatIDStringMatModifierMode modifierInput.materialID
			)
			-- Add Material Mod
			4:(print "Add Material mode")
		)
	)

	fn EvaluateMainEditMode =
	(
		--TODO implement this, disconnect selection wrapper and edit mode
		if (selection.count == 0) then 
		(
			setMatMode = 0
			SetMatModeColorUI [64,64,64] 
			SetMatModeTextUI setMatModeTextNoSel
		)
	)

	fn EvaluateEditMode =
	(
		-- determine the edit mode we want to be in.
		--if in valid mode
		--local st, et
		--st = timeStamp()

		if (selection.count == 0 or subobjectlevel == undefined) then 
		(
			--nothing is selected, edit mode disabled
			setMatMode = 0
			SetMatModeColorUI [64,64,64] 
			SetMatModeTextUI setMatModeTextNoSel setMatModeTextNoSelCompact
		)
		else
		(
			local validEpEditMode = Filters.Is_EPoly()
			local validMatModMode = (ClassOf (modPanel.getCurrentObject()) == Materialmodifier)
			local validSplineMode = Filters.Is_EditSpline()

			
				if (validEpEditMode) then
				(
					setMatMode = 1
					SetMatModeColorUI setMatModeColorEditPoly
					
					ep = Filters.GetModOrObj()
					local somethingSelected = false
					if (subobjectlevel > 0) then somethingSelected = ((ep.GetSelection #CurrentLevel) as array).count > 0

					case subobjectlevel of
					(
						0:
						(
							if (disableAllFaceMode != true) then
							(
								SetMatModeTextUI setMatModeTextEPFaceAll setMatModeTextEPFaceAllCompact
								setMatEPMode = 4
							)
							else
							( 
								setMatMode = 0
								SetMatModeColorUI [64,64,64] 
								SetMatModeTextUI setMatModeTextNoSel setMatModeTextNoSelCompact
							)
						)
						1:
						(
							setMatEPMode = 1
							SetMatModeTextUI setMatModeTextEPVert setMatModeTextEPVertCompact
						)					
						2: 				
						(
							setMatEPMode = 2
							SetMatModeTextUI setMatModeTextEPEdge setMatModeTextEPEdgeCompact
						) 
						3:
						(
							setMatEPMode = 2
							SetMatModeTextUI setMatModeTextEPEdge setMatModeTextEPEdgeCompact
						) 
						4: 
						(
							setMatEPMode = 3
							SetMatModeTextUI setMatModeTextEPFace setMatModeTextEPFaceCompact
						) 
						5:
						(
							setMatEPMode = 3
							SetMatModeTextUI setMatModeTextEPFace setMatModeTextEPFaceCompact
						) 
					)

					if somethingSelected == false then
					(
						if (disableAllFaceMode != true) then
						(
							SetMatModeTextUI setMatModeTextEPFaceAll setMatModeTextEPFaceAllCompact
							setMatEPMode = 4
						)
					) 
					--perf?
					SelectionWrapper SetMatFeedbackSelectionUI ep undefined
					SelectionWrapper MatInfoTransferSetMatIDString ep undefined

				)
				else if (validSplineMode) then 
				(
					setMatMode = 2
				)
				else if (validMatModMode) then
				(
					modifier = modPanel.getCurrentObject()
					MatInfoSetMatIDStringMatModifierMode modifier.materialID
					SetMatFeedbackSelectionMatModeUI modifier.materialID

					SetMatModeColorUI setMatModeColorMatMod
					SetMatModeTextUI setMatModeTextMatMod setMatModeTextMatModCompact
					setMatMode = 3
				)
				else
				(
					SetMatFeedbackSelectionMatModeUI 0
					
					SetMatModeColorUI setMatModeColorAddMatMod 
					SetMatModeTextUI setMatModeTextAddMatMod setMatModeTextAddMatModCompact
					setMatMode = 4
				)
				SetMatShiftButtonsToggle (validEpEditMode OR validMatModMode)
			
		--et = timeStamp()
		--print (et - st)
		)
	)	
	-------------------------------------------------------
	---- Update Selection  --------------------------------
	-------------------------------------------------------		

	fn updateSelection callback id =
	(
		--if we change the selection check if the material has changed
		with redraw off
		(
			with undo off
			(
				if (selection.count == 1) then
				(
					--update material list if neccesery
					if (selection[1].mat != undefined AND selection[1].mat != cachedMaterial ) do MaterialListFromMultiMaterial (selection[1].mat)
				)
			)	
		)

		--EvaluateEditMode()
	)

	fn updateSubSelection callback id =
	(
		--if we update the subselection, reevaluate the edit mode
		with redraw off
		(
			with undo off
			(
				EvaluateEditMode()
			)
		)
	)
	
	-------------------------------------------------------
	---- Callbacks  ---------------------------------------
	-------------------------------------------------------		
	
	fn killCallback =
	(
		--reset the callbacks. nodeevent callback needs undef and garbagecollector clean for modpanel selction change we have to remove it via removescripts
		selectionChangeCallback = undefined
		callbacks.removeScripts id:#updateSelectionOnMod
		--callbacks.removeScripts id:#sceneUndoUpdate
		gc()
	)
	
	fn createCallback =
	(
		selectionChangeCallback = NodeEventCallback selectionChanged:updateSelection subobjectSelectionChanged:updateSubSelection topologyChanged:updateSubSelection --all:updateSubSelection --modelOtherEvent:ModpanelChange11
		callbacks.addScript #modPanelSelChanged "EvaluateEditMode()" id:#updateSelectionOnMod
		--callbacks.addScript #sceneUndo "EvaluateEditMode()" id:#sceneUndoUpdate
	)

	-------------------------------------------------------
	---- Rollouts  ----------------------------------------
	-------------------------------------------------------
	rollout HeaderLeanModeOff "Compact Mode" width:176 height:25
	(
		button 'btn_compactToggle' "\x25BC" pos:[0,0] width:16 height:16 align:#left toolTip:"(Un)Fold to Compact Mode"
		edittext 'edt_matIDString' "" pos:[16,0] width:56 height:16 align:#left toolTip:"Material ID String"
		button 'btn_SelectFromSelectedMatID' "S" pos:[74,0] width:16 height:16 toolTip:"Click:Select all faces sharing the same material ID of your current selection.
Click+Ctrl: Contagious mode (select till border)" align:#left
		HyperLink 'lbl_currentSetMatModeCompact' "M+" pos:[90,0] width:16 height:16 align:#left  toolTip:"Current Set Material ID Mode"
		edittext 'edt_SetMatTypeInCompact' "" text:(setMatIDcustomMatID as string) pos:[104,0] width:24 height:16 align:#left toolTip:"Set Material ID Custom Type-In"			
		button 'btn_SetMatCompact' "\x2555" pos:[128,0] width:16 height:16 toolTip:"Click: Set Mat ID Custom (Last Type-In or Spinner)
Click+Ctrl: Set Mat ID 5 
Click+Shift: Set Mat ID 10 
Click+Alt: Set Mat ID 1 
Click+Ctrl+Shift: Set Mat ID 100"
		button 'btn_ShiftMatCompact' "\x2194" pos:[144,0] width:16 height:16 toolTip:"Click: Shift + 1 
Click+Ctrl: Shift + 5 
Click+Shift: Shift + 10
Click+Ctrl+Shift: Shift + 100		
Click+Alt+Any: Negative Direction
"	
		dropdownList 'ddl_SetMatListCompact' "" pos:[160,-5] width:16 height:64 align:#left toolTip:"Set Material ID from List"
		
		
		on HeaderLeanModeOff close do
			killCallback()
		
		on HeaderLeanModeOff resized val do MainUI_ClampWindow val.y
			
		on HeaderLeanModeOff rolledUp state do MIDToolbox.rollouts[1].open = true
		
		on btn_compactToggle pressed do
		(
			compactModeEnabled = NOT compactModeEnabled
			ToggleCompactMode compactModeEnabled
		)
		on btn_SelectFromSelectedMatID pressed do
		(
			--TODO: implemnt select by material ID regular / facesearch variant
		)
		
		on edt_matIDString entered text do
		(
			if (text as integer != undefined) then
			( 
				SelectionWrapper SetMatSetMaterialID (modPanel.getCurrentObject()) (text as integer)
				--setMatIDcustomMatID = (text as integer)
			)
			--edt_SetMatTypeInCompact.text = ""	
		)

		on edt_SetMatTypeInCompact entered text do
		(
			if (text as integer != undefined) then
			( 
				SelectionWrapper SetMatSetMaterialID (modPanel.getCurrentObject()) (text as integer)
				setMatIDcustomMatID = (text as integer)
			)
			--edt_SetMatTypeInCompact.text = ""	
		)
		on btn_SetMatCompact pressed do
		(
			
			if (keyboard.shiftPressed and keyboard.controlPressed) then SelectionWrapper SetMatSetMaterialID (modPanel.getCurrentObject()) 100
			else if (keyboard.controlPressed) then SelectionWrapper SetMatSetMaterialID (modPanel.getCurrentObject()) 5
			else if keyboard.shiftPressed then SelectionWrapper SetMatSetMaterialID (modPanel.getCurrentObject()) 10 
			else if keyboard.altPressed then SelectionWrapper SetMatSetMaterialID (modPanel.getCurrentObject()) 1 
			else SelectionWrapper SetMatSetMaterialID (modPanel.getCurrentObject()) setMatIDcustomMatID
		)
		on btn_ShiftMatCompact pressed do
		(	
			--negative dir
			if keyboard.altPressed then
			(
				if (keyboard.shiftPressed and keyboard.controlPressed) then SelectionWrapper SetMatShiftMaterialID (modPanel.getCurrentObject()) -100
				else if keyboard.controlPressed then SelectionWrapper SetMatShiftMaterialID (modPanel.getCurrentObject()) -5
				else if keyboard.shiftPressed then SelectionWrapper SetMatShiftMaterialID (modPanel.getCurrentObject()) -10 
				else SelectionWrapper SetMatShiftMaterialID (modPanel.getCurrentObject()) -1
			)
			-- positive dir
			else
			(
				if (keyboard.shiftPressed and keyboard.controlPressed) then SelectionWrapper SetMatShiftMaterialID (modPanel.getCurrentObject()) 100
				else if keyboard.controlPressed then SelectionWrapper SetMatShiftMaterialID (modPanel.getCurrentObject()) 5
				else if keyboard.shiftPressed then SelectionWrapper SetMatShiftMaterialID (modPanel.getCurrentObject()) 10 
				else SelectionWrapper SetMatShiftMaterialID (modPanel.getCurrentObject()) 1	
			)
			
		)
		on ddl_SetMatListCompact selected sel do
		( 
			SelectionWrapper SetMatSetMaterialID (modPanel.getCurrentObject()) sel
		)
	)

	rollout InfoTransfer "Mat ID Info Transfer" width:176 height:48
	(
		button 'btn_AddEP' "Add EP" pos:[8,0] width:40 height:16 toolTip:"Add an Edit Poly Modifer for Face Selection above the currently selected modifier in the stack. " align:#left
		edittext 'edt_matIDString' "" pos:[8,32] width:160 height:16 align:#left
		button 'btn_copyToClipboard' "Copy" pos:[104,16] width:64 height:16 align:#left  
		checkbutton 'ckb_autoCopyToClipboard' "Rec" pos:[72,16] width:32 height:16 highlightColor:[255,0,0] checked:autoCopyToClipboard align:#left
		button 'btn_AddTySelEP' "tySelect + EP" pos:[48,0] width:72 height:16 toolTip:"Add a tySelect modifier set to face mode and a active Edit Poly Modifer for Face Selection above the currently selected modifier in the stack. " align:#left
		button 'btn32' "Sel > ty" pos:[120,0] width:48 height:16 enabled:false toolTip:"Once possible you will be able to create a tySelect modifer from you current material ID. tySelect doesnt support scripted setup so we have to wait :(" align:#left
		label 'lbl_matIDString' "Mat ID String" pos:[8,16] width:64 height:16 align:#left

		on InfoTransfer rolledUp state do (
			MainUI_ResizeWindow MIDToolbox.rollouts[2] state
			TransferRolledUp =  not state
		)
		-- force open MIDToolbox.rollouts[2].open = true
		on btn_AddEP pressed do
			AddMod EditPolyMod
		on ckb_autoCopyToClipboard changed state do
			autoCopyToClipboard = state
		on btn_AddTySelEP pressed do
		(
			if (tySelect != undefined) then AddMod tySelect
			else print "no tySelect installed"
			AddMod EditPolyMod
		)
		on btn32 pressed do
			AddMod EditPolyMod
	)

	rollout GetSelectionFromMat "Get Selection From Mat ID" width:176 height:392
	(
		button 'btn_SelMatIDs' "Sel" pos:[110,13] width:34 height:16 toolTip:"Select all faces sharing the same material ID of your current selection" align:#left
		
		multiListBox 'lbx_MaterialsSetList' "Select From Material List" pos:[8,32] width:160 height:24 align:#left

		radiobuttons 'rdo_selectOP' "List Selection OP" pos:[6,0] width:89 height:30 labels:#("=", "+", "-") columns:3 align:#left
		
		checkbutton 'ckb4' "()" pos:[144,13] width:16 height:16 toolTip:"Contagious Select (select till border)" align:#left
		GroupBox 'grp10' "Selection" pos:[104,0] width:64 height:32 align:#left
		on GetSelectionFromMat rolledUp state do
		(
			MainUI_ResizeWindow MIDToolbox.rollouts[3] state
			GetSelRolledUp = not state
		)
		on lbx_MaterialsSetList selected sel do selectFacesFromList (lbx_MaterialsSetList.selection)
	)
	
	rollout SetMaterials "Set Mat ID" width:176 height:408
	(
		
		label 'lbl_setMatMode' "MODE:" pos:[8,0] width:40 height:16 align:#left
		HyperLink 'lbl_currentSetMatMode' "EP Face Set" pos:[48,0] width:40 height:16 color:[255,0,0] align:#left		
		button 'btn_setMatDecrement10' "10<" pos:[8,16] width:32 height:16 toolTip:"Mat ID Shift -10" align:#left
		button 'btn_setMatDecrement05' "5<" pos:[40,16] width:24 height:16 toolTip:"Mat ID Shift -5" align:#left	
		button 'btn_setMatDecrement01' "<" pos:[64,16] width:24 height:16 toolTip:"Mat ID Shift -1" align:#left
		button 'btn_setMatIncrement01' ">" pos:[88,16] width:24 height:16 toolTip:"Mat ID Shift 1" align:#left
		button 'btn_setMatIncrement05' ">5" pos:[112,16] width:24 height:16 toolTip:"Mat ID Shift 5" align:#left
		button 'btn_setMatIncrement10' ">10" pos:[136,16] width:32 height:16 toolTip:"Mat ID Shift 10" align:#left	
		button 'btn_setMat001' "1" pos:[8,32] width:32 height:16 toolTip:"Set Mat ID 1" align:#left
		button 'btn_setMat005' "5" pos:[40,32] width:32 height:16 toolTip:"Set Mat ID 5" align:#left
		button 'btn_setMat010' "10" pos:[72,32] width:32 height:16 toolTip:"Set Mat ID 10" align:#left
		button 'btn_setMat100' "100" pos:[104,32] width:32 height:16 toolTip:"Set Mat ID 100" align:#left
		button 'btn_setMatCustom' text:(setMatIDcustomMatID as string) pos:[136,32] width:32 height:16 toolTip:"Set Mat ID Custom" align:#left
		spinner 'spn_customMatID' "Set Mat ID" pos:[72,48] width:64 height:16 range:[1,1e+06,setMatIDcustomMatID] type:#integer align:#left
		checkbutton 'ckb_autoSetCustomMatID' "From List" pos:[8,48] width:64 height:16 highlightColor:[255,0,0] toolTip:"Set automatically from List Selection" align:#left
		listbox 'lbx_setMaterialFromList' "Set Material From List" pos:[8,64] width:160 height:24 align:#left

		on SetMaterials rolledUp state do
		(
			MainUI_ResizeWindow MIDToolbox.rollouts[4] state
			SetMatRolledUp =  not state
		)
		on btn_setMatDecrement10 pressed do
			SelectionWrapper SetMatShiftMaterialID (modPanel.getCurrentObject()) -10
		on btn_setMatDecrement05 pressed do
			SelectionWrapper SetMatShiftMaterialID (modPanel.getCurrentObject()) -5
		on btn_setMatDecrement01 pressed do
			SelectionWrapper SetMatShiftMaterialID (modPanel.getCurrentObject()) -1
		on btn_setMatIncrement01 pressed do
			SelectionWrapper SetMatShiftMaterialID (modPanel.getCurrentObject()) 1
		on btn_setMatIncrement05 pressed do
			SelectionWrapper SetMatShiftMaterialID (modPanel.getCurrentObject()) 5
		on btn_setMatIncrement10 pressed do
			SelectionWrapper SetMatShiftMaterialID (modPanel.getCurrentObject()) 10
		on btn_setMat001 pressed do
			SelectionWrapper SetMatSetMaterialID (modPanel.getCurrentObject()) 1
		on btn_setMat005 pressed do
			SelectionWrapper SetMatSetMaterialID (modPanel.getCurrentObject()) 5
		on btn_setMat010 pressed do
			SelectionWrapper SetMatSetMaterialID (modPanel.getCurrentObject()) 10
		on btn_setMat100 pressed do
			SelectionWrapper SetMatSetMaterialID (modPanel.getCurrentObject()) 100
		on btn_setMatCustom pressed do
			SelectionWrapper SetMatSetMaterialID (modPanel.getCurrentObject()) setMatIDcustomMatID
		on spn_customMatID changed val do
		(
			setMatIDcustomMatID = val
			SetMatUpdateSetCustomMatUI val
		)
		on lbx_setMaterialFromList selected sel do
			( SelectionWrapper SetMatSetMaterialID (modPanel.getCurrentObject()) sel)
	)

	
	rollout Statistics "Mat ID Statistics" width:176 height:72
	(
		
		on Statistics rolledUp state do MainUI_ResizeWindow MIDToolbox.rollouts[5] state

	)

	rollout settings "Settings" width:176 height:432
	(
		checkbox 'chk1' "Auto-Expand Window" pos:[16,24] width:144 height:16 checked:true align:#left
		spinner 'spn_settingsMatListLength' "List Length" pos:[16,296] width:92 height:16 range:[1,64,20] type:#integer align:#left
		checkbox 'chk2' "Generate for undefined" pos:[16,232] width:136 height:16 align:#left
		groupBox 'grp1' "Generic Material List" pos:[8,216] width:160 height:104 align:#left
		button 'btn1' "Help" pos:[8,368] width:160 height:24 align:#left
		editText 'edt1' "Name" pos:[16,272] width:144 height:16 align:#left
		groupBox 'grp2' "Material List" pos:[8,144] width:160 height:64 align:#left
		spinner 'spn3' "List Length (px)" pos:[16,160] width:72 height:16 range:[1,64,20] type:#integer align:#left
		checkbox 'chk3' "Catch Unlisted (Deep)" pos:[16,184] width:136 height:16 align:#left
		checkbox 'chk4' "AutoCopy All Faces String" pos:[16,72] width:144 height:16 align:#left
		checkbox 'chk5' "Generate for undefined" pos:[16,248] width:136 height:16 align:#left
		groupBox 'grp3' "UI" pos:[8,8] width:160 height:40 align:#left
		groupBox 'grp4' "MatID Transfer String" pos:[8,56] width:160 height:40 align:#left
		button 'btn2' "Reset to Defaults" pos:[8,336] width:160 height:24 align:#left

		on settings rolledUp state do
			MainUI_ResizeWindow MIDToolbox.rollouts[6] state
		
		on spn_settingsMatListLength changed val do
		(
			genericMaterialListLength = val
		)
		on spn3 changed val do
		(
			genericMaterialListLength = val
		)

		on btn2 pressed do MIDToolbox.lockheight = true
			
	)

	-------------------------------------------------------
	---- add rollouts / first init-------------------------
	-------------------------------------------------------
		--TODO: rewire split this properly to INI files and global persitents
		if (MIDToolbox == undefined) do MIDToolbox = newRolloutFloater "Material ID Toolbox" mainWindowDefaultWidth baseWindowHeight
		InitEditorVars()
			
		fn ToggleCompactMode state =
		(
			--logic
			if state == true then
			(
			lastHeightBeforeCompacting = MIDToolbox.size.y
			removeRollout InfoTransfer  
			removeRollout GetSelectionFromMat   
			removeRollout SetMaterials 
			removeRollout Statistics 
			removeRollout Settings
			)
			else
			(
			addRollout InfoTransfer MIDToolbox rolledup:TransferRolledUp
			addRollout GetSelectionFromMat MIDToolbox rolledup:GetSelRolledUp  
			addRollout SetMaterials MIDToolbox rolledup:SetMatRolledUp
			addRollout Statistics MIDToolbox rolledup:true  
			addRollout Settings MIDToolbox rolledup:true
			MIDToolbox.size.y = lastHeightBeforeCompacting
			)
			--callbacks
			killCallback()
			createCallback()
			--create a material List or update
			if (cachedMaterialList == undefined ) then MaterialListFromGeneric()
			else MaterialListUpdateUI (cachedMaterialList)
			--(un)fold icons
			if state then MIDToolbox.rollouts[1].btn_compactToggle.text = "\x25BA" else MIDToolbox.rollouts[1].btn_compactToggle.text = "\x25BC"			
			--size window to compact mode if true
			MainUI_CompactModeWindow state
			--Evaluate Edit Mode after mode change
			EvaluateEditMode()
		)
		
		
		-- add compact mode rollout, which serves as main rollout and is always active
		addRollout HeaderLeanModeOff MIDToolbox rolledUp:false
		-- get the state of the compact mode and toggle accordingly
		ToggleCompactMode compactModeEnabled
		
		--set the button text according to spinner 
		SetMatUpdateSetCustomMatUI(setMatIDcustomMatID)
		--pot redundant as we check in toggle compact mode
		--EvaluateEditMode()
		
	 
)