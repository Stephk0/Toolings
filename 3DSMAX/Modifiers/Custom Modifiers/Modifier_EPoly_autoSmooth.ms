/*
AutoSmooth Modifier
Only Works in max 2017+, extends Edit Poly interface, based on example from http://www.scriptspot.com/3ds-max/scripts/extrudeinsetoutline-faces-modifiers
by Stephan Viranyi https://www.artstation.com/stephko
Feel free to share and extend to your wishes and msg me for any questions or feedback at stephko@viranyi.de
*/

plugin modifier PolyAutoSmooth
	name:"Poly AutoSmooth"
	classID:#(0x31f987d9, 0x6bbfcf1d)
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
		smoothAngle type:#float default:45 ui:spnSmoothAngle
		on smoothAngle set val do delegate.autoSmoothThreshold = val
	)

	
	on create do
	(		
		delegate.animationMode = 1
		delegate.useStackSelection = on
		delegate.setEPolySelLevel #Face
		delegate.setOperation #Autosmooth
	)

	on load do initUpdate (refs.dependentNodes this)[1]
	
	on attachedToNode node do
		if isValidNode node then initUpdate node
		else if this.updateHandler != undefined do deleteChangeHandler this.updateHandler

	rollout params "Parameters"
	(
		spinner spnSmoothAngle "SmoothAngle" type:#float range:[1,180,1]
	)
	
	rollout header "How to use"
	(
		edittext 'HowToUse' text:"Autosmooth Polies. Select Faces in Stack (doesnt work if nothing selected), will autosmooth selection like EPoly does respecting surrounding Smoothing Groups" readOnly:true height:80 width:150
	)
)