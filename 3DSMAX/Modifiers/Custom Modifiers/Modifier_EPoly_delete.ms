/*
Poly Delete Modifier, retains Edge Crease and Poly Specific values unlike DeleteMesh
Only Works in max 2017+, extends Edit Poly interface, based on example from http://www.scriptspot.com/3ds-max/scripts/extrudeinsetoutline-faces-modifiers by Vojtech Cada (big thanks!)
by Stephan Viranyi https://www.artstation.com/stephko
Feel free to share and extend to your wishes and msg me for any questions or feedback at stephko@viranyi.de
*/

plugin modifier PolyDelete
	name:"Poly Delete"
	classID:#(0x43f1b987, 0x10dcc16f)
	extends:Edit_Poly
	replaceUI:on
(
	local owner
	local updateHandler

	fn initUpdate node =
	(
		this.owner = node
		this.updateHandler =
			when geometry this.owner changes do
				if isValidObj (local obj = modPanel.getCurrentObject()) do
					notifyDependents obj partIDmsg:#display
	)
	
	
	on create do
	(
		delegate.animationMode = 1
		delegate.useStackSelection = on
		delegate.setEPolySelLevel #Face
		delegate.setOperation #DeleteFace
	)

	on load do initUpdate (refs.dependentNodes this)[1]
	
	on attachedToNode node do
		if isValidNode node then initUpdate node
		else if this.updateHandler != undefined do deleteChangeHandler this.updateHandler
	
	rollout header "How to use"
	(
		edittext 'HowToUse' text:"Delete selected Poly Faces. Edge Weight/Crease are retained unlike DeleteMesh" readOnly:true height:80 width:150
	)
)