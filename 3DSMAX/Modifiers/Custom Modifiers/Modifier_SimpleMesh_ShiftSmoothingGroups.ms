/*
Shift Smoothing groups by given amount
by Stephan Viranyi https://www.artstation.com/stephko
Feel free to share and extend to your wishes and msg me for any questions or feedback at stephko@viranyi.de
*/
--todo: add whole mesh bool

plugin simpleMeshMod ShiftSGs
	name:"Shift Smoothing Groups"
	classID:#(0x549b2ff2, 0x1f974013)
(
	fn clamp minVal maxVal val =
	(
		if classOf val == point3 then 
		(
			if val.x < minVal then val.x = minVal
			else if val.x > maxVal then val.x = maxVal
			if val.y < minVal then val.y = minVal
			else if val.y > maxVal then val.y = maxVal
			if val.z < minVal then val.z = minVal
			else if val.z > maxVal then val.z = maxVal
		)
		else 
		(
			if val < minVal then val = minVal
			else if val > maxVal then val = maxVal
		)
		return val
	)
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
		
		group "Shift Smoothing Groups by"
		(
			spinner spn_shiftValue "Offset" range:[-32, 32, 0] type:#integer
		)

		group "Quick Offsets"
		(

			button 'shiftPlus4' ">" 		pos:[80,128] 	width:24 height:24 align:#left toolTip: "+4 Smoothing Groups Offset"
			button 'shiftPlus8' ">>" 		pos:[104,128] width:24 height:24 align:#left   toolTip: "+8 Smoothing Groups Offset"
			button 'shiftPlus16' ">>>" 		pos:[128,128] width:24 height:24 align:#left  toolTip:"+16 Smoothing Groups Offset"
			
			button 'shiftMinus4' "<" 		pos:[56,128] 	width:24 height:24 align:#left  toolTip:"-4 Smoothing Groups Offset"
			button 'shiftMinus8' "<<" 		pos:[32,128] 	width:24 height:24 align:#left  toolTip:"-8 Smoothing Groups Offset"
			button 'shiftMinus16' "<<<" 	pos:[8,128] 	width:24 height:24 align:#left  toolTip:"-16 Smoothing Groups Offset"
		)

		on shiftPlus4 pressed do spn_shiftValue.value = clamp -32 32 (spn_shiftValue.value + 4)
		on shiftPlus8 pressed do spn_shiftValue.value = clamp -32 32 (spn_shiftValue.value + 8)
		on shiftPlus16 pressed do spn_shiftValue.value = clamp -32 32 (spn_shiftValue.value + 16)

		on shiftMinus4 pressed do spn_shiftValue.value = clamp -32 32 (spn_shiftValue.value - 4)
		on shiftMinus8 pressed do spn_shiftValue.value = clamp -32 32 (spn_shiftValue.value - 8)
		on shiftMinus16 pressed do spn_shiftValue.value = clamp -32 32 ( spn_shiftValue.value - 16)
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
			--get this 32 bit integer representing a bitarray of the smooth groups assigned to the face
			--we need to use 32 bit interger to assign the face smoothing group, unless we convert it to an actual bitarray as described below
			local faceSG = getFaceSmoothGroup mesh face
			--create a new 32 bit int where we assign the new smoohting groups to
			local faceSGShifted = 0

			--for each smoothing group (1-32) there is...
			for sgInFace = 1 to 32 do 
			(
					-- modulo for 32 groups, make sure we stay within those 32 max groups, if we exceed we circleshift back ie 48 grp = 16, 64 grp = 32 etc, adding the 1 offset and substracting > begins at 1 and not 0
					local circularShift = (1 + mod (sgInFace + shiftValue - 1) 32) 
					if circularShift < 1 then circularShift = 32 + circularShift
					-- after many painful tries, its a simple as that, we just assign the circular shifted smoothing groups to the new "bitarray" represented as int using bit.set and bit.get:
					faceSGShifted = bit.set faceSGShifted circularShift (bit.get faceSG sgInFace)
					
					--actual bitarray variant but requires custom function to convert from 32 bit int to bitarray and back, see: 
					--https://help.autodesk.com/view/3DSMAX/2016/ENU/?guid=__files_GUID_58D1F8B6_0012_4727_AA29_B2C79EA46E16_htm
					--shiftedFaceSGBA[circularShift] = faceSGBA[sgInFace]
			)
			
			setFaceSmoothGroup mesh face faceSGShifted
		)
	)
)