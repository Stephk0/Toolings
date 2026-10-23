# Changelog — Geometry Constraint

Called **Edge Constraint Mode** up to 2.2.0. Releases before 2.2.0 did not
work reliably and are kept in `distribution/archive/` for reference only.

## 3.3.0 — 2026-10-23

- **New: Constraint Actions.** Edge / Face / Normal Constraint Action start
  Blender's own Move right away with that constraint, like Edge Slide.
  G / R / S inside it switch to Move / Rotate / Scale and all of them stay
  constrained until you confirm or cancel. The header toggle is left as it
  is; F9 on the result keeps the constraint. Three new unassigned hotkeys,
  also in the right-click Geometry Constraint submenu.

## 3.2.0 — 2026-10-21

- **New: hotkeys.** Toggle Edge / Face / Normal Constraint (switch to that
  type, or off if it's on), and two cycles: Off > Edge > Face > Normal, and
  Off > Edge > Face (along the surface). Unassigned by default; set keys in
  the add-on's Preferences, in Keymap > 3D View, or with right-click >
  Assign Shortcut. They only act in Mesh Edit mode.
- **New: right-click menu.** The Edit-mode context menu has a Geometry
  Constraint on/off entry and a submenu with every hotkey's button.
- The on/off toggle operator now only runs in Mesh Edit mode.

## 3.1.0 — 2026-10-20

- **Fixed:** shading broke while rotating or scaling with the constraint on,
  and stayed broken after confirming until the next edit. Normals are now
  recalculated after every snap.
- **Fixed:** a drag started right after another one could be projected
  from the first drag's starting positions, so the constraint seemed to use
  stale geometry. Blender doesn't always send an update after a confirm;
  the next drag now starts from the last result.
- **New: Even Slide** (Edge, on by default). Moving a selection slides every
  vertex of each connected piece the same distance along its own edge, like
  Edge Slide's Even mode, so an edge or loop keeps its size. A vertex whose
  edges are all off the drag direction now slides with the rest instead of
  staying behind. The whole piece stops at the shortest edge with Stop at
  Vertices.
- **Fixed:** a selected edge couldn't be moved along its own length; its own
  edge wasn't a rail. When you move, the ends of a selected edge or open
  chain now also slide along that edge, like Vertex Slide. Rotate and scale
  still keep to the edges leading out of the selection, so the edge doesn't
  collapse.
- **New: Show Constraint** (on by default): while transforming, the viewport
  draws the edges each vertex can slide along (bright for the ones in use),
  the Face surface, or the Normal lines.

## 3.0.0 — 2026-10-18

- **Renamed** from Edge Constraint Mode to **Geometry Constraint**: it
  constrains to edges, faces and normals. The extension id is now
  `geometry_constraint`, so Blender treats it as a new add-on: uninstall
  Edge Constraint Mode first. Renamed identifiers: `Scene.geometry_constraint`,
  `mesh.geometry_constraint_transform`, `view3d.geometry_constraint_toggle`,
  `view3d.geometry_constraint_set`. Settings saved in .blend files by the old
  add-on are not carried over.
- No behaviour change from 2.2.0.

## 2.2.0 — 2026-10-18 (Edge Constraint Mode, first working release)

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

## 2.1.0 — 2026-10-15 (Edge Constraint Mode, non-functional)

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

## 2.0.0 — 2026-10-15 (Edge Constraint Mode, non-functional)

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

## 1.1.2 (non-functional)

- Restores built-in tool gizmos hidden by 1.1.0 / 1.1.1. Custom gizmo group removed.

## 1.1.0 – 1.1.1 (non-functional)

- Persistent header toggle, transform-agnostic solver, experimental gizmo group.

## 1.0.x (non-functional)

- Initial single-operator releases.
