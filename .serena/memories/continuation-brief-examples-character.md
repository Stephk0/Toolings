# Continuation Brief — Character example scene: external libs + extracted geonodes

## Context
`Blender/Examples/ST3E_Examples_Character.blend` (Git LFS, zstd-compressed, ~168 MB) is a production
character that uses the ST3E geonode library. On 2026-09-25 its node groups were audited, broken
links repaired, local copies relinked to the library, and three custom groups extracted into
`Blender/Geonodes/`. Everything was done headlessly (Blender 5.0) and gated on the evaluated mesh
of every affected object, with modifiers set to render visibility (topology, vertex positions,
per-face materials, attribute names), before and after.

## Done
- Relinked to the library with every stored modifier value carried over, including attribute bindings (`_use_attribute`/`_attribute_name`):
  - local `GN_MirrorGroup` → `GN_Mirror_Groupable.blend`. Old `Socket_3` (X Axis) is now `Socket_51`, and the old `Material` float (`Socket_50`, 0.0 on both users) no longer exists. Output is identical.
  - local `GN_Delete` (simple 2-socket version) → `GN_Delete.blend`. The stray-geometry passes are turned off on that modifier to keep it identical.
  - local `GN_Push` → `GN_Inflate` on Cube.002/.003/.005: identical output (their amounts are ~-3e-8).
  - local `GN_ExtrudeSelection` (SM_ShoeCroc) and the missing linked `GN_ExtrudeSelection` (BézierCurve.001, SM_Zipper_Buckle, Zipper_Buckle) → `GN_ExtrudeFace`. The socket identifiers were the same, and the old `Selection Type` menu now maps to `Select by Material Index`.
  - missing `GN_MaterialOverride` (it was linked from the old `GN_Instancer.blend`) → `GN_SetMaterial`. `On` became Selection and `Material Override` became Material. The Pants modifier had On=0, so it is now Selection=False, which leaves the mesh unchanged.
- Expected changes: these modifiers were broken before and now evaluate, so their output differs:
  SM_ShoeCroc (the local extrude depended on the missing `G_Smooth Position`, so render output was empty), Zipper_Buckle, BézierCurve.001
  (extrude now applies), and SkinBase_Body_Feet (the socks override now applies: all faces M_Socks).
- Extracted into their own files, asset-marked, tagged ST3E, `is_modifier`, with a `GN_Demo` grid, and relinked into the example:
  `GN_CurveFromSurface` (ST3E/Generate), `GN_SpawnObjectsAlong` and `GN_DistributeObjectOnSurface`
  (ST3E/Scatter & Instancing). Output in the example is identical.
  None has had a layout or criteria pass (geonode-layout-mcp), tooltips, an icon or a proper demo yet.

## Open — external libraries (deliberately left, to be handled as a separate task)
The example links these from outside the repo, so they break on any other machine and in the published library:
- Higgsas `Blender 4.3Higgsas Geo Node Groups v10.blend` (Dropbox): `Mesh Ambient Occlusion` (7 users; the library `GN_AmbientOcclusion` could replace it), `Taper` (used inside GN_SpawnObjectsAlong).
- SolidifyPlus1.1 `SolidifyPlus1.1_VertCreaseFix.blend` (Dropbox): `Solidify Plus (Vert Crease Fix)` on 25 modifiers. Candidate: library `GN_Solidify2`.
- Bradley presets `extensions/user_default/bradley_geo_nodes_presets/Data/5.0/preset.blend`: `G_Curve Deformer` and friends (used by GN_SpawnObjectsAlong and the local `GN_CurveDeform`), plus the `S_*` shader groups.
- **`GN_SpawnObjectsAlong.blend` itself links Higgsas `Taper` and Bradley `G_Curve Deformer` from those absolute paths.** Localize or replace them before publishing the library.

## Open — decisions pending
- Cube.004 still uses a local `GN_Push` (Push Amount -0.01). Push uses the face normal evaluated on the Face domain and interpolated to points; GN_Inflate uses the vertex normal. At -0.01 that changes positions, and a later merge then leaves 512 fewer vertices. Options: add a normal-source option to GN_Inflate as a new socket at the END of the interface (no renumbering), or accept the difference.
- Blender 5.0 `geometry_nodes_essentials.blend` already ships **Curve to Tube** (profile, caps, UV map), **Instance on Elements** (points/edges/faces/corners, scale by face area, corner offsets) and **Array** (curve mode, merge). Compare them against the local `Sweep Curve` / `UV Curve to Mesh` and against GN_DistributeObjectOnSurface / GN_SpawnObjectsAlong before investing in those graphs.
- Local groups that were kept: primitives (Circle/Cone/Cube/Quad Sphere/Torus/UV Sphere + Fix Pivot + Set Material to Index 0), `GN_CurveDeform`, `Smooth by Angle(.001)`, and scratch trees `Geometry Nodes` / `TT-checker-override-uvgrid`.

## Next steps
1. Criteria pass on the three extracted tools (geonode-layout-mcp), then tooltips, a real demo object and an icon.
2. External-library task (above).
3. Decide on the Push/Inflate difference.
