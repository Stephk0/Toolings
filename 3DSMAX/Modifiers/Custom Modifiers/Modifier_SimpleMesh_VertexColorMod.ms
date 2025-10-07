/*
Set Vertex Colors with Effects
by Stephan Viranyi https://www.artstation.com/stephko
Feel free to share and extend to your wishes and msg me for any questions or feedback at stephko@viranyi.de

*/

plugin simpleMeshMod VertColorMod
	name:"Vertex Color Mod"
	classID:#(0x56b79364, 0x7b2561e8)
	version:080
(

	------------------------
	-- about variables section (for versioning) STARTS HERE
	------------------------
	local versionYear = 2024
	local aboutMain = "Vertex Color Mod"

	fn composeVersionNrText v =
	(
		return ("Version " + (formattedPrint ((v as float)/100) format:"0.2f") + " | " + ( versionYear as string))
	)

	local aboutDocuLink = "https://docs.google.com/document/d/1fIKEurSNeaazzYsPnCTYT7bVO4R4btWzTzvLRpjNutY/edit?usp=sharing"
	local aboutShopLink = "https://www.artstation.com/stephko"

	------------------------
	-- about variables section (for versioning) ENDS HERE
	------------------------

	local getVertsUsingFace = meshop.getVertsUsingFace
	local getFacesUsingVert = meshop.getFacesUsingVert 
	local getPolysUsingVert = meshop.getPolysUsingVert 
	local getVDataValue = meshop.getVDataValue
	local getMapVert = meshop.getMapVert
	local getMapFace = meshop.getMapFace
	local getFace = meshop.getFace 


	local inputMask = [0,0,0] --mask of rgb components
	local finalColor = white --final color to apply
	local softSelectedVerts = 1.0 --soft selcted value
	local colorSum = 1 --colorsum 

	fn clamp minVal maxVal val =
	(
		if classOf val == point3 then 
		(
			if val.x < minVal then val.x = minVal
			else if val.x > maxVal then val.x = maxVal
			if val.y < minVal then val.y = minVal
			else if val.y > maxVal then val.y = maxVal
			if val.z < minVal then val.z = minVal
			else if val.z > maxVal then val.z = maxVal
		)
		else 
		(
			if val < minVal then val = minVal
			else if val > maxVal then val = maxVal
		)
		return val
	)

	fn lerp minVal maxVal term = (maxVal - minVal) * term + minVal

	fn RGBToLuminance color = 
	(
		local r = color.x
		local g = color.y
		local b = color.z
		local maxRGB = 0
		local minRGB = 0
	 
		if r >= g then maxRGB = r
		if r >= b then maxRGB = r
		if g >= r then maxRGB = g
		if g >= b then maxRGB = g
		if b >= r then maxRGB = b
		if b >= g then maxRGB = b
	 
		if r <= g then minRGB = r
		if r <= b then minRGB = r
		if g <= r then minRGB = g
		if g <= b then minRGB = g
		if b <= r then minRGB = b
		if b <= g then minRGB = b
	 
		lumin = ((maxRGB + minRGB)/2)
	)

	fn saturate val = 
	(
	
		fn saturateF val = 
		(
			local newVal
			if val < 0 then newVal = 0
			else if val > 1 then newVal = 1
			else newVal = val
			return newVal
		)
		
		local isValColor = 0
		
		if classOf val == Color then 
		(
			--the multiplication or division by 255 for casting a color to/from a point3 or point4 is done implicitly
			isValColor = 1
			try 
			(
				a = val.a --if it crashes, we have a 3-component color
				val = val as point4
			)
			catch (val = val as point3)
		)
		
		local newVal = val
		
		try (newVal.x = saturateF val.x)
		catch (newVal = saturateF val)
		
		try (newVal.y = saturateF val.y)
		catch (return newVal)
		
		try (newVal.z = saturateF val.z)
		catch (return newVal)
		
		try (newVal.w = saturateF val.w)
		catch (return newVal)
		if isValColor == 1 then 
		(
			newVal = newVal as color
		)
	
		return newVal
	)

	fn HSV_to_RGB hsv = 
	(
		rgb = black -- it might be any color
		rgb.v = hsv.z
		rgb.s = hsv.y
		rgb.h = hsv.x
		rgb as point3
	)

	fn ringMod val1 addVal limit = 
	(
		val1 = val1 + addVal
		if val1 > limit then val1 -= limit
		else if val1 < 0 do val1 += limit
		return val1
	)
	local facesUsingVertex = #()
	local mapVertexIndex = 1
	local mapFace
	local meshFace

	fn getMapVertexForMeshVertex meshObj meshVertexIndex Vchan = (
		/*
		https://help.autodesk.com/view/3DSMAX/2016/ENU/?guid=__files_GUID_CBBA20AD_F7D5_46BC_9F5E_5EDA109F9CF4_htm
		Take the index of the mesh vertex. 
		Find out which faces reference the index of the face.
		Note the number of the vertex (1 st , 2 nd or 3 rd - .x, .y or .z) inside each face.
		For each face referencing the vertex, get the texture face with the same index.
		Get the index of the respective texture vertex from the face - 1 st , 2 nd or 3 rd / .x, .y or .z
		The vertex you got corresonds to the mesh vertex we started with.
		Repeat steps 3 to 6 for all faces found.
		*/


		--get faces from meshVertexIndex vert
		facesUsingVertex = getFacesUsingVert meshObj #(meshVertexIndex) as BitArray
		--should give is 2-inf faces with always 3 vertices each
		for faceIndex in facesUsingVertex do 
		(
			--get the map face
			mapFace = getMapFace meshObj Vchan faceIndex
			--get the actual face
			meshFace = getFace meshObj faceIndex
			--check all 3 resulting verts per face of which one shares the one from meshvertexindex
			for vertexIndexInFace = 1 to 3 do
			(
				if meshFace[vertexIndexInFace] == meshVertexIndex do mapVertexIndex = mapFace[vertexIndexInFace] -- Get the texture vertex index
			)
		)
		mapVertexIndex
	)

	parameters mainParams rollout:params
	(
		vertMode ui:rbb_vertMode default:1 type:#integer animatable:true
		writeToChannel ui:ddl_writeToChannel default:1 type:#integer animatable:true	
		Vchan ui:spn_Vchan default:0 type:#integer animatable:false
		setDefaultVCFace ui:chk_defaultVCFace default:true type:#boolean animatable:true
		delIsovert ui:chk_delIsovert default:true type:#boolean animatable:true
		buildFaces ui:chk_buildFaces default:true type:#boolean animatable:true
		forceSupport ui:chk_forceSupport default:true type:#boolean animatable:true
	) 

	parameters effectsParams rollout:paramsEffect
	(

		effectSelection ui:ddl_EffectSelection default:1 type:#integer animatable:true
		invertEffect ui:chk_InvertEffect default:false type:#boolean animatable:true

		--main params
		mainCol ui:cpk_mainCol default:white type:#color animatable:true
		secondCol ui:cpk_secondCol default:black type:#color animatable:true
		secondColTrans ui:chk_secondColTrans default:false type:#boolean animatable:true

		--gradient / positon
		normalizePosBounds ui:chk_normalizePosBounds default:true type:#boolean animatable:true
		boundsFromSelection ui:chk_boundsFromSelection default:false type:#boolean animatable:true
		positionScale ui:spn_positionScale default:100 type:#float animatable:true
		clampPos ui:chk_ClampPos default:true type:#boolean animatable:true

		--distance to point
		distPosX ui:spn_DistPosX default:0 type:#float animatable:true
		distPosY ui:spn_DistPosY default:0 type:#float animatable:true
		distPosZ ui:spn_DistPosZ default:0 type:#float animatable:true
		distRadius ui:spn_DistRadius default:1 type:#float animatable:true

		RChannel ui:chk_RChannel default:true type:#boolean animatable:true
		GChannel ui:chk_GChannel default:true type:#boolean animatable:true
		BChannel ui:chk_BChannel default:true type:#boolean animatable:true
		
		monochrome ui:chk_monochrome default:false type:#boolean animatable:true
		parabolic ui:chk_parabolic default:false type:#boolean animatable:true
		

		extraMultiply ui:spn_ExtraMultiply default:1 type:#float animatable:true
		extraPower ui:spn_ExtraPower default:1 type:#float animatable:true
		gammaBoost ui:spn_GammaBoost default:1 type:#float animatable:true
		preOffset ui:spn_PreOffset default:0 type:#float animatable:true
		
	) 

	parameters blendParams rollout:paramsBlend
	(
		blendMode ui:rbb_BlendMode default:1 type:#integer animatable:true	
		opacityValue ui:sld_opacityValue default:100 type:#integer animatable:true
	) 

	parameters HSLAParams rollout:paramsHSL
	(
		
		hueValue ui:sld_HueValue default:0 type:#integer animatable:true
		satValue ui:sld_SatValue default:0 type:#integer animatable:true
		lumValue ui:sld_LumValue default:0 type:#integer animatable:true
		
	) 
	
	parameters debugParams rollout:paramsDebug
	(
		debugNormal ui:chk_debugNormal default:false type:#boolean animatable:true
		debugTime ui:chk_debugTime default:false type:#boolean animatable:true
	) 

	
	rollout params "Parameters" category:1
	(
		group "Operate on:"
		(
			radiobuttons rbb_VertMode labels:#("Total Vertices", "Selected Vertices")
		)
		dropdownlist ddl_writeToChannel "Vertex Channel" items:#("Vertex Color", "Vertex Illumination", "Vertex Alpha","Custom Vertex Mapping")
		spinner spn_Vchan "Vertex Channel" type:#integer range:[-2,1e6,0] align:#left enabled:(ddl_writeToChannel == 4)
		
		group "Advanced Settings"
		(
			checkbox chk_defaultVCFace "Default VC Faces" checked:true
			checkbox chk_delIsovert "Delete Iso Verts" checked:true
			checkbox chk_buildFaces "buildFaces" checked:true
			checkbox chk_forceSupport "forceSupport" checked:true
		)

		on ddl_writeToChannel selected state do 
		(
			spn_Vchan.enabled =  state == 4
		)
	) 

	rollout paramsEffect "Effect" category:2
	(

		dropdownlist ddl_EffectSelection "Effect" items:#("Fill", "Vertex Normal", "Position", "Distance", "Gradient Remapping", "Curvature", "HSL Adjustment", "Perlin TBD", "Randomize TBD", "Element Id TBD")
		colorpicker cpk_mainCol "Main Color" color:white modal:false align:#left --enabled:inVColor
		colorpicker cpk_secondCol "Second Color" color:black modal:false align:#left --enabled:inVColor
		checkbox chk_secondColTrans "Second Color Transparent" checked:false
		checkbox chk_InvertEffect "Invert Effect" checked:false
		
		group "Main Settings"
		(
			label lab_posExclusive "Position Setting" align:#left
			checkbox chk_normalizePosBounds "Normalize by Bounds" checked:true
			checkbox chk_boundsFromSelection "Bounds From Selection" checked:false
			spinner spn_positionScale "positionScale" type:#worldunits range:[-1e6,1e6,100]
			label lab_posNormalExclusive "Position / Normal Setting" align:#left
			checkbox chk_ClampPos "Clamp Position" checked:true
			checkbox chk_RChannel "X Channel" checked:true
			checkbox chk_GChannel "Y Channel" checked:true
			checkbox chk_BChannel "Z Channel" checked:true	
			label lab_distExclusive "Distance Setting" align:#left
			spinner spn_DistRadius "Distance Radius" type:#worldunits range:[0,1e6,100]
			spinner spn_DistPosX "X Distance Pos" type:#worldunits range:[-1e6,1e6,0]
			spinner spn_DistPosY "Y Distance Pos" type:#worldunits range:[-1e6,1e6,0]
			spinner spn_DistPosZ "Z Distance Pos" type:#worldunits range:[-1e6,1e6,0]
			
			
		)

		group "Output"
		(
			checkbox chk_monochrome "Monochrome" checked:false
			--checkbox chk_normalize "Normalize" checked:false		
		)

		group "Adjust Effect"
		(
			spinner spn_PreOffset "Pre Offset" type:#float range:[-1e6,1e6,0]
			spinner spn_ExtraMultiply "Multiply" type:#float range:[0,1e6,1]
			spinner spn_ExtraPower "Power" type:#float range:[0,1e6,1]
			spinner spn_GammaBoost "Gamma Boost" type:#float range:[0,1e6,1]
			checkbox chk_parabolic "Parabolic" checked:true		
		)

		
	) 
	

	rollout paramsBlend "Blend Style" category:3
	(
		group "Blending"
		(
			radiobuttons rbb_BlendMode labels:#("Replace", "Multiply", "Screen", "Overlay")
			slider sld_opacityValue "Opacity" orient:#horizontal ticks:10 range:[0,100,100]
			spinner spn_opacityValue "Opacity" type:#integer range:[0,100,opacityValue] 
		)

		on sld_opacityValue changed val do spn_opacityValue.value = val
		on spn_opacityValue changed val do sld_opacityValue.value = val

	)

	rollout paramsHSL "HSL Adjustment" category:9
	(
			slider sld_HueValue "Hue" orient:#horizontal ticks:10 range:[-255,255,0] 
			spinner spn_HueValue "Hue" type:#integer range:[-255,255,hueValue]
			slider sld_SatValue "Saturation" orient:#horizontal ticks:10 range:[-255,255,0] 
			spinner spn_SatValue"Saturation" type:#integer range:[-255,255,satValue] 
			slider sld_LumValue "Lightness" orient:#horizontal ticks:10 range:[-255,255,0] 
			spinner spn_LumValue "Lightness" type:#integer range:[-255,255,lumValue] 

			on sld_HueValue rightClick do 
			(
				sld_HueValue.value = 0
				spn_HueValue.value = 0
			)

			on sld_HueValue changed val do spn_HueValue.value = val
			on spn_HueValue changed val do sld_HueValue.value = val

			on sld_SatValue rightClick do 
			(
				sld_SatValue.value = 0
				spn_SatValue.value = 0
			)

			on sld_SatValue changed val do spn_SatValue.value = val
			on spn_SatValue changed val do sld_SatValue.value = val

			on sld_LumValue rightClick do 
			(
				sld_LumValue.value = 0
				spn_LumValue.value = 0
			)

			on sld_LumValue changed val do spn_LumValue.value = val
			on spn_LumValue changed val do sld_LumValue.value = val
	)
	
		rollout paramsDebug "Debug" category:100
	(
		group "Debug"
		(
			checkbox chk_debugNormal "Normal" checked:false
			checkbox chk_debugTime "Time taken" checked:false
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


	local allVerts 
	local selectedVertices
	local faceSel

	on modifyMesh do
	(
		if debugTime do local ts = timestamp()

		-- divide opacity by 100 so we deal with 0 - 1 
		local opacityVal = (opacityValue as float / 100)
		--get if Soft sel is as we have to account for more selected faces
		local softSelOn = meshop.getVDataChannelSupport mesh 1
		--enable support for soft selection
		meshop.setVDataChannelSupport mesh 1 true
		
		--get the selection from stack
		allVerts =  mesh.vertices as bitarray
		selectedVertices = allVerts
		
		--if we only want the selection straight
		if vertMode == 2 then selectedVertices = getVertSelection mesh as bitarray
		--since soft selected verts dont count as selected we have to find them by their data value and add them to the selected array
		if vertMode == 2 and softSelOn then selectedVertices += (for vert = 1 to mesh.numverts where (meshop.getVDataValue mesh 1 vert) > 0 collect vert) as bitarray

		--support for face selection if present, convert face to vert
		faceSel = getFaceSelection mesh as bitarray
		if not faceSel.isEmpty do selectedVertices += getVertsUsingFace mesh faceSel

		--overwrite VChan depending what we choose
		case writeToChannel of 
		(
			1: Vchan = 0
			2: Vchan = -1
			3: Vchan = -2
		)

		if Vchan > 1 do meshop.setNumMaps mesh Vchan keep:true
		
		--some map support stuff not sure whats going here, works better but not all the time.
		--this should always be on otherwise we are hit with an error stopping the mod
		if forceSupport do meshop.setMapSupport mesh Vchan true			
		
		
		if buildFaces do meshop.buildMapFaces mesh Vchan keep:true
		if delIsovert do meshop.deleteIsoMapVertsAll mesh -- test this
		
		if setDefaultVCFace do defaultVCFaces mesh


		--only calc bounds if needed
		-- TODO: implement bounds fix from GridSlicer Modifier so the gradient can be set along the bounds of the selction or if the mesh if offcenter
		if effectSelection == 3 do 
		(
			--get bounds
			local centerPoint = [0,0,0]
			minX = 0
			minY = 0
			minZ = 0
			maxX = 0
			maxY = 0
			maxZ = 0
			
			--determine bound size, if whole model or only selection
			local boundVerts = allVerts
			if boundsFromSelection do boundVerts = selectedVertices
			for i in boundVerts do
			(
				vert = getVert mesh i
				centerPoint += vert
				if vert.x < minX then minX = vert.x
				if vert.y < minY then minY = vert.y
				if vert.z < minZ then minZ = vert.z
				if vert.x > maxX then maxX = vert.x
				if vert.y > maxY then maxY = vert.y
				if vert.z > maxZ then maxZ = vert.z
			)

			centerPoint = centerPoint / mesh.vertices.count

			local minBounds = point3 minX minY minZ
			local maxBounds = point3 maxX maxY maxZ
			local bounds = maxBounds - minBounds
		)

		
		
		-----------------------
		-- init color and soft selection
		-- these are per vert caches as to not create a variable for each vert anew
		-----------------------
		local vertFaces
		local neighbourVerts
		local SSOP = 1
		local originalColor = [0,0,0]

		-- TODO: resolve this, as we only need some of the variables depending on effect but should not create the var within the for loop

		if effectSelection == 2 do 
		(
			--init one var to use for each vert normal
			local vertNormal = [0,0,0]
		)
		if effectSelection == 3 do 
		(
			--init one var to use for each vert position
			local vertPositon = [0,0,0]
		)
		if effectSelection == 4 do 
		(
			--init one var to use for each vert position
			local vertPositon = [0,0,0]
			--assamble a local point from the 3 spinners to get a vector from to get the distance to
			local distancePoint = [distPosX, distPosY,distPosZ ]
			
		)
	
		-----------------------
		-- start of effect per vert
		-----------------------	

		for vert in (selectedVertices) do
		(	
			--if the vertex is selected
			if selectedVertices[vert] == true do
			(
				-----------------------
				-- re init color and soft selection for each vert
				-----------------------
				inputMask = [0,0,0]
				finalColor = white
				softSelectedVerts = 1.0
				colorSum = 1 -- simple fill
				if softSelOn and vertMode == 2 do softSelectedVerts = getVDataValue mesh 1 vert
				
				-----------------------
				-- Get original colors
				-----------------------	
				-- 1 to 1 correspondance due to reset on VC faces
				if setDefaultVCFace then originalColor = (getMapVert mesh Vchan vert) 
				--conversion from mesh vert indesx to map vert index
				else originalColor = (getMapVert mesh Vchan (getMapVertexForMeshVertex mesh vert Vchan)) 
				--write to white if not defined
				-- TODO: possibly an option if unwritten data wants to be preseved
				if originalColor == undefined then originalColor = [1,1,1]
				
				
				-----------------------
				-- Effect Types. Does whatever, outputs inputMask and colorSum
				-----------------------
				--if effectSelection == 1 do 
				--(
					-----------------------
					-- Simple Fill
					-- can be fully ommited as we init colorsum as 1 anyway
					-----------------------
					--colorSum = 1
				--)
				if effectSelection == 2 do 
				(
					-----------------------
					-- Vertex Normal
					-----------------------
					--vert normal
					vertNormal = normalize ( getNormal mesh vert )
					--TO 0-1 SPACE
					vertNormal = vertNormal * 0.5 + 0.5 
					if RChannel do inputMask.x = vertNormal.x
					if GChannel do inputMask.y = vertNormal.y
					if BChannel do inputMask.z = vertNormal.z

					-- clamp all channels to 0 - 1 space
					colorSum = clamp 0 1 (inputMask.x + inputMask.y + inputMask.z)
				)
		
				if effectSelection == 3 do 
				(
					-----------------------
					-- Position Gradient
					-----------------------
					--vert position that is our gradient
					-- todo offload this var  outside of for loop
					vertPositon = getVert mesh vert
					--move the vert start to its outer minimum bound as to start from the outest corner and then work out way from there eiher free or normalized
					--TODO: disconnect and add this as option to be world based or local based
					--TODO: add offset for pivot
					if RChannel do inputMask.x = (vertPositon.x - minBounds.x ) / positionScale
					if GChannel do inputMask.y = (vertPositon.y - minBounds.y ) / positionScale
					if BChannel do inputMask.z = (vertPositon.z - minBounds.z ) / positionScale
					--scale the position vertex to be normalized to the object bounds / size, divide by 100 because of world unit conversion
					if normalizePosBounds do inputMask = (inputMask ) / ( bounds / 100 + 0.001)
					--clamp as desired
					--TODO add more control
					if clampPos do inputMask.x = (clamp 0 100 inputMask.x)
					if clampPos do inputMask.y = (clamp 0 100 inputMask.y)
					if clampPos do inputMask.z = (clamp 0 100 inputMask.z)
					-- clamp to 0 - 1 space
					colorSum = clamp 0 1 (inputMask.x + inputMask.y + inputMask.z)
				)

				if effectSelection == 4 do 
				(
					-----------------------
					-- Distance to point
					-----------------------
					
					vertPositon = getVert mesh vert
					colorSum = distance distancePoint (vertPositon)
					colorSum /= distRadius
					colorSum = clamp 0 1 (colorSum)
				)


				if effectSelection == 6 do 
				(
					-----------------------
					-- Curvature
					-- Very WIP and lots to do to make it usable and performant
					-----------------------
					/*
					local vertNormal = getNormal mesh vert
					local faceangle = 0
					local vertFaces = meshop.getFacesUsingVert mesh vert
					for f in vertFaces do
					(
						faceangle += acos(dot vertNormal (getFaceNormal mesh f))
					)
					if (faceangle > (2 * (3.14159 / 180))) then
					(
						colorSum = 1
					)
					*/

					local vertNormal = getNormal mesh vert
					local vertPositon = getVert mesh vert
					--vertNormal = vertNormal * 0.5 + 0.5 
					colorSum = 0
					accumFaceNorm = [0,0,0]
					vertFaces = getPolysUsingVert mesh vert
					--neighbourVerts = getVertsUsingFace mesh vertFaces
					--neighbourVerts = #{}
					--vertFaces = getFacesUsingVert mesh neighbourVerts
					--neighbourVerts = getVertsUsingFace mesh vertFaces
					vertangle = 0
					for f in vertFaces do
					(
						local faceNormal = getFaceNormal mesh f
						local facePos = getFace mesh f
						local sign = 1
						local crossprod = cross vertNormal (facePos - vertPositon)
						local elevation = (faceNormal - vertNormal) 
						if (elevation.z) < 0 do sign = -1

						if debugNormal do
						(
							--print ((dot vertNormal faceNormal) as string + " dot of vert normal nr " + (vert as string) + " and facenormal " + (f as string)) 
							--print ((dot vertPositon faceNormal) as string + " dot of vert pos nr " + (vert as string) + " and facenormal " + (f as string)) 
							print (elevation)
							if sign == 1 do print ((vert as string) + " is convex ")
							if sign == -1 do print ((vert as string) + " is concave ")
						) 
						--if sign == 1 do colorSum = colorSum + 1 
							colorSum = colorSum + (dot vertNormal faceNormal) * .125 * sign
					)

					/*
					for f in vertFaces do
					(
						--one way
						faceNormal = getFaceNormal mesh f

						dirToFace = (meshop.getFace mesh f) - (getVert mesh vert)
						curDot = dot (normalize dirToFace) vertNormal
						--philtest = philtest + curDot
						
						if debugNormal do print vertangle
						vertangle += ((dot ((vertNormal) ) (faceNormal) ) / vertFaces.numberset)
						--vertangle = vertangle * curDot
						--vertangle += (dot (normalize (vertNormal) ) ( (getVert mesh vert) - (getFace mesh f) ) )
						
						--vertangle = clamp -1 1 (vertangle * 0.5 + 0.5 )
						--if vertangle >= .8 then vertangle = vertangle + 1 
						--else vertangle = vertangle - 1
						--colorSum = colorSum + vertangle / vertFaces.numberset
						
						--anglesvert += dot vertNormal faceNormal
						--2 way curvature
						--colorSum += ((dot (clamp -1 1 vertNormal) (clamp -1 1  (getFaceNormal mesh f)))) / vertFaces.numberset
					)
					--vertangle = vertangle / vertFaces.numberset
					--if vertangle < 2 then colorSum = 1
					--else colorSum = 0
					colorSum = colorSum + vertangle
					
					for v in neighbourVerts do 
					(
						neighbourNorm = getNormal mesh v
						vertangle += (dot (vertNormal ) (neighbourNorm) )
						--colorSum += (dot (vertNormal ) (neighbourNorm) ) / neighbourVerts.numberset
						--vertangle = clamp -1 1 (vertangle * 0.5 + 0.5 )
						--if vertangle >= 0.258 then vertangle = vertangle + 1
						--else vertangle = vertangle - 1
						---colorSum = colorSum + vertangle / neighbourVerts.numberset
						
						--pseudo ao?
						--dirToVert = (getVert mesh v) - (getVert mesh vert)
						--vertangle += dot dirToVert vertNormal
						
						
						--philtest = philtest + curDot
						--colorSum = dot vertNormal neighbourNorm
						--if vertangle < 0.9 then colorSum += 1 
					)
					
					--colorSum = colorSum + vertangle / neighbourVerts.numberset
					*/
					colorSum = clamp 0 1 colorSum
					--colorSum = 1 - colorSum
				)


				
				
				-----------------------
				-- Post Effects before converting to color
				-----------------------
				colorSum += preOffset
				--clamp first time after offset
				colorSum = (clamp 0 1 colorSum)
				--parabolic effect
				if parabolic do colorSum =  1 - abs ((colorSum - 0.5) * 2)
				--add extra multiply
				colorSum *= extraMultiply
				-- power to make the gradient distance more narrow
				colorSum = pow colorSum extraPower
				-- add more gamma if need be
				colorSum += gammaBoost - 1
				--gradient remap of original colors, possibly not correct might need to look for luminance instead of adding all three channels together
				if effectSelection == 5 do colorSum = (originalColor.x + originalColor.y + originalColor.z) / 3
				-- invert effect
				if invertEffect do colorSum = 1 - colorSum
				--clamp me baby one more time
				colorSum = (clamp 0 1 colorSum)

				-----------------------
				-- Blur post effect
				-- blur / avarage the vert colors of Original color and color sum per user choice
				-----------------------

				/*

				take surrounding faces
				from surrounding face take verts
				add the color values together and divide by number of surrounding vertices
				store this into an array

				*/


				-----------------------
				-- Begin color space
				-- convert 0 - 1 to color space 0 - 255
				-----------------------

				--RGB input mask as color, for debug modes
				--inputMask = inputMask as color -- not used anymore
				
				--assamble opcacity from user input and soft selection
				--TODO: add custom masks
				SSOP = opacityVal * softSelectedVerts
				
				--multiply original color to convert from 0-1 to 0-255 based
				originalColor *= 255
				--color lerp based on color sum of the input effect
				--TODO: possibly allow custom alpha value for main and second color for finetuning
				if secondColTrans then
				(
					case blendMode of
					(
						1: finalColor = (lerp (originalColor) (mainCol as point3) colorSum)
						2: finalColor = (lerp white (mainCol as point3) colorSum)
						3: finalColor = (lerp black (mainCol as point3) colorSum)
						4: finalColor = (lerp (white/2) (mainCol as point3) colorSum)
					)
				) 
				else finalColor = (lerp (secondCol as point3) (mainCol as point3) colorSum)
				-- convert to monochrome if desired
				if monochrome do finalColor = [colorSum, colorSum, colorSum] * 255

				-----------------------
				-- Blend 
				-- convert 0 - 1 to color space 0 - 255
				-----------------------

				case blendMode of
				(
					1: if SSOP < 1.0 do finalColor = (lerp originalColor finalColor SSOP)
					2: finalColor = originalColor * (lerp (white/255) (finalColor / 255) SSOP)
					3: finalColor = originalColor + (finalColor) * SSOP
					4: finalColor = originalColor * (lerp (white/255/2) (finalColor / 255) SSOP) * 2
				)
				
				--clamp final composite
				finalColor =  [clamp 0 255 finalColor.x, clamp 0 255 finalColor.y, clamp 0 255 finalColor.z]

				--convert color to hsv to alter the hue/sat/lum and then convert back to rgb
				hsvColor = [ringMod (finalColor as color).h hueValue 255, clamp 0 255 ((finalColor as color).s + satValue) , clamp 0 255 ((finalColor as color).v + lumValue) ]
				finalColor = HSV_to_RGB hsvColor
				

				--set the final color
				-- TODO: add special Alpha case
				meshop.setVertColor mesh Vchan #{vert} finalColor
				--meshop.setVertAlpha mesh Vchan #{vert} finalColor / 255
			
			)	
		) -- end for vert loop

		--TODO add option to retain selection or clear
		mesh.selectedVerts = #{}
		mesh.selectedVerts = selectedVertices
		mesh.selectedFaces = faceSel
		
		if debugTime do print ("Operation took " + (timeStamp() - ts) as string + " ms")
/*
		-- according to openchat the way to select verts with faces degress apart
		for i in range myObject.numVerts do
		(
			vert = myObject.getVert i
			normal = vert.getNormal()
			angle = 0
			for j in range vert.numFaces do
			(
				face = vert.faces[j]
				angle += acos(dot normal face.getNormal())
			)
			if (angle > (45 * (3.14159 / 180))) then
			(
				myObject.setSelectedVert i true
			)
		)
*/		
		
	)
)