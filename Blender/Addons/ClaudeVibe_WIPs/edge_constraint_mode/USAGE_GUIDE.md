# Edge Constraint Mode - Usage Guide & Examples

## Quick Start

### Installation & Activation
1. The addon is already installed at: `D:\Stephko_Tooling\Toolings\Blender\Addons\ClaudeVibe_WIPs\edge_constraint_mode`
2. In Blender: Edit > Preferences > Add-ons > Install
3. Navigate to the folder and select it
4. Enable "Mesh: Edge Constraint Mode"

### First Use
1. Select a mesh object and enter **Edit Mode** (Tab)
2. Select some vertices, edges, or faces
3. Press **N** to open the sidebar
4. Go to the **Tool** tab
5. Find the **Edge Constraint Mode** panel
6. Click **"Activate Edge Constraint Mode"**

---

## Transform Modes

### Translation (G)
- **Default mode** when activating Edge Constraint
- Move your mouse to slide selection along edges
- The geometry will follow edge paths automatically
- Can traverse across multiple edges and vertices

**Example Use Cases:**
- Adjusting the position of a loop cut while keeping it aligned with topology
- Moving vertices along curved edge flows
- Repositioning edge loops on organic models

### Rotation (R)
- Press **R** while in Edge Constraint Mode
- Horizontal mouse movement = rotation amount
- The rotation is projected onto edge tangents
- Each vertex slides along its connected edges to approximate the rotation

**Example Use Cases:**
- Twisting edge loops while maintaining topology
- Rotating selections on cylindrical forms
- Creating spiral effects along edge flows

### Scale (S)
- Press **S** while in Edge Constraint Mode
- Horizontal mouse movement = scale factor
- Scale from pivot point with motion constrained to edges
- Each vertex slides to approximate radial scaling

**Example Use Cases:**
- Expanding/contracting edge loops along surface topology
- Scaling selections on curved surfaces
- Adjusting size while maintaining edge flow

### Switching Between Modes
- Press **G** for Translation
- Press **R** for Rotation  
- Press **S** for Scale
- Can switch at any time before confirming

### Confirming/Canceling
- **Confirm:** Left Mouse Button or Enter
- **Cancel:** Right Mouse Button or Esc

---

## Settings Explained

### Constrain to Selected Edges Only
**Default:** OFF

When enabled, vertices will only slide along edges that are currently selected.

**When to use:**
- ✓ When you want precise control over which paths vertices can follow
- ✓ For creating specific edge flow modifications
- ✓ When working with complex topology and want to avoid unwanted paths

**Example:**
```
1. Select a specific edge loop
2. Enable "Constrain to Selected Edges Only"
3. Move vertices - they'll stay on that loop only
```

### Even Spacing
**Default:** OFF

Maintains uniform spacing along edges (like Blender's native Edge Slide).

**When to use:**
- ✓ When you want to preserve equal distances between vertices
- ✓ For maintaining uniform edge loops
- ✓ When creating regular patterns or subdivisions

### Clamp to Boundaries
**Default:** ON

Stops vertices at edge endpoints instead of allowing overshoot.

**When to use:**
- ✓ When working near mesh boundaries
- ✓ To prevent vertices from "jumping" past the end of an edge
- ✗ Disable if you want vertices to hit boundaries and try to continue along the next available edge

### Stop at Non-Manifold
**Default:** ON

Prevents sliding across non-manifold boundaries (edges with more than 2 faces).

**When to use:**
- ✓ When working with properly manifold meshes
- ✓ To prevent unexpected jumps at complex topology intersections
- ✗ Disable if you intentionally want to slide across non-manifold edges

### Pivot Mode

**Selection Center (Default):**
- Uses the geometric center of your selection as the pivot
- Best for most rotation and scale operations
- Automatic and intuitive

**3D Cursor:**
- Uses the 3D cursor location as the pivot
- Allows precise pivot placement
- Useful for rotation around specific points

**How to use 3D Cursor pivot:**
1. Position 3D cursor (Shift + Right Click, or View menu)
2. Set Pivot Mode to "3D Cursor"
3. Rotate or Scale - operations will use cursor as center

---

## Sensitivity Controls

### Translate Sensitivity
**Range:** 0.001 - 1.0  
**Default:** 0.01

Controls how much geometry moves relative to mouse movement.

- **Lower values** (0.001 - 0.01): Precise, fine control
- **Higher values** (0.1 - 1.0): Fast, large movements

### Rotate Sensitivity
**Range:** 0.1 - 10.0  
**Default:** 1.0

Controls rotation speed.

- **Lower values** (0.1 - 0.5): Slow, precise rotations
- **Higher values** (2.0 - 10.0): Fast rotations

### Scale Sensitivity
**Range:** 0.1 - 10.0  
**Default:** 1.0

Controls scaling speed.

- **Lower values** (0.1 - 0.5): Fine scale adjustments
- **Higher values** (2.0 - 10.0): Rapid scaling

---

## Practical Examples

### Example 1: Adjusting a Face Loop on a Cylinder

```
Scenario: You have a cylinder and want to move a horizontal edge loop up/down 
while keeping it perfectly aligned with the vertical edges.

Steps:
1. Select the horizontal edge loop (Alt + Click edge)
2. Activate Edge Constraint Mode
3. Move mouse vertically
4. The loop slides along the vertical edges
5. Confirm with LMB
```

### Example 2: Rotating Geometry on a Sphere

```
Scenario: You want to rotate vertices around a sphere while keeping them 
on the surface topology.

Steps:
1. Select vertices on the sphere
2. Set Pivot Mode to "Selection Center"
3. Activate Edge Constraint Mode
4. Press R for Rotation
5. Move mouse horizontally to rotate
6. Vertices will slide along edges to approximate the rotation
7. Confirm with LMB
```

### Example 3: Precise Edge Flow Adjustment

```
Scenario: You need to adjust an edge loop but only along specific edges.

Steps:
1. Select the edge loop you want to adjust
2. Also select the edges you want it to slide along
3. Enable "Constrain to Selected Edges Only"
4. Activate Edge Constraint Mode
5. Adjust position
6. The loop will only follow the selected edge paths
```

### Example 4: Creating a Twist Effect

```
Scenario: Create a twisted effect on a cylindrical object.

Steps:
1. Select alternating horizontal edge loops
2. Set Pivot Mode to "3D Cursor"
3. Position cursor at cylinder center
4. Activate Edge Constraint Mode
5. Press R for Rotation
6. Adjust Rotate Sensitivity if needed
7. Rotate to create twist
8. Each ring rotates while staying on the surface
```

### Example 5: Organic Model Adjustment

```
Scenario: Adjusting topology on an organic character model.

Steps:
1. Select vertices you want to reposition
2. Enable "Stop at Non-Manifold" (recommended)
3. Set Translate Sensitivity to 0.01 for precision
4. Activate Edge Constraint Mode
5. Make fine adjustments
6. Vertices will follow the natural edge flow
7. Preserve the organic topology structure
```

---

## Troubleshooting

### "Must be in Edit Mode on a mesh object"
**Solution:** Make sure you're in Edit Mode (Tab) with a mesh object selected.

### "No vertices selected"
**Solution:** Select at least one vertex, edge, or face before activating.

### Vertices not moving as expected
**Check:**
- Are you constraining to selected edges only? Try disabling.
- Is "Clamp to Boundaries" preventing movement?
- Try adjusting sensitivity settings
- Make sure vertices have connected edges to slide along

### Movement seems jerky or jumpy
**Solutions:**
- Increase mouse sensitivity (move mouse more slowly)
- Decrease transform sensitivity setting
- Check if "Stop at Non-Manifold" is causing issues

### Rotation/Scale not working well
**Solutions:**
- Adjust pivot mode (try Selection Center vs 3D Cursor)
- Increase sensitivity for more dramatic effects
- Remember: these operations are approximated through edge sliding

### Addon not showing in sidebar
**Solution:** 
- Press N to show sidebar if hidden
- Make sure you're in Edit Mode
- Check that addon is enabled in Preferences

---

## Advanced Tips

### Combining with Other Blender Tools

**Works well with:**
- Loop Cut (Ctrl + R) - create loops, then constrain them
- Proportional Editing - can be combined for smooth adjustments
- Bevel (Ctrl + B) - bevel then constrain to adjust

**Use before:**
- Solidify modifier
- Subdivision Surface
- Skin modifier

### Workflow Integration

**Retopology Workflow:**
1. Use Edge Constraint to adjust retopo loops along surface
2. Keep clean edge flow by constraining to selected edges
3. Fine-tune with low sensitivity settings

**Hard Surface Modeling:**
1. Create base topology
2. Use Edge Constraint to adjust chamfers and bevels
3. Maintain precise edge alignment

**Character Modeling:**
1. Adjust muscle flows and edge loops
2. Use rotation for creating natural twists
3. Scale for bulging effects while staying on topology

### Keyboard Shortcuts Summary

| Action | Key |
|--------|-----|
| Enter Edit Mode | Tab |
| Open Sidebar | N |
| Translate Mode | G |
| Rotate Mode | R |
| Scale Mode | S |
| Confirm | LMB / Enter |
| Cancel | RMB / Esc |

---

## Performance Notes

- **Best performance:** Selections under 10,000 vertices
- **Good performance:** 10,000 - 50,000 vertices
- **May slow down:** 50,000+ vertices

**Optimization tips:**
- Work on smaller sections when possible
- Disable proportional editing if not needed
- Close other heavy addons while using Edge Constraint

---

## Comparison with Native Tools

### vs. Edge Slide (GG)
| Feature | Edge Constraint | Edge Slide |
|---------|----------------|------------|
| Translation | ✓ Similar | ✓ |
| Rotation | ✓ Unique | ✗ |
| Scale | ✓ Unique | ✗ |
| Multi-edge paths | ✓ | Limited |
| Face/vert select | ✓ | Edges only |

**When to use Edge Constraint:**
- Need rotation/scale on edges
- Want to work with faces/verts directly
- Need multi-edge traversal

**When to use native Edge Slide:**
- Simple single-edge sliding
- Want the absolute fastest performance
- Using with proportional editing

### vs. Manual Transform (G/R/S)
Edge Constraint Mode provides the precision of manual transforms with the topology-awareness of edge-based tools. It's like having a smart constraint that automatically follows your mesh structure.

---

## Getting Help

### Resources
- **GitHub:** [https://github.com/Stephk0/Toolings](https://github.com/Stephk0/Toolings)
- **ArtStation:** [https://www.artstation.com/stephko](https://www.artstation.com/stephko)
- **Issues:** [GitHub Issues](https://github.com/Stephk0/Toolings/issues)

### Reporting Bugs
When reporting issues, please include:
1. Blender version
2. Addon version
3. Description of the problem
4. Steps to reproduce
5. Screenshot if applicable

### Feature Requests
We welcome feature requests! Please submit them through GitHub Issues with the "enhancement" tag.

---

**Happy modeling with Edge Constraint Mode!** 🎨
