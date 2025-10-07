macroScript AddModifier_Symmetry
	category:"ST3E_ModifierButtons"
	toolTip:"Add Modifier Symmetry"
	ButtonText:"Symmetry"
(
	modPanel.addModToSelection (symmetry ()) ui:on
)

macroScript AddModifier_Symmetry2022
	category:"ST3E_ModifierButtons"
	toolTip:"Add Modifier Symmetry X 2022"
	ButtonText:"Symmetry X"
(
	local symMod = symmetry ()
	symMod.PlanarZ = off
	symMod.PlanarY = off
	symMod.PlanarX = on
	modPanel.addModToSelection (symMod) ui:on
)

macroScript AddModifier_SymmetryCenter
	category:"ST3E_ModifierButtons"
	toolTip:"Add Modifier Centered Symmetry"
	ButtonText:"Symmetry Center"
(
	
	on isEnabled return mcrUtils.ValidMod symmetry
	on execute do 
	(
		symMod = symmetry()		
		for selectedObject in selection do
		(
			
			currentMod = modPanel.getCurrentObject()  
			if (superclassof currentMod == modifier) then 
			(
				modIndex = modPanel.getModifierIndex selectedObject currentMod
				addModifier selectedObject symMod before:(modIndex-1)
			)
			else addModifier selectedObject symMod before:selectedObject.modifiers.count

		)
		
		if selection.count == 1 then modPanel.setCurrentObject symMod
	)
		
)


macroScript AddModifier_Mirror
	category:"ST3E_ModifierButtons"
	toolTip:"Add Modifier Mirror"
	ButtonText:"Mirror"
(
	modPanel.addModToSelection (mirror ()) ui:on
)

macroScript AddModifier_VolumeSelect
	category:"ST3E_ModifierButtons"
	toolTip:"Add Modifier VolumeSelect"
	ButtonText:"VolumeSelect"
(
	modPanel.addModToSelection (VolumeSelect ()) ui:on
)

macroScript AddModifier_DeleteMesh
	category:"ST3E_ModifierButtons"
	toolTip:"Add Modifier DeleteMesh"
	ButtonText:"DeleteMesh"
(
	modPanel.addModToSelection (DeleteMesh ()) ui:on
)

macroScript AddModifier_Chamfer
	category:"ST3E_ModifierButtons"
	toolTip:"Add Modifier Chamfer"
	ButtonText:"Chamfer"
(
	modPanel.addModToSelection (Chamfer ()) ui:on
)

macroScript AddModifier_Editable_mesh
	category:"ST3E_ModifierButtons"
	toolTip:"Add Modifier Editable_mesh"
	ButtonText:"Editable_mesh"
(
	modPanel.addModToSelection (Edit_Mesh ()) ui:on
)

macroScript AddModifier_Edit_Poly
	category:"ST3E_ModifierButtons"
	toolTip:"Add Modifier Edit_Poly (Face Mode)"
	ButtonText:"Edit_Poly"
(
	on execute do
	(
		 AddMod EditPolyMod
		 subObjectLevel = 4
	)
	on isEnabled return mcrUtils.ValidMod EditPolyMod
)



macroScript AddModifier_Push
	category:"ST3E_ModifierButtons"
	toolTip:"Add Modifier Push"
	ButtonText:"Push"
(
	modPanel.addModToSelection (Push ()) ui:on
)

macroScript AddModifier_SmoothModifier
	category:"ST3E_ModifierButtons"
	toolTip:"Add Modifier SmoothModifier"
	ButtonText:"SmoothModifier"
(
	modPanel.addModToSelection (SmoothModifier ()) ui:on
)

macroScript AddModifier_Relax
	category:"ST3E_ModifierButtons"
	toolTip:"Add Modifier Relax"
	ButtonText:"Relax"
(
	modPanel.addModToSelection (Relax ()) ui:on
)

macroScript AddModifier_ProOptimizer
	category:"ST3E_ModifierButtons"
	toolTip:"Add Modifier ProOptimizer"
	ButtonText:"ProOptimizer"
(
	modPanel.addModToSelection (ProOptimizer ()) ui:on
)

macroScript AddModifier_Optimize
	category:"ST3E_ModifierButtons"
	toolTip:"Add Modifier Optimize"
	ButtonText:"Optimize"
(
	modPanel.addModToSelection (optimize ()) ui:on
)

macroScript AddModifier_XForm
	category:"ST3E_ModifierButtons"
	toolTip:"Add Modifier XForm"
	ButtonText:"XForm"
(
	modPanel.addModToSelection (XForm ()) ui:on
)

macroScript AddModifier_STL_Check
	category:"ST3E_ModifierButtons"
	toolTip:"Add Modifier STL_Check"
	ButtonText:"STL_Check"
(
	modPanel.addModToSelection (STL_Check ()) ui:on
)


macroScript AddModifier_DataChannelModifier
	category:"ST3E_ModifierButtons"
	toolTip:"Add Modifier DataChannelModifier"
	ButtonText:"DataChannelModifier"
(
	modPanel.addModToSelection (DataChannelModifier ()) ui:on
)

macroScript AddModifier_Clone
	category:"ST3E_ModifierButtons"
	toolTip:"Add Modifier Clone "
	ButtonText:"Clone"
(
	modPanel.addModToSelection (clone ()) ui:on
)

macroScript AddModifier_Quad_Chamfer
	category:"ST3E_ModifierButtons"
	toolTip:"Add Modifier Quad_Chamfer"
	ButtonText:"Quad_Chamfer"
(
	modPanel.addModToSelection (Quad_Chamfer ()) ui:on
)

macroScript AddModifier_QuadCap
	category:"ST3E_ModifierButtons"
	toolTip:"Add Modifier QuadCap "
	ButtonText:"QuadCap"
(
	modPanel.addModToSelection (Quad_Cap_Pro ()) ui:on
)


macroScript AddModifier_Materialmodifier
	category:"ST3E_ModifierButtons"
	toolTip:"Add Modifier Materialmodifier"
	ButtonText:"Materialmodifier"
(
	modPanel.addModToSelection (Materialmodifier ()) ui:on
)

macroScript AddModifier_Edit_Spline
	category:"ST3E_ModifierButtons"
	toolTip:"Add Modifier Edit_Spline "
	ButtonText:"Edit_Spline"
(
	on execute do AddMod Edit_Spline
	on isEnabled return mcrUtils.ValidMod Edit_Spline

	--modPanel.addModToSelection (Edit_Spline ()) ui:on
)

macroScript AddModifier_SplineOffset
	category:"ST3E_ModifierButtons"
	toolTip:"Add Modifier SplineOffset"
	ButtonText:"SplineOffset"
(
	modPanel.addModToSelection (SplineOffset ()) ui:on
)






