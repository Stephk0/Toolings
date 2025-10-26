# Stephko Toolings - Documentation Index

> Complete documentation for Blender, Unity, and 3DS Max toolings by Stephan Viranyi

## 📚 Table of Contents

- [Overview](#overview)
- [Blender Tools](#blender-tools)
- [Unity Tools](#unity-tools)
- [3DS Max Tools](#3ds-max-tools)
- [Installation Guides](#installation-guides)
- [Quick Reference](#quick-reference)

---

## 🎯 Overview

This repository contains a comprehensive collection of tools for 3D workflows across multiple platforms:

- **Blender**: Modern addons and geometry nodes for efficient modeling
- **Unity**: Import/export utilities and workflow tools
- **3DS Max**: Legacy MaxScript collection (development paused in 2023)

**Project Status:**
- ✅ **Active Development**: Blender tools
- ⚠️ **Maintenance Mode**: 3DS Max tools (ST3E)
- 🔄 **Planned**: Unity tools expansion

---

## 🔷 Blender Tools

### Addons

All Blender addons are located in: `Blender/Addons/ClaudeVibe_WIPs/`

#### 1. Mass Collection Exporter v12
**Location:** `MassExporter/`  
**Status:** ✅ Production Ready  
**Documentation:** [Mass Exporter README](Blender/Addons/ClaudeVibe_WIPs/MassExporter/README.md)

**Quick Description:**
Batch export collections with advanced parent-child handling, automatic joining, and multiple format support.

**Key Features:**
- Export multiple collections at once
- Smart empty parent handling
- On-demand mesh joining
- Support for FBX, OBJ, DAE, glTF
- Auto-move to origin
- Material override system

**Use Cases:**
- Game asset export workflows
- Modular building systems
- Batch prop export
- Unity/Unreal asset pipelines

---

#### 2. Smart Crease
**Location:** `Smart Crease/`  
**Status:** ✅ Production Ready  
**Documentation:** [Smart Crease README](Blender/Addons/ClaudeVibe_WIPs/Smart%20Crease/README.md)

**Quick Description:**
Intelligent edge crease management with multiple selection modes.

**Key Features:**
- Quick crease value application
- Selection-based crease workflows
- Sharp edge detection
- Undo-friendly operations

---

#### 3. Center Edges/Loops
**Location:** `Center Edges/`  
**Status:** ✅ Production Ready  
**Documentation:** [Center Loops README](Blender/Addons/ClaudeVibe_WIPs/Center%20Edges/README.md)

**Quick Description:**
Center edge loops and edge selections along their average position.

**Key Features:**
- Edge loop centering
- Edge selection averaging
- Maintains topology
- Works with complex selections

---

#### 4. Smart Collapse
**Location:** `Smart Collapse/`  
**Status:** ✅ Production Ready  
**Documentation:** [Smart Collapse README](Blender/Addons/ClaudeVibe_WIPs/Smart%20Collapse/README.md)

**Quick Description:**
Context-aware mesh element collapsing.

**Key Features:**
- Intelligent edge collapse
- Vertex merge operations
- Preserves mesh quality
- Multiple collapse modes

---

#### 5. Smart Orientation
**Location:** `Smart Orientation/`  
**Status:** ✅ Production Ready  
**Documentation:** [Smart Orientation README](Blender/Addons/ClaudeVibe_WIPs/Smart%20Orientation/README.md)

**Quick Description:**
Automatically set transform orientation based on selection.

**Key Features:**
- Face-based orientation
- Edge-based orientation
- Quick orientation switching
- Viewport alignment

---

#### 6. Edge Constraint Mode
**Location:** `edge_constraint_mode/`  
**Status:** ✅ Production Ready  
**Documentation:** [Edge Constraint README](Blender/Addons/ClaudeVibe_WIPs/edge_constraint_mode/README.md)

**Quick Description:**
Constrain transforms to edge directions during modeling.

**Key Features:**
- Edge-aligned transforms
- Dynamic constraint switching
- Works with move/rotate/scale
- Visual feedback

---

#### 7. Edit Mode Overlay
**Location:** `Edit Mode Overlay/`  
**Status:** ✅ Production Ready  
**Documentation:** [Edit Mode Overlay README](Blender/Addons/ClaudeVibe_WIPs/Edit%20Mode%20Overlay/README.md)

**Quick Description:**
Enhanced viewport feedback for edit mode operations.

**Key Features:**
- Visual selection indicators
- Edge/face highlighting
- Customizable colors
- Performance optimized

---

#### 8. Toggle Modifier Display
**Location:** `Toggle Modifier Display/`  
**Status:** ✅ Production Ready  
**Documentation:** [Modifier Display README](Blender/Addons/ClaudeVibe_WIPs/Toggle%20Modifier%20Display/README.md)

**Quick Description:**
Quick toggle modifier visibility in edit mode.

**Key Features:**
- One-click modifier toggle
- Edit mode specific
- Works with all modifier types
- Preserves modifier settings

---

### Geometry Nodes

**Location:** `Blender/Geonodes/`  
**Status:** ✅ Production Ready

Collection of procedural geometry node groups for common operations:

#### Available Node Groups

1. **GN_AttributeFunctions_4.5** - Attribute manipulation utilities
2. **GN_CollectionInstancer** - Advanced collection instancing
3. **GN_Delete** - Smart geometry deletion
4. **GN_ExtrudeSelection** - Selection-based extrusion
5. **GN_FillBorder** - Automatic border filling
6. **GN_GrowSelection** - Selection expansion tools
7. **GN_InsetFace** - Face inset operations
8. **GN_Instancer** - General instancing system
9. **GN_MeshFromImage** - Image to mesh conversion
10. **GN_SimpleTransform** - Basic transform operations
11. **GN_Solidify2** - Advanced solidify
12. **GN_SplitByAttribute** - Attribute-based splitting

**Installation:**
1. Set `Blender/Geonodes/` as Asset Library in Preferences → File Paths
2. Use "Link" as import method
3. Access via Asset Browser

---

## 🔶 Unity Tools

**Location:** `Unity/` (To be expanded)  
**Status:** 🔄 Planned

Utilities for Unity import/export workflows, primarily focusing on:
- FBX import automation
- Material assignment tools
- Asset organization helpers

**Note:** Currently, Unity workflows are handled through Blender Mass Exporter with Unity-specific export presets.

---

## 🔸 3DS Max Tools (ST3E)

> **Status:** ⚠️ Development paused in 2023. Maintained for legacy projects only.

**Location:** `3DSMAX/`  
**Full Documentation:** [ST3E Google Docs](https://docs.google.com/document/d/1fIKEurSNeaazzYsPnCTYT7bVO4R4btWzTzvLRpjNutY/edit?usp=sharing)

### ST3E Overview

**ST3E** (Stephko's 3ds Max Extensions) is a comprehensive MaxScript collection for enhanced 3DS Max workflows.

**Categories:**

### 1. Custom Modifiers
**Location:** `3DSMAX/Modifiers/Custom Modifiers/`

#### Edit Poly Modifiers
- **Modifier_EPoly_autoSmooth** - Auto-smoothing operations
- **Modifier_EPoly_bevel** - Procedural beveling
- **Modifier_EPoly_connect** - Edge connection
- **Modifier_EPoly_delete** - Selection deletion
- **Modifier_EPoly_extrude** - Extrusion operations
- **Modifier_EPoly_extrudeAlongSpline** - Spline-based extrusion
- **Modifier_EPoly_inset** - Face inset operations
- **Modifier_EPoly_outline** - Outline operations

#### SimpleMesh Modifiers
- **Modifier_SimpleMesh_CornerSetSelect** - Corner selection
- **Modifier_SimpleMesh_MaterialIDBySG** - Material ID from smoothing groups
- **Modifier_SimpleMesh_SGFromMatID** - Smoothing groups from Material ID
- **Modifier_SimpleMesh_SGFromVB** - Smoothing groups from vertex breaks
- **Modifier_SimpleMesh_ShiftMaterialID** - Material ID offsetting
- **Modifier_SimpleMesh_ShiftSmoothingGroups** - Smoothing group shifting
- **Modifier_SimpleMesh_SplitMesh** - Mesh splitting
- **Modifier_SimpleMesh_UVOffsetByMaterialID** - UV manipulation
- **Modifier_SimpleMesh_VertexColorMod** - Vertex color operations
- **Modifier_SimpleMesh_VertWeightTransfer** - Weight transfer

#### SimpleMod Modifiers
- **Modifier_SimpleMod_Boxify** - Box-like deformation
- **Modifier_SimpleMod_Cylindrify** - Cylindrical deformation
- **Modifier_SimpleMod_Offset** - Geometry offset
- **Modifier_SimpleMod_Pinch** - Pinch deformation
- **Modifier_SimpleMod_Scale** - Procedural scaling
- **Modifier_SimpleMod_Spherify** - Spherical deformation

### 2. Script Tools
**Location:** `3DSMAX/Scripts/ST3E/`

#### Coordinate System
- **PickDirectly** - Quick coordinate system picking

#### Editing Operations
- **PolyAutoSmoothHelpers** - Auto-smooth assistance
- **PolyChamferNoSmoothing** - Chamfer without smoothing
- **PolyConnects** - Connection tools
- **PolyFlowTools** - Edge flow operations
- **PolyLoopTools** - Loop selection tools
- **PolySmartCreateNewBase** - Intelligent base creation
- **PolySmartRemove** - Smart element removal
- **PolySmartTargetWeld** - Target weld enhancements
- **PolySnapToLocalCenter** - Local snapping
- **PolySplineSmartCollapse** - Spline collapse
- **PolyVertWeightSmoothFace** - Weight smoothing
- **PolyWeldBorders** - Border welding

#### Selection Tools
- **PolyDotRingDotGapQuickSelect** - Pattern selection
- **PolySelectExtended** - Extended selection modes
- **PolySelectFacesWithMultiSG** - Multi-smoothing group selection
- **PolySelectHalfFromBoundry** - Half-mesh selection

#### Inspection Tools
- **DisplayKnotPointsInViewport** - Knot visualization
- **DisplayMaterialIDsInViewport** - Material ID display
- **DisplayObjectNamesInViewport** - Name labels
- **InverseSeeThrough** - Inverted transparency
- **ShowCage** - Cage visualization
- **SmartIsolate** - Intelligent isolation
- **ToggleVertexColor** - Vertex color display
- **WireframeEdgeFaceOff** - Display mode switching

#### Scene Management
- **AddTurnToPoly** - Poly conversion
- **AppendBoundsSuffix** - Naming utilities
- **CleanCollapse** - Stack collapse
- **ExtractReference** - Reference extraction
- **OpenLayerManager** - Layer management
- **ResetPositionRotationScale** - Transform reset

#### Stack Management
- **CollapseStackRetainInstance** - Instance-safe collapse
- **JumpToEditableAndExit** - Quick edit mode

---

## 📥 Installation Guides

### Blender Addons Installation

**Method 1: Direct Install (Recommended)**
```
1. Download the addon .py file
2. Open Blender
3. Edit → Preferences → Add-ons
4. Click "Install..." button
5. Select the .py file
6. Enable the addon checkbox
```

**Method 2: Manual Install**
```
1. Locate Blender addons folder:
   Windows: %APPDATA%\Blender Foundation\Blender\[version]\scripts\addons\
   macOS: ~/Library/Application Support/Blender/[version]/scripts/addons/
   Linux: ~/.config/blender/[version]/scripts/addons/
2. Copy addon file to folder
3. Restart Blender
4. Enable in Preferences → Add-ons
```

**Geometry Nodes Installation**
```
1. Open Blender Preferences → File Paths
2. Add Asset Library path: [Your Path]/Blender/Geonodes/
3. Set Import Method: Link
4. Nodes appear in Asset Browser
5. Drag-drop onto objects
```

---

### 3DS Max Installation

**Scripts Installation**
```
1. Navigate to: Program Files\[MaxRoot]\scripts\
2. Copy ST3E folder to this location
3. Copy Startup folder to this location
4. Restart 3DS Max
5. Scripts available in MaxScript menu
```

**Modifiers Installation**
```
1. Navigate to: Program Files\[MaxRoot]\Plugins\
2. Copy contents of "Custom Modifiers" folder
3. Restart 3DS Max
4. Modifiers available in Modifier List
```

---

## 📖 Quick Reference

### Blender Quick Keys

Most addons add operators to:
- **Search Menu** (`F3`) - Search for addon name
- **N-Panel** - Many addons add panels here
- **Edit Mode Menu** - Context-specific operations

---

## 🔧 Troubleshooting

### Common Issues

**Blender: Addon doesn't appear**
```
✓ Check Blender version compatibility (4.5+)
✓ Enable addon in Preferences
✓ Check for errors in System Console
✓ Reload scripts (F3 → "Reload Scripts")
```

**Blender: Export fails**
```
✓ Check export path is valid
✓ Collection has mesh objects
✓ Objects are visible
✓ Debug Mode enabled for details
```

**3DS Max: Scripts not loading**
```
✓ Correct installation path
✓ Max has file write permissions
✓ No syntax errors in scripts
✓ Check MaxScript Listener for errors
```

---

## 📞 Support & Contact

**Author:** Stephan Viranyi

- **Email:** stephko@viranyi.de
- **Portfolio:** [ArtStation](https://www.artstation.com/stephko)
- **LinkedIn:** [Stephan Viranyi](https://www.linkedin.com/in/stephanviranyi/)

### Getting Help

1. **Check Documentation** - Review the specific tool's README
2. **Enable Debug Mode** - Most tools have debug/verbose options
3. **Check Console** - System Console (Blender) or Listener (Max)
4. **Report Issues** - Contact via email with:
   - Tool name and version
   - Software version
   - Steps to reproduce
   - Error messages

---

## 📜 License

**Free to share and extend**

These tools are provided free for use in personal and commercial projects. You are welcome to:
- Use in any project
- Modify for your needs
- Share with others
- Learn from the code

**Attribution appreciated but not required.**

---

## 🗺️ Roadmap

### Planned Development

**Blender (Active)**
- Additional geometry node presets
- More export format support
- Enhanced material workflow tools
- Performance optimizations

**Unity (Planned)**
- Import automation scripts
- Material assignment tools
- Asset organization utilities

**3DS Max (Maintenance)**
- Bug fixes only
- Documentation preservation
- No new features planned

---

## 📚 Additional Documentation

### Per-Tool Documentation
- [Mass Exporter v12 README](Blender/Addons/ClaudeVibe_WIPs/MassExporter/README.md) - Complete guide
- [Smart Crease README](Blender/Addons/ClaudeVibe_WIPs/Smart%20Crease/README.md)
- [Center Loops README](Blender/Addons/ClaudeVibe_WIPs/Center%20Edges/README.md)
- [Smart Collapse README](Blender/Addons/ClaudeVibe_WIPs/Smart%20Collapse/README.md)
- [Smart Orientation README](Blender/Addons/ClaudeVibe_WIPs/Smart%20Orientation/README.md)
- [Edit Mode Overlay README](Blender/Addons/ClaudeVibe_WIPs/Edit%20Mode%20Overlay/README.md)
- [Modifier Display README](Blender/Addons/ClaudeVibe_WIPs/Toggle%20Modifier%20Display/README.md)

### External Documentation
- [ST3E Complete Documentation](https://docs.google.com/document/d/1fIKEurSNeaazzYsPnCTYT7bVO4R4btWzTzvLRpjNutY/edit?usp=sharing) - 3DS Max tools

---

## 🌟 Credits

**Development:** Stephan Viranyi (Stephko)
**AI Assistance:** Claude AI (Anthropic) - Code generation and documentation
**Testing:** Community feedback and personal production use

**Special Thanks:**
- Blender Foundation
- Open source community

---

**Last Updated:** October 2025  
**Documentation Version:** 1.0  
**Tools Version:** See individual tool READMEs

---

*Happy Creating! 🚀*
