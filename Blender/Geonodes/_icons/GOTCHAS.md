# Icon pipeline — findings

Everything here cost real time to discover. Read it before changing the look
or porting this to another library.

## Blender 5 API

**The compositor is a node group, not `Scene.node_tree`.** `Scene.node_tree`
and the `Composite` node are gone. Build a `CompositorNodeTree`, terminate it
with a `NodeGroupOutput`, and assign it to `scene.compositing_node_group`.
`AlphaOver` inputs are named `Background` / `Foreground` / `Factor` /
`Straight Alpha`.

**Asset previews are writable and they survive a save.**
`bpy.ops.ed.lib_id_load_custom_preview(filepath=…)` under
`bpy.context.temp_override(id=node_group)` stores 256×256 with
`is_image_custom = True`. `preview_ensure()` + `image_pixels_float` works too
if you want to bypass the operator.

**A menu socket cannot be set as a modifier override from Python.** The integer
a modifier stores for a `NodeSocketMenu` is a value id that is not exposed
through the RNA — `enum_items` only gives `name` and `description`. `set_params`
therefore writes the **item name** onto the appended group's interface default
and deletes the modifier override. Safe only because stage A works on a
throwaway copy. Blender logs `WARNING … Missing property for input socket "X"`
for every such socket; that is expected and benign.

**`modifiers.new()` + later param writes need `obj.update_tag()`.** Setting an
ID property on a Nodes modifier after the first evaluation does not necessarily
re-trigger the depsgraph on its own.

**`libraries.load(..., assets_only=True)` mutates the list you pass.** After the
`with` block, the names list has been replaced in place by datablocks. Copy it
first or you will call `bpy.data.node_groups.get(<GeometryNodeTree>)`.

## Headless rendering

**EEVEE is not dependable in `--background`.** It goes through the GPU driver
and segfaults in `nvoglv64` partway through a batch — including on probes that
had passed unchanged minutes earlier. It also **cannot render a lightless scene
at all** in background mode, which is what killed the frame scene (pure
emission, no lights). Both stages render with **Cycles on CPU**, which is
driver-independent; a 256px icon still costs well under a second.

**Stacked transparent overlays need samples.** The frame composites four
Transparent-BSDF mix layers (vignette, scrim, inner shadow, ring). At 16
samples the gradients dither visibly; 512 is clean and still fast at 256px.

## Geometry

**Loose edges do not render.** The ST3E deformers' "Show Deformation Preview"
emits its cage as loose edges joined into the output — invisible to any
renderer. `build_cage` extracts them (delete faces with `context='FACES'`,
which takes their verts and edges with them and leaves the loose preview
behind), converts to a curve and bevels them into tubes. `FACES_ONLY` is the
opposite: it drops the faces and **keeps** their verts and edges, which is what
`build_ghost_wire` needs.

**Build the cage after the effect check.** It adds geometry and would break an
`expect="deform"` vertex-count assertion.

**Thin emissive tubes wash out.** Antialiasing lifts a ~1px tube several stops;
`0.07` linear still rendered mid-grey. The ghost wire needs `~0.015` to read as
near-black.

## Framing and lighting

**Bbox centre is not optical centre.** Suzanne's ears and snout push her
bounding box much further than they push her visible weight, so a bbox fit
lands her consistently left. The fix is to measure, not estimate: render once
with no overlay and take the **alpha-weighted centroid**, then slide the
camera. Do it before building the label so the text cannot skew it.

**Fit the union of pre- and post-modifier bounds.** Fitting the result alone
makes a deletion look like a zoom-in and gives every icon a different scale.

**Anchor the light rig to the subject, not the camera.** The camera sits four
framings away, so a light at camera-local `-Z` is still in *front* of the
subject and produces a frontal hotspot rather than a rim. No amount of tuning
the rim fixes this; the parent is wrong.

**Scale distance with the framing, not just energy.** Energy ∝ `scale²` with
the lights standing still makes a large subject render brighter than a small
one. Move the rig out by `scale` too and irradiance stays flat. (The old
`LIGHT_ENERGY = 280` was compensating for this bug; the correct value is 140.)

## Type and overlays

**Familjen Grotesk: use the STATIC build.** Blender fills the capital **A** of
the variable build (`FamiljenGrotesk[wght].ttf`, the one Google Fonts ships) as
a solid triangle — the leg aperture closes and the counter collapses to a
sliver. Reproducible at 400px, so it is not a small-size artefact. Every other
glyph is fine and the static builds are correct: it is Blender's font-to-curve
conversion choking on the variable outline. Static TTFs come from the upstream
repo (`Familjen-Sthlm/Familjen-Grotesk`, branch `master`, `fonts/ttf/`), not
from google/fonts, which only ships the variable file.

**Size text by a reference capital, not its own bounding box.** A string's bbox
includes whatever ascenders and descenders it happens to contain, so
"Spherify" would come out smaller than "Subdivide". Measure `H` at em size 1.0
and derive the size from that ratio.

**A diagonal drop shadow offset by `d` on both axes is `d·√2` away.** Divide by
√2 so the stated number is the real distance.

**A drop shadow alone will not carry white text over a white subject.** It
needs a halo — eight offset black copies — as well.

**The label must composite above the frame.** Rendering it into the subject
pass puts it *under* the bottom scrim, which washes over it. Subject and label
need separate view layers so the chain can be
`subject → over frame → over label`.

**A "vignette" is radial.** Multiplying separate per-axis falloffs gives four
discrete corner blobs — that is a corner mask. One smoothstep on the radius
from centre gives the soft circular hole. Conversely an *inner shadow* must
follow the frame outline: `min` over only the axis-aligned half-planes
describes a rectangle and ignores the chamfers, so fold the chamfer half-plane
in as another term.

**Clamp a vignette's reach to each axis' half-extent.** A falloff wider than
the half-height starts past the centre and leaves the middle permanently
darkened.

**EEVEE transparency defaults to DITHERED** and speckles at 256px; `BLENDED` is
clean. (Moot now that both stages use Cycles, but it bites in EEVEE.)

## Effect checks that geometry cannot see

**A material assignment changes no vertex** and **instances are not part of
`to_mesh()` at all.** A scatter modifier therefore reports 507 -> 0 verts: it
looks like it *destroyed* the mesh, and `expect="any"` passes on that happily
— a false green. Hence the `material` and `instances_up` expect kinds, which
compare the evaluated material slots and the depsgraph instance count.

**A modifier that consumes its input needs `keep_base`.** GN_Scatter outputs
instances only, so without the host surface drawn again the icon is dots
floating in space.

## Flipped faces are invisible in Cycles

Cycles flips the shading normal toward the viewer for opaque BSDFs, so a
flipped face renders **exactly** like an unflipped one — plain clay gives
GN_FlipFaces no icon at all. Verified, not assumed.

Culling the camera-facing side (Backfacing -> Transparent) does show the far
shell's interior, which is the literal "hollow" read, but that cavity is
enclosed and every rig light is outside it, so on its own it comes out a black
silhouette. Emission alone just lifts it to a flat grey silhouette. What works
is a point light *inside* the mesh, at roughly 1% of the rig's energy — it sits
about one radius from the shell rather than several, so rig-level power
saturates it to white.

## Not every asset-marked group is a modifier

Blender binds the mesh to a node group's **first** interface input, so a group
whose first input is not Geometry cannot work as a modifier — it evaluates to
nothing, silently, whatever else you set. `GN_Mirror` led with a Float
(`U Scale`) and emitted zero verts on every axis including stock defaults;
it is now `GNG_Mirror` on the Group catalog with `is_modifier` cleared. Check
the first input's type before writing a recipe, and before trusting the
`is_modifier` trait.

## Sockets

**A modifier's attribute toggle is a Boolean IDProperty, not an int.**
`md[id + "_use_attribute"] = 1` raises `TypeError: Cannot assign a 'int' value
to the existing 'Socket_N_use_attribute' Boolean IDProperty`. Assign `True`.
The paired key is `md[id + "_attribute_name"]`. This is the only way to feed a
per-element field to a selection or boundary socket.

**Socket names are not unique.** `GN_CollectionInstancer` exposes a Float
"Scale" and a Vector "Scale". Name-based binding silently hit whichever came
first, which is worse than failing, so `set_params` now rejects ambiguous
names outright.

**Menu items can live in a subgroup.** `GN_SplitEdgeByAttribute`'s
"Attribute Preset" has no `MenuSwitch` in the group itself - its items are in
`GNG_SetAttributename`. When a menu's items are not findable, walk the nested
groups before guessing.

**Custom split normals are per-CORNER.** A shading hash built from polygon
normals cannot see them, so `GN_NormalTransfer` reported no change. Include
`mesh.corner_normals` in the hash.

## Instancing

**Put a collection helper's prototypes at the ORIGIN.** An instancer applies
each prototype's own transform, so parking them off-screen to keep them out of
shot smears the instanced grid across that offset — `GN_CollectionInstancer`
came out as a thin line of specks with `ortho_scale` 19-36 instead of a 3x3
grid at 2.95. `hide_render` is enough to keep a prototype out of the frame;
moving it is not needed and is actively wrong.

## Process

**A failed recipe used to ship a stale icon.** `embed_icons` reported 13/13
while only 12 had built, because the failure left the previous run's PNG on
disk. `build_icons` now deletes its output when a recipe fails. Do not remove
that.

**The source `.blend`s get deleted too, not just edited.** Twice now a recipe
"went missing" and it was the underlying file being removed upstream:
`GN_DeleteStrayGeometry` folded into `GN_Delete`, `GN_Spherify` into `GN_Cast`
(Shape=Sphere). The recipe then fails with `OSError: failed to open blend
file`. Check `git status` before assuming it was your own edit — and note that
`git status -- '<dir>/*.blend'` **silently omits deleted files**, because the
glob only expands over what exists. Query the path directly.

**Do not splice `recipes.py` by string index.** Both "lost recipe" incidents
were compounded by `s.index(...)` spans swallowing a neighbouring entry. Anchor
on a unique marker, and assert the recipe count and key set before and after
any bulk edit. `coverage.py` now flags a rendered PNG with no recipe, which is
the unambiguous signature of this.

**Socket renames land mid-batch.** `GN_ExtrudeFace`'s misspelled
`Select bv Material Index` became `Select by Material Index` between two runs
of the same recipe. This is normal; `set_params` naming the missing socket is
what makes it a ten-second fix.

**The source `.blend`s change under you.** `GN_Wave` gained `Ripple X/Y/Z` and
`Affect X/Y/Z` mid-session; `GN_Delete` renamed `On Domain` → `Domain` and
absorbed the stray-geometry options. **Always re-probe a group's interface
before writing or re-running a recipe** rather than trusting recorded socket
names. A rename surfaces as
`KeyError: no such input socket(s) ['…']` from `set_params`.

**Green is necessary, not sufficient.** The effect check proves something
changed, not that the icon reads. Several recipes passed on the first build and
were still unusable: GN_MeshBoolean's cutter took two sweeps (a cutter buried
in the mesh leaves an interior cavity whose flat-shaded far wall reads as a
*bulge*; it has to bite the silhouette), GN_Delete's "half" mode deleted the
half facing the camera and looked like a smooth blob, and the stray-geometry
passes' loose edges (then their own modifier, now GN_Delete's Stray Geometry
panel) rendered as hairlines that read as render
artefacts until the prep also scattered small floating triangles. Look at every
PNG.

**Helper placement is a visual parameter, not a geometric one.** Sweep it and
look; do not calculate it.
