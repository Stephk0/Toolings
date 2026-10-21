# Geonode nodes, fields and domains

Node behaviour that differs from what the UI suggests. Verified on Blender 5.0.

- [Field on Domain's domain is the SOURCE domain](#feedback_gn_field_on_domain_is_source)
- [Edge→face boolean interpolation and face groups](#feedback_gn_edge_to_face_bool_interp)
- [Blur Attribute is a no-op on CORNER](#feedback_gn_blur_attribute_corner_noop)
- [Single-input Mesh Boolean UNION is a passthrough](#feedback_gn_mesh_boolean_selfunion)
- [Vertex data channels FBX actually carries](#feedback_gn_vertex_data_channels)
- [For-Each preview streams and tube noise](#feedback_gn_foreach_gen_preview_and_tube_noise)
- [A material index is local to the geometry it sits on](#gn_material_index_is_local)
- [Node properties that became Menu sockets](#gn_property_became_menu_socket)
- [Face-domain Delete Geometry strips loose elements](#gn_delete_face_domain_strips_loose)
- [Small node facts](#gn_small_node_facts)

<a id="feedback_gn_field_on_domain_is_source"></a>

## Field on Domain's domain is the SOURCE domain

*`GeometryNodeFieldOnDomain.domain` is where the INPUT field is evaluated, not the target — setting it to the consumer's domain silently averages the wrong thing*

To turn an edge field into a per-vertex flag, set `domain='EDGE'` and let the POINT consumer
average it — not `domain='POINT'`.

**Why:** GN_QuadCap used `domain='POINT'` on `EdgeNeighbors.Face Count == 1`, so Face Count was
averaged per vertex: 3-edge verts (1,1,2 → 1) passed, 4-edge hole corners (→ 2) failed. The demo
tubes passed; a square hole in a grid exposed it.

**How to apply:** when a check "works on the demo", add a case with different vertex valence
(grid hole corners = 4 edges, tube rims = 3). Don't test grid membership with a float
`Compare EQUAL` epsilon on u/v — use integer i/j.

<a id="feedback_gn_edge_to_face_bool_interp"></a>

## Edge→face boolean interpolation and face groups

*A BOOLEAN attribute interpolated edge→face is AND-ed; materialise it as FLOAT for "any". For "faces enclosed by marked edges" use the native Edges to Face Groups node*

Domain interpolation honours the attribute's **stored** type: a bool edge attr read on FACE is true
only if all edges are true. Reading it via `Named Attribute (FLOAT)` does not help.

**How to apply:**
- **"Any bordering edge":** `Capture Attribute(EDGE, FLOAT)` of the marker → `Evaluate on Domain
  (FACE, FLOAT)` (averages) → `> 0`.
- **"Faces enclosed by a loop" — don't hand-roll a flood fill.** `Edges to Face Groups(Boundary
  Edges = marked)` → `Face Group ID`; `size = Accumulate Field(1.0, Group ID, FACE).Total`;
  `Max/Min = Attribute Statistic(size)`, `N` = face count;
  `Inside = (Max < N) AND ((size < Max) OR (Max == Min))` — excludes the largest (background)
  group, selects nothing when there are no marks, everything when all groups are equal.
- **Repeat Zone items don't carry per-element field state** (a per-face BOOLEAN item went
  uniform). Carry Geometry and store the state as a named attribute each iteration.
- **Field/value links CAN cross a Repeat Zone boundary** — only Geometry must be an item.
- **Remove temp attributes** with `GeometryNodeRemoveAttribute` before the output or they leak/export.
- Faces sharing an edge can't be detached without `SplitEdges(selection=marked)`.
- An active Viewer node locks the viewport to its tap point — deactivate it to see the result.
- When a user's result is wrong, check their data first (typo'd attribute name, open loop) and
  ground-truth with a bmesh flood fill.

<a id="feedback_gn_blur_attribute_corner_noop"></a>

## Blur Attribute is a no-op on CORNER

*`GeometryNodeBlurAttribute` silently does nothing on the FACE CORNER domain — pin it to POINT with Field on Domain*

The corner domain has no neighbour topology; no error, the slider just does nothing (measured on
GN_AmbientOcclusion: CORNER stdev 0.122 at 0/1/3/10 iterations; POINT 0.125 → 0.019).

**How to apply:** wrap the blur in `FieldOnDomain(FLOAT, domain='POINT')` before a CORNER store.
Same for any neighbour-walking field. Assert the *effect* in the verifier (stdev drops), not just
that the socket is linked.

<a id="feedback_gn_mesh_boolean_selfunion"></a>

## Single-input Mesh Boolean UNION is a passthrough

*Mesh Boolean UNION with one multi-island mesh does not self-union; a self-intersecting DIFFERENCE already merges overlapping cutters*

- One mesh into UNION: FLOAT/MANIFOLD leave it unchanged, EXACT only splits intersecting faces.
  A real union needs ≥2 separate inputs on the multi-input socket.
- DIFFERENCE with `Self Intersection = True` subtracts overlapping cutters as their union — don't
  pre-union them.

**How to apply:** union pieces as separate inputs, or iterate islands in a For-Each zone.
Naming: `ShaderNodeTexNoise` output is **"Factor"**, not "Fac".

<a id="feedback_gn_vertex_data_channels"></a>

## Vertex data channels FBX actually carries

*FBX facts and big-interface patterns from GN_VertexDataComposer (528 sockets)*

- FBX exports ALL `color_attributes` and ALL `uv_layers` (Blender 5.0 `export_fbx_bin.py`), not
  arbitrary named float attributes (glTF/USD/Alembic only). UVs are the precise pipe (float ×2,
  8 sets), vertex colour the 8-bit pipe; Unreal reads only the first colour attribute.
- **`InputNamedAttribute` can't be set to `FLOAT2`** (`bl_rna` lists 13 types, assignment accepts
  7). Read a UV map as `FLOAT_VECTOR`, write with `Store Named Attribute` `FLOAT2`/CORNER. Always
  test enum assignment; never trust `enum_items`.
- **A huge interface is cheap** (528 sockets / 45 panels: build 0.06 s, eval 1 ms). Worry about
  node count instead.
- **A menu inside a helper group propagates its enum outward** to every linked outer socket — one
  definition instead of N × items links when N channels share a dropdown.
- **`Switch(GEOMETRY)` is lazy — use it as a cost gate** for Attribute Statistic / Raycast /
  Proximity (32 gated statistics added 2 ms on 90k verts). `IndexSwitch` with FIELD inputs is NOT
  lazy — cache expensive sources once into internal named attributes, then remove them.
- Blender 5 `GeometryNodeRaycast` has no `mapping`/`data_type` property (`Interpolation` is a menu
  socket); `GeometryNodeProximity` inputs are `Target / Group ID / Source Position / Sample Group ID`.
- **Test harness:** a "reset then apply kwargs" helper must reset EVERY parameter — leaked
  `Invert`/`Encode sRGB` produced five bogus failures.

<a id="feedback_gn_foreach_gen_preview_and_tube_noise"></a>

## For-Each preview streams and tube noise

*Preview geometry made inside a For-Each loop via one generation item per stream; noise on a tube drives RADIUS, not position*

**How to apply:**
- Geometry created inside `For Each Geometry Element` reaches the outside only through a
  **generation item** on the For-Each Output. One `generation_items.new('GEOMETRY', name)` per
  stream; outside, chain `Switch(Show_X, prev, Join(prev, stream_X))` so all-off is
  byte-identical. Renaming a gen item is safe (links bind by identity). Check for an existing debug
  gen item before adding one.
- **Noise on a swept tube: modulate `Set Curve Radius`** (Noise Factor → Map Range), not
  `Set Position` (the tube wanders off the edge). Parallel copies: offset by
  `normalize(cross(Tangent, Normal)) * spacing` via `Duplicate Elements(SPLINE)`. Expose noise
  Detail/Roughness/Distortion, not just Scale.

<a id="gn_material_index_is_local"></a>

## A material index is local to the geometry it sits on

*Set Material Index on freshly generated geometry is not "the object's slot N" — Join Geometry remaps it; an empty Material socket on Set Material is not "leave it alone"*

Generated geometry starts with an empty slot list, so an index set before a `Join Geometry` gets
remapped onto a new empty slot (GN_QuadCap: index 1 came out 0, and -1/0 came out 2).

**How to apply:**
- Set material indices **after** the join, selecting generated faces by a captured FACE bool
  (survives Join and Merge by Distance).
- `Set Material` with an empty socket appends an empty slot and assigns it — gate optional
  materials with a toggle (`Use Cap Material`).
- Order: `Set Material Index` first, `Set Material` second, so an explicit material wins.
- Evaluated `material_index` is clamped to the object's slot count — give a test mesh enough
  material slots or index checks read the clamp.

<a id="gn_property_became_menu_socket"></a>

## Node properties that became Menu sockets

*Blender 5 turned several node properties into Menu input sockets — scripts written for 4.x set a property that no longer exists*

| Node | Now a menu input | Notes |
|---|---|---|
| Merge by Distance | `Mode` (All / Connected) | inputs Geometry, Selection, Mode, Distance; no `.mode` property |
| Voxel Remesh | `Resolution Mode` | |
| Triangulate | `Quad Method` | e.g. `"Fixed"` / `"Fixed Alternate"` |
| Weld | `Mode` | |
| Raycast | `Interpolation` | see [vertex data channels](#feedback_gn_vertex_data_channels) |

Set them as input values: `node.inputs["Mode"].default_value = "Connected"`.

**How to apply:** before scripting a node from 4.x memory, add it to a throwaway group and print
`[p.identifier for p in node.bl_rna.properties]` and
`[(s.identifier, s.name, s.type) for s in node.inputs]`.

<a id="gn_delete_face_domain_strips_loose"></a>

## Face-domain Delete Geometry strips loose elements

*`DeleteGeometry` on FACE (mode ALL or ONLY_FACE) removes every face-less vert and edge regardless of its Selection — even an all-False one*

Muting the node changed 62 → 57 verts on a mesh with loose parts, so an "all passes off" state
was not identity and a face pass was coupled to the loose-vert/edge toggles. POINT/ALL and
EDGE/EDGE_FACE are strip-safe.

**How to apply:** delete faces from the POINT domain. A FACE bool read in a POINT context
averages over the vertex's faces, so "all adjacent faces flagged" = avg `> 0.999`, AND
`VertexNeighbors.Face Count > 0` to spare standalone verts. Deleting any vert of a face removes
it. Order cleanup passes islands → faces → edges (EDGE_FACE keeps verts) → loose verts.

<a id="gn_small_node_facts"></a>

## Small node facts

*Socket names and behaviours that cost a debugging round each*

**How to apply:**
- `FunctionNodeBooleanMath` output is **"Boolean"**, not "Result".
- `ShaderNodeVectorMath` has no component-wise LESS_THAN/GREATER_THAN — per-axis `Compare` +
  `Math MULTIPLY_ADD(b, -2, 1)` + `CombineXYZ`.
- `FunctionNodeHashValue` (INT) outputs a full-range int — normalise via `floored_mod 65536 / 65536`.
- `DualMesh` propagates POINT named attributes to the FACE domain; `SubdivideMesh` propagates
  face attributes to the children.
- Boundary vertex on POINT natively: `VertexNeighbors.Face Count < Vertex Count` (an edge field
  captured on POINT reads 0).
- Triangulate `Fixed Alternate` is the other diagonal uniformly, not per-face alternation — a
  checkerboard needs two selective Triangulate passes.
- An existing NODES modifier keeps the input values it captured — interface `default_value`
  changes reach only newly added modifiers.

