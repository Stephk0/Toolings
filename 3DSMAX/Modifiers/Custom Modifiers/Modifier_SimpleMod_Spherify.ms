/*
Simple Spherify Modifier
Works on any type of object. if you dont pass a selection you might have to set the pivot to the center
by Stephan Viranyi https://www.artstation.com/stephko
Feel free to share and extend to your wishes and msg me for any questions or feedback at stephko@viranyi.de
*/
plugin simpleMod simpleSpherify
name:"Simple Spherify"
classID:#(0x12c992e4, 0x2606197d)
(
	local k -- multiplier
	local newExtent
	
	parameters main rollout:params1
	(
		amount type:#float ui:amtSpin default:100		
	)

	parameters gizmoSize rollout:params2GizmoSize
	(
		gizmoSizeMode ui:rbb_gizmoSizeMode default:1 type:#integer animatable:true
		gizmoSize ui:spn_gizmoSize default:100 type:#float animatable:true
	)

	parameters gizmoSet rollout:params3GizmoSet
	(
		setGizmoFromNode type:#node useNodeTmValidity:on subAnim:on ui:pbt_setGizmoFromNode
		keepNode ui:chk_keepNode default:false type:#boolean
		setGizmoFromNodePos ui:chk_setGizmoFromNodePos default:true type:#boolean
		setGizmoFromNodeRot ui:chk_setGizmoFromNodeRot default:true type:#boolean
		setGizmoFromNodeScale ui:chk_setGizmoFromNodeScale default:true type:#boolean
		setGizmoFromNodeExtent ui:chk_setGizmoFromNodeExtent default:true type:#boolean
	)

	parameters gizmoReset rollout:params4ResetGizmo
	(
	)

		
	rollout params1 "Main Parameters"
	(
		spinner amtSpin "Percent" range:[-100,200,100] scale:1
	)

	rollout params2GizmoSize "Gizmo Size"
	(
		group "Get Gizmo Size"
		(
			radiobuttons rbb_gizmoSizeMode labels:#("From Mesh Extents", "From Absolute Value") align:#left tooltip:"Determine if the Gizmo Size is based on the mesh extents/bounds or an absolute/constant value irregardless of the objects bounds"
			spinner spn_gizmoSize "Value" align:#left  type:#worldUnits range:[0,1e6,100] enabled:(gizmoSizeMode == 2)
			button btn_getSizeFromExtent "Get Value from Extent"
		)
		
		on rbb_gizmoSizeMode changed state do 
		(
			spn_gizmoSize.enabled = state == 2	
		)

		on btn_getSizeFromExtent pressed do spn_gizmoSize.value = amax #(extent.x,extent.y,extent.z)
	)

	rollout params3GizmoSet "Set Gizmo"
	(
		group "Set Gizmo"
		(
			button setGizmoToCenter "Gizmo Position to Center"
			button setGizmoToPivot "Gizmo Position to Pivot"
		)
		group "Set Gizmo From Object"
		(
			pickButton pbt_setGizmoFromNode "Set Gizmo From Node" autoDisplay:on align:#center --enabled:(coordsysMode == 2)
			checkbox chk_keepNode "Keep Node Link (slow)" align:#left checked:false 
			checkbox chk_setGizmoFromNodePos "Set Position" align:#left checked:true 
			checkbox chk_setGizmoFromNodeRot "Set Rotation" align:#left checked:true 
			checkbox chk_setGizmoFromNodeScale "Set Scale"  align:#left checked:true
			checkbox chk_setGizmoFromNodeExtent "Set Extents"  align:#left checked:true
	
		)

		on setGizmoToCenter pressed do this.gizmo.position = center
		on setGizmoToPivot pressed do this.gizmo.position = [0,0,0]

		on pbt_setGizmoFromNode picked nodeobject do 
		(
			if setGizmoFromNodeRot do this.gizmo.rotation = nodeobject.rotation * inverse $.rotation
			if setGizmoFromNodeScale do this.gizmo.scale = nodeobject.scale
			if setGizmoFromNodePos do this.gizmo.position = nodeobject.position - $.position
			if setGizmoFromNodeExtent do 
			(
				bounds = nodeobject.max - nodeobject.min
				bounds /= nodeobject.scale
				gizmoSize = amax #(bounds.x,bounds.y,bounds.z)
			)

			if not keepNode do setGizmoFromNode = undefined
		)
	)

	
	rollout params4ResetGizmo "Reset Gizmo"
	(
		group "Reset Gizmo"
		(
			button rstGizmoPos "Reset Gizmo Position" width:140
			button rstGizmoScale "Reset Gizmo Scale" width:140
			button rstGizmoRot "Reset Gizmo Rotation" width:140
			button rstGizmoFull "Reset All" width:140
		)
		on rstGizmoPos pressed do this.gizmo.position = [0,0,0]
		on rstGizmoFull pressed do this.gizmo.transform = matrix3 1
		on rstGizmoScale pressed do this.gizmo.scale = [1,1,1]
		on rstGizmoRot pressed do 
		(
			prevPosition = this.gizmo.position
			this.gizmo.rotation = quat 0 0 0 1
			this.gizmo.position = prevPosition
		)
	)

	on map i p do
	(
		if gizmoSizeMode == 1 then newExtent = amax #(extent.x,extent.y,extent.z)
		else newExtent = gizmoSize

		k   = (newExtent / length p / 2 - 1 ) * amount / 100 + 1 

		p *= k 
		p
	)
)