-----------------------------------------------------------------------
-- Toggle Vertex Color
-----------------------------------------------------------------------
-- Toggle between Vertex colors with hotkey or button

-----------------------------------------------------------------------
-- Usage:
-- place button in toolbar and toggle
-----------------------------------------------------------------------

macroScript ToggleVertexColor
	category:"ST3E_Inspection"
	toolTip:"Toggle Vertex Color None > On > Shaded "
	ButtonText:"Toggle VC"
	(

	on isEnabled return selection.count > 0
	on execute do 
	(

		for object in selection do 
		(
			 -- show VCs
			if not object.showVertexColors then object.showVertexColors = true
			-- show VCs + Shaded
			else if object.showVertexColors and not object.vertexColorsShaded then object.vertexColorsShaded = true 
			--all off
			else if object.showVertexColors and object.vertexColorsShaded do
			(
				object.vertexColorsShaded = false
				object.showVertexColors = false
			) 
	
		)
	
		redrawViews()
	)
	

	
)

