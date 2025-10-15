-- requires scripts\ST3E\lib\PolySelectExtended.ms

macroScript PolySelectNgons
	category:"ST3E_Select"
	toolTip:"Poly Select Ngons"	
	ButtonText:"Select Ngons"
	(
		On IsEnabled Return Filters.Is_EPoly()
		On IsVisible Return Filters.Is_EPoly()
		On Execute Do
		(
			subObjectLevel = 4
			PolyToolsSelect.NumericFace 4 3 false
		)

	)

macroScript PolySelectTris
	category:"ST3E_Select"
	toolTip:"Poly Select Triangles"	
	ButtonText:"Select Tris"
	(
		On IsEnabled Return Filters.Is_EPoly()
		On IsVisible Return Filters.Is_EPoly()
		On Execute Do 		
		(
			subObjectLevel = 4
			PolyToolsSelect.NumericFace 3 1 false
		)
	)


macroScript PolySelectHalfX
	category:"ST3E_Select"
	toolTip:"Poly Select Half X"	
	ButtonText:"Select Half X"
	(
		On IsEnabled Return Filters.Is_EPoly()
		On IsVisible Return Filters.Is_EPoly()
		On Execute Do
		(
			subObjectLevel = 4
			PolyToolsSelect.Half 1 false false
		)
	)
	
macroScript PolySelectHalfY
	category:"ST3E_Select"
	toolTip:"Poly Select Half Y"
	ButtonText:"Select Half Y"
	(
		On IsEnabled Return Filters.Is_EPoly()
		On IsVisible Return Filters.Is_EPoly()
		On Execute Do 		
		(
			subObjectLevel = 4
			PolyToolsSelect.Half 2 false false
		)
	)

macroScript PolySelectHalfZ
	category:"ST3E_Select"
	toolTip:"Poly Select Half Z"
	ButtonText:"Select Half Z"
	(
		On IsEnabled Return Filters.Is_EPoly()
		On IsVisible Return Filters.Is_EPoly()
		On Execute Do
		(
			subObjectLevel = 4
			PolyToolsSelect.Half 3 false false
		)
	)

macroScript PolySelectByAngle
	category:"ST3E_Select"
	toolTip:"Poly/UV Select By Angle"	
	ButtonText:"Select °"
	(
		include "$scripts\ST3E\lib\PolySelectExtended.ms"
		On IsEnabled Return (Filters.Is_EPoly() OR ClassOf (modPanel.getCurrentObject()) == Unwrap_UVW)
		On IsVisible Return (Filters.Is_EPoly() OR ClassOf (modPanel.getCurrentObject()) == Unwrap_UVW)
		On IsChecked Do SelectByAngleFunctions.EvaluateMode()
		On Execute Do SelectByAngleFunctions.SelectByAngleToggle()
	)

macroScript PolySelectByAngle45
	category:"ST3E_Select"
	toolTip:"Poly/UV Select By Angle 45"	
	ButtonText:"Select °45"
	(
		selectAngle = 45
		include "$scripts\ST3E\lib\PolySelectExtended.ms"

		On IsEnabled Return (Filters.Is_EPoly() OR ClassOf (modPanel.getCurrentObject()) == Unwrap_UVW)
		On IsVisible Return (Filters.Is_EPoly() OR ClassOf (modPanel.getCurrentObject()) == Unwrap_UVW)
		On IsChecked Do SelectByAngleFunctions.EvaluateAngle (selectAngle)
		On Execute Do SelectByAngleFunctions.SelectByAngleToggleAngle (selectAngle)
	)

macroScript PolySelectByAngle25
	category:"ST3E_Select"
	toolTip:"Poly/UV Select By Angle 25"
	ButtonText:"Select °25"
	(

		selectAngle = 25
		include "$scripts\ST3E\lib\PolySelectExtended.ms"

		On IsEnabled Return (Filters.Is_EPoly() OR ClassOf (modPanel.getCurrentObject()) == Unwrap_UVW)
		On IsVisible Return (Filters.Is_EPoly() OR ClassOf (modPanel.getCurrentObject()) == Unwrap_UVW)
		On IsChecked Do SelectByAngleFunctions.EvaluateAngle (selectAngle)
		On Execute Do SelectByAngleFunctions.SelectByAngleToggleAngle (selectAngle)

	)

	macroScript PolySelectByAngle10
	category:"ST3E_Select"
	toolTip:"Poly/UV Select By Angle 10"
	ButtonText:"Select °10"
	(

		selectAngle = 10
		include "$scripts\ST3E\lib\PolySelectExtended.ms"
		
		On IsEnabled Return (Filters.Is_EPoly() OR ClassOf (modPanel.getCurrentObject()) == Unwrap_UVW)
		On IsVisible Return (Filters.Is_EPoly() OR ClassOf (modPanel.getCurrentObject()) == Unwrap_UVW)
		On IsChecked Do SelectByAngleFunctions.EvaluateAngle (selectAngle)
		On Execute Do SelectByAngleFunctions.SelectByAngleToggleAngle (selectAngle)
	)
	
	macroScript PolySelectByAngle5
	category:"ST3E_Select"
	toolTip:"Poly/UV Select By Angle 5"
	ButtonText:"Select °5"
	(

		selectAngle = 5
		include "$scripts\ST3E\lib\PolySelectExtended.ms"

		On IsEnabled Return (Filters.Is_EPoly() OR ClassOf (modPanel.getCurrentObject()) == Unwrap_UVW)
		On IsVisible Return (Filters.Is_EPoly() OR ClassOf (modPanel.getCurrentObject()) == Unwrap_UVW)
		On IsChecked Do SelectByAngleFunctions.EvaluateAngle (selectAngle)
		On Execute Do SelectByAngleFunctions.SelectByAngleToggleAngle (selectAngle)
	)



		

