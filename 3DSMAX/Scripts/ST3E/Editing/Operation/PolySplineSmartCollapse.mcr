macroScript SmartCollapse
	category:"ST3E_Editing"
	toolTip:"OP Smart Collapse"
	ButtonText:"Smart Collapse"
	(

		-----------------------------------------------------------------------
		-- Smart Collapse (Poly + Spline)
		-----------------------------------------------------------------------
		-- collapse in edit poly, as well as edit spline
		-----------------------------------------------------------------------

		On IsEnabled Return Filters.Is_EPoly() or Filters.Is_EditSpline()
		On IsVisible Return Filters.Is_EPoly() or Filters.Is_EditSpline()
		On Execute Do 
		(
			if (Filters.Is_EPoly()) do
			(
				local A = Filters.GetModOrObj()
				if (Filters.Is_This_EditPolyMod A) then
				(
					if (subobjectLevel == 1) then (A.ButtonOp #CollapseVertex)
					else if (subobjectLevel>1) and (subobjectLevel<4) then (A.ButtonOp #CollapseEdge)
					else if (subobjectLevel>3) then (A.ButtonOp #CollapseFace)
				)
				else (A.buttonOp #Collapse)
			)
			
			if (Filters.Is_EditSpline()) do
			(
				local prevSubObjMode = subobjectLevel
				--if we didnt select points of a spline convert to points for welding
					if (subobjectLevel>1) do
				(
					-- Returns the indices of the selected splines in the shape as an array of integers.
					-- getSplineSelection <shape>
					
					-- returns the indices of the selected segments in the specified shape spline as an array of integers.
					-- getSegSelection <shape> <spline_index_integer>
					
					-- Selects the knots specified by <knot_index_array> in the specified shape spline. <knot_index_array> is an array of integers specifying the knot indices.
					-- Knots already selected are de-selected unless keep:true is specified.
					-- setKnotSelection <shape> <spline_index_integer> <knot_index_array> [keep: <boolean> ]
					
					-- Returns true if the indexed spline is closed, false if it is open.
					-- isClosed <shape> <spline_index_integer>
					
					--f segIdx is the index of the segment
					--for open spline the knots always are:
					--knot1 = segIdx
					--knot2 = SegIdx + 1
					--For closed spline:
					--last segment have knots
					--knot1 = 1
					--knot2 = segIdx
					--the rest segments have knots idx the same as open spline
					
						prevSubObjMode = subobjectLevel
				)
				--TODO: change this to proper distance measurement
				weldSpline $ 10000000.0
				subobjectLevel = prevSubObjMode
			)
		)
	)

	