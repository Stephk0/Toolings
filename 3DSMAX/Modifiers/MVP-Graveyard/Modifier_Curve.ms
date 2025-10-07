/*
Simple Curve Modifer
Works on any type of object. if you dont pass a selection you might have to set the pivot to the center
by Stephan Viranyi https://www.artstation.com/stephko
Feel free to share and extend to your wishes and msg me for any questions or feedback at stephko@viranyi.de
https://forums.cgsociety.org/t/curvecontrol-using-the-wrong-values/1525598/18
https://forums.cgsociety.org/t/is-getpoint-in-curvecontrol-broken/1555419
https://forums.cgsociety.org/t/setting-curve-control-tangents/1863463/10
*/
plugin simpleMod curveMod
name:"Curve"
classID:#(0x3be6972f, 0x22d2d1df)
(

	local value

	parameters main rollout:params
	(
		amount type:#float ui:amtSpin default:1

		offsetXAmount type:#float ui:amtOX default:0
		offsetYAmount type:#float ui:amtOY default:0
		offsetZAmount type:#float ui:amtOZ default:0

		curveX type:#floatTab tabSizeVariable:true 
	)
		
	rollout params "Parameters"
	(
		spinner amtSpin "Multiplier"   range:[-1e6, 1e6, 1]

		spinner amtOX "Offset X"  range:[-1e6, 1e6, 0]
		spinner amtOY "Offset Y"  range:[-1e6, 1e6, 0]
		spinner amtOZ "Offset Z"  range:[-1e6, 1e6, 0]

		CurveControl uiCurveX "Curve" x_value:0 height:200 visible:true numCurves:1 y_range:[-1e6, 1e6] x_range:[0,1] uiFlags:#(#all, #constrainY)

		--on uiCurveX ptChanged ci val do format "curve % ptChanged : %\n" ci val

		on uiCurveX ptChanged ci val do (
			--test = uiCurveX.getValue uiCurveX[1] 0.5 0.5
			--curveX[1] = val
		)
/*
[x_range:<point2> ] [y_range:<point2>] \ 
[x_value:<float> ] \ 
[zoomValues:<point2>] [scrollValues:<point2>] \
[displayModes:<bitarray>] \
[commandMode:<#move_xy | #move_x | #move_y | #scale | #corner | #bezier] \
[uiFlags:<array_of_ui_flags> ] \
[rcmFlags:<array_of_rcm_flags>] [asPopup:<boolean>]
*/

		button setGizmoToCenter "Set Gizmo Position to Center"
		button rstGizmoPos "Reset Gizmo Position To Pivot"
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
		--curv = 
		--value = uiCurveX.getValue uiCurveX.curves[1] 0.5 0.5
		--print uiCurveX
		--p.x += curveX[0]
		p.y += offsetYAmount * amount
		p.z += offsetZAmount * amount	
		p
	)
)