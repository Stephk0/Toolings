macroScript ST3E_LetterSequenceMaker
	category:"ST3E_ObjectCreation"
	toolTip:"Letter Sequence Maker"
	ButtonText:"LetterSequenceMaker"
(

	global textObject
	global seqString
	global charSequenceArray

	fn filterString2 theString theDelimiters =
	(
		theTokens = #() --array of tokens to return
		ready = false
		while not ready do --repeat until no more delimiters can be found
		(
		ready = true --raise a flag that we are done
		thePosArray = #() --init. an array to hold possible split positions
		for i = 1 to theDelimiters.count do --go through all delimiters
		(
		checkPos = findString theString theDelimiters[i] --check if the delimiter is in the string
		if checkPos != undefined do append thePosArray checkPos --if it is, add to the split positions array
		) --end i loop 
		if thePosArray.count > 0 then --if the array has any splitpositions,
		(
		sort thePosArray --sort the array in ascending order
		checkPos = thePosArray[1] --grab the first position
		aToken = substring theString 1 (checkPos-1) --take the token from start to the split pos. - 1
		append theTokens aToken --add the token to the array of tokens
		theString = substring theString (checkPos+1) theString.count --remove the token and the delimiter from the string
		ready = false --lower the flag because we are not ready yet
		) --end if
		) --end while loop
		append theTokens theString --add what is left of the string to the array
		theTokens --return the array of tokens
	)

	fn RemoveAllWhiteSpace inputString = 
	(
 
		local outputString = StringStream ""
		for x in filterString inputString " \t\r\n" do format "%" x to:outputString
		outputString as string
		 
	)
	seqString = "A,B,C,D,E,F,G,H,I,J,K,L,M,N,O,P,Q,R,S,T,U,V,W,X,Y,Z" 
	if seqString == undefined then seqString = "A,B,C,D,E,F,G,H,I,J,K,L,M,N,O,P,Q,R,S,T,U,V,W,X,Y,Z" 
	--else seqString = (filterString (charSequenceArray as string) "#()")

	
	rollout ST3E_LetterSequenceMakerWindow "ST3E LetterSequenceMaker" width:232 height:400
	(
		group "Character Sequence" 
		(
			label 'lbl_letterSeq' "Letter / Character Sequence Defintion" align:#left--pos:[8,8] width:184 height:16 align:#left
			editText 'edt_letterSeq' "" text:seqString align:#left--pos:[0,32] width:224 height:24 align:#left
			button 'btn_addABC' "ABC" pos:[16,64]--pos:[8,232] width:208 height:32 align:#left
			button 'btn_add123' "123" pos:[56,64]--pos:[8,232] width:208 height:32 align:#left
		)

		local pickString = if textObject == undefined then "Pick Style from Text" else textObject.name
		fn text_filt obj = classof obj == text
		group "Pick Text Style" 
		(
			pickButton 'btn_pickStyle' pickString filter:text_filt 	
		)
		group "Naming output" 
		(
			label 'lbl_nameOuput' "Naming output" align:#left--pos:[8,96] --width:184 height:16 align:#left
			editText 'edt_BaseName' "Base Name" --pos:[8,120] --width:208 height:24 align:#left
			radioButtons 'rbt_suffixMode' "Suffix" labels:#("From Defintion", "Numbered Sequence") align:#left--pos:[8,160] width:100 height:46 align:#left
		)
		group "Object Output Offset" 
		(
			spinner spn_XOffset "X" align:#left  type:#worldUnits range:[0,1e6,100] 
			spinner spn_YOffset "Y" align:#left  type:#worldUnits range:[0,1e6,0] 
			spinner spn_ZOffset "Z" align:#left  type:#worldUnits range:[0,1e6,0] 
		)

		button 'btn_createAssets' "Create Assets" --pos:[8,232] width:208 height:32 align:#left

		on btn_pickStyle picked nodeobject do 
		(
			if classof nodeobject == text then textObject = nodeobject
			else messageBox ("Selection is not a Text Object") title:"Selection is not a Text Object" beep:true
			btn_pickStyle.text = textObject.name

		)

		on btn_createAssets pressed do 
		(
			if textObject == undefined then messageBox ("No Text Style was picked") title:"No Text Style was picked"
			else print "proceed"
			
			charSequenceArray = #()
			charSequenceArray = (filterString2 (edt_letterSeq.text) "\t, ") as array
			for i =1 to charSequenceArray.count do 
			(

				local textElement
				if textObject != undefined then
				(
					textElement = copy textObject
					textElement.transform = matrix3 1
				) 
				else textElement = text()
				textElement.name = edt_BaseName.text + (charSequenceArray[i] as string)
				textElement.text = charSequenceArray[i] as string
				textElement.position.x = (i - 1) * spn_XOffset.value
			)
		)
	)

	CreateDialog ST3E_LetterSequenceMakerWindow
)