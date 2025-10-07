macroScript ChamferNoSmoothing
	category:"ST3E_Editing"
	toolTip:"Chamfer Options"
	ButtonText:"Chamfer"
(
	---------------------------------------------------------------------------------
	-- Workaround for the annoyance of the new chamfer window / algorythm defaulting to shitty mittering type and resmoothing your model if you miss unticking the smooth box
	---------------------------------------------------------------------------------
	-- TODO: Add support for chamfer mode in non dialog mode
	-- NOTE: Possibly not needed in later 3ds max version as this was a specfic annoyance in max 2021
	--

	---------------------------------------------------------------------------------
	-- variables, changese these to set your defaults
	---------------------------------------------------------------------------------
	
	-- mitering type: 0 quad, 1 tri, 2 uniform, 3 radial, 4 patch
	miteringDefault = 0

	-- segments default 
	segmentsDefault = 0
	
	-- smooth default
	smoothDefault = false

	On IsEnabled Return Filters.Is_EPoly()
	On IsVisible Return Filters.Is_EPoly()

	On Execute Do (

		local A = modPanel.getCurrentObject()
		
		A.edgeChamferMiteringType = miteringDefault
		A.edgeChamferSegments = segmentsDefault
		A.edgeChamferSmooth = smoothDefault
		A.chamferVertexSmooth = smoothDefault
		A.chamferVertexSegments = segmentsDefaults    
			
		macros.run "Ribbon - Modeling" "EPoly_ChamferOptions"
			
	)

)
