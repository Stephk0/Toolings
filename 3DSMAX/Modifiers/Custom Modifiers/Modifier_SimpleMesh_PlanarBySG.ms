/*
set material ids based on smoothing groups. could help for trouble shooting and analysis
by Stephan Viranyi https://www.artstation.com/stephko
Feel free to share and extend to your wishes and msg me for any questions or feedback at stephko@viranyi.de
*/

plugin simpleMeshMod PlanarBySG
	name:"Planar by Smoothing Groups"
	classID:#(0x742062d0, 0x57425e53)
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

		inVColor ui:chk_inVColor default:true type:#boolean animatable:true
		inVColorThreshCol ui:cpk_vColorInputThreshCol type:#color animatable:true
		inVWeight ui:chk_inVWeight default:true type:#boolean animatable:true	
		inVWeightThresh ui:spn_vWeightInputThresh default:1.01 type:#float animatable:true	
	) 
	
	parameters sgSetup rollout:params2
	(
		distMode ui:rbb_distMode default:1 type:#integer animatable:true
		startFromPoly ui:chk_startFromPoly default:true type:#boolean
		
		SGRangeMin ui:spn_Rmin default:16 type:#integer animatable:true	
		SGRangeMax ui:spn_Rmax default:32 type:#integer animatable:true		

		draftAngle ui:spn_draftAngle default:45 type:#float animatable:true
		draftShift ui:spn_draftShift default:16 type:#integer animatable:true		
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
		group "Get Boundry Input"
		(
			checkbox chk_inVColor "from Vertex Color" checked:true tooltip:"Vertex Color acts as boundry input" align:#left
			colorpicker cpk_vColorInputThreshCol "Threshold Color" color:[0,0,0] modal:false tooltip:"Vertex Color Threshold" align:#left
			checkbox chk_inVWeight "from Vertex Weight" checked:true tooltip:"Vertex Weight Threshold acts as boundry input" align:#left
			spinner spn_vWeightInputThresh "Threshold" type:#float range:[0,1e6,1.01] tooltip:"Vertex Weight Threshold" align:#left
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
		
		group "Stray Groups"
		(
			checkbox chk_startFromPoly "Quad Strays" checked:true tooltip:"Stray Groups consist of one Smoothingr group only. Facesearch start from a Polygon rather than a triangle. Yields the same result for preview but is more accurate under the hood. Disable this if you encounter perfomance problems"	
		)

		group "Smart Neighbour"
		(
			spinner spn_SGFallBack "Unassignable Fallback" type:#integer range:[1,31,16] width:80 align:#left
		)
		group "Naive Linear Range"
		(
			spinner spn_Rmin "Range Min" type:#integer range:[1,31,16]
			spinner spn_Rmax "Range Max" type:#integer range:[2,32,32]
		)

		group "Draft Mode"
		(
			spinner spn_draftAngle "Draft Angle" type:#float range:[0,180,45]
			spinner spn_draftShift "Draft Shift" type:#integer range:[0,32,16]
		)

		on spn_Rmin val changed do if val >= spn_Rmax.value do spn_Rmin.value = spn_Rmax.value	
		on spn_Rmax val changed do if val >= spn_Rmin.value do spn_Rmax.value = spn_Rmin.value
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
		--set SG distribution min max, make sure the min is never higher then the max and vice versa
		if SGRangeMin >= SGRangeMax do SGRangeMin = SGRangeMax
		if SGRangeMax <= SGRangeMin do SGRangeMax = SGRangeMin

		-- all faces for later
		local allFaces = mesh.faces as bitarray
		-- only selected thru stack
		local selectedFaces = getFaceSelection mesh as bitarray
		-- if none is selected
		if faceMode == 1 do selectedFaces = allFaces
		local testedFaces = #{}
		
		-- operate only on faces with specified SGs
		if FilterSGFlag do
		(	
			local faceWithSG0 = #{}
			if FilterSG == 0 then faceWithSG0 = (for face = 1 to mesh.numfaces where (intToBitArray (getFaceSmoothGroup mesh face)).isEmpty collect face) as bitarray
			else faceWithSG0 = (for face = 1 to mesh.numfaces where (intToBitArray (getFaceSmoothGroup mesh face))[FilterSG] == true collect face) as bitarray
			selectedFaces -= -faceWithSG0
		)

		if distMode == 3 then
		(
			--draft mode: autosmooth everything, create no groups, just work fast and be toggleable
			meshop.autoSmooth mesh selectedFaces draftAngle
			for face in selectedFaces do
			(
				local faceSG = getFaceSmoothGroup mesh face
				local faceSGShifted = 0

				for sgInFace = 1 to 32 do 
				( 
						local circularShift = (1 + mod (sgInFace + draftShift - 1) 32) 
						faceSGShifted = bit.set faceSGShifted circularShift (bit.get faceSG sgInFace)
				)		
				setFaceSmoothGroup mesh face faceSGShifted
			)
		)

		else 
		(
		-- bitarray for vertex boundry that we fill with vertex info, weight or color
		local vertBoundry = #{}
		-- get all verts that have a color acting as boundy
		if inVColor do vertBoundry += meshop.getVertsByColor mesh inVColorThreshCol 1 1 1
		-- enable support for weight data
		if inVWeight do meshop.setVDataChannelSupport mesh 2 true
		-- add bitarray of vertices having a bigger weight number then specified threshold
		if inVWeight do vertBoundry += (for vert = 1 to mesh.numverts where (meshop.getVDataValue mesh 2 vert) >= inVWeightThresh collect vert) as bitarray
		
		-- array for face groups
		facegroups = #()
		-- copy the selected face to the testing cache that we empty / subtract each group from. once all groups are formed all faces should be substracted thus resulting in ending the while condition
		testedFaces = selectedFaces
		

		-- no of chunks
		local noChunks = 0
		--repeat till the cache is fully emptied
		while (not testedFaces.isEmpty and limitIter == false) or (limitIter == true and noChunks < testvalIntGrp ) do
		(		
			if debugMsgs do print (testedFaces.numberset as string + " in iteration " + noChunks as string)

			face_array = #{}--init. an array
			--test if a first index was assgned and if the face is still active in the testedFaces set, getting the start of the next group face
			for iTF = 1 to testedFaces.count do while (face_array.count == 0 and testedFaces[iTF] == true) do face_array = #(iTF)

			-- mark when we start / stop the grow
			local chunkStarted = true
			local chunkComplete = false
			-- as long as the faces can grow the chunk is not complete. no grow = chunk complete
			while not chunkComplete do
			(
				--from the startindex triangle, get a polygon
				-- NOTE: if we repat this with the growing face_array perfomance goes bye bye, but its enough to check for the first polygon and then proceed with triangles whilst growing
				if startFromPoly and chunkStarted do face_array = meshop.getPolysUsingFace mesh face_array ignoreVisEdges:false threshhold:45
				--stop the chunkt started signal so for the next grow we deal with triangles again. this starting face as polygon is a fix to help "stray" faces have one SG instead of 2 shared ones (bcs they are 2 triangles).
				chunkStarted = false
				-- get verts from starting index face or if we are in the next iteration the next accumlated / grown face_array effectivly growing it
				local vertsFromFace = meshop.getVertsUsingFace mesh (face_array)
				-- substract the weighted verts from the vertsFromFace, effectivly acting like a boundry / border
				vertsFromFace -= vertBoundry
				--get all faces that are are connected to verts w/o weighting - --this gives us all neighbours till the border of weight / vc blocks us from proceeding. when this is the case a chunk is formed
				local facesFromVerts = meshop.getFacesUsingVert mesh vertsFromFace
				-- make sure we only operate on selected faces and exclude unwanted ones otherwise we grow over
				facesFromVerts -= allFaces - selectedFaces
				--check if we have managed to grow by differecning the 2 bitarrays, if they are empty or 0 there is no difference thus no grow between iterations happend
				local diff = facesFromVerts - face_array as bitarray
				--append all faces to the array forming the group
				--for f in facesFromVerts where findItem face_array f == 0 do append face_array f
				for f in facesFromVerts do append face_array f
				--and repeat till the chunk is complete / there is no difference between the grow iterations
				if diff.isEmpty do chunkComplete = true
		  	)--end while when chunkComplete
			
			-- substract the face_array from the testedFaces to empty out the cache
			testedFaces -= face_array as bitArray

			--if the face array (that has now become the chunk) contains faces, append the face array into the facegroups array
			if face_array.count > 0 do
			( 
				append facegroups face_array
				noChunks += 1 -- increase chunk / groupcount
			)
			

			if debugMsgs do print (testedFaces.numberset as string + " in iteration " + (noChunks) as string + " left")
		)--end while testedFaces

		if debugMsgs do print facegroups.count
		
		local debugFaces = #()

		for i = 1 to facegroups.count do
		(
			--final resulting smoothin group
			local SGroup = 0
			--smart neighbour mode, detect the smoothing group around the facegroup and adjecent groups
			if distMode == 1 do
			(
				-- get neighbouring faces
				local vertsFromFace = meshop.getVertsUsingFace mesh (facegroups[i]) as bitarray
				local neighbourFaces = meshop.getFacesUsingVert mesh vertsFromFace as bitArray - facegroups[i] as bitarray
				-- get all neighbour Smoothin groups
				local neighbourSGs = #{}
				neighbourSGs.count = 32
				for face in neighbourFaces do
				(
					neighbourSGs += intToBitArray (getFaceSmoothGroup mesh face)
				)
				local SGassigned = false
				if (not (-neighbourSGs).isEmpty) then for SG in (-neighbourSGs) while SGassigned == false do
				(
					SGroup = bit.set SGroup SG true
					SGassigned = true
				)
				else SGroup = 0
			)
			if distMode == 2 do
			(
			--Naive method, just assign as many Sgs as you have groups and maybe shift them afterwards
			-- make sure we cylce within 32 available groups
			if (SGRangeMax - SGRangeMin > 0) then 
			(
				local circularShift = SGRangeMin + mod (i) (SGRangeMax - SGRangeMin)
				-- convert grp no. to bitarray integer
				SGroup = bit.set SGroup circularShift true
			)
			else SGroup = 0
			)

			--  hit it johnny
			for face in facegroups[i] do
			(
				setFaceSmoothGroup mesh face SGroup			
			)
		)
	) 

		--if facegroups.count > 0 and testvalIntGrp <= noChunks do mesh.selectedFaces = facegroups[testvalIntGrp]

		--if debugFaces.count > 0 do mesh.selectedFaces = debugFaces
		--mesh.selectedVerts = vertexChunk
		
		
	)
)