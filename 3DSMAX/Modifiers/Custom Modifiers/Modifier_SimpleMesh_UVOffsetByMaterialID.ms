/*
Uv Offset by Material ID.
Allows quick creation of atlases based on material IDs.
by Stephan Viranyi https://www.artstation.com/stephko
Feel free to share and extend to your wishes and msg me for any questions or feedback at stephko@viranyi.de
*/

plugin simpleMeshMod UVOffsetByMaterialID
	name:"UV Offset By Material ID"
	classID:#(0x30b473d9, 0x57135a93)
(

	local resultingTilesString = "Resulting Tiles: "

	fn clamp minVal maxVal val =
	(
		if val < minVal then val = minVal
		else if val > maxVal then val = maxVal
		return val
	)

	fn calcTileUI tileXVal tileYVal =
	(
		return resultingTilesString + ((tileXVal * tileYVal) as string)
	)

	parameters InputParam rollout:params
	(
		faceMode ui:rbb_faceMode default:1 type:#integer animatable:true
		faceModeExlude ui:chk_faceModeExlude default:false type:#boolean
		faceModeExludeID ui:spn_faceModeExludeID default:0 type:#integer animatable:true

	) 
	
	parameters mappingSetup rollout:params2
	(
		prePlanarMap ui:chk_PrePlanarMap default:false type:#boolean animatable:true
		prePlanarMapAxis ui:rbb_MapAxis default:1 type:#integer animatable:true
		prePlanarFittingStyle ui:rbb_FittingStyle default:1 type:#integer animatable:true
		preMapPadding ui:spn_preMapPadding default:0 type:#float animatable:true
		
		tileX ui:spn_TileX default:1 type:#integer animatable:true
		tileY ui:spn_TileY default:1 type:#integer animatable:true

		UVfitMode ui:rbb_UVfitMode default:1 type:#integer animatable:true
		postResize ui:spn_postResize default:100 type:#float animatable:true
		
	)

	parameters debugMain rollout:debugParams
	(
		debugMsgs ui:chk_Msgs default:false type:#boolean animatable:true
		limitIter ui:chk_Limit default:false type:#boolean animatable:true		
		testvalIntGrp ui:spn_testValIntGrp default:1 type:#integer animatable:true
		testvalIntGrw ui:spn_testValIntGrw default:1 type:#integer animatable:true	
	) 

	rollout params "Face Input"
	(

		group "Operate on"
		(
			radiobuttons rbb_faceMode labels:#("Total Faces", "Selected Faces") align:#left
			checkbox chk_faceModeExlude "Exclude Faces" checked:true tooltip:"Filter Face Selection by specified Smoothing group (Default: 0)"
			spinner spn_faceModeExludeID "Mat ID" type:#integer range:[0,32,0]  tooltip:"Filter Face Selection by specified Smoothing group (Default: 0)" align:#left
		)		

	)
	rollout params2 "Tile Mapping"
	(

		group "Tile Grid Setting"
		(
			spinner spn_TileX "Tile X" type:#integer range:[1,1e6,1] align:#left width:40
			spinner spn_TileY "Tile Y" type:#integer range:[1,1e6,1] align:#left width:40
			label lab_resultingTiles resultingTilesString align:#left

			
		)

		on spn_TileX changed val do ( lab_resultingTiles.text = calcTileUI spn_TileX.value spn_TileY.value )
		on spn_TileY changed val do ( lab_resultingTiles.text = calcTileUI spn_TileX.value spn_TileY.value )
		on params2 open do ( lab_resultingTiles.text = calcTileUI spn_TileX.value spn_TileY.value )

		group "Pre Planar Map"
		(
			checkbox chk_PrePlanarMap "Pre Planar Map" checked:false tooltip:"Apply a simple Planar Map"	
			radiobuttons rbb_MapAxis labels:#("XY", "YZ", "ZX") align:#left  tooltip:"Map Axis"
			radiobuttons rbb_FittingStyle labels:#("Uniform", "Stretch", "No fit") columns:1 align:#left  tooltip:"Pre Planar map uniformly to fit within the 0-1 UV range or stretch to entire 0-1 UV Space or map 1:1 with no fitting"
			spinner spn_preMapPadding "Padding" type:#float range:[-1e6,1e6,0] width:80 align:#left tooltip:"Padding of the Planar Map"

			spinner spn_ExcludeFaces "Exclude Mat ID" type:#integer range:[0,1e6,1000] width:80 tooltip:"Exclude Faces from Planar Mapping with this Material ID assgined. This is useful if you have premapped chunks you want to retain but still position onto the atlas" align:#left
			
		)

		group "Tile Sizing"
		(
			radiobuttons rbb_UVfitMode labels:#("Normalized / Resize", "Free run / Keep Size") columns:1 align:#left tooltip:"Should the final Tile UVs be resized to the 0-1 UV Space or placed next to the 0-1 UV space in their original size"	
			spinner spn_postResize "Tile Resizing" type:#float range:[0,1e6,100] width:80 align:#left tooltip:"Size of the UVs on tile. Smaller Value"			
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

		-- all faces for later
		local allFaces = mesh.faces as bitarray
		-- only selected thru stack
		local selectedFaces = getFaceSelection mesh as bitarray
		-- if none is selected
		if faceMode == 1 do selectedFaces = allFaces

		if faceModeExlude do
		(	
			local excludedFaces = #{}
			excludedFaces = (for face = 1 to mesh.numfaces where (getFaceMatID mesh face) == faceModeExludeID collect face) as bitarray
			selectedFaces -= -excludedFaces
		)
		
		-------------------------------
		-- Pre Planar Mapping
		-------------------------------
		--set up a projection projMatrix for the mapper
		if prePlanarMap do
		(
			-------------------------------
			--calucate bounds
			-------------------------------

			--Get the face vertices, add their positions together, divide by the number of the vertices - that’s your centerpoint. - Swordslayer

			local boundMin = [0,0,0]
			local boundMax = [0,0,0]
			local centerPoint = [0,0,0]

			for vert = 1 to mesh.vertices.count do 
			(
				local vertPos = getVert mesh vert
				centerPoint += vertPos
				if vertPos.x > boundMax.x do boundMax.x  = vertPos.x
				if vertPos.x < boundMin.x  do boundMin.x  = vertPos.x
				if vertPos.y > boundMax.y  do boundMax.y = vertPos.y
				if vertPos.y < boundMin.y do boundMin.y = vertPos.y
				if vertPos.z > boundMax.z  do boundMax.z = vertPos.z
				if vertPos.z < boundMin.z do boundMin.z = vertPos.z
			)
			local boundSize = boundMax - boundMin
			centerPoint = centerPoint / mesh.vertices.count
			/*
			print centerPoint
			print ("bound width is " + boundSize.x as string)
			print ("bound height is " + boundSize.y as string)
			print (amax (#(boundSize.x, boundSize.y)))
			*/

			local projMatrix = matrix3 1

			local axisNormal
			case prePlanarMapAxis of
			(
				1:(axisNormal = [0,0,1])
				2:(axisNormal = [0,1,0])
				3:(axisNormal = [1,0,0])
			)
			local projScaleMatrix
			case prePlanarFittingStyle of
			(
				1:
				(
					--uniform
					local remainderAxis
					case prePlanarMapAxis of
					(
						1:(remainderAxis = [0,0,1])
						2:(remainderAxis = [1,0,0])
						3:(remainderAxis = [0,1,0])
					)
					local boundsRemainder = boundSize * (1 - remainderAxis)
					local uniformBoundSize = amax (#(boundsRemainder.x, boundsRemainder.y, boundsRemainder.z))
					projScaleMatrix = scaleMatrix ([1,1,1] / uniformBoundSize * 2)
					--	projMatrix = translate projMatrix (-centerPoint * 200)
					--projScaleMatrix = translate projScaleMatrix [centerPoint.x / uniformBoundSize * 2 ,centerPoint.y / uniformBoundSize * 2 ,0]
					--projMatrix = translate projMatrix -centerPoint 
				)
				2:
				(
					--stretch
					projScaleMatrix = scaleMatrix ([1,1,1] / boundSize * 2)
					--weird nudge required to center YZ and ZX mapping, otherwise its half off
					projMatrix = translate projMatrix (-centerPoint)
					--projMatrix = translate projMatrix [0,0,-boundSize.z * 0.5] 
				)
			)
		

			--scale the projection projMatrix by the 1 / boundsize so we always fill the 0-1 space
			if prePlanarFittingStyle != 3 do projMatrix *= projScaleMatrix
			projMatrix *= scaleMatrix ([1,1,1] - preMapPadding)
			--rotate the projMatrix to desired axis
			projMatrix *= matrixFromNormal axisNormal		
		
			meshop.applyUVWMap mesh #planar tm:projMatrix
		)

		-------------------------------
		-- material id tiles
		-------------------------------
		--enable general support for mapping otherwise we get an error
		meshop.setMapSupport mesh 1 true

		local totalTiles = tileX * tileY
		local tileScale = [1 / tileX as float , 1 / tileY as float,1]
		--local matIDTiles = #{1..totalTiles} as array
		--create an array counting 1 to totalTiles to store the tiles by Material ID 
		local matIDTiles = #()
		matIDTiles.count = totalTiles
		for i = 1 to totalTiles do matIDTiles[i] = i
		--array to store the faces in per tile
		local matIDTileFaces = #()

		for face in selectedFaces do
		(	
			--get the faces material ID and loop them back when we reach total tiles limit
			--modulo by totalTiles so we start from the beginning if we use more material ids than we have on our tiles. +1 bcs we start with tile 0
			local faceMatID = (getFaceMatID mesh face)
			faceMatID = mod faceMatID (totalTiles + 1)
			if faceMatID == 0 do faceMatID += 1
		
			--if no face was added yet create a new subarray
			if matIDTileFaces[faceMatID] == undefined do matIDTileFaces[faceMatID] = #{}
			--add the corresponding face to the group
			matIDTileFaces[faceMatID] = append matIDTileFaces[faceMatID] face
		)
		
		--init row n column
		local rowCount = 0
		local colCount = 0
		local resize =  postResize / 100
		--store open edges for later
		local openEdges = meshop.getOpenEdges mesh

		--for every tile
		for matID = 1 to matIDTiles.count do
		(
			--omit if there are no face in the tile slot
			if matIDTileFaces[matID] != undefined do 
			(	
				--detach face temporarily so we have uv cut
				meshop.detachFaces mesh matIDTileFaces[matID] delete:true  asMesh:false
				local mapFaceVerts = meshop.getMapVertsUsingMapFace mesh 1 matIDTileFaces[matID]
				--repeat the collums till we reach the width of the tilegrid
				colCount = mod (matID - 1) tileX
				--by casting to the int we can make sure that floats (0.2, 0.4 etc) are not considered so mod by mat div by tileX will net the nth row
				rowCount = (mod ((matID - 1) / tileX) tileY) as integer
			
				for vert in mapFaceVerts do
				(
					--get position on uv space
					vertPos = meshop.getMapVert mesh 1 vert
					--resize tile
					local newVertPos = (vertPos * [resize, resize, 1])-- + [shift, shift, 0])-- + [colCount ,-rowCount,0])
					--shift tile after it has been resized to recenter it
					local shift = (1 - resize) * 0.5
					newVertPos += [shift, shift, 0]
					--shift each tile and row into its place
					newVertPos = newVertPos + [colCount ,-rowCount,0]
					--resize to 0 - 1
					if UVfitMode == 1 do newVertPos = (newVertPos + [0,tileY - 1,0]) * tileScale
					meshop.setMapVert mesh 1 vert newVertPos
				)
			)
		)
		local openEdgeVerts = meshop.getVertsUsingEdge mesh openEdges
		meshop.weldVertsByThreshold mesh -openEdgeVerts 0.001
		--mesh.selectedVerts = -openEdgeVerts
		--mesh.selectedEdges = openEdges 
	)	

		
)
