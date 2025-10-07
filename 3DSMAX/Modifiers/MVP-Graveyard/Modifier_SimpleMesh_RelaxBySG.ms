/*
Relax by Smoothing Groups
by Stephan Viranyi https://www.artstation.com/stephko
Feel free to share and extend to your wishes and msg me for any questions or feedback at stephko@viranyi.de
*/

plugin simpleMeshMod RelaxBySG
	name:"Relax by Smoothing Groups"
	classID:#(0x470aa2a7, 0x61accf8)
	version:100
(

	parameters main rollout:params
	(
		vertMode ui:rbb_vertMode default:1 type:#integer animatable:true	
		iteratorNr ui:spn_Iterator default:1 type:#integer animatable:true
		nMode ui:spn_nmode default:1 type:#integer animatable:true		
		freerun ui:chk_freerun default:false type:#boolean

		iterations ui:spn_iterations default:1 type:#integer animatable:true	
		relaxAmount ui:spn_relaxamount default:0.2 type:#float animatable:true		
	) 

	parameters transfer rollout:paramsTrans
	(

		projSourceMode ui:rbb_ProjSourceMode default:1 type:#integer animatable:true
		node type:#node useNodeTmValidity:on subAnim:on ui:pb_ProjSourceNode

		WeightToColor ui:chk_WeightToColor default:true type:#boolean
		WeightToColorColor ui:cpk_WeightToColorColor type:#color animatable:true
		WeightToColorValue ui:spn_WeightToColorValue default:1.01 type:#float animatable:true		

		ColorToWeight ui:chk_ColorToWeight default:false type:#boolean
		ColorToWeightColor ui:cpk_ColorToWeightColor type:#color animatable:true
		ColorToWeightValue ui:spn_ColorToWeightValue default:1.01 type:#float animatable:true	
	) 
	
	rollout params "Parameters"
	(
		group "Operate on:"
		(
			radiobuttons rbb_VertMode labels:#("Total Vertices", "Selected Vertices")
		)
		spinner spn_nmode "neighbour mode" type:#integer range:[1,1e6,1]
		spinner spn_Iterator "Debug Iterator" type:#integer range:[1,1e6,1]
		checkbox chk_freerun "Debug Freerun" checked:false
		
		spinner spn_iterations "Iterations" type:#integer range:[1,1e6,1]
		spinner spn_relaxamount "r Amount" type:#float range:[0,1e6,0.2]
	) 

	rollout paramsTrans "Transfer / Set"
	(
		group "Projection Source"
		(
			radiobuttons rbb_ProjSourceMode labels:#("Sphere", "Mesh")
			pickButton pb_ProjSourceNode "NONE" autoDisplay:on align:#center enabled:(projSourceMode == 2)
		)
		group "Weight to Color"
		(
			checkbox chk_WeightToColor "Weight -> Color" checked:true tooltip:"Transfer Vertex Weight to Vertex color"
			spinner spn_WeightToColorValue "From Weight" type:#float range:[0,1e6,1.01]
			colorpicker cpk_WeightToColorColor "To Color" color:[0,0,0] modal:false
		)
		
		group "Color To Weight"
		(
			checkbox chk_ColorToWeight "Color -> Weight" checked:false tooltip:"Transfer Vertex Color to Vertex Weight"
			colorpicker cpk_ColorToWeightColor "From Color" color:[0,0,0] modal:false
			spinner spn_ColorToWeightValue "To Weight" type:#float range:[0,1e6,1.01]
		)

		on rbb_ProjSourceMode changed state do pb_ProjSourceNode.enabled = state == 2
	) 

	fn lerp minVal maxVal term = (maxVal - minVal) * term + minVal

	on modifyMesh do
	(
		st = timeStamp()
		--get the selection from stack
		local selectedVertices =  mesh.vertices as bitarray
		if vertMode == 2 do selectedVertices = getVertSelection mesh as bitarray
		
		--new smoothed Vertices
		local smoothedVerts = #()
		currentVert = mesh.vertices as bitarray
		for i = 1 to iterations do
		(
			smoothedVerts = #()
			for vert in selectedVertices do
			(
				if vert == iteratorNr or freerun then 
				(
					--print vert
					currentVert = #{vert}
					local neighbourVerts = #{}

					if nMode == 1 then local neighbourVerts = (selectedVertices - currentVert) -- entire mesh as neighbour 
					--just the immediate neighbour
					if nMode == 2 then
					(
						local neighbourFaces = meshop.getFacesUsingVert mesh vert as bitArray
						neighbourVerts = meshop.getVertsUsingFace mesh neighbourFaces
						--neighbourVerts = neighbourVerts - #{vert}
					)
					
					--for nVerts in neighbourVerts do print nVerts
					positions = for nVert in neighbourVerts collect (getVert mesh nVert)

					local avgVertPos = [0,0,0]
					for position in positions do avgVertPos += position
					avgVertPos = avgVertPos / positions.count
					
					local vertPos = getVert mesh vert
					--print (vertPos)
					--print avgVertPos
					smoothedVertPos = vertPos + relaxAmount * (avgVertPos - vertPos)


					--smoothedVertPos = vertPos + relaxAmount * (normalize (vertPos) - vertPos)

					--smoothedVertPos = normalize vertPos * length (avgVertPos)

					--smoothedVertPos = lerp vertPos (normalize vertPos) relaxAmount
					--smoothedVertPos = (vertPos*(1-relaxAmount) + avgVertPos*relaxAmount/(iterations as float))
					
					--smoothedVertPos = (vertPos*(1-relaxAmount) + avgVertPos*relaxAmount/(float)iterations)
					--smoothedVertPos = (vertPos*(1-relaxAmount) + avgVertPos*relaxAmount)

					smoothedVertPos = lerp vertPos avgVertPos relaxAmount
					smoothedVerts[vert] = smoothedVertPos
					--if ((meshop.getVertexAngles mesh #{vert})[vert] <= 2*PI*.99999) then smoothedVerts[vert] = vertPos

					--setVert mesh vert smoothedVertPos
					--smoothed_x = x + factor * (avg_x - x)
					--smoothed_y = y + factor * (avg_y - y)
					--smoothed_z = z + factor * (avg_z - z)
					--local positions = collect nVert in neighbourVerts do (getVert mesh nVert)
					--local neighbourFaces = meshop.getFacesUsingVert mesh vert as bitArray
					--local neighbourVerts = meshop.getVertsUsingFace mesh neighbourFaces
					--print neighbourVerts
				)
			)
			for vert in selectedVertices do
			(
				setVert mesh vert smoothedVerts[vert]
			)
		)
/*
		fn relaxMesh mesh iter =
		(
			-- Declare local variables
			local vangles = #()  -- Array to hold vertex angles for each vertex
			local hold = #()  -- Array to hold original vertex positions
			local nborCount, act  -- Variables for storing nborCountimum and active values
			local vnum = mesh.numVerts  -- Number of vertices in the mesh
			local nbor = #()  -- Array to hold vertex neighbor information
			local sel = #()  -- Array to hold vertex selection state
			local vis = #()  -- Array to hold visibility of neighbors for each vertex
			local fnum = #()  -- Array to hold face count for each vertex

			-- Initialize data structures
			for i in 1 to vnum do
				(
					hold[i] = mesh.getVert i  -- Store original vertex position
					sel[i] = mesh.isVertSel i  -- Store vertex selection state
					if sel[i] then vangles[i] = MeshOps.findVertexAngle mesh i  -- Calculate and store vertex angle if vertex is selected
					nbor[i] = #()  -- Initialize array to hold vertex neighbors
					vis[i] = #()  -- Initialize array to hold neighbor visibility for this vertex
					fnum[i] = 0  -- Initialize face count for this vertex
				)

			-- Build vertex neighbor data structure
			for i in 1 to vnum do
				(
					for j in 1 to mesh.numFaces do
						(
							-- Check if this vertex is part of the current face
							if (mesh.faces[j].vtx[1] == i or mesh.faces[j].vtx[2] == i or mesh.faces[j].vtx[3] == i) then
							(
								-- Add all vertices of this face to the neighbor list for this vertex
								nbor[i][++fnum[i]] = mesh.faces[j].vtx[1]
								nbor[i][++fnum[i]] = mesh.faces[j].vtx[2]
								nbor[i][++fnum[i]] = mesh.faces[j].vtx[3]
							)
						)
				)

			-- Build neighbor visibility data structure
			for i in 1 to vnum do
				(
					for j in 1 to fnum[i] do
						(
							vis[i][j] = true  -- Initially set all neighbors to be visible
							for k in 1 to fnum[i] do
								(
									-- If this neighbor is the same as another neighbor, set it to be invisible
									if (j != k) and (nbor[i][j] == nbor[i][k]) then vis[i][j] = false
								)
						)
				)

			-- Perform relaxation iterations
			for k in 1 to iter do
				(
					for i in 1 to vnum do
						(
							-- Skip relaxation for this vertex if it is not selected and its vertex angle is less than or equal to 2*PI
							if (not sel[i] and (vangles[i] <= 2*PI*.99999)) then continue
							nborCount = nbor[i].Count  -- Number

							-- Skip relaxation for this vertex if it is on the boundary and its neighbor count is less than its face count
							if (boundary and (fnum[i] < nborCount)) then continue
							-- Skip relaxation if this vertex has no neighbors
							if (nborCount < 1) then continue
							local avg = [0,0,0]  -- Initialize average position variable
							for j in 1 to nborCount do
								(
									-- Skip this neighbor if it is not visible
									if (not vis[i][j]) then continue
									act += 1  -- Increment active neighbor count
									avg += hold[nbor[i][j]]  -- Add this neighbor's position to the average position
								)
							-- Skip relaxation if this vertex has no active neighbors
							if (act < 1) then continue
							-- Perform relaxation for this vertex by moving it towards the average position of its active neighbors
							mesh.setVert i (hold[i]*(1-relax) + avg*relax/((float)act))
						)
				)
		)		




			--print ("next vert is " + ((vert+1) as string))
			--if iteratorNr > vert do print "done"
			--for nVerts in neighbourVerts do print nVerts
			--print (selectedVertices - #{vert})
			
			--for nVert in (neighbours) do print nVert
			
			def smooth_vertices(vertices: List[Tuple[float, float, float]], factor: float) -> List[Tuple[float, float, float]]:
			smoothed_vertices = []
			for vertex in vertices:
				x, y, z = vertex
				neighbors = [n for n in vertices if n != vertex]
				num_neighbors = len(neighbors)
				if num_neighbors > 0:
					# Compute the average of the vertex and its neighbors
					avg_x = sum([n[0] for n in neighbors]) / num_neighbors
					avg_y = sum([n[1] for n in neighbors]) / num_neighbors
					avg_z = sum([n[2] for n in neighbors]) / num_neighbors
					# Smooth the vertex by the given factor
					smoothed_x = x + factor * (avg_x - x)
					smoothed_y = y + factor * (avg_y - y)
					smoothed_z = z + factor * (avg_z - z)
					smoothed_vertices.append((smoothed_x, smoothed_y, smoothed_z))
				else:
					# If the vertex has no neighbors, just append it to the list without smoothing
					smoothed_vertices.append((x, y, z))
			return smoothed_vertices
			*/

	

		if iteratorNr > selectedVertices.count do print "done"

		print ("took " + ((timeStamp() - st) as string) + " miliseconds to complete")
	)
)