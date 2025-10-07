global SelectByAngleFunctions

Struct SelectByAngleFunctionsStruct
(

	function EvaluateMode =
	(
		activeMod = modPanel.getCurrentObject()
				
		if (ClassOf (activeMod) == Unwrap_UVW) then
		(
			if (activeMod.getGeomPlanarThresholdMode() == true) then true
			else false
		)
		else if (Filters.Is_EPoly()) then
		(
			A = Filters.GetModOrObj()	
			if (A.selectByAngle == true) then true
			else false
		)
		else false

	),

	function EvaluateAngle angle =
	(
		activeMod = modPanel.getCurrentObject()
				
		if (ClassOf (activeMod) == Unwrap_UVW) then
		(
			if (activeMod.getGeomPlanarThresholdMode() == true AND activeMod.getGeomPlanarThreshold() == angle) then true
			else false
		)
		else if (Filters.Is_EPoly()) then
		(
			A = Filters.GetModOrObj()
			if (A.selectByAngle == true AND A.selectAngle == angle) then true
			else false
		)
		else false

	),

	function SelectByAngleToggle =
	(
		
		if (currPanelMode != #modify) do max modify mode

		activeMod = modPanel.getCurrentObject()

		if (ClassOf (activeMod) == Unwrap_UVW) then
		(
			if (activeMod.getGeomPlanarThresholdMode() != true)  then 
			(
				activeMod.setGeomPlanarThresholdMode true
			)
			else
			(
				activeMod.setGeomPlanarThresholdMode false
			)
		)
		else 
		(
			local A = Filters.GetModOrObj()

			if (A.selectByAngle != true) then
			(
				A.selectByAngle = true
			)	
			else A.selectByAngle = false
			
		)
	),

	function SelectByAngleToggleAngle angle =
	(
		
		if (currPanelMode != #modify) do max modify mode

		activeMod = modPanel.getCurrentObject()

		if (ClassOf (activeMod) == Unwrap_UVW) then
		(
			if (activeMod.getGeomPlanarThresholdMode() != true OR activeMod.getGeomPlanarThreshold() != angle)  then 
			(
				activeMod.setGeomPlanarThresholdMode true
				activeMod.setGeomPlanarThreshold angle
				subObjectLevel = 3
			)
			else
			(
				activeMod.setGeomPlanarThresholdMode false
			)
		)
		else 
		(
			local A = Filters.GetModOrObj()

			if (A.selectByAngle != true OR A.selectAngle != angle) then
			(
				A.selectByAngle = true
				A.selectAngle = angle
				subObjectLevel = 4
			)	
			else A.selectByAngle = false
			
		)
	)
)
SelectByAngleFunctions = SelectByAngleFunctionsStruct()

