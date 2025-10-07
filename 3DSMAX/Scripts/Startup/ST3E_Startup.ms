/*
ST3E Startup Scripts load. MUST be in startup to make sure libraries are loaded first
*/
	
	function loadLibs  = 
	(	
		fileIn ((getDir #scripts) + "\\ST3E\\Lib\\LibTest.ms")
		fileIn ((getDir #scripts) + "\\ST3E\\Lib\\PolySelectExtended.ms")
		fileIn ((getDir #scripts) + "\\ST3E\\Lib\\PolySnapToLocalCenter.ms")
		fileIn ((getDir #scripts) + "\\ST3E\\Lib\\ViewportFunctions.ms")
	)

	function loadScripts  = 
	(
		--Selection Extensions
		--fileIn ((getDir #scripts) + "\\ST3E\\EditPoly\\EditPolyOnly\\PolySelectExtended.mcr")
		--fileIn ((getDir #scripts) + "\\ST3E\\LibTester.mcr")
		fileIn ((getDir #scripts) + "\\ST3E\\RulersHelpers\\SmartConstraint.mcr")
	)

	function start = 
	(
		print "welcome to max bullshit,but this time with symlinks!"
		print "and its synced also"
		loadLibs()
		loadScripts()
	)


clearListener()
start()