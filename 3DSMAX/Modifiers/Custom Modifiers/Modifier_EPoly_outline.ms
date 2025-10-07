/*
Poly Outline Modifier, retains Edge Crease and Poly Specific values
Only Works in max 2017+, extends Edit Poly interface, based on example from http://www.scriptspot.com/3ds-max/scripts/extrudeinsetoutline-faces-modifiers by Vojtech Cada (big thanks!)
by Stephan Viranyi https://www.artstation.com/stephko
Feel free to share and extend to your wishes and msg me for any questions or feedback at stephko@viranyi.de
*/

plugin modifier PolyOutlineFaces
	name:"Poly Outline Faces"
	classID:#(0x75145ba6, 0x54afa17b)
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

	parameters main rollout:params
	(
		amount type:#float default:1 ui:spnAmount
		on amount set val do delegate.outlineAmount = val
	)
	
	on create do
	(
		delegate.animationMode = 1
		delegate.useStackSelection = on
		delegate.setEPolySelLevel #Face
		delegate.setOperation #Outline
	)

	on load do initUpdate (refs.dependentNodes this)[1]
	
	on attachedToNode node do
		if isValidNode node then initUpdate node
		else if this.updateHandler != undefined do deleteChangeHandler this.updateHandler

	rollout params "Parameters"
	(
		spinner spnAmount "Amount: " type:#worldUnits range:[-1e6, 1e6, 1]
	)

	rollout header "How to use"
	(
		edittext 'HowToUse' text:"Outline selected Poly Faces. Edge Weight/Crease are retained" readOnly:true height:80 width:150
	)
)