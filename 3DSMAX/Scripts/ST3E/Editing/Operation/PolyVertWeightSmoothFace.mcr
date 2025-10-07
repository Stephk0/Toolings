
------------------------------------------------------------------------------
-- Hotkey is meant to be used with Smoothing Group from Vertex Boundry workflow. Serves dual purpose of setting face smoothing group but also toggling "corners" for SGfromVB workflow.
-- set smoothing groups quickly selecting the face to smooth and hit the hotkey
-- vertex: toggle vertex weight / corners when in vertex mode
-- edge/border: switch to vertex and toggle verts when in edge mode
-- face/element: smooth all the faces to one group

-------------------------------------------------------------------------------


macroScript WeigthVertSmoothFace
	category:"ST3E_Editing"
	toolTip:"OP Vert Weight Toggle / Smooth Faces"
	ButtonText:"WghtVertSmtFace"
(
	On IsEnabled Return Filters.Is_EPoly
	On IsVisible Return Filters.Is_EPoly

	On Execute Do 
	(
		
			If SubObjectLevel == undefined then Max Modify Mode

			local editPoly = Filters.GetModOrObj()
			
			--if not a face selected
			if subobjectlevel < 4 then
			(
				local prevEdgeSelection = false
				--edge is selected, convert to vertex and set mode
				if subobjectlevel > 1 do
				(
					prevEdgeSelection = true
					editPoly.ConvertSelection #Edge #Vertex
					subobjectlevel = 1
				)
				--flag if any of the selected vertices is a corner
				local makeSoft = false
				local vertSelection = editPoly.GetSelection #Vertex as BitArray
				
				--if its a edit poly mod , setting data channel values operates differently
				--currently the "bug" is that a vertex needs to be selected and ui updated somehow as the value that can be gathered from the ui is the last set one and not the one from the vert selection
				if (Filters.Is_This_EditPolyMod editPoly) then
				(		
					
					editPoly.dataChannel = 1
					for vert in vertSelection while makeSoft == false do 
					(
						editPoly.Select #Vertex #{}
						editPoly.RefreshScreen() --- didnt help
						editPoly.SetOperation 85
						editPoly.Select #Vertex #{vert}
						--completeredraw() -- also didnt help
						editPoly.RefreshScreen() 
						value = editPoly.dataValue
						print value
						--editPoly.Commit ()	-- no dice
						editPoly.Select #Vertex #{vert}
						--editPoly.SetSelection #Vertex #{vert}
						--editPoly.dataChannel = 1
						--value = editPoly.dataValue
						--editPoly.Commit ()
						
						if value >= 1.01 do makeSoft = true
					)
					editPoly.Commit()
					editPoly.Select #Vertex vertSelection
					editPoly.SetSelection #Vertex vertSelection
					editPoly.SetOperation 85
					if makeSoft then editPoly.dataValue = 1
					else editPoly.dataValue = 1.01
					
					editPoly.Commit()
		
				)
				else 
				(
					with redraw off
					(
						--if any of the selected vertices is a corner aka 1.01 weight make it soft
						numsel = 1 --define a variable to pass by reference (?? from max docu)
						uniform = false --define a boolean var. for uniformity (?? from max docu)
						if editPoly.getVertexData 1 &numsel &uniform >= 1.01 do makeSoft = true
					)
					if makeSoft then editPoly.setVertexData 1 1
					else editPoly.setVertexData 1 1.01
					
				)
				if prevEdgeSelection do subObjectLevel = 2
			)
			--if face selected, smooth it entirely with 180 degress and restore previous value
			else
			(
				with redraw off 
				(
				local editPoly = Filters.GetModOrObj()
				local prevASValue = editPoly.autoSmoothThreshold
				editPoly.autoSmoothThreshold = 180
				)
				editPoly.ButtonOp #Autosmooth
				editPoly.autoSmoothThreshold = prevASValue
			)
		
	)

)