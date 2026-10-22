# Authoring ST3E Geometry Nodes

How modifiers in this folder are built, published and illustrated. The user-facing reference is
[README.md](README.md); AI-agent work rules are in [CLAUDE.md](CLAUDE.md).

Before building anything, read the [geonode asset checklist](../Knowledge/geonodes/asset-checklist.md)
(build recipe, publish traps, catalog UUIDs) and the layout criteria in
[`GEONODE_CRITERIA.md`](../Addons/LLMGeonodePipeline/GEONODE_CRITERIA.md).

## Making a group appear under Add Modifier → ST3E

New modifiers are built headlessly against Blender 5.0. To show up in the menu a group must:

1. Be **marked as an asset** (`node_group.asset_mark()`).
2. Sit on a **leaf ST3E sub-catalog** in `Blender/blender_assets.cats.txt` — `ST3E/Deform`,
   `ST3E/Generate`, `ST3E/Modify` or `ST3E/Scatter & Instancing`. The flat `ST3E` root holds no
   direct assets since the sub-catalog split, so a group left on it lands outside every group in
   the browser.
3. Have a **Geometry input and Geometry output** socket.
4. Have the **Modifier asset trait** on (`node_group.is_modifier = True`).
5. Carry the **`ST3E` tag** (`asset_data.tags.new("ST3E")`).
6. Get an **icon** — see below.

`GN_FillBorder`, `GN_MeshFromImage`, `GN_DisplaceByImage` and `GN_treeGenerator_*` are not
modifier-marked, which is why they only appear in the Asset Browser.

Every modifier also ships a demo object with the modifier attached, has tooltipped sockets and
framed, labelled nodes, and is eval-verified (identity at neutral parameters, no NaN).

## Selection gate (`GNG_SelectionGate`)

Every modifier that gates on a selection routes it through the shared **`GNG_SelectionGate`**
helper group (currently v3) and has a **`Selection` panel** right after `Geometry`, in this
order:

- **Selection** (bool, default **on**).
- **Invert Selection** (bool, default off).
- **Grow / Shrink Selection** (int, default 0) — +N grows by N rings, −N shrinks by N rings
  (shrink = grow the complement), counted in the domain the consumer evaluates on.
- **Select by Material ID** (bool, default **off**), **Selection Material ID** (int, slot index)
  and **Material ID Mode** (menu): *Add* (Selection OR material), *Subtract* (Selection minus
  material), *Intersect*, *Material Minus Selection*. Material faces are found on the FACE domain
  and spread to the consumer's domain — a vertex counts when any adjacent face matches.

**Nothing else may sit top-level.** Blender draws a level's loose sockets before its panels,
whatever the interface order says, so any top-level parameter pushes the Selection panel down
(`move` to index 1 is silently ignored). Every other input goes into a panel — R10 flags
offenders. `_build/patch_gn_selection_panel_first.py` filed the loose inputs of 12 tools into
one panel each (Displace, Weld, Wireframe, …) placed right after Selection.

Order inside the gate: combine with material → invert → grow / shrink. The group is a pure
field (no Geometry socket), sitting in the frame `Selection Gate  (GNG_SelectionGate)`. At
defaults it is an exact passthrough (byte-identical output). Grow runs one `Blur Attribute`
step + `> 0` per repeat iteration, so it is exact for any ring count.

**Menu items keep identifiers 0..3.** A modifier stores a menu override as the item
identifier, and a new input on an existing modifier is backfilled with 0. The builder renames
the Menu Switch's two default items instead of clearing them (clearing starts at 2), so a
backfilled 0 is `Add`. v2 got this wrong and v3 fixed it.

Two follow-on traps, both repaired by `_build/fix_gn_material_mode_backfill.py`:

- The modifier socket's own default is stored as an identifier too. The 40 tools patched under
  v2 kept 2 (v2's `Add`), which v3 reads as `Intersect` — fresh modifiers started there. Never
  renumber menu items without re-setting every consumer's `default_value` by name.
- Adding the menu socket to a group whose modifiers already exist stores **-1** (no item) on
  them, because the socket has no items until it is linked. Set `mod[identifier] = 0` after
  linking. The rollout scripts now do.

Building and extending it:

- The group is built from code by `_build/gng_selection_gate.py` (`ensure()` builds or
  upgrades it in the open file; `VERSION` is stored on the group as `st3e_version`). Every
  tool file holds its own local copy — the same distribution as `GNG_ObjectDirection`.
- New features go into that module: add sockets **after** the existing ones (identifiers are
  matched by name, so existing links and modifier overrides survive), bump `VERSION`, and
  run `_build/upgrade_gng_selection_gate.py` (rebuilds the group in every file, saves only
  when evaluation is unchanged). New gate inputs also need a matching modifier socket — the
  rollout pattern is `_build/patch_gn_selection_gate_v2.py` (declare, file into the
  `Selection` panel, wire, gate on identical evaluation and no worse layout).
- New modifiers: add a `GNG_SelectionGate` node fed by every input of the `Selection` panel
  above, and plug its output into every consumer of the selection.
- `_build/verify_gng_selection_gate.py` checks the group on point, face and curve domains.

Special cases (rollout: `_build/patch_gn_selection_gate_special.py`):

- `GN_ExtrudeFace` — its own grow and material select were renamed `Legacy Selection Expand /
  Contract`, `Legacy Select by Material Index` and `Legacy Selection Material Index` (a rename
  keeps the socket identifier, so older files keep their values). They still work.
- `GN_Delete` keeps its `Selection Mode` menu (Selection Group / Material ID picks the
  *source*); the gate's Select by Material ID adds to or subtracts from that source.
- `GN_SetAttribute` / `GN_Delete` — their invert was `Switch(sel, NOT sel)`; replaced by the gate.
  `GN_Delete` feeds the gate the Selection Group / Material ID menu result.
  `GN_SetAttribute`'s `Expand / Shrink` stays: it grows the *combined* criteria result, later.
- `GN_DistributeObjectOnSurface` keeps `Grow Iterations` beside the gate: its `GN_GrowSelection`
  field is evaluated by `Mesh to Points` on the subdivided surface, so it grows after subdiv.
- `GN_NormalTransfer` keeps its float mask (attribute or open-boundary mask, a Mix factor:
  0 = source normal, 1 = own normal, `Invert Mask` = `1 − mask`); the gate would binarize it.
  The gate sits **beside** it instead: a new boolean `Selection`, evaluated on POINT, picks
  `Switch(sel, mask, 1.0)` as the factor, so unselected corners keep their own normal. Its
  other inputs moved into `Source` and `Mask` panels. Rollout: `_build/patch_gn_selection_gate_new.py`
  (also `GN_InsetFaces`, whose bare `Selection` is read on FACE; its `Offset` went into an
  `Inset` panel).
- `GN_SolidifyExtended` got the material trio and panel through the v2 rollout; its builder
  (`build_gn_solidify_extended.py`) now emits them too.
- Not on the gate, on purpose: `GN_GrowSelection` (a selection utility — it outputs a grown
  selection and has its own domain-aware grow; a gate in front would duplicate it) and
  `GN_MaterialOverride` (`On` / `Invert` is a whole-object switch, not a selection). Tools with
  no selection at all (CellFrac, CollectionInstancerModel, DualMesh, EdgeDestruct, MeshBoolean,
  RadialArray, Solidify2, SpawnObjectsAlong, SplitEdgeByAttribute, Subdivide,
  TileableMeshNoise, VoxelRemesh) were left as they are.

Modifiers with the pair: `GN_Inflate`, `GN_Twist`, `GN_Taper`, `GN_Stretch`, `GN_Bend`,
`GN_Wave`, `GN_Cast`, `GN_Smooth`, `GN_Displace`, `GN_RandomizePosition`,
`GN_RandomizeMeshElements`, `GN_ShearGeometry`, `GN_FlattenByBoundary`,
`GN_SimpleTransformMesh`, `GN_Triangulate`, `GN_PointsToSpheres`, `GN_Scatter`, `GN_Mosaic`,
`GN_FlipFaces`, `GN_SetMaterial`, `GN_Weld`, `GN_ExtrudeFace`, `GN_MirrorGroup`,
`GN_AmbientOcclusion`, `GN_VertexDataComposer`, `GN_AttributeTransfer`, `GN_QuadCap`,
`GN_SolidifyExtended`, `GN_InsetFaces` — plus
`GN_Delete` and `GN_SetAttribute`, which already had one.

Nine gained the whole gate (a `Selection` defaulting to on, plus its invert) where they
previously acted on everything: `GN_AutoSmooth`, `GN_Wireframe`, `GN_ConvexHull` and
`GN_BoundingBox` (hull / box of the selected part, via a `Separate Geometry`),
`GN_NoiseDisplace`, `GN_VoronoiDisplace`, `GN_Erosion`, `GN_Erosion_3D` and
`GN_RandomDistribute` — and later `GN_NormalTransfer` (beside its mask). Blender backfills a new input on an existing modifier with the type's
zero value, not the socket default — see
[sockets & menus](../Knowledge/geonodes/sockets-and-menus.md) — which is why the README warns
users to re-tick `Selection` on those nine.

## Asset Browser icons

Each asset has a 256×256 preview rendered and embedded headlessly by the pipeline in
[`_icons/`](_icons/ICONS.md). Each recipe declares what the modifier should do (deform, add
vertices, change topology, write an attribute…) and no icon is written unless the evaluated mesh
measurably changed. Helper groups get a shared node-graph emblem; shader groups are gated on a
render diff instead. Read [`_icons/ICONS.md`](_icons/ICONS.md) (the contract) and
[`_icons/GOTCHAS.md`](_icons/GOTCHAS.md) (the findings) before changing anything there.

For a new modifier:

1. `python _icons/icon.py probe GN_X` — the real sockets and menu item names.
2. Add a recipe to `_icons/recipes.py`.
3. `python _icons/icon.py build GN_X`, and look at the PNG.
4. `python _icons/icon.py ship GN_X` — embeds, cold-verifies, and rewrites the README gallery
   and icon column (never edit the `<!-- icon-gallery:start/end -->` block by hand).

The `geonode-icons` skill runs this whole flow on request.

`_icons/coverage.py` lists which modifiers still need an icon.

## Layout tooling

The deterministic wire-routing / tidy engine (`tidy_layout.py`, formerly
`geonode_route_tidy.py`), the `layout_audit.py` rules checker, and the `run_pipeline.py`
orchestrator (tidy → verify → save) live in
[`../Addons/LLMGeonodePipeline/`](../Addons/LLMGeonodePipeline/README.md).

## Files that are not assets

- `SHG_TileableNoise.blend` holds the tileable-noise helpers that `GN_NoiseDisplace` links.
- `GN_VariousTest.blend` is a scratch/test file — ignore it.
