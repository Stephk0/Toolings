# Edge Constraint Mode

**Version:** 1.1.2 · **Blender:** 4.5+ · **Category:** Mesh

3ds Max-style **Edge Constraint** for Blender. When the mode is on, the
selection's Move / Rotate / Scale operations are projected onto each selected
vertex's incident edges — selected verts slide along the topology instead of
moving freely through space, while surrounding (unselected) geometry stays
in place.

> **Upgrading from v1.1.0 / v1.1.1?** Those versions could leave Blender's own tool gizmos
> hidden. v1.1.2 turns them back on in every 3D viewport when it loads.

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

---

[Developer notes](source/DEVELOPMENT.md)
