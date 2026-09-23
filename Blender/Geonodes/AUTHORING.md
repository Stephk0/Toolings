# Authoring ST3E Geometry Nodes

How modifiers in this folder are built, published and illustrated. The user-facing reference is
[README.md](README.md); AI-agent work rules are in [CLAUDE.md](CLAUDE.md).

Before building anything, read the [geonode asset checklist](../Knowledge/geonodes/asset-checklist.md)
(build recipe, roster, publish checklist) and the layout criteria in
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

## Selection and Invert Selection

Every modifier that gates on a selection carries an **Invert Selection** toggle directly beneath
`Selection`, in the same panel. The gate is `Selection XOR Invert Selection`: off, it is an exact
passthrough (byte-identical output). Inverting a `Selection` left at its `True` default
deselects everything, which is the correct no-op.

Modifiers with the pair: `GN_Inflate`, `GN_Twist`, `GN_Taper`, `GN_Stretch`, `GN_Bend`,
`GN_Wave`, `GN_Cast`, `GN_Smooth`, `GN_Displace`, `GN_RandomizePosition`,
`GN_RandomizeMeshElements`, `GN_ShearGeometry`, `GN_FlattenByBoundary`,
`GN_SimpleTransformMesh`, `GN_Triangulate`, `GN_PointsToSpheres`, `GN_Scatter`, `GN_Mosaic`,
`GN_FlipFaces`, `GN_SetMaterial`, `GN_Weld`, `GN_ExtrudeFace`, `GN_MirrorGroup`,
`GN_AmbientOcclusion`, `GN_VertexDataComposer`, `GN_AttributeTransfer`, `GN_QuadCap` — plus
`GN_Delete`, `GN_SetAttribute` and `GN_NormalTransfer` (`Invert Mask`), which already had one.

Nine gained the whole gate (a `Selection` defaulting to on, plus its invert) where they
previously acted on everything: `GN_AutoSmooth`, `GN_Wireframe`, `GN_ConvexHull` and
`GN_BoundingBox` (hull / box of the selected part, via a `Separate Geometry`),
`GN_NoiseDisplace`, `GN_VoronoiDisplace`, `GN_Erosion`, `GN_Erosion_3D` and
`GN_RandomDistribute`. Blender backfills a new input on an existing modifier with the type's
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

1. Add a recipe to `_icons/recipes.py`.
2. Run `build_icons.py`, then `embed_icons.py` for it.
3. Run `python _icons/readme_tables.py` to refresh the icon column in the README tables.
4. Run `python _icons/gallery.py` to rewrite the gallery between the
   `<!-- icon-gallery:start/end -->` markers in the README. Never edit that block by hand.

`_icons/coverage.py` lists which modifiers still need an icon.

## Layout tooling

The deterministic wire-routing / tidy engine (`tidy_layout.py`, formerly
`geonode_route_tidy.py`), the `layout_audit.py` rules checker, and the `run_pipeline.py`
orchestrator (tidy → verify → save) live in
[`../Addons/LLMGeonodePipeline/`](../Addons/LLMGeonodePipeline/README.md).

## Files that are not assets

- `SHG_TileableNoise.blend` holds the tileable-noise helpers that `GN_NoiseDisplace` links.
- `GN_VariousTest.blend` is a scratch/test file — ignore it.
