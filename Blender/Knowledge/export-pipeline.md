# Export pipeline

Rules and traps for exporters (MassExporter, QuickAnimationExport, any future one).

- [Exporters must leave source data untouched](#feedback_blender_exporter_no_source_mutation)
- [Hidden objects are silently excluded from exporters](#feedback_blender_hidden_objects_export)
- [Never write .exclude on the master LayerCollection](#feedback_blender_master_layercollection_exclude)
- [modifier_apply bakes hidden modifiers and refuses shape keys](#feedback_blender_modifier_apply_ignores_show_viewport)
- [Duplicates that impersonate the original need its name freed first](#feedback_blender_unique_names)
- [Imported rock FBX: clear custom split normals + shade smooth](#feedback_blender_fbx_rock_normals)
- [FBX Apply Transform misplaces children in any hierarchy](#fbx_bake_space_transform_hierarchy)
- [Hidden objects keep their selection flag](#hidden_objects_keep_selection)

<a id="feedback_blender_exporter_no_source_mutation"></a>

## Exporters must leave source data untouched

*Destructive ops run on temporary duplicates; every in-place change is restored unconditionally in `finally`.*

The user's scene must be identical after an export: no baked transforms, shifted pivots,
moved locations, swapped materials or renamed datablocks.

**Why:** `apply_transforms` + `export_at_origin` once baked meshes at (0,0,0) and never moved
them back, because the restore was gated on an option. The user's rule: "avoid ANY
alteration of the source data".

**How to apply:**
- `transform_apply`, modifier baking, anything that rewrites mesh data: on duplicates
  (MassExporter `_apply_modifiers_to_selection` / `_cleanup_modifier_copies`,
  `_apply_transforms_via_duplicates`).
- Reversible changes (`obj.location`, material overrides, name prefixes): snapshot first,
  restore in `finally`, never conditional on the option that caused them.
- Walk every exit path (success, exception, early return) and ask what is still changed.
  MassExporter's `source/tests/headless_export_test.py` checks this for every option.

<a id="feedback_blender_hidden_objects_export"></a>

## Hidden objects are silently excluded from exporters

*Object `hide_viewport`, view-layer `hide_get()` and hidden/excluded collections all keep an object out of FBX/OBJ/glTF; link it to the scene root collection to force it in.*

Clearing `hide_viewport` and `hide_set(False)` is not enough when a parent collection is
hidden or excluded; collection visibility wins.

**How to apply:** store `hide_viewport`, `hide_get()` and whether the object is already in
`scene.collection`; link it to `scene.collection`, unhide, select, export; in `finally`
unlink it if you linked it and restore the flags. Simpler and sturdier than unhiding parent
layer collections.

<a id="feedback_blender_master_layercollection_exclude"></a>

## Never write .exclude on the master LayerCollection

*Assigning `exclude` on `view_layer.layer_collection`, even to its current value, resets `exclude=False` on every descendant.*

Measured on Blender 5.0. The master is always included, so the write is useless and only
destroys state. `exclude` is also hierarchical: clearing it on a descendant force-includes
excluded ancestors.

**Why:** made MassExporter's "Export Hidden Collections" re-include excluded collections
after every export (fixed in 13.6.1, `_unhide_collection_for_export`).

**How to apply:** skip the master when writing `exclude` (its `hide_viewport` is safe), and
restore captured `exclude` flags deepest-first.

<a id="feedback_blender_modifier_apply_ignores_show_viewport"></a>

## modifier_apply bakes hidden modifiers and refuses shape keys

*`bpy.ops.object.modifier_apply` ignores `show_viewport` and fails on meshes with shape keys; bake through the depsgraph instead.*

Measured on 5.0: a cube with Subsurf(1) and a `show_viewport=False` Array(3) evaluates to
26 verts in the viewport, but looping `modifier_apply` gives 78 (the hidden Array is baked).
On a mesh with shape keys it raises "Modifier cannot be applied to a mesh with shape keys",
and a loop that swallows the error drops the modifier silently. The exporters' own
`use_mesh_modifiers` respects `show_viewport`; only the operator does not.

**How to apply:** on the temporary copy, remove the hidden modifiers you don't want
(removal keeps stack order, so later modifiers evaluate like the viewport), force the rest
visible, then bake the whole stack in one go:

```python
dg = context.evaluated_depsgraph_get()
mesh = bpy.data.meshes.new_from_object(obj.evaluated_get(dg),
                                       preserve_all_data_layers=True, depsgraph=dg)
```

Shape keys are baked at their current mix. Keep preserved Armature modifiers out of the
bake (disable during evaluation, keep on the object), or the FBX loses its rig binding.
Reference: MassExporter `_bake_modifiers` (13.8.0).

<a id="feedback_blender_unique_names"></a>

## Duplicates that impersonate the original need its name freed first

*Blender appends .001 to a taken name, so a temp copy exported under the original name comes out as `Name.001`.*

**How to apply:**
```python
original_name = obj.name
obj.name = f"__temp_{original_name}"   # free the name
copy.name = original_name              # copy gets the clean name
# cleanup: delete the copies FIRST, then restore
obj.name = original_name
```
Restoring before the copy is gone re-creates the conflict. Crash recovery should look for
leftover `__temp_` / `__mexport_` names.

<a id="feedback_blender_fbx_rock_normals"></a>

## Imported rock FBX: clear custom split normals + shade smooth

*After altering imported FBX geometry (flip, merge, recalc), the imported per-loop normals smear; clear them and shade smooth.*

**How to apply:** `bpy.ops.mesh.customdata_custom_splitnormals_clear()`, then
`bpy.ops.object.shade_smooth()`, before re-export; export with `mesh_smooth_type='OFF'` so
custom normals aren't re-embedded. The source assets were authored as flat geometry +
smooth shading, not with custom normals.

<a id="fbx_bake_space_transform_hierarchy"></a>

## FBX Apply Transform misplaces children in any hierarchy

*`bake_space_transform=True` is only correct for unparented meshes; a child in any parent chain lands in the wrong place.*

Blender's exporter does not support parenting with Apply Transform (closed as a known issue:
projects.blender.org/blender/blender/issues/70799, blender-addons #65478 / #100325,
developer.blender.org/T97043). In `fbx_utils.py` (`ObjectWrapper.fbx_object_matrix`) an object
whose parent is not exported is written in world space, but its children are corrected with
the parent's Blender `matrix_local` (relative to that unexported parent). When the parent is
rotated or offset the two frames disagree and the child moves. Armatures, cameras and lights
take another code path, so rigs break too.

Measured by importing every file into Unity 6000.3 (MassExporter Export Lab,
`unity_dump.py`; an asset = empty > meshes, a tree = empty rotated 15° > trunk > canopy). The
file itself is wrong with Apply Transform on: the canopy gets `Lcl Rotation 90,0,0` under the
trunk, so Unity knocks it over just like any other importer.

| Apply Transform | Axes (fwd / up) | Placement in Unity | Node rotation, default import | with Bake Axis Conversion |
|---|---|---|---|---|
| on | -Z / Y | **wrong** — canopy on its side, parts of an empty asset off by 0.3–0.8 m | upright | upright |
| on | Y / Z (Blender default) | correct (nothing to bake) | 90° X tilt | upright |
| off | -Z / Y | correct | 90° X tilt | **90° X tilt** |
| off | Y / Z | correct | 90° X tilt | **upright** |

Apply Scalings (None / FBX Units Scale / FBX All) never changes placement in Unity: Convert
Units scales by `UnitScaleFactor / 100`. Bake Axis Conversion turns the asset half a turn round
Y compared with the default import. glTF and OBJ are exact in every case. three.js FBXLoader
ignores both `UnitScaleFactor` and the axis system; the lab's `viewer/unity-fbx.js` adds them
and matches Unity on all 366 meshes.

**How to apply:**
- Unity 2020+: export with Apply Transform **off**, Blender's default axes (**Y forward,
  Z up**), FBX Units Scale, and tick **Bake Axis Conversion** on the model importer: correct
  hierarchy and upright nodes. With -Z / Y the -90° X stays even with Bake Axis Conversion.
  Assets come in turned half a turn round Y compared with the old Apply-Transform setup -
  check facing before switching an existing project.
- Keep Apply Transform only for single unparented static meshes.
- Unreal: Convert Scene / Force Front X Axis on import, FBX All or unit scale 0.01 on export.
  Godot 4.3+ (ufbx) applies unit conversion to the mesh; empties come in at 100× unless FBX
  Units Scale is used (godotengine/godot#90314).
- MassExporter still defaults it to on (user decision, 2026-10-21); the lab's `fbx_*` sweep
  cases (`source/tests/export_lab/`) track it.

<a id="hidden_objects_keep_selection"></a>

## Hidden objects keep their selection flag

*An object selected while unhidden for export stays selected after it is hidden again — and `context.selected_objects` no longer lists it.*

A deselect loop over `context.selected_objects` after re-hiding misses it. The next export
selects the visible objects, and the exporter (`use_selection`) also writes the invisible but
still-selected one.

**How to apply:** record `select_get()` together with the hide flags when unhiding, and put it
back *before* the objects are hidden again (MassExporter `_unhide_collection_for_export` /
`_restore_collection_for_export`).
