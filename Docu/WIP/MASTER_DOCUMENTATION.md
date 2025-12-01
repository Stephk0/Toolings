# Stephko Toolings - Complete Documentation

**Author:** Stephan Viranyi  
**Version:** 2024  
**License:** Free to share and extend  

---

## Table of Contents

- [Overview](#overview)
- [Blender Tools](#blender-tools)
  - [Addons](#blender-addons)
  - [Geometry Nodes](#geometry-nodes)
- [3ds Max Tools (ST3E)](#3ds-max-tools-st3e)
  - [Scripts](#scripts)
  - [Modifiers](#modifiers)
- [Unity Tools](#unity-tools)
- [Installation](#installation)
- [Support & Contact](#support--contact)

---

## Overview

Collection of production-proven tools for Blender, 3ds Max, and Unity, designed to enhance modeling workflows and boost productivity. All tools are free to use and extend.

### Quick Stats
- **Blender Addons:** 8 addons
- **Blender Geonodes:** 14+ geometry node presets
- **3ds Max Scripts:** 50+ scripts and macros
- **3ds Max Modifiers:** 24 custom modifiers
- **Tested Versions:**
  - Blender 4.5+
  - 3ds Max 2020-2023
  - Unity 2021+

---

## Blender Tools

**Tested on:** Blender 4.5+  
**Status:** Active development

All Blender addons are developed using Claude Desktop + Blender MCP integration, representing cutting-edge AI-assisted development.

### Blender Addons

#### 1. Smart Collapse
**Path:** `Blender/Addons/ClaudeVibe_WIPs/Smart Collapse/`  
**Version:** 1.0.0  
**Hotkey:** `Ctrl + Alt + X`

**Description:**
Intelligently collapses edges or merges vertices at center based on topology analysis.

**Features:**
- Topology detection: Automatically determines if edges exist between vertices
- Smart fallback: Uses edge collapse when topology exists, merge at center otherwise
- Works on 2+ selected vertices
- Single operation replaces two separate operations

**Installation:**
```
Blender > Edit > Preferences > Add-ons > Install from disk
Select: smart_collapse.py
```

**Usage:**
1. Enter Edit Mode
2. Select 2 or more vertices
3. Press `Ctrl + Alt + X` or Find in `Delete > Smart Collapse`
4. Operation automatically chooses best method

**Menu Location:** `View3D > Edit Mode > Mesh Menu > Delete > Smart Collapse`

---

#### 2. Smart Crease
**Path:** `Blender/Addons/ClaudeVibe_WIPs/Smart Crease/`  
**Version:** 1.0.0  
**Hotkey:** `Shift + E`

**Description:**
Context-sensitive crease tool with modal mouse control, numeric input, and HUD display.

**Features:**
- **Context-Sensitive:** Adapts to Vertex/Edge/Face selection modes
- **Modal Controls:**
  - Mouse drag: Smooth 0.0-1.0 adjustment
  - `Shift`: Fine-tune mode (10x reduced sensitivity)
  - `Ctrl`: Snap to 0.1 increments
  - `Alt`: Reset to 0.0
  - `V`: Toggle between 0 and 1
- **Numeric Input:** Type exact values (e.g., `0.5`, `.75`)
- **Live HUD:** Real-time value display
- **Subdivision Surface Integration:** Works seamlessly with SubD modifier

**Usage:**
1. Edit Mode > Select vertices/edges/faces
2. Press `Shift + E`
3. Drag mouse or type value
4. Confirm with `Enter` or `Left Click`

**Selection Mode Behaviors:**
- **Vertex Mode:** Edits vertex crease
- **Edge Mode:** Edits edge crease
- **Face Mode:** Edits boundary edges of selected faces

---

#### 3. Mass Collection Exporter
**Path:** `Blender/Addons/ClaudeVibe_WIPs/MassExporter/`  
**Version:** 12.0.0  
**Location:** `3D View > N-Panel > Mass Exporter`

**Description:**
Powerful batch export system with on-demand joining, empty-based organization, and Unity-optimized FBX settings.

**Key Features:**
- Export collections with per-collection settings
- Join empty children during export (non-destructive)
- Auto-move empties to origin
- Apply modifiers before join
- Unity-optimized FBX export
- Fallback to normal export when no empties present
- Material override system
- Custom axis orientation per export

**Export Options:**
- **Format Support:** FBX, OBJ, Collada (DAE), glTF 2.0
- **Transform Options:**
  - Export at origin
  - Apply transforms
  - Custom axis orientation (Forward/Up)
- **Material Options:**
  - Material override
  - M_ prefix auto-add
  - Assign to objects without materials

**Unity Integration:**
- FBX Units Scale application
- Bake space transform
- Proper axis orientation (-Z Forward, Y Up)
- Clean hierarchy import

**Usage:**
1. Open N-Panel > Mass Exporter
2. Add collections to export list
3. Configure per-collection settings:
   - Export path
   - Merge options
   - Empty origin handling
   - Join children options
4. Click "Export All Collections"

**Advanced Features:**
- **Auto-Move Empties:** Automatically center empties before export
- **Join Empty Children:** Joins ALL mesh children of empties into ONE object
- **Apply Modifiers:** Option to apply modifiers before join
- **Debug Mode:** Verbose logging for troubleshooting

---

#### 4. Smart Set Orientation
**Path:** `Blender/Addons/ClaudeVibe_WIPs/Smart Orientation/`  
**Version:** 1.5.0  
**Hotkey:** `Ctrl + D`

**Description:**
Context-aware transform orientation management that eliminates manual orientation switching.

**Features:**
- Automatic orientation detection based on context
- Custom orientation creation from selection
- Selection change detection (hash-based)
- Smart toggling between relevant orientations
- Clean integration with native transform system

**Behavior Matrix:**

| Context | Selection | First Press | Second Press |
|---------|-----------|-------------|--------------|
| Edit Mode | With Selection | Create Custom | Toggle Custom/Local |
| Edit Mode | No Selection | Local | Global |
| Object Mode | With Selection | Local | Global |
| Object Mode | No Selection | Global | - |
| Other Modes | Any | Global | - |

**Usage:**
1. Select geometry or object
2. Press `Ctrl + D`
3. Transform orientation automatically sets to optimal mode
4. Press again to toggle between relevant modes

---

#### 5. Center Loops
**Path:** `Blender/Addons/ClaudeVibe_WIPs/Center Edges/`  
**Version:** 1.5.1  
**Hotkey:** `Ctrl + Shift + C`

**Description:**
Centers edge loops and vertices for even topology maintenance.

**Features:**
- **Center Edge Loops:** Between perpendicular edges
- **Center Vertices:** Based on connected neighbors
- **Universal Compatibility:** Works with tris, quads, n-gons
- **Multiple Centering Modes:**
  - Average: Uses average of all perpendicular vertices
  - Opposite Pairs: Averages pairs of opposite vertices (optimized for quads)
- **Edge Length Weighting:** Optional weighting for vertex centering

**Use Cases:**
- Evening out edge loops in character models
- Correcting topology flow in hard surface
- Maintaining symmetry in organic modeling
- Cleaning up subdivided/extruded geometry

**Access Methods:**
- **Hotkey:** `Ctrl + Shift + C`
- **Edge Menu:** Right-click > Edge > Center Loops
- **Context Menu:** Right-click > Center Loops

---

#### 6. Toggle Modifier Display
**Path:** `Blender/Addons/ClaudeVibe_WIPs/Toggle Modifier Display/`  
**Version:** 1.3.0  
**Hotkeys:** `D` (Display), `Shift + D` (On Cage)

**Description:**
Quick keyboard shortcuts for modifier visibility in Edit Mode.

**Features:**
- **Edit Mode Only:** Prevents accidental toggling
- **Intelligent Parity System:**
  - First press: Syncs edit mode with viewport
  - Second press: Disables all
- **Multi-Object Support:** Works with Mesh, Curve, Surface, Font, Lattice
- **On Cage Toggle:** Separate control for cage display

**Workflow:**
1. Enter Edit Mode
2. Press `D`: Toggle modifiers in edit mode
3. Press `Shift + D`: Toggle on-cage display
4. Work with clean base geometry or full stack

---

#### 7. Edit Mode Overlay
**Path:** `Blender/Addons/ClaudeVibe_WIPs/Edit Mode Overlay/`  
**Version:** 1.1.0  
**Location:** `3D View > Sidebar (N) > View Tab`

**Description:**
Customizable overlay banner for edit mode awareness.

**Features:**
- Visual indicator when in any edit mode
- Fully customizable (text, colors, size, position, transparency)
- Supports all edit modes (Mesh, Curve, Armature, Metaball, Lattice, Surface, Text, Grease Pencil)
- Non-intrusive transparent overlay
- Real-time setting updates

**Customization Options:**
- **Text Settings:** Custom message, color, size factor
- **Rectangle Settings:** Width, height, color, opacity
- **Position Settings:** Distance from top, horizontal alignment, offset

**Use Cases:**
- Prevent accidental edits
- Teaching/streaming visual aid
- Multi-monitor status check
- Custom workflow themes

---

#### 8. Edge Constraint Mode
**Path:** `Blender/Addons/ClaudeVibe_WIPs/edge_constraint_mode/`  
**Version:** 1.1.0  
**Status:** Experimental

**Description:**
3ds Max and Maya-style edge constraint functionality for Blender.

**Features:**
- Edge-constrained transforms (Translate, Rotate, Scale)
- Modal operator with G/R/S hotkey integration
- Visual feedback with GPU rendering
- Multi-component support (vertices, edges, faces)
- Constraint options (clamp, selected edges only, even spacing)

**Transform Support:**
- **Translation:** Slides along edge topology
- **Rotation:** Rotates around pivot following edges
- **Scale:** Radial scaling constrained to edge paths

**Advanced Options:**
- Respect pinned vertices
- Stop at non-manifold boundaries
- Preserve UV stretch (experimental)

**Usage:**
1. Edit Mode > Select elements
2. Sidebar (N) > Tool > Enable Edge Constraint
3. Press G/R/S for constrained transforms
4. Confirm with LMB/Enter or cancel with RMB/ESC

---

### Geometry Nodes

**Path:** `Blender/Geonodes/`  
**Status:** Asset Library Ready  
**Installation:** Set as Asset Library path with "Link" import method

#### Available Geonodes

1. **GN_AttributeFunctions_4.5** - Attribute manipulation tools
2. **GN_CollectionInstancer** - Collection-based instancing
3. **GN_Delete** - Selection-based deletion
4. **GN_ExtrudeSelection** - Procedural extrusion
5. **GN_FillBorder** - Border filling operations
6. **GN_GrowSelection** - Selection expansion
7. **GN_InsetFace** - Face insetting
8. **GN_Instancer** - General instancing tools
9. **GN_MeshFromImage** - Image to mesh conversion
10. **GN_SimpleTransform** - Basic transform operations
11. **GN_Solidify2** - Solidify modifier equivalent
12. **GN_SplitByAttribute** - Attribute-based splitting
13. **GN_VariousTest** - Experimental nodes

**Note:** Some nodes may require third-party geometry node dependencies.

**Usage:**
1. Blender > Preferences > File Paths
2. Add Geonodes folder as Asset Library
3. Set import method to "Link"
4. Access via Asset Browser
5. Drag-drop onto models

---

## 3DS Max Tools (ST3E)

**Full Name:** Stephko's 3ds Max Extensions  
**Version:** Final Release (2023)  
**Status:** Archived - Development discontinued in favor of Blender  
**Documentation:** [Google Docs](https://docs.google.com/document/d/1fIKEurSNeaazzYsPnCTYT7bVO4R4btWzTzvLRpjNutY/edit?usp=sharing)

### Overview

ST3E is a comprehensive collection of MaxScript tools designed to enhance 3ds Max modeling workflows with quality-of-life improvements over vanilla implementations.

### Installation

#### Scripts
```
Location: Program Files\[MaxRoot]\scripts\
Contents: ST3E folder + Startup folder
```

#### Modifiers
```
Location: Program Files\[MaxRoot]\Plugins
Contents: Custom Modifiers folder contents
```

### Categories

#### Scripts (50+ tools organized in folders)

**ST3E/CoordinateSystem/**
- `PickDirectly.mcr` - Direct coordinate system picker

**ST3E/Editing/Operation/**
- `PolyAutoSmoothHelpers.mcr` - Auto-smooth workflow tools
- `PolyChamferNoSmoothing.mcr` - Chamfer without smoothing groups
- `PolyConnects.mcr` - Enhanced connect operations
- `PolyFlowTools.mcr` - Edge flow management
- `PolyLoopTools.mcr` - Loop selection utilities
- `PolySmartCreateNewBase.mcr` - Smart base creation
- `PolySmartRemove.mcr` - Intelligent element removal
- `PolySmartTargetWeld.mcr` - Target weld enhancements
- `PolySnapToLocalCenter.mcr` - Local center snapping
- `PolySplineSmartCollapse.mcr` - Spline-aware collapse
- `PolyVertWeightSmoothFace.mcr` - Vertex weight smoothing
- `PolyWeldBorders.mcr` - Border welding tools

**ST3E/Editing/Select/**
- `PolyDotRingDotGapQuickSelect.mcr` - Advanced ring selection
- `PolySelectExtended.mcr` - Extended selection tools
- `PolySelectFacesWithMultiSG.mcr` - Multi-smoothing-group face selection
- `PolySelectHalfFromBoundry.mcr` - Half selection from boundary

**ST3E/Inspection/**
- `DisplayKnotPointsInViewport.mcr` - Knot point visualization
- `DisplayMaterialIDsInViewport.mcr` - Material ID display
- `DisplayObjectNamesInViewport.mcr` - Object name overlay
- `InverseSeeThrough.mcr` - Inverse transparency
- `ShowCage.mcr` - Modifier cage display
- `SmartIsolate.mcr` - Context-aware isolation
- `ToggleVertexColor.mcr` - Vertex color display toggle
- `WireframeEdgeFaceOff.mcr` - Wireframe display modes

**ST3E/RulersHelpers/**
- `PolyConstraintsExtended.mcr` - Extended constraint system
- `SmartConstraint.mcr` - Intelligent constraints
- `SmartConstraint2.mcr` - Advanced constraints

**ST3E/SceneManagement/**
- `AddTurnToPoly.mcr` - Turn to poly conversion
- `AppendBoundsSuffix.mcr` - Bounds suffix automation
- `CleanCollapse.mcr` - Clean stack collapse
- `ExtractReference.mcr` - Reference extraction
- `OpenLayerManager.mcr` - Layer manager access
- `ResetPositionRotationScale.mcr` - Transform reset

**ST3E/StackManagement/**
- `CollapseStackRetainInstance.mcr` - Instance-preserving collapse
- `JumpToEditableAndExit.mcr` - Quick editable poly access

**ST3E/Toolsets/**
- `MatIDToolBox.ms` - Material ID management suite
- `PolyDrawOptions.ms` - Poly draw configurations

**ST3E/ViewportTools/**
- `SetViewFromClosestAngle.mcr` - Smart viewport alignment

**ST3E/ModifierButtonReplacements/**
- `ModifierAdd_CustomModifiers.mcr` - Custom modifier additions
- `ModifierAdd_QuadCap.mcr` - Quad cap modifier
- `ModifierAdd_Standards.mcr` - Standard modifiers
- `ModifierAdd_tySelect.mcr` - tySelect integration

**ST3E/ObjectCreation/**
- `LetterSequenceMaker.ms` - Letter sequence generator

#### Custom Modifiers (24 total)

**Edit Poly Modifiers:**
- `Modifier_EPoly_autoSmooth.ms` - Auto-smooth modifier
- `Modifier_EPoly_bevel.ms` - Bevel modifier
- `Modifier_EPoly_connect.ms` - Connect modifier
- `Modifier_EPoly_delete.ms` - Delete modifier
- `Modifier_EPoly_extrude.ms` - Extrude modifier
- `Modifier_EPoly_extrudeAlongSpline.ms` - Extrude along spline
- `Modifier_EPoly_inset.ms` - Inset modifier
- `Modifier_EPoly_outline.ms` - Outline modifier

**Simple Mesh Modifiers:**
- `Modifier_SimpleMesh_CornerSetSelect.ms` - Corner set selection
- `Modifier_SimpleMesh_MaterialIDBySG.ms` - Material ID by smoothing group
- `Modifier_SimpleMesh_SGFromMatID.ms` - Smoothing group from Material ID
- `Modifier_SimpleMesh_SGFromVB.ms` - Smoothing group from vertex breaks
- `Modifier_SimpleMesh_ShiftMaterialID.ms` - Material ID shifter
- `Modifier_SimpleMesh_ShiftSmoothingGroups.ms` - Smoothing group shifter
- `Modifier_SimpleMesh_SplitMesh.ms` - Mesh splitter
- `Modifier_SimpleMesh_UVOffsetByMaterialID.ms` - UV offset by Material ID
- `Modifier_SimpleMesh_VertexColorMod.ms` - Vertex color modifier
- `Modifier_SimpleMesh_VertWeightTransfer.ms` - Vertex weight transfer

**Simple Mod Modifiers:**
- `Modifier_SimpleMod_Boxify.ms` - Boxify transformation
- `Modifier_SimpleMod_Cylindrify.ms` - Cylindrical transformation
- `Modifier_SimpleMod_Offset.ms` - Offset modifier
- `Modifier_SimpleMod_Pinch.ms` - Pinch deformation
- `Modifier_SimpleMod_Scale.ms` - Scale modifier
- `Modifier_SimpleMod_Spherify.ms` - Spherify transformation

### Startup Scripts

**ST3E_Startup.ms** - Main startup script  
**ViewportOverlay.ms** - Viewport overlay system

### MVP Graveyard

Experimental and discontinued features (may not work):
- Curve modifier
- Grow smoothing groups
- Make planar
- Outline
- Planar by SG
- Relax by SG
- SG from Material ID
- Slice grid
- Smooth to adjacent

**Warning:** Features in MVP-Graveyard are unsupported and may cause issues.

---

## Unity Tools

**Status:** Not currently in repository  
**Planned:** Future additions

Unity integration focuses on:
- Asset import pipeline optimization
- Blender to Unity workflow tools
- Material and texture automation
- Scene organization utilities

---

## Installation

### Blender Addons

**Method 1: Individual Installation**
1. Open Blender
2. Edit > Preferences > Add-ons
3. Click "Install from Disk"
4. Navigate to addon `.py` file
5. Enable the addon checkbox

**Method 2: Bulk Installation**
```
Location: %APPDATA%\Blender Foundation\Blender\[version]\scripts\addons\
Action: Copy addon folders/files directly
Restart: Blender
Enable: Preferences > Add-ons
```

### Blender Geometry Nodes

1. Blender > Preferences > File Paths
2. Click "+" to add Asset Library
3. Browse to `Blender/Geonodes` folder
4. Set name (e.g., "Stephko Geonodes")
5. Set import method to "Link"
6. Access via Asset Browser (drag-drop to use)

### 3ds Max Scripts

```
Source: 3DSMAX/Scripts/
Target: C:\Program Files\Autodesk\[MaxVersion]\scripts\
Copy: ST3E and Startup folders
Restart: 3ds Max
Access: Various locations (see documentation)
```

### 3ds Max Modifiers

```
Source: 3DSMAX/Modifiers/Custom Modifiers/
Target: C:\Program Files\Autodesk\[MaxVersion]\Plugins\
Copy: All .ms files from Custom Modifiers folder
Restart: 3ds Max
Access: Modifier Panel
```

---

## Support & Contact

### Author
**Stephan Viranyi**

### Contact
- **Email:** stephko@viranyi.de
- **Portfolio:** [artstation.com/stephko](https://www.artstation.com/stephko)
- **LinkedIn:** [linkedin.com/in/stephanviranyi](https://www.linkedin.com/in/stephanviranyi/)
- **GitHub:** [github.com/Stephk0/Toolings](https://github.com/Stephk0/Toolings)

### License
**Free to share and extend**

Feel free to modify and extend these tools for your own workflows. Feedback and questions are welcome!

### Contributing
- Submit issues or feature requests on GitHub
- Share your modifications and improvements
- Provide feedback on workflows and usability
- Report bugs with reproduction steps

### Known Issues & Limitations

**Blender Addons:**
- Edge Constraint Mode is experimental
- Some geometry nodes require third-party dependencies
- Mass Exporter best tested with FBX format

**3ds Max Tools:**
- No active development (archived 2023)
- Some MVP-Graveyard features may not work
- Tested primarily on Max 2020-2023

### Version Information

- **Documentation Version:** 1.0
- **Last Updated:** 2024
- **Blender Tools:** Active Development
- **3ds Max Tools:** Archived (Final)
- **Unity Tools:** Planned

---

## Quick Reference

### Blender Hotkeys
| Tool | Hotkey | Context |
|------|--------|---------|
| Smart Collapse | `Ctrl + Alt + X` | Edit Mode |
| Smart Crease | `Shift + E` | Edit Mode |
| Smart Orientation | `Ctrl + D` | Any Mode |
| Center Loops | `Ctrl + Shift + C` | Edit Mode |
| Toggle Modifier Display | `D` | Edit Mode |
| Toggle On Cage | `Shift + D` | Edit Mode |

### Common Workflows

**Blender: Clean Export to Unity**
1. Use Mass Exporter
2. Enable "Join Empty Children"
3. Set FBX Units Scale
4. Enable "Apply Transform"
5. Set axis: -Z Forward, Y Up
6. Export

**3ds Max: Clean Mesh Preparation**
1. Use PolyFlowTools for topology
2. Apply MaterialIDBySG
3. Use SmartIsolate for focused work
4. Clean collapse with CleanCollapse
5. Reset transforms with ResetPositionRotationScale

**Blender: Topology Cleanup**
1. Center Loops for even flow
2. Smart Collapse for reduce geometry
3. Smart Crease for subdivided edges
4. Smart Orientation for aligned transforms

---

## Changelog

### 2024
- **Blender:** 8 addons at production quality
- **Documentation:** Complete rewrite and organization
- **Mass Exporter:** Version 12 with fallback export

### 2023
- **3ds Max:** Final release and archival
- **Focus:** Shifted entirely to Blender development

### 2022-Earlier
- **3ds Max:** Active ST3E development
- **Tools:** 50+ scripts and 24 modifiers created

---

**Made with ❤️ by Stephan Viranyi**  
*Bringing professional 3D workflows to artists worldwide*

