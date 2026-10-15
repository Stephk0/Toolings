# Edge Constraint Mode — developer notes

Implementation and maintenance notes. User docs: [README](../README.md).

## Layout (WMH split)

```
source/
├── __init__.py            # bl_info + register/unregister only
├── blender_manifest.toml
├── core/                  # bpy-free, pytest-covered
│   ├── vec.py             # tuple vector math, closest point on segment/triangle
│   ├── constraint.py      # MeshData + EdgeRails / FacePatch / NormalLine solvers
│   └── transform.py       # free move/rotate/scale targets, pivots, axis masks
├── blender/
│   ├── properties.py      # Scene.edge_constraint_mode (mode, reach, stop_at_selected, debug)
│   ├── operators.py       # mesh.edge_constraint_transform (modal + execute), mode ops
│   ├── ui.py              # header buttons + settings popover
│   └── keymaps.py         # G / R / S in the 'Mesh' keymap
└── tests/
    ├── test_constraint.py # pytest, no bpy
    ├── meshes.py          # plain-data cube/loop builders
    └── headless/blender_checks.py   # runs inside Blender: checks + comparison renders
```

## Model (3ds Max Editable Poly "Constraints")

Autodesk's docs: *Edge* "constrains sub-object transformations to edge
boundaries" (drag direction picks the edge), *Face* "to the individual face
surfaces", *Normal* "to its normal, or the average of its normals". Max
does not document rotate/scale behaviour; we apply the same rule to every
transform:

1. `core/transform.py` computes each selected vertex's **free target**
   (world space).
2. `core/constraint.py` maps target → constrained position, measured on the
   **original** mesh snapshot taken at invoke:
   - `EdgeRails`: displacement picks the incident edge with the largest
     positive `d·t` (edges whose both verts are selected score ×0.5, so the
     crossing edge wins for a selected loop). Move by the projected length.
     Overshoot walks to the next edge only if it turns < 60°
     (`TURN_LIMIT_COS`), up to `reach` edges, stopping at selected verts.
   - `FacePatch`: closest point on the triangulated faces around the vertex,
     grown `reach` rings; does not grow across selected edges.
   - `NormalLine`: projection onto the vertex normal.
3. The Blender layer converts to world space before solving (so object
   scale/rotation don't skew the projection) and back to local to write.

This is why a rotated cube loop shears: each vertex's displacement is
projected onto its vertical edge, so it changes height only.

v1.x bugs fixed by this model: it used `|d·t|` and moved *backwards* off the
end of an edge, and it gave the loop's own edges equal weight with the
crossing ones.

## Keymap fall-through

`keymaps.py` binds G/R/S once at register. `poll()` fails while the mode is
`NONE`, so the event falls through to Blender's own transform; there's no
install/uninstall on toggle.

## Modal notes

- The BMesh is re-resolved from the object *name* on every write (see
  `Blender/Knowledge/bpy-api-gotchas.md`, BMesh invalidated by undo push).
- The modal writes its result into the operator properties (`value`,
  `angle`/`axis`, `scale`, `orient_matrix`), so `execute()` replays it for
  Redo / F9 and for scripted use.
- Rotation angle is unwrapped per mouse event; scale ratio uses the 60 px
  softening from the knowledge page.

## Tests

```bash
# core (plain CPython 3.11+, no Blender)
cd source && python -m pytest tests -q

# inside Blender 5.0: integration checks + renders into <out_dir>
mkdir -p /tmp/ecm && ln -s "$PWD" /tmp/ecm/EdgeConstraintMode
blender --background --factory-startup --python tests/headless/blender_checks.py -- /tmp/ecm <out_dir>
# or with the PyPI wheel: pip install bpy==5.0.0 && python tests/headless/blender_checks.py /tmp/ecm <out_dir>
```

`blender_checks.py` asserts the acceptance case (rotate a cube's loop 30° →
every vert stays on its original cube planes, loop z = −x·sin 30°), plus
move, uniform scale of two loops, Face rotate, mode None → poll fails, and a
rotated/non-uniformly scaled object. It renders
`edge_constraint_{move,rotate,scale}.png` (native vs constrained), which are
the README images in `../assets/`.

The interactive mouse mapping (`_compute`) can't run headless. It was
exercised with a stand-in region/RegionView3D, but it has not been driven in
a live viewport yet.

## Roadmap

- Route the toolbar Move/Rotate/Scale gizmos through the solver.
- Curve edit mode.
- Proportional editing falloff on top of the constraint.
