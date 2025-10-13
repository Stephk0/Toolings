/*
TODO: fix button text, EpolySpecifcy level could be used
*/

macroScript QuickSelectDotRing2
category:"ST3E_Select"
toolTip:"Dot Ring 2nds"
buttontext: "|.|.|.|.|.|"
autoUndoEnabled:false
(
	on isEnabled return (PolyBoost.ValidEPmacro() and (subobjectlevel == 2 or subobjectlevel == 3))
	on execute do PolytoolsSelect.DotRing 1
)

macroScript QuickSelectDotRing3
category:"ST3E_Select"
toolTip:"Dot Ring 3rds"
buttontext: "|..|..|..|."
autoUndoEnabled:false
(
	on isEnabled return (PolyBoost.ValidEPmacro() and (subobjectlevel == 2 or subobjectlevel == 3))
	on execute do PolytoolsSelect.DotRing 2
)

macroScript QuickSelectDotRing4
category:"ST3E_Select"
toolTip:"Dot Ring 4ths"
buttontext: "|...|...|.."
autoUndoEnabled:false
(
	on isEnabled return (PolyBoost.ValidEPmacro() and (subobjectlevel == 2 or subobjectlevel == 3))
	on execute do PolytoolsSelect.DotRing 3
)

macroScript QuickSelectDotRing5
category:"ST3E_Select"
toolTip:"Dot Ring 5ths"
buttontext: "|....|....|"
autoUndoEnabled:false
(
	on isEnabled return (PolyBoost.ValidEPmacro() and (subobjectlevel == 2 or subobjectlevel == 3))
	on execute do PolytoolsSelect.DotRing 4
)

macroScript QuickSelectDotRing5
category:"ST3E_Select"
toolTip:"Dot Ring 6ths"
buttontext: "|.....|...."
autoUndoEnabled:false
(
	on isEnabled return (PolyBoost.ValidEPmacro() and (subobjectlevel == 2 or subobjectlevel == 3))
	on execute do PolytoolsSelect.DotRing 5
)

macroScript QuickSelectDotLoop2
category:"ST3E_Select"
toolTip:"Dot Loop 2nds"
buttontext: "- - - - - -"
autoUndoEnabled:false
(
	on isEnabled return (PolyBoost.ValidEPmacro() and (subobjectlevel == 2 or subobjectlevel == 3))
	on execute do PolytoolsSelect.DotLoop 1 false false
)

macroScript QuickSelectDotLoop3
category:"ST3E_Select"
toolTip:"Dot Loop 3rds"
buttontext: "-  -  -  - "
autoUndoEnabled:false
(
	on isEnabled return (PolyBoost.ValidEPmacro() and (subobjectlevel == 2 or subobjectlevel == 3))
	on execute do PolytoolsSelect.DotLoop 2 false false
)

macroScript QuickSelectDotLoop4
category:"ST3E_Select"
toolTip:"Dot Loop 4ths"
buttontext: "-   -   -   "
autoUndoEnabled:false
(
	on isEnabled return (PolyBoost.ValidEPmacro() and (subobjectlevel == 2 or subobjectlevel == 3))
	on execute do PolytoolsSelect.DotLoop 3 false false
)

macroScript QuickSelectDotLoop5
category:"ST3E_Select"
toolTip:"Dot Loop 5ths"
buttontext: "-    -    - "
autoUndoEnabled:false
(
	on isEnabled return (PolyBoost.ValidEPmacro() and (subobjectlevel == 2 or subobjectlevel == 3))
	on execute do PolytoolsSelect.DotLoop 4 false false
)
