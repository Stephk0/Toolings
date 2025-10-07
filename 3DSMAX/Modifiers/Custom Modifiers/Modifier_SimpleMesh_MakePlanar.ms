/*
Shift Material IDs by given amount
by Stephan Viranyi https://www.artstation.com/stephko
Feel free to share and extend to your wishes and msg me for any questions or feedback at stephko@viranyi.de
*/

plugin simpleMeshMod MakePlanar
	name:"Make Planar"
	classID:#(0x327db1ce, 0x6c9fb3d6)
(

	local baseshape
	local planarshape
	
	fn lerp minVal maxVal term = (maxVal - minVal) * term + minVal

	parameters main rollout:params
	(
		shiftValue ui:spn_shiftValue default:0 type:#float animatable:true		
	) 
	
	rollout params "Parameters"
	(
		spinner spn_shiftValue "Shift Material IDs by" range:[0, 100, 0] type:#float
	) 

	on modifyMesh do
	(
		--get the selection from stack
		local selectedFaces = getFaceSelection mesh as bitarray
		meshop.makeFacesPlanar mesh selectedFaces
		/*
		baseshape = mesh.verts
		planarshape = mesh.verts
		--planarshape = meshop.makeFacesPlanar baseshape selectedFaces
		meshop.moveVertsToPlane obj #{1..obj.numverts} normal 0.0
		mesh.verts = lerp baseshape planarshape (shiftValue / 100)
		*/
	)
)