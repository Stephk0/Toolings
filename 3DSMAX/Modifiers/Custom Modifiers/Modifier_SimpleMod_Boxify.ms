/*
Simple Boxify Modifier
Works on any type of object. if you dont pass a selection you might have to set the pivot to the center
by Stephan Viranyi https://www.artstation.com/stephko
original by Garp http://www.scriptspot.com/3ds-max/scripts/cylindrify-modifier
Feel free to share and extend to your wishes and msg me for any questions or feedback at stephko@viranyi.de
*/
plugin simpleMod simpleBoxify
name:"Simple Boxify"
classID:#(0x55e2e5e0, 0x56362f04)
(

	local boxshape = [1,1,1] -- box shape
	
	parameters main rollout:params
	(
		amount type:#float ui:amtSpin default:100

		centerThresholdX type:#float ui:centerThresXSpin
		centerThresholdY type:#float ui:centerThresYSpin
		centerThresholdZ type:#float ui:centerThresZSpin
	)
		
	rollout params "Parameters"
	(
		spinner amtSpin "Percent" range:[0,100,100] scale:1
		spinner centerThresXSpin "Center Threshold X" type:#worldUnits range:[0,1e6,0] 
		spinner centerThresYSpin "Center Threshold Y" type:#worldUnits range:[0,1e6,0] 
		spinner centerThresZSpin "Center Threshold Z" type:#worldUnits range:[0,1e6,0] 
		button setGizmoToCenter "Set Gizmo Position to Center"
		button rstGizmoPos "Set Gizmo Position To Pivot"
		button rstGizmoScale "Reset Gizmo Scale"
		button rstGizmoRot "Reset Gizmo Rotation"
		button rstGizmoFull "Reset All"

		on rstGizmoFull pressed do this.gizmo.transform = matrix3 1
		--this should run a "first time" if there is no selection inherited from the stack. i was not able to find it but maybe there is a way to detect if there is a selection inherited
		on setGizmoToCenter pressed do this.gizmo.position = center
		
		on rstGizmoPos pressed do this.gizmo.position = [0,0,0]
		on rstGizmoScale pressed do this.gizmo.scale = [1,1,1]
		on rstGizmoRot pressed do (
			prevPosition = this.gizmo.position
			this.gizmo.rotation = quat 0 0 0 1
			this.gizmo.position = prevPosition
		)
	)

	fn lerp minVal maxVal term = (maxVal - minVal) * term + minVal
	
	on map i p do
	(
		--write all points to the boxshape var so we can lerp it later
		--if the point is outside the center threshold of the bounds, set it to the bounds, otherwise take the point as is
		
		if (p.x > centerThresholdX) then boxshape.x = extent.x / 2
		else if (p.x < centerThresholdX and p.x > -centerThresholdX) then boxshape.x = p.x
		else if (p.x < -centerThresholdX) then boxshape.x = -extent.x / 2

		if (p.y > centerThresholdY) then boxshape.y = extent.y / 2
		else if (p.y < centerThresholdY and p.y > -centerThresholdY)  then boxshape.y = p.y
		else if (p.y < -centerThresholdY) then boxshape.y = -extent.y / 2

		if (p.z > centerThresholdZ) then boxshape.z = extent.z / 2
		else if (p.z < centerThresholdZ and p.z > -centerThresholdZ)  then boxshape.z = p.z
		else if (p.z < -centerThresholdZ) then boxshape.z = -extent.z / 2

		lerp p boxshape (amount / 100)
	)
)