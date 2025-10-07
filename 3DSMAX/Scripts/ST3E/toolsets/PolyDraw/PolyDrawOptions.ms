macroScript PolyDrawToolsetOptions
	category:"StephkoCustom"
	toolTip:"PolyDrawOptions"
	ButtonText:"PolyDrawOptions"
(
	global PolyDrawOptions
	global PDOffset
	global PDMindistance

	rollout PolyDrawOptions "Poly Draw Options" width:152 height:152
	(
		group "PolyDraw Base Options"
		(
			spinner 'offsetSpn' "Offset: " pos:[16,32] width:86 height:16 range:[0,10000,0] type:#float scale:0.1  align:#left
			spinner 'minDistanceSpn' "Min Distance" pos:[16,56] width:58 height:16 range:[0,1000,0] type:#float align:#left
			button 'pickSurfButton' PolyBoost.PolyDrawPicktext pos:[8,88] width:136 height:32 align:#left
		)
			
		on PolyDrawOptions open  do
		(
			if (PDOffset != undefined) then offsetSpn.value = PDOffset
			--PolyToolsUI.PDDistance  = PDOffset
			--PolyToolsUI.PDDrawtype = 2
			--updateToolbarButtons()
			--PolyToolsUI.PolyDrawSettings()
			--if PolyBoost.ValidEPbasemacro() do
			--(
			--PolyToolsUI.PDButtons[8] = not PolyToolsUI.PDButtons[8]
			--PolyBoost.ToolToggle 1 8 PolyToolsUI.PDButtons[8]
			--)
		)
		on offsetSpn changed val do
		(
			PDOffset = val
			PolyToolsPolyDraw.offset = PDOffset
			--PolyToolsUI.PDDrawtype = 2
			--PolyToolsPolyDraw.EndTool () 
			--updateToolbarButtons()
			--PolyToolsUI.PDDistance = PDOffset
			--PolyBoost.ToolToggle 1 5 true
			--PolyToolsUI.PolyDrawSettings()
			
		)
		--on offsetSpn entered text do
		--	PolyToolsPolyDraw.offset = text
		on minDistanceSpn changed val do
			PolyToolsPolyDraw.MinDistance = val
		--on minDistanceSpn entered text do
		--	PolyToolsPolyDraw.MinDistance = text
		on pickSurfButton pressed  do(
			PolyBoost.PolyDrawPickNode()
			PolyToolsUI.PDDrawtype = 2
			pickSurfButton.text = PolyBoost.PolyDrawPicktext
		)
	)
	CreateDialog PolyDrawOptions
	
)