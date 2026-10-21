# Geometry Constraint — developer notes

Implementation and maintenance notes. User docs: [README](../README.md).

Called Edge Constraint Mode (id `edge_constraint_mode`, `Scene.edge_constraint_mode`)
up to 2.2.0; renamed in 3.0.0. Zips in `distribution/archive/` keep the old name.

## Layout (WMH split)

```
source/
├── __init__.py            # bl_info + register/unregister only
├── blender_manifest.toml
├── core/                  # bpy-free, pytest-covered
│   ├── vec.py             # tuple vector math, closest point on segment/triangle
│   ├── constraint.py      # MeshData + EdgeRails / FacePatch / NormalLine solvers
│   ├── transform.py       # free move/rotate/scale targets (Constrained Transform op)
│   └── live.py            # LiveTracker: which originals a native transform projects from
├── blender/
│   ├── properties.py      # Scene.geometry_constraint: enabled, mode, reach, stop_at_vertices, stop_at_selected, live, debug
│   ├── live.py            # depsgraph/undo handlers that constrain Blender's own transforms
│   ├── overlay.py         # Show Constraint: POST_VIEW draw of rails / patch / normals during a drag
│   ├── operators.py       # mesh.geometry_constraint_transform (own modal, F3/scripts), toggle/set ops
│   └── ui.py              # header toggle + type dropdown + settings popover
└── tests/
    ├── pytest.ini         # rootdir = tests/, so pytest never imports the bpy addon package
    ├── test_constraint.py # solver (no bpy)
    ├── test_live.py       # tracker state machine (no bpy)
    ├── meshes.py
    └── headless/
        ├── blender_checks.py  # Blender 5.0 headless: checks + comparison renders
        ├── gui_drive.py       # REAL Blender UI under Xvfb, simulated mouse/keys, screenshots
        └── demo_media.py      # demo video / GIF / stills (README, case study)
```

## How Live mode works (v2.1)

Goal: the constraint is a toggle, and *every* native transform is
constrained (keys in any keymap, tool gizmos, menus, F3, F9).

Blender has no API to hook into the transform system, so we post-process.
A `depsgraph_update_post` handler (`blender/live.py`) runs after each
update. During a modal transform, each mouse move makes the transform
rewrite the selected verts from its own stored originals (`td->iloc`) plus
the free delta. That update fires our handler, which snaps the verts back
onto the mesh *before the viewport draws*. The next mouse move rewrites the
free positions and we snap again. So there's no drift and no flicker: the
edit cage is extracted from the BMesh lazily at draw time.

On confirm, no recalc runs after our last snap, so **the undo step Blender
pushes already holds the constrained positions**. Verified in the GUI run:
Ctrl+Shift+Z restores the constrained result.

`core/live.py: LiveTracker` decides what to project from:

| Situation | Signal | Base |
|---|---|---|
| Interactive drag (any keymap, gizmo) | `Window.modal_operators` holds a `TRANSFORM_OT_*` | idle snapshot frozen at drag start |
| Drag confirmed | a new transform op appears in `wm.operators` | remembered as redo base |
| F9 / Adjust Last Operation | `undo_post`, then positions differ from the post-undo state, same op | redo base |
| Plain Ctrl+Z / Ctrl+Shift+Z | `undo_post`/`redo_post` and positions equal the post-undo state | nothing |
| Non-modal transform from the UI (menu exec) | new transform op, positions changed | idle snapshot |
| Extrude / duplicate macros | a `MESH_OT_*` macro is modal, or the topology/selection key changed | nothing |

Facts this relies on (see `Blender/Knowledge/bpy-api-gotchas.md`):

- `Window.modal_operators` exists in 4.2+. Without it (e.g. 4.0), the
  tracker falls back to a heuristic: selected verts moved but no new
  operator was registered. The heuristic also treats a selection change
  that no registered operator caused (a script editing the selection
  inside Edit mode) as a drag. That's harmless for users, whose selection
  clicks are operators, but test scripts must select before entering Edit
  mode.
- **Operators called from Python never enter `wm.operators`**, so other
  add-ons' scripted transforms are never constrained (by design). It also
  means headless tests must fake the "drag frame" (see `live_native()` in
  `blender_checks.py`).
- Rails and patches are built from the current BMesh, with the selected
  verts put back at their snapshot positions. Unselected verts don't move
  (unless proportional editing is on).
- The transform recalculates normals for its *free* positions before our
  handler runs. After snapping we must recalc the normals around the moved
  verts (`update_normals`), or the viewport shades the snapped mesh with
  stale normals until the next edit.
- Blender doesn't always fire a depsgraph update after confirming a drag.
  The next drag's first update then arrives with the tracker still "in
  session" but a newer registered op; `decide()` closes the old session
  there and starts from `written` (our last snap).
- Our `update_edit_mesh` re-fires the handler. A module-level `_busy` guard
  and an "unchanged result → no write" check stop the loop.

## Solver model (3ds Max Editable Poly "Constraints")

Autodesk: *Edge* "constrains sub-object transformations to edge boundaries"
(drag direction picks the edge); *Face* "to the individual face surfaces";
*Normal* "to its normal, or the average of its normals". Max doesn't
document rotate or scale; we apply the same rule to every transform: the
free target is snapped back, measured on the pre-transform mesh.

- `EdgeRails`: the displacement picks the incident edge with the largest
  positive `d·t`, in two tiers.
  1. Edges leaving the selection.
  2. In-selection edges. Used only if the vertex has no leaving edge, or if
     every leaving edge opposes the motion by more than `INTO_SELECTION`
     (25 %) of it. That covers two loops scaled toward each other.

  Sideways motion along a loop is rejected. Without this rule the "hinge"
  verts of a tilted cylinder or sphere loop slid along the loop
  (`test_tilting_a_round_loop_keeps_hinge_verts_in_place`). "Inside the
  selection" means Blender's own edge selection (`MeshData.selected_edges`,
  from `BMEdge.select`), not "both verts selected": in Edge/Face select mode
  the unselected rung between two selected edges must stay a rail. An
  in-selection edge is only ever a fallback rail where it continues a leaving
  edge through the vertex (dot < -cos 60°), i.e. the rung between two
  selected loops - never a loop's own edge
  (`test_scaling_two_selected_loops_slides_them_along_the_rungs`).
  Exception (3.1): under a pure move (`solve` finds one common offset,
  `moving=True`) a chain-end vertex - exactly one selected edge - treats
  that edge as tier 1, so a selected edge can be pushed along its own
  length like Vertex Slide
  (`test_edge_moved_along_itself_slides_along_its_own_line`). Not under
  rotate / scale, where it would collapse the edge
  (`test_scaled_edge_does_not_collapse_along_itself`). By default
  (`stop_at_vertices`, 2.2) overshoot stops at the edge's far vertex, so a
  loop can't pass through an unselected loop. With it off, overshoot walks
  on to the next edge only if it turns < 60°, up to `reach` edges, and
  stops at selected verts.
- **Even slide** (`solve(..., even=True)`, Edge only): if every free
  target has the same offset (a pure move), each island of selected verts
  (joined by selected edges) slides one shared distance, the mean of the
  per-vertex projections (least squares), each vertex along its own picked
  edge. Verts with no edge along the drag take the leaving edge closest to
  the island's mean rail direction (`side_rail`), like Edge Slide's side.
  With `stop_at_vertices` the distance is clamped to the island's shortest
  rail. Rotate/scale never qualify, so per-vertex projection stays.
- `FacePatch`: the closest point on the original surface, meaning **all**
  faces (selected ones too, at their pre-transform positions) within
  `reach` rings. v2.0 excluded the selection's own faces, which stranded the
  trailing verts of a moved patch
  (`test_face_constraint_moves_a_patch_as_a_whole`).
- `NormalLine`: projection onto the pre-transform vertex normal,
  angle-weighted like Blender's.

All solving is in world space, so object scale and rotation don't skew it.

## Constrained Transform operator

`mesh.geometry_constraint_transform` (F3 "Constrained Transform") is the v2.0
self-contained modal with its own G/R/S math (axis locks, numeric input,
Ctrl snap). It is no longer bound to keys, because native transforms are
constrained live now. It stays for scripting: Python callers can request a
constraint explicitly with `use_scene_constraint=False, constraint='EDGE'`.
The live handler ignores it (it isn't a `TRANSFORM_OT_*`).

## Tests

```bash
# core (plain CPython 3.11+, no Blender)
cd source/tests && python -m pytest -q

# Blender 5.0 headless: checks + comparison renders into <out_dir>
mkdir -p /tmp/ecm && ln -s "$PWD/source" /tmp/ecm/GeometryConstraint
blender --background --factory-startup --python source/tests/headless/blender_checks.py -- /tmp/ecm <out_dir>
#   or with the PyPI wheel: pip install bpy==5.0.0 && python source/tests/headless/blender_checks.py /tmp/ecm <out_dir>

# REAL UI, simulated input (needs Xvfb, xwd, ImageMagick):
Xvfb :99 -screen 0 1600x1000x24 &
DISPLAY=:99 blender --factory-startup --enable-event-simulate \
    --python source/tests/headless/gui_drive.py -- /tmp/ecm <out_dir>

# Demo media, 1920x1080 Workbench (15 segments, ~810 frames, Edge rails drawn as yellow tubes; add `preview`
# after <frames_dir> for one frame per segment). Step 2 needs PIL.
blender -b --factory-startup --python source/tests/headless/demo_media.py -- render /tmp/ecm <frames_dir>
python source/tests/headless/demo_media.py <frames_dir> <out_dir>   # captioned/, stills/, GIF
blender -b --factory-startup --python source/tests/headless/demo_media.py -- encode <out_dir>/captioned <out_dir>/geometry_constraint_demo.mp4
```

On Windows, `gui_drive.py` runs as is apart from `capture()`, which shells
out to `xwd`; stub it to skip screenshots (last run 2026-10-18, Blender 5.0,
all 18 checks pass).

What each layer covers:

- `blender_checks.py` (5.0) runs **native** `bpy.ops.transform.*` through
  the live handler, with `transform_running` forced True for one update to
  stand in for a modal drag frame. It covers rotate, move, scale, Face,
  toggle off, a transformed object, and the scripted operator. It also
  renders `geometry_constraint_{move,rotate,scale}.png`.
- Pivot points need no add-on code. Blender's transform computes the free
  result around the pivot, and we project it. `blender_checks.py` section 7
  checks exact positions for 3D cursor (rotate + asymmetric scale), Active
  Element, Individual Origins (two islands), Bounding Box Center, and the
  F3 operator with a cursor pivot. **Trap:** without a VIEW_3D context, a
  background `bpy.ops.transform.*` ignores the pivot setting and acts as if
  the pivot were the median. `in_view3d()` runs the ops inside the startup
  layout's 3D View.
- `gui_drive.py` presses real keys in a real UI. Last run on Blender 4.0.2
  from apt, the only GUI build reachable from the dev container; 4.0
  exercises the heuristic fallback. 18 checks: R-key shear (live and
  confirmed), R about a 3D cursor beside the cube, Individual Origins with
  two loops, Ctrl+Z / Ctrl+Shift+Z keep the constrained result,
  Move-gizmo free drag, S on a frustum, toggle off, cylinder, UV sphere,
  terrain (Face), icosphere (Normal), and extrude staying free. The
  screenshots become the README's `live_*.png` pairs. Simulation traps are
  in `Blender/Knowledge/headless-and-automation.md`.

**Not yet driven in a real 5.0 UI.** The `Window.modal_operators` path is
covered by unit tests plus the 5.0 headless run, not by a live 5.0 drag.

## Roadmap

- Curve edit mode.
- Optional constraint for proportional-editing falloff verts.
- Optional constraint for macros (extrude + move) when the user wants it.
