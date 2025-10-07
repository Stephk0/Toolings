v/*
Smooth Faces to Adjecnt smoothing groups
by Stephan Viranyi https://www.artstation.com/stephko
Feel free to share and extend to your wishes and msg me for any questions or feedback at stephko@viranyi.de
*/

plugin simpleMeshMod SmoothToAdjecent
	name:"Smooth To Adjecent SG"
	classID:#(0xf134d59, 0x658f11)
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

	parameters boundryInputParam rollout:params
	(
		faceMode ui:rbb_faceMode default:1 type:#integer animatable:true
		FilterSGFlag ui:chk_FilterSG default:true type:#boolean
		FilterSG ui:spn_FilterSG default:0 type:#integer animatable:true

	) 
	
	parameters sgSetup rollout:params2
	(
		distMode ui:rbb_distMode default:1 type:#integer animatable:true	
	)

	parameters debugMain rollout:debugParams
	(
		debugMsgs ui:chk_Msgs default:false type:#boolean animatable:true
		limitIter ui:chk_Limit default:false type:#boolean animatable:true		
		testvalIntGrp ui:spn_testValIntGrp default:1 type:#integer animatable:true
		testvalIntGrw ui:spn_testValIntGrw default:1 type:#integer animatable:true	
	) 

	rollout params "Boundry Input"
	(

		group "Operate on"
		(
			radiobuttons rbb_faceMode labels:#("Total Faces", "Selected Faces") align:#left
			checkbox chk_FilterSG "Filter Selection by SG:" checked:true tooltip:"Filter Face Selection by specified Smoothing group (Default: 0)"
			spinner spn_FilterSG "Filtered SG:" type:#integer range:[0,32,0]  tooltip:"Filter Face Selection by specified Smoothing group (Default: 0)" align:#left
		)

	)
	rollout params2 "Smoothing Groups"
	(
		group "Distribution Method"
		(
			radiobuttons rbb_distMode labels:#("Smart Neighbour", "Naive Linear", "Draft Mode") align:#left  tooltip:"
			Smoothing Group Distrbution Method
			Smart Neighbour: SGs are assigned based on the neighbouring faces. If SG 1 is assigned to a neighbour group it SG 1 will not be used for the group and so on.
			Naive Linear (faster): Each group (i.e group #1-16) gets a SG (i.e SG 1-16) assigned. To avoid conflicting SGs it is possible to limit and shift the distribution range (i.e shifting SG 1-16 to SG 16-32).
			Draft Mode (fastest): Groups get classic angle based autoSmooth assigned. Draft Mode is to ease the modelling process with heavy models while retaining a rough preview as you would with traditional autosmoothing methods.
			"
		)
		
	)
	
	rollout debugParams "Debug"
	(
		checkbox chk_Msgs "Massages" checked:false tooltip:"Vertex Color Black acts as input"
		checkbox chk_Limit "Limit Iter" checked:false tooltip:"Limit the chunk iteration step"
		spinner spn_testValIntGrp "grp iter" type:#integer range:[1,1e6,32]
		spinner spn_testValIntGrw "grow iter" type:#integer range:[1,1e6,0]		
	)
	
	on modifyMesh do
	(
		local startTime = timeStamp()
		-- all faces for later
		local allFaces = mesh.faces as bitarray
		-- only selected thru stack
		local selectedFaces = getFaceSelection mesh as bitarray
		-- if none is selected
		if faceMode == 1 do selectedFaces = allFaces
		
		-- operate only on faces with specified SGs
		if FilterSGFlag do
		(	
			local faceWithSG0 = #{}
			if FilterSG == 0 then faceWithSG0 = (for face = 1 to mesh.numfaces where (intToBitArray (getFaceSmoothGroup mesh face)).isEmpty collect face) as bitarray
			else faceWithSG0 = (for face = 1 to mesh.numfaces where (intToBitArray (getFaceSmoothGroup mesh face))[FilterSG] == true collect face) as bitarray		
			selectedFaces *= faceWithSG0
		)

		--no eighbours to source from, stop
		if (allFaces - selectedFaces).isEmpty do selectedFaces = #{}
/*
		local debugFaces
		
		local vertsFromFace = meshop.getVertsUsingFace mesh (selectedFaces) as bitarray
		local allNeighbourFaces = meshop.getPolysUsingVert mesh vertsFromFace as bitArray - selectedFaces as bitarray
		local vertsFromNeighbours = meshop.getVertsUsingFace mesh allNeighbourFaces as bitArray -- vertsFromFace as bitarray
		local innerTrimFaces = meshop.getPolysUsingVert mesh vertsFromNeighbours as bitArray - allNeighbourFaces as bitarray
		
		local neighbourSGs = #{}
		neighbourSGs.count = 32
		for face in allNeighbourFaces do
		(
			neighbourSGs += intToBitArray (getFaceSmoothGroup mesh face)
		)
*/		
		local getVertsUsingFace = meshop.getVertsUsingFace
		local getFacesUsingVert = meshop.getFacesUsingVert	
		--set all smoothing groups to 0
		for face in selectedFaces do setFaceSmoothGroup mesh face 0

		local growCounter = 0
		local faceCounter = 0
		--face cache that we empty out
		local unprocessedFaces = selectedFaces -- innerTrimFaces

		local leftoverTrim = #{}

		--final Smooting group integer, not a bitarray
		local finalSG = 0
		--smoothing groups of the neighbour face(s), set size to 32
		local faceNeighbourSGs = #{}
		faceNeighbourSGs.count = 32
		--face array that we fill with the currently processable face
		local face_array = #{}

		local vertsFromFace1
		local allNeighbourFaces1
		local vertsFromNeighbours1

		--repat until all unprocessed Faces are gone
		while (not unprocessedFaces.isEmpty) do --and growCounter < testvalIntGrw do 
		(	
			--Get the outer trim of the selected faces that are adjectent to an existing neighbour
			--verts from the remaining processed faces, as we process the faces -removing them from the unprocessedFaaces cache - the faces become less and less pass by pass
			vertsFromFace1 			= getVertsUsingFace mesh unprocessedFaces
			--just the neighbours of remaining faces
			allNeighbourFaces1 		= getFacesUsingVert mesh vertsFromFace1 - unprocessedFaces
			--grow the neighbours
			vertsFromNeighbours1 	= getVertsUsingFace mesh allNeighbourFaces1 -- vertsFromFace as bitarray
			--mulitply by remainidg unprocessed faces to form the next trim
			leftoverTrim 			= getFacesUsingVert mesh vertsFromNeighbours1 * unprocessedFaces

			--trim by trim we process the faces
			while (not leftoverTrim.isEmpty) do --and faceCounter < testvalIntGrp do
			(
				finalSG = 0
				faceNeighbourSGs = #{}
				--face array that we fill with the currently processable face
				face_array = #{}

				--go through each face of the trim that has not been processed yet
				--for face = 1 to leftoverTrimCount do while (face_array.isEmpty and leftoverTrim[face] == true) do face_array = #{face}
				--for face = 1 to leftoverTrimCount do while (face_array.isEmpty and leftoverTrim[face] == true) do face_array = #{face}
				for face in leftoverTrim where (face_array.count == 0 and leftoverTrim[face] == true) do face_array = #{face}

				--form a poly from the face
				local faceFromTri
				--local faceFromTri = meshop.getPolysUsingFace mesh face_array ignoreVisEdges:false threshhold:45 as bitarray
				--1 2 1 2 testing
				faceFromTri = face_array
				--get neighbours by growing, substract the face itself
				local vertsFromSelFace 	= getVertsUsingFace mesh faceFromTri 
				local neighbourFace 	= getFacesUsingVert mesh vertsFromSelFace - faceFromTri
				
				--if there are neighbouring faces
				if neighbourFace.count != 0 do
				(
					--if there is no SG assigned omit this face
					--for nface in neighbourFace where getFaceSmoothGroup mesh nface == 0 do neighbourFace -= #{nface}
					--add every SG of the neighbouring face
					for nface in neighbourFace do faceNeighbourSGs += (intToBitArray (getFaceSmoothGroup mesh nface))
				)

				--remove the current face from the trim and unprocessed Cache
				leftoverTrim -= faceFromTri
				unprocessedFaces -= faceFromTri
				
				--for every smoothing group that is active in the neighbour, form the int to set smoothing groups to true in the face
				for SG in (faceNeighbourSGs) do finalSG = bit.set finalSG SG true
				--assign the smoothing group int
				for face in faceFromTri do setFaceSmoothGroup mesh face finalSG
				
				if debugMsgs do (
				--count faces
				faceCounter += 1
				--count trim passes
				if leftoverTrim.isEmpty do growCounter += 1
				)
			)
		)
		--print selectedFaces.numberSet
		if debugMsgs do 
		(
			print ("operated on " + faceCounter as string + " Faces")
			print ("operated on " + (growCounter + 1) as string + " Trim(s)")
			print (timeStamp() - startTime)
			print leftoverTrim.numberSet
		)
		--mesh.selectedFaces = unprocessedFaces
		--print leftoverTrim.count
		--print unprocessedFaces
		--mesh.selectedFaces = selectedFaces[testvalIntGrp]

		--print neighbourSGs
	
		--debugFaces = neighbourFaces

		--mesh.selectedFaces = innerTrimFaces
		--mesh.selectedVerts = vertsFromNeighbours

	)
)