macroScript FlowUnconstrained
	category:"ST3E_Editing"
	toolTip:"Flow Unconstrained"
	ButtonText:"FlowUnconstrained"
	(
		-----------------------------------------------------------------------
		-- Flow Unconstrained
		-----------------------------------------------------------------------
		-- store edit poly constraint, disable contstraint apply flow, reset constrain to previousl one
		-----------------------------------------------------------------------

		on isEnabled return (PolyBoost.ValidEPmacro() and subobjectlevel != 0 and subobjectlevel < 4)
		
		on execute do
		(
			local currentMod = modPanel.getCurrentObject()
			local constraintMode = currentMod.constrainType
			currentMod.constrainType = 0

			if subobjectlevel == 2 then PolyToolsModeling.SetFlow false
			else if subobjectlevel == 1 do PolyToolsModeling.SetFlowVertex()
			currentMod.constrainType = constraintMode
		
		)

	)		

