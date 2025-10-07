/*
Slice Grid
by Stephan Viranyi https://www.artstation.com/stephko
Feel free to share and extend to your wishes and msg me for any questions or feedback at stephko@viranyi.de
*/

plugin simpleMeshMod SliceGrid
	name:"Slice Grid"
	classID:#(0xdf3cb59, 0x122ec495)
	version:100
(

	--About Block, versioning
	local versionYear = 2023
	local aboutMain = "Slice Grid"

	fn composeVersionNrText v =
	(
		return ("Version " + (formattedPrint ((v/100) as float) format:"0.2f") + " | " + ( versionYear as string))
	)

	local aboutDocuLink = "https://docs.google.com/document/d/1fIKEurSNeaazzYsPnCTYT7bVO4R4btWzTzvLRpjNutY/edit?usp=sharing"
	local aboutShopLink = "https://www.artstation.com/stephko"


	-----------------------
	--
	-----------------------


	local sliceOp = meshop.Slice

	parameters main rollout:params
	(
		faceMode ui:rbb_faceMode default:1 type:#integer animatable:true	
		
		gridMode ui:rbb_gridMode default:1 type:#integer animatable:true
		
		gridX ui:spn_gridXDiv default:1 type:#integer animatable:true
		gridY ui:spn_gridYDiv default:1 type:#integer animatable:true
		gridZ ui:spn_gridZDiv default:1 type:#integer animatable:true

		gridOffsetX ui:spn_gridOffsetX default:1 type:#float animatable:true
		gridOffsetY ui:spn_gridOffsetY default:1 type:#float animatable:true
		gridOffsetZ ui:spn_gridOffsetZ default:1 type:#float animatable:true
		
		/*
		splitPreDistance ui:spn_splitPreDistance default:0 type:#float animatable:true
		splitDistance ui:spn_splitDistance default:0 type:#float animatable:true
		splitOffset ui:spn_splitOffset default:0 type:#float animatable:true
		--splitSel ui:chk_splitSel default:true type:#boolean animatable:true	
		createDuplicate ui:chk_duplicate default:false type:#boolean animatable:true
		flipOrig ui:chk_flipOrig default:false type:#boolean animatable:true
		flipNew ui:chk_flipNew default:false type:#boolean animatable:true
		*/
	)
	
	rollout params "Parameters"  category:1
	(
		group "Operate on"
		(
			radiobuttons rbb_faceMode labels:#("Total Faces", "Selected Faces")
		)
		group "Grid Divisions"
		(
			spinner spn_gridXDiv "Grid X Division" type:#integer range:[-1e6,1e6,1] align:#left
			--checkbox chk_gridXDivCenter "From Center" checked:false tooltip:"Divide from center"
			spinner spn_gridYDiv "Grid Y Division" type:#integer range:[-1e6,1e6,1] align:#left
			spinner spn_gridZDiv "Grid Z Division" type:#integer range:[-1e6,1e6,1] align:#left
			checkbox chk_XYZDivUniform "Uniform" checked:false tooltip:"Divide all axes equally"
		)
		group "Grid Settings"
		(
			
			radiobuttons rbb_gridMode labels:#("Local Grid","World Grid", "Custom Grid")
			spinner spn_gridOffsetX "X" type:#float range:[-1e6,1e6,0] align:#left width:45 across:3
			spinner spn_gridOffsetY "Y" type:#float range:[-1e6,1e6,0] align:#left width:45
			spinner spn_gridOffsetZ "Z" type:#float range:[-1e6,1e6,0] align:#left width:45
			
		)
		group "Slice Settings"
		(
			radiobuttons rbb_sliceSetting labels:#("Refine Mesh","Slice to Elements")
		)
		
		checkbox chk_duplicate "Create Duplicate" checked:false tooltip:"Create a duplicate of the Selection"
		checkbox chk_flipOrig "Flip Original" checked:false tooltip:"Split the Selection"
		checkbox chk_flipNew "Flip SplitMesh" checked:false tooltip:"Split the Selection" 
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

	fn GetCenterPoint verts =
	(
		-- setup
		local centerPoint = [0,0,0]
	
		-- determine bound size, if whole model or only selection
		for vert in verts do
		(
			centerPoint += getVert mesh vert
		)
	
		centerPoint = centerPoint / verts.count
	
		return centerPoint
	)
	
	fn CalculateBounds verts =
	(
		--get bounds

		-- setup
		local centerPoint = GetCenterPoint (verts as bitarray)
		--local centerPoint = [0,0,0]
		local minVerts = GetCenterPoint (verts as bitarray)
		local maxVerts = GetCenterPoint (verts as bitarray)

		
		local vertPos
		
		--determine bound size, if whole model or only selection
		for vert in verts do
		(
			vertPos = getVert mesh vert
			print vertPos
			
			if vertPos.x < minVerts.x do minVerts.x = vertPos.x
			if vertPos.y < minVerts.y do minVerts.y = vertPos.y
			if vertPos.z < minVerts.z do minVerts.z = vertPos.z
			if vertPos.x > maxVerts.x do maxVerts.x = vertPos.x
			if vertPos.y > maxVerts.y do maxVerts.y = vertPos.y
			if vertPos.z > maxVerts.z do maxVerts.z = vertPos.z
			
		)
		print ((maxVerts as string) + "is max outmost")
		print ((minVerts as string) + "is min outmost")
		--local bounds = maxBounds - minBounds
		return (maxVerts - minVerts)
	)

	

	on modifyMesh do
	(
		--get the selection from stack
		local selectedFaces = getFaceSelection mesh as bitarray
		--or all faces
		local allFaces = mesh.faces as bitarray
		--create a new bitarray for the newly created faces so we can use them later
		local newFaces = #{}

		local duplicate = #{}
		--operate on selected or all
		if faceMode == 1 do selectedFaces = allFaces

		--get the bounds of the object to determine the number of cuts, make sure to not cut on the outmost extent and to limit the number of cuts when dealing in world space
		--from the center (or a custom grid pivot) go positive and negative along the axis and for each division slice and offset divided by divions

		local gridNormal = normalize [gridOffsetX, gridOffsetY, gridOffsetZ]
		local slicedFaces = mesh.faces as bitarray

		local bounds = CalculateBounds (mesh.vertices as BitArray)
		print (bounds as string + "boundsize")
		local centerPoint = GetCenterPoint (mesh.vertices as BitArray)
		print (centerPoint as string + " is centerpint")
		--local fit = bounds.x * 2 / (gridX + 1)
		local fitPoint3 = (bounds) / [gridX + 1,gridY + 1,gridZ + 1]

		for i = 1 to (gridX) do
		(
			
			-- need to start at i-1 so the slice plane is centered
			--basePos = ((i-1) * fitPoint3.x) 
			-- move the slice plane halfway as many times as it fits times the amount of grid divions
			--basePos -= (gridX - 1) * fitPoint3.x * 0.5
			
			
			basePos = ((i-1) * fitPoint3.x ) + centerPoint.x - (gridX - 1) * fitPoint3.x * 0.5
			--basePos -= centerPoint.x
			--basePos -= (gridX as float) / bounds.x
			--basePos -= (bounds.x / gridX) - fit
			--basePos -= (gridX) as float * fit 
			--basePos += fit
			--basePos -= ((bounds.x - fit) * (gridX))
			--basePos -= bounds.x / gridX * (gridX-1)  + 0

			meshop.slice mesh (mesh.faces as bitarray) ([1,0,0]) basePos separate:false delete:false 

		)
		
		for i = 1 to (gridY) do
		(
			
			basePos = ((i-1) * fitPoint3.y) + centerPoint.y - (gridY - 1) * fitPoint3.y * 0.5

			meshop.slice mesh (mesh.faces as bitarray) ([0,1,0]) basePos separate:false delete:false 

		)

		for i = 1 to (gridZ) do
		(
			
			basePos = ((i-1) * fitPoint3.z) + centerPoint.z - (gridZ - 1) * fitPoint3.z * 0.5

			meshop.slice mesh (mesh.faces as bitarray) ([0,0,1]) basePos separate:false delete:false 

		)

		--sliceOp mesh selectedFaces [gridOffsetX,gridOffsetY,gridOffsetZ] 20 separate:false delete:false 
		
	)
)