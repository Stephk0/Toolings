--iconless LayerManager
-- TODO: Figure out if we can just do something to bring the layer manager always infront of other ui when clicked
-- custom button to bring back the old layer explorer behaviour. 

macroScript OpenLayerManager
	category:"ST3E_Management"
	--internalCategory: "Scene Explorer"
	toolTip:"Toggle Layer Manager "
	ButtonText:"Layer Manager"
(	

	explorerName = "Layer Explorer"

	on isChecked do 	(
		
		sceneexplorermanager.ExplorerIsOpen explorerName
	)

	on execute do
	(

		if sceneexplorermanager.ExplorerExists explorerName then 
		(
			if (not sceneexplorermanager.ExplorerIsOpen explorerName ) then
				sceneexplorermanager.OpenExplorer explorerName 
		)
		else
		(
			sceneexplorermanager.CreateExplorerFromDefault explorerName
		)
	)

	on closeDialogs do
	(
		if (sceneexplorermanager.ExplorerIsOpen explorerName and not sceneexplorermanager.IsExplorerInViewport explorerName ) then
			sceneexplorermanager.CloseExplorer explorerName
	)
)