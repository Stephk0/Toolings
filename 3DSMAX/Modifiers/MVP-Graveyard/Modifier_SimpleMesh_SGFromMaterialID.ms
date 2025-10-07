/*
Smoothing groups by Material ID
by Stephan Viranyi https://www.artstation.com/stephko
Feel free to share and extend to your wishes and msg me for any questions or feedback at stephko@viranyi.de
*/

plugin simpleMeshMod SgFromMaterialID
	name:"SG from Mat ID"
	classID:#(0x510aa946, 0x303ca418)
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
	
	parameters main rollout:paramsOp
	(
		faceMode ui:rbb_faceMode default:1 type:#integer animatable:true
		distMode ui:rbb_distMode default:1 type:#integer animatable:true
		--smart setting, sg fallback if no sg can be assigned
		SGFallBack ui:spn_SGFallBack default:0 type:#integer animatable:true	
		--naive linear range
		SGRangeMin ui:spn_Rmin default:16 type:#integer animatable:true	
		SGRangeMax ui:spn_Rmax default:32 type:#integer animatable:true		
	) 
	
	rollout paramsOp "Parameters"
	(
		group "Selection:"
		(
			radiobuttons rbb_faceMode labels:#("Total Faces", "Selected Faces")
		)

		group "Distribution Method"
		(
			radiobuttons rbb_distMode labels:#("Smart Neighbour", "Naive Linear") align:#left  tooltip:"
			Smoothing Group Distrbution Method
			Smart Neighbour: SGs are assigned based on the neighbouring faces. If SG 1 is assigned to a neighbour group it SG 1 will not be used for the group and so on.
			Naive Linear (faster): Each group (i.e group #1-16) gets a SG (i.e SG 1-16) assigned. To avoid conflicting SGs it is possible to limit and shift the distribution range (i.e shifting SG 1-16 to SG 16-32).
			"
		)

		group "Smart Neighbour"
		(
			spinner spn_SGFallBack "Unassignable Fallback" type:#integer range:[0,32,0] width:80 align:#left tooltip:"Fallback SG to assign if no SG can be assigned (avoid using big number of redundant SGs to avoid fallback assingment)"	
		)

		group "Naive Linear Range"
		(
			spinner spn_Rmin "Range Min" type:#integer range:[1,31,16]
			spinner spn_Rmax "Range Max" type:#integer range:[2,32,32]
		)
		
	) 

	on modifyMesh do
	(
		--set SG distribution min max, make sure the min is never higher then the max and vice versa
		if SGRangeMin >= SGRangeMax do SGRangeMin = SGRangeMax
		if SGRangeMax <= SGRangeMin do SGRangeMax = SGRangeMin

		-- apprently this is suppsed to speed up things but it did not?
		local getVertsUsingFace = meshop.getVertsUsingFace
		local getFacesUsingVert = meshop.getFacesUsingVert

		--get the selection from stack
		local selectedFaces = getFaceSelection mesh as bitarray
		--or all faces
		local allFaces = mesh.faces as bitarray
		--operate on selected or all
		if faceMode == 1 do selectedFaces = allFaces

		--split groups
		local splitGroups = #()
		local splitGroupFaces = #()


		for face in selectedFaces do
		(	
			--get the faces material ID
			local faceMatID = getFaceMatID mesh face
			--setup a list of splitGroups based on material IDs
			appendIfUnique splitGroups faceMatID
				
			--find to which entry the Material ID int belongs to
			local idItem = findItem splitGroups (faceMatID)
			--if no face was added yet create a new subarray
			if splitGroupFaces[idItem] == undefined do splitGroupFaces[idItem] = #{}
			--add the corresponding face to the group
			splitGroupFaces[idItem] = append splitGroupFaces[idItem] face
		)
		
		--final resulting smoothin group
		local finalSGInt = 0
		-- get all neighbour Smoothing groups
		local neighbourSGs = #{}
		neighbourSGs.count = 32

		local vertsFromFace
		local neighbourFaces
		--repeat loop for all groups
		for i = 1 to splitGroups.count do
		(
			--reset for each group
			finalSGInt = 0
			--smart neighbour mode, detect the smoothing group around the facegroup and adjecent groups
			if distMode == 1 do
			(
				-- get neighbouring faces
				vertsFromFace 	= getVertsUsingFace mesh (splitGroupFaces[i])
				neighbourFaces 	= getFacesUsingVert mesh vertsFromFace as bitArray - splitGroupFaces[i] as bitarray
				
				-- reinit neighbourSG bitarray to get all neighbour Smoothing groups of facegroup
				neighbourSGs = #{}
				neighbourSGs.count = 32
				--add them to the list of "occupied" SGs
				for face in neighbourFaces do neighbourSGs += intToBitArray (getFaceSmoothGroup mesh face)

				--loop through the inverse of the occupied smoothing groups, aka the "available" smoothing grops
				--if we found an availbe SG stop the loop by flag SGassigned
				if (not (-neighbourSGs).isEmpty) then for SG in (-neighbourSGs) while finalSGInt == 0 do finalSGInt = bit.set finalSGInt SG true
				--if all SGs are occupied, assign a fallback
				else if SGFallBack != 0 then finalSGInt = bit.set finalSGInt SGFallBack true
				else finalSGInt = 0
			)

			if distMode == 2 do
			(
				--Naive method, just assign as many Sgs as you have groups and maybe shift them afterwards
				-- make sure we cylce within 32 available groups
				if (SGRangeMax - SGRangeMin > 0) then 
				(
					local circularShift = SGRangeMin + mod (i) (SGRangeMax - SGRangeMin)
					-- convert grp no. to bitarray integer
					finalSGInt = bit.set finalSGInt circularShift true
				)
				else finalSGInt = 0
			)

			-- all set, for all the faces in this group assign the group > hit it johnny
			for face in splitGroupFaces[i] do
			(
				setFaceSmoothGroup mesh face finalSGInt			
			)
		)
	)
)