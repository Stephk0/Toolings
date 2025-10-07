/*
Shift Material IDs by given amount
by Stephan Viranyi https://www.artstation.com/stephko
Feel free to share and extend to your wishes and msg me for any questions or feedback at stephko@viranyi.de
*/

plugin simpleMeshMod ShiftMatIDs
	name:"Shift Material IDs"
	classID:#(0x2c444d8d, 0x3b709751)
(

	parameters main rollout:params
	(
		faceMode ui:rbb_faceMode default:1 type:#integer animatable:true
		shiftValue ui:spn_shiftValue default:0 type:#integer animatable:true		
	) 
	
	rollout params "Parameters"
	(
		group "Operate on"
		(
			radiobuttons rbb_faceMode labels:#("Selected Faces", "Total Faces")
		)
		group "Shift Material IDs by"
		(
			spinner spn_shiftValue "Offset" range:[-1e6, 1e6, 0] type:#integer
		)
		group "Quick Offsets"
		(

			button 'shiftPlus5' ">" 		pos:[80,128] 	width:24 height:24 align:#left toolTip: "+5 IDs Offset"
			button 'shiftPlus10' ">>" 		pos:[104,128] width:24 height:24 align:#left   toolTip: "+10 IDs Offset"
			button 'shiftPlus100' ">>>" 	pos:[128,128] width:24 height:24 align:#left  toolTip: "+100 IDs Offset"
			
			button 'shiftMinus5' "<" 		pos:[56,128] 	width:24 height:24 align:#left  toolTip: "-5 IDs Offset"
			button 'shiftMinus10' "<<" 		pos:[32,128] 	width:24 height:24 align:#left  toolTip: "-10 IDs Offset"
			button 'shiftMinus100' "<<<" 	pos:[8,128] 	width:24 height:24 align:#left  toolTip: "-100 IDs Offset"
		)

		on shiftPlus5 pressed do spn_shiftValue.value = spn_shiftValue.value + 5
		on shiftPlus10 pressed do spn_shiftValue.value = spn_shiftValue.value + 10
		on shiftPlus100 pressed do spn_shiftValue.value = spn_shiftValue.value + 100

		on shiftMinus5 pressed do spn_shiftValue.value = spn_shiftValue.value - 5
		on shiftMinus10 pressed do spn_shiftValue.value = spn_shiftValue.value - 10
		on shiftMinus100 pressed do spn_shiftValue.value = spn_shiftValue.value - 100
	) 

	on modifyMesh do
	(
		--get the selection from stack
		local selectedFaces = getFaceSelection mesh as bitarray
		--operate on selected or all
		if faceMode == 2 do selectedFaces = mesh.faces as bitarray
		--for each face in the selection
		for face in selectedFaces do
		(
			local faceMatID = getFaceMatID mesh face
			--check if face mat ID is not under 0 if we shift to left
			if (faceMatID + shiftvalue > 0) then setFaceMatID mesh face (faceMatID + shiftvalue)
			else setFaceMatID mesh face 1
		)
	)
)