/*
Poly Connect Verts
Only Works in max 2017+, extends Edit Poly interface, based on example from http://www.scriptspot.com/3ds-max/scripts/extrudeinsetoutline-faces-modifiers
by Stephan Viranyi https://www.artstation.com/stephko
Feel free to share and extend to your wishes and msg me for any questions or feedback at stephko@viranyi.de
*/
plugin modifier PolyConnectVerts
	name:"Poly Connect Verts"
	classID:#(0x517b8b5f, 0x41b6c49f)
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
		
	)

	
	on create do
	(		
		delegate.animationMode = 1
		delegate.useStackSelection = on
		delegate.setEPolySelLevel #Vertex
		delegate.setOperation #ConnectVertices
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
		edittext 'HowToUse' text:"Select only vertices in Stack. Connect selected vertices" readOnly:true height:80 width:150
	)
)