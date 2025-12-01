# ST3E - Stephko's 3ds Max Extensions

**Full Name:** Stephko's 3ds Max Extensions  
**Version:** Final Release (2023)  
**Status:** 📦 Archived - Development Discontinued  
**License:** Free to share and extend

> Comprehensive collection of 50+ MaxScript tools and 24 custom modifiers for enhanced 3ds Max workflows

---

## 📢 Important Notice

### Development Status

**⚠️ ARCHIVED PROJECT ⚠️**

- Development ceased in **2023**
- No new features planned
- No bug fixes or updates
- Focus shifted to **Blender tooling**
- Provided **as-is** for community use

### Support

- ❌ **No official support**
- ❌ **No compatibility guarantees**
- ✅ **Community can fork and modify**
- ✅ **Documentation preserved**
- ✅ **Code available for learning**

**Tested Versions:** 3ds Max 2020, 2021, 2022, 2023  
**May work on:** Newer versions (untested)  
**Compatibility:** Windows only

---

## 📋 Table of Contents

- [Overview](#overview)
- [Installation](#installation)
- [Scripts](#scripts)
- [Custom Modifiers](#custom-modifiers)
- [Toolsets](#toolsets)
- [Usage Examples](#usage-examples)
- [Known Issues](#known-issues)
- [External Documentation](#external-documentation)

---

## 🎯 Overview

### What is ST3E?

ST3E is a comprehensive MaxScript toolset developed over 3+ years to enhance 3ds Max modeling workflows. It provides quality-of-life improvements over vanilla Max implementations, focusing on:

- **Edit Poly Operations:** Enhanced poly modeling tools
- **Selection Utilities:** Advanced selection methods
- **Viewport Tools:** Improved viewport feedback and control
- **Stack Management:** Better modifier stack handling
- **Material ID Tools:** Advanced material ID management
- **Scene Organization:** Workflow optimization tools

### Philosophy

**Key Principles:**
- **Incremental improvements** over existing features
- **Context-aware operations** that adapt to selection
- **Quick access** via hotkeys and context menus
- **Non-destructive workflows** where possible
- **Production-tested** in real projects

### Architecture

```
ST3E/
├── CoordinateSystem/    (Coordinate system tools)
├── Editing/
│   ├── Operation/       (Edit Poly operations)
│   └── Select/          (Selection tools)
├── Inspection/          (Viewport display tools)
├── RulersHelpers/       (Constraint and ruler tools)
├── SceneManagement/     (Scene organization)
├── StackManagement/     (Modifier stack tools)
├── Toolsets/            (Complex tool suites)
├── ViewportTools/       (Viewport utilities)
└── ModifierButtonReplacements/ (Modifier shortcuts)
```

---

## 💾 Installation

### Prerequisites

- **3ds Max:** Version 2020 or later
- **OS:** Windows 7/10/11
- **Admin Rights:** May be required for installation
- **Backup:** Save existing scripts before installing

### Scripts Installation

**Step 1: Locate Installation Folder**
```
C:\Program Files\Autodesk\[Max Version]\scripts\
```

**Step 2: Copy Folders**
```
Source: Toolings/3DSMAX/Scripts/
Copy:
  - ST3E folder (complete)
  - Startup folder (complete)
To: [Max Root]\scripts\
```

**Step 3: Verify Structure**
```
scripts/
├── ST3E/
│   ├── CoordinateSystem/
│   ├── Editing/
│   ├── Inspection/
│   ├── RulersHelpers/
│   ├── SceneManagement/
│   ├── StackManagement/
│   ├── Toolsets/
│   ├── ViewportTools/
│   ├── ModifierButtonReplacements/
│   ├── ObjectCreation/
│   └── Lib/
└── Startup/
    ├── ST3E_Startup.ms
    └── ViewportOverlay.ms
```

**Step 4: Restart 3ds Max**

### Modifiers Installation

**Step 1: Locate Installation Folder**
```
C:\Program Files\Autodesk\[Max Version]\Plugins\
```

**Step 2: Copy Files**
```
Source: Toolings/3DSMAX/Modifiers/Custom Modifiers/
Copy: ALL .ms files
To: [Max Root]\Plugins\
```

**Step 3: Files to Copy (24 total)**
```
Modifier_EPoly_autoSmooth.ms
Modifier_EPoly_bevel.ms
Modifier_EPoly_connect.ms
Modifier_EPoly_delete.ms
Modifier_EPoly_extrude.ms
Modifier_EPoly_extrudeAlongSpline.ms
Modifier_EPoly_inset.ms
Modifier_EPoly_outline.ms
Modifier_SimpleMesh_CornerSetSelect.ms
Modifier_SimpleMesh_MaterialIDBySG.ms
Modifier_SimpleMesh_SGFromMatID.ms
Modifier_SimpleMesh_SGFromVB.ms
Modifier_SimpleMesh_ShiftMaterialID.ms
Modifier_SimpleMesh_ShiftSmoothingGroups.ms
Modifier_SimpleMesh_SplitMesh.ms
Modifier_SimpleMesh_UVOffsetByMaterialID.ms
Modifier_SimpleMesh_VertexColorMod.ms
Modifier_SimpleMesh_VertWeightTransfer.ms
Modifier_SimpleMod_Boxify.ms
Modifier_SimpleMod_Cylindrify.ms
Modifier_SimpleMod_Offset.ms
Modifier_SimpleMod_Pinch.ms
Modifier_SimpleMod_Scale.ms
Modifier_SimpleMod_Spherify.ms
```

**Step 4: Restart 3ds Max**

### Verification

1. **Open 3ds Max**
2. **Press F11** (MAXScript Listener)
3. **Look for startup messages** from ST3E
4. **Check context menus** for new options
5. **Open Modifier List** and look for custom modifiers

---

## 📜 Scripts

### CoordinateSystem

**PickDirectly.mcr**
- Direct coordinate system picker
- Bypasses standard picker dialog
- Faster workflow for coordinate changes

**Use Case:** Quick coordinate system changes without menu navigation

---

### Editing / Operation

#### PolyAutoSmoothHelpers.mcr
- Auto-smooth workflow enhancements
- Quick access to auto-smooth operations
- Context-aware smoothing options

**Use Case:** Faster auto-smoothing with better control

#### PolyChamferNoSmoothing.mcr
- Chamfer operation without affecting smoothing groups
- Preserves existing smoothing groups
- Cleaner chamfer results

**Use Case:** Hard surface modeling where smoothing control is critical

#### PolyConnects.mcr
- Enhanced edge/vertex connect operations
- Multiple connection methods
- Smart connect based on selection

**Use Case:** Complex topology modifications with more control

#### PolyFlowTools.mcr
- Edge flow analysis and correction
- Automatic flow detection
- Flow-based operations

**Use Case:** Maintaining clean edge flow in character models

#### PolyLoopTools.mcr
- Advanced loop selection utilities
- Pattern-based loop operations
- Quick loop modifications

**Use Case:** Rapid loop selection and modification

#### PolySmartCreateNewBase.mcr
- Intelligent base object creation
- Context-aware object spawning
- Clean object generation

**Use Case:** Creating new objects with proper setup

#### PolySmartRemove.mcr
- Smart element removal
- Topology-preserving deletion
- Automatic cleanup

**Use Case:** Removing elements while maintaining topology

#### PolySmartTargetWeld.mcr
- Enhanced target weld
- Better vertex selection
- Visual feedback

**Use Case:** Precise vertex welding operations

#### PolySnapToLocalCenter.mcr
- Snap operations to local centers
- Multiple snap modes
- Context-aware snapping

**Use Case:** Aligning to object centers

#### PolySplineSmartCollapse.mcr
- Spline-aware collapse operations
- Preserves curve flow
- Smart edge collapse

**Use Case:** Topology reduction near splines

#### PolyVertWeightSmoothFace.mcr
- Vertex weight smoothing
- Face-based weight operations
- Weight averaging tools

**Use Case:** Character rigging weight cleanup

#### PolyWeldBorders.mcr
- Border welding utilities
- Multiple border handling
- Clean border connections

**Use Case:** Connecting open edges

---

### Editing / Select

#### PolyDotRingDotGapQuickSelect.mcr
- Advanced ring selection patterns
- Gap-aware selection
- Pattern-based multi-ring selection

**Use Case:** Complex loop and ring selections

#### PolySelectExtended.mcr
- Extended selection capabilities
- Growth and shrink operations
- Custom selection patterns

**Use Case:** Advanced selection workflows

#### PolySelectFacesWithMultiSG.mcr
- Select faces by smoothing groups
- Multi-smoothing-group detection
- Smoothing-based selection

**Use Case:** Finding topology issues with smoothing

#### PolySelectHalfFromBoundry.mcr
- Half-object selection from boundary
- Symmetry-aware selection
- Quick half-model operations

**Use Case:** Symmetrical modeling workflows

---

### Inspection

#### DisplayKnotPointsInViewport.mcr
- Visualize spline knot points
- Enhanced spline editing
- Knot point overlay

**Use Case:** Spline editing and analysis

#### DisplayMaterialIDsInViewport.mcr
- Material ID visualization
- Color-coded ID display
- Quick ID verification

**Use Case:** Material ID management and checking

#### DisplayObjectNamesInViewport.mcr
- Object name overlay in viewport
- Dynamic name display
- Scene organization aid

**Use Case:** Managing complex scenes with many objects

#### InverseSeeThrough.mcr
- Inverse X-ray mode
- Selective transparency
- Better visibility control

**Use Case:** Working with overlapping geometry

#### ShowCage.mcr
- Modifier cage visualization
- Before/after comparison
- Stack preview

**Use Case:** Understanding modifier effects

#### SmartIsolate.mcr
- Context-aware isolation
- Smart selection isolation
- Quick focus on work area

**Use Case:** Focusing on specific objects/components

#### ToggleVertexColor.mcr
- Vertex color display toggle
- Quick color visualization
- Shading mode switching

**Use Case:** Vertex color workflow

#### WireframeEdgeFaceOff.mcr
- Wireframe display modes
- Custom viewport shading
- Edge/face visibility control

**Use Case:** Custom viewport display preferences

---

### RulersHelpers

#### PolyConstraintsExtended.mcr
- Extended transform constraints
- Custom constraint modes
- Constraint combinations

**Use Case:** Precise transform operations

#### SmartConstraint.mcr
- Intelligent constraint system
- Auto-detect constraint needs
- Quick constraint switching

**Use Case:** Faster transform workflows

#### SmartConstraint2.mcr
- Advanced constraint system (v2)
- Enhanced constraint detection
- More constraint options

**Use Case:** Complex transform scenarios

---

### SceneManagement

#### AddTurnToPoly.mcr
- Convert objects to Editable Poly
- Clean conversion process
- Preserves attributes

**Use Case:** Preparing objects for poly modeling

#### AppendBoundsSuffix.mcr
- Automatic bounding box suffix
- Name-based organization
- Quick bound identification

**Use Case:** Game asset organization

#### CleanCollapse.mcr
- Clean modifier stack collapse
- Preserves important attributes
- Better than standard collapse

**Use Case:** Finalizing meshes for export

#### ExtractReference.mcr
- Reference object extraction
- Break reference links
- Editable copy creation

**Use Case:** Working with XRefs and references

#### OpenLayerManager.mcr
- Quick layer manager access
- Keyboard shortcut support
- Faster layer access

**Use Case:** Scene organization workflows

#### ResetPositionRotationScale.mcr
- Transform reset utility
- Zero out transforms
- Clean object state

**Use Case:** Preparing objects for export/rigging

---

### StackManagement

#### CollapseStackRetainInstance.mcr
- Instance-preserving collapse
- Safe stack collapse
- Maintains instance relationships

**Use Case:** Collapsing while keeping instances

#### JumpToEditableAndExit.mcr
- Quick jump to base object
- Skip modifier stack
- Exit stack quickly

**Use Case:** Rapid base mesh editing

---

### Toolsets

#### MatIDToolBox
**Location:** `Toolsets/MatIDToolbox/MatIDToolBox.ms`

Complete material ID management suite:
- Assign IDs by selection
- Shuffle and randomize IDs
- Copy/paste IDs between objects
- ID-based selection
- ID visualization

**Use Case:** Complete material ID workflow

#### PolyDrawOptions
**Location:** `Toolsets/PolyDraw/PolyDrawOptions.ms`

Poly draw configuration tool:
- Custom draw settings
- Draw mode presets
- Quick draw switching

**Use Case:** Optimizing PolyDraw workflow

---

### ViewportTools

#### SetViewFromClosestAngle.mcr
- Smart viewport angle setting
- Closest standard view
- Quick view alignment

**Use Case:** Aligning viewport to geometry

---

### ModifierButtonReplacements

#### ModifierAdd_CustomModifiers.mcr
- Quick add custom modifiers
- Bypasses standard list
- Faster modifier addition

#### ModifierAdd_QuadCap.mcr
- QuadCap modifier quick add
- Pre-configured settings

#### ModifierAdd_Standards.mcr
- Standard modifiers quick add
- Common modifier shortcuts

#### ModifierAdd_tySelect.mcr
- tySelect modifier integration
- Quick selection modifier

**Use Case:** Faster modifier workflow

---

### ObjectCreation

#### LetterSequenceMaker.ms
- Create letter/number sequences
- Automatic spacing and alignment
- Batch text creation

**Use Case:** Creating signs, labels, UI elements

---

## 🔧 Custom Modifiers

### Edit Poly Category (8 modifiers)

All Edit Poly modifiers provide direct modifier-based access to Edit Poly operations:

#### Modifier_EPoly_autoSmooth.ms
- Auto-smooth as modifier
- Non-destructive smoothing
- Adjustable parameters

#### Modifier_EPoly_bevel.ms
- Bevel as modifier
- Editable bevel parameters
- Non-destructive bevel

#### Modifier_EPoly_connect.ms
- Connect as modifier
- Edge/vertex connection
- Parametric connections

#### Modifier_EPoly_delete.ms
- Delete as modifier
- Element removal
- Safe deletion

#### Modifier_EPoly_extrude.ms
- Extrude as modifier
- Parametric extrusion
- Height/bevel control

#### Modifier_EPoly_extrudeAlongSpline.ms
- Extrude along spline path
- Spline-based extrusion
- Profile control

#### Modifier_EPoly_inset.ms
- Inset as modifier
- Face inset operation
- Editable inset amount

#### Modifier_EPoly_outline.ms
- Outline as modifier
- Face outline operation
- Parametric outline

**Use Case:** Non-destructive Edit Poly operations in modifier stack

---

### SimpleMesh Category (10 modifiers)

Work directly on mesh data with simple operations:

#### Modifier_SimpleMesh_CornerSetSelect.ms
- Select corner vertices
- Corner detection
- Selection-based operations

#### Modifier_SimpleMesh_MaterialIDBySG.ms
- Set Material IDs from Smoothing Groups
- Automatic ID assignment
- SG-based organization

#### Modifier_SimpleMesh_SGFromMatID.ms
- Set Smoothing Groups from Material IDs
- Reverse operation
- ID-based smoothing

#### Modifier_SimpleMesh_SGFromVB.ms
- Smoothing Groups from Vertex Breaks
- Topology-based smoothing
- Auto-smooth by angles

#### Modifier_SimpleMesh_ShiftMaterialID.ms
- Shift Material ID values
- Batch ID modification
- Offset all IDs

#### Modifier_SimpleMesh_ShiftSmoothingGroups.ms
- Shift Smoothing Group values
- Batch SG modification
- Offset all SGs

#### Modifier_SimpleMesh_SplitMesh.ms
- Split mesh by criteria
- Element separation
- Mesh detachment

#### Modifier_SimpleMesh_UVOffsetByMaterialID.ms
- Offset UVs per Material ID
- ID-based UV manipulation
- Batch UV offsetting

#### Modifier_SimpleMesh_VertexColorMod.ms
- Vertex color operations
- Color manipulation
- Gradient tools

#### Modifier_SimpleMesh_VertWeightTransfer.ms
- Transfer vertex weights
- Weight copying
- Cross-object weights

**Use Case:** Mesh manipulation and organization

---

### SimpleMod Category (6 modifiers)

Simple geometric transformations:

#### Modifier_SimpleMod_Boxify.ms
- Transform to box shape
- Cubic deformation
- Adjustable strength

#### Modifier_SimpleMod_Cylindrify.ms
- Transform to cylinder shape
- Radial deformation
- Axis selection

#### Modifier_SimpleMod_Offset.ms
- Geometric offset
- Inset/outset operations
- Distance control

#### Modifier_SimpleMod_Pinch.ms
- Pinch deformation
- Point-based pinch
- Strength control

#### Modifier_SimpleMod_Scale.ms
- Modified scale operation
- Axis-based scaling
- Center point control

#### Modifier_SimpleMod_Spherify.ms
- Transform to sphere shape
- Spherical deformation
- Adjustable strength

**Use Case:** Geometric deformations and shape modifications

---

## 🎯 Usage Examples

### Example 1: Clean Export Workflow

**Goal:** Prepare mesh for game engine export

```maxscript
-- 1. Fix topology
PolyFlowTools (check edge flow)

-- 2. Set material IDs
Apply "SimpleMesh Material ID by SG" modifier

-- 3. Isolate work area
SmartIsolate (focus on object)

-- 4. Clean collapse
CleanCollapse (collapse to editable poly)

-- 5. Reset transforms
ResetPositionRotationScale (zero out)

-- 6. Export
File > Export...
```

### Example 2: Character Modeling

**Goal:** Create clean character mesh topology

```maxscript
-- 1. Use flow tools
PolyFlowTools (analyze edge flow)
PolyLoopTools (select and modify loops)

-- 2. Weight management
PolyVertWeightSmoothFace (smooth vertex weights)

-- 3. Visualization
DisplayMaterialIDsInViewport (check UVs)
SmartIsolate (focus on face)

-- 4. Final topology
PolySmartCollapse (reduce where needed)
```

### Example 3: Hard Surface Modeling

**Goal:** Create hard surface object with clean shading

```maxscript
-- 1. Chamfer without affecting SG
PolyChamferNoSmoothing (add bevels)

-- 2. Set smoothing groups
Modifier_SimpleMesh_SGFromVB (auto-smooth by angle)

-- 3. Verify material IDs
DisplayMaterialIDsInViewport (check)

-- 4. Non-destructive extrusions
Modifier_EPoly_extrude (parametric extrude)

-- 5. Shape modifications
Modifier_SimpleMod_Boxify (if needed)
```

---

## ⚠️ Known Issues

### MVP-Graveyard

**Warning:** The MVP-Graveyard folder contains experimental and abandoned features:

```
MVP-Graveyard/
├── Modifier_Curve.ms (may not work)
├── Modifier_SimpleMesh_GrowSGs.ms (unstable)
├── Modifier_SimpleMesh_MakePlanar.ms (incomplete)
├── Modifier_SimpleMesh_Outline.ms (deprecated)
├── Modifier_SimpleMesh_PlanarBySG.ms (issues)
├── Modifier_SimpleMesh_RelaxBySG.ms (slow)
├── Modifier_SimpleMesh_SGFromMaterialID.ms (buggy)
├── Modifier_SimpleMesh_SliceGrid.ms (unstable)
└── Modifier_SimpleMesh_SmoothToAdjecent.ms (issues)
```

**⚠️ Use at your own risk - No support provided**

### General Issues

1. **Compatibility:**
   - Tested on Max 2020-2023
   - May not work on newer versions
   - No compatibility testing planned

2. **Performance:**
   - Some scripts slow on high-poly meshes
   - Complex operations may take time
   - Progress feedback limited

3. **Bugs:**
   - Some edge cases not handled
   - Error handling may be incomplete
   - No bug fixes planned

4. **Documentation:**
   - Some scripts lack detailed docs
   - Context menus may vary by Max version
   - Hotkeys need manual setup

---

## 📚 External Documentation

### Full Documentation

**Google Docs:** [ST3E Complete Documentation](https://docs.google.com/document/d/1fIKEurSNeaazzYsPnCTYT7bVO4R4btWzTzvLRpjNutY/edit?usp=sharing)

Contains:
- Detailed tool descriptions
- Screenshots and examples
- Workflow guides
- Tips and tricks
- Known limitations

### Community Resources

- **GitHub:** [Stephko/Toolings](https://github.com/Stephk0/Toolings)
- **Author Portfolio:** [artstation.com/stephko](https://www.artstation.com/stephko)

---

## 🤝 Community & Support

### Getting Help

Since development has ceased:

1. **Check external docs** (Google Docs link above)
2. **Search GitHub issues** for similar problems
3. **Community support only** - no official support
4. **Fork and modify** if you need changes

### Contributing

While no longer actively developed, the community can:

1. **Fork the project**
2. **Make improvements**
3. **Share modifications**
4. **Document solutions**
5. **Help other users**

### License

**Free to share and extend**

- ✅ Use in personal projects
- ✅ Use in commercial projects
- ✅ Modify and redistribute
- ✅ Study and learn from code
- ❌ No warranty provided
- ❌ No support guaranteed

---

## 🎓 Learning from ST3E

### For MaxScript Learners

ST3E is a great resource for:

1. **MaxScript Examples:**
   - Real-world script structure
   - UI creation patterns
   - Context menu integration
   - Modifier creation

2. **Workflow Design:**
   - Tool organization
   - User experience considerations
   - Performance optimization
   - Error handling

3. **Production Practices:**
   - Code organization
   - Documentation approaches
   - Testing strategies
   - Deployment methods

### Recommended Study Files

Start with these simpler scripts:

1. `PolySnapToLocalCenter.mcr` - Basic operation
2. `ToggleVertexColor.mcr` - Simple toggle
3. `ResetPositionRotationScale.mcr` - Transform manipulation
4. `DisplayMaterialIDsInViewport.mcr` - Viewport display

Then move to complex ones:

1. `MatIDToolBox.ms` - Complete toolset
2. `PolyFlowTools.mcr` - Advanced topology
3. Custom modifiers - Modifier creation

---

## 🗺️ Migration to Blender

### Why Blender?

Development shifted to Blender because:

1. **Open Source:** No licensing restrictions
2. **Active Development:** Frequent updates
3. **Growing Industry Adoption:** More studios using Blender
4. **Python:** More powerful scripting
5. **Modern Features:** Better tooling and APIs

### Equivalent Tools

| 3ds Max Tool | Blender Equivalent |
|--------------|-------------------|
| SmartIsolate | Smart Collapse |
| PolyFlowTools | Center Loops |
| MaterialIDBySG | Smart Crease (for edge definition) |
| CleanCollapse | Mass Exporter (with apply modifiers) |
| Various display | Edit Mode Overlay |

### For 3ds Max Users

Consider trying Stephko's Blender tools:

- More actively developed
- Better documentation
- Modern workflow integration
- Free and open source

---

## 📊 Statistics

### By the Numbers

- **Scripts:** 50+
- **Custom Modifiers:** 24
- **Lines of Code:** ~10,000+
- **Development Time:** 3+ years
- **Last Update:** 2023
- **Status:** Archived

### Categories

| Category | Count |
|----------|-------|
| Editing Operations | 12 |
| Selection Tools | 4 |
| Inspection | 8 |
| Scene Management | 6 |
| Custom Modifiers | 24 |
| Toolsets | 2 |
| Other | 10+ |

---

## 💭 Final Thoughts

### Legacy

ST3E represents years of production experience and workflow optimization for 3ds Max. While no longer actively developed, it remains a useful resource for:

- **Current 3ds Max users** seeking workflow improvements
- **MaxScript learners** studying real-world examples
- **Tool developers** understanding workflow design
- **Production studios** with existing Max pipelines

### Future

Development focus has shifted to **Blender tooling**, where:

- More active development
- Better integration possibilities
- Growing user base
- Open source advantages

**Check out:** [Blender Addons](../Blender/Addons/) for current work

---

## 📞 Contact

**Author:** Stephan Viranyi  
**Email:** stephko@viranyi.de  
**Portfolio:** [artstation.com/stephko](https://www.artstation.com/stephko)  
**GitHub:** [github.com/Stephk0](https://github.com/Stephk0)

---

## 🙏 Acknowledgments

Thanks to:
- The 3ds Max community
- Early testers and users
- Autodesk for 3ds Max
- Everyone who provided feedback

---

**ST3E - Archiving 3 years of 3ds Max workflow optimization**

*Made with ❤️ by Stephan Viranyi*

