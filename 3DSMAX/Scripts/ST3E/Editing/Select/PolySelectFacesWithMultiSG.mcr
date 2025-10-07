----------------------------------------------------
-- select faces that have multiple smoothing groups assigned
-- based on https://forums.cgsociety.org/t/how-to-get-some-face-which-have-two-smoothing-groups-at-least/1344376/5
-- todo : extend to EP Modifier
----------------------------------------------------


macroScript SelectFacesWithMultipleSGs
	category:"ST3E_Modelling"
	toolTip:"Select Faces With Multiple SGs "
	ButtonText:"SelectFacesWithMultipleSGs"
	
(
	(
    function intToBitArray iNum =
    (
        if ((classOf iNum) == Integer) then
        (
            local baBits = #{}

            for i = 1 to 32 do
            (
                if (mod iNum 2 != 0) do
                (
                    baBits[i] = true
                    iNum -= 1
                )
                iNum /= 2
            )
            return baBits
        )
        else
        (
            return false
        )
    )

    if ( (selection.count == 1) and ((classOf selection[1]) == Editable_Poly) ) do
    (
        local oPoly = selection[1]

        local iSmoothingGroups = 0
        local baFaces = #{}

        for iFace = 1 to (polyOp.getNumFaces oPoly) do
        (
            iSmoothingGroups = polyOp.getFaceSmoothGroup oPoly iFace
            baSmoothingGroups = intToBitArray iSmoothingGroups

            if (baSmoothingGroups.numberSet > 1) do
            (
                baFaces[iFace] = true
            )
        )
		polyOp.setfaceselection $ baFaces
        --print baFaces
    )
)
	
)
