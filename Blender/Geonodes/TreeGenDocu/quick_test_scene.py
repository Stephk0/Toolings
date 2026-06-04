"""
Quick Test Scene Setup for Procedural Tree Generator
Author: Stephan Viranyi (Stephko)
Date: 2025-12-03

This script creates a simple test scene with a trunk curve,
then automatically sets up the tree generator.

Usage:
1. Open Blender
2. Run this script (no selection needed)
3. Adjust tree parameters in modifier panel
"""

import bpy
import os

def create_test_scene():
    """Create a clean test scene with trunk curve"""

    print("\n" + "="*60)
    print("CREATING TEST SCENE")
    print("="*60 + "\n")

    # ===== CLEAN SCENE =====
    print("→ Cleaning default scene...")
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()

    # ===== CREATE TRUNK CURVE =====
    print("→ Creating trunk curve...")

    bpy.ops.curve.primitive_bezier_curve_add(
        location=(0, 0, 0),
        rotation=(0, 0, 0)
    )

    trunk = bpy.context.active_object
    trunk.name = "TreeTrunk"

    # Make it vertical and taller
    trunk.scale = (1, 1, 5)
    bpy.ops.object.transform_apply(scale=True)

    # Edit curve points for more interesting shape
    curve_data = trunk.data
    spline = curve_data.splines[0]

    # Modify points to create slight bend
    if len(spline.bezier_points) >= 2:
        spline.bezier_points[1].co.z = 3
        spline.bezier_points[1].co.x = 0.5  # Slight bend

    print(f"✓ Created trunk: {trunk.name}")

    # ===== ADD CAMERA =====
    print("→ Adding camera...")

    bpy.ops.object.camera_add(
        location=(8, -8, 5),
        rotation=(1.1, 0, 0.785)  # Look at origin
    )
    camera = bpy.context.active_object
    camera.name = "TreeCamera"

    # Set as active camera
    bpy.context.scene.camera = camera

    print(f"✓ Created camera: {camera.name}")

    # ===== ADD LIGHT =====
    print("→ Adding sun light...")

    bpy.ops.object.light_add(
        type='SUN',
        location=(5, 5, 10),
        rotation=(0.8, 0.2, 0.5)
    )
    sun = bpy.context.active_object
    sun.name = "SunLight"
    sun.data.energy = 3.0

    print(f"✓ Created light: {sun.name}")

    # ===== SETUP VIEWPORT SHADING =====
    print("→ Configuring viewport...")

    for area in bpy.context.screen.areas:
        if area.type == 'VIEW_3D':
            for space in area.spaces:
                if space.type == 'VIEW_3D':
                    space.shading.type = 'SOLID'
                    space.shading.color_type = 'MATERIAL'
                    space.shading.light = 'STUDIO'

    # ===== SELECT TRUNK FOR GENERATOR SETUP =====
    bpy.ops.object.select_all(action='DESELECT')
    trunk.select_set(True)
    bpy.context.view_layer.objects.active = trunk

    print("✓ Scene setup complete!")
    print(f"✓ Active object: {trunk.name}\n")

    return trunk

def setup_generator(trunk_obj):
    """Run the tree generator setup script"""

    print("="*60)
    print("SETTING UP TREE GENERATOR")
    print("="*60 + "\n")

    # Get script path
    script_dir = os.path.dirname(os.path.abspath(__file__))
    setup_script = os.path.join(script_dir, "setup_tree_generator.py")

    if os.path.exists(setup_script):
        print(f"→ Loading: {setup_script}\n")

        # Execute the setup script
        with open(setup_script, 'r') as f:
            script_content = f.read()

        exec(script_content)

        return True
    else:
        print(f"✗ ERROR: Could not find setup_tree_generator.py")
        print(f"  Expected location: {setup_script}")
        print("\nPlease run setup_tree_generator.py manually.")
        return False

# ===== MAIN EXECUTION =====
if __name__ == "__main__":
    print("\n" + "="*60)
    print("PROCEDURAL TREE GENERATOR - QUICK TEST SCENE")
    print("="*60 + "\n")

    # Create test scene
    trunk = create_test_scene()

    # Setup tree generator
    success = setup_generator(trunk)

    if success:
        print("\n" + "="*60)
        print("✓✓✓ ALL DONE! ✓✓✓")
        print("="*60)
        print("\nYour tree generator is ready!")
        print("\nNEXT STEPS:")
        print("1. Look at the 3D viewport - you should see a tree!")
        print("2. Open the Modifier Properties panel (wrench icon)")
        print("3. Find 'ProceduralTreeGenerator' modifier")
        print("4. Adjust parameters to grow your tree:")
        print("   - Iterations: 0-5 (start with 2)")
        print("   - Branch Length: 0.5-3.0")
        print("   - Angular Spread: 0.2-0.6")
        print("   - Random Seed: Change for variations")
        print("\n5. Switch to Geometry Nodes workspace to see the nodes!")
        print("="*60 + "\n")
    else:
        print("\n" + "="*60)
        print("SCENE CREATED - GENERATOR SETUP FAILED")
        print("="*60)
        print("\nThe test scene is ready, but the generator setup failed.")
        print("Please run setup_tree_generator.py manually with the trunk selected.")
        print("="*60 + "\n")
