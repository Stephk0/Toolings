/*
Smoothing Group by Vertex Boundry
Create smoothing groups from vertex boundry based on weight or color.
effectivly creating the possiblty to define corners in some baselevel poly and inherit the information of the corner through the stack. 
using procedual workflows you can assign smoothin groups in a way that wasnt possible before
by Stephan Viranyi https://www.artstation.com/stephko
Feel free to share and extend to your wishes and msg me for any questions or feedback at stephko@viranyi.de


TODO:

Topo shrink shift
Eval if we can get strips
Add Statistics


--------------------------------------------
--Changelog
--
--01/01/2023: Added Perfomance opimziation by stopring the group on a local and recalling from theere instead of recreatringh groups anew all the time
--
--
--Created 01/09/2022
--------------------------------------------
*/

plugin simpleMeshMod SGFromVB
	name:"SGs from Vert Boundry"
	classID:#(0xa17e2a4, 0x7117b481)
(

	--stored Vertex count to compare against the updated version, init as undefined so we can store it and recall
	local storedMeshVertCount
	-- stored Vertex Boundry to compare against the updated version, init as undefined so we can store it and recall
	local storedVertBoundry

	-- stored selection, if the selection through the stack changes we rebuild the groups
	local storedFaceSelection
	-- stored array for final face groups , init as undefined so we can store it and recall
	local facegroups	
	-- stored array for final stray face groups if they occur , init as undefined so we can store it and recall
	local strayFacesGroups
	
	-- testing caches
	local cachedTestedFaces
	-- stored array for final stray face groups if they occur , init as undefined so we can store it and recall
	local cachedStrayFaces

	-- chunks
	local chunkStarted = false
	local chunkComplete = false





	-- stored Vertex Boundry to compare against the updated version, init as undefined so we can store it and recall
	local storedfacegroupSGIDs
	-- stored array for final face smoothing group IDs, init as undefined so we can store it and recall
	local facegroupSGIDArr


	-- apprently this is suppsed to speed up things but it did not?
	local getVertsUsingFace = meshop.getVertsUsingFace
	local getFacesUsingVert = meshop.getFacesUsingVert
	local getPolysUsingVert = meshop.getPolysUsingVert
	local getPolysUsingFace = meshop.getPolysUsingFace
	local getVDataValue = meshop.getVDataValue

	--trigger to rebuild the groups
	local forceRebuildTrigger = false

	local triggerSGRedist = false

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


	parameters boundryInputParam rollout:params
	(
		faceMode ui:rbb_faceMode default:1 type:#integer animatable:true
		FilterSGFlag ui:chk_FilterSG default:true type:#boolean
		FilterSG ui:spn_FilterSG default:0 type:#integer animatable:true

		inVColor ui:chk_inVColor default:true type:#boolean animatable:true
		inVColorThreshCol ui:cpk_vColorInputThreshCol type:#color animatable:true
		inVColorThresh ui:spn_vColorInputThresh default:1 type:#float animatable:true	
		inVWeight ui:chk_inVWeight default:true type:#boolean animatable:true	
		inVWeightThresh ui:spn_vWeightInputThresh default:1.01 type:#float animatable:true	
	) 
	
	parameters sgSetup rollout:params2
	(
		distMode ui:rbb_distMode default:1 type:#integer animatable:true
		rebuildMode ui:rbb_rebuildMode default:1 type:#integer animatable:true
		forceRebuild ui:btn_forceRebuild default:false type:#boolean
		startFromPoly ui:chk_startFromPoly default:true type:#boolean
		
		--stray group settings
		straySmoothMode ui:rbb_straySmoothMode default:1 type:#integer animatable:true
		straySGValue ui:spn_straySGValue default:0 type:#integer animatable:true	
		strayAngle ui:spn_strayAngle default:45 type:#float animatable:true
		strayAngleShift ui:spn_strayAngleShift default:16 type:#integer animatable:true	
		
		--smart setting, sg fallback if no sg can be assigned
		SGFallBack ui:spn_SGFallBack default:0 type:#integer animatable:true
		neighbourAsPoly ui:chk_NeighbourAsPoly default:false type:#boolean	
		--naive linear range
		SGRangeMin ui:spn_Rmin default:16 type:#integer animatable:true	
		SGRangeMax ui:spn_Rmax default:32 type:#integer animatable:true		
		--draft setttings
		draftAngle ui:spn_draftAngle default:45 type:#float animatable:true
		draftShift ui:spn_draftShift default:16 type:#integer animatable:true		
	)

	parameters debugMain rollout:debugParams 
	(
		debugMsgs ui:chk_Msgs default:false type:#boolean animatable:true
		debugTime ui:chk_debugTime default:false type:#boolean animatable:true
		debugRebuildMsg ui:chk_debugRebuildMsg default:false type:#boolean animatable:true
		limitIter ui:chk_Limit default:false type:#boolean animatable:true		
		testvalIntGrp ui:spn_testValIntGrp default:1 type:#integer animatable:true
		testvalIntGrw ui:spn_testValIntGrw default:1 type:#integer animatable:true
		
	) 

	rollout params "Boundry Input" category:1
	(

		group "Operate on"
		(
			radiobuttons rbb_faceMode labels:#("Total Faces", "Selected Faces") align:#left
			checkbox chk_FilterSG "Filter Selection by SG:" checked:true tooltip:"Filter Face Selection by specified Smoothing group (Default: 0)"
			spinner spn_FilterSG "Filtered SG:" type:#integer range:[0,32,0]  tooltip:"Filter Face Selection by specified Smoothing group (Default: 0)" align:#left enabled:FilterSGFlag
		)
		group "Get Boundry Input"
		(
			checkbox chk_inVColor "from Vertex Color" checked:true tooltip:"Vertex Color acts as boundry input" align:#left
			colorpicker cpk_vColorInputThreshCol "Threshold Color" color:[0,0,0] modal:false tooltip:"Vertex Color Threshold" align:#left enabled:inVColor
			spinner spn_vColorInputThresh "Color Threshold" type:#float range:[0,1e6,1] tooltip:"How much the color can daviate to form a group" align:#left enabled:inVColor
			checkbox chk_inVWeight "from Vertex Weight" checked:true tooltip:"Vertex Weight Threshold acts as boundry input" align:#left
			spinner spn_vWeightInputThresh "Threshold" type:#float range:[0,1e6,1.01] tooltip:"Vertex Weight Threshold" align:#left  enabled:inVWeight
		)

		on rbb_faceMode changed state do forceRebuildTrigger = state

		on chk_FilterSG changed state do
		( 
			spn_FilterSG.enabled = state
			forceRebuildTrigger = true
		)

		on chk_inVColor changed state do
		( 
			cpk_vColorInputThreshCol.enabled = state
			spn_vColorInputThresh.enabled = state
			forceRebuildTrigger = true
		)

		on chk_inVWeight changed state do
		( 
			spn_vWeightInputThresh.enabled = state
			forceRebuildTrigger = true
		)

		on spn_vColorInputThresh val changed do
		(
			forceRebuildTrigger = true
			
		) 
		--on spn_vWeightInputThresh val changed do forceRebuildTrigger = true
		



	)
	rollout params2 "Smoothing Groups" category:2
	(
		group "Distribution Method"
		(
			radiobuttons rbb_distMode labels:#("Smart Neighbour", "Naive Linear", "Draft by Angle Mode") align:#left  tooltip:"SG Distrbution Method
			Smart Neighbour: SGs are assigned based on the neighbouring faces. If SG 1 is assigned to a neighbour group for example SG 1 will not be used for the group and so on.
			Naive Linear (faster): Each group (i.e group #1-16) gets a SG (i.e SG 1-16) assigned. To avoid conflicting SGs it is possible to limit and shift the distribution range (i.e shifting SG 1-16 to SG 16-32).
			Draft Mode (fastest): Groups get classic angle based autoSmooth assigned. Draft Mode is to ease the modelling process with heavy models while retaining a rough preview as you would with traditional autosmoothing methods.
			"
		)

		

		group "Smart Neighbour"
		(
			checkbox chk_NeighbourAsPoly "Poly Neighbour (Precise)" align:#left checked:false  enabled:(distMode == 1) tooltip:"Attain neighbour SG from Poly rather than triangle. This is more precise when dealing with complex groups but comes at cost of perfomance"	 
			spinner spn_SGFallBack "Unassignable Fallback" type:#integer range:[0,32,0] enabled:(distMode == 1) width:80 align:#left tooltip:"Fallback SG to assign if no SG can be assigned (avoid using big number of redundant SGs to avoid fallback assingment)" enabled:(distMode == 1)
		)
		group "Naive Linear Range"
		(
			spinner spn_Rmin "Range Min" type:#integer range:[1,31,16] enabled:(distMode == 2)
			spinner spn_Rmax "Range Max" type:#integer range:[2,32,32] enabled:(distMode == 2)
		)

		group "Draft Mode"
		(
			spinner spn_draftAngle "Draft Angle" type:#float range:[0,180,45] enabled:(distMode == 3)
			spinner spn_draftShift "Draft Shift" type:#integer range:[0,32,16] enabled:(distMode == 3)
		)

		group "Stray Smoothing"
		(
			radiobuttons rbb_straySmoothMode labels:#("Stray-by-Stray", "Smooth adjecent Strays", "Smooth by Angle", "Specific Smooth Group") align:#left   enabled:(distMode != 3) tooltip:""
			spinner spn_strayAngle "Smooth Angle" type:#float range:[0,180,45] enabled:(straySmoothMode == 3)
			spinner spn_strayAngleShift "Group Shift" type:#integer range:[0,32,16] enabled:(straySmoothMode == 3)
			checkbox chk_strayAngleSmart "Smart Neighbour" align:#left checked:false enabled:false tooltip:"not implemented yet"	 
			spinner spn_straySGValue "Specific Group" type:#integer range:[0,32,0] enabled:(straySmoothMode == 4)
		)

		group "Rebuild Mode"
		(
			radiobuttons rbb_rebuildMode labels:#("On Vert Change (Faster)", "Continous (Slower)", "Manual Only") align:#left   enabled:(distMode != 3) tooltip:"
			On Vert Change:  Only rebuild Groups if a change in the vertices number or vertex colors have occured
			Continous:  Rebuild Groups with every operation. Not recommended unless the upper option provides undesireable results
			Manual Only:  Rebuild Groups only when triggered
			"
			checkbutton  btn_forceRebuild "Force Rebuild" align:#center checked:forceRebuildTrigger
			checkbox chk_startFromPoly "Start from Poly (Precise)" align:#left checked:true tooltip:"Facesearch start from a Polygon rather than a triangle. Polygon is more accurate at the cost of perfomance. Disable this only if you encounter perfomance problems"	
		)

		spinner spn_groupPackAngle "Group Pack Angle" type:#float range:[0,1,1] visible:false

		on rbb_distMode changed state do 
		(
			spn_SGFallBack.enabled = state == 1
			chk_NeighbourAsPoly.enabled = state == 1

			spn_Rmin.enabled = state == 2
			spn_Rmax.enabled = state == 2

			spn_draftAngle.enabled = state == 3
			spn_draftShift.enabled = state == 3

			rbb_straySmoothMode.enabled = state != 3
			spn_straySGValue.enabled = state != 3
			rbb_rebuildMode.enabled = state != 3
			

			forceRebuildTrigger = true
		)

		on rbb_rebuildMode changed state do 
		(
			forceRebuildTrigger = true
		)

		--on btn_forceRebuild pressed do forceRebuildTrigger = true
		on btn_forceRebuild changed state do
		( 
			forceRebuildTrigger = true
			btn_forceRebuild.checked = false
		)

		on rbb_straySmoothMode changed state do 
		(
			spn_strayAngle.enabled = state == 3
			spn_strayAngleShift.enabled = state == 3
			
			spn_straySGValue.enabled = state == 4
			forceRebuildTrigger = true
		)

		on spn_strayAngle changed val do triggerSGRedist = true
		on spn_strayAngle val entered do triggerSGRedist = true
		on spn_strayAngle buttonUp do triggerSGRedist = true

		on spn_straySGValue changed val do triggerSGRedist = true
		on spn_straySGValue val entered do triggerSGRedist = true
		on spn_straySGValue buttonUp do triggerSGRedist = true

		on spn_Rmin val changed do if val >= spn_Rmax.value do spn_Rmin.value = spn_Rmax.value	
		on spn_Rmax val changed do if val >= spn_Rmin.value do spn_Rmax.value = spn_Rmin.value
	)
	
	rollout debugParams "Debug"
	(
		checkbox chk_Msgs "Iteration & Group" checked:false tooltip:"output iterations and groups"
		checkbox chk_debugTime "Time" checked:false tooltip:"output time taken"
		checkbox chk_debugRebuildMsg "RebuildMsg" checked:false tooltip:"RebuildMsg"
		checkbox chk_Limit "Limit Iter" checked:false tooltip:"Limit the chunk iteration step"
		spinner spn_testValIntGrp "grp iter" type:#integer range:[1,1e6,32]
		spinner spn_testValIntGrw "grow iter" type:#integer range:[1,1e6,0]		
	)
	
	on modifyMesh do
	(
		--set SG distribution min max, make sure the min is never higher then the max and vice versa
		if SGRangeMin >= SGRangeMax do SGRangeMin = SGRangeMax
		if SGRangeMax <= SGRangeMin do SGRangeMax = SGRangeMin

		-- Debug Time, start here
		if debugTime do local startTime = timeStamp()
		
		-------------------------------------
		-- get the faces to process
		-------------------------------------

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
			-- not sure why i did this way previously but above should be correct		
			--selectedFaces -= -faceWithSG0
		)

		-------------------------------------
		-- Autosmooth Mode, cheap and dirty for prototyping. if user chooses this, code ends here
		-------------------------------------

		if distMode == 3 then
		(
			--draft mode: autosmooth everything, create no groups, just work fast and be (eventually) toggleable
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

			forceRebuildTrigger = false
		)

		else 
		(

			-------------------------------------
			-- vert boundry get data and check for change
			-------------------------------------


			-- bitarray for vertex boundry that we fill with vertex info, weight or color
			local vertBoundry = #{}
			--vertBoundry.count = mesh.numverts
			-- get all verts that have a color acting as boundy
			if inVColor do vertBoundry += meshop.getVertsByColor mesh inVColorThreshCol inVColorThresh inVColorThresh inVColorThresh
			-- enable support for weight data
			if inVWeight do meshop.setVDataChannelSupport mesh 2 true
			-- add bitarray of vertices having a bigger weight number then specified threshold
			if inVWeight do vertBoundry += (for vert = 1 to mesh.numverts where (getVDataValue mesh 2 vert) >= inVWeightThresh collect vert) as bitarray
		

			-------------------------------------
			-- rebuild trigger if change occured
			-------------------------------------
			-- TODO:  make facecount check

			-- init check if a group rebuild is required meshwise
			local triggerGroupRebuild  = false

			if (rebuildMode == 1 and (storedMeshVertCount != mesh.numverts or storedMeshVertCount == undefined or storedVertBoundry == undefined or (vertBoundry.numberset - storedVertBoundry.numberset) != 0) or storedFaceSelection == undefined or (storedFaceSelection.numberset - selectedFaces.numberset) != 0) then
			(
				forceRebuildTrigger = true
				
				--store the vert count to compare against the incoming mesh verts to see if there is any difference
				storedMeshVertCount = mesh.numverts
				--store the vert boundry to check if the mesh weights/colors were altered
				storedVertBoundry = vertBoundry
				storedVertBoundry.count = mesh.numverts
				--store the prev face slection through stack if change occurs
				storedFaceSelection = selectedFaces
			)

			-------------------------------------
			-- rebuild smoothing groups
			-------------------------------------

			-- init as facegroupos for first time if we dont have any content as an empty array
			if facegroups == undefined do facegroups = #()
			if strayFacesGroups == undefined do strayFacesGroups = #()
			if cachedTestedFaces == undefined do cachedTestedFaces = #{}
			if cachedStrayFaces == undefined do cachedStrayFaces = #{}

			-- Rebuild was triggered or we are in continous mode
			if rebuildMode == 2 or forceRebuildTrigger do 
			(
				-- start groupo build msg
				if debugRebuildMsg do print "Trigger Group Rebuild"
				
				--clear the old group
				facegroups = #()
				--clear the old stray group
				strayFacesGroups = #()
				--clear chaches
				cachedTestedFaces = #{}
				cachedStrayFaces = #{}
				
				-- copy the selected face to the testing cache that we empty / subtract each group from. once all groups are formed all faces should be substracted thus resulting in ending the while condition
				cachedTestedFaces = selectedFaces
				cachedStrayFaces.count = cachedTestedFaces.count

				-- no of chunks
				local noChunks = 0
				--per chunk face array
				local face_array = #{}


			-------------------------------------
			-- WHILE LOOP START 
			-------------------------------------			

				--repeat till the cache is fully emptied
				while (not cachedTestedFaces.isEmpty and limitIter == false) or (limitIter == true and noChunks < testvalIntGrp ) do
				(		
					if debugMsgs do print (cachedTestedFaces.numberset as string + " in iteration " + noChunks as string)

					-------------------------------------
					-- build face groups chunk
					-------------------------------------


					face_array = #{}--init. an array
					--test if a first index was assgned and if the face is still active in the cachedTestedFaces set, getting the start of the next group face
					--for iTF = 1 to cachedTestedFaces.count do while (face_array.count == 0 and cachedTestedFaces[iTF] == true) do face_array = #(iTF)
					for iTF in cachedTestedFaces do while (face_array.count == 0 and cachedTestedFaces[iTF] == true) do face_array = #{iTF}
					--check if we assigned a face from test cache
					if face_array.count > 0 do
					(
						-- TODO Eval moving these vars outside of while loop
						-- mark when we start / stop the grow
						chunkStarted = true
						chunkComplete = false
						local growDiff
						-- as long as the faces can grow the chunk is not complete. no grow = chunk complete
						while not chunkComplete do
						(
							--from the startindex triangle, get a polygon
							-- NOTE: if we repat this with the growing face_array perfomance goes bye bye, but its enough to check for the first polygon and then proceed with triangles whilst growing
							if startFromPoly and chunkStarted do face_array = getPolysUsingFace mesh face_array ignoreVisEdges:false threshhold:180
							--stop the chunkt started signal so for the next grow we deal with triangles again. this starting face as polygon is a fix to help "stray" faces have one SG instead of 2 shared ones (bcs they are 2 triangles).
							chunkStarted = false
							-- get verts from starting index face or if we are in the next iteration the next accumlated / grown face_array effectivly growing it
							local vertsFromFace 	= getVertsUsingFace mesh (face_array)
							local neighbourFaces 	= getFacesUsingVert mesh vertsFromFace

							-- substract the weighted verts from the vertsFromFace, effectivly acting like a boundry / border
							vertsFromFace 			-= vertBoundry
							--facesFromVerts -= (getFacesUsingVert mesh vertBoundry)
							--get all faces that are are connected to verts w/o weighting - --this gives us all neighbours till the border of weight / vc blocks us from proceeding. when this is the case a chunk is formed
							local facesFromVerts 	= getFacesUsingVert mesh vertsFromFace

							--attempting to pack groups together by angle but failed
							/*
							local avgNormalnbor = [0,0,0]
							for f in neighbourFaces do avgNormalnbor += getFaceNormal mesh f
							avgNormalnbor /= neighbourFaces.numberset

							local avgNormalfa = [0,0,0]
							for f in face_array do avgNormalfa += getFaceNormal mesh f
							avgNormalfa /= face_array.numberset

							--print (dot avgNormalnbor avgNormalfa )
							--print neighbourFaces.count
							--print neighbourFaces.numberset
							if (dot avgNormalnbor avgNormalfa >= groupPackAngle) do facesFromVerts += neighbourFaces
							*/
							-- make sure we only operate on selected faces and exclude unwanted ones otherwise we grow over
							facesFromVerts 			*= selectedFaces
							--check if we have managed to grow by differecning the 2 bitarrays, if they are empty or 0 there is no difference thus no grow between iterations happend
							growDiff 				= facesFromVerts - face_array
							--append all faces to the array forming the group
							face_array += facesFromVerts
							--and repeat till the chunk is complete / there is no difference between the grow iterations
							if growDiff.isEmpty do chunkComplete = true
						)--end while when chunkComplete
					
						--if the face array (that has now become the chunk) contains faces, append the face array into the facegroups array
						if face_array.numberset > 0 do
						( 
							--every group gets one array of faces
							if face_array.numberset > 2 or straySmoothMode == 1 then append facegroups face_array
							--else append strayFacesGroups face_array
							else if straySmoothMode > 1 then cachedStrayFaces += face_array
							noChunks += 1 -- increase chunk / groupcount
						)
						-- substract the face_array from the cachedTestedFaces to empty out the cache
						cachedTestedFaces -= face_array 
					)			
					if debugMsgs do print (cachedTestedFaces.numberset as string + " in iteration " + (noChunks + 1) as string + " left")
				)--end while cachedTestedFaces

				-------------------------------------
				-- build stray face groups
				-- todo if statement if there are strays
				-------------------------------------

				if straySmoothMode == 2 and not cachedStrayFaces.isEmpty then 
				(
					local testedStrayFaces = cachedStrayFaces
					append facegroups cachedStrayFaces	
				)

				if debugMsgs do print (facegroups.count as string + " Groups created")
		)
			--------------------------------------------------
			---Groups have been created 
			--------------------------------------------------

			--------------------------------------------------
			---Assign smoothin group to face / stray groups
			--------------------------------------------------

			if not cachedStrayFaces.isEmpty and straySmoothMode >= 3 do
			(
				
				--autosmooth all strays and then shift
				--TODO: include smart neighbour option for autosmooth
				if straySmoothMode == 3 do 
				(
					meshop.autoSmooth mesh cachedStrayFaces strayAngle
					
					for face in cachedStrayFaces do
					(
						local faceSG = getFaceSmoothGroup mesh face
						local faceSGShifted = 0

						for sgInFace = 1 to 32 do 
						( 
							local circularShift = (1 + mod (sgInFace + strayAngleShift - 1) 32) 
							faceSGShifted = bit.set faceSGShifted circularShift (bit.get faceSG sgInFace)
						)		
						setFaceSmoothGroup mesh face faceSGShifted
					)
					
					mesh.selectedFaces = selectedFaces
				)
				
				if straySmoothMode == 4 do 
				(
					--determine if its a specific group or no group and set bitinteger accordingly
					local straySG = 0
					if straySGValue != 0 do straySG = (bit.set straySG straySGValue true)

					for face in cachedStrayFaces do (setFaceSmoothGroup mesh face straySG)
				)		
				
			)
			--trigger redistrbution of smoothing groups if the previous ones have been alterd
			--accumalte all face SG ids as bitinteger without conversion, so we get a custom code for the face if SGs have changed
			local currentFacegroupIDs = 0
			for f in allFaces do currentFacegroupIDs += (getFaceSmoothGroup mesh f)


			if (storedfacegroupSGIDs == undefined or storedfacegroupSGIDs != currentFacegroupIDs) then
			(
				triggerSGRedist = true
				storedfacegroupSGIDs = currentFacegroupIDs				
				if debugRebuildMsg do print "Trigger SG Redistribution"
			) 

			--------------------------------------------------
			---Assign smoothin groups to the facegroups
			--------------------------------------------------

			--final resulting smoothin groups, init first time if we dont have any content as an empty array
			if facegroupSGIDArr == undefined do facegroupSGIDArr = #()

			
			-- neighbour Smoothing groups
			local neighbourSGs = #{}
			neighbourSGs.count = 32

			--define variables before the for loop is apprentyl more perfomant
			local vertsFromFace
			local neighbourFaces
		
			
			--repeat loop for all groups
			for i = 1 to facegroups.count do
			(
				if rebuildMode == 2 or forceRebuildTrigger or triggerSGRedist do 
				(
					
					--reset for each group
					facegroupSGIDArr[i] = 0

					--smart neighbour mode, detect the smoothing group around the facegroup and adjecent groups
					if distMode == 1 do
					(
						-- get neighbouring faces
						vertsFromFace 	= getVertsUsingFace mesh (facegroups[i])
						-- get from triangle face
						-- get from poly which is more precise
						if neighbourAsPoly then neighbourFaces 	= getPolysUsingVert mesh vertsFromFace as bitArray
						else neighbourFaces 	= getFacesUsingVert mesh vertsFromFace as bitArray 
						--substract the own face group so we get the neighbours only
						neighbourFaces -= facegroups[i] as bitarray
						-- reinit neighbourSG bitarray to get all neighbour Smoothing groups of facegroup
						neighbourSGs = #{}
						neighbourSGs.count = 32
						--add them to the list of "occupied" SGs
						for face in neighbourFaces do neighbourSGs += intToBitArray (getFaceSmoothGroup mesh face)

						--loop through the inverse of the occupied smoothing groups, aka the "available" smoothing groups
						--if we found an available / suitable Smoothing Group stop the loop by overwriting facegroupSGIDArr[i] to an int other than zero
						if (not (-neighbourSGs).isEmpty) then for SG in (-neighbourSGs) while facegroupSGIDArr[i] == 0 do facegroupSGIDArr[i] = bit.set facegroupSGIDArr[i] SG true
						--if all SGs are occupied, assign a fallback
						else if SGFallBack != 0 then facegroupSGIDArr[i] = bit.set facegroupSGIDArr[i] SGFallBack true
						else facegroupSGIDArr[i] = 0
					)

					if distMode == 2 do
					(

						--Naive method, just assign as many Sgs as you have groups and maybe shift them afterwards
						-- make sure we cylce within 32 available groups
						if (SGRangeMax - SGRangeMin > 0) then 
						(
							local circularShift = SGRangeMin + mod (i) (SGRangeMax - SGRangeMin)
							-- convert grp no. to bitarray integer
							facegroupSGIDArr[i] = bit.set facegroupSGIDArr[i] circularShift true
						)
						else facegroupSGIDArr[i] = 0
					)
				)
				-- set SG for each facegroup so the next loop in the groups knows what SGs where placed
				for face in facegroups[i] do
				(
					--setFaceSmoothGroup mesh face finalSGInt			
					setFaceSmoothGroup mesh face facegroupSGIDArr[i]	
				)
			)	
		) -- end else statement of draft mode or not


		if debugTime do print ("Operation took " + (timeStamp() - startTime) as string + " ms")

		--reset trigger
		forceRebuildTrigger = false
		triggerSGRedist = false

		--this causes a weird bug, not sure how to handle this, maybe post event?
		--params2.btn_forceRebuild.checked = forceRebuildTriggers
		--if facegroups.count > 0 and testvalIntGrp <= noChunks do mesh.selectedFaces = facegroups[testvalIntGrp]

		--if debugFaces.count > 0 do mesh.selectedFaces = debugFaces
		--mesh.selectedVerts = vertexChunk
		
		
	)
)