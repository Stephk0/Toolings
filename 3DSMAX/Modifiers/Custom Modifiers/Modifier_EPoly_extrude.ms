/*
TODO: replace classId sig so it doesnt interfere with existing
*/

plugin modifier PolyExtrude
	name:"Poly Extrude"
	classID:#(0x310ed948, 0x341c7c31)
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
		height type:#float default:1 ui:spnHeight

		on type set index do delegate.extrudeFaceType = index - 1
		on height set val do delegate.extrudeFaceHeight = val

		bias type:#float default:0 ui:spnBias
		on bias set val do delegate.extrudeFaceBias = val
	)
	
	on create do
	(
		delegate.animationMode = 1
		delegate.useStackSelection = on
		delegate.setEPolySelLevel #Face
		delegate.setOperation #ExtrudeFace
	)

	on load do initUpdate (refs.dependentNodes this)[1]
	
	on attachedToNode node do
		if isValidNode node then initUpdate node
		else if this.updateHandler != undefined do deleteChangeHandler this.updateHandler

	rollout params "Parameters"
	(
		spinner spnHeight "Height: " type:#worldUnits range:[-1e6, 1e6, 1]
		spinner spnBias "Bias: " type:#worldUnits range:[0, 1, 0]
		radioButtons rbType labels:#("Group", "Local Normal", "By Polygon")
	)
)