	macroScript SmartTargetWeld
	category:"ST3E_Editing"
	toolTip:"OP Smart TargetWeld "
	ButtonText:"SmartTargetWeld"
	
	---------------------------------------------------------------------
	-- simple script to always jump to vertex level automatically when one wants to Target Weld
	---------------------------------------------------------------------
(
	On IsEnabled Return Filters.Is_EPoly()
	On IsVisible Return Filters.Is_EPoly()

	On Execute Do 
	(
		subobjectlevel = 1
		editpolyModOrObj = Filters.GetModOrObj()
		editpolyModOrObj.toggleCommandMode #Weld
	)
)
