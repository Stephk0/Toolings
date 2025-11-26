bl_info = {
    "name": "Compositor Render Sets",
    "author": "Claude AI + Stephan Viranyi",
    "version": (1, 6, 0),
    "blender": (4, 0, 0),
    "location": "3D View > Sidebar > Compositor Render Sets",
    "description": "Render distinct collections through compositor with automatic File Output node management. Compatible with Blender 4.x and 5.0+",
    "category": "Render",
}

import bpy
from bpy.props import (
    StringProperty,
    BoolProperty,
    CollectionProperty,
    PointerProperty,
    IntProperty,
)
from bpy.types import (
    Panel,
    Operator,
    PropertyGroup,
    UIList,
)
import os
from datetime import datetime


# ============================================================================
# Property Groups
# ============================================================================

class COMPRS_CollectionItem(PropertyGroup):
    """Represents a single collection in a Render Set"""
    collection: PointerProperty(
        name="Collection",
        type=bpy.types.Collection,
        description="Collection to include in this render set"
    )

    render_visibility: BoolProperty(
        name="Render Visibility",
        description="Enable render visibility for this collection in this set",
        default=True
    )


class COMPRS_RenderSet(PropertyGroup):
    """Represents a Render Set with name, output path, and collections"""
    name: StringProperty(
        name="Render Set Name",
        description="Name of this render set (used in file naming)",
        default="RenderSet"
    )

    output_path: StringProperty(
        name="Output Path",
        description="Directory path where renders will be saved",
        default="//",
        subtype='DIR_PATH'
    )

    enabled_for_render: BoolProperty(
        name="Enabled",
        description="Include this set when rendering selected sets",
        default=True
    )

    collections: CollectionProperty(
        type=COMPRS_CollectionItem,
        name="Collections"
    )

    active_collection_index: IntProperty(
        name="Active Collection Index",
        description="Index of the active collection in the list",
        default=0
    )

    # Internal state for visibility management
    is_visible: BoolProperty(
        name="Is Visible",
        description="Current viewport visibility state of this set",
        default=True
    )


class COMPRS_Settings(PropertyGroup):
    """Settings for the addon"""
    output_node_name: StringProperty(
        name="Output Node Name",
        description="Name of the File Output node in compositor to manipulate",
        default="RenderSetOutput"
    )

    name_prefix: StringProperty(
        name="Name Prefix",
        description="Prefix to replace in File Output node input names (e.g., 'XXX' in 'XXX_Beauty')",
        default="XXX"
    )

    sync_visibility: BoolProperty(
        name="Sync Collection Viewport Visibility to Render",
        description="Sync collection render visibility to match viewport visibility (eye icon) for each render",
        default=True
    )

    sync_modifiers: BoolProperty(
        name="Sync Modifier Viewport Visibility to Render",
        description="Sync modifier render settings to match viewport display (what you see is what you get)",
        default=True
    )

    sync_objects: BoolProperty(
        name="Sync Objects in Collection Viewport Visibility to Render",
        description="Sync object render visibility to match viewport visibility for objects in render set collections only",
        default=False
    )

    hide_undefined_collections: BoolProperty(
        name="Only Hide Defined Collections for Render",
        description="Only hide/show collections defined in render sets during render, leaving other collections untouched",
        default=False
    )

    only_show_renderable: BoolProperty(
        name="Hide/Show Set Only Renderable",
        description="Limit hide/show set visibility toggle to only affect collections enabled for render (camera icon on)",
        default=False
    )

    max_tabs_per_row: IntProperty(
        name="Max Tabs Per Row",
        description="Maximum number of render set tabs to display per row before wrapping to a new row",
        default=8,
        min=1,
        max=20
    )

    enable_log: BoolProperty(
        name="Enable Log",
        description="Log render operations to the log panel",
        default=True
    )


class COMPRS_Properties(PropertyGroup):
    """Main property group storing all addon data"""
    render_sets: CollectionProperty(
        type=COMPRS_RenderSet,
        name="Render Sets"
    )

    active_set_index: IntProperty(
        name="Active Set",
        description="Currently active render set",
        default=0
    )

    settings: PointerProperty(
        type=COMPRS_Settings
    )

    log_text: StringProperty(
        name="Log",
        description="Render log messages",
        default=""
    )

    # Cache for solo mode
    solo_active: BoolProperty(
        name="Solo Active",
        description="Whether solo mode is currently active",
        default=False
    )

    # Cache for original visibility states (for solo undo)
    cached_visibility: StringProperty(
        name="Cached Visibility",
        description="JSON string of cached collection visibility states",
        default=""
    )

    # Cache for hide other sets toggle
    other_sets_hidden: BoolProperty(
        name="Other Sets Hidden",
        description="Whether other render sets are currently hidden",
        default=False
    )

    cached_other_sets_visibility: StringProperty(
        name="Cached Other Sets Visibility",
        description="JSON string of cached visibility states for hide other sets feature",
        default=""
    )

    # Cache for render operations (for abort functionality)
    is_rendering: BoolProperty(
        name="Is Rendering",
        description="Whether a render set operation is currently in progress",
        default=False
    )

    cached_node_state: StringProperty(
        name="Cached Node State",
        description="JSON string of cached File Output node state for abort functionality",
        default=""
    )


# ============================================================================
# Helper Functions
# ============================================================================

def get_output_node_base_path(node):
    """Get base path from File Output node (Blender version compatible)"""
    # Blender 5.0+ uses 'directory' instead of 'base_path'
    if hasattr(node, 'directory'):
        return node.directory
    elif hasattr(node, 'base_path'):
        return node.base_path
    else:
        # Fallback - check all attributes
        for attr in ['filepath', 'path', 'output_path']:
            if hasattr(node, attr):
                return getattr(node, attr)
        return ""

def set_output_node_base_path(node, path):
    """Set base path on File Output node (Blender version compatible)"""
    # Blender 5.0+ uses 'directory' instead of 'base_path'
    if hasattr(node, 'directory'):
        node.directory = path
    elif hasattr(node, 'base_path'):
        node.base_path = path
    else:
        # Fallback - try common attributes
        for attr in ['filepath', 'path', 'output_path']:
            if hasattr(node, attr):
                setattr(node, attr, path)
                return
        print(f"[WARNING] Could not set base path on node - unknown API")

def get_output_node_file_slots(node):
    """Get file slots from File Output node (Blender version compatible)"""
    # Blender 4.x uses 'file_slots'
    if hasattr(node, 'file_slots') and node.file_slots:
        print(f"[API] Using 'file_slots' (Blender 4.x)")
        return node.file_slots

    # Blender 5.0+ uses 'file_output_items'
    if hasattr(node, 'file_output_items') and node.file_output_items:
        print(f"[API] Using 'file_output_items' (Blender 5.0+)")
        return node.file_output_items

    # Fallback: print debug info
    print(f"[WARNING] Could not find file slots attribute")
    print(f"  Available output-related attributes: {[attr for attr in dir(node) if 'output' in attr.lower() or 'slot' in attr.lower() or 'file' in attr.lower()]}")
    return []

def get_slot_path(slot):
    """Get path from a file slot (Blender version compatible)"""
    # Try common path attributes
    for attr in ['path', 'name', 'file_path', 'filepath']:
        if hasattr(slot, attr):
            return getattr(slot, attr)

    # Debug if not found
    print(f"[WARNING] Could not find path attribute on slot")
    print(f"  Slot type: {type(slot)}")
    print(f"  Available attributes: {[attr for attr in dir(slot) if not attr.startswith('_')]}")
    return ""

def set_slot_path(slot, path):
    """Set path on a file slot (Blender version compatible)"""
    # Try common path attributes
    for attr in ['path', 'name', 'file_path', 'filepath']:
        if hasattr(slot, attr):
            try:
                setattr(slot, attr, path)
                return True
            except:
                continue

    print(f"[WARNING] Could not set path on slot")
    return False

def log_message(context, message):
    """Add a message to the log"""
    props = context.scene.compositor_render_sets
    if props.settings.enable_log:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"[{timestamp}] {message}\n"
        props.log_text += log_entry
        print(log_entry.strip())  # Also print to console


def get_active_render_set(context):
    """Get the currently active render set"""
    props = context.scene.compositor_render_sets
    if 0 <= props.active_set_index < len(props.render_sets):
        return props.render_sets[props.active_set_index]
    return None


def get_collections_from_set(render_set):
    """Get list of actual collection objects from a render set"""
    return [item.collection for item in render_set.collections if item.collection]


def find_layer_collection(layer_collection, collection):
    """Recursively find a LayerCollection for a given Collection"""
    if layer_collection.collection == collection:
        return layer_collection

    for child in layer_collection.children:
        result = find_layer_collection(child, collection)
        if result:
            return result

    return None


def apply_collection_visibility(render_set, context):
    """Apply visibility settings from render set to collections"""
    view_layer = context.view_layer

    for item in render_set.collections:
        if item.collection:
            # Find the layer collection for viewport visibility
            layer_collection = find_layer_collection(view_layer.layer_collection, item.collection)
            if layer_collection:
                # Show in viewport (eye icon in outliner)
                layer_collection.hide_viewport = False

            # Apply render visibility from the toggle
            item.collection.hide_render = not item.render_visibility


def apply_render_visibility_overrides(render_set):
    """Apply render visibility overrides from render set (call AFTER sync)"""
    print("[RENDER VISIBILITY] Applying render visibility overrides from render set:")

    for item in render_set.collections:
        if item.collection:
            # Override with the render_visibility toggle setting
            # This ensures the toggle takes precedence over sync settings
            item.collection.hide_render = not item.render_visibility

            status = "visible" if item.render_visibility else "hidden"
            print(f"  Collection '{item.collection.name}': {status} in render (hide_render = {item.collection.hide_render})")


def find_file_output_node(context):
    """Find the File Output node by name in the compositor"""
    scene = context.scene

    # Ensure compositor is enabled
    if not scene.use_nodes:
        return None, "Compositor 'Use Nodes' is not enabled. Enable it in the Compositor workspace."

    # Try to access compositor node tree - API changed in Blender 5.0
    node_tree = None

    # Method 1: Blender 5.0+ uses compositing_node_group
    if hasattr(scene, 'compositing_node_group') and scene.compositing_node_group:
        node_tree = scene.compositing_node_group
        print(f"[FIND NODE] Using Blender 5.0+ API (compositing_node_group)")
    # Method 2: Blender 4.x and earlier use node_tree
    elif hasattr(scene, 'node_tree') and scene.node_tree:
        node_tree = scene.node_tree
        print(f"[FIND NODE] Using Blender 4.x API (node_tree)")

    if not node_tree:
        # Debug: Print what's available
        print(f"[DEBUG] scene.use_nodes: {scene.use_nodes}")
        print(f"[DEBUG] hasattr(scene, 'node_tree'): {hasattr(scene, 'node_tree')}")
        print(f"[DEBUG] hasattr(scene, 'compositing_node_group'): {hasattr(scene, 'compositing_node_group')}")
        return None, "No compositor node tree found. Ensure 'Use Nodes' is enabled in the Compositor workspace."

    node_name = context.scene.compositor_render_sets.settings.output_node_name

    print(f"[FIND NODE] Looking for File Output node named: '{node_name}'")
    print(f"  Total nodes in compositor: {len(node_tree.nodes)}")

    # Search for the node
    for node in node_tree.nodes:
        if node.type == 'OUTPUT_FILE':
            print(f"    Found File Output node: '{node.name}'")
            if node.name == node_name:
                print(f"    ✓ Match! Using this node.")
                print(f"    Current base_path: {get_output_node_base_path(node)}")
                print(f"    File slots: {[get_slot_path(slot) for slot in get_output_node_file_slots(node)]}")
                return node, None

    # List all File Output nodes if not found
    file_output_nodes = [n.name for n in node_tree.nodes if n.type == 'OUTPUT_FILE']
    if file_output_nodes:
        return None, f"File Output node '{node_name}' not found. Available File Output nodes: {', '.join(file_output_nodes)}"
    else:
        return None, f"No File Output nodes found in compositor. Please add one and name it '{node_name}'"


def cache_node_state(node):
    """Cache the original state of a File Output node"""
    state = {
        'base_path': get_output_node_base_path(node),
        'file_slots': []
    }

    # Cache each file slot's path
    file_slots = get_output_node_file_slots(node)
    for i, slot in enumerate(file_slots):
        state['file_slots'].append({
            'path': get_slot_path(slot),
            'index': i
        })

    print(f"[CACHE] Cached node state:")
    print(f"  Base path: {state['base_path']}")
    print(f"  File slots: {[s['path'] for s in state['file_slots']]}")

    return state


def restore_node_state(node, state):
    """Restore a File Output node to its cached state"""
    print(f"[RESTORE] Restoring node state:")
    print(f"  Base path: {state['base_path']}")

    set_output_node_base_path(node, state['base_path'])

    # Restore each file slot path
    file_slots = get_output_node_file_slots(node)
    for slot_data in state['file_slots']:
        idx = slot_data['index']
        if idx < len(file_slots):
            set_slot_path(file_slots[idx], slot_data['path'])
            print(f"  Slot {idx}: {slot_data['path']}")

    print(f"[RESTORE] Node state restored")


def configure_node_for_set(node, render_set, prefix):
    """Configure File Output node for a specific render set"""
    print(f"\n[CONFIGURE] Configuring File Output node for set: {render_set.name}")

    # Set base path
    output_path = bpy.path.abspath(render_set.output_path)

    # IMPORTANT: Ensure the path ends with a slash for proper directory handling
    if not output_path.endswith(os.sep) and not output_path.endswith('/'):
        output_path += os.sep

    set_output_node_base_path(node, output_path)
    print(f"  Base path set to: {output_path}")

    # Create directory if it doesn't exist
    try:
        os.makedirs(output_path, exist_ok=True)
        print(f"  Directory created/verified: {output_path}")
    except Exception as e:
        print(f"  Warning: Could not create directory {output_path}: {e}")

    # Process file slots - assumes slots are in their ORIGINAL state (with prefix)
    output_names = []
    file_slots = get_output_node_file_slots(node)
    print(f"  Processing {len(file_slots)} file slots with prefix '{prefix}':")

    for i, slot in enumerate(file_slots):
        current_path = get_slot_path(slot)

        if current_path.startswith(prefix):
            # Remove prefix and replace with render set name
            remainder = current_path[len(prefix):]
            new_name = render_set.name + remainder
            set_slot_path(slot, new_name)
            output_names.append(new_name)
            print(f"    Slot {i}: '{current_path}' -> '{new_name}'")
        else:
            # Slot doesn't match prefix, keep as-is
            print(f"    Slot {i}: '{current_path}' (no prefix match, keeping as-is)")
            output_names.append(current_path)

    print(f"  Total outputs configured: {len(output_names)}")
    print(f"  Final node state:")
    print(f"    base_path: {get_output_node_base_path(node)}")
    for i, slot in enumerate(file_slots):
        print(f"    Slot {i}: {get_slot_path(slot)}")

    return output_names


def sync_visibility_to_render(context):
    """Sync collection render visibility to viewport visibility (eye icon in outliner)"""
    props = context.scene.compositor_render_sets

    if not props.settings.sync_visibility:
        return None

    # Store original render visibility
    original_states = {}
    view_layer = context.view_layer

    # Recursively sync all layer collections
    def sync_recursive(layer_coll):
        collection = layer_coll.collection
        original_states[collection.name] = collection.hide_render

        # Sync render visibility to match viewport visibility (eye icon)
        collection.hide_render = layer_coll.hide_viewport

        print(f"  Sync: '{collection.name}' - hide_render = {collection.hide_render} (from eye icon)")

        for child in layer_coll.children:
            sync_recursive(child)

    print("[SYNC] Syncing render visibility to viewport (eye icon):")
    sync_recursive(view_layer.layer_collection)

    return original_states


def restore_render_visibility(original_states):
    """Restore original render visibility states"""
    if not original_states:
        return

    print("[RESTORE] Restoring original render visibility:")
    for coll_name, hide_state in original_states.items():
        collection = bpy.data.collections.get(coll_name)
        if collection:
            collection.hide_render = hide_state
            print(f"  '{coll_name}' - hide_render = {hide_state}")


def sync_modifiers_to_viewport(context):
    """Sync modifier render settings to viewport display (WYSIWYG for modifiers)"""
    props = context.scene.compositor_render_sets

    if not props.settings.sync_modifiers:
        return None

    print("[SYNC MODIFIERS] Syncing modifier render settings to viewport display:")

    # Store original modifier states
    original_states = {}

    # Iterate through all objects in the scene
    for obj in bpy.data.objects:
        if not hasattr(obj, 'modifiers') or len(obj.modifiers) == 0:
            continue

        obj_modifiers = {}

        for mod in obj.modifiers:
            # Cache original render state
            obj_modifiers[mod.name] = mod.show_render

            # Sync render to viewport
            mod.show_render = mod.show_viewport

            print(f"  Object '{obj.name}' > Modifier '{mod.name}': show_render = {mod.show_render} (from viewport)")

        if obj_modifiers:
            original_states[obj.name] = obj_modifiers

    if original_states:
        print(f"[SYNC MODIFIERS] Synced modifiers on {len(original_states)} object(s)")
    else:
        print(f"[SYNC MODIFIERS] No objects with modifiers found")

    return original_states


def restore_modifier_settings(original_states):
    """Restore original modifier render settings"""
    if not original_states:
        return

    print("[RESTORE MODIFIERS] Restoring original modifier settings:")

    for obj_name, modifiers in original_states.items():
        obj = bpy.data.objects.get(obj_name)
        if not obj:
            continue

        for mod_name, show_render in modifiers.items():
            mod = obj.modifiers.get(mod_name)
            if mod:
                mod.show_render = show_render
                print(f"  Object '{obj_name}' > Modifier '{mod_name}': show_render = {show_render}")


def sync_objects_to_viewport(context, collections_to_sync=None):
    """Sync object render visibility to viewport visibility for objects in specified collections

    Args:
        context: Blender context
        collections_to_sync: List of collections to sync objects from. If None, returns None (feature disabled)
    """
    props = context.scene.compositor_render_sets

    if not props.settings.sync_objects:
        return None

    print("[SYNC OBJECTS] Syncing object render visibility to viewport visibility:")

    # Store original object states
    original_states = {}

    # Determine which objects to sync
    if collections_to_sync:
        # Only sync objects in the specified collections
        objects_to_sync = set()
        for collection in collections_to_sync:
            if collection:
                objects_to_sync.update(collection.objects)

        print(f"  Syncing objects from {len(collections_to_sync)} collection(s):")
        for collection in collections_to_sync:
            if collection:
                print(f"    - {collection.name} ({len(collection.objects)} objects)")
    else:
        print(f"  No collections specified - skipping object sync")
        return None

    # Iterate through objects to sync
    for obj in objects_to_sync:
        # Cache original render state
        original_states[obj.name] = obj.hide_render

        # Sync render to viewport (only sync viewport visibility to render)
        obj.hide_render = obj.hide_viewport

        print(f"  Object '{obj.name}': hide_render = {obj.hide_render} (synced from hide_viewport = {obj.hide_viewport})")

    if original_states:
        print(f"[SYNC OBJECTS] Synced {len(original_states)} object(s) from {len(collections_to_sync)} collection(s)")
    else:
        print(f"[SYNC OBJECTS] No objects found in specified collections")

    return original_states


def restore_object_settings(original_states):
    """Restore original object render visibility settings"""
    if not original_states:
        return

    print("[RESTORE OBJECTS] Restoring original object render visibility:")

    for obj_name, hide_render in original_states.items():
        obj = bpy.data.objects.get(obj_name)
        if obj:
            obj.hide_render = hide_render
            print(f"  Object '{obj_name}': hide_render = {hide_render}")


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

        # Adjust active index
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

        # Get the collection by name
        collection = bpy.data.collections.get(self.collection_name)
        if not collection:
            self.report({'WARNING'}, f"Collection '{self.collection_name}' not found")
            return {'CANCELLED'}

        # Check if already added
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
            coll_name = render_set.collections[self.index].collection.name if render_set.collections[self.index].collection else "Unknown"
            render_set.collections.remove(self.index)
            log_message(context, f"Removed collection '{coll_name}' from '{render_set.name}'")

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

        # Toggle based on current state
        new_state = not render_set.is_visible

        # Toggle visibility in view layer (this controls the eye icon in outliner)
        view_layer = context.view_layer

        # Determine which collections to toggle based on only_show_renderable setting
        collections_to_toggle = []
        if props.settings.only_show_renderable:
            # Only toggle collections with render_visibility enabled
            for item in render_set.collections:
                if item.collection and item.render_visibility:
                    collections_to_toggle.append(item.collection)
        else:
            # Toggle all collections in the set
            collections_to_toggle = get_collections_from_set(render_set)

        if not collections_to_toggle:
            if props.settings.only_show_renderable:
                self.report({'WARNING'}, "No renderable collections in this set (all have camera icon off)")
            else:
                self.report({'WARNING'}, "No collections in this render set")
            return {'CANCELLED'}

        for collection in collections_to_toggle:
            # Find the layer collection for this collection
            layer_collection = find_layer_collection(view_layer.layer_collection, collection)
            if layer_collection:
                layer_collection.hide_viewport = not new_state
                print(f"  Collection '{collection.name}': hide_viewport = {not new_state}")

        render_set.is_visible = new_state

        state_str = "shown" if new_state else "hidden"
        log_message(context, f"Render set '{render_set.name}' {state_str} in viewport")

        if props.settings.only_show_renderable:
            log_message(context, f"  (Only renderable collections affected)")


        # Force viewport and outliner update
        for area in context.screen.areas:
            if area.type in {'VIEW_3D', 'OUTLINER'}:
                area.tag_redraw()

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

        view_layer = context.view_layer

        # If solo is already active, restore previous state
        if props.solo_active:
            # Restore cached visibility
            import json
            try:
                if props.cached_visibility:
                    cached = json.loads(props.cached_visibility)
                    for coll_name, hide_state in cached.items():
                        collection = bpy.data.collections.get(coll_name)
                        if collection:
                            layer_collection = find_layer_collection(view_layer.layer_collection, collection)
                            if layer_collection:
                                layer_collection.hide_viewport = hide_state
                    props.solo_active = False
                    props.cached_visibility = ""
                    log_message(context, "Solo mode deactivated")
            except Exception as e:
                print(f"Error restoring solo state: {e}")
                pass
        else:
            # Cache current visibility and activate solo
            import json
            visibility_cache = {}

            # Cache and hide all collections
            def cache_and_hide_recursive(layer_coll):
                visibility_cache[layer_coll.collection.name] = layer_coll.hide_viewport
                layer_coll.hide_viewport = True
                for child in layer_coll.children:
                    cache_and_hide_recursive(child)

            cache_and_hide_recursive(view_layer.layer_collection)

            # Show only collections in this set
            for collection in collections_in_set:
                layer_collection = find_layer_collection(view_layer.layer_collection, collection)
                if layer_collection:
                    layer_collection.hide_viewport = False

            # Cache the state
            props.cached_visibility = json.dumps(visibility_cache)
            props.solo_active = True

            log_message(context, f"Solo mode activated for '{render_set.name}'")

        # Force viewport and outliner update
        for area in context.screen.areas:
            if area.type in {'VIEW_3D', 'OUTLINER'}:
                area.tag_redraw()

        return {'FINISHED'}


class COMPRS_OT_HideOtherSets(Operator):
    """Toggle visibility of all collections defined in render sets"""
    bl_idname = "comprs.hide_other_sets"
    bl_label = "Toggle other Sets"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        props = context.scene.compositor_render_sets
        view_layer = context.view_layer

        # Collect all collections from all render sets
        all_render_set_collections = set()
        for render_set in props.render_sets:
            collections = get_collections_from_set(render_set)
            all_render_set_collections.update(collections)

        if not all_render_set_collections:
            self.report({'WARNING'}, "No collections defined in any render sets")
            return {'CANCELLED'}

        # Toggle based on current state
        if props.other_sets_hidden:
            # Restore visibility
            import json
            try:
                if props.cached_other_sets_visibility:
                    cached = json.loads(props.cached_other_sets_visibility)
                    for coll_name, hide_state in cached.items():
                        collection = bpy.data.collections.get(coll_name)
                        if collection:
                            layer_collection = find_layer_collection(view_layer.layer_collection, collection)
                            if layer_collection:
                                layer_collection.hide_viewport = hide_state
                                print(f"  Restored collection '{collection.name}': hide_viewport = {hide_state}")
                    props.other_sets_hidden = False
                    props.cached_other_sets_visibility = ""
                    log_message(context, f"Restored visibility for {len(cached)} collection(s) from render sets")
            except Exception as e:
                print(f"Error restoring visibility: {e}")
                props.other_sets_hidden = False
                props.cached_other_sets_visibility = ""
        else:
            # Cache current visibility and hide
            import json
            visibility_cache = {}

            for collection in all_render_set_collections:
                layer_collection = find_layer_collection(view_layer.layer_collection, collection)
                if layer_collection:
                    visibility_cache[collection.name] = layer_collection.hide_viewport
                    layer_collection.hide_viewport = True
                    print(f"  Hidden collection '{collection.name}'")

            props.cached_other_sets_visibility = json.dumps(visibility_cache)
            props.other_sets_hidden = True
            log_message(context, f"Hidden {len(all_render_set_collections)} collection(s) from render sets")

        # Force viewport and outliner update
        for area in context.screen.areas:
            if area.type in {'VIEW_3D', 'OUTLINER'}:
                area.tag_redraw()

        return {'FINISHED'}


# ============================================================================
# Operators - Rendering
# ============================================================================

class COMPRS_OT_RenderSet(Operator):
    """Render one or more render sets through the compositor"""
    bl_idname = "comprs.render_set"
    bl_label = "Render Set"
    bl_options = {'REGISTER'}

    mode: StringProperty(
        name="Mode",
        description="Which sets to render: 'current', 'selected', or 'all'",
        default='current'
    )

    _timer = None
    _render_queue = []
    _current_set_index = 0
    _original_node_state = None
    _output_node = None
    _original_render_visibility = None
    _original_modifier_settings = None
    _original_object_settings = None
    _render_complete = False
    _render_handlers_installed = False

    def render_complete_handler(self, scene, depsgraph=None):
        """Called when render completes successfully"""
        print("[RENDER] Render complete handler called")
        self._render_complete = True

    def render_cancel_handler(self, scene, depsgraph=None):
        """Called when render is cancelled"""
        print("[RENDER] Render cancelled handler called")
        self._render_complete = True

    def install_render_handlers(self):
        """Install render completion handlers"""
        if not self._render_handlers_installed:
            bpy.app.handlers.render_complete.append(self.render_complete_handler)
            bpy.app.handlers.render_cancel.append(self.render_cancel_handler)
            self._render_handlers_installed = True
            print("[RENDER] Handlers installed")

    def remove_render_handlers(self):
        """Remove render completion handlers"""
        if self._render_handlers_installed:
            try:
                bpy.app.handlers.render_complete.remove(self.render_complete_handler)
                bpy.app.handlers.render_cancel.remove(self.render_cancel_handler)
            except:
                pass  # Handlers may have already been removed
            self._render_handlers_installed = False
            print("[RENDER] Handlers removed")

    def modal(self, context, event):
        if event.type == 'TIMER':
            # Check if render is complete
            if self._render_complete:
                print(f"[MODAL] Render completed for set {self._current_set_index + 1}")
                self._render_complete = False

                # Wait a moment to ensure file is fully written
                import time
                time.sleep(0.1)

                # Render completed, move to next set
                self._current_set_index += 1

                if self._current_set_index < len(self._render_queue):
                    # Render next set - reconfigure the node for this set
                    print(f"[MODAL] Moving to next set ({self._current_set_index + 1}/{len(self._render_queue)})")
                    self.render_next_set(context)
                    return {'RUNNING_MODAL'}
                else:
                    # All sets rendered, cleanup
                    print(f"[MODAL] All renders complete, cleaning up")
                    self.cleanup(context)
                    return {'FINISHED'}

        return {'PASS_THROUGH'}

    def render_next_set(self, context):
        """Render the next set in the queue"""
        props = context.scene.compositor_render_sets
        render_set = self._render_queue[self._current_set_index]

        print(f"\n{'='*60}")
        print(f"RENDERING SET {self._current_set_index + 1}/{len(self._render_queue)}: {render_set.name}")
        print(f"{'='*60}")

        log_message(context, f"Starting render for set: {render_set.name}")

        # CRITICAL: First restore node to original state before configuring
        # This ensures we always start from the clean original prefix (e.g., XXX_Beauty)
        # not from the previously modified state (e.g., CharacterA_Beauty)
        print(f"[RESTORE] Restoring node to original state before configuring...")
        restore_node_state(self._output_node, self._original_node_state)

        # Now configure the File Output node for this render set
        # Starting from the original state ensures clean prefix replacement
        prefix = props.settings.name_prefix
        output_names = configure_node_for_set(self._output_node, render_set, prefix)

        # Force compositor to update with new node settings
        # Support both Blender 4.x (node_tree) and 5.0+ (compositing_node_group) APIs
        if hasattr(context.scene, 'compositing_node_group') and context.scene.compositing_node_group:
            context.scene.compositing_node_group.update_tag()
        elif hasattr(context.scene, 'node_tree') and context.scene.node_tree:
            context.scene.node_tree.update_tag()

        # Also update the view layer to ensure changes propagate
        context.view_layer.update()

        print(f"[NODE] File Output configured for '{render_set.name}'")
        print(f"  Base path: {get_output_node_base_path(self._output_node)}")
        print(f"  Output slots: {[get_slot_path(slot) for slot in get_output_node_file_slots(self._output_node)]}")

        # Get collections in this set
        collections = get_collections_from_set(render_set)

        # Set visibility for this render set
        view_layer = context.view_layer

        # Hide collections based on the hide_undefined_collections setting
        if props.settings.hide_undefined_collections:
            # Only hide collections that are defined in any render set
            all_render_set_collections = set()
            for rs in props.render_sets:
                all_render_set_collections.update(get_collections_from_set(rs))

            # Hide only collections from render sets
            for coll in all_render_set_collections:
                layer_coll = find_layer_collection(view_layer.layer_collection, coll)
                if layer_coll:
                    layer_coll.hide_viewport = True
        else:
            # Hide all collections (original behavior)
            def hide_all_recursive(layer_coll):
                layer_coll.hide_viewport = True
                for child in layer_coll.children:
                    hide_all_recursive(child)

            hide_all_recursive(view_layer.layer_collection)

        # Apply collection visibility from the render set
        apply_collection_visibility(render_set, context)

        # Sync render visibility if enabled
        self._original_render_visibility = sync_visibility_to_render(context)

        # Apply render visibility overrides AFTER sync to ensure toggles take precedence
        # This ensures collections with render_visibility=False are excluded from render
        apply_render_visibility_overrides(render_set)

        # Sync modifier and object settings if enabled (only once, not per render set)
        if self._current_set_index == 0:  # Only on first render
            self._original_modifier_settings = sync_modifiers_to_viewport(context)

            # Gather all collections from all render sets in the queue
            all_collections_to_sync = set()
            for rs in self._render_queue:
                all_collections_to_sync.update(get_collections_from_set(rs))

            # Sync objects only from collections in the render queue
            self._original_object_settings = sync_objects_to_viewport(context, list(all_collections_to_sync))

        # Force viewport and outliner update
        for area in context.screen.areas:
            if area.type in {'VIEW_3D', 'OUTLINER'}:
                area.tag_redraw()

        # Force depsgraph update to ensure all changes are applied
        context.evaluated_depsgraph_get().update()

        # Log what will be rendered
        output_path = bpy.path.abspath(render_set.output_path)
        outputs_str = ", ".join(output_names) if output_names else "No matching outputs"
        log_message(context, f"Rendering '{render_set.name}' to '{output_path}'. Outputs: {outputs_str}")

        # Trigger render - using INVOKE_DEFAULT to allow modal to continue
        print(f"[RENDER] Triggering render operation...")
        bpy.ops.render.render('INVOKE_DEFAULT', write_still=True)

    def cleanup(self, context):
        """Cleanup after all renders complete"""
        print(f"\n{'='*60}")
        print(f"ALL RENDERS COMPLETE - CLEANING UP")
        print(f"{'='*60}")

        # Remove render handlers
        self.remove_render_handlers()

        # Remove timer
        if self._timer:
            context.window_manager.event_timer_remove(self._timer)

        # Restore render visibility
        if self._original_render_visibility:
            restore_render_visibility(self._original_render_visibility)

        # Restore modifier settings
        if self._original_modifier_settings:
            restore_modifier_settings(self._original_modifier_settings)

        # Restore object settings
        if self._original_object_settings:
            restore_object_settings(self._original_object_settings)

        # Restore the node to original state
        if self._output_node and self._original_node_state:
            restore_node_state(self._output_node, self._original_node_state)
            log_message(context, "File Output node restored to original state")

        # Clear render state flags
        props = context.scene.compositor_render_sets
        props.is_rendering = False
        props.cached_node_state = ""

        self.report({'INFO'}, f"Rendered {len(self._render_queue)} set(s)")
        log_message(context, f"Completed rendering {len(self._render_queue)} set(s)")

    def execute(self, context):
        props = context.scene.compositor_render_sets

        # Determine which sets to render
        sets_to_render = []

        if self.mode == 'current':
            render_set = get_active_render_set(context)
            if render_set:
                sets_to_render = [render_set]
            else:
                self.report({'ERROR'}, "No active render set")
                return {'CANCELLED'}

        elif self.mode == 'selected':
            sets_to_render = [rs for rs in props.render_sets if rs.enabled_for_render]
            if not sets_to_render:
                self.report({'WARNING'}, "No render sets enabled for rendering")
                return {'CANCELLED'}

        elif self.mode == 'all':
            sets_to_render = list(props.render_sets)
            if not sets_to_render:
                self.report({'WARNING'}, "No render sets available")
                return {'CANCELLED'}

        # Find the File Output node
        node, error = find_file_output_node(context)
        if not node:
            self.report({'ERROR'}, error)
            log_message(context, f"ERROR: {error}")
            return {'CANCELLED'}

        # Cache original node state
        self._original_node_state = cache_node_state(node)
        self._output_node = node
        self._render_queue = sets_to_render
        self._current_set_index = 0
        self._render_complete = False

        # Store state in scene properties for abort functionality
        import json
        props.is_rendering = True
        props.cached_node_state = json.dumps(self._original_node_state)

        # Install render handlers to detect completion
        self.install_render_handlers()

        # Start rendering the first set
        self.render_next_set(context)

        # Add timer for modal
        self._timer = context.window_manager.event_timer_add(0.5, window=context.window)
        context.window_manager.modal_handler_add(self)

        return {'RUNNING_MODAL'}

    def cancel(self, context):
        """Called when operator is cancelled"""
        print("[OPERATOR] Cancelled")
        self.cleanup(context)


class COMPRS_OT_AbortRender(Operator):
    """Abort the current render and restore File Output node to original state"""
    bl_idname = "comprs.abort_render"
    bl_label = "Abort Render"
    bl_options = {'REGISTER'}

    @classmethod
    def poll(cls, context):
        # Check if a render set operation is currently in progress
        props = context.scene.compositor_render_sets
        return props.is_rendering

    def execute(self, context):
        props = context.scene.compositor_render_sets

        print("\n" + "="*60)
        print("ABORTING RENDER")
        print("="*60)

        # Stop the render by calling ESC (cancels render)
        try:
            bpy.ops.render.render('INVOKE_DEFAULT', animation=False)
        except:
            pass

        # Restore the File Output node from cached state
        node, error = find_file_output_node(context)
        if node and props.cached_node_state:
            import json
            try:
                cached_state = json.loads(props.cached_node_state)
                restore_node_state(node, cached_state)
                log_message(context, "File Output node restored to original state")
                print("[ABORT] File Output node successfully restored")
            except Exception as e:
                log_message(context, f"Error restoring File Output node: {e}")
                print(f"[ABORT] Error restoring node: {e}")
                self.report({'ERROR'}, f"Failed to restore File Output node: {e}")
        elif not node:
            log_message(context, f"Render aborted - Warning: {error}")
            self.report({'WARNING'}, f"Could not find File Output node: {error}")
        else:
            log_message(context, "Render aborted - No cached node state available")
            self.report({'WARNING'}, "No cached node state - manual verification recommended")

        # Clear render state flags
        props.is_rendering = False
        props.cached_node_state = ""

        # Clear any other running states
        props.solo_active = False
        props.other_sets_hidden = False

        log_message(context, "Render operation aborted")
        self.report({'INFO'}, "Render aborted and File Output node restored")

        return {'FINISHED'}


# ============================================================================
# UI List for Collections
# ============================================================================

class COMPRS_UL_CollectionList(UIList):
    """UIList for displaying collections in a render set"""

    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        if item.collection:
            row = layout.row(align=True)
            row.label(text=item.collection.name, icon='OUTLINER_COLLECTION')

            # Render visibility toggle
            row.prop(item, "render_visibility", text="", icon='RESTRICT_RENDER_OFF' if item.render_visibility else 'RESTRICT_RENDER_ON', emboss=False)

            # Remove button
            op = row.operator("comprs.remove_collection", text="", icon='X', emboss=False)
            op.index = index
        else:
            layout.label(text="<Missing Collection>", icon='ERROR')


# ============================================================================
# Main Panel
# ============================================================================

class COMPRS_PT_MainPanel(Panel):
    """Main panel for Compositor Render Sets"""
    bl_label = "Compositor Render Sets"
    bl_idname = "COMPRS_PT_main_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Render Sets'

    def draw(self, context):
        layout = self.layout
        props = context.scene.compositor_render_sets

        # ====================================================================
        # Render Set Setup Section
        # ====================================================================

        box = layout.box()
        box.label(text="Render Set Setup", icon='RENDERLAYERS')

        # Tabs for render sets with row wrapping
        if len(props.render_sets) > 0:
            max_tabs_per_row = props.settings.max_tabs_per_row

            # Create rows as needed based on max_tabs_per_row
            for row_start in range(0, len(props.render_sets), max_tabs_per_row):
                row = box.row(align=True)
                row_end = min(row_start + max_tabs_per_row, len(props.render_sets))

                for i in range(row_start, row_end):
                    render_set = props.render_sets[i]
                    if i == props.active_set_index:
                        row.operator("comprs.select_set", text=render_set.name, depress=True, emboss=True).index = i
                    else:
                        row.operator("comprs.select_set", text=render_set.name, depress=False).index = i

            # Active render set details
            render_set = props.render_sets[props.active_set_index]

            col = box.column(align=True)
            col.prop(render_set, "name", text="Name")
            col.prop(render_set, "output_path", text="Output")
            col.prop(render_set, "enabled_for_render", text="Enabled for Render")

            box.separator()

            # Collections list
            box.label(text="Collections:", icon='OUTLINER_COLLECTION')

            # Use template_list properly with the active_collection_index
            box.template_list(
                "COMPRS_UL_CollectionList",
                "",
                render_set,
                "collections",
                render_set,
                "active_collection_index",
                rows=4
            )

            col = box.column(align=True)
            col.operator("comprs.add_collection", text="Add Collection", icon='ADD')

            # Show collection count
            if len(render_set.collections) > 0:
                box.label(text=f"{len(render_set.collections)} collection(s) in set", icon='INFO')

            box.separator()

            # Visibility controls
            col = box.column(align=True)
            visibility_text = "Hide Set" if render_set.is_visible else "Show Set"
            col.operator("comprs.toggle_set_visibility", text=visibility_text, icon='HIDE_OFF' if render_set.is_visible else 'HIDE_ON')

            hide_other_text = "Show other Sets" if props.other_sets_hidden else "Hide other Sets"
            hide_other_icon = 'RESTRICT_VIEW_OFF' if props.other_sets_hidden else 'RESTRICT_VIEW_ON'
            col.operator("comprs.hide_other_sets", text=hide_other_text, icon=hide_other_icon)

            solo_text = "Un-Solo Set" if props.solo_active else "Solo Set"
            col.operator("comprs.solo_set", text=solo_text, icon='SOLO_ON' if props.solo_active else 'SOLO_OFF')

        else:
            box.label(text="No render sets. Add one below.", icon='INFO')

        # Add/Remove buttons
        row = box.row(align=True)
        row.operator("comprs.add_render_set", text="Add Set", icon='ADD')
        row.operator("comprs.remove_render_set", text="Remove Set", icon='REMOVE')

        layout.separator()

        # ====================================================================
        # Render Section
        # ====================================================================

        box = layout.box()
        box.label(text="Render", icon='RENDER_STILL')

        col = box.column(align=True)
        col.scale_y = 1.3

        op = col.operator("comprs.render_set", text="Render Current Set", icon='RENDER_STILL')
        op.mode = 'current'

        op = col.operator("comprs.render_set", text="Render Selected Sets", icon='RENDERLAYERS')
        op.mode = 'selected'

        op = col.operator("comprs.render_set", text="Render All Sets", icon='RENDER_ANIMATION')
        op.mode = 'all'

        box.separator()

        # Abort button (only enabled when rendering)
        col = box.column(align=True)
        col.enabled = props.is_rendering
        col.operator("comprs.abort_render", text="Abort Render", icon='CANCEL')

        layout.separator()

        # ====================================================================
        # Settings Section
        # ====================================================================

        box = layout.box()
        box.label(text="Settings", icon='PREFERENCES')

        settings = props.settings
        col = box.column(align=True)
        col.prop(settings, "output_node_name", text="Output Node Name")
        col.prop(settings, "name_prefix", text="Name Prefix")

        box.separator()
        col = box.column(align=True)
        col.label(text="UI Settings:", icon='WINDOW')
        col.prop(settings, "max_tabs_per_row", text="Max Tabs Per Row")

        box.separator()
        col = box.column(align=True)
        col.label(text="Sync Options:", icon='UV_SYNC_SELECT')
        col.prop(settings, "sync_visibility")
        col.prop(settings, "sync_modifiers")
        col.prop(settings, "sync_objects")

        box.separator()
        col = box.column(align=True)
        col.label(text="Visibility Options:", icon='RESTRICT_VIEW_OFF')
        col.prop(settings, "hide_undefined_collections")
        col.prop(settings, "only_show_renderable")

        box.separator()
        col = box.column(align=True)
        col.prop(settings, "enable_log", text="Enable Log")

        # Debug/Test button
        box.separator()
        box.operator("comprs.test_node_setup", text="Test Node Setup", icon='VIEWZOOM')

        layout.separator()

        # ====================================================================
        # Log Section
        # ====================================================================

        box = layout.box()
        row = box.row()
        row.label(text="Log", icon='TEXT')
        row.operator("comprs.clear_log", text="", icon='X')

        if props.log_text:
            # Split log into lines and show last 10
            lines = props.log_text.strip().split('\n')
            num_lines_to_show = min(10, len(lines))

            col = box.column(align=True)
            for line in lines[-num_lines_to_show:]:
                col.label(text=line[:80])  # Truncate long lines
        else:
            box.label(text="No log entries yet")


# ============================================================================
# Additional Panels for Other Editors
# ============================================================================

class COMPRS_PT_ShaderEditorPanel(Panel):
    """Panel in Shader Editor"""
    bl_label = "Compositor Render Sets"
    bl_idname = "COMPRS_PT_shader_editor_panel"
    bl_space_type = 'NODE_EDITOR'
    bl_region_type = 'UI'
    bl_category = 'Render Sets'

    @classmethod
    def poll(cls, context):
        return context.space_data.tree_type == 'ShaderNodeTree'

    def draw(self, context):
        # Use the same draw method as the main panel
        COMPRS_PT_MainPanel.draw(self, context)


class COMPRS_PT_CompositorPanel(Panel):
    """Panel in Compositor"""
    bl_label = "Compositor Render Sets"
    bl_idname = "COMPRS_PT_compositor_panel"
    bl_space_type = 'NODE_EDITOR'
    bl_region_type = 'UI'
    bl_category = 'Render Sets'

    @classmethod
    def poll(cls, context):
        return context.space_data.tree_type == 'CompositorNodeTree'

    def draw(self, context):
        # Use the same draw method as the main panel
        COMPRS_PT_MainPanel.draw(self, context)


class COMPRS_PT_GeometryNodesPanel(Panel):
    """Panel in Geometry Nodes Editor"""
    bl_label = "Compositor Render Sets"
    bl_idname = "COMPRS_PT_geometry_nodes_panel"
    bl_space_type = 'NODE_EDITOR'
    bl_region_type = 'UI'
    bl_category = 'Render Sets'

    @classmethod
    def poll(cls, context):
        return context.space_data.tree_type == 'GeometryNodeTree'

    def draw(self, context):
        # Use the same draw method as the main panel
        COMPRS_PT_MainPanel.draw(self, context)


# ============================================================================
# Additional Operators
# ============================================================================

class COMPRS_OT_SelectSet(Operator):
    """Select a render set tab"""
    bl_idname = "comprs.select_set"
    bl_label = "Select Set"

    index: IntProperty()

    def execute(self, context):
        props = context.scene.compositor_render_sets
        props.active_set_index = self.index
        return {'FINISHED'}


class COMPRS_OT_ClearLog(Operator):
    """Clear the render log"""
    bl_idname = "comprs.clear_log"
    bl_label = "Clear Log"

    def execute(self, context):
        context.scene.compositor_render_sets.log_text = ""
        return {'FINISHED'}


class COMPRS_OT_TestNodeSetup(Operator):
    """Test if the File Output node can be found and configured"""
    bl_idname = "comprs.test_node_setup"
    bl_label = "Test Node Setup"
    bl_description = "Verify that the File Output node is correctly configured"

    def execute(self, context):
        props = context.scene.compositor_render_sets

        print("\n" + "="*60)
        print("TESTING FILE OUTPUT NODE SETUP")
        print("="*60)

        # Test 1: Find the node
        node, error = find_file_output_node(context)
        if not node:
            self.report({'ERROR'}, error)
            log_message(context, f"TEST FAILED: {error}")
            return {'CANCELLED'}

        self.report({'INFO'}, f"✓ Found node: {node.name}")
        log_message(context, f"✓ Node found: {node.name}")

        # Test 2: Check file slots
        prefix = props.settings.name_prefix
        file_slots = get_output_node_file_slots(node)
        matching_slots = [get_slot_path(slot) for slot in file_slots if get_slot_path(slot).startswith(prefix)]

        if not matching_slots:
            msg = f"No file slots with prefix '{prefix}' found. Available slots: {[get_slot_path(slot) for slot in file_slots]}"
            self.report({'WARNING'}, msg)
            log_message(context, f"WARNING: {msg}")
        else:
            self.report({'INFO'}, f"✓ Found {len(matching_slots)} matching slots: {matching_slots}")
            log_message(context, f"✓ Matching slots ({len(matching_slots)}): {', '.join(matching_slots)}")

        # Test 3: Check current render set
        render_set = get_active_render_set(context)
        if not render_set:
            msg = "No active render set"
            self.report({'WARNING'}, msg)
            log_message(context, f"WARNING: {msg}")
        else:
            self.report({'INFO'}, f"✓ Active set: {render_set.name}")
            log_message(context, f"✓ Active render set: {render_set.name}")

            # Test 4: Simulate configuration
            print("\nSimulating configuration:")
            for slot in file_slots:
                slot_path = get_slot_path(slot)
                if slot_path.startswith(prefix):
                    remainder = slot_path[len(prefix):]
                    new_name = render_set.name + remainder
                    print(f"  {slot_path} → {new_name}")

        print("="*60)
        print("TEST COMPLETE")
        print("="*60 + "\n")

        self.report({'INFO'}, "Node setup test complete - check console for details")
        return {'FINISHED'}


# ============================================================================
# Registration
# ============================================================================

classes = (
    COMPRS_CollectionItem,
    COMPRS_RenderSet,
    COMPRS_Settings,
    COMPRS_Properties,
    COMPRS_OT_AddRenderSet,
    COMPRS_OT_RemoveRenderSet,
    COMPRS_OT_AddCollection,
    COMPRS_OT_RemoveCollection,
    COMPRS_OT_ToggleSetVisibility,
    COMPRS_OT_SoloSet,
    COMPRS_OT_HideOtherSets,
    COMPRS_OT_RenderSet,
    COMPRS_OT_AbortRender,
    COMPRS_OT_SelectSet,
    COMPRS_OT_ClearLog,
    COMPRS_OT_TestNodeSetup,
    COMPRS_UL_CollectionList,
    COMPRS_PT_MainPanel,
    COMPRS_PT_ShaderEditorPanel,
    COMPRS_PT_CompositorPanel,
    COMPRS_PT_GeometryNodesPanel,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)

    bpy.types.Scene.compositor_render_sets = PointerProperty(type=COMPRS_Properties)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)

    del bpy.types.Scene.compositor_render_sets


if __name__ == "__main__":
    register()
