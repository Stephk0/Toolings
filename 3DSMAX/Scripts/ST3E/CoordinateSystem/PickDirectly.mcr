macroScript PickCoordsysDirectly
	category:"StephkoCustom"
	toolTip:"PickCoordsysDirectly "
	ButtonText:"PickCoordsysDirectly"
	--------------------------------------------------------------------
	-- PickCoordsysDirectly
	--------------------------------------------------------------------
	-- pick a foreign reference coordinate system directly from a toolbar or hotkey instead of going thrugh the reference coordinate system dropdown
	--------------------------------------------------------------------
	-- TODO: check for the bug that is being throw
	-- return to prev command mode
(
	toBeSelected = pickObject count:1 forceListenerFocus:false
	
	if (toBeSelected != undefined) do
	(
	toolmode.commandmode = #MOVE
	toolMode.coordsys toBeSelected
	toolmode.commandmode = #ROTATE
	toolMode.coordsys toBeSelected
	toolmode.commandmode = #SQUASH
	toolMode.coordsys toBeSelected
	toolmode.commandmode = #NUSCALE
	toolMode.coordsys toBeSelected
	toolmode.commandmode = #USCALE
	toolMode.coordsys toBeSelected
	)
	
)

macroScript PickCoordsysDirectlyAndCenterPivot
	category:"StephkoCustom"
	toolTip:"Pick Coordsys Directly And center Pivot "
	ButtonText:"PickCoordsysDirectlyAndCenterPivot"
	--------------------------------------------------------------------
	-- PickCoordsysDirectlyAndCenter
	--------------------------------------------------------------------
	-- pick a foreign reference coordinate system directly from a toolbar or hotkey instead of going thrugh the reference coordinate system dropdown and set the transform center
	--------------------------------------------------------------------
(
	toBeSelected = pickObject count:1 forceListenerFocus:false
	
	if (toBeSelected != undefined) do
	(
	toolmode.commandmode = #MOVE
	toolMode.coordsys toBeSelected
	toolMode.transformCenter() 
	toolmode.commandmode = #ROTATE
	toolMode.coordsys toBeSelected
	toolMode.transformCenter() 
	toolmode.commandmode = #SQUASH
	toolMode.coordsys toBeSelected
	toolMode.transformCenter() 
	toolmode.commandmode = #NUSCALE
	toolMode.coordsys toBeSelected
	toolMode.transformCenter() 
	toolmode.commandmode = #USCALE
	toolMode.coordsys toBeSelected
	toolMode.transformCenter() 
	)
	
)
