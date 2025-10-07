/*
Poly Extrude Along Spline
Only Works in max 2017+, extends Edit Poly interface, based on example from http://www.scriptspot.com/3ds-max/scripts/extrudeinsetoutline-faces-modifiers
by Stephan Viranyi https://www.artstation.com/stephko
Feel free to share and extend to your wishes and msg me for any questions or feedback at stephko@viranyi.de
*/

plugin modifier PolyExtrudeAlongSpline
	name:"Poly Extrude Along Spline"
	classID:#(0xba2d919, 0x768fe79d)
	extends:Edit_Poly
	replaceUI:on
(
	local owner
	local updateHandler
	

	fn initUpdate node =
	(
		this.owner = node
		this.updateHandler =
			when geometry this.owner changes do
				if isValidObj (local obj = modPanel.getCurrentObject()) do
					notifyDependents obj partIDmsg:#display
	)

	parameters main rollout:params
	(

		extrudeAlongSplineAlign type:#boolean default:true ui:chkAlign
		on extrudeAlongSplineAlign set val do delegate.extrudeAlongSplineAlign = val

		extrudeAlongSplineNode type:#node ui:nodePick
		on extrudeAlongSplineNode set val do
		(
		if (this.owner != undefined) do delegate.worldToObjectTransform = this.owner.transform as matrix3
		delegate.extrudeAlongSplineNode = val
		)

		extrudeAlongSplineRotation type:#float default:0 ui:spnRotation
		on extrudeAlongSplineRotation set val do delegate.extrudeAlongSplineRotation = val

		extrudeAlongSplineSegments type:#integer default:6 ui:spnSegments
		on extrudeAlongSplineSegments set val do delegate.extrudeAlongSplineSegments = val

		extrudeAlongSplineTaper type:#float default:0 ui:spnTaper
		on extrudeAlongSplineTaper set val do delegate.extrudeAlongSplineTaper = val
		
		extrudeAlongSplineTaperCurve type:#float default:0 ui:spnCurve
		on extrudeAlongSplineTaperCurve set val do delegate.extrudeAlongSplineTaperCurve = val

		extrudeAlongSplineTwist type:#float default:0 ui:spnTwist
		on extrudeAlongSplineTwist set val do delegate.extrudeAlongSplineTwist = val


	)

	
	on create do
	(		
		delegate.animationMode = 1
		delegate.useStackSelection = on
		delegate.setEPolySelLevel #Face
		delegate.setOperation #ExtrudeAlongSpline

	)

	on load do initUpdate (refs.dependentNodes this)[1]
	
	on attachedToNode node do
		if isValidNode node then initUpdate node
		else if this.updateHandler != undefined do deleteChangeHandler this.updateHandler

	rollout params "Parameters"
	(
		fn splineFilter obj = superClassOf obj == shape
		pickbutton nodePick "Select Spline" width:140 filter:splineFilter autoDisplay:true

		checkbox chkAlign " Align to face normal" checked:true
		
		spinner spnRotation "Rotation" type:#float range:[-1e6, 1e6, 0]
		spinner spnSegments "Segmentst" type:#integer range:[1, 1e6, 6]
		spinner spnTaper "Taper Amount" type:#float range:[-1e6, 1e6, 0]
		spinner spnCurve "Taper Curve" type:#float range:[-1e6, 1e6, 0]
		spinner spnTwist "Twist" type:#float range:[-1e6, 1e6, 0]
		

		
	)
	
	
	rollout header "How to use"
	(
		edittext 'HowToUse' text:"Select Face to Extrude in Stack, assign Spline. Same as Extrude Along Spline in Epoly" readOnly:true height:80 width:150
	)
)