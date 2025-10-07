# ST3E 3ds Max Scripts & Modifiers Documentation

**Author:** Stephan Viranyi (https://www.artstation.com/stephko)  
**Contact:** stephko@viranyi.de

## Overview

ST3E is a comprehensive collection of MaxScript tools and custom modifiers designed to enhance 3ds Max modeling workflows. The suite focuses on Edit Poly operations, viewport feedback, stack management, and procedural workflows.

---

## Installation

### Scripts Installation
Place the `ST3E` and `Startup` folders in:
```
Program Files/[MaxRoot]/scripts/
```

### Modifiers Installation
Place contents of `Custom Modifiers` folder in:
```
C:\Program Files\Autodesk\Max_Root\Plugins
```

**Warning:** Contains experimental/work-in-progress features. Some scripts may not function as expected.

---

## Core Categories

### 1. Selection Tools (ST3E_Modelling)

#### **PolySelectHalfFromBoundry.mcr**
- **Purpose:** Selects half of a mesh based on boundary vertices/edges
- **Features:**
  - Converts vertex/edge selections to face boundaries
  - Iteratively grows selection from boundary
  - Handles Edit Poly modifiers and Editable Poly
- **Usage:** Select boundary verts/edges, run script to select connected half

#### **PolySelectExtended.mcr**
- **Select by Angle:** Toggle-based angle selection for faces (5°, 10°, 25°, 45°)
- **Select Ngons:** Selects faces with 4+ sides
- **Select Triangles:** Selects 3-sided faces
- **Select Half X/Y/Z:** Selects half of mesh along axis
- **Works with:** Edit Poly and Unwrap UVW modifiers

#### **PolyDotRingDotGapQuickSelect.mcr**
- **Dot Ring:** Select every nth edge in ring pattern (2nds, 3rds, 4ths, 5ths, 6ths)
- **Dot Loop:** Select every nth edge in loop pattern (2nds, 3rds, 4ths, 5ths)
- **Requires:** PolyBoost plugin

#### **PolySelectFacesWithMultiSG.mcr**
- **Purpose:** Selects faces with multiple smoothing groups assigned
- **Use Case:** Finding problematic smoothing on meshes

#### **WIP_PolySplineSmartSelectMaterialID.mcr**
- **Purpose:** Select by Material ID for Edit Poly, Edit Spline, and Unwrap UVW
- **Features:**
  - Multi-selection support
  - Works across different modifier types
  - Accumulates selections from multiple material IDs

---

### 2. Editing Operations (ST3E_Editing)

#### **PolySmartCreateNewBase.mcr**
- **Context-Sensitive Creation:**
  - **Vertex mode:** Cut tool
  - **Border mode:** Cap border
  - **Edge mode:** Bridge edges or create edge
  - **Face mode:** Create face or bridge polygons
- **Based on:** Per128's original concept, adapted for Edit Poly

#### **PolySmartTargetWeld.mcr**
- **Purpose:** Automatically switches to vertex mode and activates weld
- **Simplifies:** Target weld workflow

#### **PolySmartRemove.mcr**
- **Smart Deletion:**
  - **Multiple objects/no subobject:** Deletes entire selection
  - **Vertex mode:** Remove vertices
  - **Edge mode:** Remove edges (Ctrl: remove vertices too)
  - **Face/Element:** Delete faces
  - **Splines:** Delete spline segments

#### **PolySmartCollapse.mcr**
- **Context-Sensitive Collapse:**
  - **Vertex mode:** Collapse vertices
  - **Edge/Border mode:** Collapse edges
  - **Face/Element mode:** Collapse faces
  - **Spline mode:** Weld spline segments

#### **PolyChamferNoSmoothing.mcr**
- **Purpose:** Opens chamfer dialog with custom defaults
- **Defaults:**
  - Quad mitering
  - 0 segments
  - Smoothing OFF
- **Reason:** Workaround for 3ds Max 2021's annoying chamfer defaults

#### **PolyConnects.mcr**
- **Connect 1-8:** Quick connect with 1-8 segments
- **Connect1AndCap:** Context-sensitive connect/cap
  - Vertex: Connect vertices
  - Edge: Connect edges
  - Border: Cap border
- **Works with:** Edit Poly and Edit Spline

#### **PolyAutoSmoothHelpers.mcr**
- **Quick AutoSmooth:** 15°, 30°, 45°, 60°, 75°, 90°, 180°
- **Feature:** Retains custom value in command panel
- **Requires:** Face mode (4) or Element mode (5)

#### **PolySnapToLocalCenter.mcr**
- **Center X/Y/Z:** Snaps selection to local center on specified axis
- **Works with:**
  - Object level (multiple objects)
  - Subobject level (verts, edges, faces)
  - Edit Poly modifiers and Editable Poly

#### **PolyFlowTools.mcr**
- **Flow Unconstrained:** Applies flow without constraints
- **Temporarily disables:** Edge/Face/Normal constraints during operation

#### **PolyLoopTools.mcr**
- **Relax Loop:** Relaxes edge loops (no auto-loop)
- **Center Loop:** Centers edge loops (no auto-loop)
- **Straighten Unconstrained:** Straightens with/without even spacing
- **All operations:** Temporarily disable constraints

#### **PolyWeldBorders.mcr**
- **Purpose:** Finds first Edit Poly or base Editable Poly
- **Action:** Selects open edges → converts to vertices → opens weld dialog
- **Use Case:** Welding split-apart models

#### **PolyVertWeightSmoothFace.mcr**
- **Dual Purpose:**
  - **Vertex/Edge mode:** Toggle vertex weight (1.0 ↔ 1.01) for "corner" workflow
  - **Face/Element mode:** Smooth all faces to 180° (single smoothing group)
- **Use Case:** Smoothing Group from Vertex Boundary workflow

---

### 3. Stack Management (ST3E_StackManagement)

#### **JumpToEditableAndExit.mcr**
- **Smart Navigation:**
  - If no subobject: Toggle show end result (primitives) or jump to first Edit Poly/Spline
  - If in subobject: Exit to object level
  - If at object level: Jump to first Edit Poly/Spline modifier or base editable
- **Settings:**
  - Edit Poly: Jump to face mode (4)
  - Edit Spline: Jump to vertex mode (1)

#### **CollapseStackRetainInstance.mcr**
- **Purpose:** Collapses stack while retaining instances
- **Method:** Uses `maxOps.CollapseNodeTo` on selection
- **Use Case:** Batch collapse while maintaining instance relationships

---

### 4. Viewport Inspection (ST3E_Inspection)

#### **DisplayMaterialIDsInViewport.mcr**
- **Toggle-based viewport overlay** showing Material IDs at face centers
- **Features:**
  - Works with Edit Poly modifier and Editable Poly
  - Color-coded text display
  - Performance-optimized caching
- **Controls:** Toggle on/off with button (checked state)

#### **DisplayKnotPointsInViewport.mcr**
- **Purpose:** Displays knot points for splines in viewport
- **Features:**
  - White circles for unselected knots
  - Red circles for selected knots
  - Works with SplineShape and Line objects

#### **DisplayObjectNamesInViewport.mcr**
- **Viewport Display:**
  - Object names at pivot positions
  - Position coordinates
  - 3D cross at pivot
  - Group indicators (green for groups)
- **Features:**
  - Selected objects in red
  - Hidden objects excluded

#### **ShowCage.mcr**
- **Purpose:** Toggles show cage (no undo)
- **Checked state:** Reflects current cage visibility
- **Use Case:** Quick cage toggle during modeling

#### **SmartIsolate.mcr**
- **Smart Isolation Toggle:**
  - Same/no selection: Exit isolate
  - Changed selection: Re-enter isolate with new selection
  - Prevents camera/zoom changes during isolation
- **Requires:** 3ds Max 2013+

#### **InverseSeeThrough.mcr**
- **Ghost Mode:** Makes everything EXCEPT selection transparent
- **Toggle:** Same selection exits ghost mode
- **Use Case:** Aligning geometry tucked under other objects

#### **WireframeEdgeFaceOff.mcr**
- **Smart Toggle:**
  - Edged Faces OFF → Edged Faces ON
  - Edged Faces ON → Wireframe ON (Edged Faces OFF)
  - Wireframe ON → Both OFF
- **Integration:** Logical progression for topology inspection

#### **ToggleVertexColor.mcr**
- **Three-State Toggle:**
  1. Vertex Colors OFF
  2. Vertex Colors ON
  3. Vertex Colors ON + Shaded
- **Cycles through:** All three states

---

### 5. Viewport Overlay System (Startup/ViewportOverlay.ms)

**Automatic visual feedback system** that runs on startup:

#### **Edit Mode Indicators:**
- **Edit Poly/Spline:** Yellow border
- **Show End Result ON:** Blue border
- **Subobject Mode Borders:**
  - Vertex: Blue dotted
  - Edge: Teal solid (2px)
  - Border: Orange solid (2px)
  - Face: Orange solid (4px)
  - Element: Orange solid (8px)

#### **Constraint Indicators:**
- **Edge Constraint:** Orange right border
- **Face Constraint:** Orange left border
- **Normal Constraint:** Orange top border
- **Visual feedback:** Colored screen borders

#### **Statistics Display:**
- Type, Name, Modifier, Subobject Level
- Centered at top of viewport
- Yellow text

---

### 6. Coordinate System Tools (ST3E_CoordinateSystem)

#### **PickDirectly.mcr**
- **Pick and Apply:** Pick object, set as coordinate system for all transform modes
- **PickCoordsysDirectlyAndCenterPivot:** Also sets transform center

#### **SmartConstraint.mcr / SmartConstraint2.mcr**
- **Mouse Position Based:**
  - Top: Normal constraint
  - Right: Edge constraint
  - Left: Face constraint
  - Bottom: No constraint
- **SmartConstraint2 Features:**
  - Pie menu style UI with visual feedback
  - Confirmat on radius exceeded
  - No undo for uninterrupted workflow

#### **PolyConstraintsExtended.mcr**
- **No-Undo Constraint Toggles:**
  - Toggle Edge ↔ Normal
  - Toggle Edge ↔ Face ↔ Normal (full cycle)
  - Individual toggles for Edge, Face, Normal
- **Checked state:** Shows active constraint

---

### 7. Scene Management (ST3E_Management)

#### **CleanCollapse.mcr**
- **Purpose:** Duplicates selection and attaches to single clean mesh
- **Features:**
  - User input for mesh name
  - Creates mesh at 0,0,0 pivot
  - Deletes original geometry
  - Filters to GeometryClass only

#### **ResetPositionRotationScale.mcr**
- **Three Scripts:**
  - Reset Position: Sets pos to [0,0,0]
  - Reset Rotation: Resets rotation (preserves position)
  - Reset Scale: Sets scale to [1,1,1]

#### **AddTurnToPoly.mcr**
- **Purpose:** Adds Turn To Poly modifier to selection
- **Use Case:** FBX export to retain polygons
- **Smart:** Doesn't add multiple instances

#### **RemoveTurnToPoly.mcr**
- **Purpose:** Removes topmost Turn To Poly modifier
- **Smart:** Handles instances (only processes one per instance group)

#### **ExtractReference.mcr**
- **Extract Master:** Extracts base object from reference
- **Select Instances+References:** Selects all instances and references
- **Select References:** (WIP) Attempts to select only references

#### **AppendBoundsSuffix.mcr**
- **Purpose:** Adds object dimensions to name
- **Format:** `ObjectName_XXXxYYYxZZZ`
- **Example:** `Box_100x050x200`

#### **OpenLayerManager.mcr**
- **Purpose:** Toggle-friendly Layer Explorer
- **Checked state:** Shows if Layer Explorer is open

---

### 8. Modifier Button Replacements (ST3E_ModifierButtons)

Provides hotkey/toolbar access to modifiers:

#### **Standard Modifiers:**
- Symmetry, Mirror, Edit Poly, Edit Mesh, Edit Spline
- VolumeSelect, DeleteMesh, Chamfer, Push, Relax
- SmoothModifier, ProOptimizer, Optimize
- XForm, STL_Check, DataChannelModifier
- QuadCap, Quad_Chamfer, Materialmodifier
- SplineOffset

#### **Custom Modifiers:**
- Shift SG, Shift MatID, Split Mesh
- Simple Scale, Simple Offset, Simple Cylindrify, Simple Boxify, Simple Spherify
- Poly Detach, Poly Outline, Poly Inset, Poly Bevel, Poly Extrude
- Poly Extrude Along Spline, Poly AutoSmooth, Poly Clone, Poly Delete

#### **tySelect Support:**
- Add tySelect modifier
- Add tySelect Face mode

---

## Custom Modifiers

### SimpleMod Modifiers (Work on any geometry)

#### **Simple Scale** (Modifier_SimpleMod_Scale.ms)
- **Parameters:** X/Y/Z scale multiplier
- **Gizmo:** Adjustable position, rotation, scale
- **Use Case:** Non-destructive scaling with gizmo control

#### **Simple Offset** (Modifier_SimpleMod_Offset.ms)
- **Local/World Space:** Separate offset controls
- **Align Options:** Min/Center/Max alignment on each axis
- **Gizmo:** Full transform control from node/object
- **Version:** 1.00 (2023)

#### **Simple Cylindrify** (Modifier_SimpleMod_Cylindrify.ms)
- **Purpose:** Morphs geometry toward cylinder shape
- **Parameters:** 
  - Percent (0-100%)
  - Center threshold
- **Original:** Based on Garp's Cylindrify

#### **Simple Boxify** (Modifier_SimpleMod_Boxify.ms)
- **Purpose:** Morphs geometry toward box shape
- **Parameters:**
  - Percent (0-100%)
  - Center threshold per axis (X/Y/Z)

#### **Simple Spherify** (Modifier_SimpleMod_Spherify.ms)
- **Purpose:** Morphs geometry toward sphere
- **Gizmo Size Modes:**
  - From Mesh Extents (automatic)
  - From Absolute Value (manual)

#### **Simple Pinch** (Modifier_SimpleMod_Pinch.ms)
- **Purpose:** Pinch effect with parabolic falloff
- **Per-Axis Control:** X/Y/Z percent (-1000% to 200%)
- **Gizmo Size Modes:** Mesh extents or absolute value

---

### SimpleMeshMod Modifiers (Work on mesh geometry)

#### **Vertex Weight/Color Transfer** (Modifier_SimpleMesh_VertWeightTransfer.ms)
- **Weight → Color:** Transfer vertex weight to vertex color
- **Color → Weight:** Transfer vertex color to vertex weight
- **Modes:** Total vertices or selected vertices
- **Use Case:** Visualizing or transferring weight data

#### **Shift Material IDs** (Modifier_SimpleMesh_ShiftMaterialID.ms)
- **Shift:** Offset Material IDs by value (-32 to +32)
- **Quick Offsets:** ±5, ±10, ±100 buttons
- **Circular:** Wraps at Material ID 1
- **Modes:** Selected faces or total faces

#### **Shift Smoothing Groups** (Modifier_SimpleMesh_ShiftSmoothingGroups.ms)
- **Shift:** Offset SGs by value (-32 to +32)
- **Quick Offsets:** ±4, ±8, ±16 buttons
- **Circular:** Wraps within 32 smoothing groups
- **Use Case:** Adjust SG ranges non-destructively

#### **SG from Material ID** (Modifier_SimpleMesh_SGFromMaterialID.ms)
**Version:** 0.80 (2024)

**Purpose:** Assigns smoothing groups based on Material IDs

**Distribution Methods:**
- **Smart Neighbour:** Assigns SG based on neighbors (avoids conflicts)
- **Linear Modulo:** 1:1 mapping with circular range (MatID 1→SG 1, etc.)

**Features:**
- Poly Neighbour mode (more precise, slower)
- Fallback SG when all occupied
- Range control (shift SG distribution)

#### **Material ID by SG** (Modifier_SimpleMesh_MaterialIDBySG.ms)
- **Purpose:** Sets Material IDs based on Smoothing Groups
- **Override Options:**
  - Zero SG faces (custom MatID)
  - Multi-SG faces (custom MatID)
- **Select Multi-SG:** Option to select problematic faces

#### **UV Offset by Material ID** (Modifier_SimpleMesh_UVOffsetByMaterialID.ms)
- **Purpose:** Creates UV atlases from Material IDs
- **Features:**
  - Tile grid (X × Y)
  - Pre-planar mapping (XY/YZ/ZX)
  - Fitting styles (Uniform/Stretch/No fit)
  - Padding control
- **Post-processing:** Normalize or keep size

#### **Split Mesh** (Modifier_SimpleMesh_SplitMesh.ms)
- **Split Modes:**
  - Split Selection(s)
  - Split Extrude Selection(s)
  - Extrude Selection(s)
  - Edge Extrusion(s)
- **Options:**
  - Split by Material ID
  - Create duplicate
  - Flip normals
- **Parameters:** Base offset, split distance, height offset

#### **Corner Set/Select** (Modifier_SimpleMesh_CornerSetSelect.ms)
**Version:** 1.00 (2023)

**Purpose:** Defines corners from topology

**Corner Types:**
- Outer Open Corners
- Inner Open Corners
- Intersections

**Border Detection:**
- Open borders
- Material ID intersections
- Smoothing Group intersections
- Face selection boundaries

**Output Options:**
- Select corners
- Corner → Vertex Color
- Corner → Vertex Weight

**Use Case:** Define corners for procedural workflows (e.g., with SG from Vertex Boundary)

#### **SG from Vertex Boundary** (Modifier_SimpleMesh_SGFromVB.ms)
**Purpose:** Creates smoothing groups from vertex boundaries (weight/color)

**Boundary Input:**
- Vertex Color threshold
- Vertex Weight threshold (≥1.01 for "corners")

**Distribution Methods:**
- **Smart Neighbour:** SG based on neighbors
- **Naive Linear:** Linear mapping with range
- **Draft by Angle:** AutoSmooth with shift

**Stray Handling:**
- Stray-by-Stray
- Smooth adjacent strays
- Smooth by angle
- Specific smoothing group

**Rebuild Modes:**
- On Vert Change (faster, cached)
- Continuous (slower, always rebuilds)
- Manual Only

**Performance:**
- Cached groups (only rebuilds on topology/boundary change)
- Start from Poly option (more accurate)

**Use Case:** Procedural smoothing workflows where corners are defined earlier in stack

#### **Vertex Color Mod** (Modifier_SimpleMesh_VertexColorMod.ms)
**Version:** 0.80 (2024)

**Purpose:** Advanced vertex color operations with effects

**Output Channels:**
- Vertex Color (0)
- Vertex Illumination (-1)
- Vertex Alpha (-2)
- Custom Vertex Mapping (user-defined)

**Effects:**
1. **Fill:** Solid color
2. **Vertex Normal:** Normal direction as color
3. **Position:** Gradient from position (normalized/world)
4. **Distance:** Distance from point with radius
5. **Gradient Remapping:** Remap existing colors
6. **Curvature:** Convex/concave detection (WIP)
7. **HSL Adjustment:** Hue/Saturation/Lightness shifts

**Adjustments:**
- Pre-offset, Multiply, Power, Gamma
- Parabolic curve
- Monochrome conversion
- Invert effect

**Blend Modes:**
- Replace, Multiply, Screen, Overlay
- Opacity control

**Soft Selection:** Respects soft selection for blending

---

### Edit Poly Extension Modifiers

These extend the Edit Poly modifier interface (Max 2017+):

#### **Poly Outline Faces** (Modifier_EPoly_outline.ms)
- **Purpose:** Outline with Edge Crease retention
- **Parameters:** Amount (worldUnits)
- **Features:** Uses stack selection, face mode

#### **Poly Inset Faces** (Modifier_EPoly_inset.ms)
- **Purpose:** Inset with Edge Crease retention
- **Parameters:** 
  - Amount (worldUnits)
  - Type: Group or By Polygon

#### **Poly Extrude** (Modifier_EPoly_extrude.ms)
- **Purpose:** Extrude faces
- **Parameters:**
  - Height (worldUnits)
  - Bias (0-1)
  - Type: Group, Local Normal, By Polygon

#### **Poly Bevel** (Modifier_EPoly_bevel.ms)
- **Purpose:** Bevel faces
- **Parameters:**
  - Height, Outline, Bias
  - Type: Group, Local Normal, By Polygon

#### **Poly Delete** (Modifier_EPoly_delete.ms)
- **Purpose:** Delete faces (retains Edge Weight/Crease unlike DeleteMesh)
- **Operation:** Delete Face

#### **Poly Detach** (Modifier_EPoly_detach.ms)
- **Purpose:** Detach faces
- **Operation:** Detach

#### **Poly Clone** (Modifier_EPoly_clone.ms)
- **Purpose:** Clone faces
- **Operation:** Clone

#### **Poly AutoSmooth** (Modifier_EPoly_autoSmooth.ms)
- **Purpose:** AutoSmooth with stack selection
- **Parameters:** Smooth Angle (1-180°)
- **Note:** Requires face selection in stack

#### **Poly Connect Verts** (Modifier_EPoly_connect.ms)
- **Purpose:** Connect vertices
- **Parameters:** Smooth Angle (for resulting edges)
- **Selection:** Vertex mode only

#### **Poly Extrude Along Spline** (Modifier_EPoly_extrudeAlongSpline.ms)
- **Purpose:** Extrude faces along spline path
- **Parameters:**
  - Spline picker
  - Align to face normal (boolean)
  - Rotation, Segments
  - Taper Amount/Curve, Twist

---

## Graveyard Modifiers (MVP-Graveyard)

**Note:** Experimental/incomplete modifiers. May not function correctly.

- **Modifier_SimpleMesh_GrowSGs.ms:** Grow smoothing groups (incomplete)
- **Modifier_SimpleMesh_Outline.ms:** Toon outline via flipped normals
- **Modifier_SimpleMesh_RelaxBySG.ms:** Relax by smoothing groups (WIP)
- **Modifier_SimpleMesh_SliceGrid.ms:** Slice mesh in grid pattern (incomplete)
- **Modifier_SimpleMesh_SmoothToAdjecent.ms:** Smooth to adjacent SG (incomplete)
- **Modifier_Curve.ms:** Curve modifier (incomplete implementation)
- **Modifier_SimpleMesh_MakePlanar.ms:** Make faces planar (basic)
- **Modifier_SimpleMesh_PlanarBySG.ms:** Planar operations by SG (WIP)
- **Modifier_SimpleMesh_SGFromMaterialID.ms:** SG from Mat ID (older version)

---

## Toolsets

### Material ID Toolbox (ST3E_toolsets/MatIDToolbox)

**Comprehensive Material ID management interface**

#### **Features:**
- **Info Transfer:** Display/copy Material ID string
- **Selection:** Select faces by Material ID from multi-list
- **Set Material ID:**
  - Shift (±1, ±5, ±10)
  - Set (1, 5, 10, 100, custom)
  - List-based selection
- **Modes:**
  - Edit Poly (vertex→face, edge→face, face)
  - Edit Spline
  - Material Modifier
  - Add Material Modifier

#### **UI Modes:**
- **Compact Mode:** Single-line interface
- **Full Mode:** All features with rollouts

#### **Context-Sensitive:**
- Automatically detects Edit Poly, Material Modifier
- Shows current mode with color coding
- Enables/disables operations based on context

### PolyDraw Toolset (ST3E_toolsets/PolyDraw)

**PolyDrawOptions.ms:**
- Settings dialog for PolyBoost PolyDraw tool
- Offset distance, Min distance
- Pick surface button
- **Requires:** PolyBoost plugin

---

## Object Creation Tools

### Letter Sequence Maker (ST3E_ObjectCreation/LetterSequenceMaker.ms)

**Purpose:** Batch-create text objects from sequence

**Features:**
- Custom character sequence (comma-separated)
- ABC/123 quick-add buttons
- Pick text style from existing text object
- Naming: Base name + suffix (from definition or numbered)
- Offset: X/Y/Z spacing between objects

**Use Case:** Creating alphabets, number sets, custom character sets

---

## Viewport Tools (ST3E_ViewportTools)

#### **SetViewFromClosestAngle.mcr**
- **Purpose:** Set viewport to closest orthographic angle
- **Toggle:** If already in that view, switch to perspective
- **Threshold:** 0.5 direction threshold
- **Views:** Top, Bottom, Front, Back, Left, Right

---

## Library Files (ST3E/Lib)

#### **ViewportFunctions.ms**
- `NormalizedViewportMousePos()`: Mouse position in -1 to 1 space
- `NormalizedViewportMouseAngle()`: Mouse angle 0-360° from center

#### **PolySelectExtended.ms**
- `EvaluateMode()`: Check if Select by Angle is active
- `EvaluateAngle(angle)`: Check if specific angle is active
- `SelectByAngleToggle()`: Toggle Select by Angle mode
- `SelectByAngleToggleAngle(angle)`: Toggle specific angle

#### **PolySnapToLocalCenter.ms**
- `CenterOnAxis(axis)`: Centers on X/Y/Z axis
- Global constants: `X=1`, `Y=2`, `Z=3`
- Handles constraints, soft selection, coordinate systems

---

## Workflow Integration Examples

### 1. Smoothing Group from Vertex Boundary Workflow

**Goal:** Procedural smoothing based on corner definition

**Stack Setup:**
```
1. Base Editable Poly
2. Edit Poly (select corners manually or procedurally)
3. Corner Set/Select Modifier
   - Set vertex weight to 1.01 for corners
4. Edit Poly (modeling operations)
5. SG from Vertex Boundary Modifier
   - Uses vertex weight ≥1.01 as boundaries
   - Smart Neighbour distribution
   - Auto-updates when topology changes
```

**Benefits:**
- Define corners once, inherit through stack
- Procedural smoothing survives topology changes
- No manual smoothing group assignment

### 2. Material ID Atlas Workflow

**Goal:** Create UV atlas from Material IDs

**Stack Setup:**
```
1. Base Mesh with Material IDs assigned
2. UV Offset by Material ID Modifier
   - 4×4 tile grid (16 tiles)
   - Pre-planar map (uniform fit)
   - Normalize to 0-1 space
```

**Result:** Each Material ID gets its own tile in atlas

### 3. Non-Destructive Modeling Stack

**Stack Example:**
```
1. Primitive (Box)
2. Edit Poly (base modeling)
3. Symmetry Modifier
4. Edit Poly (symmetric modeling)
5. Simple Offset (centering/repositioning)
6. Simple Scale (proportional adjustments)
7. Poly Bevel (selected faces)
8. SG from Material ID (procedural smoothing)
9. Turn To Poly (FBX export prep)
```

---

## Keyboard Shortcut Recommendations

**Selection:**
- `Q`: Select by Angle Toggle
- `Ctrl+Q`: Select Ngons
- `Shift+Q`: Select Tris

**Editing:**
- `Shift+E`: Smart Create (context-sensitive)
- `Ctrl+Backspace`: Smart Remove
- `Ctrl+Shift+Backspace`: Smart Collapse
- `Shift+W`: Target Weld
- `C`: Connect 1 Or Cap
- `Shift+C`: Connect 2-8 (numerical row)

**Constraints:**
- `Alt+X`: Smart Constraint (mouse-based)
- `Alt+C`: Constraint Toggle Edge→Normal
- `Alt+Shift+C`: Constraint Toggle Full Cycle

**Stack:**
- `Alt+Q`: Jump To Editable And Exit
- `Alt+I`: Smart Isolate

**Inspection:**
- `Alt+V`: Toggle Vertex Color
- `Alt+Z`: Wireframe/Edged Face Toggle
- `Alt+X`: Inverse See-Through

---

## Performance Considerations

### Cached Systems:
- **SG from Vertex Boundary:** Only rebuilds on topology/boundary change
- **Material ID Toolbox:** Caches material lists
- **Viewport Overlays:** Cached GW functions

### Heavy Operations:
- **Corner Set/Select:** Can be slow on dense meshes (consider Face mode)
- **Vertex Color Mod Curvature:** Experimental, performance varies
- **UV Offset by Material ID:** Pre-planar mapping on dense meshes

### Optimization Tips:
- Use "Start from Poly" mode only when precision needed
- Limit Debug messages (overhead)
- Use Manual Rebuild mode for iterative work

---

## Known Issues & Limitations

1. **PolyDraw Options:** Requires PolyBoost plugin
2. **Edit Poly Modifiers:** Require 3ds Max 2017+
3. **Smart Constraint2:** Flyout UI may not work in all viewport configurations
4. **Vertex Color Mod Curvature:** Work in progress, results may vary
5. **Reference Selection:** Incomplete (Extract Reference tool)
6. **Graveyard Modifiers:** Not fully functional, use at own risk

---

## Credits & Acknowledgments

- **Vojtech Cada:** Edit Poly modifier extension examples
- **Garp:** Original Cylindrify concept
- **Per128:** Original Smart Create concept
- **Soulburn Scripts:** Instance handling inspiration
- **Various Forum Contributors:** Code snippets and advice

---

## License & Support

**License:** Free to share and extend  
**Support:** stephko@viranyi.de  
**Portfolio:** https://www.artstation.com/stephko  
**Documentation:** https://docs.google.com/document/d/1fIKEurSNeaazzYsPnCTYT7bVO4R4btWzTzvLRpjNutY/edit?usp=sharing

**Feel free to modify and extend these tools for your own workflows. Feedback and questions are welcome!**
