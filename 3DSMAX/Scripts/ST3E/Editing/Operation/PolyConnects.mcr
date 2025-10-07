-------------------------------------
-- Connect as a set of segment preset from 1-8
-- Connect 1 consolidates connect edges and connect vert into one context senstive function
-------------------------------------
-------------------------------------
-- Connect and cap consolidates connect edges, connect vert and cap into one context senstive function
-- verts selected > connect verts
-- edges selected > connect edges
-- border selected > cap selcted border
-------------------------------------
-- todo add support for splines? divide spline
-- todo make struct function
-------------------------------------

macroScript Connect1AndCap
	category:"ST3E_Editing"
	toolTip:"OP Connect 1 Or Cap"
	ButtonText:"Connect1AndCap"
	(
		-- customize this if you want more divisions
		--due to the the way splineops are implmented we can only devide once and then redive, so every even number doenst really work
		local segments = 1
		
		--on isEnabled return (subobjectlevel != undefined and (Filters.Is_EPoly() or (Filters.Is_EditSpline() and (classof (modPanel.GetcurrentObject()) != Edit_Spline))) and subobjectlevel != 0 and subobjectlevel < 4)
		on isEnabled return (subobjectlevel != undefined and (Filters.Is_EPoly() or Filters.Is_EditSpline()) and subobjectlevel != 0 and subobjectlevel < 4)
		
		on execute do
		(

			--if epoly
			if Filters.Is_EPoly() then 
			(	
				currMod = Filters.GetModOrObj()

				if (subobjectlevel==2) then
				(
					currMod.connectEdgeSegments = segments
					if (Filters.Is_This_EditPolyMod currMod) then currMod.ButtonOp #ConnectEdges
					else currMod.ConnectEdges ()
				)
				else if (subobjectlevel==1) then currMod.buttonOp #ConnectVertices
				else if (subobjectlevel==3) then currMod.ButtonOp #Cap
			)

			else if Filters.Is_EditSpline() then
			(
				--from vanilla max, undoable single divide
				--ApplyOperation Edit_Spline Splineops.Divide
				splineCopy = copy selection[1]
				
				--multiple devisions but doesnt work with Edit_spline nor is it undoable
				
				local splineSel = #()
				--for all splines check if we have them selected and add to array
				for i=1 to (numSplines splineCopy) do
				(
					local segSel = getSegSelection splineCopy i
					if segSel.count > 0 do appendIfUnique splineSel i
				)
				--for every splines we have added get array of segments and divide them
				for spline in splineSel do
				(
					local segSel = #()
					segSel = getSegSelection splineCopy spline
					for segment in segSel do
					(
						subdivideSegment splineCopy spline segment segments
					)
				)
				instanceReplace  selection[1] splineCopy
				updateShape selection[1]
				delete splineCopy
				
				--theHold.Accept "flatten spline"
				
			)

		)

	)		
	macroScript Connect1
	category:"ST3E_Editing"
	toolTip:"OP Connect 1"
	ButtonText:"C/1"
	(
		on isEnabled return (subobjectlevel != undefined and (Filters.Is_EPoly() or Filters.Is_EditSpline()) and subobjectlevel != 0 and subobjectlevel < 4)
		
		on execute do
		(
			local segments = 1
			currMod = Filters.GetModOrObj()
			
			if (subobjectlevel==2) then
			(
				currMod.connectEdgeSegments = segments
				if (Filters.Is_This_EditPolyMod currMod) then currMod.ButtonOp #ConnectEdges
				else currMod.ConnectEdges ()
			)
			else if (subobjectlevel==1) then currMod.buttonOp #ConnectVertices
		
		)

	)		
	macroScript Connect2
	category:"ST3E_Editing"
	toolTip:"OP Connect 2"
	ButtonText:"C/2"
	(
		on isEnabled return (subobjectlevel != undefined and (Filters.Is_EPoly() or Filters.Is_EditSpline()) and subobjectlevel != 0 and subobjectlevel < 4)
		
		on execute do
		(
			local segments = 2
			currMod = Filters.GetModOrObj()
			
			if (subobjectlevel==2) then
			(
				currMod.connectEdgeSegments = segments
				if (Filters.Is_This_EditPolyMod currMod) then currMod.ButtonOp #ConnectEdges
				else currMod.ConnectEdges ()
			)	
		)

	)	
	macroScript Connect3
	category:"ST3E_Editing"
	toolTip:"OP Connect 3"
	ButtonText:"C/3"
	(
		on isEnabled return (PolyBoost.ValidEPmacro() and subobjectlevel != 0 and subobjectlevel > 1 and subobjectlevel < 4)
		
		on execute do
		(
			local segments = 3
			currMod = Filters.GetModOrObj()
			
			if (subobjectlevel==2) then
			(
				currMod.connectEdgeSegments = segments
				if (Filters.Is_This_EditPolyMod currMod) then currMod.ButtonOp #ConnectEdges
				else currMod.ConnectEdges ()
			)	
		)

	)		
	macroScript Connect4
	category:"ST3E_Editing"
	toolTip:"OP Connect 4"
	ButtonText:"C/4"
	(
		on isEnabled return (PolyBoost.ValidEPmacro() and subobjectlevel != 0 and subobjectlevel > 1 and subobjectlevel < 4)
		
		on execute do
		(
			local segments = 4
			currMod = Filters.GetModOrObj()
			
			if (subobjectlevel==2) then
			(
				currMod.connectEdgeSegments = segments
				if (Filters.Is_This_EditPolyMod currMod) then currMod.ButtonOp #ConnectEdges
				else currMod.ConnectEdges ()
			)	
		)

	)		
	macroScript Connect5
	category:"ST3E_Editing"
	toolTip:"OP Connect 5"
	ButtonText:"C/5"
	(
		on isEnabled return (PolyBoost.ValidEPmacro() and subobjectlevel != 0 and subobjectlevel > 1 and subobjectlevel < 4)

		on execute do
		(
			local segments = 5
			currMod = Filters.GetModOrObj()
			
			if (subobjectlevel==2) then
			(
				currMod.connectEdgeSegments = segments
				if (Filters.Is_This_EditPolyMod currMod) then currMod.ButtonOp #ConnectEdges
				else currMod.ConnectEdges ()
			)	
		)
	)	
	macroScript Connect6
	category:"ST3E_Editing"
	toolTip:"OP Connect 6"
	ButtonText:"C/6"
	(
		on isEnabled return (PolyBoost.ValidEPmacro() and subobjectlevel != 0 and subobjectlevel > 1 and subobjectlevel < 4)

		on execute do
		(
			local segments = 6
			currMod = Filters.GetModOrObj()
			
			if (subobjectlevel==2) then
			(
				currMod.connectEdgeSegments = segments
				if (Filters.Is_This_EditPolyMod currMod) then currMod.ButtonOp #ConnectEdges
				else currMod.ConnectEdges ()
			)	
		)

	)
	macroScript Connect7
	category:"ST3E_Editing"
	toolTip:"OP Connect 7"
	ButtonText:"C/7"
	(
		on isEnabled return (PolyBoost.ValidEPmacro() and subobjectlevel != 0 and subobjectlevel > 1 and subobjectlevel < 4)

		on execute do
		(
			local segments = 7
			currMod = Filters.GetModOrObj()
			
			if (subobjectlevel==2) then
			(
				currMod.connectEdgeSegments = segments
				if (Filters.Is_This_EditPolyMod currMod) then currMod.ButtonOp #ConnectEdges
				else currMod.ConnectEdges ()
			)	
		)

	)
	macroScript Connect8
	category:"ST3E_Editing"
	toolTip:"OP Connect 8"
	ButtonText:"C/8"
	(
		on isEnabled return (PolyBoost.ValidEPmacro() and subobjectlevel != 0 and subobjectlevel > 1 and subobjectlevel < 4)

		on execute do
		(
			local segments = 8
			currMod = Filters.GetModOrObj()
			
			if (subobjectlevel==2) then
			(
				currMod.connectEdgeSegments = segments
				if (Filters.Is_This_EditPolyMod currMod) then currMod.ButtonOp #ConnectEdges
				else currMod.ConnectEdges ()
			)	
		)

	)

	
	

