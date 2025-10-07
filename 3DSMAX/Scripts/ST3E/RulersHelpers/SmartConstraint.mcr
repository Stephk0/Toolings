	---------------------------------------------------------------------
	-- Constrains without undo for uninterupted modelling flow
	---------------------------------------------------------------------
	
	macroScript SmartConstraint
	category:"ST3E_RulersHelpers"
	toolTip:"Smart Constraint"
	
(
	on isEnabled do Ribbon_Modeling.ValidSelection()
	
	on execute do 
	(
		if selection.count > 0 and Ribbon_Modeling.ValidSelection() then
		(
			undo off
			(
				--local threshold = 0.1
				local mousePos = ViewportFunctions.NormalizedViewportMousePos()
				local mouseAngle = ViewportFunctions.NormalizedViewportMouseAngle()
				
				curmod = Modpanel.getcurrentObject()

				-- if outside of viewport
				if ((distance [0,0] mousePos) > 1) then curmod.constrainType = 0
				
				else if (mouseAngle < 45 or mouseAngle > 315) then curmod.constrainType = 3 --normal
				--version where ege is on both sides and face down, felt a bit wonky
				--else if ((mouseAngle > 45 and mouseAngle < 135) or (mouseAngle > 225 and mouseAngle < 315)) then curmod.constrainType = 1
				--else if (mouseAngle > 135 and mouseAngle < 225) then curmod.constrainType = 2

				else if (mouseAngle > 45 and mouseAngle < 135) then curmod.constrainType = 1 --edge
				else if (mouseAngle > 225 and mouseAngle < 315) then curmod.constrainType = 2 --face
				else if (mouseAngle > 135 and mouseAngle < 225) then curmod.constrainType = 0 --off
				
			)
		)
	)
)

