/*
Script to enable modifier buttons outside the command modifer panel (hotkeys, quadmenu, flaoting windows, etc)
*/

/*
SimpleMesh Mods
*/

macroScript AddModifier_ShiftSG
	category:"ST3E_ModifierButtons"
	toolTip:"Add Modifier Shift Smoothing Groups"
	ButtonText:"Shift SG"
(
	on execute do AddMod ShiftSGs
	on isEnabled return mcrUtils.ValidMod ShiftSGs
)

macroScript AddModifier_ShiftMatID
	category:"ST3E_ModifierButtons"
	toolTip:"Add Modifier Shift Material IDs"
	ButtonText:"Shift MatID"
(
	on execute do AddMod ShiftMatIDs
	on isEnabled return mcrUtils.ValidMod ShiftMatIDs
)

macroScript AddModifier_SplitMesh
	category:"ST3E_ModifierButtons"
	toolTip:"Add Modifier Split Mesh"
	ButtonText:"Split Mesh"
(
	on execute do AddMod SplitMesh
	on isEnabled return mcrUtils.ValidMod SplitMesh
)

/*
Simple Mods
*/

macroScript AddModifier_Cylindrify
	category:"ST3E_ModifierButtons"
	toolTip:"Add Modifier Simple Cylindrify "
	ButtonText:"Cylindrify"
(
	on execute do AddMod simpleCylindrify
	--on isEnabled return mcrUtils.ValidMod cylindrify
)

macroScript AddModifier_Boxify
	category:"ST3E_ModifierButtons"
	toolTip:"Add Modifier Simple Boxify"
	ButtonText:"Boxify"
(
	on execute do AddMod simpleBoxify
	--on isEnabled return mcrUtils.ValidMod boxify
)

macroScript AddModifier_Scale
	category:"ST3E_ModifierButtons"
	toolTip:"Add Modifier Simple Scale"
	ButtonText:"Scale"
(
	on execute do AddMod simpleScale
	--on isEnabled return mcrUtils.ValidMod scale2
)

macroScript AddModifier_Offset
	category:"ST3E_ModifierButtons"
	toolTip:"Add Modifier Simple Offset"
	ButtonText:"Offset"
(
	on execute do AddMod simpleOffset
	--on isEnabled return mcrUtils.ValidMod offset
)

macroScript AddModifier_Spherify
	category:"ST3E_ModifierButtons"
	toolTip:"Add Modifier Simple Spherify"
	ButtonText:"Spherify"
(
	on execute do AddMod simpleSpherify
	--on isEnabled return mcrUtils.ValidMod spherify2
)

/*
Edit Poly Scripted Mods
--mcrUtils.ValidMod has weird perfomance issues
*/

macroScript AddModifier_PolyDetach
	category:"ST3E_ModifierButtons"
	toolTip:"Add Modifier Poly Detach"
	ButtonText:"PolyDetach"
(
	on execute do AddMod PolyDetach
	--on isEnabled return mcrUtils.ValidMod PolyDetach
)

macroScript AddModifier_OutlineFaces
	category:"ST3E_ModifierButtons"
	toolTip:"Add Modifier Poly Outline Faces "
	ButtonText:"PolyOutline"
(
	on execute do AddMod PolyOutlineFaces
	--modPanel.addModToSelection (OutlineFaces ()) ui:on
)

macroScript AddModifier_InsetFaces
	category:"ST3E_ModifierButtons"
	toolTip:"Add Modifier Poly Inset Faces"
	ButtonText:"PolyInset"
(
	on execute do AddMod PolyInsetFaces
	--modPanel.addModToSelection (InsetFaces ()) ui:on
)


macroScript AddModifier_PolyBevel
	category:"ST3E_ModifierButtons"
	toolTip:"Add Modifier Poly Bevel"
	ButtonText:"PolyBevel"
(
	on execute do AddMod PolyBevel
	--on isEnabled return mcrUtils.ValidMod PolyBevel
)
macroScript AddModifier_PolyExtrude
	category:"ST3E_ModifierButtons"
	toolTip:"Add Modifier Poly Extrude"
	ButtonText:"PolyExtrude"
(
	on execute do AddMod PolyExtrude
	--on isEnabled return mcrUtils.ValidMod PolyExtrude
)

macroScript AddModifier_PolyExtrudeAlongSpline
	category:"ST3E_ModifierButtons"
	toolTip:"Add Modifier Poly Extrude Along Spline"
	ButtonText:"PolyExtrudeAlongSpline"
(
	on execute do AddMod PolyExtrudeAlongSpline
	--on isEnabled return mcrUtils.ValidMod PolyExtrudeAlongSpline
)

macroScript AddModifier_PolyAutosmooth
	category:"ST3E_ModifierButtons"
	toolTip:"Add Modifier Poly Autosmooth"
	ButtonText:"PolyAutosmooth"
(
	on execute do AddMod PolyAutoSmooth
	--on isEnabled return mcrUtils.ValidMod PolyAutoSmooth
)

macroScript AddModifier_PolyClone
	category:"ST3E_ModifierButtons"
	toolTip:"Add Modifier Poly Clone"
	ButtonText:"PolyClone"
(
	on execute do AddMod PolyClone
	--on isEnabled return mcrUtils.ValidMod PolyClone
)

macroScript AddModifier_PolyDelete
	category:"ST3E_ModifierButtons"
	toolTip:"Add Modifier Poly Delete"
	ButtonText:"PolyDelete"
(
	on execute do AddMod PolyDelete
	--on isEnabled return mcrUtils.ValidMod PolyDelete
)


