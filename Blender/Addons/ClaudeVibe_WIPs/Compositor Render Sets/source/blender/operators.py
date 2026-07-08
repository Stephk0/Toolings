"""Operators for Compositor Render Sets."""

import json

import bpy
from bpy.props import BoolProperty, EnumProperty, IntProperty, StringProperty
from bpy.types import Operator

from .compat import (
    dbg,
    get_compositor_node_tree,
    get_output_node_base_path,
    get_output_node_file_slots,
    get_slot_path,
    set_output_node_base_path,
)
from .node_state import (
    cache_node_state,
    configure_node_for_set,
    find_file_output_node,
    mute_unused_output_nodes,
    restore_node_state,
    restore_output_nodes_mute_state,
    snapshot_output_nodes_mute,
)
from .properties import log_message
from .visibility import (
    apply_collection_visibility,
    apply_render_visibility_overrides,
    build_layer_collection_map,
    get_active_render_set,
    get_collections_from_set,
    hide_all_collections,
    iter_layer_collections,
    restore_modifier_settings,
    restore_object_settings,
    restore_render_visibility,
    restore_viewport_visibility,
    save_viewport_visibility,
    sync_modifiers_to_viewport,
    sync_objects_to_viewport,
    sync_visibility_to_render,
    tag_redraw_3d_and_outliner,
)


# ============================================================================
# Operators - Render Set Management
# ============================================================================

class COMPRS_OT_AddRenderSet(Operator):
    """Add a new render set"""
    bl_idname = "comprs.add_render_set"
    bl_label = "Add Render Set"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        props = context.scene.compositor_render_sets
        new_set = props.render_sets.add()
        new_set.name = f"RenderSet_{len(props.render_sets)}"
        props.active_set_index = len(props.render_sets) - 1

        log_message(context, f"Added new render set: {new_set.name}")
        return {'FINISHED'}


class COMPRS_OT_RemoveRenderSet(Operator):
    """Remove the current render set"""
    bl_idname = "comprs.remove_render_set"
    bl_label = "Remove Render Set"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        props = context.scene.compositor_render_sets

        if len(props.render_sets) == 0:
            self.report({'WARNING'}, "No render sets to remove")
            return {'CANCELLED'}

        removed_name = props.render_sets[props.active_set_index].name
        props.render_sets.remove(props.active_set_index)

        if props.active_set_index >= len(props.render_sets):
            props.active_set_index = max(0, len(props.render_sets) - 1)

        log_message(context, f"Removed render set: {removed_name}")
        return {'FINISHED'}


class COMPRS_OT_AddCollection(Operator):
    """Add a collection to the current render set"""
    bl_idname = "comprs.add_collection"
    bl_label = "Add Collection"
    bl_options = {'REGISTER', 'UNDO'}

    collection_name: StringProperty(
        name="Collection",
        description="Name of the collection to add"
    )

    def execute(self, context):
        render_set = get_active_render_set(context)
        if not render_set:
            self.report({'WARNING'}, "No active render set")
            return {'CANCELLED'}

        if not self.collection_name:
            self.report({'WARNING'}, "No collection selected")
            return {'CANCELLED'}

        collection = bpy.data.collections.get(self.collection_name)
        if not collection:
            self.report({'WARNING'}, f"Collection '{self.collection_name}' not found")
            return {'CANCELLED'}

        for item in render_set.collections:
            if item.collection == collection:
                self.report({'WARNING'}, f"Collection '{collection.name}' already in set")
                return {'CANCELLED'}

        new_item = render_set.collections.add()
        new_item.collection = collection

        log_message(context, f"Added collection '{collection.name}' to '{render_set.name}'")
        return {'FINISHED'}

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)

    def draw(self, context):
        layout = self.layout
        layout.prop_search(self, "collection_name", bpy.data, "collections", text="Collection")


class COMPRS_OT_RemoveCollection(Operator):
    """Remove a collection from the current render set"""
    bl_idname = "comprs.remove_collection"
    bl_label = "Remove Collection"
    bl_options = {'REGISTER', 'UNDO'}

    index: IntProperty()

    def execute(self, context):
        render_set = get_active_render_set(context)
        if not render_set:
            return {'CANCELLED'}

        if 0 <= self.index < len(render_set.collections):
            item = render_set.collections[self.index]
            coll_name = item.collection.name if item.collection else "Unknown"
            render_set.collections.remove(self.index)
            log_message(context, f"Removed collection '{coll_name}' from '{render_set.name}'")

        return {'FINISHED'}


class COMPRS_OT_AddVisibleCollections(Operator):
    """Add all currently visible collections in viewport (excluding constant collections)"""
    bl_idname = "comprs.add_visible_collections"
    bl_label = "Add Currently Visible Collections"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        props = context.scene.compositor_render_sets
        render_set = get_active_render_set(context)
        if not render_set:
            self.report({'WARNING'}, "No active render set")
            return {'CANCELLED'}

        # Constant collections (global and per-set overrides) are excluded
        constant_collections = {item.collection for item in props.constant_collections
                                if item.collection}
        for rs in props.render_sets:
            if rs.override_constant_collections:
                constant_collections.update(
                    item.collection for item in rs.constant_collections
                    if item.collection)

        existing_collections = set(get_collections_from_set(render_set))

        visible_collections = [
            layer_coll.collection
            for layer_coll in iter_layer_collections(context.view_layer)
            if not layer_coll.hide_viewport
            and layer_coll.collection not in constant_collections
            and layer_coll.collection not in existing_collections
        ]

        added_count = 0
        skipped_count = 0
        for collection in visible_collections:
            new_item = render_set.collections.add()
            try:
                new_item.collection = collection
                added_count += 1
            except RuntimeError as e:
                # Assignment can fail for embedded/library collections
                render_set.collections.remove(len(render_set.collections) - 1)
                skipped_count += 1
                print(f"  Skipped collection '{collection.name}': {e}")

        if added_count > 0:
            message = f"Added {added_count} visible collection(s) to '{render_set.name}'"
            if skipped_count > 0:
                message += f" (skipped {skipped_count} embedded collection(s))"
            self.report({'INFO'}, message)
            log_message(context, message)
        elif skipped_count > 0:
            self.report({'INFO'}, f"No collections added. Skipped {skipped_count} embedded collection(s)")
        else:
            self.report({'INFO'}, "No new visible collections to add (all visible collections are already in set or are constant collections)")

        return {'FINISHED'}


class COMPRS_OT_ClearAllCollections(Operator):
    """Remove all collections from the current render set"""
    bl_idname = "comprs.clear_all_collections"
    bl_label = "Clear All Collections"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        render_set = get_active_render_set(context)
        if not render_set:
            self.report({'WARNING'}, "No active render set")
            return {'CANCELLED'}

        collection_count = len(render_set.collections)
        if collection_count == 0:
            self.report({'INFO'}, "No collections to clear")
            return {'CANCELLED'}

        render_set.collections.clear()

        self.report({'INFO'}, f"Cleared {collection_count} collection(s) from '{render_set.name}'")
        log_message(context, f"Cleared {collection_count} collection(s) from '{render_set.name}'")
        return {'FINISHED'}


class COMPRS_OT_AddConstantCollection(Operator):
    """Add a constant render set collection"""
    bl_idname = "comprs.add_constant_collection"
    bl_label = "Add Constant Render Set Collection"
    bl_options = {'REGISTER', 'UNDO'}

    collection_name: StringProperty(
        name="Collection",
        description="Name of the collection to add as constant"
    )

    use_override: BoolProperty(
        name="Use Override",
        description="Add to per-set override instead of global",
        default=False
    )

    def execute(self, context):
        props = context.scene.compositor_render_sets

        if not self.collection_name:
            self.report({'WARNING'}, "No collection selected")
            return {'CANCELLED'}

        collection = bpy.data.collections.get(self.collection_name)
        if not collection:
            self.report({'WARNING'}, f"Collection '{self.collection_name}' not found")
            return {'CANCELLED'}

        if self.use_override:
            render_set = get_active_render_set(context)
            if not render_set:
                self.report({'WARNING'}, "No active render set")
                return {'CANCELLED'}
            target = render_set.constant_collections
            label = f"'{render_set.name}' override"
        else:
            target = props.constant_collections
            label = "global constant collections"

        for item in target:
            if item.collection == collection:
                self.report({'WARNING'}, f"Collection '{collection.name}' already in {label}")
                return {'CANCELLED'}

        new_item = target.add()
        new_item.collection = collection
        log_message(context, f"Added constant render set collection '{collection.name}' to {label}")
        return {'FINISHED'}

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)

    def draw(self, context):
        layout = self.layout
        layout.prop_search(self, "collection_name", bpy.data, "collections", text="Collection")


class COMPRS_OT_RemoveConstantCollection(Operator):
    """Remove a constant render set collection"""
    bl_idname = "comprs.remove_constant_collection"
    bl_label = "Remove Constant Render Set Collection"
    bl_options = {'REGISTER', 'UNDO'}

    index: IntProperty()
    use_override: BoolProperty(default=False)

    def execute(self, context):
        props = context.scene.compositor_render_sets

        if self.use_override:
            render_set = get_active_render_set(context)
            if not render_set:
                return {'CANCELLED'}
            target = render_set.constant_collections
            label = f"'{render_set.name}' override"
        else:
            target = props.constant_collections
            label = "global constant collections"

        if 0 <= self.index < len(target):
            item = target[self.index]
            coll_name = item.collection.name if item.collection else "Unknown"
            target.remove(self.index)
            log_message(context, f"Removed constant render set collection '{coll_name}' from {label}")

        return {'FINISHED'}


# ============================================================================
# Operators - Visibility Control
# ============================================================================

class COMPRS_OT_ToggleSetVisibility(Operator):
    """Toggle viewport visibility of all collections in the current set"""
    bl_idname = "comprs.toggle_set_visibility"
    bl_label = "Show/Hide Set"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        props = context.scene.compositor_render_sets
        render_set = get_active_render_set(context)
        if not render_set:
            self.report({'WARNING'}, "No active render set")
            return {'CANCELLED'}

        if not render_set.collections:
            self.report({'WARNING'}, "No collections in this render set")
            return {'CANCELLED'}

        new_state = not render_set.is_visible

        if props.settings.only_show_renderable:
            collections_to_toggle = [item.collection for item in render_set.collections
                                     if item.collection and item.render_visibility]
        else:
            collections_to_toggle = get_collections_from_set(render_set)

        if not collections_to_toggle:
            if props.settings.only_show_renderable:
                self.report({'WARNING'}, "No renderable collections in this set (all have camera icon off)")
            else:
                self.report({'WARNING'}, "No collections in this render set")
            return {'CANCELLED'}

        layer_map = build_layer_collection_map(context.view_layer)
        for collection in collections_to_toggle:
            layer_collection = layer_map.get(collection)
            if layer_collection:
                layer_collection.hide_viewport = not new_state

        render_set.is_visible = new_state

        state_str = "shown" if new_state else "hidden"
        log_message(context, f"Render set '{render_set.name}' {state_str} in viewport")
        if props.settings.only_show_renderable:
            log_message(context, "  (Only renderable collections affected)")

        tag_redraw_3d_and_outliner(context)
        return {'FINISHED'}


class COMPRS_OT_SoloSet(Operator):
    """Show only the collections in the current set, hide all others"""
    bl_idname = "comprs.solo_set"
    bl_label = "Solo Set"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        props = context.scene.compositor_render_sets
        render_set = get_active_render_set(context)

        if not render_set:
            self.report({'WARNING'}, "No active render set")
            return {'CANCELLED'}

        collections_in_set = get_collections_from_set(render_set)
        if not collections_in_set:
            self.report({'WARNING'}, "No collections in this render set")
            return {'CANCELLED'}

        layer_map = build_layer_collection_map(context.view_layer)

        if props.solo_active:
            # Restore cached visibility
            try:
                if props.cached_visibility:
                    cached = json.loads(props.cached_visibility)
                    for coll_name, hide_state in cached.items():
                        collection = bpy.data.collections.get(coll_name)
                        layer_collection = layer_map.get(collection) if collection else None
                        if layer_collection:
                            layer_collection.hide_viewport = hide_state
                    log_message(context, "Solo mode deactivated")
            except (json.JSONDecodeError, TypeError) as e:
                print(f"[COMPRS ERROR] Restoring solo state: {e}")
            props.solo_active = False
            props.cached_visibility = ""
        else:
            # Cache current visibility, hide everything, show only the set
            visibility_cache = {}
            for layer_coll in iter_layer_collections(context.view_layer):
                visibility_cache[layer_coll.collection.name] = layer_coll.hide_viewport
                layer_coll.hide_viewport = True

            for collection in collections_in_set:
                layer_collection = layer_map.get(collection)
                if layer_collection:
                    layer_collection.hide_viewport = False

            props.cached_visibility = json.dumps(visibility_cache)
            props.solo_active = True
            log_message(context, f"Solo mode activated for '{render_set.name}'")

        tag_redraw_3d_and_outliner(context)
        return {'FINISHED'}


class COMPRS_OT_HideOtherSets(Operator):
    """Toggle visibility of all collections defined in other render sets"""
    bl_idname = "comprs.hide_other_sets"
    bl_label = "Toggle other Sets"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        props = context.scene.compositor_render_sets
        layer_map = build_layer_collection_map(context.view_layer)

        other_render_set_collections = set()
        for i, render_set in enumerate(props.render_sets):
            if i != props.active_set_index:
                other_render_set_collections.update(get_collections_from_set(render_set))

        if not other_render_set_collections:
            self.report({'WARNING'}, "No collections defined in other render sets")
            return {'CANCELLED'}

        if props.other_sets_hidden:
            # Restore visibility
            try:
                if props.cached_other_sets_visibility:
                    cached = json.loads(props.cached_other_sets_visibility)
                    for coll_name, hide_state in cached.items():
                        collection = bpy.data.collections.get(coll_name)
                        layer_collection = layer_map.get(collection) if collection else None
                        if layer_collection:
                            layer_collection.hide_viewport = hide_state
                    log_message(context, f"Restored visibility for {len(cached)} collection(s) from render sets")
            except (json.JSONDecodeError, TypeError) as e:
                print(f"[COMPRS ERROR] Restoring visibility: {e}")
            props.other_sets_hidden = False
            props.cached_other_sets_visibility = ""
        else:
            # Cache current visibility and hide
            visibility_cache = {}
            for collection in other_render_set_collections:
                layer_collection = layer_map.get(collection)
                if layer_collection:
                    visibility_cache[collection.name] = layer_collection.hide_viewport
                    layer_collection.hide_viewport = True

            props.cached_other_sets_visibility = json.dumps(visibility_cache)
            props.other_sets_hidden = True
            log_message(context, f"Hidden {len(other_render_set_collections)} collection(s) from other render sets")

        tag_redraw_3d_and_outliner(context)
        return {'FINISHED'}


class COMPRS_OT_ToggleConstantCollections(Operator):
    """Toggle viewport visibility of constant render set collections"""
    bl_idname = "comprs.toggle_constant_collections"
    bl_label = "Toggle Constant Render Set Collections"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        props = context.scene.compositor_render_sets
        render_set = get_active_render_set(context)

        if render_set and render_set.override_constant_collections:
            constant_colls = [item.collection for item in render_set.constant_collections
                              if item.collection]
            if not constant_colls:
                self.report({'WARNING'}, "No constant render set collections in this render set override")
                return {'CANCELLED'}
        else:
            constant_colls = [item.collection for item in props.constant_collections
                              if item.collection]
            if not constant_colls:
                self.report({'WARNING'}, "No global constant render set collections defined")
                return {'CANCELLED'}

        layer_map = build_layer_collection_map(context.view_layer)

        if props.constant_collections_visible:
            # Hide constant collections and cache state
            visibility_cache = {}
            for collection in constant_colls:
                layer_collection = layer_map.get(collection)
                if layer_collection:
                    visibility_cache[collection.name] = layer_collection.hide_viewport
                    layer_collection.hide_viewport = True

            props.cached_constant_collections_visibility = json.dumps(visibility_cache)
            props.constant_collections_visible = False
            log_message(context, f"Hidden {len(constant_colls)} constant render set collection(s)")
        else:
            # Restore visibility
            try:
                if props.cached_constant_collections_visibility:
                    cached = json.loads(props.cached_constant_collections_visibility)
                    for coll_name, hide_state in cached.items():
                        collection = bpy.data.collections.get(coll_name)
                        layer_collection = layer_map.get(collection) if collection else None
                        if layer_collection:
                            layer_collection.hide_viewport = hide_state
                    log_message(context, f"Restored visibility for {len(cached)} constant render set collection(s)")
            except (json.JSONDecodeError, TypeError) as e:
                print(f"[COMPRS ERROR] Restoring constant collections visibility: {e}")
                # Fallback: just show them
                for collection in constant_colls:
                    layer_collection = layer_map.get(collection)
                    if layer_collection:
                        layer_collection.hide_viewport = False
            props.constant_collections_visible = True
            props.cached_constant_collections_visibility = ""

        tag_redraw_3d_and_outliner(context)
        return {'FINISHED'}


# ============================================================================
# Operators - Rendering
# ============================================================================

class COMPRS_OT_RenderSet(Operator):
    """Render one or more render sets through the compositor"""
    bl_idname = "comprs.render_set"
    bl_label = "Render Set"
    bl_options = {'REGISTER'}

    mode: EnumProperty(
        name="Mode",
        description="Which sets to render",
        items=[
            ('current', "Current Set", "Render only the active render set"),
            ('all', "Batch", "Render all sets enabled for batch render"),
        ],
        default='current'
    )

    def render_single_set(self, context, render_set, set_index, total_sets):
        """Render a single set synchronously."""
        props = context.scene.compositor_render_sets

        print(f"\n{'=' * 60}")
        print(f"RENDERING SET {set_index + 1}/{total_sets}: {render_set.name}")
        print(f"{'=' * 60}")
        log_message(context, f"Starting render for set: {render_set.name}")

        # Determine which File Output node and original state to use
        if render_set.override_output_settings:
            output_node, error = find_file_output_node(context, render_set)
            if not output_node:
                self.report({'ERROR'}, f"Override node not found for '{render_set.name}': {error}")
                log_message(context, f"ERROR: {error}")
                return
            if output_node.name not in self._override_node_states:
                self._override_node_states[output_node.name] = cache_node_state(output_node)
            original_state = self._override_node_states[output_node.name]
        else:
            output_node = self._output_node
            original_state = self._original_node_state

        # Reset to original, then configure for this set
        restore_node_state(output_node, original_state)
        output_names = configure_node_for_set(output_node, render_set, context)

        node_tree = get_compositor_node_tree(context.scene)
        if node_tree:
            node_tree.update_tag()
        context.view_layer.update()

        if props.settings.mute_unused_output_nodes:
            mute_unused_output_nodes(context, output_node.name)

        # Save original viewport visibility ONLY on first render
        if set_index == 0:
            self._original_viewport_visibility = save_viewport_visibility(context)

        # Get constant collections (if enabled)
        constant_collections = []
        if props.settings.render_constant_collections:
            if render_set.override_constant_collections:
                constant_collections = [item.collection for item in render_set.constant_collections
                                        if item.collection]
            else:
                constant_collections = [item.collection for item in props.constant_collections
                                        if item.collection]

        layer_map = build_layer_collection_map(context.view_layer)

        # Hide collections based on the hide_undefined_collections setting
        if props.settings.hide_undefined_collections:
            # Only hide collections that are defined in any render set
            all_defined_collections = set()
            for rs in props.render_sets:
                all_defined_collections.update(get_collections_from_set(rs))
                if props.settings.render_constant_collections and rs.override_constant_collections:
                    all_defined_collections.update(
                        item.collection for item in rs.constant_collections if item.collection)
            if props.settings.render_constant_collections:
                all_defined_collections.update(
                    item.collection for item in props.constant_collections if item.collection)

            for coll in all_defined_collections:
                layer_coll = layer_map.get(coll)
                if layer_coll:
                    layer_coll.hide_viewport = True
        else:
            hide_all_collections(context)

        # Show this set's collections, then constant collections
        apply_collection_visibility(render_set, context, layer_map)

        if constant_collections:
            dbg(f"[CONSTANT COLLECTIONS] Showing {len(constant_collections)} constant collection(s)")
            for coll in constant_collections:
                layer_coll = layer_map.get(coll)
                if layer_coll:
                    layer_coll.hide_viewport = False
                    coll.hide_render = False

        # Sync render visibility; keep only the FIRST snapshot as the original
        if set_index == 0:
            self._original_render_visibility = sync_visibility_to_render(context)
        else:
            sync_visibility_to_render(context)

        apply_render_visibility_overrides(render_set)

        # Sync modifiers and objects ONLY on first render
        if set_index == 0:
            all_collections_to_sync = set()
            for rs in self._render_queue:
                all_collections_to_sync.update(get_collections_from_set(rs))

            self._original_modifier_settings = sync_modifiers_to_viewport(
                context, list(all_collections_to_sync))
            self._original_object_settings = sync_objects_to_viewport(
                context, list(all_collections_to_sync))

        tag_redraw_3d_and_outliner(context)
        context.evaluated_depsgraph_get().update()

        output_path = bpy.path.abspath(render_set.output_path)
        outputs_str = ", ".join(output_names) if output_names else "No matching outputs"
        log_message(context, f"Rendering '{render_set.name}' to '{output_path}'. Outputs: {outputs_str}")

        # Synchronous render (blocks until complete)
        bpy.ops.render.render('EXEC_DEFAULT', write_still=True)
        print(f"[RENDER] Render complete for '{render_set.name}'")

        # Restore node to original state immediately after render
        restore_node_state(output_node, original_state)

    def cleanup(self, context):
        """Restore all cached state after renders complete (or fail)."""
        print(f"\n{'=' * 60}")
        print(f"RENDER BATCH DONE ({len(self._render_queue)} SET(S)) - CLEANING UP")
        print(f"{'=' * 60}")

        if self._original_viewport_visibility:
            restore_viewport_visibility(context, self._original_viewport_visibility)

        if self._original_render_visibility:
            restore_render_visibility(self._original_render_visibility)

        if self._original_modifier_settings:
            restore_modifier_settings(self._original_modifier_settings)

        if self._original_object_settings:
            restore_object_settings(self._original_object_settings)

        if self._output_node and self._original_node_state:
            restore_node_state(self._output_node, self._original_node_state)
            log_message(context, "Global File Output node restored to original state")

        # Restore all override nodes to their original states
        node_tree = get_compositor_node_tree(context.scene)
        if node_tree:
            for node_name, node_state in self._override_node_states.items():
                node = node_tree.nodes.get(node_name)
                if node and node.type == 'OUTPUT_FILE':
                    restore_node_state(node, node_state)
                    log_message(context, f"Override File Output node '{node_name}' restored to original state")

        if self._original_output_nodes_mute_states:
            restore_output_nodes_mute_state(context, self._original_output_nodes_mute_states)
            log_message(context, "File Output nodes mute states restored")

        props = context.scene.compositor_render_sets
        props.is_rendering = False
        props.cached_node_state = ""

        self.report({'INFO'}, f"Rendered {len(self._render_queue)} set(s)")
        log_message(context, f"Completed rendering {len(self._render_queue)} set(s)")

    def execute(self, context):
        props = context.scene.compositor_render_sets

        # Fresh per-run state (never class-level: operator instances persist)
        self._render_queue = []
        self._output_node = None
        self._original_node_state = None
        self._override_node_states = {}
        self._original_render_visibility = None
        self._original_viewport_visibility = None
        self._original_modifier_settings = None
        self._original_object_settings = None
        self._original_output_nodes_mute_states = None

        # Determine which sets to render
        if self.mode == 'current':
            render_set = get_active_render_set(context)
            if not render_set:
                self.report({'ERROR'}, "No active render set")
                return {'CANCELLED'}
            sets_to_render = [render_set]
        else:  # 'all'
            sets_to_render = [rs for rs in props.render_sets if rs.enabled_for_batch_render]
            if not sets_to_render:
                self.report({'WARNING'}, "No render sets enabled for batch rendering")
                return {'CANCELLED'}

        # Find the global File Output node
        node, error = find_file_output_node(context)
        if not node:
            self.report({'ERROR'}, error)
            log_message(context, f"ERROR: {error}")
            return {'CANCELLED'}

        self._original_node_state = cache_node_state(node)
        self._output_node = node
        self._render_queue = sets_to_render

        # Pre-cache all override nodes' states BEFORE any rendering starts,
        # so we capture their original, unmodified state.
        for render_set in sets_to_render:
            if render_set.override_output_settings:
                override_node, error = find_file_output_node(context, render_set)
                if override_node:
                    if override_node.name not in self._override_node_states:
                        self._override_node_states[override_node.name] = cache_node_state(override_node)
                else:
                    print(f"[COMPRS WARNING] Could not find override node for set "
                          f"'{render_set.name}': {error}")

        # Snapshot mute states before render_single_set mutes per set
        if props.settings.mute_unused_output_nodes:
            self._original_output_nodes_mute_states = snapshot_output_nodes_mute(context)

        # Store state in scene properties for recovery functionality
        props.is_rendering = True
        props.cached_node_state = json.dumps(self._original_node_state)

        print(f"\n{'=' * 60}")
        print(f"STARTING RENDER - {len(sets_to_render)} SET(S)")
        print(f"{'=' * 60}")

        # Cleanup MUST run even if a render throws, or the node stays
        # reconfigured and scene visibility stays mangled.
        try:
            for i, render_set in enumerate(sets_to_render):
                self.render_single_set(context, render_set, i, len(sets_to_render))
        finally:
            self.cleanup(context)

        return {'FINISHED'}

    def cancel(self, context):
        print("[COMPRS] Render operator cancelled")
        self.cleanup(context)


class COMPRS_OT_AbortRender(Operator):
    """Recover from an interrupted render: restore the File Output node and clear stuck state flags"""
    bl_idname = "comprs.abort_render"
    bl_label = "Abort Render"
    bl_options = {'REGISTER'}

    @classmethod
    def poll(cls, context):
        props = context.scene.compositor_render_sets
        return props.is_rendering

    def execute(self, context):
        props = context.scene.compositor_render_sets

        print("\n" + "=" * 60)
        print("ABORTING / RECOVERING RENDER STATE")
        print("=" * 60)

        # Restore the File Output node from cached state
        node, error = find_file_output_node(context)
        if node and props.cached_node_state:
            try:
                cached_state = json.loads(props.cached_node_state)
                restore_node_state(node, cached_state)
                log_message(context, "File Output node restored to original state")
            except (json.JSONDecodeError, TypeError, KeyError) as e:
                log_message(context, f"Error restoring File Output node: {e}")
                self.report({'ERROR'}, f"Failed to restore File Output node: {e}")
        elif not node:
            log_message(context, f"Render aborted - Warning: {error}")
            self.report({'WARNING'}, f"Could not find File Output node: {error}")
        else:
            log_message(context, "Render aborted - No cached node state available")
            self.report({'WARNING'}, "No cached node state - manual verification recommended")

        # Clear stuck state flags
        props.is_rendering = False
        props.cached_node_state = ""
        props.solo_active = False
        props.other_sets_hidden = False

        log_message(context, "Render operation aborted")
        self.report({'INFO'}, "Render state reset and File Output node restored")
        return {'FINISHED'}


# ============================================================================
# Operators - UI helpers
# ============================================================================

class COMPRS_OT_SelectSet(Operator):
    """Select a render set tab"""
    bl_idname = "comprs.select_set"
    bl_label = "Select Set"

    index: IntProperty()

    def execute(self, context):
        props = context.scene.compositor_render_sets
        old_index = props.active_set_index
        props.active_set_index = self.index

        # When switching tabs, refresh the visibility button state from the
        # actual viewport state of the newly active set's collections.
        if old_index != self.index:
            render_set = get_active_render_set(context)
            if render_set:
                collections_in_set = get_collections_from_set(render_set)
                if collections_in_set:
                    layer_map = build_layer_collection_map(context.view_layer)
                    visible_count = sum(
                        1 for collection in collections_in_set
                        if (lc := layer_map.get(collection)) and not lc.hide_viewport)
                    render_set.is_visible = visible_count > len(collections_in_set) / 2

                tag_redraw_3d_and_outliner(context)

        return {'FINISHED'}


class COMPRS_OT_ToggleBatchRender(Operator):
    """Toggle batch render enabled for a render set"""
    bl_idname = "comprs.toggle_batch_render"
    bl_label = "Toggle Batch Render"
    bl_options = {'REGISTER', 'UNDO'}

    index: IntProperty()

    def execute(self, context):
        props = context.scene.compositor_render_sets
        if 0 <= self.index < len(props.render_sets):
            render_set = props.render_sets[self.index]
            render_set.enabled_for_batch_render = not render_set.enabled_for_batch_render
        return {'FINISHED'}


class COMPRS_OT_ClearLog(Operator):
    """Clear the render log"""
    bl_idname = "comprs.clear_log"
    bl_label = "Clear Log"

    def execute(self, context):
        context.scene.compositor_render_sets.log_text = ""
        return {'FINISHED'}


class COMPRS_OT_CreateNodeSetup(Operator):
    """Create the required File Output node setup based on settings"""
    bl_idname = "comprs.create_node_setup"
    bl_label = "Create Node Setup"
    bl_description = "Create a File Output node with the configured name in the compositor"
    bl_options = {'REGISTER', 'UNDO'}

    use_override: BoolProperty(
        name="Use Override Settings",
        description="Create node using per-set override settings",
        default=False
    )

    def execute(self, context):
        props = context.scene.compositor_render_sets
        scene = context.scene

        # Scene.use_nodes is deprecated and slated for removal in Blender 6.0
        if hasattr(scene, 'use_nodes') and not scene.use_nodes:
            scene.use_nodes = True
            log_message(context, "Enabled compositor 'Use Nodes'")

        node_tree = get_compositor_node_tree(scene)
        if not node_tree and hasattr(scene, 'compositing_node_group'):
            # Blender 5.0: a fresh scene has no compositing node group yet
            node_tree = bpy.data.node_groups.new("Compositing Nodes", 'CompositorNodeTree')
            scene.compositing_node_group = node_tree
            log_message(context, "Created compositing node group")
        if not node_tree:
            self.report({'ERROR'}, "Could not access compositor node tree")
            return {'CANCELLED'}

        if self.use_override:
            render_set = get_active_render_set(context)
            if not render_set or not render_set.override_output_settings:
                self.report({'ERROR'}, "No active render set or override not enabled")
                return {'CANCELLED'}
            node_name = render_set.output_node_name_override
            prefix = render_set.name_prefix_override
        else:
            node_name = props.settings.output_node_name
            prefix = props.settings.name_prefix

        if node_name in node_tree.nodes:
            self.report({'WARNING'}, f"File Output node '{node_name}' already exists")
            return {'CANCELLED'}

        output_node = node_tree.nodes.new('CompositorNodeOutputFile')
        output_node.name = node_name
        output_node.label = node_name
        set_output_node_base_path(output_node, "//")

        # Blender 5.0's 'format' is an enum; set it to individual images.
        # On 4.x 'format' is an ImageFormatSettings pointer - assignment fails.
        if hasattr(output_node, 'format'):
            try:
                output_node.format = 'IMAGE'
            except (AttributeError, TypeError):
                pass

        # Replace default slots with one example slot in prefix convention
        example_slot = prefix + "_ExampleSlot"
        if hasattr(output_node, 'file_slots'):
            # Blender 4.x API - remove() takes the input SOCKET, not the slot
            while len(output_node.inputs) > 0:
                output_node.file_slots.remove(output_node.inputs[0])
            output_node.file_slots.new(example_slot)
        elif hasattr(output_node, 'file_output_items'):
            # Blender 5.0+ API - new() takes socket type and name
            while len(output_node.file_output_items) > 0:
                output_node.file_output_items.remove(output_node.file_output_items[0])
            output_node.file_output_items.new('RGBA', example_slot)
        else:
            self.report({'ERROR'}, "Could not find file slots API")
            return {'CANCELLED'}

        output_node.location = (400, 0)

        self.report({'INFO'}, f"Created File Output node '{node_name}' with example slot '{example_slot}'")
        log_message(context, f"Created File Output node '{node_name}' with example slot '{example_slot}'")
        return {'FINISHED'}


class COMPRS_OT_TestNodeSetup(Operator):
    """Test if the File Output node can be found and configured"""
    bl_idname = "comprs.test_node_setup"
    bl_label = "Test Node Setup"
    bl_description = "Verify that the File Output node is correctly configured"

    use_override: BoolProperty(
        name="Use Override Settings",
        description="Test using per-set override settings",
        default=False
    )

    def execute(self, context):
        props = context.scene.compositor_render_sets

        print("\n" + "=" * 60)
        print("TESTING FILE OUTPUT NODE SETUP")
        print("=" * 60)

        if self.use_override:
            render_set = get_active_render_set(context)
            if not render_set or not render_set.override_output_settings:
                self.report({'ERROR'}, "No active render set or override not enabled")
                return {'CANCELLED'}
            node_name = render_set.output_node_name_override
            prefix = render_set.name_prefix_override
            print(f"Testing with override settings from '{render_set.name}'")
        else:
            node_name = props.settings.output_node_name
            prefix = props.settings.name_prefix
            print("Testing with global settings")

        # Test 1: Find the node
        node, error = find_file_output_node(context, render_set if self.use_override else None)
        if not node:
            self.report({'ERROR'}, error)
            log_message(context, f"TEST FAILED: {error}")
            return {'CANCELLED'}

        self.report({'INFO'}, f"✓ Found node: {node.name}")
        log_message(context, f"✓ Node found: {node.name}")

        # Test 2: Check file slots
        file_slots = get_output_node_file_slots(node)
        slot_paths = [get_slot_path(slot) for slot in file_slots]
        matching_slots = [path for path in slot_paths if path.startswith(prefix)]

        if not matching_slots:
            msg = f"No file slots with prefix '{prefix}' found. Available slots: {slot_paths}"
            self.report({'WARNING'}, msg)
            log_message(context, f"WARNING: {msg}")
        else:
            self.report({'INFO'}, f"✓ Found {len(matching_slots)} matching slots: {matching_slots}")
            log_message(context, f"✓ Matching slots ({len(matching_slots)}): {', '.join(matching_slots)}")

        # Test 3: Check current render set + simulate configuration
        render_set = get_active_render_set(context)
        if not render_set:
            msg = "No active render set"
            self.report({'WARNING'}, msg)
            log_message(context, f"WARNING: {msg}")
        else:
            self.report({'INFO'}, f"✓ Active set: {render_set.name}")
            log_message(context, f"✓ Active render set: {render_set.name}")

            print("\nSimulating configuration:")
            for path in matching_slots:
                print(f"  {path} → {render_set.name + path[len(prefix):]}")

        print("=" * 60)
        print("TEST COMPLETE")
        print("=" * 60 + "\n")

        self.report({'INFO'}, "Node setup test complete - check console for details")
        return {'FINISHED'}


classes = (
    COMPRS_OT_AddRenderSet,
    COMPRS_OT_RemoveRenderSet,
    COMPRS_OT_AddCollection,
    COMPRS_OT_RemoveCollection,
    COMPRS_OT_AddVisibleCollections,
    COMPRS_OT_ClearAllCollections,
    COMPRS_OT_AddConstantCollection,
    COMPRS_OT_RemoveConstantCollection,
    COMPRS_OT_ToggleSetVisibility,
    COMPRS_OT_SoloSet,
    COMPRS_OT_HideOtherSets,
    COMPRS_OT_ToggleConstantCollections,
    COMPRS_OT_RenderSet,
    COMPRS_OT_AbortRender,
    COMPRS_OT_SelectSet,
    COMPRS_OT_ToggleBatchRender,
    COMPRS_OT_ClearLog,
    COMPRS_OT_CreateNodeSetup,
    COMPRS_OT_TestNodeSetup,
)
