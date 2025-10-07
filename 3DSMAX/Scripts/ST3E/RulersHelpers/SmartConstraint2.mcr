---------------------------------------------------------------------
-- Pie menu style constrain selector in the viewport
-- Constrains without undo for uninterupted modelling flow
-- Requires ViewportFunctions.ms from /Lib . Place ViewportFunctions.ms in maxroot/scripts/startup
---------------------------------------------------------------------
	
macroScript SmartConstraint2
category:"ST3E_RulersHelpers"
toolTip:"Smart Constraint 2"	
(

	--------------------
	-- settings
	--------------------
	local flyoutTime = 1000 				-- time it takes till the ui vanishes again
	local confirmationRadius = 64 		-- distance from middle point to confirm choice in pixels 
	local enableGraphicFeedback = true  -- enable the ui
	local enableUICross			= true
	local enableUIMouseline 	= true
	local enableUIText 			= true
	
	local UITextShorthand		= false -- replace text with shorts

	local UICrossSize 			= 64
	local UIMouselineLength 	= 128

	local UICrossColor 			= yellow
	local UIMouslineColor 		= yellow
	local UITextColor 			= yellow
	--------------------
	-- internal
	--------------------

	local stopInputTimer = dotNetObject "System.Windows.Forms.Timer"
	stopInputTimer.interval = flyoutTime

	local forceUpdateTimer = dotNetObject "System.Windows.Forms.Timer"
	forceUpdateTimer.interval = 10

	local tempCenter = [0,0,0]
	local constrainChoice = 0
	local showGraphicOverlay = false

	local curmod

	--------------------
	-- viewport feedback
	--------------------

	fn GW_displayChoiceIndicator =
	(

		if showGraphicOverlay do
		(
			gw.setTransform (Matrix3 1)
				
			local mouselineColor = #(UIMouslineColor, UIMouslineColor)
			local crossColor = #(UICrossColor, UICrossColor)
			local mouseDirection

			case constrainChoice of 
			(
				0: mouseDirection = [ 0, 1,1] --norm
				1: mouseDirection = [ 1, 0,1] --edge
				2: mouseDirection = [ 0,-1,1] --off
				3: mouseDirection = [-1, 0,1] --face
			)

			--mouse direction line
			if enableUIMouseline do gw.hPolyline #(tempCenter, tempCenter + mouseDirection * UIMouselineLength ) false rgb:mouselineColor
			
			--cross
			if enableUICross do 
			(
				local crossSizeHalf = UICrossSize / 2
				gw.hPolyline #(tempCenter - [ crossSizeHalf,crossSizeHalf,0],	tempCenter + [ crossSizeHalf,crossSizeHalf,0]	) false rgb:crossColor
				gw.hPolyline #(tempCenter + [-crossSizeHalf,crossSizeHalf,0],	tempCenter - [-crossSizeHalf,crossSizeHalf,0]	) false rgb:crossColor
			)
			
			--text
			if enableUIText do 
			(
				local normalString = "Normal"
				if UITextShorthand do normalString = "N"
				gw.htext (tempCenter + [0,48,0] - [(gw.getTextExtent normalString).x / 2,0,0]) normalString color:UITextColor
				
				local edgeString = "Edge"
				if UITextShorthand do edgeString = "E"
				gw.htext (tempCenter + [48,0,0] ) edgeString color:UITextColor
				
				local faceString = "Face"
				if UITextShorthand do faceString = "F"
				gw.htext (tempCenter - [48,0,0] - [(gw.getTextExtent faceString).x,0,0]) faceString color:UITextColor
				
				local noneString = "None"
				if UITextShorthand do noneString = "-"
				gw.htext (tempCenter - [0,48,0] - [(gw.getTextExtent noneString).x / 2,0,0]) noneString color:UITextColor
			)
			
			gw.enlargeUpdateRect #whole
			gw.updateScreen()
			--gw.setTransform (Matrix3 1)
		)

	)
	if GW_displayChoiceIndicator != undefined do unregisterRedrawViewsCallback GW_displayChoiceIndicator
	if (GW_displayChoiceIndicator != undefined and enableGraphicFeedback) do registerRedrawViewsCallback GW_displayChoiceIndicator

	--------------------
	-- input logic
	--------------------

	fn setConstrainChoice =
	(
		winSizeY = gw.getWinSizeY()
		
		local mousePosH 	= [mouse.pos[1]	,mouse.pos[2] 	* -1 + winSizeY	,0]
		local dir 			= normalize (mousePosH - tempcenter)
		if dir.x == 1 then constrainChoice = 2
		else 
		(	
			local sign
			if (dir.x < 0) then sign = 1 else sign = 0
			--create "clockface" starting at 12 o clock = 0 - 360, devide this by 90 to get 4 parts
			constrainChoice = ((atan ((-dir.y)/dir.x)) + 90 + (180 * sign)) / 90
			--shift the clock so we are "between" the clockface directions
			constrainChoice = mod (constrainChoice + 0.5) 4
			--convert to integer to get a clear number
			constrainChoice = constrainChoice as integer
		)
	)

	--------------------
	-- set constraint
	--------------------

	fn setEPolyConstraint = 
	(
		undo off
		(	
			case constrainChoice of 
			(			
				0: curmod.constrainType = 3 --normal
				1: curmod.constrainType = 1 --edge
				2: curmod.constrainType = 0 --off
				3: curmod.constrainType = 2 --face		
			)
		)
	)
	
	--------------------
	-- stop n choose
	--------------------

	fn StopAndSetConstraint = 
	(		
		--print ("elapsed time is " + ((timeStamp() - prevTime) as string))
		--update view to show last state
		redrawViews()
		--disable the graphic
		showGraphicOverlay = false
		--get the final chosen direction
		setConstrainChoice()
		--set the contrstain
		setEPolyConstraint()
		--redraw to reflect the changes
		redrawViews()
		--stop the functions
		forceUpdateTimer.stop()
		stopInputTimer.stop()	
	)

	--------------------
	-- const feedback
	--------------------

	fn forceViewportUpdate = 
	(
		--force viewport updates, because otherwise the constrain indicator wont be updated if the viewport isnt set to "improve image progressivly"
		setConstrainChoice()
		--if the user exceeds the distance from the middle we confirm a choice even before the flyout is over
		confirmDistance = distance tempCenter [mouse.pos[1],mouse.pos[2] * -1 + gw.getWinSizeY() ,0]
		if confirmDistance > confirmationRadius do StopAndSetConstraint()
		redrawViews()
	)

	dotnet.addEventHandler stopInputTimer "tick" StopAndSetConstraint
	dotnet.addEventHandler forceUpdateTimer "tick" forceViewportUpdate

	on isEnabled do Filters.Is_EPoly()
	
	on execute do 
	(
		--store current mod
		curmod = Modpanel.getcurrentObject()
		--store last mouseposition as center
		tempCenter 	= [mouse.pos[1]	,mouse.pos[2] * -1 + gw.getWinSizeY(), 0]
		--enbale the graphics overlay
		if enableGraphicFeedback do 
		(
			showGraphicOverlay = true
			--update the view
			redrawViews()
			
		)
		forceUpdateTimer.start()
		--start the timer when we stop the input and close the action
		stopInputTimer.start()
		

	)
)

