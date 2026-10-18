# Changelog — Edge Constraint Mode

## 2.2.0 — 2026-10-18

- **Fixed (Edge):** a sliding vertex no longer passes through existing,
  unselected loops. A second loop cut between the first loop and the cube's
  end used to slide straight through the first loop to the end. It now stops
  at the end of its own edge, like 3ds Max.
- **Fixed (Edge):** with edges selected in Edge or Face select mode, an
  unselected edge that joins two selected ones (the rung between two
  selected edges) is now a rail. Scaling or rotating two parallel edges
  slides them along the edges between them. Before, those rungs were
  treated as part of the selection, so the verts stuck or slid off along
  the wrong edge into the neighbouring face.
- **Fixed (Edge):** scaling two selected loops toward each other slides
  them along the edges between them. Before, the corner verts slid sideways
  along their own loop and the cube's walls caved in.
- **New:** **Stop at Vertices** setting (Edge, on by default). Turn it off for
  the old behaviour, where a vertex keeps sliding over the next edges up to
  **Reach**. Reach and Stop at Selected now apply to Edge only while it is
  off.

## 2.1.0 — 2026-10-15

- **New: Live mode.** The constraint is now an on/off toggle that constrains
  Blender's own transforms: G / R / S in any keymap, the toolbar Move /
  Rotate / Scale / Transform gizmos, Mesh ▸ Transform, F3 and Adjust Last
  Operation (F9). Axis locks, typed values, snapping and pivot settings all
  come from Blender itself.
- **New:** the header shows an on/off toggle and an Edge / Face / Normal
  dropdown, placed right after the UV menu so it's always visible.
- **Fixed:** undo and redo keep the constrained result.
- **Fixed (Edge):** the "hinge" vertices of a tilted round loop (cylinder,
  sphere) no longer slide along the loop. A loop's own edges are now used
  only when the motion points back into the selection.
- **Fixed (Face):** a moved patch no longer leaves its trailing vertices
  behind. Every face of the original surface counts.
- **Fixed (Normal):** vertex normals are angle-weighted, matching Blender.
- **Changed:** G / R / S are no longer remapped. The v2.0 modal stays
  available as **Constrained Transform** (F3) for scripting.
- **Not constrained, by design:** scripted transforms from other add-ons,
  extrude / duplicate macros, edge and vertex slide.
- Verified with every **Transform Pivot Point** (Median, Bounding Box,
  3D Cursor, Individual Origins, Active Element), with exact expected
  positions in Blender 5.0, plus real-UI drags around the 3D cursor and
  with Individual Origins.
- Tests: tracker state-machine tests, Blender 5.0 headless checks through
  the live handler, and a real-UI simulated-input driver (16 checks).

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
