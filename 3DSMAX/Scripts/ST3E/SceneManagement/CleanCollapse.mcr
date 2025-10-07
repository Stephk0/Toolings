macroScript CleanCollapse
	category:"ST3E_Management"
	toolTip:"Clean collapse selection"
	ButtonText:"CleanCollapse"
	(

	-----------------------------------------------------------------------
	-- Clean Collapse
	-----------------------------------------------------------------------
	-- duplicates your seletion, and attachs it to one mesh that is based on a clean cube on pivot 0 0 0
	-----------------------------------------------------------------------
	-- TODO add material
	-- TODO filter only geometry class
	-----------------------------------------------------------------------

	-----------------------------------------------------------------------
	-- persitent variables
	-----------------------------------------------------------------------

	persistent global nameString

	local geoclassFilteredSelection
	local clonedNodes
	-----------------------------------------------------------------------
	-- code starts here
	-----------------------------------------------------------------------

	if (selection.count > 0) then
	(
		-- thanks https://forums.cgsociety.org/t/easy-prompt-for-string-input-equivalent-of-messagebox/1520844/4
		-- get a name string from user
		if (nameString == undefined) then nameString = "_MESH"
		theObj = dotNetObject "MaxCustomControls.RenameInstanceDialog" nameString
		theobj.text ="Type in new name for your lowpoly here"
		DialogResult = theObj.Showmodal()

		--test if the ok button was pressed
		if (dotnet.compareenums TheObj.DialogResult ((dotnetclass "System.Windows.Forms.DialogResult").OK)) then
		(
			--get the new text string
			nameString = theobj.InstanceName 

			--filter only geometry class
			geoclassFilteredSelection = for obj in selection where superclassof obj == GeometryClass collect obj
				
			-- store selection to add to box mesh
			clonedNodes = #()
			maxOps.cloneNodes geoclassFilteredSelection clonetype:#copy actualNodeList:geoclassFilteredSelection newNodes:&clonedNodes
			-- instantiate the plane and convert it to a poly
			combined_Mesh = convertToPoly(Plane lengthsegs:1 widthsegs:1 isSelected:on)
			combined_Mesh.name = nameString
			-- make sure we are in modify mode
			max modify mode
			-- delete the one face of the plane
			combined_Mesh.EditablePoly.SetSelection #Face #{1}
			combined_Mesh.EditablePoly.delete #Face
			combined_Mesh.EditablePoly.SetSelection #Face #{}

			--collapse each copys stack down
			for obj in clonedNodes do maxOps.CollapseNodeTo obj 1 off

			
			for obj in clonedNodes where isValidNode obj do 
			(
				combined_Mesh.EditablePoly.attach obj combined_Mesh
			)

			convertToMesh(combined_Mesh)
			convertToPoly(combined_Mesh)

			--combined_Mesh.EditablePoly.SetSelection #Face #{}

			-- for some shitty reason editablepoly has no attach list but edit poly mod does. lets add one and collapse back to an editable poly
			--addmodifier combined_Mesh (Edit_Poly())
			--combined_Mesh.Edit_Poly.AttachList &clonedNodes editPolyNode:combined_Mesh
			--convertToPoly(combined_Mesh)
		)
	)
	
)

