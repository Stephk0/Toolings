# Stephko Toolings - Documentation Index

> Complete documentation for Blender, Unity, and 3DS Max toolings by Stephan Viranyi

## 📚 Table of Contents

- [Overview](#overview)
- [Blender Addons](#blender-addons)
- [Blender Geometry Nodes](#blender-geometry-nodes)
- [Unity Tools](#unity-tools)
- [3DS Max Tools](#3ds-max-tools)
- [Installation Guides](#installation-guides)
- [Troubleshooting](#troubleshooting)

---

## 🎯 Overview

This repository is a **compilation of independent tools** for 3D workflows across platforms:

- **Blender**: 16 production addons + a 37-modifier Geometry Nodes library
- **Unity**: model import automation
- **3DS Max**: legacy MaxScript collection (ST3E, development paused 2023)

**Project Status:**
- ✅ **Active Development**: Blender addons & geometry nodes
- 🔄 **Light development**: Unity tools
- ⚠️ **Maintenance Mode**: 3DS Max tools (ST3E)

Each tool follows the standard layout: `README.md` + `source/` + `distribution/`
(see `Blender/Addons/ClaudeVibe_WIPs/_TOOLING_STRUCTURE.md`).

---

## 🔷 Blender Addons

All Blender addons live in `Blender/Addons/ClaudeVibe_WIPs/`. Each folder contains its own
`README.md` (detailed usage), a `source/` folder, and an installable zip under `distribution/`.

### Export & Pipeline

| Tool | Ver | Description | Docs |
|------|-----|-------------|------|
| **Mass Collection Exporter** | 13.6.2 | Batch export collections/objects (FBX, OBJ, DAE, glTF) with suffix grouping, parent-empty handling, and per-collection settings | [README](Blender/Addons/ClaudeVibe_WIPs/MassExporter/README.md) |
| **Quick Animation Export** | 1.0.9 | Streamlined export of animation/action clips to game-engine-ready files | [README](Blender/Addons/ClaudeVibe_WIPs/QuickAnimationExport/README.md) |
| **Animation Layers Quick Export** | 0.3.0 | One-click non-destructive merge + FBX export for [Animation Layers](https://blendermarket.com/products/animation-layers) rigs | [README](Blender/Addons/ClaudeVibe_WIPs/AnimLayersQuickExport/README.md) |

### Modeling

| Tool | Ver | Description | Docs |
|------|-----|-------------|------|
| **Smart Crease** | 1.5.1 | Context-sensitive edge/vertex crease with preset keys + modal mouse control | [README](Blender/Addons/ClaudeVibe_WIPs/Smart%20Crease/README.md) |
| **Smart Collapse** | 1.0.0 | 3ds Max-style collapse (collapse + merge at center) | [README](Blender/Addons/ClaudeVibe_WIPs/Smart%20Collapse/README.md) |
| **Smart Set Orientation** | 1.5.0 | Set transform orientation from selection (Maya "D" working-pivot style) | [README](Blender/Addons/ClaudeVibe_WIPs/Smart%20Set%20Orientation/README.md) |
| **Center Edges/Loops** | 1.5.1 | Center edge loops / selections along their average position | [README](Blender/Addons/ClaudeVibe_WIPs/Center%20Edges/README.md) |
| **Edge Constraint Mode** | 1.1.2 | 3ds Max-style edge constraint — verts slide along topology during transforms | [README](Blender/Addons/ClaudeVibe_WIPs/EdgeConstraintMode/README.md) |

### Modifiers

| Tool | Ver | Description | Docs |
|------|-----|-------------|------|
| **Synced Modifiers** | 2.5.0 | Add & keep modifiers synchronized across objects via drivers; Geometry Nodes input sync | [README](Blender/Addons/ClaudeVibe_WIPs/SyncedModifiers/README.md) |
| **Modifier List (Stephko fork)** | 1.9.89 | Enhanced modifier-stack UI (list view, popup, sidebar) with GN input-attribute toggle fix | [README](Blender/Addons/ClaudeVibe_WIPs/ModifierList_Stephko/source/docs/README.md) |
| **Toggle Modifier Display** | 1.3.0 | Quick modifier visibility toggle in edit mode (D / Shift+D), 3ds Max "show end result" style | [README](Blender/Addons/ClaudeVibe_WIPs/Toggle%20Modifier%20Display/README.md) |

### UV, Naming & Rigging

| Tool | Ver | Description | Docs |
|------|-----|-------------|------|
| **Tile UV Projector** | 1.2.1 | Tile-based UV projection/placement for texture-atlas workflows | [README](Blender/Addons/ClaudeVibe_WIPs/TileUVProjector/README.md) |
| **Add Bounds To Name** | 1.1.3 | Rename objects from bounding-box dimensions (units, rounding, swizzle, presets) | [README](Blender/Addons/ClaudeVibe_WIPs/AddBoundsToName/README.md) |
| **Skin Transfer Setup** | 1.3.0 | Per-part skin setup (as-is / data transfer / bind-to-bone) with centralized rig + base | [README](Blender/Addons/ClaudeVibe_WIPs/SkinTransferSetup/README.md) |

### Viewport & Render

| Tool | Ver | Description | Docs |
|------|-----|-------------|------|
| **Edit Mode Overlay** | 1.1.0 | Enhanced edit-mode viewport feedback / text overlay | [README](Blender/Addons/ClaudeVibe_WIPs/Edit%20Mode%20Overlay/README.md) |
| **Compositor Render Sets** | 1.7.4 | Multi-render-setup management for compositor workflows with batch rendering | [README](Blender/Addons/ClaudeVibe_WIPs/Compositor%20Render%20Sets/README.md) |

---

## 🔷 Blender Geometry Nodes

**Location:** `Blender/Geonodes/`
**Status:** ✅ Active
**Full reference:** **[ST3E Geometry Nodes Library README](Blender/Geonodes/README.md)**

A library of **37 ST3E modifiers** available from the **Add Modifier → ST3E** quick-pick menu,
grouped into:

- **Deformers** (14) — Inflate, Spherify, Twist, Taper, Stretch, Bend, Wave, Cast, Smooth,
  Displace, RandomizePosition, ShearGeometry, FlattenByBoundary, SimpleTransformMesh
- **Generators & Topology** (12) — Subdivide, Triangulate, Wireframe, ConvexHull, BoundingBox,
  DualMesh, VoxelRemesh, RadialArray, PointsToSpheres, Scatter, MeshBoolean, CollectionInstancer
- **Mesh & Attribute Utilities** (11) — FlipFaces, AutoSmooth, SetMaterial, MaterialOverride,
  Weld, Delete, ExtrudeFace, MirrorGroup, SplitEdgeByAttribute, SetAttribute, AttributeTransfer

Plus Asset-Browser-only utility groups (FillBorder, GrowSelection, InsetFace, etc.), the
**Procedural Tree Generator** ([`TreeGenDocu/`](Blender/Geonodes/TreeGenDocu/README.md)), and the
`geonode_route_tidy.py` layout tool. See the library README for the full table, parameters, and
installation steps.

**Installation:**
1. Add the `Blender/` folder as an Asset Library in **Preferences → File Paths**.
2. Set Import Method: **Link**.
3. Use **Add Modifier → ST3E**, or drag from the Asset Browser.

---

## 🔶 Unity Tools

**Location:** `Unity/`
**Status:** 🔄 Light development

| Tool | Ver | Description | Docs |
|------|-----|-------------|------|
| **Model Import Processor** | 1.0 | Automated FBX/model import processing pipeline for Unity (2019.4+) | [README](Unity/ModelImportProcessor/README.md) |

---

## 🔸 3DS Max Tools (ST3E)

> **Status:** ⚠️ Development paused in 2023. Maintained for legacy projects only.

**Location:** `3DSMAX/`
**Full Documentation:** [ST3E Google Docs](https://docs.google.com/document/d/1fIKEurSNeaazzYsPnCTYT7bVO4R4btWzTzvLRpjNutY/edit?usp=sharing)

**ST3E** (Stephko's 3ds Max Extensions) is a comprehensive MaxScript collection for enhanced
3DS Max workflows.

### Custom Modifiers (`3DSMAX/Modifiers/Custom Modifiers/`)

- **Edit Poly:** autoSmooth, bevel, connect, delete, extrude, extrudeAlongSpline, inset, outline
- **SimpleMesh:** CornerSetSelect, MaterialIDBySG, SGFromMatID, SGFromVB, ShiftMaterialID,
  ShiftSmoothingGroups, SplitMesh, UVOffsetByMaterialID, VertexColorMod, VertWeightTransfer
- **SimpleMod:** Boxify, Cylindrify, Offset, Pinch, Scale, Spherify

### Script Tools (`3DSMAX/Scripts/ST3E/`)

- **Coordinate System:** PickDirectly
- **Editing:** PolyAutoSmoothHelpers, PolyChamferNoSmoothing, PolyConnects, PolyFlowTools,
  PolyLoopTools, PolySmartCreateNewBase, PolySmartRemove, PolySmartTargetWeld,
  PolySnapToLocalCenter, PolySplineSmartCollapse, PolyVertWeightSmoothFace, PolyWeldBorders
- **Selection:** PolyDotRingDotGapQuickSelect, PolySelectExtended, PolySelectFacesWithMultiSG,
  PolySelectHalfFromBoundry
- **Inspection:** DisplayKnotPointsInViewport, DisplayMaterialIDsInViewport,
  DisplayObjectNamesInViewport, InverseSeeThrough, ShowCage, SmartIsolate, ToggleVertexColor,
  WireframeEdgeFaceOff
- **Scene:** AddTurnToPoly, AppendBoundsSuffix, CleanCollapse, ExtractReference,
  OpenLayerManager, ResetPositionRotationScale
- **Stack:** CollapseStackRetainInstance, JumpToEditableAndExit

---

## 📥 Installation Guides

### Blender Addons

**Drag-and-drop (recommended, Blender 4.2+):** drag the latest `.zip` from a tool's
`distribution/` folder onto Blender, then enable it.

**Classic install:** Edit → Preferences → Add-ons → Install… → select the `.zip` → enable.

### Blender Geometry Nodes

1. Preferences → File Paths → Asset Libraries → add the `Blender/` folder.
2. Set Import Method: **Link**.
3. Use **Add Modifier → ST3E**, or drag node groups from the Asset Browser.

### 3DS Max (Legacy)

- **Scripts:** copy `ST3E` + `Startup` folders → `[MaxRoot]\scripts\`
- **Modifiers:** copy `Custom Modifiers` contents → `[MaxRoot]\Plugins\`
- Restart 3DS Max.

---

## 🔧 Troubleshooting

**Blender: addon doesn't appear**
- Check Blender version compatibility (4.2+ / 5.0 recommended)
- Enable the addon in Preferences
- Check the System Console for errors (Window → Toggle System Console)
- F3 → "Reload Scripts"

**Blender: geometry node missing from Add Modifier → ST3E**
- The group must be asset-marked, carry the `ST3E` tag, have the *Modifier* asset trait on,
  and have Geometry in/out sockets. See the [library README](Blender/Geonodes/README.md).

**Blender: export fails**
- Check the export path exists and is writable
- Collection has visible mesh objects
- Enable Debug Mode for detailed logging

**3DS Max: scripts not loading**
- Correct installation path; Max has file-write permissions; check the MaxScript Listener.

---

## 📞 Support & Contact

**Author:** Stephan Viranyi

- **Email:** stephko@viranyi.de
- **Portfolio:** [ArtStation](https://www.artstation.com/stephko)
- **LinkedIn:** [Stephan Viranyi](https://www.linkedin.com/in/stephanviranyi/)

---

## 📜 License

These tools are provided free for personal and commercial use — use, modify, and share freely.
Attribution appreciated but not required. No warranty provided.

---

## 🌟 Credits

**Development:** Stephan Viranyi (Stephko)
**AI Assistance:** Claude AI (Anthropic) with Blender MCP integration
**Testing:** Personal production use + community feedback

---

**Last Updated:** 2026-06-06
**Documentation Version:** 2.0

---

*Happy Creating! 🚀*
