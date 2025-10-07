/*
Toon Outline by flipped and pushed normals
by Stephan Viranyi https://www.artstation.com/stephko
Feel free to share and extend to your wishes and msg me for any questions or feedback at stephko@viranyi.de
*/

plugin simpleMeshMod PushNormalOutline
	name:"Push Normal Outline"
	classID:#(0x13f11635, 0x324f2268)
(

	parameters main rollout:paramsOp
	(
		faceMode ui:rbb_faceMode default:1 type:#integer animatable:true
		splitByMat ui:chk_SplitByMat default:false type:#boolean animatable:true	
		
		splitMode ui:rbb_splitMode default:1 type:#integer animatable:true
		splitPreOffset ui:spn_splitPreOffset default:0 type:#float animatable:true
		splitPreDistance ui:spn_splitPreDistance default:0 type:#float animatable:true
		splitDistance ui:spn_splitDistance default:0 type:#float animatable:true
		splitOffset ui:spn_splitOffset default:0 type:#float animatable:true
		--splitSel ui:chk_splitSel default:true type:#boolean animatable:true	
		createDuplicate ui:chk_duplicate default:false type:#boolean animatable:true
		flipOrig ui:chk_flipOrig default:false type:#boolean animatable:true
		flipNew ui:chk_flipNew default:false type:#boolean animatable:true
		
	)
	
	parameters select rollout:paramsSel
	(

		keepSel ui:chk_keepSel default:false type:#boolean animatable:true
		selClone ui:chk_selClone default:false type:#boolean animatable:true
		selExtr ui:chk_selExtr default:false type:#boolean animatable:true		
	)  
	
	rollout paramsOp "Parameters"
	(
		group "Selection:"
		(
			radiobuttons rbb_faceMode labels:#("Total Faces", "Selected Faces")
			checkbox chk_SplitByMat "Selections by Material ID" checked:true tooltip:"Create unique Selections by Material ID"
		)
		group "Operation:"
		(
			radiobuttons rbb_splitMode labels:#("Split Selection(s)","Split Extrude Selection(s)", "Extrude Selection(s)","Edge Extrusion(s)")
			--checkbox chk_SplitByMat "Split Extrude" checked:true tooltip:"Filter Face Selection by Material IDs"
		)
		spinner spn_splitPreOffset "Outline Width" type:#worldUnits range:[-1e6,1e6,0]
		spinner spn_splitPreDistance "Base Split Distance" type:#worldUnits range:[-1e6,1e6,0]
		spinner spn_splitDistance "Split Distance" type:#worldUnits range:[-1e6,1e6,0]
		spinner spn_splitOffset "Height Offset" type:#worldUnits range:[-1e6,1e6,0] 
		--checkbox chk_splitSel "Split Selection" checked:true tooltip:"Split the Selection"
		checkbox chk_duplicate "Create Duplicate" checked:false tooltip:"Create a duplicate of the Selection"
		checkbox chk_flipOrig "Flip Original" checked:false tooltip:"Split the Selection"
		checkbox chk_flipNew "Flip SplitMesh" checked:false tooltip:"Split the Selection" 
	) 
	
	rollout paramsSel "Select"
	(
		checkbox chk_keepSel "Keep Selection" checked:true tooltip:"Split the Selection"
		checkbox chk_selClone "Select Duplicate" checked:true tooltip:"Split the Selection"
		checkbox chk_selExtr "Select Extrusion" checked:true tooltip:"Split the Selection"
	) 

	on modifyMesh do
	(
		--get the selection from stack
		local selectedFaces = getFaceSelection mesh as bitarray
		--or all faces
		local allFaces = mesh.faces as bitarray
		--create a new bitarray for the newly created faces so we can use them later
		local newFaces = #{}

		local orignalMesh = #{}
		--operate on selected or all
		if faceMode == 1 do selectedFaces = allFaces

		--split groups
		local splitGroups = #()
		local splitGroupFaces = #()

		if splitByMat then
		(
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
		)
		else 
		(
			--just assign one group and our selcted faces to it
			splitGroups = #(1)
			splitGroupFaces[1] = selectedFaces
		)
		--detach all selected Faces

		meshop.detachFaces mesh selectedFaces delete:false  asMesh:false
		orignalMesh =  mesh.faces as bitarray - allFaces
		extrudeface mesh selectedFaces splitPreOffset 100 dir:#independent
		meshop.flipNormals mesh selectedFaces

		--local extrusionPart = mesh.faces as bitarray - newFaces - duplicate - allFaces
		local finalSelection = #{}

		if keepSel do finalSelection += orignalMesh
		if selClone do finalSelection += selectedFaces
		--if selExtr do finalSelection += extrusionPart
		if finalSelection.numberSet != 0 do mesh.selectedFaces = finalSelection
		--mesh.selectedFaces = newFaces
	)
)