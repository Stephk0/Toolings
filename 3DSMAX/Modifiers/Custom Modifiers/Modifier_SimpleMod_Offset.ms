/*
Simple Offset Modifier
Works on any type of object. if you dont pass a selection you might have to set the pivot to the center
by Stephan Viranyi https://www.artstation.com/stephko
Feel free to share and extend to your wishes and msg me for any questions or feedback at stephko@viranyi.de
*/
plugin simpleMod simpleOffset
name:"Simple Offset"
remap:#(#("offsetXAmount","offsetYAmount","offsetZAmount", "amount"), #("offsetLS_X","offsetLS_Y","offsetLS_Z", "amountLS"))
version:100
classID:#(0xd2e7397, 0x3f22296d)
(

	

	--About Block, versioning
	local pluginLoaded = false -- ?
	local versionYear = 2023
	local aboutMain = "Numeric Offset and Align"

	fn composeVersionNrText v =
	(
		return ("Version " + (formattedPrint ((v as float)/100) format:"0.2f") + " | " + ( versionYear as string))
	)

	local aboutDocuLink = "https://docs.google.com/document/d/1fIKEurSNeaazzYsPnCTYT7bVO4R4btWzTzvLRpjNutY/edit?usp=sharing"
	local aboutShopLink = "https://www.artstation.com/stephko"
	
	local alignDir = 0

	fn alignToExtentOffsetMix alignAxis extent center =
	(
		
		if alignAxis > 1 then
		(
			alignDir = 0
			case alignAxis of 
			(
				2: alignDir = -1
				3: alignDir = 0
				4: alignDir = 1
			)	
			return (extent * 0.5) * alignDir - center
		)
		else return 0
		
	)

	local rotatedVector
	local tmrotation-- = quat 0 0 0 0

	parameters main rollout:params
	(
		node_transform type:#maxObject subanim:on 
		tmnode type:#node

		amountLS type:#float ui:amtSpinLS default:1

		offsetLS_X type:#float ui:offsetLS_X default:0
		offsetLS_Y type:#float ui:offsetLS_Y default:0
		offsetLS_Z type:#float ui:offsetLS_Z default:0

		amountWS type:#float ui:amtSpinWS default:1

		offsetWS_X type:#float ui:offsetWS_X default:0
		offsetWS_Y type:#float ui:offsetWS_Y default:0
		offsetWS_Z type:#float ui:offsetWS_Z default:0

		alignX ui:rbb_alignX type:#integer default:1 animatable:true
		alignY ui:rbb_alignY type:#integer default:1 animatable:true
		alignZ ui:rbb_alignZ type:#integer default:1 animatable:true
	)
	
	parameters gizmoSet rollout:SetGizmo
	(
		setGizmoFromNode type:#node useNodeTmValidity:on subAnim:on ui:pbt_setGizmoFromNode
		keepNode ui:chk_keepNode default:false type:#boolean
		setGizmoFromNodePos ui:chk_setGizmoFromNodePos default:true type:#boolean
		setGizmoFromNodeRot ui:chk_setGizmoFromNodeRot default:true type:#boolean
		setGizmoFromNodeScale ui:chk_setGizmoFromNodeScale default:true type:#boolean
		setGizmoFromNodeExtent ui:chk_setGizmoFromNodeExtent default:true type:#boolean
	)

		
	rollout params "Parameters" category:1
	(
		group "Local Offset"
		(
			spinner offsetLS_X "Offset X" type:#worldUnits range:[-1e6, 1e6, 0] align:#left
			spinner offsetLS_Y "Offset Y" type:#worldUnits range:[-1e6, 1e6, 0] align:#left
			spinner offsetLS_Z "Offset Z" type:#worldUnits range:[-1e6, 1e6, 0] align:#left

			spinner amtSpinLS "Multiplier"   range:[-1e6, 1e6, 1] align:#left
			button btn_setMultiplierToObjectSize "Rescale to Object Size" width:140 tooltip:"Rescale the Gizmo to match the Object Size (Gizmoscale / Obejct Scale)"
		)

		group "World Offset"
		(
			spinner offsetWS_X "Offset X" type:#worldUnits range:[-1e6, 1e6, 0] align:#left
			spinner offsetWS_Y "Offset Y" type:#worldUnits range:[-1e6, 1e6, 0] align:#left
			spinner offsetWS_Z "Offset Z" type:#worldUnits range:[-1e6, 1e6, 0] align:#left

			spinner amtSpinWS "Multiplier"   range:[-1e6, 1e6, 1] align:#left
		)
		group "Align"
		(
			label lab_Align "  NONE | Min | Center | Max" align:#left
			label lab_AlignX "X" align:#left across:2
			radiobuttons rbb_alignX labels:#("   ","   ","   ","   ") align:#left columns:4 offset:[-55,0] 
			
			label lab_AlignY "Y" align:#left across:2
			radiobuttons rbb_alignY labels:#("   ","   ","   ","   ") align:#left columns:4 offset:[-55,0]
			
			label lab_AlignZ "Z" align:#left across:2
			radiobuttons rbb_alignZ labels:#("   ","   ","   ","   ") align:#left columns:4 offset:[-55,0]
		)

		
		
	)

	rollout SetGizmo "Set Gizmo" category:2
	(

		group "Rotate Gizmo"
		(
			button btn_rotateGizmoToWorld "Rotate to World Space" width:140 tooltip:"Align the Gizmo Rotation so its matches a Zero World Rotation"
			button btn_rotateGizmoToLocal "Rotate to Local Space" width:140 tooltip:"Align the Gizmo Rotation so its matches a Zero Local Rotation"
		)

		group "Rescale Gizmo"
		(
			button btn_rescaleGizmoToObjectSize "Rescale to Object Size" width:140 tooltip:"Rescale the Gizmo to match the Object Size (Gizmoscale / Obejct Scale)"
			button btn_rescaleGizmoToOriginalSize "Reset Size" width:140 tooltip:"Reset the Gizmo Scale to Default"
		)
		group "Set Gizmo From Object"
		(
			pickButton pbt_setGizmoFromNode "Set Gizmo From Node" autoDisplay:on align:#center width:140--enabled:(coordsysMode == 2)
			checkbox chk_keepNode "Keep Node Link (slow)" align:#left checked:false 
			checkbox chk_setGizmoFromNodePos "Set Position" align:#left checked:true 
			checkbox chk_setGizmoFromNodeRot "Set Rotation" align:#left checked:true 
			checkbox chk_setGizmoFromNodeScale "Set Scale"  align:#left checked:true
			checkbox chk_setGizmoFromNodeExtent "Set Extents"  align:#left checked:true
	
		)

		on setGizmoToCenter pressed do this.gizmo.position = center
		on setGizmoToPivot pressed do this.gizmo.position = [0,0,0]


		on btn_rotateGizmoToWorld pressed do
		(
			prevPosition = this.gizmo.position
			this.gizmo.rotation = $.transform.rotation
			this.gizmo.position = prevPosition
		) 

		on btn_rotateGizmoToLocal pressed do
		(
			prevPosition = this.gizmo.position
			this.gizmo.rotation = quat 0 0 0 1
			this.gizmo.position = prevPosition
		) 

		on btn_rescaleGizmoToObjectSize pressed do this.gizmo.scale = 1 / $.transform.scale
		on btn_rescaleGizmoToOriginalSize pressed do this.gizmo.scale = [1,1,1]

		on pbt_setGizmoFromNode picked nodeobject do 
		(
			if setGizmoFromNodeRot do this.gizmo.rotation = nodeobject.rotation * inverse $.rotation
			if setGizmoFromNodeScale do this.gizmo.scale = nodeobject.scale
			if setGizmoFromNodePos do this.gizmo.position = nodeobject.position - $.position

			if not keepNode do setGizmoFromNode = undefined
		)
	)

	rollout ResetGizmo "Reset Gizmo" category:3
	(
		group "Reset Gizmo"
		(
			button rstGizmoPos "Reset Gizmo Position"  width:140
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


	------------------------
	-- about section START HERE
	------------------------


	rollout paramsAbout "About" category:256 rolledUp:true
	(

		label lab_aboutMain aboutMain align:#left
		label lab_aboutVersion align:#left
		label lab_aboutSV "by Stephan Viranyi" align:#left
		hyperLink hyp_aboutDocuLink "Help | Documentation" color:blue address:aboutDocuLink
		hyperLink hyp_aboutShopLink "Visit my Artstation" color:blue address:aboutShopLink

		--load version number. version is not accessible as local varaia
		on paramsAbout open do lab_aboutVersion.text = composeVersionNrText version 
	)

	------------------------
	-- about section ENDS HERE
	------------------------

	fn alignToExtentOffset alignAxis extent center =
	(
		
		if alignAxis > 1 then
		(
			alignDir = 0	
			if alignAxis == 2 do alignDir = -1
			if alignAxis == 3 do alignDir = 0
			if alignAxis == 4 do alignDir = 1
			return (extent * 0.5) * alignDir - center
		)
		else return 0
		
	)

	on map i p do 
	(
		--align
		p += [alignToExtentOffsetMix alignX extent.x center.x, alignToExtentOffsetMix alignY extent.y center.y, alignToExtentOffsetMix alignZ extent.z center.z]

		--offset local
		if (offsetLS_X + offsetLS_Y + offsetLS_Z) != 0 do p += [offsetLS_X,offsetLS_Y,offsetLS_Z] * amountLS

		--offset world
		--if tmnode != undefined do tmrotation = tmnode.transform.rotation
		--if tmrotation != undefined and this.gizmo != undefined do tmrotation *= this.gizmo.rotation
		--rotatedVector = [offsetWS_X,offsetWS_Y,offsetWS_Z] * tmrotation
		--p -= rotatedVector * amountWS

		--offset world working
		if (offsetWS_X + offsetWS_Y + offsetWS_Z) != 0 do 
		(
			if $ != undefined do 
			(
				tmrotation = $.transform.rotation
				if tmrotation != undefined and this.gizmo != undefined do tmrotation *= this.gizmo.rotation
				rotatedVector = [offsetWS_X, offsetWS_Y, offsetWS_Z] * tmrotation
				
				p -= rotatedVector * amountWS / $.transform.scale
			)
			
		)

		p
	)
	
	

)