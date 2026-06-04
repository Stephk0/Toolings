# Procedural Tree Generator - Frame Organization

**Version:** 1.1
**Date:** 2025-12-04
**Status:** ✅ Complete

## Overview

The TreeGenerator Geometry Nodes tree has been organized into **5 color-coded frames** following the Procedural Tree Generator Specification (lines 766-829). This organization provides clear visual structure and makes the complex node tree easier to understand and maintain.

---

## Frame Structure

### Frame 1: INPUT PROCESSING
- **Color:** Green (0.3, 0.5, 0.3)
- **Location:** X: -1200 to -700
- **Node Count:** 6 nodes
- **Purpose:** Initial geometry processing and preparation

**Contents:**
- Group Input
- Mesh to Curve conversion
- Curve resampling (multiple)
- Set Curve Normal

**Flow:** Receives input geometry → Converts to curves → Resamples for even distribution → Sets consistent normals

---

### Frame 2: ATTRIBUTE INITIALIZATION
- **Color:** Blue (0.3, 0.3, 0.5)
- **Location:** X: -650 to -400
- **Node Count:** 7 nodes
- **Purpose:** Initialize core attributes for branch tracking

**Contents:**
- Store Named Attribute: `iteration_level` (Int, starts at 0)
- Store Named Attribute: `branch_id` (Int, unique ID)
- Store Named Attribute: `branch_thickness` (Float)
- Store Named Attribute: `curve_parameter` (Float, 0-1)
- Index node (for ID generation)
- Spline Parameter (for curve factor)

**Flow:** Sets up the attribute system used throughout the tree for tracking branch hierarchy and properties

---

### Frame 3: BRANCH GENERATION
- **Color:** Red (0.5, 0.3, 0.3)
- **Location:** X: -350 to 500, Y: 200 (Main level)
- **Node Count:** 84 nodes (largest frame)
- **Purpose:** Core branching algorithm and iteration

**Contents:**
- **Repeat Zone Input/Output** - Main iteration container
- Random Value nodes (spawn position selection)
- Sample Curve (spawn point selection)
- Curve Line (new branch creation)
- Join Geometry (combine branches)
- Boolean logic for endpoint handling
- Curve to Points conversion
- Duplicate Elements
- Comparison and switch nodes
- Many supporting math and logic nodes

**Flow:** Iteratively generates new branches from parent curves using the Repeat Zone. Contains the majority of the branching logic including spawn point selection, branch creation, and geometry joining.

**Special Notes:**
- This frame contains the Repeat Zone, which is the heart of the iterative branch generation
- Nodes are organized in a grid (6 columns) to accommodate the large number of nodes
- Repeat Input at X:-200, Repeat Output at X:300

---

### Frame 4: GROWTH DIRECTION CALCULATOR
- **Color:** Orange (0.5, 0.4, 0.2)
- **Location:** X: -350 to 500, Y: -450 (Below main flow)
- **Node Count:** 8 nodes
- **Purpose:** Calculate branch growth directions and angles

**Contents:**
- Vector Math (normalization, scaling)
- Rotation nodes (angular control)
- Separate XYZ (coordinate manipulation)
- Noise Texture (natural variation)

**Flow:** Calculates growth vectors for new branches based on parent direction, random variation, and natural forces

**Phase 1 Implementation:**
- Parent normal inheritance
- Random angular variation
- Basic normalization

**Phase 2+ (Planned):**
- Sun direction (phototropism)
- Gravity vector
- Wind noise
- Fibonacci/golden angle distribution

---

### Frame 5: GEOMETRY BUILDER
- **Color:** Purple (0.4, 0.3, 0.5)
- **Location:** X: 550 to 1100
- **Node Count:** 8 nodes
- **Purpose:** Convert curves to final mesh geometry

**Contents:**
- Named Attribute readers (branch_thickness)
- Set Curve Radius
- Curve Circle (profile, 8 vertices)
- Curve to Mesh
- Set Shade Smooth
- Group Output

**Flow:** Reads thickness attributes → Sets curve radius → Creates circular profile → Converts to mesh → Smooths shading → Outputs final geometry

---

## Visual Layout

### Horizontal Flow (Left to Right)
```
Input → Attributes → [Branch Generation] → Geometry → Output
-1200     -650            -350 to 500         550        800
```

### Vertical Layers
```
        Main Flow (Y: 100-200)
        ┌────────────────────────────────────┐
        │  Input → Attr → Branch → Geometry  │
        └────────────────────────────────────┘
                        ↓
                        ↓
        Growth Calculation (Y: -450)
        ┌────────────────────────────────────┐
        │  Vector Math, Noise, Rotation      │
        └────────────────────────────────────┘
```

### Frame Positioning
- No overlapping frames
- 100-150 pixel spacing between frames
- Clear left-to-right signal flow
- Growth Direction positioned below to avoid clutter

---

## Color Coding Reference

| Frame | Color | RGB | Visual Purpose |
|-------|-------|-----|----------------|
| Input Processing | Green | (0.3, 0.5, 0.3) | Data entry point |
| Attribute Initialization | Blue | (0.3, 0.3, 0.5) | Data storage setup |
| Branch Generation | Red | (0.5, 0.3, 0.3) | Core algorithm |
| Growth Direction | Orange | (0.5, 0.4, 0.2) | Physics/forces |
| Geometry Builder | Purple | (0.4, 0.3, 0.5) | Mesh output |

**Future Frames (Phase 2+):**
- Decay System: Yellow (0.5, 0.5, 0.2)
- Canopy System: Cyan (0.2, 0.5, 0.5)
- Asset Scattering: Magenta (0.5, 0.3, 0.5)

---

## Node Organization Within Frames

### General Principles
1. **Left-to-right flow:** Nodes arranged to follow data flow direction
2. **Grid layout:** Nodes in regular grid (3-6 columns depending on frame)
3. **Spacing:** 150-250px horizontal, 100-120px vertical
4. **No stacking:** Nodes don't overlap
5. **Repeat Zone:** Clearly visible with input/output nodes positioned prominently

### Specific Frame Layouts

**Input Processing:** 3 columns, vertical flow
**Attribute Initialization:** 3 columns, attribute setup sequence
**Branch Generation:** 6 columns, grid layout (due to 84 nodes)
**Growth Direction:** 4 columns, calculation sequence
**Geometry Builder:** 3 columns, conversion pipeline

---

## Re-organizing the Tree

If you need to re-apply this organization:

### Method 1: Run the Organization Script
```python
# In Blender's Scripting workspace
# Open: TreeGenDocu/organize_node_frames.py
# Press: Alt+P or click "Run Script"
```

### Method 2: Manual Organization
1. Open Geometry Node Editor
2. Select TreeTrunk_Mesh object
3. View TreeGenerator node group
4. Create frames (Shift+A → Layout → Frame)
5. Set frame colors (Frame Properties panel)
6. Parent nodes to frames (drag or Ctrl+P)
7. Position frames and nodes

---

## Implementation Notes

### Current Status (Phase 1 MVP)
- ✅ 5 frames created and color-coded
- ✅ 113 nodes organized
- ✅ Frames positioned to avoid overlaps
- ✅ Left-to-right flow maintained
- ✅ Proper spacing implemented
- ✅ Repeat Zone clearly contained

### Known Issues
- Some nodes in Branch Generation frame may benefit from further sub-categorization in future phases
- Viewer nodes (debugging) are currently in Branch Generation frame

### Future Enhancements (Phase 2+)
- Add Frame 6: Decay System (thickness/length decay logic)
- Add Frame 7: Canopy System (growth boundaries)
- Add Frame 8: Asset Scattering (leaf placement)
- Sub-frames within Branch Generation for better organization
- Reroute nodes for long connections

---

## Specification Compliance

This organization follows the **Procedural Tree Generator Specification v1.0**:
- Section: "Frame Organization & Naming" (lines 760-911)
- Frame colors match specification exactly
- Frame positioning follows specification guidelines
- Node types assigned to correct frames
- Naming conventions followed (ALL CAPS for frames)

---

## Viewing the Organized Tree

### In Blender
1. Select the `TreeTrunk_Mesh` object
2. Open **Geometry Node Editor** (Shift+F3)
3. Ensure `TreeGenerator` node group is active
4. Press **Home** to frame all nodes
5. Use **Mouse Wheel** to zoom
6. **Middle Mouse** to pan

### Navigation Tips
- **F** - Frame selected nodes
- **Home** - Frame all nodes
- **Ctrl+Left/Right Arrow** - Navigate between frames
- **G** - Move nodes/frames
- **Shift+D** - Duplicate selection

---

## Maintenance

### When Adding New Nodes
1. Determine which frame the node belongs to based on its function
2. Parent the node to the appropriate frame (Ctrl+P)
3. Position it within the frame's grid layout
4. Maintain proper spacing (150-250px horizontal)

### When Modifying Frames
- Keep colors consistent with specification
- Maintain left-to-right flow
- Ensure no frame overlaps
- Update this documentation

---

## References

- **Specification:** `ProceduralTreeGenerator_Specification.md`
- **Setup Script:** `setup_tree_generator.py`
- **Organization Script:** `organize_node_frames.py`
- **MCP Integration:** `MCP_INTEGRATION.md`

---

**Last Updated:** 2025-12-04
**Author:** Stephan Viranyi (Stephko)
**Status:** ✅ Production Ready
