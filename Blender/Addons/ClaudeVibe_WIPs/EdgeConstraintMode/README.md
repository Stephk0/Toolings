# Edge Constraint Mode

3ds Max-style **Edge Constraint** for Blender. When the mode is on, the
selection's Move / Rotate / Scale operations are projected onto each selected
vertex's incident edges — selected verts slide along the topology instead of
moving freely through space, while surrounding (unselected) geometry stays
in place.

## Status

v1.1.2 — Mesh edit mode. Currently covers G / R / S keys only; the custom
gizmo group from v1.1.0–v1.1.1 was pulled because `GIZMO_GT_button_2d` in
3D space rendered as viewport-filling discs. A proper gizmo group built on
`GIZMO_GT_dial_3d` / `GIZMO_GT_arrow_3d` is queued for v1.2. The solver is
transform-agnostic so adding new drivers (gizmos, multi-gizmo, curve mode)
won't require core changes.

Upgrading from v1.1.0 / v1.1.1: this version force-restores
`space.show_gizmo_tool = True` on every 3D viewport at register so the
built-in tool gizmos return even if a prior version failed to restore them.

## Use

1. Enter **Mesh Edit mode** on a mesh.
2. Click the **edge-constraint toggle** in the 3D Viewport header (the
   `SNAP_EDGE` icon — it shows depressed while the mode is active).
3. Make a vert/edge/face selection.
4. Press **G**, **R**, or **S** as usual. Motion is projected onto each
   selected vertex's nearest incident edge. (Gizmo-click and menu-invoked
   transforms still bypass the mode — see Limitations.)
5. Confirm with **LMB / Enter**, cancel with **RMB / Esc**.
6. Click the header button again (or leave edit mode) to turn the mode off.

## How it works

`EdgeConstraintSolver.apply_deltas(world_deltas)` is the only place that
touches topology. Every modal transform computes per-vertex world-space deltas
(translate = uniform drag, rotate = rotation about pivot, scale = radial from
pivot) and hands them to the solver, which picks the best-aligned incident
edge for each vert and walks along it. Future drivers (the multi-gizmo,
custom ops, curve mode) just need to produce world-space deltas — the solver
doesn't care where they came from.

## Settings

- **Stop at Selected** *(scene)* — when a slide walks past an edge end, stop
  if the next vertex is also selected. Prevents selected verts from colliding
  when several slide toward the same neighbour.

## Limitations (v1)

- Mesh only. Curve edit mode is on the roadmap.
- Pivot is selection median; 3D-cursor / active-element pivots are not wired
  up yet.
- Gizmo-click and menu-invoked transforms (e.g. clicking the Move tool
  gizmo, or Mesh > Transform > Move) bypass the mode — only G / R / S
  keys route through it for now.
