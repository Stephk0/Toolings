# Export Lab — spec

A test bench for Mass Collection Exporter. Blender exports a fixed scene through every
combination of export modes, and a three.js page loads every file that came out and checks it
against an independent model of what the exporter promises (the *oracle*). The page is the
place to look at the results: the three assets lined up, their file names, formats and folders,
and a pass/fail for every case.

| File | Role |
|------|------|
| `build_scene.py` | Builds `assets/export_lab/MassExporter_ExportLab.blend` (stone, plant, tree, stage) |
| `run_matrix.py` | Runs every case through the real addon, writes `manifest.json`, `scene.json`, `cases/` |
| `viewer/oracle.js` | The expected result of a case, from this spec. No Blender, no addon code |
| `viewer/checks.js` | Loads one exported file with three.js and compares it with the oracle |
| `viewer/index.html`, `viewer/app.js` | The Export Lab page |
| `serve.py` | Serves a run folder with correct MIME types (`http.server` on Windows sends .js as text/plain) |

```bash
B="C:/Program Files/Blender Foundation/Blender 5.0/blender.exe"
"$B" -b --factory-startup --python build_scene.py -- ../../__init__.py ../../../assets/export_lab/MassExporter_ExportLab.blend [preview.png]
"$B" -b --factory-startup --python run_matrix.py  -- ../../__init__.py ../../../assets/export_lab/MassExporter_ExportLab.blend <out_dir> [id_filter]
python serve.py <out_dir> 8000               # open http://localhost:8000, press "Run all checks"
```

## 1. The scene

```
Nature                       parent collection, never exported by the house setup itself
  Stone                      SM_Stone (Displace x2, hidden Decimate), SM_Stone_COL
  Plant                      SM_Plant (empty) > Pot (Solidify, Bevel, hidden Weighted Normal)
                                              Pot > Soil
                                              Pot > Stem > Leaves (Subdivision, Solidify)
                                              SM_Plant_COL
  Tree                       SM_Tree (empty, rotated 15°) > Trunk (hidden Subdivision) > Canopy (Displace)
                                                           SM_Tree_COL
  Extras  (eye off)          SM_Pebble
Stage                        floor, LabCam, LightRig + LKey/LFill/LRim (geonode icon rig)
```

Every asset sits off the world origin. Every modifier stack has one modifier switched off in
the viewport (and render). `_COL` meshes have no material and display as wire. The
`Extras` collection is hidden with the outliner eye. Material names carry no `M_` prefix, so
*Add M_ Prefix* is visible in the files.

The saved file holds the **house setup**: one row per asset (`Stone`, `Plant`, `Tree`), each
into its own folder `Exports/<asset>/`, *Group by Suffix* on with `_COL` and `_LOD1`, FBX,
Apply Modifiers and Only Visible Modifiers on. The `Nature` row is present but switched off.

## 2. Cases

**Matrix A — modes.** The six per-collection mode switches

| bit | switch | UI label |
|---|---|---|
| W | `export_as_single_fbx` | Whole Collection as One File |
| S | `use_suffix_grouping` | Group by Suffix |
| C | `export_subcollections_as_single` | Sub-Collections as Single |
| E | `use_empty_origins` | Use Parent Empties |
| J | `join_empty_children` | Join Empty Children |
| M | `merge_to_single` | Merge |

in all 64 combinations × 3 formats (FBX, OBJ, glTF) × 2 row layouts:

- `parent` — one row `Nature` into `Nature/`
- `assets` — rows `Stone`, `Plant`, `Tree` into `Stone/`, `Plant/`, `Tree/`

Case id: `<layout>-<ext>-<WSCEJM bits>`, e.g. `assets-fbx-010000`. 384 cases.

**Matrix B — options.** One option flipped at a time on top of each distinct mode (individual,
merge, suffix, subcoll, empties, join, whole, subcoll+join), glTF (FBX for the FBX options),
`parent` layout. Case id
`opt-<option>-<mode>`.

| option | flips |
|---|---|
| `apply_modifiers_off` | global Apply Modifiers off |
| `only_visible_off` | global Only Visible Modifiers off |
| `move_to_center_off` | row Move to Center off |
| `apply_transforms_on` | global Apply Transforms on |
| `m_prefix_on` | Add M_ Prefix on |
| `materials_overwrite` | Materials: Overwrite, material `M_Override` |
| `materials_fill_empty` | Materials: Fill Empty, material `M_Override` |
| `export_hidden_off` | Export Hidden Collections off |
| `suffixes_all_disabled` | every suffix in the list unticked (suffix mode only) |
| `custom_name` | Custom Filename `Nature_Pack` (whole mode only) |
| `relative_path` | export path `//ExportLab_relative_<id>/<row>/` (individual, whole) |
| `fbx_apply_transform_on` / `_off` | FBX with Apply Transform (`bake_space_transform`) at the default (on) / off |
| `fbx_<bake\|nobake>_<none\|units\|all>_<unity\|blender>` | FBX settings sweep on whole, suffix and empties: Apply Transform on/off × Apply Scalings None / FBX Units Scale / FBX All × axes Unity (-Z forward, Y up) / Blender default (Y forward, Z up). 12 settings × 3 modes |

The FBX sweep tests what the engines see. **Unity ground truth:** `unity_dump.py` imports every
FBX of the run into Unity (batch mode, model importer defaults, once with Bake Axis Conversion
off and once on) and writes `unity.json`: every node's transform and world mesh bounds. The page
judges FBX files through `viewer/unity-fbx.js`, a Unity import model on top of three.js
FBXLoader, and checks that model against `unity.json` (R-UNITY).

What the model adds to FBXLoader, both measured against Unity 6000.3:
- **Convert Units** — Unity scales the file by `UnitScaleFactor / 100`; FBXLoader ignores the
  factor (Apply Scalings *None* comes in 100× too big).
- **Axis system** — Unity converts the file's `UpAxis` / `FrontAxis` / `CoordAxis` to its own;
  FBXLoader ignores them (a Z-up file lies on its back). *Bake Axis Conversion* puts the
  conversion into the nodes and turns the result half a turn round Y.
- Unity is left-handed; the page shows Unity's space with x mirrored (its right-handed view).

Stock FBXLoader matches Unity for 205 of the 366 FBX meshes of a run, the model for all 366
(1 cm). The importer is a switch in the viewport (Unity / three.js FBXLoader).

Findings (Unity 6000.3, the sweep):
- Blender's FBX exporter does not support parenting with Apply Transform (closed as "known
  issue", projects.blender.org/blender/blender/issues/70799, blender-addons #65478). The file
  itself is wrong: the canopy (child of the trunk) gets `Lcl Rotation 90,0,0` where it should
  have none. Unity shows the canopy knocked over too.
- Apply Transform on is only correct with Blender's own axes (Y forward, Z up), where it has
  nothing to bake.
- Apply Transform off places every part correctly with every Apply Scalings and both axis
  presets. Node rotations come in upright (no 90° X) only with **Y forward / Z up + Bake Axis
  Conversion**; with -Z / Y every node keeps a 90° X tilt, Bake Axis Conversion or not.

Every case starts from the exporter defaults plus: Apply Modifiers on, Only Visible
Modifiers on, suffixes `_COL` and `_LOD1` enabled.

## 3. Expected result (the oracle)

Rules carry an id; every check in the page reports the rule it tests, so one root cause shows
up as one failing rule, however many cases it touches.

`meshes(X)` = every mesh in collection X and its descendants. When **Export Hidden
Collections** is off, meshes of hidden collections and hidden objects are left out
(R-HIDDEN-SUB).

**R-HIDDEN-ROW** — a row whose collection is hidden exports nothing when Export Hidden
Collections is off.

**R-HIDDEN-SUB** — "Hidden collections/objects ARE exported by default … disable it to skip
them." With the toggle off, a hidden sub-collection of an exported row is skipped too.

**R-PRIORITY** — the first switch that applies decides the mode:
Whole → Suffix (needs at least one enabled suffix) → Sub-Collections → Empties → Merge →
Individual. Join only matters inside Empties (and Sub-Collections + Empties).

**R-WHOLE** — one file `<Custom Filename or collection>`; it holds `meshes(C)` with their
hierarchy (empties included).

**R-SUFFIX** — one file per group, named after the group's base name (the name without its
suffix). Each mesh joins exactly one group, claimed in this order:
1. members of an empty that sits directly in C → the empty's base name
2. the remaining meshes of each direct sub-collection → the sub-collection's base name
3. the remaining direct meshes → their own base name

A mesh belongs to its nearest empty ancestor (grandchildren included).

**R-SUBCOLL** — direct meshes of C → `<C>_main`; then each direct sub-collection S → `<S>`
with `meshes(S)`. With Empties + Join on, each S follows R-JOIN instead.

**R-EMPTIES** — a parent empty is an asset: one file per empty, named after the empty,
holding its members as separate elements with their hierarchy. Meshes under no empty: Merge
on → `<C>` with all of them, off → one file each.

**R-JOIN** — Empties + Join: one file per empty, named after it, with a single mesh named
after the empty made of its members, origin at the empty. Loose meshes as in R-EMPTIES.
Sub-Collections + Empties + Join, on each sub-collection S: if S holds no empty with mesh
members, fall back to Merge / Individual; otherwise one file `<S>` with a single mesh `<S>`
made of every member and every loose mesh of S, origin at the first empty.

**R-MERGE** — one file `<C>` holding `meshes(C)`.

**R-INDIVIDUAL** — one file per mesh of `meshes(C)`, named after the mesh.

**R-FOLDER** — every file lands in the export path of the row that produced it, and nowhere
else. No other files are written, except the `.mtl` library beside each `.obj`.

**R-RELATIVE** — a `//` export path is relative to the .blend, as everywhere else in Blender.

Per file:

**R-NODES** — the file holds a node for every expected mesh and no node named after any other
mesh of the scene. (A joined file holds one mesh node named `<X>`.)

**R-TRIS** — triangle count of the file = sum over its meshes of:
modifiers baked when Apply Modifiers is on (only viewport-enabled ones when Only Visible
Modifiers is on, all of them when it is off), base mesh when it is off. Join bakes when Apply
Modifiers (row or global) is on, otherwise drops modifiers.

**R-CENTER** — Move to Center is the only centring option. On, each asset's pivot sits at
the origin: the pivot of a root node is its parent when that parent is an empty outside the
file (the asset's empty), otherwise the root itself. Roots under the same empty keep their
offsets from it; several pivots stack at the origin. Apply Transforms keeps the centring and
bakes it (roots at 0). Off: every root keeps its distance from the world origin. Not checked
for OBJ (OBJ has no object transforms).

**R-PLACEMENT** — in a file with several meshes, each mesh's bounding-box centre, measured from
the centre of all of them, matches Blender (Y-up converted). Catches parts that are moved or
rotated against each other, which root checks cannot see.

**R-MATERIALS** — Materials: Keep → the source names; Overwrite → every mesh uses
`M_Override`; Fill Empty → the `_COL` meshes (no material) use `M_Override` and the rest keep
theirs, also inside a joined mesh. Add M_ Prefix makes every name start with `M_`.

Per case:

**R-RUN** — the operator finishes and logs no export error.

**R-SELECTION** — the selection after the export is the selection before it, hidden objects
included. (The runner clears the selection before each case, so a leak cannot reach the next
case's files.)

**R-SOURCE** — the scene is identical before and after the export (transforms, parents, mesh
data, modifiers, materials and their names, visibility, collections).

**R-UNITY** — FBX through the Unity importer: per mesh, the page's Unity import model and
Unity's own import (`unity.json`, same Bake Axis Conversion) agree on the world bounds within
1 cm. Skipped when the run has no `unity.json` or the three.js importer is selected.

## 4. The page

- **Line-up** — the selected case's files side by side in a three.js view, grouped by folder,
  each with a label: file name, format, folder, triangle count and its check state.
  Original-scale; the camera frames the line-up. Viewport panels:
  - *Export settings* — the case as exporter settings: rows, format, the six mode switches, an
    option, and the 64-combination mini matrix. Clicking one switches to that case; the camera
    stays, so outcomes compare in place.
  - *View* — FBX importer (Unity model / three.js FBXLoader) and Bake Axis Conversion (both
    re-run the checks), Line-up / As exported (every file at its true position), grid, world
    origin, file origins, node pivots, orientation arrows (green up, blue forward = Unity +Z),
    bounds, file labels, node names, collision meshes, wireframe, expected parts (the oracle's
    boxes, dashed), gizmo size, camera presets.
  - Click a part to read its node: position (and Unity's), rotation, scale, tris, materials.
- **Folder tree** — what was written, with expected-but-missing files and unexpected files
  marked.
- **Checks** — every rule for the case: expected, found, pass/fail.
- **Cases** — filter by matrix, layout, format, effective mode, each W/S/C/E/J/M switch
  (on / off / any) and status; sort by id, mode, file count or failures.
- **Matrix** — the 64 switch combinations as an 8 × 8 grid per layout and format, coloured by
  the effective mode, with the check state on top. Shows at a glance which switches are dead
  under which others.
- **Outcomes** — cases grouped by identical output (same files), so the 384 combinations
  collapse into the handful of results they actually produce.
- **Rules** — failures per rule, with the cases each one touches.
- **Run all checks** loads every file of every case; results can be copied as JSON.
