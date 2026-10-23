# Changelog — Flow Element

## 1.0.0 — 2026-10-23

- **New:** Flow Element: 3ds Max Edge Flow / Vertex Flow for Blender, plus face mode. It
  rebuilds lost curvature of edge loops, vertices and face patches from the surrounding
  geometry. It is exact on cylinders and spheres, works on several adjacent loops and on
  large flattened patches in one go, and keeps vertices from sliding along their lines.
  Tension, Mix and Refine Passes are in the redo panel. Find it in the right-click menu and
  the Vertex / Edge / Face menus.
- Replaces the old `flow_element_stable.py` add-on, which is not carried over.
