-----------------------------------------
-- AppendBoundsSuffix
-- get bounds and add them as a suffix to the name
-- TODO: add ui, custom relinking of dimensions 
--
-----------------------------------------


macroScript AppendBoundsSuffix
	category:"ST3E_Management"
	toolTip:"Append Bounds Suffix"
	ButtonText:"AppendBoundsSuffix"
(
	local prefix = "_"
	local seperator = "x"
	local bounds = [0,0,0]
	for object in selection do
	(
		bounds = object.max - object.min

		boundsXString = formattedPrint bounds.x format:"000.f"
		boundsXString = formattedPrint (boundsXString as integer) format:"03d"
		
		boundsYString = formattedPrint bounds.y format:"000.f"
		boundsYString = formattedPrint (boundsYString as integer) format:"03d"
		
		boundsZString = formattedPrint bounds.z format:"000.f"
		boundsZString = formattedPrint (boundsZString as integer) format:"03d"
		
		object.name = object.name + prefix + boundsXString + seperator + boundsZString + seperator + boundsYString
	)
)

