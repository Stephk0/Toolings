# Quick Animation Export — developer notes

Implementation and maintenance notes. User docs: [README](../README.md).

## Folder layout
- `source/` — addon package (`__init__.py`, `operators.py`, `properties.py`, `ui.py`,
  `al_bridge.py`, `icons/`, plus the `_make_annotated_doc.py` dev helper)
- `distribution/` — current installable zip; older builds in `distribution/archive/`
- `assets/` — panel/doc screenshots (`QuickAnimationExport_docs.png`,
  `quick_anim_export_screenshot.png`)

See the repo-level `_TOOLING_STRUCTURE.md` for the standard tool layout.
