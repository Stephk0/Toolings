# Changelog — Edge Constraint Mode

## 2.0.0 — 2026-10-15

- **New:** Constraint dropdown like 3ds Max (None / Edge / Face / Normal) in the
  Edit-mode header, plus a settings popover (Reach, Stop at Selected, Debug).
- **Fixed:** rotating or scaling a selected loop now works like Max. Each vertex
  slides along the edge that crosses the selection, so rotating a cube's loop
  shears it and the cube stays a cube. v1.x let verts slide along the loop's
  own edges and could push them backwards off the end of an edge.
- **New:** Face constraint (slide over the surrounding surface) and Normal
  constraint (along the vertex normal).
- **New:** in-transform axis locks (X/Y/Z, again for Local, Shift for plane),
  typed numeric values, Ctrl snapping, G/R/S switching, proper mouse to world
  mapping, Pivot Point setting (median, bounds, cursor, active), and
  multi-object edit mode.
- **New:** Redo / Adjust Last Operation (F9) and scripted use via
  `bpy.ops.mesh.edge_constraint_transform(...)`.
- **Changed:** G/R/S are bound once and fall through to Blender's transform
  when the constraint is None, instead of installing and removing keymap items
  on every toggle. The mode no longer switches itself off when you leave Edit
  mode.
- Refactored to WMH split (bpy-free `core/` + pytest, `blender/` UI).
- Added `blender_manifest.toml`.

## 1.1.2

- Restores built-in tool gizmos hidden by 1.1.0 / 1.1.1. Custom gizmo group removed.

## 1.1.0 – 1.1.1

- Persistent header toggle, transform-agnostic solver, experimental gizmo group.

## 1.0.x

- Initial single-operator releases.
