/*
Simple Cylindrify Modifier
Works on any type of object. if you dont pass a selection you might have to set the pivot to the center
by Stephan Viranyi https://www.artstation.com/stephko
original by Garp http://www.scriptspot.com/3ds-max/scripts/cylindrify-modifier
Feel free to share and extend to your wishes and msg me for any questions or feedback at stephko@viranyi.de
*/
plugin simpleMod simpleCylindrify
name:"Simple Cylindrify"
classID:#(0xa79cf0f, 0x43e876f0)
(
	local k -- multiplier
	
	parameters main rollout:params
	(
		amount type:#float ui:amtSpin default:100

		centerThreshold type:#float ui:centerThresSpin
	)
		
	rollout params "Parameters"
	(
		spinner amtSpin "Percent" range:[0,100,100] scale:1
		spinner centerThresSpin "Center Threshold" type:#worldUnits range:[0,1e6,0] 
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
	
	on map i p do
	(
		k = ((amax #(extent.x,extent.y) / length [p.x,p.y] / 2 - 1)) * amount / 100 + 1 
		if (abs(p.x - center.x) > centerThreshold) do 
		(
			p.x *= k
			--p.y *= k
		)
		if (abs(p.y - center.y) > centerThreshold) do 
		(

			p.y *= k
		)
		p
	)
)