/*
Smoothingr group from Material ID
by Stephan Viranyi https://www.artstation.com/stephko
Feel free to share and extend to your wishes and msg me for any questions or feedback at stephko@viranyi.de
*/
--todo: add whole mesh bool

plugin simpleMeshMod SGFromMatID
	name:"Smoothing Groups from Material ID"
	classID:#(0x4438359, 0x58a91035)
	version:080
(
	------------------------
	-- about variables section (for versioning) STARTS HERE
	------------------------
	local versionYear = 2024
	local aboutMain = "Smoothing Groups from Mat ID"

	fn composeVersionNrText v =
	(
		return ("Version " + (formattedPrint ((v as float)/100) format:"0.2f") + " | " + ( versionYear as string))
	)

	local aboutDocuLink = "https://docs.google.com/document/d/1fIKEurSNeaazzYsPnCTYT7bVO4R4btWzTzvLRpjNutY/edit?usp=sharing"
	local aboutShopLink = "https://www.artstation.com/stephko"

	------------------------
	-- about variables section (for versioning) ENDS HERE
	------------------------


	-- apprently this is suppsed to speed up things but it did not?
	local getVertsUsingFace = meshop.getVertsUsingFace
	local getFacesUsingVert = meshop.getFacesUsingVert
	local getPolysUsingVert = meshop.getPolysUsingVert
	local getPolysUsingFace = meshop.getPolysUsingFace

	--function to convert bit integer to bitarray
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
		faceMode ui:rbb_faceMode default:1 type:#integer animatable:true
		distMode ui:rbb_distMode default:1 type:#integer animatable:true
		
		--smart setting, sg fallback if no sg can be assigned
		SGFallBack ui:spn_SGFallBack default:0 type:#integer animatable:true
		neighbourAsPoly ui:chk_NeighbourAsPoly default:false type:#boolean	
		--naive linear range
		SGRangeMin ui:spn_Rmin default:1 type:#integer animatable:true	
		SGRangeMax ui:spn_Rmax default:32 type:#integer animatable:true	
	) 
	
	rollout params "Parameters" category:1 
	(
		group "Operate on"
		(
			radiobuttons rbb_faceMode labels:#("Selected Faces", "Total Faces")
		)

		group "Smoothing Group Distribution"
		(
			radiobuttons rbb_distMode labels:#("Smart Neighbour", "Linear Modulo")  toolTip: "Distribute by assigning best smoothing group that is not used by adjecent face OR by mapping the material IDs to smoothing groups 1:1 repeating after Material 32"
		)
		group "Smart Neighbour"
		(
			checkbox chk_NeighbourAsPoly "Poly Neighbour (Precise)" align:#left checked:false  enabled:(distMode == 1) tooltip:"Attain neighbour SG from Poly rather than triangle. This is more precise when dealing with complex groups but comes at cost of perfomance"	 
			spinner spn_SGFallBack "Unassignable Fallback" type:#integer range:[0,32,0] enabled:(distMode == 1) width:80 align:#left tooltip:"Fallback SG to assign if no SG can be assigned (avoid using big number of redundant SGs to avoid fallback assingment)" enabled:(distMode == 1)
		)

		group "Naive Linear Range"
		(
			spinner spn_Rmin "Range Min" type:#integer range:[1,31,1] enabled:(distMode == 2)
			spinner spn_Rmax "Range Max" type:#integer range:[2,32,32] enabled:(distMode == 2)
		)

		on rbb_distMode changed state do 
		(
			spn_SGFallBack.enabled = state == 1
			chk_NeighbourAsPoly.enabled = state == 1

			spn_Rmin.enabled = state == 2
			spn_Rmax.enabled = state == 2
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

		--load version number. version is not accessible as local var up until the rollout is present
		on paramsAbout open do lab_aboutVersion.text = composeVersionNrText version 
	)

	------------------------
	-- about section ENDS HERE
	------------------------

	on modifyMesh do
	(
		--set SG distribution min max, make sure the min is never higher then the max and vice versa
		if SGRangeMin >= SGRangeMax do SGRangeMin = SGRangeMax
		if SGRangeMax <= SGRangeMin do SGRangeMax = SGRangeMin

		--get the selection from stack
		local selectedFaces = getFaceSelection mesh as bitarray
		--operate on selected or all
		if faceMode == 2 do selectedFaces = mesh.faces as bitarray

		--get the material ID and their corresponding faces as arrays
		local facematIDGroups = #()
		local facematIDGroupFaces = #()
	
		--variables outside the for loop for material id sorting
		local faceMatID
		local idItem

		for face in selectedFaces do
		(	
			--get the faces material ID
			faceMatID = getFaceMatID mesh face
			--setup a list of facematIDGroups based on material IDs
			appendIfUnique facematIDGroups faceMatID
			
			--find to which entry the Material ID int belongs to
			idItem = findItem facematIDGroups (faceMatID)
			--if no face was added yet create a new subarray
			if facematIDGroupFaces[idItem] == undefined do facematIDGroupFaces[idItem] = #{}
			--add the corresponding face to the group
			-- ??? does this make sense, shouldnt be the var before = be gone?
			facematIDGroupFaces[idItem] = append facematIDGroupFaces[idItem] face
		)

		--final resulting smoothin groups, init first time if we dont have any content as an empty array
		if facegroupSGIDArr == undefined do facegroupSGIDArr = #()
				
		-- neighbour Smoothing groups
		local neighbourSGs = #{}
		neighbourSGs.count = 32

		--variables outside teh for loop for smart distribution mode
		local vertsFromFace
		local neighbourFaces

		for i = 1 to facematIDGroups.count do
		(
			--reset for each group
			facegroupSGIDArr[i] = 0

			case distMode of 
			(
				1:
				(
					--smart method
					-- get neighbouring faces
					vertsFromFace 	= getVertsUsingFace mesh (facematIDGroupFaces[i])
					-- get from triangle face
					-- get from poly which is more precise
					if neighbourAsPoly then neighbourFaces 	= getPolysUsingVert mesh vertsFromFace as bitArray
					else neighbourFaces 	= getFacesUsingVert mesh vertsFromFace as bitArray 
					--substract the own face group so we get the neighbours only
					neighbourFaces -= facematIDGroupFaces[i] as bitarray
					-- reinit neighbourSG bitarray to get all neighbour Smoothing groups of facegroup
					neighbourSGs = #{}
					neighbourSGs.count = 32
					--add them to the list of "occupied" SGs
					for face in neighbourFaces do neighbourSGs += intToBitArray (getFaceSmoothGroup mesh face)

					--loop through the inverse of the occupied smoothing groups, aka the "available" smoothing groups
					--if we found an available / suitable Smoothing Group stop the loop by overwriting facegroupSGIDArr[i] to an int other than zero ending the while statement
					if (not (-neighbourSGs).isEmpty) then for SG in (-neighbourSGs) while facegroupSGIDArr[i] == 0 do facegroupSGIDArr[i] = bit.set facegroupSGIDArr[i] SG true
					--if all SGs are occupied, assign a fallback
					else if SGFallBack != 0 then facegroupSGIDArr[i] = bit.set facegroupSGIDArr[i] SGFallBack true
					else facegroupSGIDArr[i] = 0
				)
				2:
				(
					--naive method
					if (SGRangeMax - SGRangeMin > 0) then 
					(
						local circularShift = SGRangeMin + mod (facematIDGroups[i] - 1) (SGRangeMax - SGRangeMin + 1)
						facegroupSGIDArr[i] = bit.set facegroupSGIDArr[i] circularShift true -- Calculate smoothing group using modulo.
					)
				)
			)

			for face in facematIDGroupFaces[i] do
			(
				setFaceSmoothGroup mesh face facegroupSGIDArr[i]
			)
			
			--setFaceSmoothGroup mesh face smoothingGroup
		)
		/*
		for face in selectedFaces do
		(
			--get this 32 bit integer representing a bitarray of the smooth groups assigned to the face
			--we need to use 32 bit interger to assign the face smoothing group, unless we convert it to an actual bitarray as described below
			local faceMatID = getFaceMatID mesh face
			local circularShift = (1 + mod (faceMatID - 1) 32)
			--create a new 32 bit int where we assign the new smoohting groups to
			local smoothingGroup = bit.set smoothingGroup circularShift true -- Calculate smoothing group using modulo.
			setFaceSmoothGroup mesh face smoothingGroup

			
		)
		*/
	)
)