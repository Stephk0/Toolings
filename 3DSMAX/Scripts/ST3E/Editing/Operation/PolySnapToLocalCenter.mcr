-------------------------------------
-- Snap selected vertes / edges to its local center
-- requires scripts\ST3E\lib\PolySnapToLocalCenter.ms
-------------------------------------
-------------------------
-- todo: support for splines
-------------------------

macroScript SnapToLocalCenterX
	category:"ST3E_Editing"
	toolTip:"OP Snap To Local Center X"
	ButtonText:"Center X"
	(
	
		--global CenterOnAxis, X
		--on isEnabled return (Filters.Is_EPolySpecifyLevel #{1..4} or (Filters.Is_EditSpline() and subObjectLevel != 0))
		
		on execute do 
		(
			--include "$scripts\ST3E\lib\PolySnapToLocalCenter.ms"
			CenterOnAxis (X)
		)
	)
	
	macroScript SnapToLocalCenterY
	category:"ST3E_Editing"
	toolTip:"OP Snap To Local Center Y"
	ButtonText:"Center Y"
	(
		--global CenterOnAxis, Y	
		--on isEnabled return (Filters.Is_EPolySpecifyLevel #{1..4} or (Filters.Is_EditSpline() and subObjectLevel != 0))
		
		on execute do
		(
			--include "$scripts\ST3E\lib\PolySnapToLocalCenter.ms"
			CenterOnAxis (Y)
		)
	)

	macroScript SnapToLocalCenterZ
	category:"ST3E_Editing"
	toolTip:"OP Snap To Local Center Z"
	ButtonText:"Center Z"
	(
		--global CenterOnAxis, Z
		--on isEnabled return (Filters.Is_EPolySpecifyLevel #{1..4} or (Filters.Is_EditSpline() and subObjectLevel != 0))
		
		on execute do
		(
			--include "$scripts\ST3E\lib\PolySnapToLocalCenter.ms"
			CenterOnAxis (Z)
		)
	)

	