/*
Poly Inset Modifier, retains Edge Crease and Poly Specific values
Only Works in max 2017+, extends Edit Poly interface, based on example from http://www.scriptspot.com/3ds-max/scripts/extrudeinsetoutline-faces-modifiers by Vojtech Cada (big thanks!)
by Stephan Viranyi https://www.artstation.com/stephko
Feel free to share and extend to your wishes and msg me for any questions or feedback at stephko@viranyi.de
*/
--TODOTODO: generate new ClassID

plugin modifier PolyInsetFaces
	name:"Poly Inset Faces"
	classID:#(0x4efc6553, 0x4544956c)
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
		type type:#integer animatable:off default:1 ui:rbType
		amount type:#float default:1 ui:spnAmount

		on type set index do delegate.insetType = index - 1
		on amount set val do delegate.insetAmount = val
	)
	
	on create do
	(
		delegate.animationMode = 1
		delegate.useStackSelection = on
		delegate.setEPolySelLevel #Face
		delegate.setOperation #Inset
	)

	on load do initUpdate (refs.dependentNodes this)[1]
	
	on attachedToNode node do
		if isValidNode node then initUpdate node
		else if this.updateHandler != undefined do deleteChangeHandler this.updateHandler

	rollout params "Parameters"
	(
		spinner spnAmount "Amount: " type:#worldUnits range:[-1e6, 1e6, 1]
		radioButtons rbType labels:#("Group", "By Polygon")
	)

	rollout header "How to use"
	(
		edittext 'HowToUse' text:"Inset selected Poly Faces. Edge Weight/Crease are retained" readOnly:true height:80 width:150
	)
)