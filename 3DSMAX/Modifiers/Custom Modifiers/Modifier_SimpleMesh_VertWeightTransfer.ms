/*
Set and transfer weights to color , color to verts
by Stephan Viranyi https://www.artstation.com/stephko
Feel free to share and extend to your wishes and msg me for any questions or feedback at stephko@viranyi.de
*/

plugin simpleMeshMod VertWeightTransfer
	name:"Vertex Weight / Color Transfer"
	classID:#(0x3baa6e99, 0x49e003c1)
(

	local getVertsUsingFace = meshop.getVertsUsingFace

	parameters main rollout:params
	(
		vertMode ui:rbb_vertMode default:1 type:#integer animatable:true	
	) 

	parameters transfer rollout:paramsTrans
	(
		WeightToColor ui:chk_WeightToColor default:true type:#boolean
		WeightToColorColor ui:cpk_WeightToColorColor type:#color animatable:true
		WeightToColorValue ui:spn_WeightToColorValue default:1.01 type:#float animatable:true		

		ColorToWeight ui:chk_ColorToWeight default:false type:#boolean
		ColorToWeightColor ui:cpk_ColorToWeightColor type:#color animatable:true
		ColorToWeightValue ui:spn_ColorToWeightValue default:1.01 type:#float animatable:true	
	) 
	
	rollout params "Parameters"
	(
		group "Operate on"
		(
			radiobuttons rbb_VertMode labels:#("Total Vertices", "Selected Vertices")
		)
	) 

	rollout paramsTrans "Transfer / Set"
	(
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
	) 

	on modifyMesh do
	(

		--get the selection from stack
		local selectedVertices =  mesh.vertices as bitarray
		if vertMode == 2 do selectedVertices = getVertSelection mesh as bitarray
		local faceSel = getFaceSelection mesh as bitarray
		if not faceSel.isEmpty do selectedVertices += getVertsUsingFace mesh faceSel
		--enable support for vertex weight
		meshop.setVDataChannelSupport mesh 2 true
		
		--transfer weight to color 
		if WeightToColor do 
		(
			local weightedVerts = (for vert = 1 to mesh.numverts where (meshop.getVDataValue mesh 2 vert) >= WeightToColorValue collect vert) as bitarray
			meshop.setVertColor mesh 0 (weightedVerts * selectedVertices) WeightToColorColor
		)
		--tranfer color to weight
		if ColorToWeight do 
		(
			local coloredVerts = meshop.getVertsByColor mesh ColorToWeightColor 1 1 1
			coloredVerts = coloredVerts * selectedVertices
			for vert in coloredVerts do
			(
				meshop.setVDataValue mesh 2 vert ColorToWeightValue
			)
		)
		
		
	)
)