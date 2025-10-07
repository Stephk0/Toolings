/*
set material ids based on smoothing groups. could help for trouble shooting and analysis
by Stephan Viranyi https://www.artstation.com/stephko
Feel free to share and extend to your wishes and msg me for any questions or feedback at stephko@viranyi.de
*/

plugin simpleMeshMod MaterialIDBySG
	name:"Material ID by Smoothing Groups"
	classID:#(0x7974a6b2, 0x385cd171)
(

    function intToBitArray iNum =
    (
        if ((classOf iNum) == Integer) then
        (
            local baBits = #{}

            for i = 1 to 32 do
            (
                if (mod iNum 2 != 0) do
                (
                    baBits[i] = true
                    iNum -= 1
                )
                iNum /= 2
            )
            return baBits
        )
        else
        (
            return false
        )
    )

	parameters main rollout:params
	(
		--var for SG0 Mat ID override
		overrideSG0MatID ui:chk_overrideSG0 default:false type:#boolean animatable:true	
		SG0MatIDOverride ui:spn_SG0MatIDOverride default:33 type:#integer animatable:true
		
		--var for multi SG Mat ID override
		overrideMultiSGMatID ui:chk_overrideMultiSG default:false type:#boolean animatable:true	
		multiSGMatIDOverride ui:spn_multiSGMatIDOverride default:34 type:#integer animatable:true	

		--var to select multi SGs
		selectMultiSG ui:chk_selectMultiSG default:false type:#boolean animatable:true		
		
		--var to apply to all
		applyToAll ui:chk_applyToAll default:true type:#boolean animatable:true	
	) 
	
	rollout params "Parameters"
	(
		--ui for SG0 override
		checkbox chk_overrideSG0 "Overide Zero SGs" checked:false tooltip:"Override Material ID for faces with no smoothing groups (Default is keep existing Material ID)"
		spinner spn_SG0MatIDOverride "Zero SG Mat ID" type:#integer range:[1,1e6,33]
		
		--ui for multi SG override
		checkbox chk_overrideMultiSG "Overide Multi SGs" checked:false tooltip:"Override Material ID for faces with multiple smoothing groups (Default is highest active Smoothing Group Number)"
		spinner spn_multiSGMatIDOverride "Multi SG Mat ID" type:#integer range:[1,1e6,34]

		--ui for select multi SG
		checkbox chk_selectMultiSG "Sel multiple SGs" checked:false tooltip:"Select Faces with multiple Smoothing Groups"

		--ui to apply to all
		checkbox chk_applyToAll "Apply to whole mesh" checked:true tooltip:"Apply the material ID "
	) 

	on modifyMesh do
	(
		--get the selection from stack
		local selectedFaces = getFaceSelection mesh as bitarray
		--or all faces
		if (applyToAll == true) then selectedFaces = mesh.faces as bitarray

		local resultingFaceSelection = #{}

		for face in selectedFaces do
		(
			--get this 32 bit integer representing a bitarray of the smooth groups assigned to the face
			--we need to use 32 bit interger to assign the face smoothing group, unless we convert as described below
			--local faceSG = getFaceSmoothGroup mesh face
			local faceSG = intToBitArray (getFaceSmoothGroup mesh face)
			

			--for each smoothing group (1-32) there is...
			for sgInFace = 1 to 32 do 
			(
				if (faceSG[sgInFace] == true) then setFaceMatID mesh face sgInFace
			)

			--if there is no smoothing group assigned
			if (overrideSG0MatID == true and faceSG.numberset == 0) then setFaceMatID mesh face SG0MatIDOverride

			--if we have more then one smoothing group assigned
			if (faceSG.numberSet > 1) then
			(
				if (overrideMultiSGMatID == true) then setFaceMatID mesh face multiSGMatIDOverride

				if (selectMultiSG == true) then resultingFaceSelection = append resultingFaceSelection face
			)			
		)
		-- not sure how to force active selection in stack
		--setSelectionLevel owningNode #face
		if (selectMultiSG == true) then mesh.selectedFaces = resultingFaceSelection

	)
)