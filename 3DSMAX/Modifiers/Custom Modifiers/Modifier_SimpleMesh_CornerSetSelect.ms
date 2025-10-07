/*
Select Corner Verts based on their topology
by Stephan Viranyi https://www.artstation.com/stephko
Feel free to share and extend to your wishes and msg me for any questions or feedback at stephko@viranyi.de
*/

plugin simpleMeshMod CornerSetSelect
	name:"Corner Set / Select"
	version:100
	classID:#(0x3634fddb, 0x6ba5181e)
(

	--Revision Log
	--
	--

	--About Block, versioning
	local versionNr = 1.00
	local versionYear = 2023
	local aboutMain = "Define Corners from Topology"
	local aboutVersion = ("Version " + (versionNr as string) + " | " + (versionYear as string))
	local aboutDocuLink = "https://docs.google.com/document/d/1fIKEurSNeaazzYsPnCTYT7bVO4R4btWzTzvLRpjNutY/edit?usp=sharing"
	local aboutShopLink = "https://www.artstation.com/stephko"

	--vars
	local getPolysUsingFace = meshop.getPolysUsingFace
	local getFacesUsingVert = meshop.getFacesUsingVert
	local getVertsUsingFace = meshop.getVertsUsingFace

	--stored Arrays
	local cornerVerts = #{} -- final corner verts list
	
	local facesFromVerts = #{} -- temp faces from verts, reuse array for each vert
	local meshVertSelection = #{} -- temp verts from face groups, reuse array for each vert
	local numberOfFaces = 0 -- temp int for number of faces for convience, reuse var for each vert
	
	local selectedFaces = #{} -- selected Faces thru stack
	local borderSelectedFaces = #{} -- selected Faces thru stack
	--split groups Mat ID
	local splitGroups = #()
	local splitGroupFaces = #()
	--split groups SG ID
	local splitGroupsSG = #()
	local splitGroupFacesSG = #()

	local owner
	local updateHandler

	parameters main rollout:params category:1
	(
		selMode ui:rbb_selMode default:1 type:#integer animatable:true

		outerCorner ui:chk_outerCorner default:true type:#boolean
		innerCorner ui:chk_innerCorner default:true type:#boolean
		intersections ui:chk_intersection default:true type:#boolean
		ignoreNgon ui:chk_ignoreNgon default:true type:#boolean

		borderByOpen ui:chk_BorderByOpen default:true type:#boolean
		borderByMatID ui:chk_BorderByMatID default:false type:#boolean
		borderBySG ui:chk_BorderBySG default:false type:#boolean
		borderBySelection ui:chk_BorderBySelection default:false type:#boolean
	) 

	parameters setCorners rollout:paramsSet category:2
	(
		selectCorners ui:chk_selectCorners default:true type:#boolean
		
		cornerToColor ui:chk_CornerToColor default:false type:#boolean
		cornerColor ui:cpk_CornerColor type:#color animatable:true
		
		cornerToWeight ui:chk_CornerToWeight default:false type:#boolean
		cornerWeight ui:spn_CornerWeight default:1.01 type:#float animatable:true	
	) 

	parameters debugMain rollout:debugParams
	(
		debugMsgs ui:chk_Msgs default:false type:#boolean animatable:true
		faceMode ui:rbb_faceMode default:1 type:#integer animatable:true
	) 

	rollout params "Parameters"  category:1
	(

		group "Operate on"
		(
			radiobuttons rbb_selMode labels:#("Total Faces", "Selected Faces Only") align:#left
		)

		group "Corner Settings"
		(
			checkbox chk_outerCorner "Outer Open Corners" checked:true align:#left tooltip:"Enable Outer Corners"
			checkbox chk_innerCorner "Inner Open Corners" checked:true align:#left tooltip:"Enable Inner Corners"
			checkbox chk_intersection "Intersections" checked:true align:#left tooltip:"Enable Intersection Corners"
			checkbox chk_ignoreNgon "Ignore 5-Sided" checked:true align:#left tooltip:"Ignore 5-sided nGons. Useful for custom ngon corners without Smoothing Groups before chamfering"
		)

		group "Border Corners by"
		(
			checkbox chk_BorderByOpen "Open Border" checked:true align:#left tooltip:"Form Corners from Open Edges"
			checkbox chk_BorderByMatID "Material ID Intersect" checked:false align:#left tooltip:"Form Corners from Material ID intersections"
			checkbox chk_BorderBySG "SG Intersect" checked:false align:#left tooltip:"Form Corners from Smoothing Groups intersections"
			checkbox chk_BorderBySelection "Face Selection" checked:false align:#left tooltip:"Form Corners from Selection intersections"
		)

		

	)

	rollout paramsSet "Set / Select Corners" category:2
	(
		checkbox chk_selectCorners "Select Corners" checked:false tooltip:"Select Corners in Stack"

		group "Corner to Vertex Color"
		(
			checkbox chk_CornerToColor "Enabled" checked:false tooltip:"Set the Corners to desired Vertex Color"
			colorpicker cpk_CornerColor "To Color" color:[0,0,0] modal:false
		)
		
		group "Corner To Vertex Weight"
		(
			checkbox chk_CornerToWeight "Enabled" checked:false tooltip:"Set the Corners to desired Vertex Weight"
			spinner spn_CornerWeight "To Weight" type:#float range:[0,1e6,1.01]
		)
	) 

	rollout paramsAbout "About" category:9 rolledUp:true
	(

		label lab_aboutMain aboutMain align:#left
		label lab_aboutVersion aboutVersion align:#left
		label lab_aboutSV "by Stephan Viranyi" align:#left
		hyperLink hyp_aboutDocuLink "Help | Documentation" color:blue address:aboutDocuLink
		hyperLink hyp_aboutShopLink "Visit my Artstation" color:blue address:aboutShopLink

	)
	
	rollout debugParams "Debug" category:10 rolledUp:true
	(
		checkbox chk_Msgs "Massages" checked:false tooltip:"Debug Corner Info"

		group "Get Corners from"
		(
			radiobuttons rbb_faceMode labels:#("Quads", "Triangles") align:#left
		)
	)

	-- tried topology change intercept but no luck
	/*
	on update do 
	(
		this.updateHandler = when topology owningNode changes do print ("hello " + (owningNode as string))
	)
	*/
	

	on modifyMesh do
	(	
		
		--get selected faces	
		selectedFaces = mesh.faces as bitarray
		borderSelectedFaces = getFaceSelection mesh as bitarray
		
		if selMode == 2 and borderBySelection do selectedFaces = borderSelectedFaces
		
		-- Grouping Mechanism START -------------------
		-- TODO: Intercept mesh change and only then update the groups
		-----------------------------------------------
		--clear the corner verts array since we start adding corners, pass by pass
		--final cornerverts
		cornerVerts = #{}
		
		--clear group arrays
		--split groups Mat ID
		splitGroups = #()
		splitGroupFaces = #()
		--split groups SG ID
		splitGroupsSG = #()
		splitGroupFacesSG = #()

		if intersections and (borderByMatID or borderBySG) then
		(
			-- Material ID pass

			if borderByMatID do for face in selectedFaces do
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
				-- ??? does this make sense, shouldnt be the var before = be gone?
				splitGroupFaces[idItem] = append splitGroupFaces[idItem] face
			)
			
			-- SG ID pass
			if borderBySG do
			(
				for face in selectedFaces do
				(	
					--get the faces material ID
					local faceSG = getFaceSmoothGroup mesh face
					--setup a list of splitGroups based on material IDs
					appendIfUnique splitGroupsSG faceSG
					
					--find to which entry the Material ID int belongs to
					local idItem = findItem splitGroupsSG (faceSG)
					--if no face was added yet create a new subarray
					if splitGroupFacesSG[idItem] == undefined do splitGroupFacesSG[idItem] = #{}
					--add the corresponding face to the group
					-- ??? does this make sense, shouldnt be the var before = be gone?
					splitGroupFacesSG[idItem] = append splitGroupFacesSG[idItem] face
				)

				join splitGroups splitGroupsSG
				join splitGroupFaces splitGroupFacesSG
			)
		)
		else 
		(
			--just assign one group and our selcted faces to it
			splitGroups = #(1)
			splitGroupFaces[1] = selectedFaces
		)
		-- if we want to border by face selection we just add it as one extra group
		if intersections and borderBySelection do
		(
			append splitGroups (splitGroups.count + 1)
			splitGroupFaces[splitGroups.count + 1] = append splitGroupFaces borderSelectedFaces
		)

		-- Grouping Mechanism END -------------------
		-- TODO: Intercept mesh change and only then update the groups
		-----------------------------------------------

		--for every split group
		for i = 1 to splitGroups.count do
		(
			--convert the face selection to vertex selection
			meshVertSelection = getVertsUsingFace mesh splitGroupFaces[i]
			-- for each vert of this selection
			for vert in meshVertSelection do 
			(
				--get surrouding triangles
				--facesFromVerts = #{}
				facesFromVerts = getFacesUsingVert mesh vert
				--convert to poly
				if faceMode == 1 do facesFromVerts = getPolysUsingFace mesh facesFromVerts ignoreVisEdges:false 
				--mask the faces
				facesFromVerts *= splitGroupFaces[i]
				-- remainig faces
				numberOfFaces = facesFromVerts.numberset
		
				if faceMode == 1 do 
				(
					-- poly/quad mode
					if outerCorner and numberOfFaces < 3 do cornerVerts += #{vert}
					if innerCorner and (numberOfFaces == 6 or (numberOfFaces == 5) and not ignoreNgon) do cornerVerts += #{vert}
				)
				if faceMode == 2 do 
				(
					-- triangle mode
					if outerCorner and numberOfFaces < 3 do cornerVerts += #{vert}
					--if innerCorner and numberOfFaces == 5 do cornerVerts += #{vert}
					if innerCorner and (numberOfFaces == 5 or (numberOfFaces == 4) and not ignoreNgon) do cornerVerts += #{vert}
				)

				if debugMsgs do 
				(	
					if faceMode == 1 do
					(
						-- counting polies
						print ("Vertex " + (vert as string) + " has " + (numberOfFaces as string) + " polies")
						case numberOfFaces of 
						(
							1:(print ("Vertex " + (vert as string) + " is outer corner with 1 face"))
							2:(print ("Vertex " + (vert as string) + " is outer corner with 2 face"))
							3:(print ("Vertex " + (vert as string) + " is loopsegment with 3 face"))
							4:(print ("Vertex " + (vert as string) + " is loopsegment with 4 face"))
							5:(print ("Vertex " + (vert as string) + " is with 5 face (ngon)"))
							6:(print ("Vertex " + (vert as string) + " is inner with 6 face"))
							7:(print ("Vertex " + (vert as string) + " is inner with 7 face"))
						)

					)
					if faceMode == 2 do
					(
						-- counting triangles
						print ("Vertex " + (vert as string) + " has " + (numberOfFaces as string) + " triangles")
						case numberOfFaces of 
						(
							1:(print ("Vertex " + (vert as string) + " is outer corner"))
							2:(print ("Vertex " + (vert as string) + " is outer corner"))
							3:(print ("Vertex " + (vert as string) + " is loopsegment"))
							4:(print ("Vertex " + (vert as string) + " is loopsegment"))
							5:(print ("Vertex " + (vert as string) + " is inner corner"))
						)
					)
				)
			)
		)

		-- if we only want to operate on selected faces
		if selMode == 2 do 
		(
			cornerVerts *= getVertsUsingFace mesh borderSelectedFaces
		)

		--shave open corners
		if not borderByOpen do cornerVerts -= meshop.getVertsUsingEdge mesh (meshop.getOpenEdges mesh)

		-- all done, set the corners from the list

		--set corner colors
		if cornerToColor do 
		(
			meshop.setVertColor mesh 0 (cornerVerts) cornerColor
		)
		--set corner weights
		if cornerToWeight do 
		(
			meshop.setVDataChannelSupport mesh 2 true
			for vert in cornerVerts do
			(
				meshop.setVDataValue mesh 2 vert cornerWeight
			)
		)
	
		--set the selection
		if selectCorners do 
		(
			mesh.selectedVerts = #{}
			mesh.selectedVerts = cornerVerts
		)
	)
)