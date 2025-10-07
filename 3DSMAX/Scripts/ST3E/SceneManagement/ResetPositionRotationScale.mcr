-----------------------------------------
-- reset position to zero in one click
-- reset rotation in one click
-- reset scale to 100 in one click
-----------------------------------------


macroScript ResetPosition
	category:"ST3E_Management"
	toolTip:"Reset Position"
	ButtonText:"Reset Position"
(

	for obj in selection do obj.pos = [0,0,0]
	redrawViews()
)

macroScript ResetRotation
	category:"ST3E_Management"
	toolTip:"Reset Rotation"
	ButtonText:"Reset Rotation"
(
	for obj in selection do 
	(
		--local prevPosition = obj.pos
		--obj.rotation = (quat 0 0 0 1)
		--obj.pos = prevPosition
		in coordsys (transmatrix obj.transform.pos) obj.rotation = (quat 0 0 0 1)
	)
	redrawViews()
)

macroScript ResetScaleTo100
	category:"ST3E_Management"
	toolTip:"Reset Scale"
	ButtonText:"Reset Scale"
(
	for obj in selection do obj.scale = [1,1,1]
	redrawViews()
)
