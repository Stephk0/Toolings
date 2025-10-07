macroScript AddModifier_tySelect
	category:"StephkoCustom"
	toolTip:"Add Modifier tySelect"
	ButtonText:"tySelect"
(
	modPanel.addModToSelection (tySelect ()) ui:on
)

macroScript AddModifier_tySelectFace
	category:"StephkoCustom"
	toolTip:"Add Modifier tySelect Face"
	ButtonText:"tySel Face"
(
	modfierToAdd = tySelect()
	--modfierToAdd.subObject = 2  -- formally was called like this
	modfierToAdd.subObjectMode = 2
	modPanel.addModToSelection (modfierToAdd) ui:on
)
