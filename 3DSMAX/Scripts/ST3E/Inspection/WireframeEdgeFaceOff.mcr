---------------------------------------------------------------------------------
-- Toggle Wireframe and Display Edged Faces so that they make sense 
-- assuming edged faces is level 1 inspection on topology, wireframe mode is level 2 to get the surrounding topology context it made sense to me to auto disable level 1 if level 2 is disabled and vice versa
-- TODO add support for old viewport from >max 2017
---------------------------------------------------------------------------------


macroScript WireframeEdgeFaceToggle
	category:"ST3E_Inspection"
	toolTip:"Toggle Wireframe and Edged Faces (Replace Wireframe Mode)"
	ButtonText:"Toggle Wireframe and Edged Faces"
(

	global vs = NitrousGraphicsManager.GetActiveViewportSetting()
	--todo: add support for older max versions
	/*
	edgeMode = viewport.SetShowEdgeFaces
	*/

	on isChecked return viewport.GetShowEdgeFaces()
			
	on execute do
	(
		if (viewport.GetShowEdgeFaces() ==  true) then
		(
			-- wireframe mode off
			viewport.SetShowEdgeFaces (false)

			-- edged faces mode off
			vs.SelectedEdgedFacesEnabled = false
		)
		else if (viewport.GetShowEdgeFaces() == false) then
		(
			-- wireframe mode on
			viewport.SetShowEdgeFaces (true)
			-- edged faces mode off
			vs.SelectedEdgedFacesEnabled = false
		)
	)
)

macroScript EdgeFaceWireframeToggle
	category:"ST3E_Inspection"
	toolTip:"Toggle Edged Faces and Wireframe Mode (Replace Display Edged Faces Only)"
	ButtonText:"Toggle Edged Faces and Wireframe Mode"

(
	-- TODO add support for old viewport from >max 2017
	global vs = NitrousGraphicsManager.GetActiveViewportSetting()

	on isChecked return vs.SelectedEdgedFacesEnabled
			
	on execute do
	(

		if (vs.SelectedEdgedFacesEnabled == true) then vs.SelectedEdgedFacesEnabled = false

		else if (vs.SelectedEdgedFacesEnabled == false) then
		(
			-- wireframe mode off
			viewport.SetShowEdgeFaces (false)
			--  edged faces on
			vs.SelectedEdgedFacesEnabled = true
		)
		redrawViews()
	)
)
