# Quick Animation Export

**Version:** 1.0.9 · **Blender:** 4.2+ · **Category:** Animation · **Author:** Stephan Viranyi

Streamlined export of animation/action clips from Blender to game-engine-ready files.

## Install
Drag-and-drop the latest zip from [`distribution/`](distribution/) onto Blender
(4.2+), or install it via *Edit ▸ Preferences ▸ Add-ons ▸ Install from Disk*.

## Folder layout
- `source/` — addon package (`__init__.py`, `operators.py`, `properties.py`, `ui.py`,
  `al_bridge.py`, `icons/`, plus the `_make_annotated_doc.py` dev helper)
- `distribution/` — current installable zip; older builds in `distribution/archive/`
- `assets/` — panel/doc screenshots (`QuickAnimationExport_docs.png`,
  `quick_anim_export_screenshot.png`)

See the repo-level `_TOOLING_STRUCTURE.md` for the standard tool layout.
