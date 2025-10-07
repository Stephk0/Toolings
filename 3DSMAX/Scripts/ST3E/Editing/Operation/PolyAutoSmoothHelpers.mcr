------------------------------------------------------------------------------
-- set smoothing groups quickly by choosing from 15,30,45 etc degrees instead of going thru the commandpanel. retains your custom value in the commandpanel
-- TODO: add custom value option / script something
-------------------------------------------------------------------------------

macroScript AutoSmooth15
	category:"ST3E_Editing"
	toolTip:"OP Auto Smooth 15°"
	ButtonText:"AutoSmooth15"
(
	On IsEnabled Return Filters.Is_EPolySpecifyLevel #{5..6}
	On IsVisible Return Filters.Is_EPolySpecifyLevel #{5..6}

	On Execute Do (
		
			If SubObjectLevel == undefined then Max Modify Mode
			if subobjectlevel < 4 then subobjectlevel = 4
			else (
				local A = Filters.GetModOrObj()
				local prevASValue = A.autoSmoothThreshold
				A.autoSmoothThreshold = 15
				A.ButtonOp #Autosmooth
				A.autoSmoothThreshold = prevASValue
			)
		
	)

)

macroScript AutoSmooth30
	category:"ST3E_Editing"
	toolTip:"OP Auto Smooth 30°"
	ButtonText:"AutoSmooth30"
(
	On IsEnabled Return Filters.Is_EPolySpecifyLevel #{5..6}
	On IsVisible Return Filters.Is_EPolySpecifyLevel #{5..6}

	On Execute Do (
		
			If SubObjectLevel == undefined then Max Modify Mode
			if subobjectlevel < 4 then subobjectlevel = 4
			else (
				local A = Filters.GetModOrObj()
				local prevASValue = A.autoSmoothThreshold
				A.autoSmoothThreshold = 30
				A.ButtonOp #Autosmooth
				A.autoSmoothThreshold = prevASValue
			)
		
	)

)

macroScript AutoSmooth45
	category:"ST3E_Editing"
	toolTip:"OP Auto Smooth 45°"
	ButtonText:"AutoSmooth45"
(
	On IsEnabled Return Filters.Is_EPolySpecifyLevel #{5..6}
	On IsVisible Return Filters.Is_EPolySpecifyLevel #{5..6}

	On Execute Do (
		
			If SubObjectLevel == undefined then Max Modify Mode
			if subobjectlevel < 4 then subobjectlevel = 4
			else (
				local A = Filters.GetModOrObj()
				local prevASValue = A.autoSmoothThreshold
				A.autoSmoothThreshold = 45
				A.ButtonOp #Autosmooth
				A.autoSmoothThreshold = prevASValue
			)
		
	)

)

macroScript AutoSmooth60
	category:"ST3E_Editing"
	toolTip:"OP Auto Smooth 60°"
	ButtonText:"AutoSmooth60"
(
	On IsEnabled Return Filters.Is_EPolySpecifyLevel #{5..6}
	On IsVisible Return Filters.Is_EPolySpecifyLevel #{5..6}

	On Execute Do (
		
			If SubObjectLevel == undefined then Max Modify Mode
			if subobjectlevel < 4 then subobjectlevel = 4
			else (
				local A = Filters.GetModOrObj()
				local prevASValue = A.autoSmoothThreshold
				A.autoSmoothThreshold = 60
				A.ButtonOp #Autosmooth
				A.autoSmoothThreshold = prevASValue
			)
	
	)

)

macroScript AutoSmooth75
	category:"ST3E_Editing"
	toolTip:"OP Auto Smooth 75°"
	ButtonText:"AutoSmooth75"
(
	On IsEnabled Return Filters.Is_EPolySpecifyLevel #{5..6}
	On IsVisible Return Filters.Is_EPolySpecifyLevel #{5..6}

	On Execute Do (
		
			If SubObjectLevel == undefined then Max Modify Mode
			if subobjectlevel < 4 then subobjectlevel = 4
			else (
				local A = Filters.GetModOrObj()
				local prevASValue = A.autoSmoothThreshold
				A.autoSmoothThreshold = 75
				A.ButtonOp #Autosmooth
				A.autoSmoothThreshold = prevASValue
			)
		
	)

)

macroScript AutoSmooth90
	category:"ST3E_Editing"
	toolTip:"OP Auto Smooth 90°"
	ButtonText:"AutoSmooth90"
(
	On IsEnabled Return Filters.Is_EPolySpecifyLevel #{5..6}
	On IsVisible Return Filters.Is_EPolySpecifyLevel #{5..6}

	On Execute Do (
		
			If SubObjectLevel == undefined then Max Modify Mode
			if subobjectlevel < 4 then subobjectlevel = 4
			else (
				local A = Filters.GetModOrObj()
				local prevASValue = A.autoSmoothThreshold
				A.autoSmoothThreshold = 90
				A.ButtonOp #Autosmooth
				A.autoSmoothThreshold = prevASValue
			)
		
	)

)

macroScript AutoSmooth180
	category:"ST3E_Editing"
	toolTip:"OP Auto Smooth 180°"
	ButtonText:"AutoSmooth180"
(
	On IsEnabled Return Filters.Is_EPolySpecifyLevel #{5..6}
	On IsVisible Return Filters.Is_EPolySpecifyLevel #{5..6}

	On Execute Do (
		
			If SubObjectLevel == undefined then Max Modify Mode
			if subobjectlevel < 4 then subobjectlevel = 4
			else (
				local A = Filters.GetModOrObj()
				local prevASValue = A.autoSmoothThreshold
				A.autoSmoothThreshold = 180
				A.ButtonOp #Autosmooth
				A.autoSmoothThreshold = prevASValue
			)
		
	)

)