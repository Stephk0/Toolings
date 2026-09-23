# Stephko Toolings

> Production-ready tools for Blender, Unity, and 3DS Max workflows

[![Blender](https://img.shields.io/badge/Blender-4.5+-orange.svg)](https://www.blender.org/)
[![3DS Max](https://img.shields.io/badge/3DS%20Max-Legacy-blue.svg)](https://www.autodesk.com/products/3ds-max/)
[![License](https://img.shields.io/badge/License-Free-green.svg)](LICENSE)

---

## 🚀 Start here

| I want to… | Go to |
|------------|-------|
| Browse every tool with versions | 📖 **[Complete Documentation Index](DOCUMENTATION_INDEX.md)** |
| Install a Blender addon | ⬇️ **[Addon table below](#-blender-addons)** — grab the zip from the tool's `distribution/` |
| Use the Geometry Nodes library | 🧱 **[ST3E Geometry Nodes Library](Blender/Geonodes/README.md)** |
| Look up a shortcut or operator | 📝 **[Quick Reference](QUICK_REFERENCE.md)** |
| Understand a Blender API trap | 🧠 **[Blender Knowledge](Blender/Knowledge/README.md)** |

---

## 🔷 Blender Addons

18 production-ready addons. Each lives in its own folder — **README** links to the usage docs,
**zip** links to the installable build (older builds in that folder's `archive/`).

### Export & Pipeline

| Tool | What it does | Docs | Download |
|------|--------------|------|----------|
| **Mass Collection Exporter** | Batch export collections/objects (FBX, OBJ, DAE, glTF) with suffix grouping, parent-empty handling and per-collection settings | [README](Blender/Addons/MassExporter/README.md) · [flow charts](Blender/Addons/MassExporter/EXPORT_FLOW.md) | [zip](Blender/Addons/MassExporter/distribution/) |
| **Quick Animation Export** | One-click export of animation/action clips to game-engine-ready files | [README](Blender/Addons/QuickAnimationExport/README.md) | [zip](Blender/Addons/QuickAnimationExport/distribution/) |
| **Library Publisher** | Publishes the ST3E asset library to a Google Shared Drive as `ST3E_Ext` | [README](Blender/Addons/LibraryPublisher/README.md) | [zip](Blender/Addons/LibraryPublisher/distribution/) |
| **Library Relink** | Bulk-relink a file's linked libraries to a new folder, with dry-run preview | [README](Blender/Addons/LibraryRelink/README.md) | [zip](Blender/Addons/LibraryRelink/distribution/) |

### Modeling

| Tool | What it does | Docs | Download |
|------|--------------|------|----------|
| **Smart Crease** | Context-sensitive edge/vertex crease with preset keys + modal mouse control | [README](Blender/Addons/Smart%20Crease/README.md) | [zip](Blender/Addons/Smart%20Crease/distribution/) |
| **Smart Collapse** | 3ds Max-style collapse (collapse + merge at center) | [README](Blender/Addons/Smart%20Collapse/README.md) | [zip](Blender/Addons/Smart%20Collapse/distribution/) |
| **Smart Set Orientation** | Transform orientation from selection, Maya working-pivot style | [README](Blender/Addons/Smart%20Set%20Orientation/README.md) | [zip](Blender/Addons/Smart%20Set%20Orientation/distribution/) |
| **Center Edges / Loops** | Center edge loops or selections along their average position | [README](Blender/Addons/Center%20Edges/README.md) | [zip](Blender/Addons/Center%20Edges/distribution/) |
| **Edge Constraint Mode** | 3ds Max-style edge constraint — verts slide along topology during transforms | [README](Blender/Addons/EdgeConstraintMode/README.md) | [zip](Blender/Addons/EdgeConstraintMode/distribution/) |

### Modifiers

| Tool | What it does | Docs | Download |
|------|--------------|------|----------|
| **Synced Modifiers** | Add & keep modifiers synchronized across objects via drivers, incl. Geometry Nodes inputs | [README](Blender/Addons/SyncedModifiers/README.md) | [zip](Blender/Addons/SyncedModifiers/distribution/) |
| **Modifier List (Stephko fork)** | Enhanced modifier-stack UI (list view, popup, sidebar) with the GN input-attribute toggle fix | [README](Blender/Addons/ModifierList_Stephko/README.md) | [zip](Blender/Addons/ModifierList_Stephko/distribution/) |
| **Toggle Modifier Display** | Quick modifier visibility toggle in edit mode (D / Shift+D), 3ds Max show-end-result style | [README](Blender/Addons/Toggle%20Modifier%20Display/README.md) | [zip](Blender/Addons/Toggle%20Modifier%20Display/distribution/) |

### UV, Naming & Rigging

| Tool | What it does | Docs | Download |
|------|--------------|------|----------|
| **Tile UV Projector** | Tile-based UV projection/placement for texture-atlas workflows | [README](Blender/Addons/TileUVProjector/README.md) | [zip](Blender/Addons/TileUVProjector/distribution/) |
| **Add Bounds To Name** | Rename objects from bounding-box dimensions (units, rounding, swizzle, presets) | [README](Blender/Addons/AddBoundsToName/README.md) | [zip](Blender/Addons/AddBoundsToName/distribution/) |
| **Skin Transfer Setup** | Per-part skin setup (as-is / data transfer / bind-to-bone) with centralized rig + base | [README](Blender/Addons/SkinTransferSetup/README.md) | [zip](Blender/Addons/SkinTransferSetup/distribution/) |

### Viewport & Render

| Tool | What it does | Docs | Download |
|------|--------------|------|----------|
| **Compositor Render Sets** | Multi-render-setup management for compositor workflows, with batch rendering | [README](Blender/Addons/Compositor%20Render%20Sets/README.md) | [zip](Blender/Addons/Compositor%20Render%20Sets/distribution/) |
| **Edit Mode Overlay** | Enhanced edit-mode viewport feedback / text overlay | [README](Blender/Addons/Edit%20Mode%20Overlay/README.md) | [zip](Blender/Addons/Edit%20Mode%20Overlay/distribution/) |

### Authoring tooling

| Tool | What it does | Docs | Download |
|------|--------------|------|----------|
| **LLM Geonode Pipeline** | Reads and lays out Geometry Nodes graphs — `tidy_layout` engine + GeoNode Layout MCP server | [README](Blender/Addons/LLMGeonodePipeline/README.md) · [criteria](Blender/Addons/LLMGeonodePipeline/GEONODE_CRITERIA.md) | [zip](Blender/Addons/LLMGeonodePipeline/distribution/) |

> Folder convention and release steps: [`Blender/Addons/_TOOLING_STRUCTURE.md`](Blender/Addons/_TOOLING_STRUCTURE.md)

---

## 🧱 Blender Geometry Nodes — the ST3E library

**53 modifiers**, reachable straight from **Add Modifier → ST3E**, plus supporting node groups.
Every asset ships an Asset Browser icon and a demo object with the modifier already attached.

| Link | What you get |
|------|--------------|
| 📚 **[Full library reference](Blender/Geonodes/README.md)** | All 53 modifiers with icons, parameters and source files |
| 🎯 [Deformers](Blender/Geonodes/README.md#deformers) | Inflate, Twist, Taper, Stretch, Bend, Wave, Cast, Erosion, NoiseDisplace, … |
| 🏗 [Generators & Topology](Blender/Geonodes/README.md#generators--topology) | Subdivide, Wireframe, VoxelRemesh, Scatter, MeshBoolean, QuadCap, Mosaic, … |
| 🔧 [Mesh & Attribute Utilities](Blender/Geonodes/README.md#mesh--attribute-utilities) | AutoSmooth, MaterialOverride, GrowSelection, AttributeTransfer, AmbientOcclusion, … |
| 🖼 [Asset Browser icons](Blender/Geonodes/_icons/ICONS.md) | The headless icon pipeline ([gotchas](Blender/Geonodes/_icons/GOTCHAS.md)) |
| 🌳 [Procedural Tree Generator](Blender/Geonodes/TreeGenDocu/README.md) | Setup guide + [full specification](Blender/Geonodes/TreeGenDocu/ProceduralTreeGenerator_Specification.md) |
| 🧠 [Geonode authoring knowledge](Blender/Knowledge/geonodes/asset-checklist.md) | Build recipe, layout rules, field semantics, publish checklist |
| 🔍 [Dependency audit](Blender/Knowledge/DEPENDENCY_REPORT.md) | External-dependency report for every geonode file |

---

## 🎨 Blender Shading

Blender re-creations of Unity URP shaders and viewport-only effects (cavity, curvature, SSS).
→ **[Shading README](Blender/Shading/README.md)** · [notes](Blender/Knowledge/shading.md)

---

## 🔶 Unity Tools

| Tool | What it does | Docs |
|------|--------------|------|
| **Model Import Processor** | Automated FBX/model import processing pipeline (Unity 2019.4+) | [README](Unity/ModelImportProcessor/README.md) · [quick ref](Unity/ModelImportProcessor/QUICK_REFERENCE.md) · [architecture](Unity/ModelImportProcessor/SYSTEM_ARCHITECTURE.md) |

---

## 🔸 3DS Max Tools (Legacy — ST3E)

Comprehensive MaxScript collection — [README](3DSMAX/README.md) · [external documentation](https://docs.google.com/document/d/1fIKEurSNeaazzYsPnCTYT7bVO4R4btWzTzvLRpjNutY/edit?usp=sharing)

> ⚠️ **Note:** 3DS Max tools are in maintenance mode (development stopped 2023)

---

## ⚡ Quick Installation

### Blender Addons

Every addon lives in its own folder under `Blender/Addons/<Tool>/`; the current installable
zip is in `Blender/Addons/<Tool>/distribution/` (older builds in `distribution/archive/`) —
use the **Download** column in the [addon table](#-blender-addons).

**Option A: Direct Install**
```
1. Take the zip from Blender/Addons/<Tool>/distribution/
2. Blender → Edit → Preferences → Add-ons
3. Click "Install from Disk..." (or drag & drop the zip) and select it
4. Enable checkbox
```

**Option B: Manual Install**
```
1. Extract the zip into:
   Windows: %APPDATA%\Blender Foundation\Blender\[version]\scripts\addons\
   macOS: ~/Library/Application Support/Blender/[version]/scripts/addons/
   Linux: ~/.config/blender/[version]/scripts/addons/
2. Restart Blender
3. Enable in Preferences
```

### Geometry Nodes
```
1. Preferences → File Paths → Asset Libraries
2. Add a library pointing at the Blender/ folder
   (the asset catalog blender_assets.cats.txt lives there)
3. Set Import Method: Link
4. Add Modifier → ST3E, or drag from the Asset Browser
```

### 3DS Max Tools (ST3E)
```
Scripts: Copy ST3E + Startup folders → [MaxRoot]\scripts\
Modifiers: Copy Custom Modifiers contents → [MaxRoot]\Plugins\
```

[Detailed Installation Instructions](DOCUMENTATION_INDEX.md#-installation-guides)

---

## 📚 Documentation map

**Repo-wide**
- 📖 [Complete Documentation Index](DOCUMENTATION_INDEX.md) — every tool, with versions
- 📝 [Quick Reference](QUICK_REFERENCE.md) — shortcuts and operators at a glance
- 🔧 [Installation Guide](DOCUMENTATION_INDEX.md#-installation-guides) · 🐛 [Troubleshooting](DOCUMENTATION_INDEX.md#-troubleshooting)
- 🌐 [Docs site](docs-site/README.md) — Astro/Starlight build of these docs

**Blender**
- 🧱 [ST3E Geometry Nodes Library](Blender/Geonodes/README.md) — the full 53-modifier reference
- 🧠 [Blender Knowledge](Blender/Knowledge/README.md) — API traps, export rules, headless runs, shading
  - [bpy API gotchas](Blender/Knowledge/bpy-api-gotchas.md) · [export pipeline](Blender/Knowledge/export-pipeline.md) · [headless & automation](Blender/Knowledge/headless-and-automation.md) · [addon architecture](Blender/Knowledge/addon-architecture.md)
  - Geonodes: [asset checklist](Blender/Knowledge/geonodes/asset-checklist.md) · [layout](Blender/Knowledge/geonodes/layout.md) · [nodes & fields](Blender/Knowledge/geonodes/nodes-and-fields.md) · [sockets & menus](Blender/Knowledge/geonodes/sockets-and-menus.md) · [techniques](Blender/Knowledge/geonodes/techniques.md) · [asset files](Blender/Knowledge/geonodes/asset-files.md)
- 📐 [Addon folder convention](Blender/Addons/_TOOLING_STRUCTURE.md) — layout + release steps
- 🛠 [Shared addon-dev notes](Blender/Addons/docs/)

**Per-tool:** every folder under `Blender/Addons/` has its own `README.md` — linked from the
[addon table](#-blender-addons) above.

---

## ⚙️ Requirements

### Blender
- **Version:** 5.0 target, 4.5+ supported (Geometry Nodes library needs 5.0+)
- **Platform:** Windows, macOS, Linux
- **Dependencies:** None (pure Python)

### 3DS Max (Legacy)
- **Version:** 2020+ (some scripts should work with older versions)
- **Platform:** Windows only
- **Dependencies:** MaxScript runtime (included with Max)

---

## 🎨 Project Status

| Tool Category | Status | Development |
|--------------|--------|-------------|
| Blender Addons | ✅ Active | New features, bug fixes |
| Blender GeoNodes | ✅ Active | New nodes, optimization |
| Blender Shading | ✅ Active | URP ports, viewport-effect node groups |
| Unity Tools | 🔄 Light | Model Import Processor |
| 3DS Max (ST3E) | ⚠️ Maintenance | Bug fixes only |

---

## 🤝 Contributing

While this is primarily a personal toolset, feedback and suggestions are welcome!

**Ways to contribute:**
- Report bugs or issues via email
- Suggest features or improvements
- Share workflows and use cases
- Create tutorial content

**Not accepting pull requests** at this time, but feel free to fork and modify for your needs!

---

## 📞 Contact & Support

**Author:** Stephan Viranyi (Stephko)

📧 Email: stephko@viranyi.de  
🎨 Portfolio: [ArtStation](https://www.artstation.com/stephko)  
💼 LinkedIn: [stephanviranyi](https://www.linkedin.com/in/stephanviranyi/)


---

## 📜 License

**Free & Open Use**

✅ Use in personal projects  
✅ Use in commercial projects  
✅ Modify and customize  
✅ Share with others  
✅ Learn from the code

❌ Attribution appreciated but not required  
❌ No warranty provided (use at own risk)

---

## 🌟 Credits

**Development:** Stephan Viranyi  
**AI Assistance:** Claude AI (Anthropic) for code generation and documentation with Blender MCP 
**Testing:** Personal production use + community feedback

**Built With:**
- Blender Python API
- MaxScript (3DS Max)
- Love for efficient workflows ❤️


---

## 🏆 Showcase

**Want to share your work using these tools?**

Send examples to stephko@viranyi.de with:
- Project name and description
- Which tools you used
- How they helped your workflow
- Permission to showcase

Featured projects may be added to documentation!

---

## ⚡ Quick Command Reference

### Blender Shortcuts (addon-specific)

Most addons add operators accessible via:
- `F3` → Search menu (search addon name)
- `N` → Side panel (many addons add panels)
- Context menus in Edit Mode


---

## 🔔 Stay Updated

Watch this repository or star it to be notified of updates!

**Recent Updates:**
- September 2026: README rebuilt around direct per-tool links; addons flattened to `Blender/Addons/<Tool>/`
- September 2026: Asset Browser icons for every ST3E asset (67, rendered headlessly — see [`_icons/`](Blender/Geonodes/_icons/ICONS.md)); library now 53 modifiers, incl. GN_QuadCap
- June 2026: Documentation refresh — full addon roster + [geonode library reference](Blender/Geonodes/README.md)
- Earlier: Mass Exporter v13.6, Synced Modifiers v2.5, Tile UV Projector, Edge Constraint Mode

---

## 🙏 Acknowledgments

Thanks to:
- Blender Community
- Blender Foundation for amazing software
- Anthropic for Claude AI assistance
- 3D community for feedback and testing
- Everyone using and enjoying these tools!

---

**⭐ Don't forget to check out the [Complete Documentation Index](DOCUMENTATION_INDEX.md)!**

---

*Built with ❤️ for the 3D community*

**Happy Creating! 🚀**
