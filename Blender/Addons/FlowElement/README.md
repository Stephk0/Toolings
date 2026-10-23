# Flow Element

**Version:** 1.0.0 · **Blender:** 4.5+ (built for 5.0) · **Category:** Mesh

3ds Max **Edge Flow** and **Vertex Flow** for Blender, plus the same for faces. Flow Element
reads the curvature of the geometry around your selection and rebuilds it. It does not
average positions like Relax/Smooth; it puts the curve back.

- Flattened or dented a ring on a cylinder? Select the edge loop, run Flow Element, and it
  is round again, because the rings around it still are.
- A vertex pushed in on an organic shape pops back onto the surface the neighbouring edge
  lines describe.
- A patch of faces that was flattened (or scaled to 0 along its normal) is rebuilt from the
  curvature of the surface around it.

## Installation

1. Grab `distribution/FlowElement_v1.0.0.zip`
2. Drag the zip into the Blender window (or `Edit > Preferences > Add-ons > Install from Disk...`)
3. Enable **Flow Element**

## Usage

Edit Mode, select, then run **Flow Element** from:

- the right-click menu (follows the select mode), or
- **Vertex**, **Edge** or **Face** menu in the header (runs in that mode).

No default hotkey: right-click the menu entry → *Add to Quick Favorites* or *Assign Shortcut*.

| Mode | Select | What moves | Curvature comes from |
|------|--------|-----------|----------------------|
| **Edge** | One or more edge loops (or parts of loops) | The loop vertices | The edges crossing the loop, on both sides |
| **Vertex** | Vertices | The selected vertices | Every edge line running through each vertex |
| **Face** | Faces | All vertices of the faces | The surface around the selection, read along every edge line |
| **Auto** | — | Follows the select mode: face, then edge, then vertex | |

Each vertex keeps its place along the edge lines through it. It only moves across them, so
loops do not slide or bunch up.

### Settings (redo panel, F9)

| Setting | Default | What it does |
|---------|---------|--------------|
| **Mode** | Auto | See the table above |
| **Tension** | 1.0 | 1 matches the surrounding curvature. 0 makes the lines straight (linear). Above 1 overshoots, below 0 bends the other way |
| **Mix** | 1.0 | Blend between the original and the flowed position |
| **Refine Passes** | 4 | Re-reads the curves at the corrected positions. Raise it for very distorted or large selections |
| **Debug Log** | off | Prints counts and timing to the system console |

## Tips and limits

- The geometry around the selection is the reference. Leave at least one, ideally two,
  undamaged rows of edges on each side of what you want to fix.
- Several adjacent loops or a big face patch work in one go; the curve is read from the
  first undamaged rows on both sides.
- A vertex on an open mesh border, or a line that never leaves the selection (a whole
  selected ring in Vertex mode), has nothing to read along that line. Those lines are
  ignored, and a vertex with no usable line stays where it is. The report says how many.
- Works on quads best. Poles, triangles and n-gons fall back to the straightest edges
  through the vertex.
- If the older `flow_element_stable.py` add-on is still enabled, you will see two
  *Flow Element* entries. Disable the old one.

Developer notes: [source/DEVELOPMENT.md](source/DEVELOPMENT.md) · Changes:
[source/CHANGELOG.md](source/CHANGELOG.md)
