-----------------------------------------------------------------------
-- Inverse See Through
-----------------------------------------------------------------------
-- same as see-trough but inverted to all visible geo in the viewport
-- helps with aligning geometry to other geometry that is tucked in oder under some other geometry making it hard to see / snap geo to
-- similar to Ghost Mode in Zbrush
-----------------------------------------------------------------------
-- Usage:
-- select object(s) to ghost and hit hotkey / button
-- if the same object(s) is selected and you hit hotkey /button again and you exit out of ghostmode
-- selecting a different object or going into isolate mode, thus changing the inverted selction will cause the script to run again
-----------------------------------------------------------------------

macroScript InverseSeeThrough
	category:"ST3E_Inspection"
	toolTip:"Inverse See-Through "
	ButtonText:"InverseSeeThrough"
	(

	-----------------------------------------------------------------------
	-- persitent variables
	-----------------------------------------------------------------------
	
	persistent global prevSelection
	persistent global prevInvertedSelection

	-----------------------------------------------------------------------
	-- code starts here
	-----------------------------------------------------------------------
	--get / collect all objects that are visible in the viewport into an array
	local visibleObjectsInViewport = (for o in objects where not o.isHiddenInVpt collect o)

	if (selection.count > 0) then
	(
		--------------------------------------------------------------------
		-- local var
		--------------------------------------------------------------------
		-- flag selectionmismatch
		local flagMismatch = false
		--populate the inverted selection with all objects visible
		local invertedCurrentSelection = visibleObjectsInViewport

		-- remove the objects from the list that are present in selection, exclude the ones that are not visble in the viewport
		for selectedObj = 1 to selection.count where not selection[selectedObj].isHiddenInVpt do deleteItem invertedCurrentSelection (findItem invertedCurrentSelection selection[selectedObj]) 

		-- make our base selection solid / non xray
		for i = 1 to selection.count do selection[i].xray = false

		-- perform first time undefined check, if undefined set the list as we assume a fresh scene / start
		if (prevSelection == undefined OR prevInvertedSelection == undefined) do
		(
			prevSelection = selection 
			prevInvertedSelection = invertedCurrentSelection 
		)

		--check if the prev Selection and the previous inverted selection matches our current selection and inverted selection
		if (prevSelection != undefined AND prevInvertedSelection != undefined) then
		(
			for i = 1 to (amax prevInvertedSelection.count invertedCurrentSelection.count) while not flagMismatch do if (prevInvertedSelection[i] != invertedCurrentSelection[i]) do flagMismatch = true
			for i = 1 to (amax prevSelection.count selection.count) while not flagMismatch do if (prevSelection[i] != selection[i]) do flagMismatch = true
		)

		-- if the selection is different we just update the match list for the next check but proceed in the code
		if flagMismatch then
		(		
			prevSelection = selection
			prevInvertedSelection = invertedCurrentSelection 
		)
		-- if we have the same selection, meaning we want to exit out, we clear the array list and dont proceed in code
		else 
		(	
			prevSelection = #()
			prevInvertedSelection = #()
		)

		-- if we didnt stop the script we set the inverted selection to xray mode
		if flagMismatch then for i = 1 to invertedCurrentSelection.count do invertedCurrentSelection[i].xray = true
		-- otherwise set all objects to non xray
		else for o in visibleObjectsInViewport do o.xray = false
	)
	else
	(
		-- nothing selected make it all solid and clear the array
		prevSelection = #()
		prevInvertedSelection = #()
		for o in visibleObjectsInViewport do o.xray = false
	)	
	redrawViews()
)

