macroScript PolySmartCreate2
	category:"ST3E_Editing"
	toolTip:"OP Smart Create"
	ButtonText:"SmartCreate"
	(
		-----------------------------------------------------------------------
			-- Edit Poly Smart Create
			-- original idea by Per128 but adapted to different workflow
			-- added edit_poly support
			-- added auto modfiy mode?
			-----------------------------------------------------------------------
			-----------------------------------------------------------------------
			--   Vertex mode:
			--		cut tool
			--   Border mode:
			--      Cap border
			--   Edge mode:
			--		If a valid bridge selection, will bridge edges
			--		Otherwise create edge
			--   Face mode:
			--      If less than two faces selected, will enter create face mode
			--      Otherwise will bridge the polies
			-----------------------------------------------------------------------
			-------------------------------------
			-- TODO: add support for splines? connect
			-- TODO: replace variable names with something bit more reasonable
			-- TODO: Add Bridge
			-------------------------------------
			-----------------------------------------------------------------------

		On IsEnabled Return Filters.Is_EPoly()
		On IsVisible Return Filters.Is_EPoly()
		On IsChecked Do 
		(
			try 
			(
				local A = Filters.GetModOrObj()
				if (Filters.Is_This_EditPolyMod A) then
				(
					local mode = A.GetCommandMode
					(mode == #CreateVertex) or (mode == #CreateEdge) or (mode == #CreateFace)
				)
				else false
			)
			catch ( false )
		)

		On Execute Do 
		(
			
				If SubObjectLevel == undefined then Max Modify Mode
				local A = Filters.GetModOrObj()
				local msl = A.GetMeshSelLevel ()
				if msl == #vertex then 
				(
					SubObjectLevel = 2
					A.toggleCommandMode #CreateEdge
				)
				else (
					if msl == #edge then (A.toggleCommandMode #CreateEdge)
					else (A.toggleCommandMode #CreateFace)
				)
			
		)
	)

	
	


		

