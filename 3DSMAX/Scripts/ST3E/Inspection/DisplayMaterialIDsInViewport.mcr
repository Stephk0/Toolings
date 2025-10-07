---------------------------------------------------------------------
-- Display Material IDs in Viewport
-- by Stephan Viranyi https://www.artstation.com/stephko
-- Feel free to share and extend to your wishes and msg me for any questions or feedback at stephko@viranyi.de
-- 2023
-- TODO: implement callback mechanism if the mesh selection has changed so we update currentMod and nodeSelection only when we change selections and dont "Get" them all the time
---------------------------------------------------------------------
	
macroScript DisplayMaterialIDsInViewport
category:"ST3E_Inspection"
toolTip:"Display Material IDs in Viewport"	
(

	--------------------
	-- settings
	--------------------

	global toggleDisplayIDs = 0 -- global to save the toggle state in 0 = off, 1 = on
	
	--------------------
	-- internal
	--------------------

	--to prevent memory leak it is recommended to cache often used functions and vars. especially GW functions

	local currentMod
	local setTransform = gw.setTransform (Matrix3 1)
	local updateScreen = gw.UpdateScreen()
	local textdisplay = gw.text
	local nodeSelection
	local getFaceCenter = polyop.getFaceCenter
	local getFaceMatID = polyop.getFaceMatID
	local getFaceSelection = polyop.getFaceSelection 
	local getModOrObject = Filters.GetModOrObj()
	--------------------
	-- viewport feedback
	--------------------
	UnregisterRedrawViewsCallback GW_DisplayMaterialIDs

	fn GW_DisplayMaterialIDs =
	(
		currentMod = Filters.GetModOrObj()
		nodeSelection = selection[1]
		
		if nodeSelection != undefined and currentMod != undefined and toggleDisplayIDs == 1 and Filters.Is_EPoly() do -- and classof selection[1] != Editable_mesh do
		(
			setTransform
			case ClassOf currentMod of 
			(
				Editable_Poly:for face in (getFaceSelection currentMod) do textdisplay  (getFaceCenter currentMod face node:nodeSelection ) ((getFaceMatID currentMod face ) as string) color:White
				Edit_Poly:for face in (currentMod.GetSelection #Face) do textdisplay  (currentMod.getFaceCenter face) ((currentMod.GetFaceMaterial  face ) as string) color:White
			)

			updateScreen
		)	

	)

	UnregisterRedrawViewsCallback GW_DisplayMaterialIDs
	registerRedrawViewsCallback GW_DisplayMaterialIDs

	--on isEnabled do Filters.Is_EPoly() -- only work if EP

	on isChecked do toggleDisplayIDs == 1 --Button checked state based on toggle
	
	on execute do 
	(
		--init variables for the first time
		setTransform = gw.setTransform (Matrix3 1)
		updateScreen = gw.UpdateScreen()
		textdisplay = gw.text
		getFaceCenter = polyop.getFaceCenter
		getFaceMatID = polyop.getFaceMatID
		getFaceSelection = polyop.getFaceSelection 
		getModOrObject = Filters.GetModOrObj()
		
		--toggle mechanism
		if toggleDisplayIDs == 0 then toggleDisplayIDs = 1
		else toggleDisplayIDs = 0
		
	)
)

