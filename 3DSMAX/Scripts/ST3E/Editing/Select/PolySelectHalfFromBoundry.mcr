macroScript PolySelectHalfFromBoundry
	category:"ST3E_Modelling"
	toolTip:"Poly Select Half From Boundry"	
	ButtonText:"Select HalfFromVert"
	(

		persistent global prevFaceSel

		On IsEnabled Return Filters.Is_EPoly()
		On IsVisible Return Filters.Is_EPoly()
		On Execute Do
		(
			with redraw off(
			--bitarray of verts forming the boundry
			local vertexBoundry = #{}
			if prevFaceSel == undefined do prevFaceSel = #{}
			local prevEdgeSel = #{}
			local prevVertSel = #{}
			local element
			local process = true
			local st = timestamp()
			local ep = modPanel.getCurrentObject()
			--get the selection as vertex boundry
			prevVertSel = ep.GetSelection #Vertex
			prevEdgeSel =  ep.GetSelection #Edge


			if subObjectLevel == 1 then
			(
				vertexBoundry = ep.GetSelection #Vertex
			)
			else if subObjectLevel == 2 or subObjectLevel == 3 do 
			(
				ep.convertSelection #Edge #Vertex
				vertexBoundry = ep.GetSelection #Vertex
			)
			if subObjectLevel > 3 do
			(
				local faceSel = ep.GetSelection #Face
				if (prevFaceSel - faceSel).isEmpty do
				(
					print "is same"
					if Filters.Is_This_EditPolyMod ep then
					(
						ep.convertSelection #Face #Element
						element = ep.GetSelection #Face
						ep.SetSelection #Face #{}
						ep.Select #Face #{}
					)
					else  element = polyop.getElementsUsingFace ep prevFaceSel

					ep.SetSelection #Face (-prevFaceSel * element)
					process = false
				) 
			)
			--print (vertexBoundry as string + " vertices are boundries")
			if process do 
			(
			--faceTrim
			local trimFaces = #{}
			--ep.Select #Face trimFaces
			--ep.SetSelection #Face trimFaces
			--ep.SetSelection #Face #{(ep.convertSelection #Edge #Vertex)}
			ep.convertSelection #Vertex #Face
			--ep.SetSelection #Face #{(ep.convertSelection #Vertex #Face)}
			trimFaces = ep.GetSelection #Face
			local element
			if Filters.Is_This_EditPolyMod ep then
			(
				ep.convertSelection #Face #Element
				element = ep.GetSelection #Face
				ep.SetSelection #Face #{}
				ep.Select #Face #{}
			)
			else  element = polyop.getElementsUsingFace ep trimFaces
			--print element
			trimFaces *= element
			--ep.SetSelection #Face element

			local face_array = #{}
			local vertsFromFace = #{}
			local facesFromVerts = #{}
			--difference between grows
			local growDiff
			--count grows to nope out when needed
			local growCounter = 0
			chunkComplete = false
			
			--set to face mode in 
			if Filters.Is_This_EditPolyMod ep then ep.SetEPolySelLevel #Face
			
			while not chunkComplete and process do
			(
				--assign the first face of the trim
				for face in trimFaces where (face_array.count == 0 and trimFaces[face] == true) do face_array = #{face}
				--set selection to the one trim face, for edit_poly hit Select otherwise we selct nothing
				ep.SetSelection #Face face_array
				if Filters.Is_This_EditPolyMod ep do ep.Select #Face face_array
				--Get the neighbours as verts
				ep.convertSelection #Face #Vertex
				vertsFromFace = ep.GetSelection #Vertex
				--substract the vertex boundry
				vertsFromFace -= vertexBoundry
				--set selection to the vertices of the face, for edit_poly hit Select otherwise we selct nothing
				ep.SetSelection #Vertex vertsFromFace
				if Filters.Is_This_EditPolyMod ep do ep.Select #Vertex vertsFromFace
	
				--convert to face to get the next neighbour
				ep.convertSelection #Vertex #Face
				facesFromVerts = ep.GetSelection #Face
				ep.SetSelection #Face facesFromVerts
				if Filters.Is_This_EditPolyMod ep do ep.Select #Face facesFromVerts
			
				--grow counting
				growDiff = facesFromVerts - face_array
				--add the already accounted faces to the array so we can process it for the next round till growDiff is empyy
				face_array += facesFromVerts
				growCounter +=1
				if growDiff.isEmpty do chunkComplete = true
			)
		)
			ep.SetSelection #Edge prevEdgeSel
			ep.SetSelection #Vertex prevVertSel
			subObjectLevel = 4
			print ("chunk formed with " + growCounter as string + " iterations")
		)
		redrawViews()
		prevFaceSel = ep.GetSelection #Face
		print (timestamp() - st) as string
			--ep.SetSelection #Vertex face_array
			--ep.SetSelection #Vertex face_array

/*
			if Filters.Is_This_EditPolyMod ep then
			(
				--edit_poly mod
			)
        	else 
			(
				--editable poly
			) 
		*/
		)


	)





		

