macroScript ShowCage
	category:"ST3E_Inspection"
	toolTip:"Show Cage (No Undo)"
	ButtonText:"Show Cage"
(

	on isEnabled do Ribbon_Modeling.ValidSelection()
	
	on isChecked do
	(
		if Ribbon_Modeling.ValidSelection() then
		(
			curmod = Modpanel.getcurrentObject()
			curmod.showcage
		)
		else false
	)
	
	on execute do 
	(
		with undo off
		(
			curmod = Modpanel.getcurrentObject()
			curmod.showcage = not curmod.showcage
		)
	)
)