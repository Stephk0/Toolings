	---------------------------------------------------------------------
	-- Constrains without undo for uninterupted modelling flow
	---------------------------------------------------------------------
	
	macroScript ConstrainToggleEN
	category:"ST3E_RulersHelpers"
	toolTip:"Constrain Toggle Edge > Normal (No Undo)"
	ButtonText:"ConstraintToggleEN"
	
(
	on isEnabled do Filters.Is_EPoly()
	
	on execute do 
	(
		undo off
		(
			curmod = Modpanel.getcurrentObject()

			-- if then else monster because we skip f
			if (curmod.constrainType > 1) then curmod.constrainType = 0
			else if (curmod.constrainType == 0) then curmod.constrainType = 1
			else if (curmod.constrainType == 1) then curmod.constrainType = 3
		)
		
	)
)

macroScript ConstrainToggleFull
category:"ST3E_RulersHelpers"
toolTip:"Constrain Toggle Edge > Face > Normal (No Undo)"
ButtonText:"ConstraintToggleEFN"

(
	on isEnabled do Filters.Is_EPoly()

	on execute do 
	(
		undo off
		(
			curmod = Modpanel.getcurrentObject()

			if (curmod.constrainType == 3) then curmod.constrainType = 0
			else curmod.constrainType += 1
		)
		
	)
)

	macroScript ConstrainEdgeNoUndo
	category:"ST3E_RulersHelpers"
	toolTip:"Constrain Edge Toggle (No Undo)"
	ButtonText:"ConstraintEdgeNoUndo"
	
(
	on isEnabled do Filters.Is_EPoly()
	
	on isChecked do
	(
		if (Filters.Is_EPoly() ) then
		(		
			curmod = Modpanel.getcurrentObject()
			(curmod.constrainType == 1)
		)
		else
		(
			false
		)
	)
	
	on execute do 
	(
		undo off
		(
			curmod = Modpanel.getcurrentObject()
			--toggleable
			if (curmod.constrainType != 1) then curmod.constrainType = 1
			else curmod.constrainType = 0
		)
		
	)
)

macroScript ConstrainFaceNoUndo
category:"ST3E_RulersHelpers"
toolTip:"Constrain Face Toggle (No Undo)"
ButtonText:"ConstrainFaceNoUndo"

(
	on isEnabled do Filters.Is_EPoly()

	on isChecked do
	(
		if (Filters.Is_EPoly() ) then
		(		
			curmod = Modpanel.getcurrentObject()
			(curmod.constrainType == 2)
		)
		else
		(
			false
		)
	)

	on execute do 
	(
		undo off
		(
			curmod = Modpanel.getcurrentObject()
			--toggleable
			if (curmod.constrainType != 2) then curmod.constrainType = 2
			else curmod.constrainType = 0
		)
		
	)
)
macroScript ConstrainNormalNoUndo
category:"ST3E_RulersHelpers"
toolTip:"Constrain Normal Toggle (No Undo)"
ButtonText:"ConstrainNormalNoUndo"

(
	on isEnabled do Filters.Is_EPoly()

	on isChecked do
	(
		if (Filters.Is_EPoly() ) then
		(		
			curmod = Modpanel.getcurrentObject()
			(curmod.constrainType == 3)
		)
		else
		(
			false
		)
	)

	on execute do 
	(
		undo off
		(
			curmod = Modpanel.getcurrentObject()
			--toggleable
			if (curmod.constrainType != 3) then curmod.constrainType = 3
			else curmod.constrainType = 0
		)
		
	)
)
