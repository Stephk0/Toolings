/*
Simple Scale Modifier
Works on any type of object. if you dont pass a selection you might have to set the pivot to the center
by Stephan Viranyi https://www.artstation.com/stephko
Feel free to share and extend to your wishes and msg me for any questions or feedback at stephko@viranyi.de
*/
plugin simpleMod simpleScale
name:"Simple Scale"
classID:#(0x7981ed0, 0x444b35d2)
(

	parameters main rollout:params
	(
		amount type:#float ui:amtSpin default:1

		scaleXAmount type:#float ui:amtSX default:1
		scaleYAmount type:#float ui:amtSY default:1
		scaleZAmount type:#float ui:amtSZ default:1
	)
		
	rollout params "Parameters"
	(
		spinner amtSpin "Multiplier"   range:[-1e6, 1e6, 1]

		spinner amtSX "Scale X"  range:[-1e6, 1e6, 1]
		spinner amtSY "Scale Y"  range:[-1e6, 1e6, 1]
		spinner amtSZ "Scale Z"  range:[-1e6, 1e6, 1]


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
		p.x *= scaleXAmount * amount
		p.y *= scaleYAmount * amount
		p.z *= scaleZAmount * amount
		p
	)
)