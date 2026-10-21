# Single source of truth for the addon version. bl_info + blender_manifest.toml
# both derive from this; the panel title does NOT show the version. Bump here
# and in blender_manifest.toml only.
VERSION = (13, 9, 0)

bl_info = {
    "name": "Mass Collection Exporter",
    "author": "Claude AI, Stephko",
    "version": VERSION,
    "blender": (4, 2, 0),
    "location": "3D View > N-Panel > Mass Exporter",
    "description": "Batch export collections with modifier apply, rig export, armature options, state-proof visibility isolation (local view / hidden / excluded), suffix grouping, and whole-collection-as-one-file export",
    "category": "Import-Export",
}

import bpy
import os
import mathutils
from bpy.props import (
    StringProperty,
    BoolProperty,
    EnumProperty,
    CollectionProperty,
    PointerProperty,
    IntProperty
)
from bpy.types import (
    Panel,
    Operator,
    PropertyGroup,
    UIList
)
from bpy_extras.io_utils import ExportHelper

# STANDALONE FUNCTION - The core logic extracted so both button and export can use it
# ============================================================================
# Temporary-copy helpers
# ============================================================================
# Every destructive step of an export (modifier bake, transform apply, join)
# runs on throwaway copies made here. Copies are built with Object.copy() +
# data.copy() instead of bpy.ops.object.duplicate so the result does not depend
# on the user's Preferences > Editing > Duplicate Data settings (an unticked
# "Mesh" there makes the operator share mesh data with the source).

_TEMP_TAG = "_mexport_temp"
_TEMP_PREFIXES = ("__mexport_xform_", "__mexport_")


def _local_view_spaces():
    """Every 3D viewport space (in every window) that is in local view."""
    spaces = []
    wm = getattr(bpy.context, 'window_manager', None)
    if wm is None:
        return spaces
    for window in wm.windows:
        for area in window.screen.areas:
            if area.type != 'VIEW_3D':
                continue
            for space in area.spaces:
                if space.type == 'VIEW_3D' and getattr(space, 'local_view', None):
                    spaces.append(space)
    return spaces


def _duplicate_object(obj, temp=True):
    """Copy obj (with its own data) into the same collections and local views.

    temp=True tags the copy so a crashed run can find and delete it later.
    """
    copy = obj.copy()
    if obj.data is not None:
        copy.data = obj.data.copy()
    if temp:
        copy[_TEMP_TAG] = True
    linked = False
    for coll in obj.users_collection:
        try:
            coll.objects.link(copy)
            linked = True
        except RuntimeError:
            pass
    if not linked:
        bpy.context.scene.collection.objects.link(copy)
    for space in _local_view_spaces():
        try:
            if obj.local_view_get(space):
                copy.local_view_set(space, True)
        except (AttributeError, RuntimeError, TypeError):
            pass
    return copy


def _remove_temp_object(obj):
    """Delete a temporary copy and its mesh data when nothing else uses it."""
    try:
        data = obj.data
        bpy.data.objects.remove(obj, do_unlink=True)
    except ReferenceError:
        return
    if isinstance(data, bpy.types.Mesh) and data.users == 0:
        bpy.data.meshes.remove(data)


def _bake_modifiers(context, obj, keep_names=()):
    """Bake obj's modifier stack into a new mesh, keeping `keep_names` live.

    Evaluates through the depsgraph instead of looping modifier_apply:
    modifier_apply refuses meshes with shape keys ("Modifier cannot be applied
    to a mesh with shape keys") and the old loop then dropped the modifier
    silently. The depsgraph bake works with shape keys (they are baked at
    their current mix, as every exporter does once modifiers are applied).
    Modifiers to bake are force-enabled first, so the caller decides which
    hidden ones survive by removing them before calling. Kept modifiers
    (preserved Armature bindings) are disabled during evaluation and stay on
    the object afterwards.
    """
    bake = [m.name for m in obj.modifiers if m.name not in keep_names]
    if not bake or obj.type != 'MESH':
        return
    kept_state = []
    for mod in obj.modifiers:
        if mod.name in keep_names:
            kept_state.append((mod.name, mod.show_viewport))
            mod.show_viewport = False
        else:
            mod.show_viewport = True
    if obj.data.shape_keys:
        print(f"[MassExporter] '{obj.name}': shape keys are baked at their current "
              f"values because modifiers are applied")
    context.view_layer.update()
    depsgraph = context.evaluated_depsgraph_get()
    new_mesh = bpy.data.meshes.new_from_object(
        obj.evaluated_get(depsgraph), preserve_all_data_layers=True, depsgraph=depsgraph)
    old_mesh = obj.data
    obj.data = new_mesh
    if old_mesh.users == 0:
        bpy.data.meshes.remove(old_mesh)
    for name in bake:
        obj.modifiers.remove(obj.modifiers[name])
    for name, shown in kept_state:
        obj.modifiers[name].show_viewport = shown


def _strip_hidden_modifiers(obj, keep_names=()):
    """Remove viewport-disabled modifiers (except kept ones) from a temp copy."""
    for mod in list(obj.modifiers):
        if not mod.show_viewport and mod.name not in keep_names:
            print(f"[MassExporter] Skipping viewport-disabled modifier "
                  f"'{mod.name}' on '{obj.name}'")
            obj.modifiers.remove(mod)


def _move_to_world_origin(obj):
    """Put obj's WORLD position at (0,0,0), whether or not it has a parent."""
    mw = obj.matrix_world.copy()
    mw.translation = (0.0, 0.0, 0.0)
    obj.matrix_world = mw


def _find_empty_groups(collection, view_layer=None):
    """Return [(empty, member_meshes)] for every empty in collection's tree.

    A mesh belongs to its NEAREST empty ancestor among those empties, so
    grandchildren (empty > mesh > mesh) are included and nested empties do not
    claim the same mesh twice. Empties left without members are dropped.
    With view_layer given, objects outside it are ignored.
    """
    empties = []
    seen = set()

    def walk(coll):
        for obj in coll.objects:
            if obj.type != 'EMPTY' or obj.name in seen or not _exportable(obj):
                continue
            if view_layer is not None and obj.name not in view_layer.objects:
                continue
            seen.add(obj.name)
            empties.append(obj)
        for child in coll.children:
            walk(child)

    walk(collection)
    groups = []
    for empty in empties:
        members = []
        for desc in empty.children_recursive:
            if desc.type != 'MESH' or not _exportable(desc):
                continue
            if view_layer is not None and desc.name not in view_layer.objects:
                continue
            owner = desc.parent
            while owner is not None and owner.name not in seen:
                owner = owner.parent
            if owner is not None and owner.name == empty.name:
                members.append(desc)
        if members:
            groups.append((empty, members))
    return groups


def _collection_meshes(collection):
    """Every mesh in collection and its descendants, de-duplicated, stable order."""
    result = []
    names = set()
    for obj in collection.all_objects:
        if obj.type == 'MESH' and obj.name not in names and _exportable(obj):
            names.add(obj.name)
            result.append(obj)
    return result


def _loose_meshes(collection, groups):
    """Meshes in collection's tree that no empty group claims."""
    claimed = {m.name for _, members in groups for m in members}
    return [o for o in _collection_meshes(collection) if o.name not in claimed]


def _join_copies(context, sources, origin_world, bake, only_visible, temp=True, fill_material=None):
    """Join copies of `sources` into one new object whose origin is origin_world.

    Each copy bakes its OWN modifier stack before the join (bake=True), or has
    every modifier stripped (bake=False). bpy.ops.object.join keeps only the
    active object's stack, so joining un-baked copies used to drop every other
    child's modifiers and spread the active child's stack over all of them.
    fill_material fills each copy's empty slots BEFORE the join: after it, the
    faces of a material-less part point at the first slot of another part.
    Copies that are not consumed are cleaned up on failure.
    """
    copies = []
    try:
        for src in sources:
            copy = _duplicate_object(src, temp=temp)
            copies.append(copy)
            if bake:
                if only_visible:
                    _strip_hidden_modifiers(copy)
                _bake_modifiers(context, copy)
            else:
                copy.modifiers.clear()
            if fill_material is not None and copy.type == 'MESH':
                _fill_empty_slots(copy, fill_material)
        context.view_layer.update()
        for copy in copies:
            if copy.parent is not None:
                world = copy.matrix_world.copy()
                copy.parent = None
                copy.matrix_world = world
        context.view_layer.update()

        if len(copies) > 1:
            batch_select_objects(copies, context)
            bpy.ops.object.join()
            joined = context.active_object
        else:
            joined = copies[0]

        # Move the origin to origin_world without moving any vertex in world space
        old = joined.matrix_world.copy()
        new = old.copy()
        new.translation = origin_world
        joined.data.transform(new.inverted() @ old)
        joined.matrix_world = new
        context.view_layer.update()
        return joined
    except Exception:
        for copy in copies:
            try:
                if copy.name in bpy.data.objects:
                    _remove_temp_object(copy)
            except ReferenceError:
                pass
        raise


class _TempCopies:
    """Copies that stand in for source objects during one export.

    originals hold a temporary `__mexport_*` name while the copy carries the
    real name, so the exported file shows clean names. reparented records
    source objects whose parent was pointed at a copy for the export.
    """

    def __init__(self):
        self.copies = []
        self.originals = []
        self.names = []
        self.reparented = []

    def __bool__(self):
        return bool(self.copies)


def _make_named_copy(obj, prefix):
    """Rename obj to prefix+name and return a copy carrying the real name."""
    original_name = obj.name
    obj.name = f"{prefix}{original_name}"
    copy = _duplicate_object(obj)
    copy.name = original_name
    return copy, original_name


def _finish_swap(context, objects, temp):
    """Select copies instead of their originals and keep the hierarchy intact.

    Any exported object (copy or untouched source) whose parent was replaced
    by a copy is re-pointed at that copy, with matrix_parent_inverse adjusted
    so its world transform is unchanged. Without this the child points at the
    original, which is not exported, and the FBX loses the hierarchy.
    """
    for obj in temp.originals:
        obj.select_set(False)
    for copy in temp.copies:
        copy.select_set(True)
    for obj in objects:
        if obj not in temp.originals:
            obj.select_set(True)

    context.view_layer.update()
    by_original = {o.name: c for o, c in zip(temp.originals, temp.copies)}
    copy_names = {c.name for c in temp.copies}
    for obj in list(context.selected_objects):
        parent = obj.parent
        if parent is None or parent.name not in by_original:
            continue
        new_parent = by_original[parent.name]
        old_inverse = obj.matrix_parent_inverse.copy()
        if obj.name not in copy_names:
            temp.reparented.append((obj, parent, old_inverse))
        obj.parent = new_parent
        obj.matrix_parent_inverse = new_parent.matrix_world.inverted() @ parent.matrix_world @ old_inverse
    context.view_layer.update()

    if temp.copies:
        context.view_layer.objects.active = temp.copies[0]
    else:
        still = [o for o in objects if o not in temp.originals]
        if still:
            context.view_layer.objects.active = still[0]


def _cleanup_temp_copies(context, temp):
    """Undo _finish_swap: restore parents, delete copies, restore names/selection."""
    for obj, parent, inverse in reversed(temp.reparented):
        try:
            obj.parent = parent
            obj.matrix_parent_inverse = inverse
        except ReferenceError:
            pass
    for copy in temp.copies:
        _remove_temp_object(copy)
    for obj, name in zip(temp.originals, temp.names):
        if obj.name in bpy.data.objects:
            obj.name = name
    for obj in temp.originals:
        if obj.name in bpy.data.objects:
            obj.select_set(True)
    if temp.originals and temp.originals[0].name in bpy.data.objects:
        context.view_layer.objects.active = temp.originals[0]
    context.view_layer.update()


def _recover_stale_temp_objects():
    """Clean up after an export that crashed mid-flight.

    Deletes tagged temporary copies first (they hold the real names), then
    gives the renamed originals their names back. Returns how many objects
    were touched.
    """
    count = 0
    for obj in [o for o in bpy.data.objects if o.get(_TEMP_TAG)]:
        _remove_temp_object(obj)
        count += 1
    for obj in list(bpy.data.objects):
        for prefix in _TEMP_PREFIXES:
            if obj.name.startswith(prefix):
                clean = obj.name[len(prefix):]
                if clean not in bpy.data.objects:
                    obj.name = clean
                    count += 1
                break
    return count


# ============================================================================
# Export option helpers
# ============================================================================

# The OBJ exporter names its axes differently from the FBX exporter
_OBJ_AXIS = {
    'X': 'X', 'Y': 'Y', 'Z': 'Z',
    '-X': 'NEGATIVE_X', '-Y': 'NEGATIVE_Y', '-Z': 'NEGATIVE_Z',
}

_FILE_EXT = {'FBX': 'fbx', 'OBJ': 'obj', 'GLTF': 'glb'}


def _export_format(props):
    """The export format, with FBX standing in for a value this version no
    longer has (a scene saved with Collada/DAE selected)."""
    fmt = props.export_format
    return fmt if fmt in _FILE_EXT else 'FBX'


def _file_ext(props):
    return _FILE_EXT[_export_format(props)]


def _has_enabled_suffixes(props):
    return any(s.enabled and s.suffix for s in props.suffix_items)


def _export_dir(item):
    """Absolute export folder of a row. A `//` path is relative to the .blend
    file (bpy.path.abspath); os.makedirs would otherwise read `//Exports` as a
    UNC share and fail with "Cannot create directory"."""
    path = (item.export_path or "").strip()
    if not path:
        return ""
    return os.path.normpath(bpy.path.abspath(path))


# Names of objects left out of the running export because they sit in a hidden
# sub-collection (or are hidden themselves) while Export Hidden Collections is
# off. Filled by export_collection for the duration of one row, read by every
# function that gathers the objects of a collection.
_SKIPPED = set()


def _exportable(obj):
    return obj.name not in _SKIPPED


def _hidden_object_names(collection):
    """Objects of collection's tree that are only reachable through a hidden
    sub-collection, or are hidden themselves (eye / monitor icon)."""
    root_lc = bpy.context.view_layer.layer_collection
    visible = set()

    def coll_hidden(coll):
        if getattr(coll, 'hide_viewport', False):
            return True
        lc = _find_layer_collection(root_lc, coll)
        return lc is not None and (lc.exclude or lc.hide_viewport)

    def walk(coll, hidden):
        hidden = hidden or coll_hidden(coll)
        if not hidden:
            for obj in coll.objects:
                try:
                    shown = not (obj.hide_viewport or obj.hide_get())
                except RuntimeError:
                    shown = False
                if shown:
                    visible.add(obj.name)
        for child in coll.children:
            walk(child, hidden)

    walk(collection, False)
    return {o.name for o in collection.all_objects if o.name not in visible}


_MATERIAL_MODES = [
    ('KEEP', "Keep", "Export every object with its own materials", 0),
    ('FILL', "Fill Empty",
     "Keep existing materials; objects and slots without a material get the override material. "
     "Joined meshes are filled per part, before the join", 1),
    ('OVERWRITE', "Overwrite", "Replace every material with the override material", 2),
]


def _material_mode(props):
    """The material mode, reading the pre-13.9 checkboxes when they are still set."""
    if props.material_mode != 'KEEP':
        return props.material_mode
    if props.override_materials:
        return 'OVERWRITE'
    if props.assign_if_no_material:
        return 'FILL'
    return 'KEEP'


def _fill_material(props):
    """The material that fills empty slots, or None when the mode is not Fill Empty."""
    if _material_mode(props) == 'FILL':
        return props.override_material
    return None


def _clear_legacy_material_flags(props):
    if props.override_materials:
        props.override_materials = False
    if props.assign_if_no_material:
        props.assign_if_no_material = False


@bpy.app.handlers.persistent
def _migrate_material_flags(_dummy=None):
    """Turn the pre-13.9 material checkboxes of every scene into material_mode."""
    for scene in bpy.data.scenes:
        props = getattr(scene, "mass_exporter_props", None)
        if props is None or not (props.override_materials or props.assign_if_no_material):
            continue
        mode = _material_mode(props)
        props.override_materials = False
        props.assign_if_no_material = False
        props.material_mode = mode


def _fill_empty_slots(obj, mat):
    """Give obj's empty material slots (or a slot-less mesh) mat. Temp copies only."""
    me = obj.data
    if not me.materials:
        me.materials.append(mat)
        return
    for i, m in enumerate(me.materials):
        if m is None:
            me.materials[i] = mat
    for slot in obj.material_slots:
        if slot.link == 'OBJECT' and slot.material is None:
            slot.material = mat


_ITEM_SETTINGS_SKIP = {'rna_type', 'name', 'collection', 'export_enabled'}


def _copy_item_settings(src, dst):
    """Copy every per-collection setting from src to dst (quick-export items)."""
    for prop in src.bl_rna.properties:
        if prop.identifier in _ITEM_SETTINGS_SKIP or prop.is_readonly:
            continue
        setattr(dst, prop.identifier, getattr(src, prop.identifier))


def _override_materials_temporarily(objects, props):
    """Apply the Material Options to the objects about to be exported.

    Changes are made in place and fully reverted by _restore_materials:
    mesh material lists, object-linked slots and material names.
    """
    backup = {'meshes': [], 'slots': [], 'names': []}
    mat = props.override_material
    mode = _material_mode(props) if mat is not None else 'KEEP'
    replace = mode == 'OVERWRITE'
    seen_meshes = set()
    meshes = [o for o in objects if o.type == 'MESH' and o.data is not None]

    if mode != 'KEEP':
        for obj in meshes:
            # Fill Empty: skip objects whose every slot already has a material
            if not replace and obj.material_slots and all(s.material for s in obj.material_slots):
                continue
            for i, slot in enumerate(obj.material_slots):
                if slot.link == 'OBJECT':
                    backup['slots'].append((obj, i, slot.material))
            me = obj.data
            if me.name not in seen_meshes:
                seen_meshes.add(me.name)
                backup['meshes'].append((me, list(me.materials)))
                if replace or not me.materials:
                    me.materials.clear()
                    me.materials.append(mat)
                else:
                    for i, m in enumerate(me.materials):
                        if m is None:
                            me.materials[i] = mat
            for slot in obj.material_slots:
                if slot.link == 'OBJECT' and (replace or slot.material is None):
                    slot.material = mat

    if props.add_m_prefix:
        renamed = set()
        for obj in meshes:
            for slot in obj.material_slots:
                m = slot.material
                if m is None or m.name in renamed or m.name.startswith("M_"):
                    continue
                try:
                    old = m.name
                    m.name = "M_" + old
                    renamed.add(m.name)
                    backup['names'].append((m, old))
                except (AttributeError, RuntimeError):
                    pass
    return backup


def _restore_materials(backup):
    if not backup:
        return
    for mat, old in reversed(backup['names']):
        try:
            mat.name = old
        except (AttributeError, RuntimeError, ReferenceError):
            pass
    for me, materials in backup['meshes']:
        try:
            me.materials.clear()
            for m in materials:
                me.materials.append(m)
        except ReferenceError:
            pass
    for obj, index, mat in backup['slots']:
        try:
            slot = obj.material_slots[index]
            slot.link = 'OBJECT'
            slot.material = mat
        except (IndexError, ReferenceError):
            pass

def move_empties_to_origin_core_logic(context, report_func=None, collections=None):
    """Move every empty that drives mesh children to WORLD origin.

    `collections` limits the scan; None means every enabled collection (the
    debug button). Export All passes only the collections that have
    'Move All Empties to Origin' ticked, so the flag never leaks into other
    collections of the same run.
    """
    # Force OBJECT mode
    if bpy.ops.object.mode_set.poll():
        bpy.ops.object.mode_set(mode='OBJECT')

    props = context.scene.mass_exporter_props

    if collections is None:
        collections = [item.collection for item in props.collection_items
                       if item.export_enabled and item.collection]

    if not collections:
        if report_func:
            report_func({'WARNING'}, "No collections enabled for export")
        print("No collections enabled for export")
        return {'CANCELLED'}

    print(f"Checking empties in {len(collections)} collections:")
    for coll in collections:
        print(f"  - {coll.name}")

    # Collect, de-duplicated by name (an empty can sit in several collections)
    unique_empties = {}
    for collection in collections:
        for empty, members in _find_empty_groups(collection):
            unique_empties.setdefault(empty.name, (empty, members))

    if not unique_empties:
        if report_func:
            report_func({'WARNING'}, "No empties with children found in enabled collections")
        print("No empties with children found in enabled collections")
        return {'CANCELLED'}

    print(f"\nFound {len(unique_empties)} empties to move:")

    for empty, members in unique_empties.values():
        print(f"Moving {empty.name} from {empty.matrix_world.translation} to world origin")
        _move_to_world_origin(empty)
        context.view_layer.update()
        for child in members:
            print(f"    {child.name} now at: {child.matrix_world.translation}")

    if report_func:
        report_func({'INFO'}, f"Moved {len(unique_empties)} empties to origin")
    print(f"\nSUCCESS: Moved {len(unique_empties)} empties to origin (0,0,0)")
    return {'FINISHED'}

# FIXED: Join ALL empties from ALL enabled collections
def join_empty_children_core_logic(context, report_func=None, apply_modifiers=False, apply_only_visible=False, keep_joined_copy=True):
    """Debug preview: build one joined COPY per empty (children of every
    enabled collection). Source objects are never touched; the joined copies
    stay in the scene for inspection."""
    # Force OBJECT mode
    if bpy.ops.object.mode_set.poll():
        bpy.ops.object.mode_set(mode='OBJECT')

    props = context.scene.mass_exporter_props

    enabled_collections = [item.collection for item in props.collection_items
                           if item.export_enabled and item.collection]
    if not enabled_collections:
        if report_func:
            report_func({'WARNING'}, "No collections enabled for export")
        print("No collections enabled for export")
        return {'CANCELLED'}

    unique_empties = {}
    for collection in enabled_collections:
        for empty, members in _find_empty_groups(collection, context.view_layer):
            unique_empties.setdefault(empty.name, (empty, members, collection))

    if not unique_empties:
        if report_func:
            report_func({'WARNING'}, "No empties with children found in enabled collections")
        print("No empties with children found in enabled collections")
        return {'CANCELLED'}

    print(f"\nFound {len(unique_empties)} empties with children to join:")

    original_selection = context.selected_objects.copy()
    original_active = context.active_object
    joined = []
    try:
        for empty, members, parent_collection in unique_empties.values():
            print(f"\nProcessing {empty.name} with {len(members)} child(ren)")
            try:
                joined_obj = _join_copies(
                    context, members, empty.matrix_world.translation.copy(),
                    bake=apply_modifiers,
                    only_visible=apply_only_visible or props.apply_only_visible_modifiers,
                    temp=False,
                )
            except Exception as e:
                print(f"  Error processing {empty.name}: {e}")
                continue
            if joined_obj is None:
                continue

            desired_name = f"{parent_collection.name}_joined"
            final_name = desired_name
            counter = 1
            while final_name in bpy.data.objects:
                final_name = f"{desired_name}_{counter}"
                counter += 1
            joined_obj.name = final_name

            # The copy already lives in the children's collections; make sure
            # it is also visible in the collection the empty was found in.
            if joined_obj.name not in parent_collection.objects:
                parent_collection.objects.link(joined_obj)

            if not keep_joined_copy:
                joined_obj.hide_set(True)
                joined_obj.hide_viewport = True
            joined.append(joined_obj.name)
            print(f"  Created '{joined_obj.name}' at {joined_obj.matrix_world.translation}")
    finally:
        batch_deselect_all(context)
        for obj in original_selection:
            if obj.name in bpy.data.objects:
                obj.select_set(True)
        if original_active and original_active.name in bpy.data.objects:
            context.view_layer.objects.active = original_active

    if joined and report_func:
        report_func({'INFO'}, f"Created joined copies for {len(joined)} empties: {', '.join(joined[:3])}")
    elif report_func:
        report_func({'WARNING'}, "No joined copies were created")
    return {'FINISHED'}

# Property Groups

class SuffixItem(PropertyGroup):
    """Individual suffix definition for grouping exports"""
    suffix: StringProperty(
        name="Suffix",
        description="Suffix to look for (e.g., _COL, _LOD0, _UCX)",
        default="_COL"
    )

    enabled: BoolProperty(
        name="Enabled",
        description="Enable this suffix for grouping",
        default=True
    )

    description: StringProperty(
        name="Description",
        description="Description of what this suffix represents",
        default="Collision"
    )


# ============================================================================
# Suffix Grouping Helper Functions
# ============================================================================

_SUFFIX_SEPARATORS = ("_", "-", ".", " ")


def get_base_name_without_suffix(name, suffix_items):
    """
    Get the base name by removing any matching suffix.
    Returns (base_name, matched_suffix) or (name, None) if no suffix matched.

    Trailing separator characters (_ - . space) are stripped from the
    resulting base so that suffixes typed without a leading separator
    (e.g. "cape") group correctly with the unsuffixed sibling
    (e.g. "char_001" and "char_001_cape" both reduce to "char_001").
    """
    name_lower = name.lower()
    # Match the longest enabled suffix first so "cape" doesn't out-match
    # "_cape" when both are defined.
    enabled = sorted(
        (item for item in suffix_items if item.enabled),
        key=lambda i: len(i.suffix),
        reverse=True,
    )
    for item in enabled:
        suffix_lower = item.suffix.lower()
        if not suffix_lower:
            continue
        if name_lower.endswith(suffix_lower):
            base = name[: -len(item.suffix)]
            # Strip a single trailing separator so "char_001_" -> "char_001"
            if base and base[-1] in _SUFFIX_SEPARATORS:
                base = base[:-1]
            return base, item.suffix
    return name, None


def find_suffix_groups(objects, suffix_items, debug=False):
    """
    Group objects by their base name (without suffix).
    Returns a dict: {base_name: [(obj, suffix_or_None), ...]}

    Objects without any suffix are grouped under their own name.
    Objects with suffixes are grouped with their base name counterparts.
    """
    groups = {}

    for obj in objects:
        base_name, suffix = get_base_name_without_suffix(obj.name, suffix_items)

        if base_name not in groups:
            groups[base_name] = []

        groups[base_name].append((obj, suffix))

        if debug:
            if suffix:
                print(f"  Object '{obj.name}' -> base '{base_name}' (suffix: {suffix})")
            else:
                print(f"  Object '{obj.name}' -> base '{base_name}' (no suffix)")

    return groups


def find_suffix_groups_in_collection(collection, suffix_items, include_subcollections=True, debug=False):
    """
    Find all meshes in a collection and group them by base name.

    Every mesh lands in exactly ONE group, claimed in this order:
      1. children of an empty in the collection -> the empty's base name
      2. meshes of a direct sub-collection      -> the sub-collection's base name
      3. any other direct mesh                  -> its own base name
    (Before v13.8.0 an empty's child was also grouped under its own name and
    so exported twice.)

    Returns dict: {base_name: {'objects': [(obj, suffix)], 'empties': [empty], 'subcollections': [coll]}}
    """
    groups = {}
    claimed = set()

    def add(base_name, obj, suffix, empty=None, subcoll=None):
        group = groups.setdefault(base_name, {'objects': [], 'empties': [], 'subcollections': []})
        if obj.name in claimed:
            return
        claimed.add(obj.name)
        group['objects'].append((obj, suffix))
        if empty is not None and empty not in group['empties']:
            group['empties'].append(empty)
        if subcoll is not None and subcoll not in group['subcollections']:
            group['subcollections'].append(subcoll)

    if debug:
        print(f"Processing collection: {collection.name}")

    # 1) Empties directly in the collection claim their mesh members
    direct_empty_groups = [
        (empty, members) for empty, members in _find_empty_groups(collection)
        if empty.name in collection.objects
    ]
    for empty, members in direct_empty_groups:
        empty_base, empty_suffix = get_base_name_without_suffix(empty.name, suffix_items)
        for child in members:
            add(empty_base, child, empty_suffix, empty=empty)
        if debug:
            print(f"  Empty '{empty.name}' ({len(members)} children) -> '{empty_base}'")

    # 2) Sub-collections claim their remaining meshes
    if include_subcollections:
        for sub_coll in collection.children:
            sub_base, sub_suffix = get_base_name_without_suffix(sub_coll.name, suffix_items)
            sub_meshes = [o for o in _collection_meshes(sub_coll) if o.name not in claimed]
            for obj in sub_meshes:
                add(sub_base, obj, sub_suffix, subcoll=sub_coll)
            if debug and sub_meshes:
                print(f"  Sub-collection '{sub_coll.name}' ({len(sub_meshes)} meshes) -> '{sub_base}'")

    # 3) Remaining direct meshes group by their own name
    for obj in collection.objects:
        if obj.type != 'MESH' or obj.name in claimed or not _exportable(obj):
            continue
        base_name, suffix = get_base_name_without_suffix(obj.name, suffix_items)
        add(base_name, obj, suffix)
        if debug:
            print(f"  Mesh '{obj.name}' -> '{base_name}'")

    return {k: v for k, v in groups.items() if v['objects']}


# ============================================================================
# Performance Helpers (from v12.6.0)
# ============================================================================

def batch_deselect_all(context):
    """Deselect all by iterating only currently selected objects — much faster
    than batch_deselect_all(context) which walks all scene objects."""
    for obj in context.selected_objects:
        obj.select_set(False)


def batch_select_objects(objects, context, deselect_first=True):
    """Efficiently select a list of objects."""
    if deselect_first:
        batch_deselect_all(context)
    for obj in objects:
        obj.select_set(True)
    if objects:
        context.view_layer.objects.active = objects[0]


def build_collection_depth_map():
    """Build a collection -> depth map for fast O(n) lookups.
    Depth is distance from the scene root collection (root = 0)."""
    depth_map = {}

    def traverse(collection, depth):
        depth_map[collection] = depth
        for child in collection.children:
            traverse(child, depth + 1)

    for scene in bpy.data.scenes:
        traverse(scene.collection, 0)

    for coll in bpy.data.collections:
        if coll not in depth_map:
            depth_map[coll] = 0

    return depth_map


def find_immediate_collection(obj, depth_map=None):
    """Return the deepest (most immediate) collection directly containing obj.
    Pass a pre-built depth_map when calling in a loop for best performance."""
    containing = [c for c in bpy.data.collections if obj.name in c.objects]
    if not containing:
        return None
    if len(containing) == 1:
        return containing[0]
    if depth_map is None:
        depth_map = build_collection_depth_map()
    return max(containing, key=lambda c: depth_map.get(c, 0))


class CollectionExportItem(PropertyGroup):
    """Individual collection export settings"""
    collection: PointerProperty(
        name="Collection",
        type=bpy.types.Collection,
        description="Collection to export"
    )

    export_enabled: BoolProperty(
        name="Export",
        description="Enable export for this collection",
        default=False
    )

    merge_to_single: BoolProperty(
        name="Merge",
        description="Merge all objects in collection to single file",
        default=False
    )

    export_subcollections_as_single: BoolProperty(
        name="Sub-Collections as Single",
        description="Export each sub-collection as a single merged object",
        default=False
    )

    use_empty_origins: BoolProperty(
        name="Use Parent Empties",
        description="Search for parent empties and use them as origins/centers",
        default=False
    )

    join_empty_children: BoolProperty(
        name="Join Empty Children",
        description="Combine all mesh children into a single object per export",
        default=False
    )

    apply_modifiers_before_join: BoolProperty(
        name="Apply Modifiers",
        description="Apply modifiers before joining meshes",
        default=False
    )

    apply_only_visible: BoolProperty(
        name="Only Visible Modifiers",
        description=(
            "Skip modifiers disabled in the viewport when joining. The global "
            "'Only Visible Modifiers' (Modifier & Rig Options) already does this when on; "
            "this toggle forces it for this collection when the global one is off"
        ),
        default=False
    )

    move_to_center: BoolProperty(
        name="Move to Center",
        description=(
            "Put each exported asset at the world origin (0,0,0) for the export: its parent "
            "empty when it has one, otherwise the object itself. The scene is restored "
            "afterwards, so assets can stay lined up side by side in Blender"
        ),
        default=True
    )

    use_suffix_grouping: BoolProperty(
        name="Group by Suffix",
        description="Group objects with matching names but different suffixes (e.g., sm_cube and sm_cube_COL) into single exports",
        default=False
    )

    export_as_single_fbx: BoolProperty(
        name="Whole Collection as One File",
        description=(
            "Export the entire collection (including all subcollections, meshes, "
            "armatures and empties) into a single file, preserving hierarchy. "
            "Armature modifiers stay bound because rigs are included in the same export. "
            "Takes priority over other export modes"
        ),
        default=False
    )

    single_fbx_custom_name: StringProperty(
        name="Custom Filename",
        description=(
            "Filename to use when 'Whole Collection as One File' is enabled "
            "(without extension). Leave empty to use the collection's name"
        ),
        default=""
    )

    export_path: StringProperty(
        name="Export Path",
        description="Path where files will be exported",
        default="",
        subtype='DIR_PATH'
    )

class MassExporterProperties(PropertyGroup):
    """Main property group for Mass Exporter"""

    # Collection Options
    collection_items: CollectionProperty(
        type=CollectionExportItem,
        name="Collection Export Items"
    )

    active_collection_index: IntProperty(
        name="Active Collection Index",
        default=0
    )

    # Suffix Grouping Options
    suffix_items: CollectionProperty(
        type=SuffixItem,
        name="Export Suffixes"
    )

    active_suffix_index: IntProperty(
        name="Active Suffix Index",
        default=0
    )

    # Transform Options
    # Note: "Export at Origin" is gone — centering is now per-collection via
    # `move_to_center` on each CollectionItem. See _center_root_objects_temporarily.

    apply_transforms: BoolProperty(
        name="Apply Transforms",
        description="Apply object transforms before export",
        default=False
    )

    axis_forward: EnumProperty(
        name="Forward Axis",
        description="Forward axis for export",
        items=[
            ('X', 'X Forward', ''),
            ('Y', 'Y Forward', ''),
            ('Z', 'Z Forward', ''),
            ('-X', '-X Forward', ''),
            ('-Y', '-Y Forward', ''),
            ('-Z', '-Z Forward', ''),
        ],
        default='-Z'
    )

    axis_up: EnumProperty(
        name="Up Axis",
        description="Up axis for export",
        items=[
            ('X', 'X Up', ''),
            ('Y', 'Y Up', ''),
            ('Z', 'Z Up', ''),
            ('-X', '-X Up', ''),
            ('-Y', '-Y Up', ''),
            ('-Z', '-Z Up', ''),
        ],
        default='Y'
    )

    # Material Options
    material_mode: EnumProperty(
        name="Materials",
        description="What the exported files use as materials",
        items=_MATERIAL_MODES,
        default='KEEP',
        update=lambda self, _context: _clear_legacy_material_flags(self),
    )

    override_material: PointerProperty(
        name="Override Material",
        type=bpy.types.Material,
        description="Material used by Fill Empty and Overwrite"
    )

    # Before v13.9.0 two checkboxes set the material behaviour. They stay
    # registered so older files keep their choice; _migrate_material_flags
    # turns them into material_mode on load and clears them.
    override_materials: BoolProperty(
        name="Override Materials (legacy)",
        description="Replaced by Materials > Overwrite",
        default=False
    )

    assign_if_no_material: BoolProperty(
        name="Assign if No Material (legacy)",
        description="Replaced by Materials > Fill Empty",
        default=False
    )

    add_m_prefix: BoolProperty(
        name="Add M_ Prefix if Missing",
        description="Add M_ prefix to material names if missing",
        default=False
    )

    # File Export Options
    export_format: EnumProperty(
        name="Export Format",
        description="File format for export",
        # Explicit values keep files saved before v13.8.0 loading the right
        # format: 2 was Collada (DAE), removed with Blender 5.0.
        items=[
            ('FBX', 'FBX', 'Export as FBX', 0),
            ('OBJ', 'OBJ', 'Export as OBJ', 1),
            ('GLTF', 'glTF 2.0 (.glb)', 'Export as binary glTF 2.0', 3),
        ],
        default='FBX'
    )

    debug_mode: BoolProperty(
        name="Debug Mode",
        description="Print debug information during export",
        default=False
    )

    # FBX Scale and Transform Options
    apply_scaling: EnumProperty(
        name="Apply Scaling",
        description="How to apply scaling to exported FBX (affects scale in Unity)",
        items=[
            ('FBX_SCALE_NONE', 'None', 'Do not apply any scaling'),
            ('FBX_SCALE_UNITS', 'FBX Units Scale', 'Apply unit scaling (recommended for Unity)'),
            ('FBX_SCALE_CUSTOM', 'FBX Custom Scale', 'Apply custom scale'),
            ('FBX_SCALE_ALL', 'FBX All', 'Apply all scaling'),
        ],
        default='FBX_SCALE_UNITS'
    )

    bake_space_transform: BoolProperty(
        name="Apply Transform",
        description=(
            "Bake the axis conversion into object data so Unity imports without a "
            "-90° rotation. Blender marks this experimental: it can misplace armatures "
            "and animation, so turn it off for rigged or animated exports"
        ),
        default=True
    )

    apply_modifiers: BoolProperty(
        name="Apply Modifiers",
        description="Apply all object modifiers before export",
        default=True
    )

    apply_only_visible_modifiers: BoolProperty(
        name="Only Visible Modifiers",
        description=(
            "Only bake modifiers that are enabled in the viewport (monitor icon on). "
            "Blender's own Apply Modifier operator ignores that toggle and bakes disabled "
            "modifiers anyway, so they are stripped from the temporary export copy first. "
            "Armature modifiers kept for rig binding are never stripped"
        ),
        default=True
    )

    skip_armature_modifier: BoolProperty(
        name="Skip Armature Modifier",
        description="When applying modifiers, skip armature deform modifiers (exports mesh without armature deformation)",
        default=False
    )

    export_rig_with_mesh: BoolProperty(
        name="Export Rig with Mesh",
        description="Include the armature object from Armature modifiers in the export, even if it is not part of the export collection",
        default=False
    )

    # FBX Armature Options
    primary_bone_axis: EnumProperty(
        name="Primary Bone Axis",
        items=[
            ('X', 'X Axis', ''),
            ('Y', 'Y Axis', ''),
            ('Z', 'Z Axis', ''),
            ('-X', '-X Axis', ''),
            ('-Y', '-Y Axis', ''),
            ('-Z', '-Z Axis', ''),
        ],
        default='Y'
    )

    secondary_bone_axis: EnumProperty(
        name="Secondary Bone Axis",
        items=[
            ('X', 'X Axis', ''),
            ('Y', 'Y Axis', ''),
            ('Z', 'Z Axis', ''),
            ('-X', '-X Axis', ''),
            ('-Y', '-Y Axis', ''),
            ('-Z', '-Z Axis', ''),
        ],
        default='X'
    )

    armature_nodetype: EnumProperty(
        name="Armature FBX Node",
        items=[
            ('NULL', 'Null', 'Export armature as a null/locator node'),
            ('ROOT', 'Root', 'Export armature as a root node'),
            ('LIMBNODE', 'LimbNode', 'Export armature as a limb node'),
        ],
        default='NULL'
    )

    use_armature_deform_only: BoolProperty(
        name="Only Deform Bones",
        description="Only export bones used for mesh deformation",
        default=True
    )

    add_leaf_bones: BoolProperty(
        name="Add Leaf Bones",
        description="Append a final bone to the end of each chain to specify the tip of the last bone",
        default=False
    )

    export_hidden_collections: BoolProperty(
        name="Export Hidden Collections",
        description=(
            "Temporarily unhide collections/objects that are hidden "
            "(collection hide_viewport, layer collection exclude / hide, "
            "object eye icon, selection lock, local view) so they can be "
            "exported. Original visibility state is restored afterward. "
            "When disabled, hidden collections are skipped with a warning"
        ),
        default=True
    )

# Blender has two separate "hide" flags:
#   - Collection.hide_viewport: the monitor icon in the outliner (disable in
#     viewports globally, across all view layers)
#   - LayerCollection.hide_viewport: the EYE icon in the outliner (per view
#     layer, temporary)
# Users almost always toggle the EYE in the outliner, so the UIList eye has to
# read/write LayerCollection.hide_viewport to stay in sync.
def _find_layer_collection(root_lc, target_coll):
    """Return the LayerCollection wrapping target_coll in the active view
    layer, or None if the collection is not present in this view layer."""
    if root_lc is None or target_coll is None:
        return None
    stack = [root_lc]
    while stack:
        lc = stack.pop()
        if lc.collection == target_coll:
            return lc
        stack.extend(lc.children)
    return None


def _collection_effective_hidden(coll):
    """Return the best-effort 'is the eye icon off?' for coll.

    Uses LayerCollection.hide_viewport when the collection is in the active
    view layer; falls back to Collection.hide_viewport otherwise.
    """
    if coll is None:
        return False
    try:
        root_lc = bpy.context.view_layer.layer_collection
    except AttributeError:
        root_lc = None
    lc = _find_layer_collection(root_lc, coll)
    if lc is not None:
        return bool(lc.hide_viewport)
    return bool(getattr(coll, 'hide_viewport', False))


# UI Lists
class MASSEXPORTER_UL_collections(UIList):
    """UI List for collection items"""

    def draw_item(self, context, layout, data, item, icon, active_data,
                  active_propname, index=0, flt_flag=0):
        if self.layout_type in {'DEFAULT', 'COMPACT'}:
            coll = item.collection

            # Eye icon mirrors the outliner eye: LayerCollection.hide_viewport
            # in the active view layer. Falls back to Collection.hide_viewport
            # if the collection is not in this view layer.
            is_hidden = _collection_effective_hidden(coll)
            eye_icon = 'HIDE_ON' if is_hidden else 'HIDE_OFF'
            vis_row = layout.row()
            vis_row.enabled = coll is not None
            op = vis_row.operator("massexporter.toggle_collection_visibility",
                                  text="", icon=eye_icon, emboss=False)
            op.index = index

            # Export checkbox
            layout.prop(item, "export_enabled", text="")

            # Merge checkbox
            layout.prop(item, "merge_to_single", text="", icon='SNAP_FACE_CENTER')

            # Collection selector
            layout.prop(item, "collection", text="")

            # Export path
            row = layout.row()
            row.prop(item, "export_path", text="")
            row.operator("massexporter.select_folder", text="", icon='FOLDER_REDIRECT').index = index

# Operators
class MASSEXPORTER_OT_move_empties_to_origin(Operator):
    """Move empties with children to origin - only those in enabled collections"""
    bl_idname = "massexporter.move_empties_to_origin"
    bl_label = "Move Empties to Origin"
    bl_description = "Move empties with mesh children to origin (0,0,0) - only from enabled collections"
    
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        """Move empties to origin - uses the standalone core logic function"""
        return move_empties_to_origin_core_logic(context, self.report)

class MASSEXPORTER_OT_join_empties(Operator):
    """Join children of empties - only those in enabled collections"""
    bl_idname = "massexporter.join_empties"
    bl_label = "Join Empties"
    bl_description = "Create joined copies of all mesh children of empties - only from enabled collections"

    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        """Join empty children - uses the copy-based core logic function and KEEPS the copies"""
        props = context.scene.mass_exporter_props

        # Check if any enabled collection has apply_modifiers_before_join enabled
        apply_modifiers = False
        apply_only_visible = False
        for item in props.collection_items:
            if item.export_enabled and item.collection and item.apply_modifiers_before_join:
                apply_modifiers = True
                if item.apply_only_visible:
                    apply_only_visible = True
                break

        # KEEP the joined copies for debug button (keep_joined_copy=True)
        return join_empty_children_core_logic(context, self.report, apply_modifiers, apply_only_visible, keep_joined_copy=True)

class MASSEXPORTER_OT_add_collection(Operator):
    """Add a new collection to export list"""
    bl_idname = "massexporter.add_collection"
    bl_label = "Add Collection"
    bl_description = "Add a new collection to the export list"

    def execute(self, context):
        props = context.scene.mass_exporter_props
        new_item = props.collection_items.add()
        props.active_collection_index = len(props.collection_items) - 1
        return {'FINISHED'}

class MASSEXPORTER_OT_remove_collection(Operator):
    """Remove collection from export list"""
    bl_idname = "massexporter.remove_collection"
    bl_label = "Remove Collection"
    bl_description = "Remove selected collection from export list"

    def execute(self, context):
        props = context.scene.mass_exporter_props
        if props.collection_items:
            props.collection_items.remove(props.active_collection_index)
            props.active_collection_index = max(0, props.active_collection_index - 1)
        return {'FINISHED'}


class MASSEXPORTER_OT_toggle_collection_visibility(Operator):
    """Toggle viewport (and render) visibility of the collection assigned to this row"""
    bl_idname = "massexporter.toggle_collection_visibility"
    bl_label = "Toggle Collection Visibility"
    bl_description = "Toggle visibility of the assigned collection (viewport + render)"

    index: IntProperty()

    def execute(self, context):
        props = context.scene.mass_exporter_props
        if not (0 <= self.index < len(props.collection_items)):
            return {'CANCELLED'}
        coll = props.collection_items[self.index].collection
        if coll is None:
            self.report({'WARNING'}, "No collection assigned to this row")
            return {'CANCELLED'}
        if not hasattr(coll, 'hide_viewport'):
            self.report({'WARNING'},
                        f"'{getattr(coll, 'name', '<unknown>')}' is not a Collection (type={type(coll).__name__})")
            return {'CANCELLED'}
        # Toggle the same flag the outliner eye uses so the UIs stay in sync.
        # LayerCollection.hide_viewport is per-view-layer (the eye). We only
        # fall back to Collection.hide_viewport when the collection isn't in
        # the active view layer at all.
        lc = _find_layer_collection(context.view_layer.layer_collection, coll)
        if lc is not None:
            lc.hide_viewport = not lc.hide_viewport
        else:
            coll.hide_viewport = not coll.hide_viewport
            if hasattr(coll, 'hide_render'):
                coll.hide_render = coll.hide_viewport
        return {'FINISHED'}


# ============================================================================
# Suffix Management Operators
# ============================================================================

class MASSEXPORTER_OT_add_suffix(Operator):
    """Add a new suffix to the grouping list"""
    bl_idname = "massexporter.add_suffix"
    bl_label = "Add Suffix"
    bl_description = "Add a new suffix for grouping exports (e.g., _COL for collision)"

    suffix: StringProperty(
        name="Suffix",
        default="_COL"
    )

    description: StringProperty(
        name="Description",
        default="Collision"
    )

    def execute(self, context):
        props = context.scene.mass_exporter_props
        item = props.suffix_items.add()
        item.suffix = self.suffix
        item.description = self.description
        item.enabled = True
        props.active_suffix_index = len(props.suffix_items) - 1
        return {'FINISHED'}

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)

    def draw(self, context):
        layout = self.layout
        layout.prop(self, "suffix")
        layout.prop(self, "description")


class MASSEXPORTER_OT_remove_suffix(Operator):
    """Remove suffix from grouping list"""
    bl_idname = "massexporter.remove_suffix"
    bl_label = "Remove Suffix"
    bl_description = "Remove selected suffix from grouping list"

    def execute(self, context):
        props = context.scene.mass_exporter_props
        if props.suffix_items:
            props.suffix_items.remove(props.active_suffix_index)
            props.active_suffix_index = max(0, props.active_suffix_index - 1)
        return {'FINISHED'}


class MASSEXPORTER_OT_add_default_suffixes(Operator):
    """Add common default suffixes"""
    bl_idname = "massexporter.add_default_suffixes"
    bl_label = "Add Default Suffixes"
    bl_description = "Add common suffixes like _COL (collision), _LOD0, _UCX (Unreal collision)"

    def execute(self, context):
        props = context.scene.mass_exporter_props

        # Common game development suffixes
        defaults = [
            ("_COL", "Collision"),
            ("_col", "Collision (lowercase)"),
            ("_UCX", "Unreal Convex Collision"),
            ("_LOD0", "LOD Level 0"),
            ("_LOD1", "LOD Level 1"),
            ("_LOD2", "LOD Level 2"),
            ("_LOD3", "LOD Level 3"),
        ]

        added_count = 0
        existing_suffixes = [item.suffix.lower() for item in props.suffix_items]

        for suffix, desc in defaults:
            if suffix.lower() not in existing_suffixes:
                item = props.suffix_items.add()
                item.suffix = suffix
                item.description = desc
                item.enabled = True
                added_count += 1

        if added_count > 0:
            props.active_suffix_index = len(props.suffix_items) - 1
            self.report({'INFO'}, f"Added {added_count} default suffix(es)")
        else:
            self.report({'INFO'}, "All default suffixes already exist")

        return {'FINISHED'}


class MASSEXPORTER_UL_suffixes(UIList):
    """UIList for suffix items"""
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname):
        if self.layout_type in {'DEFAULT', 'COMPACT'}:
            row = layout.row(align=True)
            row.prop(item, "enabled", text="")
            row.prop(item, "suffix", text="", emboss=False)
            row.label(text=f"({item.description})")
        elif self.layout_type == 'GRID':
            layout.alignment = 'CENTER'
            layout.prop(item, "enabled", text="")

class MASSEXPORTER_OT_select_folder(Operator, ExportHelper):
    """Select folder for export path"""
    bl_idname = "massexporter.select_folder"
    bl_label = "Select Export Folder"
    bl_description = "Select folder for export path"

    filename_ext = ""
    use_filter_folder = True

    index: IntProperty()

    def execute(self, context):
        props = context.scene.mass_exporter_props
        if self.index < len(props.collection_items):
            # Get directory path from filepath
            directory = os.path.dirname(self.filepath)
            props.collection_items[self.index].export_path = directory
        return {'FINISHED'}

class MASSEXPORTER_OT_export_all(Operator):
    """Export all enabled collections - join happens on-demand during export"""
    bl_idname = "massexporter.export_all"
    bl_label = "Export All"
    bl_description = "Export all enabled collections - join happens on-demand during each export"

    def execute(self, context):
        # Force OBJECT mode to avoid operator context errors
        if bpy.ops.object.mode_set.poll():
            bpy.ops.object.mode_set(mode='OBJECT')

        props = context.scene.mass_exporter_props
        exported_count = 0
        exported_collection_names = []  # NEW: Track exported collection names

        # Clean up temp-export objects left behind by an interrupted run, so
        # they cannot collide with the names this run hands to its copies.
        recovered = _recover_stale_temp_objects()
        if recovered:
            self.report({'WARNING'},
                        f"Recovered {recovered} leftover temp objects from a prior export")

        # Store original selection and active object
        original_selection = context.selected_objects.copy()
        original_active = context.active_object
        
        # Snapshot every empty's local transform BEFORE any export operation;
        # the empty-moving steps are undone from this in finally.
        original_empty_positions = {}
        if props.debug_mode:
            print("\n=== EXPORT STARTED - STORING ORIGINAL POSITIONS ===")

        for obj in bpy.context.scene.objects:
            if obj.type == 'EMPTY':
                original_empty_positions[obj.name] = obj.matrix_basis.copy()

        # Centering is one per-row option, Move to Center, applied per exported
        # file (see _center_root_objects_temporarily). The old "Move All Empties
        # to Origin" pre-pass and "Center Each Empty" are gone since v13.9.0.

        # Export only collections whose checkbox is enabled, regardless of
        # which row is active/selected in the UIList. A per-item try/except
        # ensures one bad collection does not abort the rest of the batch.
        failed = []
        try:
            for item in props.collection_items:
                if not (item.export_enabled and item.collection and item.export_path):
                    continue
                coll = item.collection
                coll_name = getattr(coll, 'name', '<unknown>')
                # Validate the pointer is actually a Collection — it must
                # expose `all_objects`. If not, the row is pointing at an
                # Object/ID by mistake (possible after old data migrations);
                # skip and warn instead of crashing/hanging in the export
                # path.
                if not hasattr(coll, 'all_objects'):
                    self.report({'WARNING'},
                                f"Row '{coll_name}' is not a Collection "
                                f"(type={type(coll).__name__}) — skipping")
                    continue
                if props.debug_mode:
                    print(f"\n--- Exporting '{coll_name}' ---")
                try:
                    if self.export_collection(context, props, item):
                        exported_count += 1
                        exported_collection_names.append(coll_name)
                except Exception as e:
                    failed.append((coll_name, str(e)))
                    if props.debug_mode:
                        import traceback
                        traceback.print_exc()
        finally:
            # Surface per-item failures to the user.
            for coll_name, err in failed:
                self.report({'ERROR'}, f"Export failed for '{coll_name}': {err}")

            # Restore ALL empty positions at the very end
            if props.debug_mode:
                print("\n=== EXPORT FINISHED - RESTORING ALL POSITIONS ===")

            for empty_name, original_basis in original_empty_positions.items():
                empty = bpy.data.objects.get(empty_name)
                if empty is not None and empty.matrix_basis != original_basis:
                    if props.debug_mode:
                        print(f"Restoring {empty_name} to {original_basis.translation}")
                    empty.matrix_basis = original_basis

            # Update scene after all restorations
            bpy.context.view_layer.update()

            # Restore original selection
            batch_deselect_all(context)
            for obj in original_selection:
                if obj.name in bpy.data.objects:  # Check if object still exists
                    obj.select_set(True)
            if original_active and original_active.name in bpy.data.objects:
                context.view_layer.objects.active = original_active

            if props.debug_mode:
                print("=== ALL POSITIONS RESTORED ===")

        # NEW: Report exported collection names
        if exported_count > 0:
            names_str = ", ".join(exported_collection_names[:3])  # Show first 3
            if len(exported_collection_names) > 3:
                names_str += f", ... ({len(exported_collection_names)} total)"
            self.report({'INFO'}, f"Exported {exported_count} collections: {names_str}")
        else:
            self.report({'WARNING'}, "No collections were exported")
            
        return {'FINISHED'}

    @staticmethod
    def _get_layer_collection_path(root_lc, target_coll):
        """Return all LayerCollections from root down to the one wrapping target_coll.

        Uses explicit visited-set + iterative BFS to guard against any malformed
        layer-collection graph that could otherwise send the previous recursive
        implementation into an infinite loop / stack blow-up. A proper Blender
        scene has a pure tree, but library-linked / override scenes have been
        observed to briefly expose cycles while state is in transition.

        CRITICAL: the visited set is keyed on the wrapped Collection's name, NOT
        `id(lc)`. Blender re-creates the `LayerCollection` Python wrapper on every
        `.children` access, so each wrapper is a throwaway object; once it is
        garbage-collected Python freely RECYCLES its `id()` for the next wrapper.
        Keying `visited` on `id(lc)` therefore produces false "already visited"
        hits that abort the search before it reaches the target — returning [],
        which silently disables the entire unhide pipeline (the bug that left
        eye-hidden parent collections un-revealed during export). Collection names
        are unique per blend file and stable across wrapper churn, so they are a
        safe identity key.
        """
        if root_lc is None or target_coll is None:
            return []
        visited = set()
        # Each queue entry is (layer_coll, path_so_far_without_self)
        queue = [(root_lc, [])]
        while queue:
            lc, path = queue.pop(0)
            key = lc.collection.name if lc.collection is not None else id(lc)
            if key in visited:
                continue
            visited.add(key)
            if lc.collection == target_coll:
                return path + [lc]
            for child in lc.children:
                queue.append((child, path + [lc]))
        return []

    @staticmethod
    def _collection_is_hidden(collection):
        """Return True if the collection is hidden through any viewport-level
        mechanism: data-level `hide_viewport`, or any layer collection on the
        path having `exclude` or `hide_viewport` set."""
        if getattr(collection, 'hide_viewport', False):
            return True
        root_lc = bpy.context.view_layer.layer_collection
        path = MASSEXPORTER_OT_export_all._get_layer_collection_path(root_lc, collection)
        for lc in path:
            if lc.exclude or lc.hide_viewport:
                return True
        return False

    @staticmethod
    def _unhide_collection_for_export(collection):
        """Force collection into a fully-exportable state, deterministically.

        Strategy: clear every Blender hide flag that can block select_set and
        make the object invisible to the exporter — on every Collection and
        LayerCollection touched by the export, and on every object in scope.
        Restore is symmetric: the backup is a flat list of (obj/coll/lc,
        original-value-tuple) entries that _restore_collection_for_export
        replays in reverse order. That property guarantees two consecutive
        exports yield the same scene state.

        Scope of what gets unhidden, all in a single pass:

          Collections (data-block — the monitor icon):
            - Every Collection on the path from scene root to target
            - Target itself
            - Every descendant Collection of target (recursively)
            Flags cleared: hide_viewport, hide_render

          LayerCollections (the outliner eye + the exclude checkbox):
            - Same tree: root-to-target + all descendants
            Flags cleared: exclude, hide_viewport

          Objects (collection.all_objects of target — flat recursive list):
            Flags cleared: hide_viewport, hide_get (eye), hide_select
            Added to local view in every 3D-viewport space that currently
            has local view active, so select_set is not silently rejected

        After the Collection and LayerCollection flips we flush the view
        layer once; object flips follow; we flush again so hide_get reflects
        the flips before the caller's select_set fires.
        """
        backup = {
            'target_collection': collection,
            'coll_flags': [],     # [(coll, hide_viewport, hide_render), ...]
            'layer_coll': [],     # [(lc, exclude, hide_viewport, is_master), ...]
            'objects': [],        # [(obj, hide_viewport, hide_get), ...]
            'hide_select': [],    # [(obj, prev_hide_select), ...]
            'local_view': [],     # [(obj, space), ...]
            'selected': [],       # [(obj, select_get), ...]
        }

        root_lc = bpy.context.view_layer.layer_collection
        path = MASSEXPORTER_OT_export_all._get_layer_collection_path(root_lc, collection)

        # Every LayerCollection we will touch: path (root→target) + every
        # descendant of target. Drives both LayerCollection-flag clearing and
        # Collection-flag clearing (one Collection per LayerCollection).
        lc_all = list(path)
        if path:
            stack = list(path[-1].children)
            while stack:
                lc = stack.pop()
                lc_all.append(lc)
                stack.extend(lc.children)

        # 1) Clear LayerCollection flags (per-view-layer: exclude + eye).
        #    NEVER write `exclude` on the master (scene-root) LayerCollection:
        #    on Blender 5.0, assigning `master.exclude` — even to its current
        #    value — cascades a reset of EVERY descendant LayerCollection's
        #    `exclude` flag across the whole view layer. That silently wipes the
        #    original exclude state (including unrelated excluded collections)
        #    *before* we record it, so the backup captures the wrong values and
        #    restore can never put them back. The master is always effectively
        #    included anyway, so skipping its `exclude` loses nothing; we still
        #    clear its eye (hide_viewport). `is_master` is stored so the
        #    symmetric restore can skip it without needing the root reference.
        for lc in lc_all:
            is_master = (lc == root_lc)
            backup['layer_coll'].append((lc, lc.exclude, lc.hide_viewport, is_master))
            if not is_master:
                lc.exclude = False
            lc.hide_viewport = False

        # 2) Clear Collection-level flags (global: monitor icon + camera)
        #    Iterate the Collections behind each LayerCollection, de-duped.
        #    De-dupe on the Collection NAME, not id(coll): `lc.collection`
        #    returns a fresh wrapper each access and Python recycles freed
        #    wrappers' id()s, so id()-keyed dedup yields false collisions that
        #    would skip clearing a still-hidden collection (same class of bug
        #    as the old id(lc) path-walk — see _get_layer_collection_path).
        seen_colls = set()
        for lc in lc_all:
            coll = lc.collection
            if coll is None:
                continue
            key = coll.name
            if key in seen_colls:
                continue
            seen_colls.add(key)
            hv = getattr(coll, 'hide_viewport', False)
            hr = getattr(coll, 'hide_render', False)
            backup['coll_flags'].append((coll, hv, hr))
            if hasattr(coll, 'hide_viewport'):
                coll.hide_viewport = False
            if hasattr(coll, 'hide_render'):
                coll.hide_render = False

        # CRITICAL: flush the view layer now, BEFORE touching per-object state.
        # Clearing `lc.exclude` re-adds the collection's objects to the view
        # layer — but until the depsgraph refreshes, calling `obj.hide_set()`
        # or `obj.select_set()` raises "object is not in view layer" and the
        # exporter silently writes nothing.
        bpy.context.view_layer.update()

        # 3) Object-level flags + local view membership.
        #    Every 3D viewport (across every window) currently in local view.
        local_view_spaces = []
        wm = getattr(bpy.context, 'window_manager', None)
        if wm is not None:
            for window in wm.windows:
                for area in window.screen.areas:
                    if area.type != 'VIEW_3D':
                        continue
                    for space in area.spaces:
                        if space.type == 'VIEW_3D' and getattr(space, 'local_view', None):
                            local_view_spaces.append(space)

        # Materialize into a plain Python list BEFORE the loop. Iterating a
        # live `bpy_prop_collection` while the body calls `hide_set` /
        # `local_view_set` mutates the depsgraph mid-walk — on Blender 5.0
        # this has been observed to invalidate the underlying iterator and
        # segfault. A frozen list of object refs sidesteps that entirely.
        try:
            all_objects = list(getattr(collection, 'all_objects', ()) or ())
        except (ReferenceError, AttributeError, TypeError):
            all_objects = []
        skipped = []
        for obj in all_objects:
            # Skip stale / freed references defensively — `obj` from a
            # cached list can outlive the underlying ID datablock.
            try:
                _ = obj.name
            except (ReferenceError, AttributeError):
                continue
            try:
                backup['objects'].append((obj, obj.hide_viewport, obj.hide_get()))
                backup['selected'].append((obj, obj.select_get()))
                obj.hide_viewport = False
                obj.hide_set(False)
            except (AttributeError, RuntimeError, ReferenceError) as exc:
                # After the exhaustive layer flush above this should never
                # fire; keep it as a visible regression signal.
                skipped.append((getattr(obj, 'name', '<?>'), str(exc)))
                continue
            try:
                if obj.hide_select:
                    backup['hide_select'].append((obj, True))
                    obj.hide_select = False
            except (AttributeError, ReferenceError):
                pass
            for space in local_view_spaces:
                try:
                    was_in_lv = obj.local_view_get(space)
                except (AttributeError, RuntimeError, TypeError, ReferenceError):
                    continue
                if not was_in_lv:
                    try:
                        obj.local_view_set(space, True)
                        backup['local_view'].append((obj, space))
                    except (AttributeError, RuntimeError, TypeError, ReferenceError):
                        continue

        if skipped:
            print(f"[MassExporter] _unhide_collection_for_export: skipped "
                  f"{len(skipped)} objects not in view layer "
                  f"(first: {skipped[0]}) — this is a bug, please report")

        # Flush so hide_get() reflects the flips before the caller selects.
        bpy.context.view_layer.update()

        return backup

    @staticmethod
    def _restore_collection_for_export(backup):
        """Symmetric restore. Replays the backup in reverse order so two
        consecutive exports leave the scene in identical state."""
        # Objects first (they depend on their collections existing in view
        # layer — which, after restore, may no longer be true).
        # Selection goes back while the objects are still visible: once hidden
        # they drop out of context.selected_objects, so the caller's deselect
        # missed them and they stayed selected, leaking into the next export.
        for obj, was_selected in backup.get('selected', ()):
            if obj.name in bpy.data.objects:
                try:
                    obj.select_set(was_selected)
                except (RuntimeError, ReferenceError):
                    pass
        for obj, space in backup.get('local_view', ()):
            if obj.name in bpy.data.objects:
                try:
                    obj.local_view_set(space, False)
                except (AttributeError, RuntimeError, TypeError):
                    pass
        for obj, prev in backup.get('hide_select', ()):
            if obj.name in bpy.data.objects:
                try:
                    obj.hide_select = prev
                except AttributeError:
                    pass
        for obj, hide_viewport, hide_eye in backup.get('objects', ()):
            if obj.name in bpy.data.objects:
                try:
                    obj.hide_viewport = hide_viewport
                    obj.hide_set(hide_eye)
                except (AttributeError, RuntimeError):
                    pass

        # Collection-level flags (monitor + camera icons)
        for coll, hv, hr in backup.get('coll_flags', ()):
            if hasattr(coll, 'hide_viewport'):
                try:
                    coll.hide_viewport = hv
                except (AttributeError, ReferenceError):
                    pass
            if hasattr(coll, 'hide_render'):
                try:
                    coll.hide_render = hr
                except (AttributeError, ReferenceError):
                    pass

        # LayerCollection flags (eye + exclude) — last, so the view layer's
        # final state is the originally-saved one. Restore DEEPEST-FIRST
        # (reverse of capture order): `exclude` is hierarchical, so writing an
        # ancestor's `exclude` before its descendants' would force-include the
        # descendants and corrupt their flags. Skip the master's `exclude` for
        # the same reason it is skipped on the way in (see _unhide_*).
        for lc, was_excluded, was_hidden, is_master in reversed(backup.get('layer_coll', ())):
            try:
                if not is_master:
                    lc.exclude = was_excluded
                lc.hide_viewport = was_hidden
            except (AttributeError, ReferenceError):
                pass

    def export_collection(self, context, props, item):
        """Export a single collection"""
        collection = item.collection
        export_path = _export_dir(item)

        if props.debug_mode:
            print(f"\n=== EXPORTING COLLECTION: {collection.name} ===")

        if item.export_path.strip().startswith("//") and not bpy.data.filepath:
            self.report({'ERROR'},
                        f"'{collection.name}': save the .blend file first - its export path "
                        f"'{item.export_path}' is relative to it")
            return False
        try:
            os.makedirs(export_path, exist_ok=True)
        except OSError:
            self.report({'ERROR'}, f"Cannot create directory: {export_path}")
            return False

        # Visibility isolation: forces collection / layer collection / object
        # / local-view state into an exportable shape for the duration of the
        # export, then restores it in `finally`. Local-view isolation is
        # always applied (it is the only way the exporter works at all while
        # the user is in local view); hidden-collection isolation is gated on
        # the user-facing `export_hidden_collections` toggle so skipping
        # hidden rows stays an option.
        is_hidden = MASSEXPORTER_OT_export_all._collection_is_hidden(collection)
        if is_hidden and not props.export_hidden_collections:
            self.report(
                {'WARNING'},
                f"Skipping '{collection.name}' — it is hidden and "
                "'Export Hidden Collections' is off"
            )
            return False
        if is_hidden and props.debug_mode:
            print(f"[MassExporter] Unhiding hidden collection '{collection.name}' for export "
                  f"(armature rules still apply via export_rig_with_mesh)")
        # With the toggle off, hidden sub-collections and hidden objects of
        # this row are left out too, not only a hidden row. Read BEFORE the
        # unhide below clears the flags.
        _SKIPPED.clear()
        if not props.export_hidden_collections:
            _SKIPPED.update(_hidden_object_names(collection))
            if _SKIPPED and props.debug_mode:
                print(f"[MassExporter] Leaving out hidden objects: {sorted(_SKIPPED)}")
        visibility_backup = MASSEXPORTER_OT_export_all._unhide_collection_for_export(collection)

        try:
            # Handle different export modes
            # Whole-collection-as-one-file takes highest priority — it bundles
            # every object (meshes + armatures + empties + ...) into a single
            # FBX with hierarchy intact, so it should short-circuit the other
            # per-collection modes.
            if item.export_as_single_fbx:
                return MASSEXPORTER_OT_export_all.export_collection_as_single_fbx(self, context, props, item)
            # Suffix grouping takes priority if enabled and at least one
            # suffix is switched on (a list of only disabled suffixes would
            # otherwise hijack Merge / per-object export)
            if item.use_suffix_grouping and _has_enabled_suffixes(props):
                return MASSEXPORTER_OT_export_all.export_with_suffix_grouping(self, context, props, item)
            elif item.export_subcollections_as_single:
                return MASSEXPORTER_OT_export_all.export_subcollections_as_single(self, context, props, item)
            elif item.use_empty_origins:
                return MASSEXPORTER_OT_export_all.export_with_empty_origins(self, context, props, item)
            else:
                objects = MASSEXPORTER_OT_export_all.get_collection_objects(self, collection)

                if not objects:
                    self.report({'WARNING'}, f"No objects found in collection: {collection.name}")
                    return False

                if item.merge_to_single:
                    return MASSEXPORTER_OT_export_all.export_objects_as_single(self, context, props, objects, collection.name, export_path, item=item)
                else:
                    success_count = 0
                    for obj in objects:
                        if MASSEXPORTER_OT_export_all.export_single_object(self, context, props, obj, export_path, item=item):
                            success_count += 1
                    return success_count > 0
        finally:
            _SKIPPED.clear()
            if visibility_backup:
                MASSEXPORTER_OT_export_all._restore_collection_for_export(visibility_backup)

    def export_subcollections_as_single(self, context, props, item):
        """Export each sub-collection as a single merged object"""
        collection = item.collection
        export_path = _export_dir(item)
        success_count = 0

        if props.debug_mode:
            print(f"Exporting sub-collections as single files for: {collection.name}")

        # Export main collection objects (if any) as one file
        main_objects = [obj for obj in collection.objects if obj.type == 'MESH' and _exportable(obj)]
        if main_objects:
            if MASSEXPORTER_OT_export_all.export_objects_as_single(self, context, props, main_objects, f"{collection.name}_main", export_path, item=item):
                success_count += 1

        # Export each sub-collection as individual merged files
        for sub_collection in collection.children:
            # FIXED: Use new join logic if join_empty_children is enabled
            if item.use_empty_origins and item.join_empty_children:
                # Join all empties in this sub-collection and export as one
                if MASSEXPORTER_OT_export_all.export_collection_with_all_empties_joined(self, context, props, item, sub_collection, export_path):
                    success_count += 1
            else:
                sub_objects = MASSEXPORTER_OT_export_all.get_collection_objects(self, sub_collection)
                if sub_objects:
                    if MASSEXPORTER_OT_export_all.export_objects_as_single(self, context, props, sub_objects, sub_collection.name, export_path, item=item):
                        success_count += 1

        return success_count > 0

    # Object types that survive a round-trip through the FBX exporter. Anything
    # else (e.g. metaballs, volumes, grease pencil) is dropped silently and only
    # bloats the selection, so we filter at the source.
    _SINGLE_FBX_TYPES = frozenset({
        'MESH', 'ARMATURE', 'EMPTY', 'CURVE', 'SURFACE',
        'META', 'FONT', 'CAMERA', 'LIGHT', 'LATTICE',
    })

    @staticmethod
    def _collect_collection_objects_for_single_fbx(collection):
        """Return every exportable object from `collection` and its descendants.

        Uses `collection.all_objects` so subcollections are included with no
        manual recursion. Order is deterministic for stable debug output.
        """
        return [
            obj for obj in collection.all_objects
            if obj.type in MASSEXPORTER_OT_export_all._SINGLE_FBX_TYPES and _exportable(obj)
        ]

    @staticmethod
    def _center_root_objects_temporarily(objects):
        """Move to Center: put each exported asset's pivot at world (0,0,0).

        The pivot of a root (an object whose parent is None or outside the
        export set) is its parent when that parent is an EMPTY - the empty is
        the asset's origin, so the parts keep their layout around it - and
        the root itself otherwise. Children follow their parent, so only
        pivots move. Several pivots stack at the origin.

        Positions go through matrix_world, so parent inverse matrices and
        parented empties are honoured. Returns a backup of each pivot's
        matrix_basis for `_restore_root_object_locations`.
        """
        if not objects:
            return None
        obj_set = set(objects)
        pivots = []
        for o in objects:
            if o.parent is not None and o.parent in obj_set:
                continue
            pivot = o.parent if (o.parent is not None and o.parent.type == 'EMPTY') else o
            if pivot not in pivots:
                pivots.append(pivot)
        if not pivots:
            return None
        backup = [(o, o.matrix_basis.copy()) for o in pivots]
        for o in pivots:
            bpy.context.view_layer.update()
            _move_to_world_origin(o)
        bpy.context.view_layer.update()
        return backup

    @staticmethod
    def _restore_root_object_locations(backup):
        if not backup:
            return
        for obj, original in reversed(backup):
            if obj.name in bpy.data.objects:
                obj.matrix_basis = original
        bpy.context.view_layer.update()

    def export_collection_as_single_fbx(self, context, props, item):
        """Export the whole collection (meshes + armatures + empties + ...)
        as a single file, preserving hierarchy.

        Mesh armature modifiers stay valid because every referenced rig in
        the collection ships in the same file. External rigs are still
        picked up via `perform_export`'s `_select_associated_rigs` path when
        `export_rig_with_mesh` is enabled globally. Apply Transforms bakes on
        temporary copies; children keep pointing at their (copied) parents.
        """
        collection = item.collection
        export_path = _export_dir(item)

        if props.debug_mode:
            print(f"\n=== SINGLE-FBX EXPORT: {collection.name} ===")

        objects = MASSEXPORTER_OT_export_all._collect_collection_objects_for_single_fbx(collection)
        if not objects:
            self.report({'WARNING'}, f"No exportable objects in: {collection.name}")
            return False

        if props.debug_mode:
            print(f"  {len(objects)} objects:")
            for o in objects:
                print(f"    [{o.type}] {o.name}")

        # Resolve filename: custom override (trimmed) falls back to collection name.
        custom = (item.single_fbx_custom_name or "").strip()
        out_name = custom if custom else collection.name

        batch_select_objects(objects, context)

        # Per-collection "Move to Center" — park root-level objects at the
        # origin for the export, then restore.
        location_backup = None
        if item.move_to_center:
            location_backup = MASSEXPORTER_OT_export_all._center_root_objects_temporarily(objects)

        xform = _TempCopies()
        try:
            if props.apply_transforms:
                xform = MASSEXPORTER_OT_export_all._apply_transforms_via_duplicates(context, objects)

            filepath = os.path.join(export_path, f"{out_name}.{_file_ext(props)}")

            if props.debug_mode:
                print(f"  Exporting to: {filepath}")

            return MASSEXPORTER_OT_export_all.perform_export(self, props, filepath)
        finally:
            if xform:
                _cleanup_temp_copies(context, xform)
            MASSEXPORTER_OT_export_all._restore_root_object_locations(location_backup)

    def export_with_suffix_grouping(self, context, props, item):
        """
        Export with suffix grouping enabled.
        Groups objects/empties/subcollections by base name and exports them together.
        Example: sm_cube_4x4 and sm_cube_4x4_COL are exported as single file 'sm_cube_4x4.fbx'
        Each mesh belongs to exactly one group (see find_suffix_groups_in_collection).
        """
        collection = item.collection
        export_path = _export_dir(item)
        success_count = 0

        if props.debug_mode:
            print(f"\n=== SUFFIX GROUPING EXPORT: {collection.name} ===")
            print(f"Enabled suffixes: {[s.suffix for s in props.suffix_items if s.enabled]}")

        groups = find_suffix_groups_in_collection(
            collection,
            props.suffix_items,
            include_subcollections=True,
            debug=props.debug_mode
        )

        if not groups:
            self.report({'WARNING'}, f"No objects found in collection: {collection.name}")
            return False

        for base_name, group_data in groups.items():
            all_meshes = [obj for obj, _suffix in group_data['objects'] if obj.type == 'MESH']
            if not all_meshes:
                continue

            if props.debug_mode:
                print(f"\n  Exporting group '{base_name}' with {len(all_meshes)} mesh(es):")
                for mesh in all_meshes:
                    print(f"    - {mesh.name}")

            if MASSEXPORTER_OT_export_all.export_objects_as_single(
                self, context, props, all_meshes, base_name, export_path, item=item
            ):
                success_count += 1
            elif props.debug_mode:
                print(f"  ✗ Failed to export '{base_name}'")

        if props.debug_mode:
            print(f"\n=== SUFFIX GROUPING COMPLETE: {success_count}/{len(groups)} groups exported ===")

        return success_count > 0

    def export_with_empty_origins(self, context, props, item):
        """Use Parent Empties: every parent empty is one asset.

        One file per empty, named after it, with the empty as the pivot (Move
        to Center puts it at the origin). Without Join the member meshes keep
        their hierarchy as separate elements of the file; with Join they become
        one mesh named after the empty. Meshes under no empty: Merge on ->
        `<collection>`, off -> one file each.
        """
        collection = item.collection
        export_path = _export_dir(item)
        success_count = 0

        context.view_layer.update()
        groups = _find_empty_groups(collection, context.view_layer)
        loose = [o for o in _loose_meshes(collection, groups) if o.name in context.view_layer.objects]

        if props.debug_mode:
            print(f"Parent empties in {collection.name}: {len(groups)} assets, {len(loose)} loose meshes")

        for empty, members in groups:
            if props.debug_mode:
                print(f"\n--- ASSET: {empty.name} ({len(members)} meshes) ---")
            if item.join_empty_children:
                ok = MASSEXPORTER_OT_export_all.export_empty_joined(
                    self, context, props, item, empty, members, export_path)
            else:
                ok = MASSEXPORTER_OT_export_all.export_objects_as_single(
                    self, context, props, members, empty.name, export_path, item=item)
            if ok:
                success_count += 1

        if loose:
            if item.merge_to_single:
                if MASSEXPORTER_OT_export_all.export_objects_as_single(self, context, props, loose, collection.name, export_path, item=item):
                    success_count += 1
            else:
                for obj in loose:
                    if MASSEXPORTER_OT_export_all.export_single_object(self, context, props, obj, export_path, item=item):
                        success_count += 1

        return success_count > 0

    def export_empty_joined(self, context, props, item, empty, members, export_path):
        """Join copies of one empty's members into a mesh named after the
        empty, with its origin at the empty, and export it as `<empty>`."""
        empty_name = empty.name
        basis = empty.matrix_basis.copy()
        joined = None
        try:
            if item.move_to_center:
                _move_to_world_origin(empty)
                context.view_layer.update()
            joined = _join_copies(
                context, members, empty.matrix_world.translation.copy(),
                bake=item.apply_modifiers_before_join or props.apply_modifiers,
                only_visible=item.apply_only_visible or props.apply_only_visible_modifiers,
                fill_material=_fill_material(props),
            )
            # The empty holds the name the joined mesh must carry in the file
            empty.name = f"__mexport_{empty_name}"
            joined.name = empty_name
            return MASSEXPORTER_OT_export_all.export_single_object_simple(
                self, context, props, joined, empty_name, export_path)
        except Exception as e:
            if props.debug_mode:
                import traceback
                traceback.print_exc()
            self.report({'ERROR'}, f"Error joining '{empty_name}': {e}")
            return False
        finally:
            if joined is not None:
                _remove_temp_object(joined)
            if empty.name != empty_name:
                empty.name = empty_name
            empty.matrix_basis = basis
            context.view_layer.update()

    def export_collection_with_all_empties_joined(self, context, props, item, collection, export_path):
        """
        Join copies of every mesh in the collection into ONE object named after
        the collection, with its origin at the first empty, and export it.
        Members of empties and loose meshes are both included. Each copy bakes
        its own modifier stack first (Apply Modifiers here or the global one),
        otherwise all modifiers are dropped from the copies.
        FALLBACK: If no empties found, exports meshes in collection normally.
        """
        if props.debug_mode:
            print(f"\n=== JOINING ALL EMPTIES IN COLLECTION: {collection.name} ===")

        context.view_layer.update()
        groups = _find_empty_groups(collection, context.view_layer)

        if not groups:
            if props.debug_mode:
                print("No empties with children found - falling back to normal export")
            objects = MASSEXPORTER_OT_export_all.get_collection_objects(self, collection)
            if not objects:
                return False
            if item.merge_to_single:
                return MASSEXPORTER_OT_export_all.export_objects_as_single(self, context, props, objects, collection.name, export_path, item=item)
            success_count = 0
            for obj in objects:
                if MASSEXPORTER_OT_export_all.export_single_object(self, context, props, obj, export_path, item=item):
                    success_count += 1
            return success_count > 0

        sources = [m for _, members in groups for m in members]
        sources += [o for o in _loose_meshes(collection, groups) if o.name in context.view_layer.objects]
        origin = groups[0][0].matrix_world.translation.copy()

        if props.debug_mode:
            print(f"Joining {len(sources)} meshes from {len(groups)} empties, origin {origin}")

        original_selection = context.selected_objects.copy()
        original_active = context.active_object
        joined_obj = None
        try:
            joined_obj = _join_copies(
                context, sources, origin,
                bake=item.apply_modifiers_before_join or props.apply_modifiers,
                only_visible=item.apply_only_visible or props.apply_only_visible_modifiers,
                fill_material=_fill_material(props),
            )
            joined_obj.name = collection.name
            if item.move_to_center:
                mw = joined_obj.matrix_world.copy()
                mw.translation = (0.0, 0.0, 0.0)
                joined_obj.matrix_world = mw
                context.view_layer.update()
            return MASSEXPORTER_OT_export_all.export_single_object_simple(
                self, context, props, joined_obj, collection.name, export_path)
        except Exception as e:
            if props.debug_mode:
                import traceback
                traceback.print_exc()
            self.report({'ERROR'}, f"Error during join-all export: {str(e)}")
            return False
        finally:
            if joined_obj is not None:
                _remove_temp_object(joined_obj)
            batch_deselect_all(context)
            for obj in original_selection:
                if obj.name in bpy.data.objects:
                    obj.select_set(True)
            if original_active and original_active.name in bpy.data.objects:
                context.view_layer.objects.active = original_active

    def export_single_object_simple(self, context, props, obj, name, export_path):
        """Simple export of a single object without additional transform modifications"""
        if props.debug_mode:
            print(f"Simple export: {obj.name} as {name}")
            print(f"  Object world position: {obj.matrix_world.translation}")

        original_selection = context.selected_objects.copy()
        original_active = context.active_object

        try:
            batch_select_objects([obj], context)
            filepath = os.path.join(export_path, f"{name}.{_file_ext(props)}")
            if props.debug_mode:
                print(f"Exporting to: {filepath}")
            return MASSEXPORTER_OT_export_all.perform_export(self, props, filepath)
        finally:
            batch_deselect_all(context)
            for original_obj in original_selection:
                if original_obj.name in bpy.data.objects:
                    original_obj.select_set(True)
            if original_active and original_active.name in bpy.data.objects:
                context.view_layer.objects.active = original_active

    def get_collection_objects(self, collection):
        """Get all objects from collection and sub-collections"""
        objects = []

        # Add objects directly in collection
        for obj in collection.objects:
            if obj.type == 'MESH' and _exportable(obj):
                objects.append(obj)

        # Add objects from sub-collections
        for child_collection in collection.children:
            objects.extend(self.get_collection_objects(child_collection))

        return objects

    def export_objects_as_single(self, context, props, objects, collection_name, export_path, item=None):
        """Export multiple objects as single file.

        Source data must never be altered. Centering (item.move_to_center)
        parks each export-set root at world (0,0,0) and is restored in finally.
        apply_transforms runs on temporary duplicates because transform_apply
        is destructive to mesh vertices. Centering happens BEFORE the duplicate
        so transform_apply bakes the centered position into the exported mesh.
        """
        batch_select_objects(objects, context)

        # Snapshot loc/rot/scale up front so we can restore unconditionally
        # in finally, no matter which option mutated what.
        original_transforms = [
            (obj.name, obj.location.copy(), obj.rotation_euler.copy(), obj.scale.copy())
            for obj in objects
        ]

        location_backup = None
        xform = _TempCopies()
        try:
            if item is not None and item.move_to_center:
                location_backup = MASSEXPORTER_OT_export_all._center_root_objects_temporarily(objects)
            if props.apply_transforms:
                xform = MASSEXPORTER_OT_export_all._apply_transforms_via_duplicates(context, objects)

            filepath = os.path.join(export_path, f"{collection_name}.{_file_ext(props)}")
            return MASSEXPORTER_OT_export_all.perform_export(self, props, filepath)
        finally:
            # Delete duplicates first so original names are free to be restored.
            if xform:
                _cleanup_temp_copies(context, xform)
            if location_backup is not None:
                MASSEXPORTER_OT_export_all._restore_root_object_locations(location_backup)
            for name, loc, rot, scale in original_transforms:
                obj = bpy.data.objects.get(name)
                if obj:
                    obj.location = loc
                    obj.rotation_euler = rot
                    obj.scale = scale

    def export_single_object(self, context, props, obj, export_path, item=None):
        """Export single object.

        Source data must never be altered. Centering (item.move_to_center)
        parks the object's root at world (0,0,0) and is restored in finally.
        apply_transforms runs on a temporary duplicate because transform_apply
        is destructive to mesh vertices. Centering happens BEFORE the duplicate
        so transform_apply bakes the centered position into the exported mesh.
        """
        original_name = obj.name
        return MASSEXPORTER_OT_export_all.export_objects_as_single(
            self, context, props, [obj], original_name, export_path, item=item)

    @staticmethod
    def _apply_modifiers_to_selection(context, objects, skip_armature=False, only_visible=False):
        """Bake modifiers on temporary copies of mesh objects and swap the
        selection so copies replace originals. Returns a _TempCopies for
        _cleanup_modifier_copies.

        Armature modifiers whose rig is already in the export selection are
        always preserved — baking them would strip the skin binding from the
        FBX even though the rig ships in the same file. `skip_armature` is
        kept as a manual override that preserves ALL armature modifiers
        regardless of whether the rig is in the selection.

        `only_visible` limits the bake to modifiers enabled in the viewport:
        disabled ones are DELETED from the temporary copy before baking, which
        keeps the stack order intact exactly like the viewport. Preserved
        armature modifiers are exempt — stripping a hidden armature modifier
        would silently unbind the mesh from its rig in the FBX.
        """
        temp = _TempCopies()
        rigs_in_selection = {o.name for o in objects if o.type == 'ARMATURE'}

        def _kept(mod):
            if mod.type != 'ARMATURE':
                return False
            if skip_armature:
                return True
            return mod.object is not None and mod.object.name in rigs_in_selection

        for obj in objects:
            if obj.type != 'MESH':
                continue  # armatures/empties: leave in selection as-is

            keep = {m.name for m in obj.modifiers if _kept(m)}
            to_bake = [m for m in obj.modifiers
                       if m.name not in keep and (m.show_viewport or not only_visible)]
            if not to_bake:
                continue  # nothing to bake — export the source object untouched

            copy = None
            try:
                copy, original_name = _make_named_copy(obj, "__mexport_")
                if only_visible:
                    _strip_hidden_modifiers(copy, keep)
                _bake_modifiers(context, copy, keep)
                temp.copies.append(copy)
                temp.originals.append(obj)
                temp.names.append(original_name)
            except Exception as e:
                print(f"[MassExporter] Could not bake modifiers of '{obj.name}': {e}")
                if copy is not None:
                    _remove_temp_object(copy)
                if obj.name.startswith("__mexport_"):
                    obj.name = obj.name[len("__mexport_"):]

        _finish_swap(context, objects, temp)
        return temp

    @staticmethod
    def _cleanup_modifier_copies(context, temp):
        """Delete temporary copies and restore original names, parents and selection."""
        _cleanup_temp_copies(context, temp)

    @staticmethod
    def _apply_transforms_via_duplicates(context, objects):
        """Bake location/rotation/scale into mesh data on temporary copies.

        transform_apply rewrites vertex coordinates in place, so it must never
        run on source meshes. Each mesh is copied, the copy takes the original's
        name, and the transform is baked into the copy's own mesh. Non-mesh
        objects are left untouched. Children are re-pointed at the baked copy
        without moving (see _finish_swap). Returns a _TempCopies.
        """
        temp = _TempCopies()

        for obj in objects:
            if obj.type != 'MESH':
                continue
            copy = None
            try:
                copy, original_name = _make_named_copy(obj, "__mexport_xform_")
                # transform_apply bakes only the local transform. A parent that
                # is not exported (the asset's empty, possibly moved to the
                # origin by Move to Center) would still place the copy, so the
                # copy leaves it first and its whole world transform is baked.
                if copy.parent is not None and copy.parent not in objects:
                    world = copy.matrix_world.copy()
                    copy.parent = None
                    copy.matrix_world = world
                batch_select_objects([copy], context)
                bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
                temp.copies.append(copy)
                temp.originals.append(obj)
                temp.names.append(original_name)
            except Exception as e:
                print(f"[MassExporter] Could not apply transforms of '{obj.name}': {e}")
                if copy is not None:
                    _remove_temp_object(copy)
                if obj.name.startswith("__mexport_xform_"):
                    obj.name = obj.name[len("__mexport_xform_"):]

        _finish_swap(context, objects, temp)
        return temp

    @staticmethod
    def _select_associated_rigs(objects):
        """Select armature objects referenced by Armature modifiers.

        Temporarily links each rig to the scene root collection so
        collection-level hiding cannot block the exporter, clears every
        visibility/selection block on it (object hide flags, hide_select,
        local-view membership in every active 3D viewport), and selects it.
        Returns a backup list for full restoration by _deselect_rigs.

        Mirrors the local-view handling in _unhide_collection_for_export: a
        rig outside the active local view reports hide_get()==True and
        select_set(True) is a silent no-op, which is why armature export
        previously did nothing while in local view.
        """
        backup = []
        seen = set()
        root_coll = bpy.context.scene.collection

        local_view_spaces = []
        wm = getattr(bpy.context, 'window_manager', None)
        if wm is not None:
            for window in wm.windows:
                for area in window.screen.areas:
                    if area.type != 'VIEW_3D':
                        continue
                    for space in area.spaces:
                        if space.type == 'VIEW_3D' and getattr(space, 'local_view', None):
                            local_view_spaces.append(space)

        for obj in objects:
            if obj.type != 'MESH':
                continue
            for mod in obj.modifiers:
                if mod.type != 'ARMATURE' or not mod.object or mod.object.name not in bpy.data.objects:
                    continue
                rig = mod.object
                if rig.name in seen:
                    continue
                seen.add(rig.name)
                entry = {
                    'rig': rig,
                    'was_selected': rig.select_get(),
                    'hide_viewport': rig.hide_viewport,
                    'hide_eye': rig.hide_get(),
                    'in_root': rig.name in root_coll.objects,
                    'hide_select': getattr(rig, 'hide_select', False),
                    'local_view': [],
                }
                # Link to root collection so collection-level visibility cannot hide it
                if not entry['in_root']:
                    root_coll.objects.link(rig)
                # Clear object-level hide flags
                rig.hide_viewport = False
                rig.hide_set(False)
                # Clear selection lock
                try:
                    if rig.hide_select:
                        rig.hide_select = False
                except AttributeError:
                    pass
                # Inject into every active local view so it is selectable
                for space in local_view_spaces:
                    try:
                        was_in_lv = rig.local_view_get(space)
                    except (AttributeError, RuntimeError, TypeError):
                        continue
                    if not was_in_lv:
                        try:
                            rig.local_view_set(space, True)
                            entry['local_view'].append(space)
                        except (AttributeError, RuntimeError, TypeError):
                            continue
                # Flush before select_set so hide_get reflects the flips
                bpy.context.view_layer.update()
                if not entry['was_selected']:
                    rig.select_set(True)
                backup.append(entry)
        return backup

    @staticmethod
    def _deselect_rigs(backup):
        """Restore rig visibility, selection, local-view membership, and collection
        membership from a backup produced by _select_associated_rigs."""
        root_coll = bpy.context.scene.collection
        for entry in backup:
            rig = entry['rig']
            if rig.name not in bpy.data.objects:
                continue
            if not entry['was_selected']:
                try:
                    rig.select_set(False)
                except RuntimeError:
                    pass
            try:
                rig.hide_viewport = entry['hide_viewport']
                rig.hide_set(entry['hide_eye'])
            except (AttributeError, RuntimeError):
                pass
            try:
                rig.hide_select = entry.get('hide_select', False)
            except AttributeError:
                pass
            for space in entry.get('local_view', ()):
                try:
                    rig.local_view_set(space, False)
                except (AttributeError, RuntimeError, TypeError):
                    continue
            if not entry['in_root'] and rig.name in root_coll.objects:
                root_coll.objects.unlink(rig)

    def perform_export(self, props, filepath):
        """Perform the actual export based on format — the single choke point.

        Order: pull in rigs, bake modifiers on temporary copies, apply the
        Material Options to whatever is now selected, export, then undo all of
        it in reverse. Exporter-side modifier flags stay off because baking
        already happened on the copies."""
        context = bpy.context
        initial_selected = list(context.selected_objects)

        added_rigs = []
        modifiers = _TempCopies()
        material_backup = None
        try:
            # Add rigs FIRST so they are included in the selection passed to modifier apply
            if props.export_rig_with_mesh:
                added_rigs = MASSEXPORTER_OT_export_all._select_associated_rigs(initial_selected)

            selected = list(context.selected_objects)
            if props.apply_modifiers:
                modifiers = MASSEXPORTER_OT_export_all._apply_modifiers_to_selection(
                    context, selected,
                    skip_armature=props.skip_armature_modifier,
                    only_visible=props.apply_only_visible_modifiers
                )

            material_backup = _override_materials_temporarily(list(context.selected_objects), props)

            export_format = _export_format(props)
            if export_format != props.export_format:
                print(f"[MassExporter] Export format '{props.export_format}' is no longer "
                      f"available - exporting FBX")

            if export_format == 'FBX':
                bpy.ops.export_scene.fbx(
                    filepath=filepath,
                    use_selection=True,
                    axis_forward=props.axis_forward,
                    axis_up=props.axis_up,
                    apply_scale_options=props.apply_scaling,
                    bake_space_transform=props.bake_space_transform,
                    use_mesh_modifiers=False,
                    primary_bone_axis=props.primary_bone_axis,
                    secondary_bone_axis=props.secondary_bone_axis,
                    armature_nodetype=props.armature_nodetype,
                    use_armature_deform_only=props.use_armature_deform_only,
                    add_leaf_bones=props.add_leaf_bones
                )

            elif export_format == 'OBJ':
                bpy.ops.wm.obj_export(
                    filepath=filepath,
                    export_selected_objects=True,
                    forward_axis=_OBJ_AXIS[props.axis_forward],
                    up_axis=_OBJ_AXIS[props.axis_up],
                    export_materials=True,
                    apply_modifiers=False
                )

            elif export_format == 'GLTF':
                # glTF is always Y-up; the axis settings do not apply.
                bpy.ops.export_scene.gltf(
                    filepath=filepath,
                    export_format='GLB',
                    use_selection=True,
                    export_apply=False
                )

            return True

        except Exception as e:
            print(f"Export error: {str(e)}")
            self.report({'ERROR'}, f"Export failed for {os.path.basename(filepath)}: {e}")
            return False

        finally:
            _restore_materials(material_backup)
            if modifiers:
                MASSEXPORTER_OT_export_all._cleanup_modifier_copies(context, modifiers)
            if added_rigs:
                MASSEXPORTER_OT_export_all._deselect_rigs(added_rigs)

class MASSEXPORTER_OT_export_selected_collection(Operator):
    """Export collection of currently selected object as a whole"""
    bl_idname = "massexporter.export_selected_collection"
    bl_label = "Export Collection of Selected"
    bl_description = "Export the immediate collection containing the selected object as a whole, using configured export settings (ignores 'Sub-Collections as Single' mode)"

    def find_immediate_collection(self, obj):
        """Find the immediate (lowest-level) collection containing the object"""
        # Start with all collections that contain this object
        containing_collections = []
        for collection in bpy.data.collections:
            if obj.name in collection.objects:
                containing_collections.append(collection)

        if not containing_collections:
            return None

        # If only one collection, return it
        if len(containing_collections) == 1:
            return containing_collections[0]

        # Find the most specific (deepest) collection by checking which collections
        # are children of other collections in the list
        # A collection is "immediate" if it's not a parent of any other collection in the list
        immediate_collection = None
        for coll in containing_collections:
            is_parent = False
            for other_coll in containing_collections:
                if coll != other_coll and self.is_parent_of(coll, other_coll):
                    is_parent = True
                    break

            # If this collection is not a parent of any other, it's more immediate
            if not is_parent:
                immediate_collection = coll
                break

        return immediate_collection if immediate_collection else containing_collections[0]

    def is_parent_of(self, parent_coll, child_coll):
        """Check if parent_coll is a parent (or ancestor) of child_coll"""
        # Check direct children by comparing collection objects
        for child in parent_coll.children:
            if child == child_coll:
                return True

        # Check recursively through all descendants
        for child in parent_coll.children:
            if self.is_parent_of(child, child_coll):
                return True

        return False

    def execute(self, context):
        # Force OBJECT mode
        if bpy.ops.object.mode_set.poll():
            bpy.ops.object.mode_set(mode='OBJECT')

        # Get active object
        active_obj = context.active_object
        if not active_obj:
            self.report({'WARNING'}, "No object selected")
            return {'CANCELLED'}

        # Find the immediate collection containing this object
        target_collection = self.find_immediate_collection(active_obj)

        if not target_collection:
            self.report({'WARNING'}, f"Object '{active_obj.name}' is not in any collection")
            return {'CANCELLED'}

        # Find or create export item for this collection
        props = context.scene.mass_exporter_props
        export_item = None
        for item in props.collection_items:
            if item.collection == target_collection:
                export_item = item
                break

        # If not in export list, we need an export path from somewhere
        if not export_item:
            # Try to find a parent collection in the export list and use its settings
            parent_export_item = self.find_parent_export_item(target_collection, props)

            if not parent_export_item:
                self.report({'WARNING'}, f"Collection '{target_collection.name}' is not in export list and no parent collection found")
                return {'CANCELLED'}

            if not parent_export_item.export_path:
                self.report({'WARNING'}, f"No export path set for collection hierarchy")
                return {'CANCELLED'}

            # Temporary export item inheriting EVERY parent setting; only the
            # parent's custom filename is dropped so the file is named after
            # this collection.
            export_item = props.collection_items.add()
            _copy_item_settings(parent_export_item, export_item)
            export_item.collection = target_collection
            export_item.export_enabled = True
            export_item.single_fbx_custom_name = ""

            temp_created = True
        else:
            if not export_item.export_path:
                self.report({'WARNING'}, f"No export path set for collection '{target_collection.name}'")
                return {'CANCELLED'}
            temp_created = False

        # Store original selection
        original_selection = context.selected_objects.copy()
        original_active = context.active_object

        # Export the collection as a whole: switch off the sub-collection split
        # for the duration (restored in finally on every exit path)
        original_export_subcollections = export_item.export_subcollections_as_single
        export_item.export_subcollections_as_single = False
        try:
            if MASSEXPORTER_OT_export_all.export_collection(self, context, props, export_item):
                self.report({'INFO'}, f"Exported collection '{target_collection.name}'")
                return {'FINISHED'}
            self.report({'ERROR'}, f"Failed to export collection '{target_collection.name}'")
            return {'CANCELLED'}
        finally:
            if temp_created:
                props.collection_items.remove(len(props.collection_items) - 1)
            else:
                export_item.export_subcollections_as_single = original_export_subcollections

            # Restore selection
            batch_deselect_all(context)
            for obj in original_selection:
                if obj.name in bpy.data.objects:
                    obj.select_set(True)
            if original_active and original_active.name in bpy.data.objects:
                context.view_layer.objects.active = original_active

    def find_parent_export_item(self, collection, props):
        """Find a parent collection in the export list"""
        for item in props.collection_items:
            if item.collection and self.is_parent_of(item.collection, collection):
                return item
        return None

class MASSEXPORTER_OT_export_selected_subcollections(Operator):
    """Export sub-collections of currently selected object's collection"""
    bl_idname = "massexporter.export_selected_subcollections"
    bl_label = "Export Sub-Collections of Selected"
    bl_description = "Export each sub-collection of the collection containing the selected object, using the collection's configured export settings"

    def find_immediate_collection(self, obj):
        """Find the immediate (lowest-level) collection containing the object"""
        # Start with all collections that contain this object
        containing_collections = []
        for collection in bpy.data.collections:
            if obj.name in collection.objects:
                containing_collections.append(collection)

        if not containing_collections:
            return None

        # If only one collection, return it
        if len(containing_collections) == 1:
            return containing_collections[0]

        # Find the most specific (deepest) collection by checking which collections
        # are children of other collections in the list
        # A collection is "immediate" if it's not a parent of any other collection in the list
        immediate_collection = None
        for coll in containing_collections:
            is_parent = False
            for other_coll in containing_collections:
                if coll != other_coll and self.is_parent_of(coll, other_coll):
                    is_parent = True
                    break

            # If this collection is not a parent of any other, it's more immediate
            if not is_parent:
                immediate_collection = coll
                break

        return immediate_collection if immediate_collection else containing_collections[0]

    def is_parent_of(self, parent_coll, child_coll):
        """Check if parent_coll is a parent (or ancestor) of child_coll"""
        # Check direct children by comparing collection objects
        for child in parent_coll.children:
            if child == child_coll:
                return True

        # Check recursively through all descendants
        for child in parent_coll.children:
            if self.is_parent_of(child, child_coll):
                return True

        return False

    def find_parent_export_item(self, collection, props):
        """Find a parent collection in the export list"""
        for item in props.collection_items:
            if item.collection and self.is_parent_of(item.collection, collection):
                return item
        return None

    def execute(self, context):
        # Force OBJECT mode
        if bpy.ops.object.mode_set.poll():
            bpy.ops.object.mode_set(mode='OBJECT')

        # Get active object
        active_obj = context.active_object
        if not active_obj:
            self.report({'WARNING'}, "No object selected")
            return {'CANCELLED'}

        # Find the immediate collection containing this object
        target_collection = self.find_immediate_collection(active_obj)

        if not target_collection:
            self.report({'WARNING'}, f"Object '{active_obj.name}' is not in any collection")
            return {'CANCELLED'}

        # Check if collection has sub-collections
        if not target_collection.children:
            self.report({'WARNING'}, f"Collection '{target_collection.name}' has no sub-collections")
            return {'CANCELLED'}

        # Find or get export settings
        props = context.scene.mass_exporter_props
        export_item = None
        for item in props.collection_items:
            if item.collection == target_collection:
                export_item = item
                break

        # If not in export list, try to find parent collection settings
        if not export_item:
            parent_export_item = self.find_parent_export_item(target_collection, props)

            if not parent_export_item:
                self.report({'WARNING'}, f"Collection '{target_collection.name}' is not in export list and no parent collection found")
                return {'CANCELLED'}

            if not parent_export_item.export_path:
                self.report({'WARNING'}, f"No export path set for collection hierarchy")
                return {'CANCELLED'}

            # Use parent's settings as reference
            reference_item = parent_export_item
        else:
            if not export_item.export_path:
                self.report({'WARNING'}, f"No export path set for collection '{target_collection.name}'")
                return {'CANCELLED'}
            reference_item = export_item

        # Store original selection
        original_selection = context.selected_objects.copy()
        original_active = context.active_object

        exported_count = 0
        temp_items_created = 0
        try:
            for sub_collection in target_collection.children:
                # Temporary export item with every reference setting; the
                # custom filename would make every sub-collection overwrite
                # the same file, so it is dropped.
                temp_item = props.collection_items.add()
                temp_items_created += 1
                _copy_item_settings(reference_item, temp_item)
                temp_item.collection = sub_collection
                temp_item.export_enabled = True
                temp_item.single_fbx_custom_name = ""

                if MASSEXPORTER_OT_export_all.export_collection(self, context, props, temp_item):
                    exported_count += 1

            if exported_count > 0:
                self.report({'INFO'}, f"Exported {exported_count} sub-collections from '{target_collection.name}'")
                return {'FINISHED'}
            else:
                self.report({'ERROR'}, "No sub-collections were exported")
                return {'CANCELLED'}
        finally:
            # Temporary items were appended last; remove them on every exit path
            for _ in range(temp_items_created):
                props.collection_items.remove(len(props.collection_items) - 1)
            # Restore selection
            batch_deselect_all(context)
            for obj in original_selection:
                if obj.name in bpy.data.objects:
                    obj.select_set(True)
            if original_active and original_active.name in bpy.data.objects:
                context.view_layer.objects.active = original_active

# Panels
class MASSEXPORTER_OT_export_selected_objects(Operator):
    """Export collections of selected objects using their configured export settings"""
    bl_idname = "massexporter.export_selected_objects"
    bl_label = "Export Selected Object(s)"
    bl_description = "Export the collections containing selected objects, using each collection's configured export settings (merge, sub-collections, etc.)"

    def find_immediate_collection(self, obj):
        """Find the immediate (lowest-level) collection containing the object"""
        # Start with all collections that contain this object
        containing_collections = []
        for collection in bpy.data.collections:
            if obj.name in collection.objects:
                containing_collections.append(collection)

        if not containing_collections:
            return None

        # If only one collection, return it
        if len(containing_collections) == 1:
            return containing_collections[0]

        # Find the most specific (deepest) collection
        immediate_collection = None
        for coll in containing_collections:
            is_parent = False
            for other_coll in containing_collections:
                if coll != other_coll and self.is_parent_of(coll, other_coll):
                    is_parent = True
                    break

            if not is_parent:
                immediate_collection = coll
                break

        return immediate_collection if immediate_collection else containing_collections[0]

    def is_parent_of(self, parent_coll, child_coll):
        """Check if parent_coll is a parent (or ancestor) of child_coll"""
        for child in parent_coll.children:
            if child == child_coll:
                return True

        for child in parent_coll.children:
            if self.is_parent_of(child, child_coll):
                return True

        return False

    def find_parent_export_item(self, collection, props):
        """Find a parent collection in the export list"""
        for item in props.collection_items:
            if item.collection and self.is_parent_of(item.collection, collection):
                return item
        return None


    def find_parent_collection(self, collection):
        """Find the direct parent collection of the given collection"""
        for coll in bpy.data.collections:
            if collection.name in coll.children:
                return coll
        return None

    def execute(self, context):
        """Export ONLY the selected objects, not entire collections.

        Wrapped in a single try/finally so every exit path (early warning
        returns, exceptions mid-export, successful completion) restores the
        original selection and active object. Previously, early returns
        skipped cleanup, which could leave the scene in a partially-modified
        state that made subsequent `Export All` calls hang.
        """
        # Snapshot state BEFORE touching the scene so cleanup can always run.
        original_selection = context.selected_objects.copy()
        original_active = context.active_object

        # Force OBJECT mode
        if bpy.ops.object.mode_set.poll():
            bpy.ops.object.mode_set(mode='OBJECT')

        props = context.scene.mass_exporter_props
        exported_count = 0
        cancelled = False

        try:
            # Get selected mesh objects
            selected_objects = [obj for obj in context.selected_objects if obj.type == 'MESH']
            if not selected_objects:
                self.report({'WARNING'}, "No mesh objects selected")
                cancelled = True
                return {'CANCELLED'}

            # Group selected objects by their immediate collection
            collection_groups = {}
            for obj in selected_objects:
                coll = self.find_immediate_collection(obj)
                if coll:
                    collection_groups.setdefault(coll, []).append(obj)

            if not collection_groups:
                self.report({'WARNING'}, "Selected objects are not in any collections")
                cancelled = True
                return {'CANCELLED'}

            # Export each collection group
            for collection, objects in collection_groups.items():
                # Find export item for this collection or its parent
                export_item = None
                for item in props.collection_items:
                    if item.collection == collection:
                        export_item = item
                        break

                # If not found, check parent collections
                if not export_item:
                    parent_export_item = self.find_parent_export_item(collection, props)
                    if not parent_export_item:
                        self.report({'WARNING'}, f"Collection '{collection.name}' not in export list - skipping")
                        continue
                    export_item = parent_export_item

                if not export_item.export_path:
                    self.report({'WARNING'}, f"No export path for collection '{collection.name}' - skipping")
                    continue

                # Respect the same hidden-collection gating the main Export All
                # path uses, so behavior is consistent across entry points.
                is_hidden = MASSEXPORTER_OT_export_all._collection_is_hidden(collection)
                if is_hidden and not props.export_hidden_collections:
                    self.report({'WARNING'},
                                f"Skipping '{collection.name}' — it is hidden and "
                                "'Export Hidden Collections' is off")
                    continue

                # Drive every path through the unhide pipeline so a hidden
                # parent, a sibling-excluded layer collection, or local view
                # cannot silently produce an empty export. Restore is
                # guaranteed in finally, which in turn means two consecutive
                # exports leave the scene in identical state.
                visibility_backup = MASSEXPORTER_OT_export_all._unhide_collection_for_export(collection)
                try:
                    # Check if this is a subcollection and should be exported as a whole
                    parent_coll = self.find_parent_collection(collection)
                    parent_item = None
                    if parent_coll:
                        for item in props.collection_items:
                            if item.collection == parent_coll:
                                parent_item = item
                                break

                    # If parent has "export subcollections as single" enabled, export entire subcollection
                    if parent_item and parent_item.export_subcollections_as_single:
                        if props.debug_mode:
                            print(f"Exporting entire subcollection '{collection.name}' (parent has subcollections-as-single enabled)")
                        sub_objects = MASSEXPORTER_OT_export_all.get_collection_objects(self, collection)
                        if MASSEXPORTER_OT_export_all.export_objects_as_single(
                                self, context, props, sub_objects, collection.name, _export_dir(export_item), item=export_item):
                            exported_count += 1
                    elif export_item.use_suffix_grouping and _has_enabled_suffixes(props):
                        # Selection only: group the selected meshes by base name
                        groups = find_suffix_groups(objects, props.suffix_items, debug=props.debug_mode)
                        for base_name, members in groups.items():
                            if MASSEXPORTER_OT_export_all.export_objects_as_single(
                                    self, context, props, [o for o, _s in members], base_name,
                                    _export_dir(export_item), item=export_item):
                                exported_count += 1
                    elif export_item.merge_to_single and len(objects) > 1:
                        group_name = f"{collection.name}_selected"
                        if MASSEXPORTER_OT_export_all.export_objects_as_single(
                                self, context, props, objects, group_name, _export_dir(export_item), item=export_item):
                            exported_count += 1
                    else:
                        if props.debug_mode:
                            print(f"Exporting {len(objects)} selected objects from '{collection.name}'")
                        for obj in objects:
                            if MASSEXPORTER_OT_export_all.export_single_object(
                                    self, context, props, obj, _export_dir(export_item), item=export_item):
                                exported_count += 1
                finally:
                    MASSEXPORTER_OT_export_all._restore_collection_for_export(visibility_backup)

            if exported_count > 0:
                self.report({'INFO'}, f"Exported {exported_count} object(s)")
                return {'FINISHED'}
            self.report({'ERROR'}, "No objects were exported")
            cancelled = True
            return {'CANCELLED'}

        finally:
            # Always restore selection + active, even on early warning returns.
            # This prevents leaked `__mexport_*` renames from partial runs from
            # breaking the next export.
            batch_deselect_all(context)
            for obj in original_selection:
                if obj.name in bpy.data.objects:
                    obj.select_set(True)
            if original_active and original_active.name in bpy.data.objects:
                context.view_layer.objects.active = original_active
            # Double-check: if anything left a temp copy or `__mexport_*`
            # rename behind, undo it now so the next export starts clean.
            _recover_stale_temp_objects()


class MASSEXPORTER_PT_main_panel(Panel):
    """Main Mass Exporter Panel"""
    bl_label = "Mass Collection Exporter"
    bl_idname = "MASSEXPORTER_PT_main_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Mass Exporter"

    def draw(self, context):
        layout = self.layout
        props = context.scene.mass_exporter_props

        # Export button
        layout.operator("massexporter.export_all", text="Export All Collections", icon='EXPORT')
        layout.prop(props, "export_hidden_collections")

        layout.separator()

        # Quick export from selection — foldable so people can collapse it
        # once they've muscle-memoried the buttons.
        header, body = layout.panel("massexporter_main_quick_export", default_closed=False)
        header.label(text="Quick Export from Selection", icon='RESTRICT_SELECT_OFF')
        if body is not None:
            row = body.row()
            row.scale_y = 1.2
            row.operator("massexporter.export_selected_objects", icon='OBJECT_DATA')
            row = body.row()
            row.scale_y = 1.2
            row.operator("massexporter.export_selected_collection", icon='OUTLINER_COLLECTION')
            row = body.row()
            row.scale_y = 1.2
            row.operator("massexporter.export_selected_subcollections", icon='OUTLINER_OB_GROUP_INSTANCE')

        layout.separator()

        # Debug mode
        layout.prop(props, "debug_mode")

class MASSEXPORTER_PT_debug(Panel):
    """Debug Controls Panel"""
    bl_label = "Debug Controls"
    bl_idname = "MASSEXPORTER_PT_debug"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Mass Exporter"
    bl_parent_id = "MASSEXPORTER_PT_main_panel"
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        layout = self.layout

        # Move empties button
        row = layout.row()
        row.scale_y = 1.2
        row.operator("massexporter.move_empties_to_origin", text="Move Empties to Origin", icon='OUTLINER_OB_EMPTY')

        # Join empties button
        row = layout.row()
        row.scale_y = 1.2
        row.operator("massexporter.join_empties", text="Join Empties (Preview)", icon='MOD_SOLIDIFY')

class MASSEXPORTER_PT_collections(Panel):
    """Collection Options Panel"""
    bl_label = "Collection Options"
    bl_idname = "MASSEXPORTER_PT_collections"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Mass Exporter"
    bl_parent_id = "MASSEXPORTER_PT_main_panel"

    def draw(self, context):
        layout = self.layout
        props = context.scene.mass_exporter_props

        # Collection list
        row = layout.row()
        row.template_list(
            "MASSEXPORTER_UL_collections", "",
            props, "collection_items",
            props, "active_collection_index"
        )

        # Add/Remove buttons
        col = row.column(align=True)
        col.operator("massexporter.add_collection", icon='ADD', text="")
        col.operator("massexporter.remove_collection", icon='REMOVE', text="")

        # Enhanced options for active collection
        if props.collection_items and len(props.collection_items) > props.active_collection_index:
            active_item = props.collection_items[props.active_collection_index]

            layout.separator()
            layout.label(text="Enhanced Export Options:")

            # Whole-collection-as-one-file — when on, this overrides the other
            # per-collection modes (suffix grouping / subcollection split /
            # empty origins). UI greys those out so the precedence is visible.
            single_box = layout.box()
            single_box.prop(active_item, "export_as_single_fbx")
            if active_item.export_as_single_fbx:
                sub = single_box.column(align=True)
                sub.prop(active_item, "single_fbx_custom_name", text="Filename")
                if not (active_item.single_fbx_custom_name or "").strip():
                    info = single_box.row()
                    info.label(text=f"Falls back to: {active_item.collection.name if active_item.collection else '<collection name>'}", icon='INFO')
                single_box.label(text="Includes meshes, armatures, empties, curves, etc.", icon='ARMATURE_DATA')

            sub_modes = layout.column()
            sub_modes.enabled = not active_item.export_as_single_fbx
            # Order mirrors export precedence: suffix grouping > subcollections > empty origins.
            sub_modes.prop(active_item, "use_suffix_grouping")
            sub_modes.prop(active_item, "export_subcollections_as_single")
            sub_modes.prop(active_item, "use_empty_origins")

            if active_item.use_empty_origins:
                header, body = sub_modes.panel("massexporter_collections_join_options", default_closed=True)
                header.label(text="Join Options", icon='MOD_SOLIDIFY')
                if body is not None:
                    body.prop(active_item, "join_empty_children")
                    if active_item.join_empty_children:
                        body.prop(active_item, "apply_modifiers_before_join")
                        if active_item.apply_modifiers_before_join:
                            body.prop(active_item, "apply_only_visible")

            # Per-collection move-to-center applies to whole-collection-as-one-file
            # too, so it lives outside the sub_modes gating.
            layout.separator()
            layout.prop(active_item, "move_to_center")

class MASSEXPORTER_PT_transform(Panel):
    """Transform Options Panel"""
    bl_label = "Transform Options"
    bl_idname = "MASSEXPORTER_PT_transform"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Mass Exporter"
    bl_parent_id = "MASSEXPORTER_PT_main_panel"

    def draw(self, context):
        layout = self.layout
        props = context.scene.mass_exporter_props

        layout.prop(props, "apply_transforms")
        layout.label(text="(centering is per-collection via 'Move to Center')", icon='INFO')

        layout.separator()
        layout.label(text="Transform Axis Settings:")

        row = layout.row()
        row.prop(props, "axis_forward", text="Forward")
        row.prop(props, "axis_up", text="Up")

class MASSEXPORTER_PT_materials(Panel):
    """Material Options Panel"""
    bl_label = "Material Options"
    bl_idname = "MASSEXPORTER_PT_materials"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Mass Exporter"
    bl_parent_id = "MASSEXPORTER_PT_main_panel"

    def draw(self, context):
        layout = self.layout
        props = context.scene.mass_exporter_props

        layout.prop(props, "material_mode", expand=True)

        row = layout.row()
        row.enabled = _material_mode(props) != 'KEEP'
        row.prop(props, "override_material")
        layout.prop(props, "add_m_prefix")

class MASSEXPORTER_PT_export(Panel):
    """File Export Options Panel"""
    bl_label = "File Export Options"
    bl_idname = "MASSEXPORTER_PT_export"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Mass Exporter"
    bl_parent_id = "MASSEXPORTER_PT_main_panel"

    def draw(self, context):
        layout = self.layout
        props = context.scene.mass_exporter_props

        layout.prop(props, "export_format")

        # Show FBX-specific options when FBX is selected
        if props.export_format == 'FBX':
            header, body = layout.panel("massexporter_export_fbx_options", default_closed=False)
            header.label(text="FBX Options", icon='EXPORT')
            if body is not None:
                body.prop(props, "apply_scaling")
                body.prop(props, "bake_space_transform")

                body.separator()
                body.label(text="Axis Orientation:")
                row = body.row()
                row.prop(props, "axis_forward", text="Forward")
                row.prop(props, "axis_up", text="Up")

                body.separator()
                body.label(text="Armature:", icon='ARMATURE_DATA')
                row = body.row()
                row.prop(props, "primary_bone_axis", text="Primary")
                row = body.row()
                row.prop(props, "secondary_bone_axis", text="Secondary")
                body.prop(props, "armature_nodetype")
                body.prop(props, "use_armature_deform_only")
                body.prop(props, "add_leaf_bones")

            header, body = layout.panel("massexporter_export_unity_tips", default_closed=True)
            header.label(text="Unity Import Tips", icon='INFO')
            if body is not None:
                body.label(text="• Apply Scaling: Use 'FBX Units Scale'")
                body.label(text="• Apply Transform: Enable for static meshes")
                body.label(text="   (experimental — disable for rigs / animation)")
                body.label(text="• Default: -Z Forward, Y Up for Unity")


class MASSEXPORTER_PT_modifier_rig(Panel):
    """Modifier & Rig Options Panel

    Houses options that affect modifier evaluation and rig/armature handling
    during export — the animation-adjacent settings that used to live at the
    bottom of File Export Options.
    """
    bl_label = "Modifier & Rig Options"
    bl_idname = "MASSEXPORTER_PT_modifier_rig"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Mass Exporter"
    bl_parent_id = "MASSEXPORTER_PT_main_panel"

    def draw(self, context):
        layout = self.layout
        props = context.scene.mass_exporter_props

        header, body = layout.panel("massexporter_modrig_modifiers", default_closed=False)
        header.label(text="Modifiers", icon='MODIFIER')
        if body is not None:
            body.prop(props, "apply_modifiers")
            sub = body.row()
            sub.enabled = props.apply_modifiers
            sub.prop(props, "apply_only_visible_modifiers")

        header, body = layout.panel("massexporter_modrig_armature", default_closed=False)
        header.label(text="Rig / Armature", icon='ARMATURE_DATA')
        if body is not None:
            body.prop(props, "export_rig_with_mesh")
            sub = body.row()
            sub.enabled = props.apply_modifiers
            sub.prop(props, "skip_armature_modifier")


class MASSEXPORTER_PT_suffix_grouping(Panel):
    """Suffix Grouping Panel"""
    bl_label = "Suffix Grouping"
    bl_idname = "MASSEXPORTER_PT_suffix_grouping"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Mass Exporter"
    bl_parent_id = "MASSEXPORTER_PT_main_panel"

    def draw(self, context):
        layout = self.layout
        props = context.scene.mass_exporter_props

        header, body = layout.panel("massexporter_suffix_about", default_closed=True)
        header.label(text="About Suffix Grouping", icon='INFO')
        if body is not None:
            body.label(text="Group objects by base name + suffix")
            body.label(text="Example: cube + cube_COL = cube.fbx")

        # Suffix list with add/remove buttons
        row = layout.row()
        row.template_list("MASSEXPORTER_UL_suffixes", "", props, "suffix_items",
                         props, "active_suffix_index", rows=4)

        col = row.column(align=True)
        col.operator("massexporter.add_suffix", icon='ADD', text="")
        col.operator("massexporter.remove_suffix", icon='REMOVE', text="")

        # Show description for active suffix
        if props.suffix_items and len(props.suffix_items) > props.active_suffix_index:
            active_suffix = props.suffix_items[props.active_suffix_index]
            layout.separator()
            box = layout.box()
            box.label(text=f"Description: {active_suffix.description}", icon='TEXT')

        layout.separator()

        # Add default suffixes button
        layout.operator("massexporter.add_default_suffixes",
                       text="Add Default Suffixes",
                       icon='PRESET')

# Registration
classes = [
    # Property Groups (must be registered first)
    SuffixItem,
    CollectionExportItem,
    MassExporterProperties,

    # UI Lists
    MASSEXPORTER_UL_collections,
    MASSEXPORTER_UL_suffixes,

    # Operators
    MASSEXPORTER_OT_move_empties_to_origin,
    MASSEXPORTER_OT_join_empties,
    MASSEXPORTER_OT_add_collection,
    MASSEXPORTER_OT_remove_collection,
    MASSEXPORTER_OT_toggle_collection_visibility,
    MASSEXPORTER_OT_select_folder,
    MASSEXPORTER_OT_add_suffix,
    MASSEXPORTER_OT_remove_suffix,
    MASSEXPORTER_OT_add_default_suffixes,
    MASSEXPORTER_OT_export_all,
    MASSEXPORTER_OT_export_selected_collection,
    MASSEXPORTER_OT_export_selected_subcollections,
    MASSEXPORTER_OT_export_selected_objects,

    # Panels — registration order determines the vertical order of
    # sub-panels under the main panel in the N-Panel.
    MASSEXPORTER_PT_main_panel,
    MASSEXPORTER_PT_collections,
    MASSEXPORTER_PT_transform,
    MASSEXPORTER_PT_materials,
    MASSEXPORTER_PT_modifier_rig,
    MASSEXPORTER_PT_export,
    MASSEXPORTER_PT_suffix_grouping,
    MASSEXPORTER_PT_debug,
]

def _draw_viewport_header_export_all(self, context):
    """Small 'Export All' button in the 3D Viewport header.

    Sits at the right end of the header (appended after the stock
    Selectability/Visibility/Gizmo/Overlay toggles). Greyed out when no
    collection is enabled for export so the click surfaces the reason via
    tooltip rather than running a no-op.
    """
    scene = getattr(context, 'scene', None)
    props = getattr(scene, 'mass_exporter_props', None) if scene else None
    if props is None:
        return
    enabled_count = sum(
        1 for item in props.collection_items
        if item.export_enabled and item.collection is not None
    )
    layout = self.layout
    row = layout.row(align=True)
    row.separator()
    sub = row.row(align=True)
    sub.enabled = enabled_count > 0
    sub.operator("massexporter.export_all", text="", icon='EXPORT')


def register():
    for cls in classes:
        bpy.utils.register_class(cls)

    bpy.types.Scene.mass_exporter_props = PointerProperty(type=MassExporterProperties)
    bpy.app.handlers.load_post.append(_migrate_material_flags)
    bpy.types.VIEW3D_HT_header.append(_draw_viewport_header_export_all)

def unregister():
    if _migrate_material_flags in bpy.app.handlers.load_post:
        bpy.app.handlers.load_post.remove(_migrate_material_flags)
    try:
        bpy.types.VIEW3D_HT_header.remove(_draw_viewport_header_export_all)
    except (ValueError, AttributeError):
        pass

    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)

    del bpy.types.Scene.mass_exporter_props

if __name__ == "__main__":
    register()
