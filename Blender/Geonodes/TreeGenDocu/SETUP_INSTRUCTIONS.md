# Procedural Tree Generator - Setup Instructions

**Version:** 1.0 - Phase 1 MVP
**Date:** 2025-12-03
**Status:** Initial Implementation

---

## Quick Start

### Method 1: Using the Setup Script (Recommended)

1. **Open Blender 4.5+**

2. **Create a trunk curve:**
   - Add > Curve > Bezier (or run the quick test setup below)
   - Scale it vertically to create a trunk shape (S, Z, 5)
   - Optional: Edit curve to add bends/character

3. **Select your trunk curve**

4. **Open Scripting Workspace** (top menu)

5. **Load the setup script:**
   - Click "Open" in text editor
   - Navigate to: `Toolings/Blender/Geonodes/setup_tree_generator.py`
   - Click "Open"

6. **Run the script:**
   - Click "Run Script" button (▶ icon)
   - Or press `Alt + P`

7. **Adjust parameters** in the Modifier Properties panel

### Method 2: Quick Test Scene

Run this in Blender's Python Console to create a test trunk:

```python
import bpy

# Delete default objects
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete()

# Create simple trunk curve
bpy.ops.curve.primitive_bezier_curve_add(location=(0, 0, 0))
trunk = bpy.context.active_object
trunk.name = "TreeTrunk"

# Make it vertical
trunk.scale.z = 5
bpy.ops.object.transform_apply(scale=True)

# Now run the setup_tree_generator.py script
exec(open(r"D:\Stephko_Tooling\Toolings\Blender\Geonodes\setup_tree_generator.py").read())
```

---

## Current Features (Phase 1 MVP)

### ✅ Implemented

- **Input Processing:**
  - Mesh edge to curve conversion
  - Curve resampling for even point distribution
  - Attribute initialization

- **Core Branch Generation:**
  - Iterative branch spawning using Repeat Zones
  - Configurable iteration depth (0-10 levels)
  - Random spawn point selection along parent curves
  - Basic growth direction (parent normal + randomness)

- **Geometry Building:**
  - Curve to mesh conversion
  - Radius control via attributes
  - Smooth shading
  - Circular branch profiles (8 vertices)

- **User Parameters:**
  - Base Thickness (0.01 - 2.0m)
  - Branch Length (0.1 - 10.0m)
  - Iterations (0 - 10 levels)
  - Random Seed (reproducible randomness)
  - Angular Spread (0.0 - 1.0, controls chaos)

### 🔄 Coming Soon (Phase 2+)

- Thickness/length decay per iteration
- Sun direction (phototropism)
- Gravity effect
- Wind noise
- Canopy system
- Leaf/asset scattering
- Advanced growth forces

---

## Node Organization

The setup script creates **5 organized frames:**

1. **INPUT PROCESSING** (Green)
   - Mesh to Curve conversion
   - Curve resampling
   - Normal setting

2. **ATTRIBUTE INITIALIZATION** (Blue)
   - `iteration_level` storage
   - `branch_id` storage
   - `branch_thickness` storage
   - `curve_parameter` storage

3. **BRANCH GENERATION** (Red)
   - Repeat Zone for iterations
   - Spawn point sampling
   - Curve line creation
   - Geometry joining

4. **GROWTH DIRECTION** (Orange)
   - Normal calculation
   - Random variation
   - Vector blending
   - Direction normalization

5. **GEOMETRY BUILDER** (Purple)
   - Radius assignment
   - Curve to Mesh conversion
   - Profile creation
   - Shade smoothing

---

## Parameter Guide

### Base Thickness
- **Range:** 0.01 - 2.0m
- **Default:** 0.1m
- **Effect:** Controls the radius of the trunk and all branches
- **Tips:**
  - 0.05-0.1 for small trees/bushes
  - 0.2-0.5 for medium trees
  - 0.5-2.0 for large/ancient trees

### Branch Length
- **Range:** 0.1 - 10.0m
- **Default:** 1.0m
- **Effect:** How long each branch segment grows
- **Tips:**
  - Lower values (0.5-1.5): Compact, bushy trees
  - Higher values (2-5): Sprawling, dramatic trees

### Iterations
- **Range:** 0 - 10 levels
- **Default:** 2
- **Effect:** How many times to subdivide branches
- **Tips:**
  - 0 = Just the trunk
  - 1 = Trunk + main branches
  - 2 = Trunk + main + sub-branches
  - 3+ = Increasingly complex/dense
  - **Warning:** 5+ can be very slow!

### Random Seed
- **Range:** 0 - 999,999
- **Default:** 0
- **Effect:** Generates different tree variations
- **Tips:**
  - Change to get completely different tree shapes
  - Same seed = same tree (reproducible)
  - Useful for forest variations

### Angular Spread
- **Range:** 0.0 - 1.0
- **Default:** 0.3
- **Effect:** How chaotic/random branch directions are
- **Tips:**
  - 0.0 = Perfectly straight (boring)
  - 0.2-0.4 = Natural looking
  - 0.6-0.8 = Wild/chaotic
  - 1.0 = Complete chaos

---

## Troubleshooting

### "No active object" error
- **Solution:** Select your curve object before running the script

### Branches don't appear
- **Check:** Iterations > 0
- **Check:** Branch Length > 0
- **Check:** Base Thickness > 0
- **Try:** Increase Angular Spread to 0.5

### Blender freezes/very slow
- **Cause:** Too many iterations or high resample count
- **Solution:**
  - Reduce Iterations to 2-3
  - Lower resample count in script (default: 20)
  - Disable viewport real-time update

### Branches look angular/blocky
- **Cause:** Low profile resolution
- **Solution:** Edit `curve_circle.inputs['Resolution']` in script
  - Default: 8 vertices
  - Recommended: 8-12 (balance quality/speed)
  - High quality: 16-24 (slow)

### Can't find modifier
- **Check:** Modifier is named "ProceduralTreeGenerator"
- **Location:** Modifier Properties panel (wrench icon)
- **Look for:** Geometry Nodes modifier

---

## Advanced Usage

### Editing the Node Tree

After running the script, you can manually edit the node tree:

1. Select your object
2. Go to Geometry Nodes workspace (top menu)
3. You'll see the organized frames
4. Add your own nodes/modifications

### Custom Trunk Shapes

Instead of a simple curve, create interesting trunks:

```python
# Y-shaped trunk
bpy.ops.curve.primitive_bezier_curve_add()
trunk = bpy.context.active_object
trunk.data.splines[0].bezier_points[1].co.z = 2
trunk.data.splines[0].bezier_points[1].handle_right.x = 1

# Add second branch
bpy.ops.object.mode_set(mode='EDIT')
bpy.ops.curve.extrude()
# Move to create Y-shape
```

### Saving as Asset

To reuse your tree generator:

1. In Geometry Nodes editor, click the shield icon next to node group name
2. Choose "Mark as Asset"
3. Save your .blend file
4. Access from Asset Browser in future projects

---

## Performance Tips

### For Viewport Work:
- Keep iterations at 2-3
- Use low resample count (10-20)
- Disable modifier viewport visibility when not editing

### For Final Render:
- Increase to 4-5 iterations
- Higher resample count (50-100)
- Enable only for final render

### Memory Optimization:
- Avoid iterations > 6
- Lower branch count per iteration
- Use instancing for leaves (Phase 6)

---

## Next Steps

### Immediate Improvements You Can Make:

1. **Add thickness decay:**
   - Add Math nodes to reduce branch_thickness per iteration
   - Multiply by 0.7 each level

2. **Add length decay:**
   - Scale Branch Length based on iteration level
   - Use index from Repeat Zone

3. **Improve spacing:**
   - Add Poisson Disk Sampling for better distribution
   - Avoid branches too close together

4. **Add gravity:**
   - Add Vector (0, 0, -1) to growth direction
   - Weight by iteration level (more droop on small branches)

### Watch for Future Updates:

- **Phase 2:** Natural growth forces (sun, gravity, wind)
- **Phase 3:** Canopy system (growth boundaries)
- **Phase 4:** Mesh canopy integration
- **Phase 5:** Leaf scattering system
- **Phase 6:** Polish and optimization

---

## File Structure

```
Toolings/Blender/Geonodes/
├── setup_tree_generator.py          # Main setup script
├── TreeGenDocu/
│   ├── ProceduralTreeGenerator_Specification.md  # Full specification
│   └── SETUP_INSTRUCTIONS.md         # This file
└── GN_treeGenerator_02.blend         # Example file (will be created)
```

---

## Technical Details

### Attributes Created:

| Name | Type | Usage |
|------|------|-------|
| `iteration_level` | Int | Generation depth (0=trunk) |
| `branch_id` | Int | Unique identifier |
| `branch_thickness` | Float | Radius for mesh |
| `curve_parameter` | Float | Position along curve [0-1] |

### Node Count: ~35 nodes (Phase 1)
### Frame Count: 5 organized sections
### Blender Version Required: 4.0+ (Repeat Zones)
### Recommended: Blender 4.5+

---

## Support

### Issues/Questions:
- Check specification: `ProceduralTreeGenerator_Specification.md`
- Review troubleshooting section above
- Verify Blender version (4.5+ recommended)

### Modification:
- Script is fully commented
- Feel free to customize
- Frames keep organization clean

---

**Happy Tree Growing! 🌳**

---

*Last Updated: 2025-12-03*
*Author: Stephan Viranyi (Stephko)*
*Status: Phase 1 Complete - MVP Functional*
