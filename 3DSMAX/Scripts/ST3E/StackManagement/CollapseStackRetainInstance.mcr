macroScript CollapseStackRetainInstance
	category:"ST3E_StackManagement"
	toolTip:"Collapse Stack on Selection and retain Instances"
	ButtonText:"Collapse Stack"
	(
		-----------------------------------------------------------------------
		-- Collapse Stack on Selection and retain Instances
		-----------------------------------------------------------------------
		-- to retain instance you have to right click onto the modifer and choose collapse To. This script helps to do this on multiple objects
		-----------------------------------------------------------------------
		
		on execute do for obj in selection do maxOps.CollapseNodeTo obj 1 off

	)		
