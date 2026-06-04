# Synced Modifiers

**Version:** 2.5.0 · **Blender:** 2.91+ · **Category:** Object · **Author:** Stephan Viranyi

Add modifiers to multiple objects at once and keep them synchronized using Blender's
driver system — now with Geometry Nodes support.

## Features
- Driver-based sync of modifier properties across many objects
- Geometry Nodes modifier support with dynamic input syncing
- Sync ID system (`ModifierName (Source:abc123)`) for reliable source tracking
- Reference-field sync (Object / Collection / Material) with viewport refresh
- Find original source by tracing the driver chain; resync when GN inputs change

## Install
Drag-and-drop the latest zip from [`distribution/`](distribution/) onto Blender
(4.2+), or install it via *Edit ▸ Preferences ▸ Add-ons ▸ Install from Disk*.

## Folder layout
- `source/` — addon source (`__init__.py`, modules, and dev/design docs:
  `CLAUDE.md`, `INSTALLATION.md`, `GEOMETRY_NODES_IMPLEMENTATION_PLAN.md`, `CHANGELOG_v2.4.1.md`)
- `distribution/` — current installable zip; older builds in `distribution/archive/`

See the repo-level `_TOOLING_STRUCTURE.md` for the standard tool layout.
