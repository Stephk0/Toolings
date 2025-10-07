macroScript AddTurnToPoly
category:"ST3E_Management"
toolTip:"Add TurnToPoly Mod to Selection"
ButtonText:"AddTurnToPoly"
(
	-----------------------------------------------------------------------
	-- Add turn to poly modifiers
	-----------------------------------------------------------------------
	-- adds a non instanced turn to poly modifier to the top of your stack of your selection. this is helpful for exporting as fbx to retain polygons

	for i = 1 to (selection.count) where superclassof selection[i] == GeometryClass do
	(
		-- dont add multiple turn to polies, also prevents adding multuple ones on selected instances		
		if (ClassOf selection[i].modifiers[1] != Turn_To_Poly) then addModifier selection[i] (Turn_To_Poly())
	)
	
)

macroScript RemoveTurnToPoly
category:"ST3E_Management"
toolTip:"Remove TurnToPoly Mod from Selection"
ButtonText:"RemoveTurnToPoly"
(
	-----------------------------------------------------------------------
	-- Remove turn to poly modifiers
	-----------------------------------------------------------------------
	-- removes the topmost turn to poly modifier. this is helpful when you added a turn to poly for export but forgot to save the sceneMaterials
	-- Hugs and Kisses to Per Abrahmsen for providing me some neat pointers and code!
	
	local TTPmodifier
	local selectionBuffer = selection as array
	local selectionToProcessing = #()
	
	--Filter Instances out of the selection so we just select one of each instance for processing
	for obj in selectionBuffer do
	(
		--get if there are multiple instances of this obj in selection
		local obj_instances = #()
		InstanceMgr.GetInstances obj &obj_instances
		--is it a repating instance and not a reference
		if (obj_instances.count > 1 AND (for obj_instance in obj_instances where not (areNodesInstances obj obj_instance) collect obj_instance).count == 0) then
		(
			--we have to check for references as they are treated as instances
			--TODO: this could probaly be moved to the upper if statement
			--local obj_references
			--check if it has a set of references TODO: for loop could be stopped upon first ref
			--obj_references = for obj_instance in obj_instances where not (areNodesInstances obj obj_instance) collect obj_instance
			--if its a referenced copy add the actual object to the list
			--if (obj_references.count > 0) then appendIfUnique selectionToProcessing obj
			--otherwise only add the first instance in the instance list
			appendIfUnique selectionToProcessing obj_instances[1]
			
			-- this yielded some weird result, would be a perfomance saver and it looks correct. resizing of collection is no bueno?
			/*
			for obj_instance in obj_instances do
			(	
				idx	= findItem selectionBuffer obj_instance
				print idx
				if idx > 0 then deleteItem selectionBuffer idx
			)
			*/
		)
		--is unique object
		else appendIfUnique selectionToProcessing obj
	)
	
	max modify mode
	
	for obj in selectionToProcessing do
	(
		--get topmost modifier
		select obj
		TTPmodifier = modPanel.getCurrentObject()
		--if its a turn to poly, delete it
		if (ClassOf TTPmodifier == Turn_To_Poly) then deleteModifier obj TTPmodifier
	)
	
	select selectionBuffer
	redrawViews()
	
/*
	--Hugs and Kisses to Per Abrahmsen for beating me to it and providing me that neat code
	local objs						= selection as array
	local objs_final				= #()
	for obj in objs					do
	(	
		local obj_instances
		InstanceMgr.GetInstances	obj &obj_instances
		if obj_instances.count > 1 then
		(	
			append objs_final obj
			for obj_instance in obj_instances do
			(	
				idx	= (findItem objs obj_instance )
				if idx > 0 then deleteItem objs idx
			)
		)
	)
	while isSelectionFrozen() do thawSelection()
	--eselect objs_final
	--Hugs and Kisses to Soulburn for making this awesome bit of code for quick processing of mulitple Objects without reiterating instances
	fn sLibRemoveUnneededInstancesFromArray objsToProcess = 
	(
	a = #()
	while objsToProcess.count != 0 do
		(
		append a objsToProcess[1]
		objsWithoutFirst = sLibRemoveItemFromArray objsToProcess objsToProcess[1]
		trimmedArray = sLibRemoveInstancesOfObjFromArray objsWithoutFirst objsToProcess[1]
		objsToProcess = sLibCopyArray trimmedArray
		)
	return a
	)
	local newSelect = sLibRemoveUnneededInstancesFromArray selection
	*/

	
	
)