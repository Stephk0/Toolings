# Export pipeline

Rules and traps for exporters (MassExporter, QuickAnimationExport, any future one).

> Migrated verbatim from Claude auto-memory on 2026-09-22. Dates and version numbers are from when each note was written — trust the code when they disagree.

- [Exporters must leave source data untouched](#feedback_blender_exporter_no_source_mutation)
- [Hidden objects are silently excluded from exporters](#feedback_blender_hidden_objects_export)
- [Never write .exclude on the master LayerCollection](#feedback_blender_master_layercollection_exclude)
- [modifier_apply bakes show_viewport=False modifiers](#feedback_blender_modifier_apply_ignores_show_viewport)
- [Imported rock FBX: clear custom split normals + shade smooth](#feedback_blender_fbx_rock_normals)

<a id="feedback_blender_exporter_no_source_mutation"></a>

## Exporters must leave source data untouched

*For any Blender exporter in this repo, source data must be untouched after export — destructive ops go on temporary duplicates and any in-place mutation must be unconditionally restored in finally*

Blender export addons in this repo (Mass Collection Exporter and any future ones) must guarantee that the user's source scene is byte-for-byte identical after an export. No leftover mesh transforms, no shifted pivots, no moved locations.

**Why:** The user discovered apply_transforms + export_at_origin corrupting source data — meshes baked at (0,0,0) and never moved back. They stated explicitly: "we need to avoid ANY alteration of the source data. what ever we do for export make sure we undo it once it was exported." This is a durable rule for the export pipeline, not a one-off fix.

**How to apply:**
- Destructive bpy ops (transform_apply, modifier_apply, anything that rewrites mesh vertex data or removes data) must run on temporary duplicates. The duplicate-and-rename pattern is established by `_apply_modifiers_to_selection` / `_cleanup_modifier_copies` in MassExporter; mirror it (see `_apply_transforms_via_duplicates` added in v13.5.3).
- Reversible mutations (e.g. setting `obj.location = (0,0,0)` for export_at_origin) require a snapshot up front and an UNCONDITIONAL restore in `finally`. Never gate the restore on the option being off — combining options previously skipped restores and that's exactly how the apply_transforms × export_at_origin bug shipped.
- When testing a new export option, mentally walk through: "what state did I change, and is every change reverted on every exit path (success, exception, early return)?"
- See [Addon architecture and release](addon-architecture.md#feedback_blender_addon_always_zip) for packaging after the fix.

<a id="feedback_blender_hidden_objects_export"></a>

## Hidden objects are silently excluded from exporters

*Hidden objects (hide_viewport or hide_get) are silently excluded from Blender exporters — always unhide temporarily before export and restore after*

Hidden objects are silently skipped by Blender's exporters (FBX, OBJ, DAE, GLTF).

**Why:** Blender has multiple independent visibility layers — object-level `hide_viewport`, view layer eye toggle `hide_get()`, and collection-level visibility. An object hidden via any of these cannot be selected or exported. Critically, clearing `hide_viewport` and `hide_set(False)` is NOT enough if the object is nested inside a hidden or excluded collection — collection visibility takes priority.

**How to apply:** The only reliable way to force-include an object in an export is to temporarily link it to `bpy.context.scene.collection` (the root collection), which is always visible and never excluded:
1. Store original state: `hide_viewport`, `hide_get()`, whether already in root collection
2. `scene.collection.objects.link(rig)` if not already there
3. `obj.hide_viewport = False`, `obj.hide_set(False)`
4. Select the object
5. Export
6. Restore in a `finally` block: unlink from root if we added it, restore hide flags

Do NOT try to walk and unhide parent layer collections — it is complex and fragile. The root collection link approach is simpler and bulletproof.

<a id="feedback_blender_master_layercollection_exclude"></a>

## Never write .exclude on the master LayerCollection

*Assigning LayerCollection.exclude on the master (scene-root) layer collection cascades a reset of every descendant's exclude across the whole view layer*

On Blender 5.0, assigning `.exclude` to the **master** (scene-root) LayerCollection — i.e. `bpy.context.view_layer.layer_collection` — **even to its current value** triggers a cascade that resets `exclude=False` on EVERY descendant LayerCollection in the view layer, including collections unrelated to your operation. The master is always effectively included, so this write does nothing useful and only corrupts state.

Confirmed live (MCP): set `lc_parent.exclude=True`; then a loop that does `master.exclude=False` first wiped parent/child back to False before they were even recorded.

Also: `exclude` is **hierarchical**. Setting a descendant's `exclude=False` while an ancestor is excluded force-includes the ancestor. So when restoring a captured set of exclude flags, restore **deepest-first** (reverse capture order), not ancestor-first.

**Why:** This caused Mass Exporter's "Export Hidden Collections" to silently re-include excluded collections after every export (the unhide pipeline destroyed the state it was about to back up). Fixed in MassExporter v13.6.1 (`_unhide_collection_for_export` / `_restore_collection_for_export`).

**How to apply:** In any visibility-isolation / unhide-restore routine that walks LayerCollections: (1) never write `.exclude` on the master layer collection — skip it (still safe to clear its `.hide_viewport` eye); (2) restore `.exclude` flags deepest-first. Relates to [Export pipeline](export-pipeline.md#feedback_blender_exporter_no_source_mutation) and [Export pipeline](export-pipeline.md#feedback_blender_hidden_objects_export).

<a id="feedback_blender_modifier_apply_ignores_show_viewport"></a>

## modifier_apply bakes show_viewport=False modifiers

*bpy.ops.object.modifier_apply bakes modifiers even when show_viewport is False — delete disabled modifiers off a temp copy first to match viewport geometry*

`bpy.ops.object.modifier_apply()` has **no notion of `show_viewport`**. It bakes a modifier
that is switched off in the stack exactly as if it were on. Measured in Blender 5.0 on a cube
with a visible Subsurf(1) + a `show_viewport=False` Array(count=3):

- viewport-evaluated geometry: **26 verts**
- looping `modifier_apply` over `obj.modifiers`: **78 verts** ← the disabled Array got baked

So "apply all modifiers before export" silently ships geometry the user never saw. Note this is
the opposite direction from [Export pipeline](export-pipeline.md#feedback_blender_hidden_objects_export) (hidden *objects* are
silently *excluded*); hidden *modifiers* are silently *included*.

**Why:** `modifier_apply` evaluates the single modifier directly via
`BKE_mesh_create_derived_for_modifier`, bypassing the depsgraph's viewport-visibility gating.
The FBX/OBJ exporters' own `use_mesh_modifiers` path *does* respect it — only the manual apply
operator doesn't, which makes the discrepancy easy to miss.

**How to apply:** never "skip" the hidden modifier in the apply loop — **delete it from the
temporary copy before applying anything**. Deleting keeps stack order intact, so whatever
follows a stripped modifier evaluates on the previous result, exactly like the viewport:

```python
for mod in list(copy.modifiers):
    if only_visible and not mod.show_viewport:
        copy.modifiers.remove(mod)
for mod in list(copy.modifiers):
    bpy.ops.object.modifier_apply(modifier=mod.name)
```

Two riders:
- If *every* modifier is hidden, skip duplicating the object entirely and export it as-is.
- Exempt Armature modifiers that are preserved for rig binding — stripping a hidden one
  silently unbinds the mesh from its rig in the FBX.

Implemented as the "Only Visible Modifiers" option (default ON) in MassExporter v13.7.0,
`_apply_modifiers_to_selection(..., only_visible=)`. Work on temp copies per
[Export pipeline](export-pipeline.md#feedback_blender_exporter_no_source_mutation).

<a id="feedback_blender_fbx_rock_normals"></a>

## Imported rock FBX: clear custom split normals + shade smooth

*When fixing imported rock FBX meshes in Blender, always clear custom split normals and apply shade smooth as the finishing step — never rely on imported per-loop normals*

For rock / nature-asset FBX cleanup workflows (flipped face fixes, geometry alterations), the finishing step must be:
1. Clear custom split normals (`bpy.ops.mesh.customdata_custom_splitnormals_clear()`)
2. Apply shade smooth on all faces (`bpy.ops.object.shade_smooth()`)

**Why:** FBX import preserves per-loop custom normals from the original DCC tool. When geometry is altered in Blender (face flip, merge, recalc, etc.), the custom normals remain attached to the old loop data and end up smearing or breaking visual shading on the modified regions. The original source authoring did not depend on custom normals — flat geometry + shade smooth was the intended look.

**How to apply:** After any geometry-altering fix (flipping faces, merging verts, recalc outside) but BEFORE exporting back to FBX. Combine with `mesh_smooth_type='OFF'` on export so Blender writes face/vertex normals rather than re-embedding custom split normals.

Related: [Export pipeline](export-pipeline.md#feedback_blender_hidden_objects_export)
