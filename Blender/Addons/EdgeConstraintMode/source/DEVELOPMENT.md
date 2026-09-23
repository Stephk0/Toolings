# Edge Constraint Mode — developer notes

Implementation and maintenance notes. User docs: [README](../README.md).

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

## How it works

`EdgeConstraintSolver.apply_deltas(world_deltas)` is the only place that
touches topology. Every modal transform computes per-vertex world-space deltas
(translate = uniform drag, rotate = rotation about pivot, scale = radial from
pivot) and hands them to the solver, which picks the best-aligned incident
edge for each vert and walks along it. Future drivers (the multi-gizmo,
custom ops, curve mode) just need to produce world-space deltas — the solver
doesn't care where they came from.
