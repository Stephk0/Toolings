macroScript ExtractRefernece
	category:"ST3E_Management"
	toolTip:"Extract Reference"
	ButtonText:"Extract Reference"
(

	fn ExtractMaster refObj = 
	(
		local master = point();
		--if refObj[4][refObj[4].numSubs].name==“Modified Object” then master.baseObject=refObj.modifiedObject
		--else master.baseObject=refObj.baseObject
		master.baseObject=refObj.baseObject
		master
	)

	ExtractMaster $
)

macroScript SelectReferencesInstances
	category:"ST3E_Management"
	toolTip:"Select All Instances + References"
	buttonText:"Select All Instances+References"
(
	local nodes = getCurrentSelection()
	local baseObjs = for obj in nodes collect obj.baseObject
	for obj in objects where findItem baseObjs obj.baseObject > 0 do append nodes obj
	select nodes
)

macroScript SelectReferences
	category:"ST3E_Management"
	toolTip:"Select All References"
	buttonText:"Select References"
(
	--TODO: Doesnt work properly, not sure how to find only the references
	local nodes = getCurrentSelection()
	local baseObjects = #()
	--local baseObjs = for obj in nodes collect obj.baseObject
	local baseObjs = for obj in nodes do appendIfUnique baseObjs (obj.baseObject as Editable_Poly)
	for obj in objects where findItem baseObjs obj.baseObject do appendIfUnique baseObjects obj
		print baseObjects
	select baseObjects[1]
)



