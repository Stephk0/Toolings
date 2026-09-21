# ST3E geonode icons

Asset-browser previews for the ST3E Geometry Nodes modifiers. Every icon is a
256×256 RGBA render of the same Suzanne, under the same rig, behind the same
frame, so the set reads as one family in the Asset Browser and in the
Add Modifier → ST3E menu.

**Start here if you are picking this up cold.** This file is the whole
contract. `GOTCHAS.md` beside it records the things that cost real time to
find — read that before changing anything visual.

---

## Layout

```
_icons/
  recipes.py       one entry per modifier — what to build, how to prep it, what to expect
  stage.py         studio scene, base meshes, prep steps, effect checker, framing, label
  build_icons.py   STAGE A — render out/<GROUP>.png (never touches the source .blend)
  embed_icons.py   STAGE B — write those PNGs into each .blend as the asset preview
  make_frames.py   regenerates frames/*.png (one per catalog)
  coverage.py      which modifiers still have no recipe / no preview
  recatalog_groups.py  puts the GNG_* helpers on the ST3E/Group catalog
  verify_embed.py  cold-reads every closed .blend and checks the preview landed
  fonts/           vendored Familjen Grotesk (static) + its OFL licence
  frames/          256² catalog overlays: ring, bar, vignette, scrim, inner shadow
  out/             rendered icons + manifest.json
  GOTCHAS.md       hard-won findings; read before changing the look
```

## Running it

Blender 5.0 headless. `--factory-startup` keeps user addons out — some crash
GPU draw handlers in `--background`.

```powershell
$B = "C:\Program Files\Blender Foundation\Blender 5.0\blender.exe"
cd D:\Stephko_Tooling\Toolings\Blender\Geonodes\_icons

& $B --background --factory-startup --python make_frames.py           # frames, after any frame edit
& $B --background --factory-startup --python coverage.py              # what is still missing
& $B --background --factory-startup --python build_icons.py           # all recipes
& $B --background --factory-startup --python build_icons.py -- GN_Twist   # one
& $B --background --factory-startup --python embed_icons.py -- --dry-run
& $B --background --factory-startup --python embed_icons.py           # WRITES the .blends
& $B --background --factory-startup --python verify_embed.py          # cold check, always run this
```

Frames only need regenerating when `make_frames.py` changes; the icons
composite whatever PNG is in `frames/`.

**Stage A is read-only against the library.** Node groups are appended as
**copies** into a throwaway scene, so a recipe may freely mutate them (menu
defaults, for one). **Stage B is the only step that saves**, and it writes
nothing but ID previews.

Always finish with `verify_embed.py`. It reopens each closed `.blend` and
confirms the preview is 256×256, `is_image_custom`, still asset-marked and
non-empty — the only step that proves the previews landed in the files rather
than just in memory. Its group list comes from `recipes.py` so it cannot drift.

## The whole pipeline in one pass

For each recipe, `build_one()`:

1. wipe, build the studio scene (two view layers, see **Layering**)
2. build the base mesh, run `prep` steps, build any `helpers`
3. snapshot the mesh signature and the pre-modifier world bounds
4. append the node group, attach it as a modifier, bind `params`
5. snapshot again → **effect check**. Fail ⇒ no PNG, and any stale PNG is
   deleted
6. optional `ghost_wire`, optional deformation `cage`
7. fit the camera (bbox + reserved bands), place the light rig
8. **recentre**: render once with no overlay, measure the alpha centroid, slide
   the camera so the pixels are centred
9. build the name label on the label view layer
10. compositor `subject → over frame → over label`, render the final PNG

---

## Writing a recipe

```python
"GN_Delete": dict(
    catalog="Modify",                      # picks the frame tint
    short="Delete",                        # name burned over the lower tile
    base="suzanne",                        # suzanne|grid|plane|cylinder|icosphere
    prep=[("subsurf", 1), "shade_smooth",
          ("material_slots", 2),
          ("material_index_by", "half")],  # <- the gotcha handling
    params={"Selection Mode": "Material ID",   # Menu sockets take the ITEM NAME
            "Material ID": 1, "Domain": "Face"},
    ghost_wire="removed",                  # wireframe what the modifier deleted
    expect="verts_down",                   # enforced at build time
),
```

Keys: `file`, `catalog`, `short`, `base`, `base_args`, `prep`, `helpers`,
`params`, `material`, `cage`, `cage_resolution`, `ghost_wire`, `keep_base`,
`wire_only`, `two_sided`, `expect`.

A param value of `("attr", "name")` binds that socket to a mesh **attribute**
instead of a constant — the modifier UI's little spreadsheet toggle. Selection
and boundary sockets want a per-element field, which a constant cannot express.
Pair it with `("bool_attribute", name, domain, mode, bands)` in `prep`.

`hollow` culls the camera-facing surface and lights the cavity from inside,
which is the only way `GN_FlipFaces` has an icon at all — see `GOTCHAS.md`.
`two_sided` is the alternative, rendering backfaces in a warning tint.

`emblem=True` skips the modifier entirely and renders a shared tile — for the
**ST3E/Group** catalog, see below.

`material=("split", "<attr>", hue)` shows one attribute twice, hue-shifted
across a screen-space diagonal: the same data arriving somewhere else.

Helpers can be objects, materials (`kind="material"`) or collections
(`kind="collection"`, with `items=[…]`).

`ghost_wire` modes: `"removed"` (the edges a delete-type modifier took away),
`"all"` (the whole original, e.g. the coarse cage over a Subdivide result),
`"result"` (the evaluated mesh's own edges, for topology operators whose output
looks unchanged until you see its new edge flow).

`keep_base` draws the prepared mesh again unmodified — needed when the modifier
consumes its input, as a scatter does. `wire_only` hides the solid result and
keeps only its wireframe; with `keep_base` and `ghost_wire="result"` that is
what makes `GN_BoundingBox` show Suzanne inside a wire box instead of an
anonymous cube.

A helper can be a material rather than an object:
`dict(name="mat", kind="material", colour=(r, g, b, 1.0))`.

Parameters bind **by socket name**, resolved to identifiers internally. Menu
sockets are special — see `GOTCHAS.md`.

An external object for an Object/Collection socket:

```python
helpers=[dict(name="cutter", base="icosphere",
              base_args={"subdiv": 3, "r": 0.6},
              location=(0.3, -0.7, 0.3))],
params={"Cutter Object": "@cutter", "Operation": "Difference"},
```

Helpers are inputs, not subjects: `hide_render` is on and they are excluded
from the camera fit.

### Workflow for a new batch

1. `coverage.py` → pick the next groups.
2. Probe their real interface first — **never write a recipe from memory or
   from this document's socket names.** Dump `ng.interface.items_tree` plus the
   `GeometryNodeMenuSwitch` item names for each target.
3. Write the recipes, classify each into a prep class, set `expect`.
4. Build. Green on the effect check is necessary, not sufficient — **look at
   every PNG.** The checker proves something changed, not that it reads.
5. Embed, then cold-verify.

## The effect check

Every build evaluates the subject before and after the modifier and compares
vertex count, polygon count and a hash of the vertex positions. The recipe
declares what should happen:

| `expect`            | passes when                                        |
|---------------------|----------------------------------------------------|
| `deform`            | positions changed, vertex count did not            |
| `verts_up`          | vertex count went up                               |
| `verts_down`        | vertex count went down                             |
| `topology` / `any`  | anything measurably changed                        |
| `attribute:<name>`  | that attribute exists after and its values vary    |
| `material`          | the evaluated material slots changed               |
| `instances_up`      | the depsgraph instance count went up               |
| `shading`           | polygon normals, smooth flags or corner normals changed |
| `attribute_added:<name>` | the modifier created that attribute (it may be all zeros) |

`material` and `instances_up` exist because neither shows up in geometry:
assigning a material changes no vertex, and instances are not part of
`to_mesh()` at all — a scatter looks like it *destroyed* the mesh (507 → 0
verts), which `any` would have happily accepted as a pass.

Fail ⇒ **no PNG is written** and the run reports FAIL. This is the point of the
whole thing: many of these modifiers do nothing without specific input, and a
silently unmodified Suzanne is a worse icon than a missing one. Validated
against deliberately broken recipes (Delete with no material indices, Twist at
angle 0, AO writing to an attribute the material does not read) — all rejected.

## The five prep classes

1. **Nothing** — Twist, Bend, Taper, Stretch, Inflate, Smooth, Cast,
   Wave, Displace, Subdivide, Triangulate, Wireframe, ConvexHull, BoundingBox,
   DualMesh, VoxelRemesh, AutoSmooth, FlipFaces, RadialArray, Weld, …
2. **Material slots + per-face `material_index`** — `GN_Delete` (Material ID),
   `GN_ExtrudeFace`, `GN_SetMaterial`, `GN_MaterialOverride`, `GN_SetAttribute`.
   → `("material_slots", n)` then `("material_index_by", "half"|"stripes"|"noise")`.
   Slots are clay-coloured by default so they do not fight the family look;
   pass `{"tint": True}` when the material split is what the icon must show.
3. **External object or collection** — `GN_MeshBoolean` (Cutter Object),
   `GN_NormalTransfer` (Source Object), `GN_Scatter` (Instance Object),
   `GN_CollectionInstancerModel`, `GN_RandomDistribute`, `GN_Mirror*`.
   → `helpers=[…]` + `"@name"` param values.
4. **Named attribute or boundary selection** — `GN_FlattenByBoundary`
   (Boundary Edges), `GN_Mosaic`, `GN_SplitEdgeByAttribute`, `GN_GrowSelection`,
   `GN_RandomizeMeshElements` (Group Attribute).
   → `("attribute", name, domain, type, expr)` / `("mark_open_boundary", axis)`.
5. **Attribute-only output, no geometry change** — `GN_AmbientOcclusion`,
   `GN_SetAttribute`, `GN_AttributeTransfer`, `GN_VertexDataComposer`.
   → `material=("attribute", "<attr>", "color", "emission")` plus
   `expect="attribute:<attr>"`. Unlit emission reproduces the attribute
   exactly; `"clay"` feeds it into the lit Principled instead.

Plus subjects where Suzanne is simply wrong and `base=` changes: Erosion wants
a terrain grid, Mosaic a bounded plane.

---

## The look, and every number behind it

### Camera — `stage.py`

`CAM_ROT = (70°, 0°, 35°)`. In Blender's XYZ euler for a camera, **X is
elevation** (90° = eye level, smaller looks down more steeply), **Z is
azimuth**, **Y is roll** and stays at zero. Position is derived from the fit.

### Framing

`MARGIN 1.06`, `CAGE_MARGIN 1.10`. The fit uses the **union of pre- and
post-modifier bounds** — fitting the result alone makes a modifier that removes
geometry look like a zoom-in, and gives every icon a different scale. The cage
is excluded from the fit but drawn.

`BAR_SAFE` (41px) and `LABEL_SAFE` (62px) reserve the top bar and the bottom
label band; the subject is fitted into what is left and centred in *that* band.

Then `recentre_camera()` renders once with no overlay and slides the camera so
the **alpha centroid** lands on target. Bbox centre ≠ optical centre for
Suzanne — her ears and snout push the box much further than they push the
visible weight.

### Lighting — `LIGHT_SPECS` in `stage.py`

One line per light: `(name, position, energy×, area size, colour)`. Positions
are in **rig space** — centred on the subject, oriented like the camera, +X
right, +Y up, +Z toward the viewer.

Warm key upper-right, cool fill lower-left, small hot rim low and behind on the
left, so the left silhouette (in shadow from the key) takes a hard bright edge.
`LIGHT_ENERGY 140`; distance, area size and energy all scale with the framing
together.

### Frame — `make_frames.py`

Chamfered-square ring, 45° corners at `CHAMFER 17px`, except `SQUARE_CORNERS
("tl",)` which stays square so the bar reads as a tab. `STROKE 3px`, flush with
the image border. `SHADOW_PX 1 / ALPHA 0.5` is a dark line just inside the ring.

Top bar `BAR_H 29.4px`, tint per catalog, `ST3E / <Category>` left-aligned in
Consolas at `TEXT_CAP 12.075px` with a hard black `TEXT_SHADOW_PX 2px` emboss.

Overlays over the content area: radial `VIGNETTE` (128px feather, 0.30), a
bottom `SCRIM` (88px, 0.55) behind the name, and an `INNER_SHADOW` (18px, 0.10)
following the frame outline including the chamfers.

### Name label — `stage.py`

`LABEL_CAP_PX 19.25`, centred `LABEL_BOTTOM_PX 30` above the bottom edge, in
vendored **static** Familjen Grotesk Medium. White, with a `LABEL_OUTLINE_PX
1.3` black halo in eight directions plus a `LABEL_SHADOW_PX 2` drop shadow.

### Layering

The subject must composite **under** the frame and the label **over** it, so
they cannot be the same image. Two view layers — `Subject` and `Label`, each
seeing only its own collection — chained `subject → over frame → over label`.
Still one render call. The label layer is off unless a recipe has a `short`.

---

## Roster status

`coverage.py` prints it live. At the last run: **57 recipes, 0 outstanding** —
49 modifiers plus 8 group emblems.

## ST3E/Group — the helper groups

`GNG_*` groups are asset-marked for reuse in the node editor, not as modifiers.
Most of them **cannot be attached as a modifier at all**: their first interface
input is a Bool, Colour, Vector or Menu, so Blender has no geometry to bind and
the group evaluates to nothing. There is no "effect on Suzanne" to photograph.

They get their own catalog — `ST3E/Group`,
`5d2a7c14-9e3b-4f06-8c72-1b4e6a9d3f58`, slate-blue frame — and a shared
`emblem=True` tile (three linked boxes, `base="nodegraph"`), distinguished by
the name in the label. `recatalog_groups.py` moves them onto that catalog and
clears `is_modifier`/`is_tool`; it is asset-metadata only and gates each save
on evaluated geometry being unchanged.

`GN_Mirror` was renamed **`GNG_Mirror`** and joined them. It was never a usable
modifier — its first input is a Float (`U Scale`), so it emitted zero geometry
under every setting. `GN_MirrorGroup` in the same file is the real modifier.

`GN_VariousTest.blend` is a scratch file and is excluded, so `GNG_MixValues`
(which lives only there) has no recipe.

## One representational icon

`GN_AttributeTransfer` is the only icon that does not photograph its own
output. The node creates the `Color` attribute it targets but writes 0.0 to
every element, across eight parameter sets: `From Attribute` bound to
`position`, to a custom `FLOAT`, and to a custom `FLOAT_COLOR` whose source
demonstrably varies (0.0–1.33); `Selected Groups` both ways; presets `Color`
and `Custom`; `Replace` at amount 1.0; `Adjust Base Attribute` 1.0. It appears
`From Attribute` is not a value input in that sense — it belongs to the
Higgsas attribute-*group* system, so a working recipe probably needs a prep
that establishes a named attribute group first.

The icon therefore shows a convexity map authored in `prep`, split on a
screen-space diagonal with the far half hue-shifted — the same attribute
arriving somewhere else. Its gate asserts only what the node verifiably does,
which is create the attribute (`expect="attribute_added:Color"`). If someone
works out the real parameters, swap the material for
`("attribute", "Color", …)` and the expect back to `attribute:Color`.

## Known weak spot

`GN_AmbientOcclusion` on Suzanne: mostly convex, so the AO map is nearly white
and the recipe pushes `Input Min` to 0.88 to make the occlusion read at all. A
concave subject would show it properly, at the cost of family consistency.
