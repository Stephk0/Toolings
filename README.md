# ST3E — Stephko's 3D Extensions

![ST3E Geometry Nodes library in the Asset Browser, next to the character example scene](Blender/Examples/ST3E_Library_Overview.jpg)

> Production-ready tools for Blender, Unity, and 3DS Max workflows

[![Blender](https://img.shields.io/badge/Blender-5.0%20%C2%B7%204.5+-orange.svg)](https://www.blender.org/)
[![3DS Max](https://img.shields.io/badge/3DS%20Max-Legacy-blue.svg)](https://www.autodesk.com/products/3ds-max/)
[![License](https://img.shields.io/badge/License-Free-green.svg)](#-license)

Free Blender addons, a 53-modifier Geometry Nodes library, shader ports, and a legacy 3ds Max
toolkit — built for and tested in real production.
**Every tool below links straight to its docs and its installable zip.**

**Why "ST3E"?** It is the name for the whole toolset, not just one part of it. Three letters
you can type with one hand, so it is quick to call up and search for — and wherever it
appears (the *Add Modifier → ST3E* menu, the `ST3E` asset tag, these docs) it leads you to the
rest of the tools.

---

## ✨ New: Geometry Constraint

![Geometry Constraint: Edge, Face and Normal constraints keep Blender's Move, Rotate and Scale on the mesh](Blender/Addons/GeometryConstraint/assets/demo/geometry_constraint_demo.gif)

3ds Max Editable Poly constraints for Blender: switch it on in the Edit-mode header, pick
**Edge**, **Face** or **Normal**, and every native transform (keys, gizmos, menus, F9) stays
on the mesh. [Docs](Blender/Addons/GeometryConstraint/README.md) ·
[zip](Blender/Addons/GeometryConstraint/distribution/)

## ✨ New: Modifier Stack Actions

![Modifier Stack Actions: Show Up To Here, Extract As, Add Modifier After, Move to Last](Blender/Addons/ModifierStackActions/assets/demo/modifier_stack_actions_demo.gif)

Right-click any modifier: see the stack up to that modifier, extract the mesh at that point as
a new object, add or paste a modifier right before or after it, or move it up, down, to the
top or bottom.
[Docs](Blender/Addons/ModifierStackActions/README.md) ·
[tutorial](Blender/Addons/ModifierStackActions/TUTORIAL.md) ·
[zip](Blender/Addons/ModifierStackActions/distribution/)

---

## 🔷 Blender Addons

| Tool | What it does | Get it |
|------|--------------|--------|
| **Add Bounds To Name** | Rename objects from their bounding-box dimensions | [docs](Blender/Addons/AddBoundsToName/README.md) · [zip](Blender/Addons/AddBoundsToName/distribution/) |
| **Center Edges / Loops** | Center edge loops or selections along their average position | [docs](Blender/Addons/Center%20Edges/README.md) · [zip](Blender/Addons/Center%20Edges/distribution/) |
| **Compositor Render Sets** | Manage multiple render setups in the compositor, with batch rendering | [docs](Blender/Addons/Compositor%20Render%20Sets/README.md) · [zip](Blender/Addons/Compositor%20Render%20Sets/distribution/) |
| **Edit Mode Overlay** | Extra edit-mode viewport feedback and text overlay | [docs](Blender/Addons/Edit%20Mode%20Overlay/README.md) · [zip](Blender/Addons/Edit%20Mode%20Overlay/distribution/) |
| **Geometry Constraint** | 3ds Max-style Edge / Face / Normal constraint toggle — every Move, Rotate and Scale stays on the mesh | [docs](Blender/Addons/GeometryConstraint/README.md) · [zip](Blender/Addons/GeometryConstraint/distribution/) |
| **Library Publisher** | Publish the ST3E asset library to a Google Shared Drive | [docs](Blender/Addons/LibraryPublisher/README.md) · [zip](Blender/Addons/LibraryPublisher/distribution/) |
| **Library Relink** | Bulk-relink a file's linked libraries to a new folder, with a dry-run preview | [docs](Blender/Addons/LibraryRelink/README.md) · [zip](Blender/Addons/LibraryRelink/distribution/) |
| **Mass Collection Exporter** | Batch export collections/objects (FBX, OBJ, glTF) with suffix grouping and per-collection settings | [docs](Blender/Addons/MassExporter/README.md) · [tutorial](Blender/Addons/MassExporter/TUTORIAL.md) · [zip](Blender/Addons/MassExporter/distribution/) |
| **Modifier List (Stephko fork)** | Enhanced modifier-stack UI: list view, popup, sidebar | [docs](Blender/Addons/ModifierList_Stephko/README.md) · [zip](Blender/Addons/ModifierList_Stephko/distribution/) |
| **Modifier Stack Actions** | Right-click a modifier: show or extract the stack up to it, add or paste a modifier before / after it, move it up / down / to first / last | [docs](Blender/Addons/ModifierStackActions/README.md) · [tutorial](Blender/Addons/ModifierStackActions/TUTORIAL.md) · [zip](Blender/Addons/ModifierStackActions/distribution/) |
| **Quick Animation Export** | One-click export of animation/action clips, game-engine ready | [docs](Blender/Addons/QuickAnimationExport/README.md) · [zip](Blender/Addons/QuickAnimationExport/distribution/) |
| **Skin Transfer Setup** | Per-part skinning: as-is, data transfer, or bind-to-bone | [docs](Blender/Addons/SkinTransferSetup/README.md) · [zip](Blender/Addons/SkinTransferSetup/distribution/) |
| **Smart Collapse** | 3ds Max-style collapse — merge at center | [docs](Blender/Addons/Smart%20Collapse/README.md) · [zip](Blender/Addons/Smart%20Collapse/distribution/) |
| **Smart Crease** | Context-sensitive edge/vertex crease with preset keys and modal mouse control | [docs](Blender/Addons/Smart%20Crease/README.md) · [zip](Blender/Addons/Smart%20Crease/distribution/) |
| **Smart Isolate** | 3ds Max Smart Isolate on Numpad / — nests deeper on a sub-selection, can keep cameras and lights | [docs](Blender/Addons/Smart%20Isolate/README.md) · [zip](Blender/Addons/Smart%20Isolate/distribution/) |
| **Smart Set Orientation** | Transform orientation from selection, Maya working-pivot style | [docs](Blender/Addons/Smart%20Set%20Orientation/README.md) · [zip](Blender/Addons/Smart%20Set%20Orientation/distribution/) |
| **Smart Wireframe View** | One hotkey (Shift+Alt+Z) cycles overlays off / overlays / overlays + wireframe | [docs](Blender/Addons/Smart%20Wireframe%20View/README.md) · [zip](Blender/Addons/Smart%20Wireframe%20View/distribution/) |
| **Synced Modifiers** | Keep modifiers in sync across objects, including Geometry Nodes inputs | [docs](Blender/Addons/SyncedModifiers/README.md) · [zip](Blender/Addons/SyncedModifiers/distribution/) |
| **Tile UV Projector** | Tile-based UV projection and placement for texture atlases | [docs](Blender/Addons/TileUVProjector/README.md) · [zip](Blender/Addons/TileUVProjector/distribution/) |
| **Toggle Modifier Display** | Toggle modifier visibility in edit mode (D / Shift+D), 3ds Max "show end result" style | [docs](Blender/Addons/Toggle%20Modifier%20Display/README.md) · [zip](Blender/Addons/Toggle%20Modifier%20Display/distribution/) |

**Install:** drag the zip from the tool's `distribution/` folder onto Blender, or
*Edit → Preferences → Add-ons → Install from Disk…*, then enable it.

---

## 🧱 Geometry Nodes library

**53 modifiers** straight from **Add Modifier → ST3E**: deformers, generators, topology and
attribute tools. Every one has an Asset Browser icon and ships with a demo object.

→ **[Library reference](Blender/Geonodes/README.md)** —
[Deformers](Blender/Geonodes/README.md#deformers) ·
[Generators & Topology](Blender/Geonodes/README.md#generators--topology) ·
[Mesh & Attribute Utilities](Blender/Geonodes/README.md#mesh--attribute-utilities) ·
[Procedural Tree Generator](Blender/Geonodes/TreeGenDocu/README.md)

**Install:** *Preferences → File Paths → Asset Libraries* → add the **`Blender/`** folder
(not `Blender/Geonodes/`), set Import Method to **Link**, then use *Add Modifier → ST3E*.

---

## 🎨 More

- **[Shading](Blender/Shading/README.md)** — Blender re-creations of Unity URP shaders, plus cavity and curvature effects
- **[Unity — Model Import Processor](Unity/ModelImportProcessor/README.md)** — automated FBX/model import pipeline (Unity 2019.4+)
- **[3ds Max](3DSMAX/README.md)** — the original ST3E MaxScript tools and custom modifiers ([full documentation](https://docs.google.com/document/d/1fIKEurSNeaazzYsPnCTYT7bVO4R4btWzTzvLRpjNutY/edit?usp=sharing)). ⚠️ Maintenance only since 2023.

---

## 📚 Help

- 📖 **[Documentation Index](DOCUMENTATION_INDEX.md)** — every tool with its version
- 📝 [Quick Reference](QUICK_REFERENCE.md) — shortcuts and panels at a glance
- 🔧 [Installation details](DOCUMENTATION_INDEX.md#-installation-guides) · 🐛 [Troubleshooting](DOCUMENTATION_INDEX.md#-troubleshooting)
- 🛠 Building or changing these tools? See **[DEVELOPMENT.md](DEVELOPMENT.md)**

**Requirements:** Blender 5.0 recommended, 4.5+ supported. No external Python dependencies.

---

## 📜 License

Free for personal and commercial use — use, modify, and share. Attribution appreciated,
not required. No warranty.

## 📞 Contact

**Stephan Viranyi (Stephko)** — stephko@viranyi.de ·
[ArtStation](https://www.artstation.com/stephko) ·
[LinkedIn](https://www.linkedin.com/in/stephanviranyi/)

Bug reports and ideas welcome by email. Not accepting pull requests, but fork freely.
Developed with Claude (Anthropic) as a coding assistant.
