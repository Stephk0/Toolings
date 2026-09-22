# Geonode nodes, fields and domains

Node behaviour that differs from what the UI suggests.

> Migrated verbatim from Claude auto-memory on 2026-09-22. Dates and version numbers are from when each note was written — trust the code when they disagree.

- [Field on Domain's domain is the SOURCE domain](#feedback_gn_field_on_domain_is_source)
- [Edge→face boolean interpolation and loop flood-fill](#feedback_gn_edge_to_face_bool_interp)
- [Blur Attribute is a no-op on CORNER](#feedback_gn_blur_attribute_corner_noop)
- [Single-input Mesh Boolean UNION is a passthrough](#feedback_gn_mesh_boolean_selfunion)
- [Vertex data channels FBX actually carries](#feedback_gn_vertex_data_channels)
- [For-Each preview streams and tube noise](#feedback_gn_foreach_gen_preview_and_tube_noise)

<a id="feedback_gn_field_on_domain_is_source"></a>

## Field on Domain's domain is the SOURCE domain

*GN Field on Domain's `domain` is where the INPUT field is evaluated (source), not the target — setting it to the consumer's domain silently averages the wrong thing*

`GeometryNodeFieldOnDomain.domain` = the domain the input field is EVALUATED on; the result is then adapted to whatever context reads it. To turn an edge field into a per-vertex flag, set `domain='EDGE'` and let the POINT-domain consumer (Store/Compare) average it — NOT `domain='POINT'`.

**Why:** GN_QuadCap (2026-09-21) shipped `domain='POINT'` on a border-edge flag (`EdgeNeighbors.Face Count == 1`). That evaluated Face Count per VERTEX (int average → rounded), so vertices with 3 edges (1,1,2 → 1) passed and hole corners with 4 edges (1,1,2,2 → 1.5 → 2) failed. The demo tubes happened to pass; only a square hole in a grid exposed it (4 of 8 rim verts never welded).

**How to apply:** when a check "works on the demo", add a case with different vertex valence (grid hole corners = 4 edges, tube rims = 3). Related gotcha from the same build: a float `Compare EQUAL` epsilon of 0.25 on grid u/v in [0,1] lumps the next ring into the rim once the grid has ≥4 segments — test rim membership on integer i/j instead. See [ST3E geonode modifier — build recipe, roster, publish checklist](asset-checklist.md).

<a id="feedback_gn_edge_to_face_bool_interp"></a>

## Edge→face boolean interpolation and loop flood-fill

*Blender GN edge→face: bool interp = AND (materialize FLOAT to fix); plus flood-fill region-inside-a-loop recipe + Repeat-Zone per-element-state gotcha*

When converting an **edge selection to a face selection** in Geometry Nodes ("select every face that borders a marked edge"), the obvious route — read the edge attribute and `Evaluate on Domain (FACE)` — **only works if the source attribute is FLOAT or INT**. A **BOOLEAN** edge attribute interpolated edge→face uses **AND** semantics: the face comes out true only when *all* of its edges are true. Verified live in Blender 5.0 (2026-06-02): a 2×2 grid with 1 of a face's 4 edges marked selected nothing; marking all edges selected everything; the same test with a FLOAT/INT attribute selected correctly.

**Why:** domain interpolation honours the attribute's *stored* type, not the read type. Reading a bool attr with `Named Attribute (data_type=FLOAT)` does NOT help — the edge→face shrink still runs as boolean AND, then converts.

**How to apply — force OR-semantics ("any bordering edge"):** materialize the marker as a real FLOAT on the edge domain *before* the face interpolation, then threshold > 0:
1. `Named Attribute (FLOAT)` reads the user's edge attr → per-edge 1.0/0.0 (bool True→1.0).
2. Feed it into a `Capture Attribute` node set to **domain=EDGE, FLOAT** (sits on the main geometry path) → its anonymous Attribute output is now a genuine float edge attribute.
3. `Evaluate on Domain (FACE, FLOAT)` of that capture output → averages the face's edge values (e.g. 1 of 4 marked = 0.25).
4. `Compare GREATER_THAN, B=0.0` → true = face borders ≥1 marked edge.

The float-materialization above is the building block for **edge→face transfers**, but "any bordering edge" was the WRONG semantics for `GN_ExtrudeFace`'s `Select by Edge Group` mode. The user wants **containment**: edges form a closed *border loop* and only the faces *enclosed* by it are extruded ("faces-between-edge selection"). "Any bordering edge" over-selects — it grabs the faces on BOTH sides of every wall edge.

**Containment = flood-fill (region inside a closed edge loop), implemented in helper group `EGF Region From Borders` (in `GN_ExtrudeSelection.blend`):**
- Inputs: Geometry, `Blocked` (edge bool = wall, here `NamedAttribute(EdgeGroupAttr,FLOAT) > 0`), `Iterations` (int, default 256). Output: Geometry + `Inside` (face bool).
- Seed `outside` = faces touching a **naked** edge (`Edge Neighbors → Face Count < 2`) that is **not** Blocked → materialize that edge bool to FLOAT (Capture EDGE) → `Evaluate on Domain(FACE) > 0`.
- Repeat zone floods `outside` inward across non-blocked edges; `inside = NOT outside` = the enclosed region. All cross-domain steps use the FLOAT-materialize trick above (both face→edge and edge→face).
- Verified Blender 5 (2026-06-02): loop around 2 faces → exactly those 2; closed loop around 1 → that 1; all edges marked → every face (each is its own walled cell); open/incomplete loop → nothing (outside leaks in — by design, loop must be closed).

**Two hard gotchas this exposed:**
1. **Repeat Zone non-geometry field items don't carry per-element state.** Feeding a per-face boolean into a Repeat `BOOLEAN` item collapsed it (whole mesh went uniform). FIX: carry only Geometry through the zone and persist per-face state as a **named attribute** stored on that geometry (`Store Named Attribute` in the body, read back with `Named Attribute` each iteration).
2. **Named temp attrs leak onto the output mesh.** `GeometryNodeRemoveAttribute` exists in Blender 5 (inputs Geometry/Pattern Mode/Name) — capture the final result into an anonymous attr, then RemoveAttribute the temp name before the group output. Result: zero leftover attributes (verified).

In `GN_ExtrudeFace` the mode is gated by a **geometry `Switch`** on `Select by Edge Group` (lazy → the flood-fill only runs when the mode is on), and `Inside` feeds the existing additive-OR selection chain alongside `Selection`/`Material Index`. Sockets: `Select by Edge Group` (bool), `Edge Group Attribute` (string). The earlier "any bordering edge" build (the `edge_grp_border` capture item) was removed.

**Iterations must NOT be user-facing (footgun).** It was first exposed as `Edge Group Fill Iterations` and a user left it at 0 → the flood-fill never ran → "outside" stayed as just the boundary rim → almost the whole mesh read as "inside" and extruded (looked like a giant blob). FIX (2026-06-02, verified live via [Headless Blender and automation](../headless-and-automation.md#reference_blender_mcp)): removed the socket and drive iterations internally from `Attribute Domain Size` (MESH → Face Count) → `Math Minimum` cap 1024 → `region.Iterations`. Face count is a safe upper bound on flood distance; the 1024 cap prevents a freeze on huge meshes (a real loop is never that deep). It now "just works", no knob.

**FINAL algorithm (2026-06-02) — use the NATIVE `Edges to Face Groups` node; do NOT hand-roll a flood fill.** The user discovered Blender 5's `GeometryNodeEdgesToFaceGroups` (input `Boundary Edges` bool, output `Face Group ID` int) which natively partitions faces into connected islands separated by the boundary (marked) edges — exactly the components I was painfully approximating with corner-seed floods. They (rightly) told me to scrap the custom `EGF Region From Borders` group AND the `SplitEdges` separation: "we get the faces from the edges to face group node more easily and it's native." The clean selection:
- `Edges to Face Groups(Boundary Edges = marked-edge bool)` → `Face Group ID` per face (handles interior loops AND boundary-edge pockets natively — the mesh's open boundary is NOT a separator, only the marked edges are).
- `group_size` = `Accumulate Field`(Value=1.0, Group ID = Face Group ID, domain FACE).**Total**.
- `Attribute Statistic`(group_size, FACE) → **Max**, **Min**; `N` = `Attribute Domain Size`(MESH).Face Count.
- `Inside = (Max < N)  AND  ( (group_size < Max)  OR  (Max == Min) )`.
  - `Max < N` ⇒ more than one group (else 1 group = whole mesh = no enclosed pockets ⇒ select NOTHING — the important no-marks/open-path case).
  - `group_size < Max` ⇒ keep every group except the largest (= the background). This is "exclude background"; works for any number of pockets, interior or boundary.
  - `Max == Min` (with >1 group) ⇒ all groups equal size ⇒ all-edges-style ⇒ select all.
- Verified live + headless Blender 5: `Edge_Group`(closed loop)→[46,50]; `Edge_Group_Test`(loop + boundary-closed loop)→[3,17,18,52]; no-marks→nothing; loop-2→2; all-edges→all 4; gate-off & Selection/Material modes intact. Much smaller, native, editable. Nodes live under frame "Face-group select …" feeding `Switch Edge Group.True`; geometry path restored straight through (no gate/region/split).

**Per-group extrude wrapped in an outer Repeat Zone (2026-06-02, user's chosen design).** The user wanted each face group extruded "one by one" with ALL the existing extrude features intact, and proposed iterating the face-group IDs in a repeat. Implemented: store `egf_gid`(INT)=Face Group ID and `egf_ext`(BOOL)=Inside once on the geometry; wrap the ENTIRE extrude body (`GN_GrowSelection.001` → … → `Switch.008`, including the existing inner divisions Repeat Zone — nested repeats are fine) in a NEW outer Repeat Zone `EGF Outer Repeat In/Out`; iterations = `Select by Edge Group ? max(egf_gid)+1 : 1`; inside, the selection feeding `Evaluate on Domain → GN_GrowSelection.001.Selection` = `Switch(Select by Edge Group, true = (egf_gid==Iteration AND egf_ext), false = Boolean Math.001 [the old Selection-OR-Material combined])`. Removed old `Boolean Math.005`/`Switch Edge Group`. KEY ENABLER: **field/value links CAN cross a Repeat Zone boundary** (verified) — only Geometry must be a repeat item, so all ~30 params (Height/crease/etc.) just connect straight through; no per-param items needed. Edge-OFF ⇒ iterations=1 ⇒ byte-identical to before (verified: Selection→17/12, Material→13/8, no-marks→9/4). Edge-ON ⇒ each group extruded in its own iteration; new faces inherit `egf_gid` so a group is never re-extruded in a later iteration.

**BUT the repeat does NOT topologically separate adjacent groups.** Verified live + headless: two pockets sharing a marked edge → each gets its own walls/top (a dividing wall between them, NOT a merged flat top — an improvement over single-pass), yet they stay CONNECTED AT THE BASE (the shared marked edge at z=0) → still 1 island (16 raised faces on the real mesh, z→0.72). This is a geometric fact: you cannot detach two faces that share an edge without splitting that edge. So full detachment STILL needs a `SplitEdges(selection=marked)`. Current state: repeat gives distinct-blocks-rooted-to-ground; add one SplitEdges for fully-detached islands. Also noted: per-group path yields a slightly different face count than single-pass for the "Outer Faces" feature on a lone pocket (loop-2: 31/22 vs 33/24) — minor, uninvestigated. Viewport gotcha: the user's active Viewer node locks the viewport to its tap point (looks flat / shows Face Group IDs) even in object mode — deactivate it to see the extrusion.

When a user's result is wrong, FIRST check their data via MCP: (a) the modifier's `Edge Group Attribute` may point at the wrong/typo'd attribute (cases seen: `Edge_Group_Test` typed without the dot vs the real `Edge_Group._Test`; pointing at an open stub vs the closed loop); (b) inspect the marked-edge subgraph in bmesh (degrees, endpoints, whether endpoints lie on the mesh boundary). Ground-truth the expected faces with a pure-Python bmesh flood fill (walls=marked, seed=corner faces or boundary) before trusting the node.

Related: [Headless Blender and automation](../headless-and-automation.md#feedback_blender_version_and_headless), [ST3E geonode modifier — build recipe, roster, publish checklist](asset-checklist.md), [Geonode sockets, interfaces and menus](sockets-and-menus.md#feedback_gn_menu_socket_default).

<a id="feedback_gn_blur_attribute_corner_noop"></a>

## Blur Attribute is a no-op on CORNER

*GN Blur Attribute silently does nothing on the FACE CORNER domain — pin it to POINT with Field on Domain*

`GeometryNodeBlurAttribute` only walks point/edge/face neighbours. Evaluated in a
face-corner context (i.e. feeding a `Store Named Attribute` with `domain='CORNER'`,
which is what a vertex-colour write usually is) it is a **silent no-op** — no error,
no warning, the slider just does nothing.

Measured on GN_AmbientOcclusion (4 samples, jitter on, sealed box):

| domain | iters 0 | 1 | 3 | 10 |
|---|---|---|---|---|
| CORNER | sd 0.12238 | 0.12238 | 0.12238 | 0.12238 |
| POINT  | sd 0.12455 | 0.07890 | 0.05334 | 0.01926 |

**Why:** the corner domain has no neighbour topology for the blur to traverse, and
Blender reports nothing when the domain is unsupported.

**How to apply:** wrap the blur output in
`GeometryNodeFieldOnDomain(data_type='FLOAT', domain='POINT')` before it reaches the
store. That forces the blur subtree to evaluate on vertices and lets the store
interpolate back out, so one slider behaves identically whichever output domain the
user picks. Same trap applies to any neighbour-walking field node fed into a CORNER
store. Always assert the *effect* in the verifier (stdev drops), never just that the
socket is linked — see [Geonode techniques](techniques.md#project_gn_ambient_occlusion).

<a id="feedback_gn_mesh_boolean_selfunion"></a>

## Single-input Mesh Boolean UNION is a passthrough

*GN Mesh Boolean UNION with a single multi-island mesh does NOT self-union (passthrough); a self-intersecting DIFFERENCE already merges overlapping cutter shells*

Two verified facts about Geometry Nodes `Mesh Boolean` (Blender 5.0), from EdgeDestruct
multi-tube work (2026-07):

1. **A single mesh fed into `Mesh Boolean` UNION (one input) is a PASSTHROUGH** — it does
   NOT merge/self-union overlapping islands, regardless of `Self Intersection`. Tested
   FLOAT / EXACT / MANIFOLD solvers: FLOAT & MANIFOLD leave it unchanged, EXACT only splits
   intersecting faces (keeps internal walls). A real union requires ≥2 SEPARATE geometry
   inputs to the multi-input socket. There is no clean single-input self-union node.
2. **A `Mesh Boolean` DIFFERENCE with `Self Intersection = True` already subtracts multiple
   overlapping cutter shells as their combined union volume** — so pre-unioning cutters
   before a self-intersecting difference is redundant (verified: identical output, clean
   continuous cut, no double surfaces). Only pre-union if you need to DISABLE that
   self-intersection for performance.

**How to apply:** don't add a "union the cutters first" step ahead of a self-intersecting
difference — it's a no-op. If you genuinely need a merged manifold, union the pieces as
separate inputs (or iterate islands in a Repeat/For-Each zone).

Also (Blender 5 naming): `ShaderNodeTexNoise` output is **"Factor"**, not "Fac".
Related: [Geonode sockets, interfaces and menus](sockets-and-menus.md#feedback_gn_new_socket_backfills_zero), [Geonode sockets, interfaces and menus](sockets-and-menus.md#feedback_gn_link_rewire_gotchas).

<a id="feedback_gn_vertex_data_channels"></a>

## Vertex data channels FBX actually carries

*FBX vertex-data facts + the big-interface GN patterns from GN_VertexDataComposer (528 sockets, menu-in-helper-group, lazy Switch as a cost gate)*

Built `GN_VertexDataComposer` (2026-08-09). What generalizes:

**What FBX actually carries (checked in Blender 5.0's own `export_fbx_bin.py`, not forums):**
- ALL `me.color_attributes` are exported (`vcolnumber = len(me.color_attributes)`, line ~1291)
  and ALL `me.uv_layers` (line ~1339). Not just the active one — that forum claim is stale.
- Arbitrary named float attributes are NOT exported to FBX (glTF/USD/Alembic only).
- Engine reality: **UVs are the precise pipe** (full float ×2, 8 sets), **vertex colour is the
  8-bit pipe** (Unity `Color32` / Unreal `FColor`). Unreal's FBX importer reads only the FIRST
  colour attribute, so slots 2+ must go to UVs.

**`GeometryNodeInputNamedAttribute` cannot be set to `FLOAT2`.** `bl_rna` lists 13 data types
but assignment only accepts 7 (`FLOAT, INT, BOOLEAN, FLOAT_VECTOR, FLOAT_COLOR, QUATERNION,
FLOAT4X4`). So: **read a UV map as `FLOAT_VECTOR` → (u,v,0); write it as `FLOAT2`/CORNER**
(Store Named Attribute DOES accept FLOAT2, and its Value socket is a VECTOR). Always test
enum assignment, never trust `bl_rna.properties[x].enum_items`.

**`iface.new_panel()` has NO `parent` kwarg** (unlike `new_socket`, which does). Nest panels
with `iface.move_to_parent(panel, parent, len(parent.interface_items))`. Nesting works and
survives save/reload.

**A huge interface is fine.** Measured: 528 sockets / 45 panels (32 of them nested) / 1440
modifier IDProperties → build 0.06 s, attach 0 s, evaluate 1 ms, save/reload instant. Stop
worrying about socket count; worry about node count and per-channel evaluation instead.

**Put a repeated menu INSIDE a helper group — the enum propagates outward.** A helper group
with a `NodeSocketMenu` input whose internal `MenuSwitch(INT)` defines 30 items exposes those
30 items on EVERY outer interface socket linked to it. That turned 32 × 30 = 960 menu links
into one definition + 32 instance links. Same for the component menu. This is the scaling
answer whenever N channels need the same dropdown (contrast with
[Geonode sockets, interfaces and menus](sockets-and-menus.md#feedback_gn_menu_to_index_switch), which is about ONE menu driving several switches).

**`Switch(GEOMETRY)` is lazy — use it as a COST GATE for expensive field nodes.** An
`Attribute Statistic` / `Raycast` / `Proximity` fed by `Switch(GEOMETRY, cond, <unconnected>,
geo)` costs nothing when the condition is off, because the empty branch feeds empty geometry.
Measured: auto-range on all 32 channels (32 statistics) added 2 ms on 90k verts. Without the
gate every channel would run a full mesh pass. Also cache genuinely expensive per-element
sources ONCE into internal `__vdc_*` named attributes and read them back by name — an
`IndexSwitch` with FIELD inputs is NOT lazy, so all branches would otherwise evaluate per
channel.

**Strip internal attributes** with `GeometryNodeRemoveAttribute` at the end of the graph, or
they export. Verified none leak.

**Blender 5 `GeometryNodeRaycast` has no `mapping` or `data_type` Python property** —
`Interpolation` is a MENU input socket now. `GeometryNodeProximity` inputs are
`Target / Group ID / Source Position / Sample Group ID`.

**Verification-harness lesson (cost 7 false failures):** a "reset the params then apply kwargs"
test helper must reset **every** parameter. `Invert` and `Encode sRGB` leaked across cases and
produced five bogus failures whose values looked like real graph bugs — the giveaway was a max
of 1.353 = `1.055·2^(1/2.4)−0.055`, i.e. sRGB applied to an inverted out-of-range ramp. Also
scope R9-style uniqueness checks to INPUT sockets (the in/out `Geometry` pair is universal),
and exempt `NodeReroute` from "every node is framed" like `layout_audit` R8 does.

<a id="feedback_gn_foreach_gen_preview_and_tube_noise"></a>

## For-Each preview streams and tube noise

*GN preview-overlay of cutters made inside a For-Each loop = split generation_items per stream + per-stream Switch; and noise on a tube must drive RADIUS not POSITION to stay parallel to the edge*

Two verified techniques from EdgeDestruct extra-tube preview work (2026-07-20):

1. **Preview-overlaying geometry that is generated INSIDE a `For Each Geometry
   Element` loop** (per-island cutters, tubes, etc.): the only way to surface it
   at the group output (outside the loop) is a **generation item** on the For-Each
   *Output* node — an accumulator that realizes the geometry across all iterations.
   To preview several internal streams *separately* (e.g. regular tubes vs extra
   tubes vs corner cubes), give each its **own** `generation_items.new('GEOMETRY',
   name)` and feed each from its in-loop source. Renaming a gen item is safe
   (outside links bind by socket identity, not name). Then outside the loop build a
   chain of `Switch(Show_X, False=prev, True=Join(prev, stream_X))` — one Switch per
   toggle — so **all-toggles-off passes the result through byte-identical** (the
   geometry-unchanged gate stays green). EdgeDestruct already carried corner cubes
   out via an unused debug gen feeding a Viewer — check for that before adding one.

2. **Noise on a swept tube/curve: drive RADIUS, not POSITION.** Offsetting curve
   points by a `Noise Texture` **Color** output via `Set Position` makes the tube
   *wander off* the edge (looks broken, non-parallel). To keep parallel copies
   running along the edge tangent, feed a clean curve into the sweep and let noise
   modulate **`Set Curve Radius`** (Noise Factor -> Map Range -> Min/Max radius).
   Lateral parallel offset = `normalize(cross(Curve Tangent, Normal))` * spacing via
   `Duplicate Elements(SPLINE)` + Duplicate Index. Expose the noise **Detail /
   Roughness / Distortion** as group inputs (not just Scale) for real control;
   type-zero legacy backfill of those is harmless (0 = valid). Related:
   [Geonode sockets, interfaces and menus](sockets-and-menus.md#feedback_gn_new_socket_backfills_zero), [Geonode nodes, fields and domains](nodes-and-fields.md#feedback_gn_mesh_boolean_selfunion),
   [Geonode techniques](techniques.md#feedback_gn_deformer_center_gizmo_symmetry).
