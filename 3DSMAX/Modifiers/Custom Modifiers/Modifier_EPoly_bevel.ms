/*
Poly Bevel Modifier
Only Works in max 2017+, extends Edit Poly interface, based on example from Vojtech Cada http://www.scriptspot.com/3ds-max/scripts/extrudeinsetoutline-faces-modifiers
by Stephan Viranyi https://www.artstation.com/stephko
Feel free to share and extend to your wishes and msg me for any questions or feedback at stephko@viranyi.de
*/
plugin modifier PolyBevel
	name:"Poly Bevel"
	classID:#(0x5587e7a1, 0x502d025d)
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
		type type:#integer animatable:off default:2 ui:rbType
		on type set index do delegate.bevelType = index - 1

		bevelHeight type:#float default:10 ui:spnBevelHeight
		on bevelHeight set val do delegate.bevelHeight = val

		bevelOutline type:#float default:0 ui:spnBevelOutline
		on bevelOutline set val do delegate.bevelOutline = val

		bevelBias type:#float default:0 ui:spnBevelBias
		on bevelBias set val do delegate.bevelFaceBias = val
	)

	
	on create do
	(		
		delegate.animationMode = 1
		delegate.useStackSelection = on
		delegate.setEPolySelLevel #Face
		delegate.setOperation #Bevel
	)

	on load do initUpdate (refs.dependentNodes this)[1]
	
	on attachedToNode node do
		if isValidNode node then initUpdate node
		else if this.updateHandler != undefined do deleteChangeHandler this.updateHandler

	rollout params "Parameters"
	(
		spinner spnBevelHeight "Bevel Height" type:#worldUnits range:[-1e6, 1e6, 10]
		spinner spnBevelOutline "Bevel Outline" type:#worldUnits range:[-1e6, 1e6, 0]
		spinner spnBevelBias "Bevel Bias" type:#worldUnits range:[0, 1, 0]
		radioButtons rbType labels:#("Group", "Local Normal", "By Polygon")
	)
	
	
	rollout header "How to use"
	(
		edittext 'HowToUse' text:"Select Faces through the stack and bevel like Edit Poly" readOnly:true height:80 width:150
	)
)