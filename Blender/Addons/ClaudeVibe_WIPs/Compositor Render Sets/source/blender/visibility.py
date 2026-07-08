"""Collection / modifier / object visibility management around renders.

IMPORTANT: none of these functions ever touch the ROOT (master) layer
collection. Hiding it - or syncing its state onto the master scene
collection's hide_render - blanks the entire view layer.
"""

import bpy

from .compat import dbg


def get_active_render_set(context):
    """Get the currently active render set, or None."""
    props = context.scene.compositor_render_sets
    if 0 <= props.active_set_index < len(props.render_sets):
        return props.render_sets[props.active_set_index]
    return None


def get_collections_from_set(render_set):
    """List of actual collection datablocks from a render set."""
    return [item.collection for item in render_set.collections if item.collection]


def iter_layer_collections(view_layer):
    """Yield every layer collection under the root, excluding the root itself."""
    def walk(layer_coll):
        for child in layer_coll.children:
            yield child
            yield from walk(child)
    yield from walk(view_layer.layer_collection)


def build_layer_collection_map(view_layer):
    """Map {collection: layer_collection} for O(1) lookups (root excluded).

    A collection linked into several parents keeps its FIRST layer
    collection, matching the old recursive-search behavior.
    """
    mapping = {}
    for layer_coll in iter_layer_collections(view_layer):
        mapping.setdefault(layer_coll.collection, layer_coll)
    return mapping


def find_layer_collection(view_layer, collection):
    """Find the LayerCollection for a Collection (root excluded)."""
    for layer_coll in iter_layer_collections(view_layer):
        if layer_coll.collection == collection:
            return layer_coll
    return None


def collect_objects(collections):
    """All objects in the given collections, including nested sub-collections."""
    objects = set()
    for collection in collections:
        if collection:
            objects.update(collection.all_objects)
    return objects


def apply_collection_visibility(render_set, context, layer_map=None):
    """Show the set's collections in viewport and apply their render toggles."""
    if layer_map is None:
        layer_map = build_layer_collection_map(context.view_layer)

    for item in render_set.collections:
        if item.collection:
            layer_collection = layer_map.get(item.collection)
            if layer_collection:
                layer_collection.hide_viewport = False
            item.collection.hide_render = not item.render_visibility


def apply_render_visibility_overrides(render_set):
    """Re-apply per-collection render toggles (call AFTER visibility sync)."""
    dbg("[RENDER VISIBILITY] Applying render visibility overrides:")
    for item in render_set.collections:
        if item.collection:
            item.collection.hide_render = not item.render_visibility
            dbg(f"  '{item.collection.name}': "
                f"hide_render = {item.collection.hide_render}")


def sync_visibility_to_render(context):
    """Sync collection hide_render to viewport visibility (eye icon).

    Returns {collection_name: original_hide_render} or None when disabled.
    """
    props = context.scene.compositor_render_sets
    if not props.settings.sync_visibility:
        return None

    original_states = {}
    dbg("[SYNC] Syncing render visibility to viewport (eye icon):")
    for layer_coll in iter_layer_collections(context.view_layer):
        collection = layer_coll.collection
        original_states[collection.name] = collection.hide_render
        collection.hide_render = layer_coll.hide_viewport
        dbg(f"  '{collection.name}': hide_render = {collection.hide_render}")

    return original_states


def restore_render_visibility(original_states):
    """Restore hide_render states captured by sync_visibility_to_render."""
    if not original_states:
        return
    dbg("[RESTORE] Restoring original render visibility:")
    for coll_name, hide_state in original_states.items():
        collection = bpy.data.collections.get(coll_name)
        if collection:
            collection.hide_render = hide_state
            dbg(f"  '{coll_name}': hide_render = {hide_state}")


def save_viewport_visibility(context):
    """Snapshot {collection_name: hide_viewport} for all layer collections."""
    original_states = {}
    for layer_coll in iter_layer_collections(context.view_layer):
        original_states[layer_coll.collection.name] = layer_coll.hide_viewport
    print(f"[SAVE] Saved viewport visibility for {len(original_states)} "
          "collection(s)")
    return original_states


def restore_viewport_visibility(context, original_states):
    """Restore viewport visibility captured by save_viewport_visibility."""
    if not original_states:
        return
    dbg("[RESTORE] Restoring original viewport visibility:")
    for layer_coll in iter_layer_collections(context.view_layer):
        name = layer_coll.collection.name
        if name in original_states:
            layer_coll.hide_viewport = original_states[name]
            dbg(f"  '{name}': hide_viewport = {original_states[name]}")


def hide_all_collections(context):
    """Hide every layer collection in the viewport (root excluded)."""
    for layer_coll in iter_layer_collections(context.view_layer):
        layer_coll.hide_viewport = True


def sync_modifiers_to_viewport(context, collections_filter=None):
    """Sync modifier show_render to show_viewport (WYSIWYG for modifiers).

    Returns {object_name: {modifier_name: original_show_render}} or None
    when disabled.
    """
    props = context.scene.compositor_render_sets
    if not props.settings.sync_modifiers:
        return None

    if collections_filter and props.settings.only_sync_modifiers_in_renderset:
        objects_to_process = collect_objects(collections_filter)
        dbg(f"[SYNC MODIFIERS] Filtering to {len(objects_to_process)} "
            "objects in render set collections")
    else:
        objects_to_process = bpy.data.objects
        dbg("[SYNC MODIFIERS] Syncing modifiers on ALL objects in scene")

    original_states = {}
    for obj in objects_to_process:
        if not getattr(obj, 'modifiers', None):
            continue
        obj_modifiers = {}
        for mod in obj.modifiers:
            obj_modifiers[mod.name] = mod.show_render
            mod.show_render = mod.show_viewport
            dbg(f"  '{obj.name}' > '{mod.name}': show_render = {mod.show_render}")
        original_states[obj.name] = obj_modifiers

    print(f"[SYNC MODIFIERS] Synced modifiers on {len(original_states)} object(s)")
    return original_states


def restore_modifier_settings(original_states):
    """Restore show_render captured by sync_modifiers_to_viewport."""
    if not original_states:
        return
    dbg("[RESTORE MODIFIERS] Restoring original modifier settings:")
    for obj_name, modifiers in original_states.items():
        obj = bpy.data.objects.get(obj_name)
        if not obj:
            continue
        for mod_name, show_render in modifiers.items():
            mod = obj.modifiers.get(mod_name)
            if mod:
                mod.show_render = show_render
                dbg(f"  '{obj_name}' > '{mod_name}': show_render = {show_render}")


def sync_objects_to_viewport(context, collections_to_sync=None):
    """Sync object hide_render to hide_viewport for objects in the given
    collections. Returns {object_name: original_hide_render} or None.
    """
    props = context.scene.compositor_render_sets
    if not props.settings.sync_objects or not collections_to_sync:
        return None

    original_states = {}
    for obj in collect_objects(collections_to_sync):
        original_states[obj.name] = obj.hide_render
        obj.hide_render = obj.hide_viewport
        dbg(f"  Object '{obj.name}': hide_render = {obj.hide_render}")

    print(f"[SYNC OBJECTS] Synced {len(original_states)} object(s)")
    return original_states


def restore_object_settings(original_states):
    """Restore hide_render captured by sync_objects_to_viewport."""
    if not original_states:
        return
    dbg("[RESTORE OBJECTS] Restoring original object render visibility:")
    for obj_name, hide_render in original_states.items():
        obj = bpy.data.objects.get(obj_name)
        if obj:
            obj.hide_render = hide_render
            dbg(f"  Object '{obj_name}': hide_render = {hide_render}")


def tag_redraw_3d_and_outliner(context):
    """Refresh viewport and outliner after visibility changes."""
    for area in context.screen.areas:
        if area.type in {'VIEW_3D', 'OUTLINER'}:
            area.tag_redraw()
