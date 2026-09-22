# Geonode techniques

Reusable build recipes from specific ST3E modifiers.

> Migrated verbatim from Claude auto-memory on 2026-09-22. Dates and version numbers are from when each note was written — trust the code when they disagree.

- [Deformers: Center, gizmo, symmetry](#feedback_gn_deformer_center_gizmo_symmetry)
- [Effect direction by axis or external object](#feedback_gn_object_direction_axis)
- [Region-fill tile generator (GN_Mosaic)](#feedback_gn_region_fill_tile_generator)
- [Shared GNG_AmbientOcclusion core](#project_gn_ambient_occlusion)

<a id="feedback_gn_deformer_center_gizmo_symmetry"></a>

## Deformers: Center, gizmo, symmetry

*ST3E deformer geonodes with a pivot must expose Center + Show-Gizmo (3-axis Linear gizmo) and a Symmetry toggle (abs-distance-from-center), matching GN_ShearGeometry*

For ST3E **deformer** geonodes that have a reasonable pivot/center, follow this convention (user instruction 2026-06-03/04, modelled on `GN_ShearGeometry`):

**1. Editable Center.** Expose `Center` (NodeSocketVector, subtype `TRANSLATION`, default (0,0,0)) = the world-space pivot. Rewire the math relative to Center (`pos - Center` … `+ Center` for scaling/rotation pivots; `VectorRotate.Center` for twist). Default 0 must reproduce the pre-center behaviour (the natural pivot was the world origin for most; for Bend the bar's middle pivots at Center).

**2. Show-Gizmo toggle → draggable 3-axis gizmo.** Expose `Show Gizmo` (bool, default True). Build three `GeometryNodeGizmoLinear` nodes (one per axis): `Value` ← component of `SeparateXYZ(Center)`, `Position` ← `Center`, `Direction` = unit axis, `color_id` = `X`/`Y`/`Z`, `draw_style='ARROW'`. `JoinGeometry(mainGeo + the 3 gizmo Transform outputs)`, then `Switch(input_type='GEOMETRY', Switch=Show Gizmo, False=mainGeo, True=join)` → group output. **Verified: the gizmo is a viewport overlay only — it does NOT add real mesh verts** (evaluated vert count identical gizmo on/off). **Caveat:** the drag write-back (editing Center) traces back through `Separate XYZ`; this is interactive and CANNOT be verified headless — must be tested live by the user. Gizmo nodes: `GizmoLinear`(Value/Position/Direction→Transform geo), `GizmoDial`(angle), `GizmoTransform`(Value=MATRIX/Position/Rotation→Transform).

**3. Symmetry toggle (where it changes behaviour).** Expose `Symmetry` (bool, default False) ONLY for **gradient-along-axis** deformers (Taper, Twist — like Shear). `GN_ShearGeometry`'s exact pattern: `measure = Switch(input_type='FLOAT', Switch=Symmetry, False=(coord − centerCoord), True=ABS(coord − centerCoord))`, then that signed/abs measure drives the effect. So Symmetry mirrors the deformation across the center plane (both sides act the same). `centerCoord` = `dot(Center, axisVec)`. For Taper/Twist I normalise: `t_sym = clamp(|coord−centerCoord| / max(Range/2, eps), 0, 1)` and `drive = Switch(Symmetry, False=t01, True=t_sym)`. **Do NOT add Symmetry to inherently-symmetric deformers** — Spherify & Wave are radial about Center, Stretch scales symmetrically about Center, and a centered single-arc Bend is already Z-symmetric (cos is even); a toggle there would be a no-op/ambiguous.

**4. Multi-axis effect filter (user instruction 2026-06-04).** A deformation effect should usually be filterable to a SUBSET of axes — "a taper can be an X-taper along Y, or an XZ-taper along Y". For along/perpendicular scaling deformers (Taper, Stretch) expose `Affect X` / `Affect Y` / `Affect Z` bools (default all True). Implement by scaling each WORLD axis component independently (drop the dot/along/perp decomposition): `scale_i` built per axis, then `new = Center + (pos-Center) * CombineXYZ(scale_x,scale_y,scale_z)`. **Auto-exclude the gradient axis** so defaults match old behaviour for ANY axis choice: `isPerp_i = 1 - SeparateXYZ(axisVec)[i]` (1 if perpendicular, 0 if it's the gradient axis); `effect_i = isPerp_i * Affect_i` (bool→float). Taper: `scale_i = 1 + (s-1)*effect_i`. Stretch: `scale_i = axisVec_i*Factor + isPerp_i*(1 + (Factor^-0.5 - 1)*Affect_i)` (gradient axis always ×Factor; only selected perp axes squash). Verified: Affect-X-off leaves X coords byte-unchanged while Y still scales. Does NOT fit Twist/Bend (planar), Spherify/Inflate (radial/normal), or Wave (single displacement direction) — left those alone. NB stretch's gradient axis DOES move (that's the stretch) — don't assert gradient-axis-unchanged in tests (only taper's gradient is unchanged).

**5. Naming, center marker, and UI panels (user instruction 2026-06-04).**
- The gizmo toggle is named **`Show Center Gizmo`** (not "Show Gizmo").
- Besides the 3 move arrows, add a **crosshair center marker**: one more `GizmoLinear` with `draw_style='CROSS'`, `color_id='PRIMARY'`, `Value` ← `SeparateXYZ(Center).z` (the SAME value the Z arrow edits — verified two gizmos CAN target one value with no error and no extra verts; gizmos stay overlay-only), `Position` ← `Center`. It reads as "this point is the deformation center." (Scalar-center Shear: the cross's `Value` = `Center Offset`, `Position` = the offset point, `Direction` = mask-axis vector.)
- **Use GN interface PANELS** to categorise modifier inputs (`ng.interface.new_panel(name, default_closed=False)` then `ng.interface.move_to_parent(socket, panel, index)`). Convention: `Selection` stays top-level; then a **base-params panel** named after the effect (Twist/Taper/Wave/…); then (for scaling deformers) an **`Affect Axes`** panel (default_closed=True); then a **`Center`** panel LAST holding `Center` + `Show Center Gizmo` (scalar Shear: `Center Offset` + `Show Center Gizmo`). Even Inflate/Smooth (no center) get a single base panel.
- **Direction-of-effect menus** for single-direction deformers: `GN_Wave` gained a **`Displace Along`** menu (X/Y/Z/**Normal**) via master MenuSwitch(INT 0-3) → IndexSwitch(VECTOR) with item 3 = normalize(Input Normal); radius is measured in the plane perpendicular to the chosen dir (`d - dot(d,dir)·dir`), so `Z` reproduces the old XY-plane ripple. offset = `dir × Amplitude × sin(...)`.

**6. Deformation preview cage (user instruction 2026-06-04).** A toggleable bbox **lattice** that visualises the deform on a clean cage (like a twist shown on a box). KEY ENABLER: the deformation is a POSITION FIELD whose bounds come from a fixed `Attribute Statistic` on the input object — so the SAME field can be fed into a SECOND `Set Position` driving a generated cage, and it deforms consistently (the cage spans the object's bbox, so `t=(coord-objMin)/objRange` runs 0→1 across it). Generic wiring (works for every positional deformer): (a) add `Show Deformation Preview`(bool, default False) + `Preview Resolution`(int 12) in a closed **`Preview`** panel; (b) **tap the field** feeding the single existing `Set Position` (find its `Position`/`Offset` source socket — generic, no per-modifier hardcoding); (c) `cage = GNG_DeformCage(InputGeo, Resolution)` then `Set Position(cage, <same field, same Position/Offset mode>)`; (d) rewire output through `Switch(GEOMETRY, Show Deformation Preview, false=cur, true=Join(cur, deformedCage))`. **`GNG_DeformCage`** helper group: `Bound Box`→Min/Max→dims/center; adaptive uniform cells = `MeshCube(Size=dims, VertsX/Y/Z = round(dim_i / (max(dims)/Resolution))+1` via `FunctionNodeFloatToInt`); `Delete Geometry(domain=FACE, mode='ONLY_FACE')` leaves the wireframe; `Set Position(Offset=center)` to place it. It's REAL (gated) geometry, not an overlay — appears only when toggled (turn off for export); demos ship with it ON. **Only POSITIONAL deformers** (Twist/Taper/Bend/Spherify/Stretch/Wave/Shear) — NOT Inflate (normal-based: cage uses the cage's own box normals, wrong) or Smooth (topology-blur: meaningless on a different mesh). GOTCHA: a pre-existing demo modifier won't pick up the new `Preview Resolution` default (=0 → bare 2×2×2 cube) — set it explicitly on the demo and in tests.

**Scalar (1-D) center variant — `GN_ShearGeometry` (updated 2026-06-04):** when the pivot is 1-D (a `Center Offset` float along an axis, not a 3-D point), use ONE `GizmoLinear`: `Value` ← the Group-Input float directly (cleanest write-back), `Direction` ← the existing **mask-axis vector** (tap the `Mask Axis Menu` MenuSwitch/VECTOR `Output` — do NOT add a second switch off the same menu), `Position` ← `MaskAxisVec × Center Offset` (VectorMath SCALE) so the arrow sits on the pivot plane. Same `Show Gizmo` Join+Switch(GEOMETRY) gating. Added surgically WITHOUT re-laying-out the existing hand-made graph (placed the gizmo cluster in a frame below; existing node positions untouched). ShearGeometry already had `Center Offset` + `Symmetry`, so only the gizmo+toggle were missing.

Applies to the 2026-06-03 deformer batch (see [ST3E geonode modifier — build recipe, roster, publish checklist](asset-checklist.md)). Build headless per [Geonode asset files](asset-files.md#feedback_geonode_file_needs_object); lay out per [Geonode layout](layout.md#feedback_gn_node_layout_spacing); axis menus via [Geonode sockets, interfaces and menus](sockets-and-menus.md#feedback_gn_menu_to_index_switch).

**7. A distance-from-center deformer mirrors unless the distance is SIGNED (user image-diff on GN_Wave, 2026-09-20).** Any effect driven by `length(pos - Center)` (or `length(perp)`) is an EVEN function of position: on an object straddling the Center you get a mirror plane through it and a visible crease, and the wave never cycles continuously across the mesh. **Default must be a signed distance; the mirrored version is the `Symmetry` bool, default OFF** (existing bool sockets backfill legacy modifiers to False, which is the new default -- intended). Signing needs a reference direction: with a per-axis weight vector `R` and an effect direction `dir`, use `d = dot(perp*R, normalize(R - dir*(R.dir)))` (R projected into the perpendicular plane, so the gradient magnitude stays 1 and the wavelength is right); `Symmetry ON` = `length(perp*R)`. Gate the change by asserting Symmetry-ON reproduces the pre-change evaluated verts BIT-FOR-BIT, then flip the shipped demo to the new default. Test continuity as a parity property, not by eyeballing: Phase 0 => `z(-p) == -z(p)` signed (odd) vs `z(-p) == z(p)` mirrored (even). Note GN_Wave's `Affect X/Y/Z` are FACTOR floats (tunable), not the bools item 4 describes. Related: [Geonode sockets, interfaces and menus](sockets-and-menus.md#feedback_gn_new_socket_backfills_zero).

<a id="feedback_gn_object_direction_axis"></a>

## Effect direction by axis or external object

*ST3E deform modifiers expose effect direction quick-by-axis (X/Y/Z) OR custom via an external object/empty — the GNG_ObjectDirection convention + gotchas*

User instruction 2026-07-19: **every ST3E deform modifier with a direction/axis must let the
user set the effect direction either quick-by-axis (X/Y/Z, already present) OR custom via an
external object/empty.** "Whenever there's a direction vector, the user probably wants axis or
object." The non-object path (manual X/Y/Z + manual Center) stays fully first-class; the object
is a purely additive, opt-in menu item + socket. See [ST3E geonode modifier — build recipe, roster, publish checklist](asset-checklist.md),
[Geonode techniques](techniques.md#feedback_gn_deformer_center_gizmo_symmetry), [Geonode sockets, interfaces and menus](sockets-and-menus.md#feedback_gn_menu_to_index_switch).

#### The convention
- **Direction = the empty's ORIENTATION**, its local **+Z** axis (user rotates the empty like an
  arrow to aim it; position ignored unless it drives Center). NOT aim-at-location.
- **UX = a new `Object` item appended to each existing Axis/Direction menu** (X/Y/Z → +Object),
  plus a `Direction Object` (Object socket). Selecting `Object` uses the empty; X/Y/Z as before.
- **`Use Object As Center`** bool (default OFF) on modifiers that have a `Center` pivot — when ON,
  the empty's location becomes the deform pivot instead of the Center vector.

#### Reusable helper: `GNG_ObjectDirection` (build once, appended into every file)
`Object` → `ObjectInfo(transform_space='RELATIVE')` → `FunctionNodeTransformDirection(dir=unit_axis,
transform)` → `VectorMath NORMALIZE`. Outputs: **Direction** (local +Z), **Direction X** (local +X),
**Direction Y** (local +Y), **Location** (for Use Object As Center). RELATIVE keeps it in the
modified object's local space. No object assigned → zero matrix → dir=(0,0,0) → deform is identity
(safe). Builder + rollout scripts were scratchpad `axisdir_lib.py` / `apply_axisdir.py` (throwaway).

#### Per-modifier wiring (11 modifiers done 2026-07-19)
- **menu-int → IndexSwitch pattern** (Twist, Taper, Stretch, Cast[cyl axis], Wave, Displace):
  append `Object` to the INT MenuSwitch, add a VECTOR IndexSwitch item = helper.Direction; if the
  modifier also has a FLOAT "along-axis coord" IndexSwitch (Twist, Taper) add an item =
  `dot(Position, dir)`.
- **direct VECTOR MenuSwitch** (NoiseDisplace, VoronoiDisplace, ShearGeometry): append `Object`
  enum item, link helper.Direction into the NEW item input. Keep existing Custom Vector/Normal.
- **Erosion** ("Along Axis" = three `ShaderNodeTexWave` with bands_direction X/Y/Z reading implicit
  position): added a 4th wave texture, bands X, fed `Vector = CombineXYZ(dot(pos,dir),0,0)` so it
  bands along the empty's axis (== X texture when empty aims at X).
- **Center override** (Twist/Taper/Stretch/Cast/Wave/Bend): `Switch(VECTOR, uoc, Center, helper.Location)`,
  then rewire ONLY the `ShaderNodeVectorMath`/`ShaderNodeVectorRotate` consumers of the Center
  group-input to the switch output — the gizmo (`GeometryNodeGizmoLinear` + `SeparateXYZ`) stays on
  the manual Center so the arrows still edit it. Center is emitted by MULTIPLE Group Input nodes —
  gather consumers across ALL of them, not one.
- **GN_Bend** (had NO axis): rebuilt to vectors. New `Bend Axis` (length `La`) + `Bend Direction`
  (deflection `Da`, orthogonalized `Da_o=normalize(Da-dot(Da,La)La)`), hinge `Ha=La×Da_o`.
  `newPos = C + sinA·r·La + (R-cosA·r)·Da_o + w·Ha`, w=dot(pos-C,Ha). Reproduces the old X-length/Z-bend
  EXACTLY at Axis=X/Dir=Z (verified maxd 0.0). ONE Direction Object drives both: its local +Z = length
  axis, local +X = deflection (the "as they relate" principle). Menus X/Y/Z/Object.
- **GN_ShearGeometry**: `Object` on BOTH Shear Axis (=empty local +Z) and Mask Axis (=empty local +X)
  from the SAME single Direction Object — one empty, two related perpendicular axes.

#### Gotchas (all bitten)
- **cos(90°) is not 0 in float32** (~-4.37e-8). An empty aimed "exactly" at an axis gives a
  sub-epsilon-tilted direction, NOT bit-exact (1,0,0). Harmless everywhere EXCEPT **GN_Cast's
  cylinder cast, which is pole-singular**: verts on the axis get `normalize(perp≈0)` → snap to unit
  → an isolated ~1.0 jump at ≤2 pole verts. Inherent to cylinder casting, cosmetic; equivalence
  tests must tolerate a few pole outliers (median/p99, not max).
- **VECTOR MenuSwitch item-input identifiers are NOT `Item_{index}`** — GN_ShearGeometry's were
  `Item_2/3/4`. Append by DIFFING the set of `Item_*` input identifiers before/after
  `enum_items.new()`, never assume `Item_{len}`.
- **A modifier's menu override maps to the enum item's internal VALUE id, not its 0-based position.**
  Cleanly-built menus have value ids 0,1,2,… so `m[sock]=int` works by luck; hand-built ones
  (Shear) are non-sequential and `m[sock]=0` misses ("Missing property" warning, reads as nothing).
  `NodeEnumItem` has no `.value` attr to read. **Override-agnostic verify:** set the interface menu
  socket's `default_value` (by item NAME) and RE-ADD the modifier (fresh picks defaults), rather
  than fighting int overrides. This also matters for anything int-driving these menus.
- **GN_Erosion's demo is a flat grid → its normal-masking yields ~0 offset** (shipped demo evaluates
  to maxd 0.0 — pre-existing; erosion is built for rocky/varied normals). Verify axis features on an
  **icosphere** (there Object(Z→+Y) == Along=Y at 1.5e-6), NOT on the flat demo (both zero = false pass).
  Same trap: an equivalence maxd of EXACTLY 0.0 can mean "both identity", not "match" — require a
  visibly-deforming reference.
- New interface inputs backfill existing modifiers with type-zero (Object socket = None) →
  defaults reproduce old behavior. See [Geonode sockets, interfaces and menus](sockets-and-menus.md#feedback_gn_new_socket_backfills_zero).

#### Verify recipe
Equivalence: an empty whose local +Z = world axis A must make `Axis=Object` == `Axis=A` (exact,
~1e-7). For Bend/Shear that need two axes, build the empty's matrix_world columns so local Z and
local X land on the intended world axes. Tidy each edited graph via `run_pipeline.py` (geometry-gate
+ R1/R2/R7). All 11 saved + tidied.

<a id="feedback_gn_region_fill_tile_generator"></a>

## Region-fill tile generator (GN_Mosaic)

*Recipe + gotchas for GN generators that fill bounded mesh regions with a tile field (GN_Mosaic) — raycast canvas for containment+region id, cross-domain all/any tests, contour rows, empty-Proximity trap, GN geometry has no material*

Built for `GN_Mosaic` (2026-08-03). Reusable whenever a geonode must **fill an area
bounded by edge loops** with generated elements. See [ST3E geonode modifier — build recipe, roster, publish checklist](asset-checklist.md).

**Why:** every one of these cost a debug cycle; three of them fail *silently* (no error,
just a parameter that appears to do nothing).

**How to apply:**

**Regions from walls.** `SplitEdges(mesh, Selection=wall)` makes each bounded area a
connected component → `MeshIsland.Island Index` → `SampleIndex(domain=FACE, data_type=INT,
Index=Index)` carries the region id back onto the *unsplit* mesh (face indices survive
SplitEdges) → `StoreNamedAttribute(FACE, INT)` = the raycast **canvas**. Walls =
`Boundary Edges` field OR open edges (`EdgeNeighbors.Face Count < 2`). Separating by a face
`Selection` FIRST makes the selection border a wall for free. (Same family as
[Geonode nodes, fields and domains](nodes-and-fields.md#feedback_gn_edge_to_face_bool_interp) / GN_FlattenByBoundary.)

**One Raycast does containment AND region lookup.** Cast from `p + N*rayLen` along `-N`
at the canvas with `data_type='INT'`, `Interpolation="Nearest"`, `Attribute` = the region
attr: `Is Hit` = "inside the surface", `Attribute` = which region. `rayLen` = bbox diagonal
+ 1. **In a FACE context `Position` evaluates to the face centroid**, so one such raycast
tags every finished tile.

**Fit modes (all-corners vs any-corner).** A boolean read across domains is **AND**-ed, so
materialise it: `FieldOnDomain(domain=POINT, data_type=FLOAT)` of the bool, read in a FACE
context = the average over the face's verts → `>0.999` = *fully inside*, `>0.001` = *any
overlap*. Centre-inside = the same trick on a field that is constant per tile.

**Exact tiling = PARTITION the region, don't intersect a grid with it.** A grid ∩ region
can never land tile edges on an arbitrary outline, which is what every fit-mode /
boundary-fit / contour-row compensation exists to paper over. Subdividing the region's
own faces instead makes exact coverage free (measured 100.00% at zero grout). Recipe
(GN_Mosaic's Shatter mode): seed one point per region triangle carrying its 3 corners
(`Corners of Face(Sort Index k)` → `Vertex of Corner` → `Sample Index(Position)`), then a
Repeat Zone of recursive **longest-edge bisection** — relabel so the longest edge is P→Q
with apex R, cut at M on PQ, children are (P,M,R) and (M,Q,R).

**Beyond triangles (3-6 corners).** Carry up to six corner vectors + a count; one split
cuts edge i and edge j = i+d, giving children of d+2 and n-d+2 corners. Draw d from
`[max(1, n+2-M), min(n-1, M-2)]` and both children stay within Max Corners M — **always
halving parks every tile at four corners for ever, so pentagons and hexagons never
appear**. M=3 is the special case: the second cut lands ON a vertex (d = n-1) instead of
on an edge. Build the mesh with one `Instance on Points` pass per corner count (selection
= count matches) rather than one prototype with degenerate doubled corners; then
`Face of Corner` → **"Index in Face"** gives each corner its slot, and an
`Evaluate on Domain(CORNER)` carries the result back to the point domain exactly, because
each tile owns its vertices outright.

**Tiling a mosaic is a GROUT problem, not a vertex-matching one.** The instinct is to
mirror every split from one bounds face to the opposite one. That cannot be done in a
partition — the tile on the far side is a different polygon and cannot be forced to split
in sympathy; keying the cut position on the WRAPPED coordinate only helps where both
faces happen to divide the same span, which in practice is almost never (measured: 0 of
7 split-created cuts matched). It does not matter. Tiles are separated by grout anyway,
so a seam is invisible as soon as (a) no tile crosses the box and (b) tiles are inset
from a bounds face by **half the interior Gap** — then two copies meet at exactly one Gap,
identical to every other joint. Using the *Boundary* Gap there instead is the actual bug:
the seam then shows 2x Boundary Gap as a visible line. Verified by rendering a 3x3 array.

**Jitter is what exposes whether the seam really tiles.** At zero jitter every cut is a
midpoint, so both faces divide a shared span identically *by accident* and the seam looks
perfect — turn jitter on and they diverge (measured 0 → 16 unmatched cuts). Keying the cut
POSITION on the wrapped midpoint does not fix it: it fixes *where* a seam is cut but not
*whether*, and the decision stays tile-dependent, so the faces still part company after the
first level. **The only exact fix is to never create a NEW vertex on a seam**: a cut may
start or end on an existing seam vertex (drop that child a corner), but the seam keeps
exactly the subdivision the input mesh gave it — periodic by construction, at any jitter
(measured 0 unmatched at jitter 0 / 0.5 / 1.0). Cost: tile spacing ALONG a seam comes from
the input mesh, so subdivide it for a finer border. Guard the degenerate case — a diagonal
whose two ends are both existing vertices needs ≥2 corners either side or the child is a
two-corner sliver; veto the split instead.
Second trap in the same area: a shatter tile sits exactly ON the wall, so a reserved-band
test of `distance > band` deletes every boundary tile when the band is zero — compare
against `band - 1e-5`.

**Rewriting the corner set in place corrupts it.** Each new corner is looked up out of ALL
the old ones, so a chain of stores that overwrites V0 before V1 is computed feeds the
fresh value straight back into the next lookup — every second child silently collapsed
onto a single corner (area fell to ~2% of the region). Write to scratch attributes first,
then copy scratch → real in a second pass.

**Per-edge grout (a different gap on the boundary).** The bisector formula only works when
both adjacent edges want the same offset. For d1 ≠ d2 solve for the point at d1 from one
edge and d2 from the other: with unit inward normals n1, n2 and c = n1·n2,
`α = (d1 − c·d2)/(1−c²)`, `β = (d2 − c·d1)/(1−c²)`, `p = v + α n1 + β n2`. Detect a
boundary edge by its midpoint's distance to the wall geometry (~0, since the tiles
partition the region exactly). **Do not cap the step to avoid inversion** — that silently
leaves sharp corners short of the gap, and no after-the-fact push repairs it (at a sharp
corner, moving away from one wall moves *towards* the other). Apply the exact solve and
DROP tiles whose step would have been capped: a tile with no room for its own grout is
nothing but grout.

**The trick that makes recursion possible at all:** GN cannot cut a face along a line, but
tiles are separated by grout anyway, so they need no shared topology. Carry each tile as
ONE POINT with corner attributes; a split is just `Duplicate Elements(Amount = split ? 2
: 1)` — **`Amount` is a per-element field**. Rebuild real triangles at the end by
instancing a 3-vert `Mesh Circle(NGON)`: instance attributes survive Realize, so each
vertex already knows its tile's corners and picks one with `Index % 3`.

Four things that bite in that zone:
- **Anything random that both children must agree on has to be stored BEFORE the
  duplicate** (the cut point M especially) — recompute it per child and the two halves
  tear apart. Store the split decision too, or unsplit tiles get "half split".
- **Thread a pass counter through the zone as a second repeat item.** Randoms keyed on
  element index alone are constant across passes for a region that is still one tile, so
  a tile that failed its split roll once fails it *forever* — a whole shape came back as
  a single untouched triangle.
- **Longest-edge bisection provably cannot repair a bad seed** (it preserves the worst
  initial angle). Slivers in the input triangulation survive as hairline tiles all the
  way out. Fix the *seed*, not the recursion — a fan-filled n-gon or `bmesh triangle_fill`
  hands it spans across the whole shape; a proper radial/quad topology fixes it. An
  aspect test (`longest² / area > 6`) helps but only softens it.
- **Uniform grout on triangles**: shift each corner along its angle bisector by
  `gap / (2·sin(θ/2))`. That backs every EDGE off by exactly half the gap whatever the
  corner angle. Cap the shift at ~0.4× the shorter adjacent edge so small tiles cannot
  invert.

**Adaptive tile size = a Repeat Zone that splits crowded cells.** Per pass: `refine =
distance(cell centre → wall) < sqrt(FaceArea) * threshold` AND the centre raycasts onto
the surface → `SeparateGeometry(FACE)` → `SubdivideMesh(Level=1)` on the selected part →
`JoinGeometry` with the inverted part. T-junctions are harmless because every face
becomes its own tile anyway. Store per-cell randoms AFTER the zone, keyed on the final
face index, or all four children inherit the parent's draw. **The trap that made this
look broken: the lattice is still in its own flat local space at that point while the
walls are in world space** — rotate the sample position by the plane rotation and add the
grid origin first, or the test almost never fires (it fired on ~10 cells instead of ~180;
symptom was a barely-there 15% size gradient instead of 20×).

**With mixed tile sizes the grout can no longer be one global factor** — a quarter-size
tile would lose a quarter of its grout. Measure each tile: `rms` distance from its own
centroid (`AccumulateField` of `dot(p-c,p-c)` / count, sqrt), which for a square of side
s is s/√2, then `scale = (s − Gap)/s`. Clamp the scale at ~0.4 so the deepest sub-tiles
are not eaten alive by an absolute grout width.

**A reserved band must be a WHOLE-TILE rule, not a centre rule.** Testing only the centre
let grid tiles poke half their width into the last contour row and overlap it. Unsigned
proximity makes the all-vertex form free of side effects: at band 0 `distance > 0` is
trivially true, so the band-off behaviour is untouched.

**Reshaping a tile onto a boundary: move along the wall's PERPENDICULAR, signed.**
`dir = normalize(pos − closestWallPoint) * (inside ? +1 : −1)`, then
`target = closestWallPoint + dir * BoundaryGap`. Aiming at the tile centroid instead
drags vertices sideways past their neighbours and bites notches out of the tile; snapping
flat onto the wall folds a quad whenever two corners share one target. Keep the centroid
direction only as the degenerate fallback for a vertex sitting exactly on the wall.

**Never charge a whole-tile reservation per vertex.** A band reserved for contour rows
must be tested ONCE, on the tile centre; testing it per vertex too costs an extra
tile-width of fill everywhere and made "fully inside" look broken (62% → 84% coverage on
the same scene once separated). Per-vertex gets the user's own margin, nothing more.
Corollary for the honest answer: *fully inside* inherently leaves a tile-wide strip along
every wall — that strip is what contour rows (or overlap+cut) are for, not a bug.

**Clipping must test the REGION, not just "did the ray hit the surface".** The canvas is
never split, so a vertex on the far side of an interior wall still hits it happily. Compare
the vertex's region against the tile's own (`FieldOnDomain(domain=FACE)` of a centre-hit
raycast, exact because each tile is its own island) or nothing ever hugs an interior loop.

**Geometry Proximity against an EMPTY target returns Distance 0** — so a `distance >
margin` test reads as "hard against the boundary" and culls *everything* when the user has
no walls marked. Gate every such test on the node's `Is Valid` output:
`clear = (distance > margin) OR NOT Is Valid`.

**GN-generated geometry carries NO material.** `obj.data.materials.append(mat)` does
nothing for it — the tiles render Blender's default grey. Expose a `Material` socket +
`Set Material` node. (Cost a full "why is my colour attribute not working" detour.)

**`FLOAT_COLOR` goes on the CORNER domain** (where Blender's own colour attributes live).
But the store then runs in a CORNER context, where `Index` is the **corner** index and
paints a gradient across each face — feed the id from
`FieldOnDomain(domain=FACE, data_type=INT, Value=Index)` instead.

**Per-element local transform.** `SplitEdges` with no selection = every face its own
island → `AccumulateField(Group Index=Island Index)` of Position and of 1.0 gives the
per-element centroid; a FACE attribute read in a POINT context is then **exact** (one face
per vert). Then `pos' = centroid + rotate(pos-centroid)*scale + jitter`.

**Contour rows following an outline** (four traps, all hit on 2026-08-03):

1. **A curve tangent on a poly spline is INTERPOLATED between per-control-point
   BISECTORS.** On a coarse outline (a square = 4 control points) the 45° corner
   rotation is smeared along the entire straight run, so contour bricks sit visibly
   skewed on walls that are dead straight. Fix: `ResampleCurve` to ~0.15 × pitch
   **before** sampling tile positions — with dense control points the bisector is the
   segment direction. Measure it, don't eyeball: take each output quad's longest edge
   and compare to the wall direction (skew was (±0.27,−0.96) vs the true (0,−1,0)).
2. **`MeshToCurve` splits at T-junctions.** Where an interior wall meets the outline the
   outline becomes several OPEN splines; offsetting/resampling those as curves doubled
   and crossed the rows. Do the sampling once, then work on a **point cloud**
   (`CurveToPoints(mode='LENGTH')`, which also hands you Tangent/Normal/Rotation) —
   `DuplicateElements(POINT, Amount=rows)` gives the row via `Duplicate Index`.
3. **Relaxation onto the wall must be RESCUE-ONLY.** Pushing every point out to its full
   row distance (via the proximity gradient, or worse a 1/cos corner correction) walks
   corner points diagonally inward and **rounds a square outline into a blob**. Only
   move points that are outside, or closer than half a tile: target = `0.5 * TileSize`,
   with the push signed by an inside test and capped at one row.
4. **`MergeByDistance` to kill corner pile-ups must be keyed to the TILE**
   (`0.5 * TileSize`), never to the spacing along the wall — a spacing-relative radius
   swallows legitimate neighbours and averages their tangents.

Inward direction = `cross(N, tangent)` with the **sign resolved by probing**: raycast at
`p + inward*0.35*pitch`; miss ⇒ flip. Carry the row's target distance in a named attr
(`Duplicate Index` does not survive the merge) and drop points that ended up far from it
— those came from a folded stretch and would stack a second tile.

**Varying the triangle diagonal** (Blender 5): `Triangulate.Quad Method` is a MENU INPUT
SOCKET — two sequential Triangulate nodes with complementary selections, `"Fixed"` and
`"Fixed Alternate"`. Decide per cell with randoms stored as FACE attrs *before* the first
pass, so both halves of a split cell keep them.

**Grid sizing.** Measure the surface extent along the in-plane basis vectors with
`AttributeStatistic(FLOAT, POINT)` of `dot(pos-center, T)`; always clamp the resulting
vertex counts (`MINIMUM 400`) or a small Tile Size freezes Blender.

#### Giving the Shatter partition the grid's per-tile wobble (GN_Mosaic v7)

Each shattered tile is its own mesh island, so the grid's whole variation stage ports
straight across: `MeshIsland.Island Index` as the group for three `AccumulateField`s
(count, ΣP, ΣP²) gives the tile's centroid and rms radius, the island index doubles as
the `ID` for the `RandomValue` nodes, and you rotate/scale/slide about that centroid.
Run it AFTER the cull so the fit, band and grout tests still see the untouched partition.

Three things that are NOT obvious:

1. **Scale the SLIDE by the grout — but do not do the same to the rotation.**
   Position offset = `Gap*0.5*Jitter` is exactly right: it cannot make tiles collide, and
   at Gap 0 it is identically zero so "100% coverage at zero grout" still holds no matter
   how high the user pushes it. Applying the same reasoning to rotation (cap the angle at
   `(Gap*0.5)/rms`, since Shatter mixes sizes and a big tessera sweeps its corners further)
   was a MISTAKE that shipped and was reported within the hour as "rotation jitter doesnt
   work". Measured: asked 11.5° and 28.6° on a coarse break-up, got 6.5° both times — and
   at Gap 0 the cap is zero, so the control did nothing whatsoever. **A safety clamp that
   silently stops a control from responding reads as a broken feature.** Deliver the angle
   asked for, let tiles overlap at high values (the grid's own Rotation Jitter does), and
   put the trade-off in the tooltip. Diagnose this class of bug by measuring the DELIVERED
   quantity in the user's units — angle between a tile's first edge before and after, in
   degrees, swept across the input range — not "did any vertex move".
2. **A seam test must run on the PRE-INSET corner.** `seam_vert` on the final position
   finds nothing: by then the grout inset has already pulled the seam vertex `Gap/2` off
   the bounds-box face, so `|p_k| > half - 1e-4` is false for every one of them (measured:
   60 seam vertices, all missed, all still moving). Evaluate the test on the corner value
   feeding the inset, `FieldOnDomain(CORNER→POINT)` it, and **store it as a named attr** —
   the variation stage is on the far side of a `DeleteGeometry`, so a field cannot reach it.
3. **Tiles on a seam must sit the wobble out entirely.** Under `Tileable` the tile across
   the box is a DIFFERENT shape, so there is no rigid motion the two could share and no
   wrapped-coordinate trick that helps (same reason mirroring split *positions* failed).
   "Any vertex of this island is on a seam" = `AccumulateField(seam-as-FLOAT, Group=island)
   > 0.5`. Costs a ring of unwobbled tiles around the repeat; document it.

**Do not judge a Shatter render by eye without checking the settings first.** Shatter only
ever SUBDIVIDES the region's own faces, so `Tile Size` larger than the input's face size
is a no-op ceiling, and a `Gap` that is a large fraction of the resulting seed-sized tiles
gets most of them dropped as all-grout (a tile with no room for its own grout is nothing
but grout). A demo at Tile Size 0.22 / Gap 0.03 on a 0.1-face mesh rendered as a sparse
band hugging the outline — which looks exactly like a broken region fill, and is not.
Sanity-check with total tile area vs surface area before debugging the graph.

#### Turning a single value into a `min .. max` range (GN_Mosaic v8)

Pattern that keeps it backward compatible: add only the MAX socket, default 0, and take
`hi = MAXIMUM(base, base_Max)`. Anything at or below the base collapses the range to the
base, so 0 means "no range" and the tool reproduces its old output exactly — worth an
explicit regression check (`every Max at 0 → the same tile count as the baseline`).

**Key the draw on the right element, or the result is subtly wrong:**
- per TILE → `RandomValue` with `ID` = the tile id (or island index).
- per EDGE → **`ShaderNodeTexWhiteNoise` on the edge MIDPOINT**, never a tile id. Each of
  the two tiles sharing a joint insets its own corners using its own copy of that edge, so
  a tile-keyed draw makes them disagree and the joint comes out wedge-shaped. Both compute
  the same midpoint, so a position-keyed draw makes them agree automatically. Under
  Tileable, run the midpoint through `wrapped_mid` first so an edge on the +face and its
  partner on the -face draw the same width.
- in a Repeat Zone (Shatter's splitter) → draw the target size INSIDE the zone keyed on the
  element index, so the range changes how far each piece is broken down. Applying it after
  the fact would only scale a uniform field.

**Measuring a grout width in a test.** Tiles own their vertices outright, so the two sides
of a joint are two separate edges: collect every edge midpoint with its face index, bucket
them on a grid COARSER than the joint (a finer bucket puts the two sides in different cells
and finds nothing), and take the nearest midpoint belonging to a different face. Report
QUARTILES, not min/max — an edge whose neighbour was dropped as all-grout has no partner,
so its "nearest" is a whole tile away and wrecks the extremes.

<a id="project_gn_ambient_occlusion"></a>

## Shared GNG_AmbientOcclusion core

*GN_AmbientOcclusion — the ST3E raycast AO tool and the SHARED GNG_AmbientOcclusion core that GN_VertexDataComposer links*

Built 2026-09-20. `Blender/Geonodes/GN_AmbientOcclusion.blend` ships two groups:

- **`GNG_AmbientOcclusion`** — the reusable sampling core, and the single source of
  truth for occlusion in the library. Geometry in → geometry out **plus an
  "Ambient Occlusion" float field**. Other .blend files **LINK** it (relative
  `//GN_AmbientOcclusion.blend`), they do not reimplement it.
- **`GN_AmbientOcclusion`** — the modifier wrapper: occluder object/collection,
  shaping (auto range, input min/max, invert, gamma, strength), blur, and a write
  block targeting a colour attribute, a float attribute, or both, on Point or
  Face Corner.

**Sampling design (the non-obvious part):** a Repeat Zone fires ONE `GeometryNodeRaycast`
`Samples` times. A Repeat Zone cannot carry per-element field state
([Geonode nodes, fields and domains](nodes-and-fields.md#feedback_gn_edge_to_face_bool_interp)), so the **geometry is the accumulator** —
each iteration reads the cache attribute, adds the hit weight, stores it back. Every
scalar the body needs (distance, spread, bias, jitter, seed, the cache NAME as a STRING
item) enters as its own loop item, and each one must be wired straight through
input→output or it resets every pass. Directions: `u = (k+0.5)/N`,
`cos θ = 1 - u·spread` (uniform) or `sqrt(1 - u·spread)` (cosine), azimuth =
`k · golden angle + per-point random` — the per-point rotation is what stops banding.

**Build / verify / tidy:**
`_build/build_gn_ambient_occlusion.py` → `_build/verify_gn_ambient_occlusion.py`
(41 checks; open plane = 1.0, sealed box = 0.0, all 6 write-target × domain combos) →
`run_pipeline.py -- GN_AmbientOcclusion`.

**GN_VertexDataComposer now links it**: its old inline 5-ray chain is gone, the
"Ambient Occlusion" source runs through a group node, and a new `Occlusion Samples`
socket was added (socket count 528 → 529, the verifier's F4 constant was updated).
The disabled branch stores a constant 1.0 and is picked by a lazy `Switch(GEOMETRY)`,
so turning the pass off skips the group entirely instead of just zeroing it.

Gotchas hit while building it, each with its own memory: blur is a no-op on CORNER
([Geonode nodes, fields and domains](nodes-and-fields.md#feedback_gn_blur_attribute_corner_noop)), demo scenes ship the factory Cube
([Geonode asset files](asset-files.md#feedback_geonode_demo_scene_hygiene) — both this file and VDC now delete all
startup meshes), new interface sockets backfill zero so `Samples` is clamped in-graph
([Geonode sockets, interfaces and menus](sockets-and-menus.md#feedback_gn_new_socket_backfills_zero)). Also fixed `tidy_layout.process_file`,
which crashed on a demo object carrying a non-NODES modifier (`md.node_group` on a
Subsurf). Roster/publish checklist: [ST3E geonode modifier — build recipe, roster, publish checklist](asset-checklist.md).
