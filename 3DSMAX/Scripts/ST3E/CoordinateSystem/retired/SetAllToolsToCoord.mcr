----------------------------------------------
-- simple extension that sets the transform coordinate pivot for all transform modes (move, rotate, scale)
-- TODO find some way get the scaling mode (nuscale, sqaush) when no activly in there
-- TODO add remaining modes
--
-- REDUNDANT: User can set constant transform in Prefernces, thus this script is not needed
--
--
---------------------------------------------

macroScript SetAllPivotsToCoordView
	category:"StephkoCustom"
	toolTip:"View All"
	ButtonText:"View All"
(
	currentMode = toolmode.commandmode
	toolmode.commandmode = #MOVE
	toolmode.coordsys #view
	toolmode.commandmode = #ROTATE
	toolmode.coordsys #view
	toolmode.commandmode = #USCALE
	toolmode.coordsys #view
	toolmode.commandmode = #NUSCALE
	toolmode.coordsys #view
	toolmode.commandmode = #SQUASH
	toolmode.coordsys #view
	
	toolmode.commandmode = currentMode
	
)

macroScript SetAllPivotsToCoordLocal
	category:"StephkoCustom"
	toolTip:"Local All"
	ButtonText:"Local All"
(
	currentMode = toolmode.commandmode
	toolmode.commandmode = #MOVE
	toolmode.coordsys #local
	toolmode.commandmode = #ROTATE
	toolmode.coordsys #local
	toolmode.commandmode = #USCALE
	toolmode.coordsys #local
	toolmode.commandmode = #NUSCALE
	toolmode.coordsys #local
	toolmode.commandmode = #SQUASH
	toolmode.coordsys #local
	
	toolmode.commandmode = currentMode
	
)


macroScript SetAllPivotsToCoordGimbal
	category:"StephkoCustom"
	toolTip:"Gimbal All"
	ButtonText:"Gimbal All"
(
	currentMode = toolmode.commandmode
	toolmode.commandmode = #MOVE
	toolmode.coordsys #gimbal
	toolmode.commandmode = #ROTATE
	toolmode.coordsys #gimbal
	toolmode.commandmode = #USCALE
	toolmode.coordsys #gimbal
	toolmode.commandmode = #NUSCALE
	toolmode.coordsys #gimbal
	toolmode.commandmode = #SQUASH
	toolmode.coordsys #gimbal
	
	toolmode.commandmode = currentMode
	
)


macroScript SetAllPivotsToCoordScreen
	category:"StephkoCustom"
	toolTip:"Screen All"
	ButtonText:"Screen All"
(
	currentMode = toolmode.commandmode
	toolmode.commandmode = #MOVE
	toolmode.coordsys #screen
	toolmode.commandmode = #ROTATE
	toolmode.coordsys #screen
	toolmode.commandmode = #USCALE
	toolmode.coordsys #screen
	toolmode.commandmode = #NUSCALE
	toolmode.coordsys #screen
	toolmode.commandmode = #SQUASH
	toolmode.coordsys #screen
	
	toolmode.commandmode = currentMode
	
)
