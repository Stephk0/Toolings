/*
All the loop tools like in vanilla, except the constrainst get disabled during the op so they always work the same
*/


macroScript LoopToolsRelaxLoopUnconstrained
	category:"ST3E_Editing"
	toolTip:"OP LoopTools Relax Unconstrained"
	ButtonText:"LoopToolsRelaxUnconstrained"
	(

		-----------------------------------------------------------------------
		-- Relax Loop Unconstrained
		-----------------------------------------------------------------------
		-- relax loop from loop tools except it doesnt autoLoop but only applies to selection and keeps constraints
		-- Not needed anymore, Relax Loops works just fine
		-----------------------------------------------------------------------
		on isEnabled return (PolyBoost.ValidEPmacro() and (subobjectlevel == 2 or subobjectlevel == 3))
		on execute do
		(
		
			local currentMod = modPanel.getCurrentObject()
			local constraintMode = currentMod.constrainType
			currentMod.constrainType = 0
			PolyToolsModeling.RelaxLoop false
			currentMod.constrainType = constraintMode

		) 
	)

macroScript LoopToolsCenter
	category:"ST3E_Editing"
	toolTip:"OP LoopTools Center"
	ButtonText:"LoopToolsCenter"
	(

		-----------------------------------------------------------------------
		-- Center Loop
		-----------------------------------------------------------------------
		-- center loop from loop tools except it doesnt autoLoop but only applies to selection

		-----------------------------------------------------------------------
		on isEnabled return (PolyBoost.ValidEPmacro() and (subobjectlevel == 2 or subobjectlevel == 3))
		on execute do PolyToolsModeling.CenterLoop false
	)

	macroScript LoopToolsCenterUnconstrained
	category:"ST3E_Editing"
	toolTip:"OP LoopTools Center Unconstrained"
	ButtonText:"LoopToolsCenterUnconstrained"
	(

		-----------------------------------------------------------------------
		-- Center Loop unconstrained
		-----------------------------------------------------------------------
		-- center loop from loop tools except it doesnt autoLoop but only applies to selection, also it disregards constraints

			-----------------------------------------------------------------------
		on isEnabled return (PolyBoost.ValidEPmacro() and (subobjectlevel == 2 or subobjectlevel == 3))
		on execute do
		(
		
			local currentMod = modPanel.getCurrentObject()
			local constraintMode = currentMod.constrainType
			currentMod.constrainType = 0
			PolyToolsModeling.CenterLoop false
			currentMod.constrainType = constraintMode

		) 
	)

	macroScript LoopToolsStraightenUnconstrained
	category:"ST3E_Editing"
	toolTip:"OP LoopTools Straighten Unconstrained"
	ButtonText:"LoopToolsStraightenUnconstrained"
	(

		-----------------------------------------------------------------------
		-- Straighten Unconstrained
		-----------------------------------------------------------------------
		-- straighten that disregards constraints

		-----------------------------------------------------------------------
	on isEnabled return (PolyBoost.ValidEPmacro() and (subobjectlevel == 2 or subobjectlevel == 3))
	on execute do
	(
	
		local currentMod = modPanel.getCurrentObject()
		local constraintMode = currentMod.constrainType
		currentMod.constrainType = 0
		PolyToolsModeling.StraightLoop false false
		currentMod.constrainType = constraintMode

	) 
	)

	macroScript LoopToolsStraightenUnconstrainedEvenSpacing
	category:"ST3E_Editing"
	toolTip:"OP LoopTools Straighten Unconstrained Even Spacing"
	ButtonText:"LoopToolsStraightenUnconstrainedEvenSpacing"
	(

		-----------------------------------------------------------------------
		-- Straighten Unconstrained even spacing
		-----------------------------------------------------------------------
		-- straighten that disregards constraints

		-----------------------------------------------------------------------
	on isEnabled return (PolyBoost.ValidEPmacro() and (subobjectlevel == 2 or subobjectlevel == 3))
	on execute do
	(
	
		local currentMod = modPanel.getCurrentObject()
		local constraintMode = currentMod.constrainType
		currentMod.constrainType = 0
		PolyToolsModeling.StraightLoop false true
		currentMod.constrainType = constraintMode

	) 
	)



		

