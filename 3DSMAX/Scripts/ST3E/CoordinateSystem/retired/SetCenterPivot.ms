-----------------------------------------------------------------------
-- set the pivot via hotkey/toolbar button instead of the dropdown
-------------------------------------------------------------------

macroScript CenterPivotTransform
	category:"StephkoCustom"
	toolTip:"Use Transform Center"
	ButtonText:"PivotTransform"
(	
	toolMode.transformCenter()
	
)

macroScript CenterPivotPivot
	category:"StephkoCustom"
	toolTip:"Use Pivot Point Center"
	ButtonText:"PivotPoint"
(	
	toolMode.pivotCenter()
	
)

macroScript CenterPivotSelection
	category:"StephkoCustom"
	toolTip:"Use Selection Center"
	ButtonText:"PivotSelection"
(	
	toolMode.selectionCenter()
	
)

