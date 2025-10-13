-- Viewport overlay showing you some states and stats, mostly evolving around the object you are currently editing
-- shows constrains and if you are in show end result mode or if you have a modifier active and selected
-- useful if you manage several objects with long stacks and want to quickly jump between them and understand what "state" they are in
unregisterRedrawViewsCallback GW_displayObjectNames
fn createBorder posX posY winSizeX winSizeY width borderColor=
(
	topBorder 		= (box2 posX 				posY 				(winSizeX - posX * 2)  	width					)
	bottomBorder 	= (box2 posX 				(winSizeY - posY - width) 	(winSizeX - posX * 2)  	width					)
	leftBorder 		= (box2 posX 				posY  				(width + 1)				(winSizeY - posY * 2)	)	
	rightBorder 	= (box2 (winSizeX - posX - width) 	posY 		(width + 1)				(winSizeY - posY * 2)	)
	
	gw.wrect topBorder borderColor
	gw.wrect bottomBorder borderColor
	gw.wrect leftBorder borderColor
	gw.wrect rightBorder borderColor

)

fn createDottedBorder posX posY winSizeX winSizeY width borderColor=
(
	--dotted line
	local dotDistance 	= 16
	local dotLength 	= 8
	local dotWidth 		= 2
	local padding 		= posX
	
	for i = 1 to ((((winSizeX - padding *2) / dotDistance) as integer)) do 
	(
		topBorder = (box2 (-dotDistance + padding + i * dotDistance) 32 dotLength dotWidth )
		gw.wrect topBorder borderColor
		
		bottomBorder = (box2 (-dotDistance + padding + i * dotDistance) (winSizeY - 32) dotLength dotWidth )
		gw.wrect bottomBorder borderColor
	)
	
	for i = 1 to ((((winSizeY - padding *2 ) / dotDistance) as integer)) do 
	(
		leftBorder = (box2 32 (-dotDistance + padding + i * dotDistance) dotWidth dotLength )
		gw.wrect leftBorder borderColor
		
		rightBorder = (box2 (winSizeX - 32) (-dotDistance + padding + i * dotDistance) dotWidth dotLength )
		gw.wrect rightBorder borderColor
		
	)
)

fn vpSelStats_fn = (
    vpWidth = gw.getWinSizeX()
 
    selType = try(($.baseObject) as string)catch("n/a")
    SelName = try(($.name) as string)catch("n/a")
    selMod = try (((modpanel.getCurrentObject()).name) as string)catch("n/a") --Only works if Modifier Tab is active.
    selSub = try (subobjectLevel as string)catch("n/a")
 
    allInfo = ("Type: " + selType + "  |  ") + ("Name: " + SelName + "  |  ") + ("Modifier: " + selMod + "  |  ") + ("Sub Object Level: " + selSub)
    viewCenterX = (vpWidth / 2) - (((gw.getTextExtent allInfo).x) / 2)
 
    --gw.setTransform (Matrix3 1)
    gw.wtext [viewCenterX,64,0] allInfo color:Yellow
    --gw.UpdateScreen()
)

fn clamp minVal maxVal val =
(
	if val < minVal then val = minVal
	else if val > maxVal then val = maxVal
	return val
)

fn GW_displayObjectNames =
(
	gw.setTransform (Matrix3 1)
	winSizeX = gw.getWinSizeX()
	winSizeY = gw.getWinSizeY()
	
	if getCommandPanelTaskMode() == #modify do
	(
		local epMod = Modpanel.getcurrentObject()
		
		--topBorder 		= (box2 (winSizeX / 2) 32	(64) 16)
		leftBorder 		= (box2 0 0	16 winSizeY)
		rightBorder 	= (box2 (winSizeX - 16) 0	16 winSizeY)
		topBorder 		= (box2 0 0	winSizeX 16)
		--gw.wrect topBorder red
		if not epMod == undefined do
		(
			if Filters.Is_EPoly() do
			(
				
				gw.wrect rightBorder [128,128,128]
				gw.wrect leftBorder [128,128,128]
				gw.wrect topBorder [128,128,128]
				
				local constrainString
				case epMod.constrainType of 
				(
					--0: ()
					1: gw.wrect rightBorder orange
					2: gw.wrect leftBorder orange
					3: gw.wrect topBorder orange
				)
				--gw.wtext [mouse.pos[1] + 12, mouse.pos[2] + 24,0] constrainString color:green
			)
			
			if not subObjectLevel == undefined and subObjectLevel > 0 do
			(
				--edit border
				createBorder 16 16 winSizeX winSizeY 2 yellow
				--show end result border
				if showEndResult == true do createBorder 17 17 winSizeX winSizeY 8 [100,100,255] 
			
				case subObjectLevel of 
				(
					1: createDottedBorder 32 32 winSizeX winSizeY 2 blue
					2: createBorder 32 32 winSizeX winSizeY 2 [0,200,128]
					3: createBorder 32 32 winSizeX winSizeY 2 [200,128,48]
					4: createBorder 32 32 winSizeX winSizeY 4 orange
					5: createBorder 32 32 winSizeX winSizeY 8 orange
				)

			)
		)
	)

	--Stats about the object, copeid from a polycount post, cant remember :(
	vpSelStats_fn()
		
	
	gw.enlargeUpdateRect #whole
	gw.updateScreen()
	--gw.setTransform (Matrix3 1)	

)
registerRedrawViewsCallback GW_displayObjectNames