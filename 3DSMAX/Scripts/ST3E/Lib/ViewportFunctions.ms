global ViewportFunctions

Struct ViewportFunctionsStruct
(


	function NormalizedViewportMousePos =
	(
		--get total pixel size of vp and pixel pos of mouse
		local dir = [mouse.pos[1] / gw.getWinSizeX(), 1 - (mouse.pos[2] / gw.getWinSizeY())]
		--normlize and rescale to -1 to 1
		dir = dir * 2 - 1
		return dir
	),
	
		function NormalizedViewportMouseAngle =
	(
		--get total pixel size of vp and pixel pos of mouse
		local dir = [mouse.pos[1] / gw.getWinSizeX(), 1 - (mouse.pos[2] / gw.getWinSizeY())]
		--normlize and rescale to -1 to 1
		dir = dir * 2 - 1
		--save sign for angle
		local sign
		if (dir.x < 0) then sign = 1 else sign = 0
		--flip dir.y for cw rotation, shift by 90m degree as the unit circle starts from 1,0 add 180 degrees if we are on the other side
		local directionAngle = (atan ((-dir.y)/dir.x)) + 90 + (180 * sign)
		--print directionAngle
	)
)
ViewportFunctions = ViewportFunctionsStruct()

