-----------------------------------------------------------------------
-- Smart Isolate
-----------------------------------------------------------------------
-- Isolate as always, except its a toggle if you have the same selection or no selection, isolate further when your selection has changed
-- this negates the need for an "exit" button as you can always exit out when you have the same/no selection active
-- Additionally fixes the camera changing positon and orientaion when entering/exiting isolate mode

-----------------------------------------------------------------------
-- Usage:
-- replace original isolate hotkey
-- select object(s) to isolate. When not in isolate it will go into isolate mode. keeping the same selection or selecting nothing exits isolate mode. changin the selection re-enters isolate mode with the active selection
-- you can place a button in the toolbar to indicate if you are in isolate mode or not
-----------------------------------------------------------------------
-- only available max 2013+

macroScript SmartIsolate
	category:"ST3E_Inspection"
	toolTip:"Smart Isolate (Replace Isolate View) "
	ButtonText:"Isolate"
	(
-----------------------------------------------------------------------
	-- persitent variables
	-----------------------------------------------------------------------
	--store selection to check if its the same
	persistent global prevSelection
	--if the user creates a button, reflect the state based on if we are in isolate mode or not
	on isChecked return IsolateSelection.IsolateSelectionModeActive()
	on execute do 
	(
		-- only available max 2013+
		if ((maxVersion())[1] < 15000) then (messageBox ("This feature is only available Max 2013+ :(") title:"Max 2013+ Feature")
		--autodesk hiding useful options :). this essentially enables the isolate view to not change pers/zoom level in all views
		if IsolateSelection.ZoomExtents then IsolateSelection.ZoomExtents = false

		fn IsolateMode mode pSelection =
		(
			--update previous selection list for next check
			prevSelection = pSelection
			--store viewport matrix and set after isolating
			--local VPTM = viewport.getTM()
			case (mode as integer) of
			(
				0:(IsolateSelection.ExitIsolateSelectionMode())
				1:(IsolateSelection.EnterIsolateSelectionMode())
			)
			-- i guess thats redundant as ZoomExtents is fixing this issue
			--viewport.setTM VPTM
		
		)

		if (selection.count > 0) then
		(
			--mismatch flag
			local flagMismatch = false
			-- perform first time undefined check, if undefined set the list as we assume a fresh scene / start
			if prevSelection == undefined do prevSelection = selection as array

			--if the selection is differing from previous selection
			if prevSelection != undefined do for i = 1 to (amax prevSelection.count selection.count) while not flagMismatch do if (prevSelection[i] != selection[i]) do flagMismatch = true

			-- if the selection is different we just update the match list for the next check and (re)enter isolate mode
			if flagMismatch then IsolateMode 1 (selection as array)

			-- if we have the same selection, meaning we want to exit out
			else IsolateMode 0 #()
			
			
		)
		else IsolateMode 0 #()
	
		redrawViews()
	)
	

	
)

