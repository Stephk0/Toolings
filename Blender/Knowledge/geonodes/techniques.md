# Geonode techniques

Reusable build recipes from ST3E modifiers. Layout and interface rules live in
`Blender/Addons/LLMGeonodePipeline/GEONODE_CRITERIA.md`; this page keeps the recipes and traps.

- [Deformers: Center, gizmo, symmetry](#feedback_gn_deformer_center_gizmo_symmetry)
- [Effect direction by axis or external object](#feedback_gn_object_direction_axis)
- [Region-fill and tile generators](#feedback_gn_region_fill_tile_generator)
- [Shared GNG_AmbientOcclusion core](#project_gn_ambient_occlusion)
- [Per-region and per-element aggregates](#gn_per_region_aggregates)
- [Tileable lattice noise](#gn_tileable_lattice_noise)

<a id="feedback_gn_deformer_center_gizmo_symmetry"></a>

## Deformers: Center, gizmo, symmetry

*Deformers with a pivot expose `Center` + `Show Center Gizmo`, `Symmetry` only for gradient-along-axis effects, `Affect X/Y/Z` for scaling effects, and an optional preview cage — modelled on GN_ShearGeometry*

**How to apply:**

1. **Center.** `Center` (NodeSocketVector, subtype `TRANSLATION`, default 0) is the world pivot.
   Rewrite the math relative to it (`pos - Center … + Center`; `VectorRotate.Center` for twist).
   Default 0 must reproduce the pre-center result.
2. **`Show Center Gizmo`** (bool, default True). Three `GeometryNodeGizmoLinear` (one per axis):
   `Value` ← component of `SeparateXYZ(Center)`, `Position` ← `Center`, `Direction` = unit axis,
   `color_id` X/Y/Z, `draw_style='ARROW'`. Plus a center marker: one more GizmoLinear,
   `draw_style='CROSS'`, `color_id='PRIMARY'`, `Value` ← the same `SeparateXYZ(Center).z` (two
   gizmos may target one value). Gate with `Switch(GEOMETRY, Show, main, Join(main, gizmos))`.
   Gizmos are overlay-only — evaluated vert count is identical on/off. Drag write-back can only be
   tested live, not headless.
   *Scalar pivot* (Shear's `Center Offset` float): one GizmoLinear, `Value` ← the Group Input float,
   `Direction` ← the existing mask-axis MenuSwitch output (don't add a second switch off the menu),
   `Position` ← `axisVec × Center Offset`.
3. **`Symmetry`** (bool, default False) only for gradient-along-axis deformers (Taper, Twist, Shear):
   `measure = Switch(FLOAT, Symmetry, coord − c, ABS(coord − c))`, `c = dot(Center, axisVec)`;
   normalised `t_sym = clamp(|coord−c| / max(Range/2, eps), 0, 1)`. Not for radial or already
   symmetric effects (Cast/sphere, Stretch, centred Bend) — there it is a no-op.
4. **Distance-from-center effects must be SIGNED by default.** `length(pos - Center)` is even:
   an object straddling the Center gets a mirror crease. Sign it with a reference direction:
   `d = dot(perp*R, normalize(R - dir*(R·dir)))`; `Symmetry ON` = `length(perp*R)`. Gate the
   change by asserting Symmetry-ON reproduces the old evaluated verts bit-for-bit; test continuity
   as parity (`z(-p) == -z(p)` signed vs `z(-p) == z(p)` mirrored).
5. **`Affect X/Y/Z`** for along/perpendicular scaling (Taper, Stretch): scale each world axis
   separately, `new = Center + (pos-Center) * CombineXYZ(s_x, s_y, s_z)`. Auto-exclude the
   gradient axis so defaults match for any axis: `isPerp_i = 1 - SeparateXYZ(axisVec)[i]`,
   `effect_i = isPerp_i * Affect_i`. Taper `s_i = 1 + (s-1)*effect_i`; Stretch
   `s_i = axisVec_i*Factor + isPerp_i*(1 + (Factor^-0.5 - 1)*Affect_i)` (Stretch's gradient axis
   does move — don't assert it unchanged). Not for planar (Twist/Bend), radial/normal, or
   single-direction (Wave) effects.
6. **Preview cage** (`Show Deformation Preview` bool default False + `Preview Resolution` int 12,
   in a closed `Preview` panel). The deform is a position field with bounds from a fixed
   `Attribute Statistic` of the input, so the same field drives a second `Set Position` on a cage:
   tap the field feeding the existing `Set Position`, `cage = GNG_DeformCage(Geo, Resolution)`,
   `Set Position(cage, same field, same mode)`, output via `Switch(GEOMETRY, Show, cur, Join(cur, cage))`.
   `GNG_DeformCage`: Bound Box → `MeshCube(Size=dims, Verts_i = round(dim_i/(max(dims)/Res))+1)` →
   `Delete Geometry(FACE, ONLY_FACE)` → offset to center. Real geometry (turn off for export).
   Positional deformers only — not Inflate (normal-based) or Smooth (topology).
   A pre-existing modifier backfills `Preview Resolution = 0` (bare 2×2×2 cube) — set it explicitly.
7. **Direction menus** for single-direction effects: master `MenuSwitch(INT)` → `IndexSwitch(VECTOR)`
   with an extra `Normal` item = `normalize(Input Normal)`; measure radius in the plane
   perpendicular to the chosen direction (`d - dot(d,dir)·dir`).

Panel order: see GEONODE_CRITERIA "Interface". Related:
[menus](sockets-and-menus.md#feedback_gn_menu_to_index_switch),
[backfill](sockets-and-menus.md#feedback_gn_new_socket_backfills_zero).

<a id="feedback_gn_object_direction_axis"></a>

## Effect direction by axis or external object

*Every deform modifier with a direction offers X/Y/Z OR an external empty's orientation, via the shared `GNG_ObjectDirection` helper*

**Convention:** append an `Object` item to each existing axis/direction menu and add a
`Direction Object` socket. Direction = the empty's local **+Z** (orientation, not aim-at-location).
Pivot tools also get `Use Object As Center` (bool, default OFF). The X/Y/Z + manual Center path
stays first-class.

**Helper `GNG_ObjectDirection`:** `ObjectInfo(transform_space='RELATIVE')` →
`FunctionNodeTransformDirection(unit_axis, transform)` → `NORMALIZE`. Outputs Direction (+Z),
Direction X, Direction Y, Location. No object → zero matrix → direction (0,0,0) → identity (safe).

**How to apply:**
- INT MenuSwitch → IndexSwitch modifiers: add a VECTOR item = helper.Direction (and a FLOAT
  "along-axis coord" item = `dot(Position, dir)` where one exists). Direct VECTOR MenuSwitch:
  add an enum item and link the helper into the new item input.
- Center override: `Switch(VECTOR, UseObj, Center, helper.Location)`, rewire only the math
  consumers of Center — the gizmo stays on the manual Center. Center is emitted by several
  Group Input nodes; gather consumers across all of them.
- Two-axis tools (Bend, Shear): one empty drives both — local +Z = primary axis, local +X =
  secondary; orthogonalise (`Da_o = normalize(Da - dot(Da,La)La)`).

**Traps:**
- **cos(90°) ≠ 0 in float32** (~-4.4e-8): an empty "exactly" on an axis is slightly tilted.
  Harmless except pole-singular ops (cylinder cast: ≤2 pole verts jump) — equivalence tests use
  median/p99, not max.
- **VECTOR MenuSwitch item identifiers are not `Item_{index}`** (Shear's were `Item_2/3/4`).
  Diff the set of `Item_*` identifiers before/after `enum_items.new()`.
- Menu overrides map to the item's value id, not its position — see
  [menus](sockets-and-menus.md#feedback_gn_menu_socket_default).
- **A max delta of exactly 0.0 can mean "both identity", not "match".** Verify on a visibly
  deforming reference (GN_Erosion's flat demo deforms nothing — use an icosphere).

**Verify:** an empty whose local +Z = world axis A must make `Axis=Object` == `Axis=A` (~1e-7).

<a id="feedback_gn_region_fill_tile_generator"></a>

## Region-fill and tile generators

*General GN traps from building GN_Mosaic (fill edge-bounded regions with tiles) — several fail silently, a parameter just appears to do nothing*

**How to apply:**
- **Regions from walls:** `SplitEdges(Selection=wall)` → `MeshIsland.Island Index` →
  `SampleIndex(FACE, INT, Index)` back onto the unsplit mesh (face indices survive SplitEdges) →
  store as a FACE INT "canvas". Walls = `Boundary Edges` OR `EdgeNeighbors.Face Count < 2`.
- **One Raycast = containment + region lookup:** cast from `p + N*rayLen` along `-N` at the canvas,
  `data_type='INT'`, `Interpolation="Nearest"`: `Is Hit` = inside, `Attribute` = region id. In a
  FACE context `Position` is the face centroid.
- **All-corners vs any-corner:** a bool read across domains is AND-ed. Materialise it with
  `FieldOnDomain(POINT, FLOAT)`; read in FACE context it averages → `>0.999` all inside, `>0.001`
  any overlap. Clipping must compare the vertex's **region**, not just "ray hit".
- **Geometry Proximity against an EMPTY target returns Distance 0** → `distance > margin` culls
  everything. Gate: `clear = (distance > margin) OR NOT Is Valid`.
- **GN-generated geometry has no material** — `obj.data.materials.append` does nothing. Expose a
  `Material` socket + `Set Material`.
- **`FLOAT_COLOR` belongs on CORNER**, but there `Index` is the corner index — feed ids from
  `FieldOnDomain(FACE, INT, Index)`.
- **Recursion without topology:** carry each element as ONE point with corner attributes; split =
  `Duplicate Elements(Amount = split ? 2 : 1)` (`Amount` is a per-element field); rebuild faces by
  instancing a `Mesh Circle(NGON)` (instance attributes survive Realize). In that Repeat Zone:
  store anything both children must agree on (cut point, split decision) **before** the duplicate;
  thread a **pass counter** as a repeat item or index-keyed randoms repeat every pass; never
  rewrite a corner set in place (write to scratch attributes, then copy).
- **Adaptive subdivision in a Repeat Zone:** check the sample is in the same space as the walls
  (local lattice vs world walls made the test fire on ~10 of ~180 cells). Store per-cell randoms
  after the zone, keyed on the final face index.
- **Curve tangents on a poly spline are interpolated bisectors** — `ResampleCurve` densely before
  sampling. `MeshToCurve` splits at T-junctions — work on a point cloud (`CurveToPoints`).
- **Per-edge randoms shared by two faces:** key on the edge MIDPOINT (`ShaderNodeTexWhiteNoise`),
  not a face id, or the two sides disagree.
- **Clamp generated vertex counts** (`MINIMUM 400`) or a small size freezes Blender.
- **Backward-compatible range:** add only a `_Max` socket default 0, `hi = MAXIMUM(base, base_Max)`.
- **Testing:** a safety clamp that stops a control responding reads as a broken feature — measure
  the delivered quantity in the user's units across the input range. Report quartiles, not min/max.
  Sanity-check settings (total tile area vs surface area) before debugging a "broken" render.

Triangulate `Quad Method` is a menu socket in Blender 5 — see
[properties that became menu sockets](nodes-and-fields.md#gn_property_became_menu_socket).

<a id="project_gn_ambient_occlusion"></a>

## Shared GNG_AmbientOcclusion core

*`GN_AmbientOcclusion.blend` ships the reusable `GNG_AmbientOcclusion` core; other files LINK it (relative `//GN_AmbientOcclusion.blend`), never reimplement it*

**Sampling recipe:** a Repeat Zone fires one `GeometryNodeRaycast` `Samples` times. Repeat items
can't carry per-element state ([why](nodes-and-fields.md#feedback_gn_edge_to_face_bool_interp)),
so the **geometry is the accumulator**: read a cache attribute, add the hit weight, store it back.
Every scalar the body needs (distance, spread, seed, the cache name as a STRING item) is its own
loop item wired straight input→output, or it resets each pass. Directions: `u = (k+0.5)/N`,
`cos θ = 1 - u·spread` (uniform) or `sqrt(1 - u·spread)` (cosine), azimuth =
`k · golden angle + per-point random` (the random rotation stops banding).

**How to apply:** for an optional pass, select it with a lazy `Switch(GEOMETRY)` so "off" skips
the group. Build/verify: `_build/build_gn_ambient_occlusion.py` → `verify_gn_ambient_occlusion.py`
→ `run_pipeline.py -- GN_AmbientOcclusion`. Related:
[blur on CORNER](nodes-and-fields.md#feedback_gn_blur_attribute_corner_noop).

<a id="gn_per_region_aggregates"></a>

## Per-region and per-element aggregates

*Island / group id + Accumulate Field gives any per-region sum, mean or size without loops — from GN_FlattenByBoundary, GN_Delete (stray islands) and GN_RandomizeMeshElements*

**How to apply:**
- **Region id:** `MeshIsland.Island Index` (connected components; a loose vert is its own
  island), or walls → id as in [region fill](#feedback_gn_region_fill_tile_generator).
- **Mean / plane:** `AccumulateField(Group ID = id).Total` of `FaceNormal·Area`, `Pos·Area`,
  `Area` → area-weighted normal and centroid per region; `FieldOnDomain(POINT)` to verts.
- **Size of an island:** RMS = `sqrt(Σaxes (E[p²] − E[p]²))` from three accumulations (count, ΣP,
  ΣP²) — no min/max needed. Compare against `AttributeStatistic.Max` of that size (the largest
  island), not a global bbox, so a far-away stray can't inflate the reference.
- **Move whole elements rigidly:** one INT key per FACE (`IndexSwitch` of Island / Index /
  Material / attribute) → `FieldOnDomain(FACE)` → `MeshFaceSetBoundaries` → `SplitEdges` (a
  shared vertex is never asked to move two ways), and key every random on that id via
  `RandomValue`'s **ID** input. An odd number of mirrored axes flips winding → `FlipFaces`.
- Verify rigidity with an invariant (a cube's corners stay equidistant from its own centre).

<a id="gn_tileable_lattice_noise"></a>

## Tileable lattice noise

*Tileable noise = hashes on a lattice that wraps `mod N`; float32 and lattice resonance are the silent failure modes — from GN_TileableMeshNoise*

**How to apply:**
- Wrap every lattice index `mod N`, **including the +1 neighbour** — forgetting it seams the last
  cell. Verify by shifting one tile and checking verts mate exactly.
- **Keep hash keys below 2^24** (float32 exact; e.g. `c·4096 + r + 999331`); separate channels with
  the Hash node's Seed input, not by bigger keys. Use a prime modulus (46337) — a power-of-2
  modulus clustered ids (59/64 distinct).
- **A second lattice at the mesh lattice's frequency does nothing**: vortex/feature centres land
  exactly on verts (r = 0 or r = rmax). Give it its own lattice (half frequency, integer count),
  jitter its centres, and let the effect die before the cell border.
- Anything per cell that must match across a seam is computed from the wrapped cell id (shared
  by both halves within a tile) and must be identical per tile — constant magnitudes or means
  over the wrapped id, never per-half quantities.
- Barycentric side tests on a `Fixed` triangulation are knife-edge on the diagonal (`fu+fv = 1`
  exactly) — test `fu > fv`.
- Seams need a visual check too: render 3×3 copies (see
  [demo render](asset-files.md#feedback_geonode_demo_scene_hygiene)).

