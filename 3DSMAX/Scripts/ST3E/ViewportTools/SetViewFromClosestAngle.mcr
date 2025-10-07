macroScript SetViewFromClosestAngle
	category:"ST3E_ViewportTools"
	toolTip:"Set View From Closest Angle / Perspective Toggle"
	ButtonText:"ViewClosestAnglePerps"
(

	local viewTm
	local viewDir

	-- toggle between persp and specific view if the same is active. one button now rules all viewmodes, no need for another button to toggle persp
	fn setViewPerpToggle viewtype = 
	(
		if viewtype == viewport.getType() then viewport.setType #view_persp_user
		else 
		(
			viewport.setType viewtype
			max zoomext sel all
		)
	)
	
	on execute do 
	(
		viewTm = Inverse(getViewTM())
		-- The Z axis of this matrix is the view direction.
		viewDir = -viewTm.row3

		if 		viewDir.x > 0.5 	then setViewPerpToggle #view_left
		else if viewDir.x < -0.5 	then setViewPerpToggle #view_right
		else if viewDir.y > 0.5 	then setViewPerpToggle #view_front 
		else if viewDir.y < -0.5 	then setViewPerpToggle #view_back 
		else if viewDir.z > 0.5 	then setViewPerpToggle #view_bottom
		else if viewDir.z < -0.5 	then setViewPerpToggle #view_top  
	)
)