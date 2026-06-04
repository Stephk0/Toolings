# Modifier List (Stephko fork)

**Version:** 1.9.89 · **Blender:** 4.2+ · **Category:** Interface · **Author:** Stephan Viranyi (fork)

A fork of the *Modifier List* addon with Stephko-specific fixes — notably restoring the
**Geometry Nodes Input Attribute Toggle** in the list view on Blender 5.

## Install
Drag-and-drop the latest zip from [`distribution/`](distribution/) onto Blender
(4.2+), or install it via *Edit ▸ Preferences ▸ Add-ons ▸ Install from Disk*.

## Folder layout
- `source/` — full addon tree (`__init__.py`, `modules/`, `addon_registration.py`,
  `icons/`, `dev_tools/`, `tests/`, `docs/`, `CHANGELOG.md`, `LICENSE`)
- `distribution/` — current installable zip; older builds in `distribution/archive/`

> Upstream project retains its own `LICENSE` and `CHANGELOG.md` inside `source/`.

See the repo-level `_TOOLING_STRUCTURE.md` for the standard tool layout.
