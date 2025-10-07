/*

*/

macroScript SelectbyMaterialID
	category:"StephkoCustom"
	toolTip:"Select by Material ID"
	ButtonText:"SelectByMaterialID"
	(

		on isEnabled return (subobjectlevel != undefined and (Filters.Is_EPoly() or Filters.Is_EditSpline() or (ClassOf (modPanel.getCurrentObject()) == Unwrap_UVW)) and subobjectlevel != 0 and subobjectlevel < 6)
		
		on execute do
		(
			local selectedObj = selection[1]
			activeMod = Filters.GetModOrObj()
			local matIDs = #{}

			if (Filters.Is_EPoly()) then
			(

				if (subobjectlevel==1) then (activeMod.ConvertSelection #Vertex #Face)
				if (subobjectlevel==2 OR subobjectlevel==3) then (activeMod.ConvertSelection #Edge #Face)

				subobjectlevel = 4

				local selectedFaces = activeMod.GetSelection #Face
				
				--collect unique material IDs that are selected
				for face in selectedFaces do
				(
					local faceMatID = activeMod.GetFaceMaterial face
					appendIfUnique matIDs faceMatID
				)

				if (Filters.Is_This_EditPolyMod activeMod) then
				(	

					local clearSelectionOn = activeMod.selectByMaterialClear
					--if (activeMod.selectByMaterialClear == true) then clearSelectionOn = true
					--repeat button op for every material ID
					for matID in matIDs do
					(
						activeMod.selectByMaterialClear = false
						activeMod.selectByMaterialID = matID - 1
						activeMod.ButtonOp #SelectByMaterial
					)
					activeMod.selectByMaterialClear = clearSelectionOn
				)
				else
				(
					
					local resultingFaces = #{}
					--select by material, store the resulting faces and accumulate if unique
					for matID in matIDs do
					(
						activeMod.selectByMaterial matID
						local selectedFacesByMaterial = activeMod.GetSelection #Face as array
						
						for face in selectedFacesByMaterial do
						(
							appendIfUnique resultingFaces face
						)
					
					)
					activeMod.SetSelection #Face resultingFaces

				)
			)
			else if (Filters.Is_EditSpline()) then
			(	
				--collect unique material IDs that are selected
				for spline = 1 to (numSplines selectedObj) do
				(
					local selectedSegments = getSegSelection selectedObj spline
					
					for segment in selectedSegments do 
					(
						appendIfUnique matIDs (getMaterialID selectedObj spline segment)
					)	
				)
				
				--clear selection
				for spline = 1 to (numSplines selectedObj) do
				(
					setSegSelection selectedObj spline #()
				)
				--for every material ID select the segment if it has the same ID and accumulate the selection by using keep:true
				for matID in matIDs do
				(		
					for spline = 1 to (numSplines selectedObj) do
					(
						for segment = 1 to (numSegments selectedObj spline) do 
						(
							if (getMaterialID selectedObj spline segment == matID) do setSegSelection selectedObj spline #(segment) keep:true
						)
					)	
				)
			)
			
			else if (ClassOf (activeMod) == Unwrap_UVW) then
			(
				selectedFaces = activeMod.getSelectedFaces()
				print selectedFaces
				
				for face in selectedFaces do
				(
					activeMod.selectFaces #{face}
					completeredraw() -- workaround needed to update the spinner in the uv so getSelectMatID actually works...
					appendIfUnique matIDs (activeMod.getSelectMatID())
					
				)

				print matIDs

				local resultingFaces = #{}
				--select by material, store the resulting faces and accumulate if unique
				for matID in matIDs do
				(
					activeMod.selectByMatID matID
					local selectedFacesByMaterial = activeMod.getSelectedFaces()
					
					for face in selectedFacesByMaterial do
					(
						appendIfUnique resultingFaces face
					)
				
				)
				activeMod.selectFaces resultingFaces
			)
		)

	)		
	

	

	
	

