macroScript PolySmartRemoveVerts
	category:"ST3E_Editing"
	toolTip:"OP Smart Remove (Remove Verts)"
	ButtonText:"PolySmartRemoveVerts"
	(
		-----------------------------------------------------------------------
		-- Smart Remove
		-----------------------------------------------------------------------
		-- same as ctrl + backspace but can be customly set, allowing better integration into your customized workflow
		-- deltes face if face/element selection
		-----------------------------------------------------------------------

		fn EdgeRemoveVertices ep =
		(
			with redraw off
			(		
			--store selections to reobtain later
			local prevVertSelection = ep.GetSelection #Vertex
			local prevFaceSelection = ep.GetSelection #Face
			with undo off(
			--surrounding faces of edge
			ep.convertSelection #Edge #Face
			local surroundingFacesOfEdge = ep.GetSelection #Face
			surroundingFacesOfEdge.count = ep.GetNumFaces()
			--surround faces of vertices
			ep.convertSelection #Edge #Vertex
			local vertsOfLine = ep.GetSelection #Vertex
			ep.convertSelection #Vertex #Face
			local surroundingFacesOfVert = ep.GetSelection #Face
			surroundingFacesOfVert.count = ep.GetNumFaces()
			--diff the two surrounding faces forming the endchunk of the loop
			ep.setSelection #Face (surroundingFacesOfVert - surroundingFacesOfEdge)
			--convert this chunk to verts
			ep.convertSelection #Face #Vertex
			-- substract the endchunk verts
			vertsOfLine -= ep.GetSelection #Vertex
			ep.setSelection #Vertex vertsOfLine
			)
			--we are still in subobj 2, so remove the edge first
			ep.Remove()
			--then remove the verts in subobj 1
			subobjectLevel = 1
			ep.Remove()
			--back to edge mode
			subobjectLevel = 2
			)
			-- reset previously active selections
			ep.setSelection #Face prevFaceSelection
			ep.setSelection #Vertex prevVertSelection
			
			
		)

		on isEnabled return Filters.Is_EPoly
		
		on execute do
		(
			local currentMod = modPanel.getCurrentObject()
			
			if Filters.Is_This_EditPolyMod currentMod then
			(
				case subobjectlevel of
				(
					1:(currentMod.ButtonOp #RemoveVertex)
					2:(currentMod.ButtonOp #RemoveEdgeRemoveVertices)
					3:(currentMod.ButtonOp #RemoveEdgeRemoveVertices)
					4:(currentMod.ButtonOp #DeleteFace)
					5:(currentMod.ButtonOp #DeleteFace)
				)
			)
        	else 
			(

				case subobjectlevel of
				(
					1:(currentMod.Remove ())
					2:(EdgeRemoveVertices currentMod)
					3:(EdgeRemoveVertices currentMod)
					4:(currentMod.delete #Face)
					5:(currentMod.delete #Face)
				)
			)
		
		)

	)		
	macroScript PolySmartRemove
	category:"ST3E_Editing"
	toolTip:"OP Smart Remove"
	ButtonText:"PolySmartRemove"
	(

		-----------------------------------------------------------------------
		-- Smart Remove
		-----------------------------------------------------------------------
		-- same as shift+backspace but can be customly set, allowing better integration into your customized workflow
		-- deltes face if face/element selection
		-----------------------------------------------------------------------

		local prevSelection

		on isEnabled return Filters.Is_EPoly
		
		on execute do
		(
			--init array if we dont have one
			if prevSelection == undefined do prevSelection = #()

			if selection.count > 1 OR subObjectLevel == 0 do 
			(
				delete selection
				/*
				if prevSelection != selection then
				(
					print "sure?"
					prevSelection = selection as Array
				)
				else delete selection
				*/
			)

			local currentMod = modPanel.getCurrentObject()
			

			case ClassOf currentMod of 
			(
				Editable_Poly:
				(
					case subobjectlevel of
					(
					1:(currentMod.remove selLevel:#currentLevel)
					2:(currentMod.remove selLevel:#currentLevel)
					3:(currentMod.remove selLevel:#currentLevel)
					4:(currentMod.delete #Face)
					5:(currentMod.delete #Face)
					)
				)
				Edit_Poly:
				(
					case subobjectlevel of
					(
						1:(currentMod.ButtonOp #RemoveVertex)
						2:(
							if (keyboard.controlPressed) then currentMod.ButtonOp #RemoveEdgeRemoveVertices
							else currentMod.ButtonOp #RemoveEdge			
						)
						3:(
							if (keyboard.controlPressed) then currentMod.ButtonOp #RemoveEdgeRemoveVertices
							else currentMod.ButtonOp #RemoveEdge			
						)
						4:(currentMod.ButtonOp #DeleteFace)
						5:(currentMod.ButtonOp #DeleteFace)
					)
				)
				Line:splineOps.delete selection[1]
				Splineshape:splineOps.delete selection[1]
		
			)


			
		
		)

	)		
