"""File Output node discovery, state caching and per-set configuration."""

import os

import bpy

from ..core import naming
from .compat import (
    dbg,
    get_compositor_node_tree,
    get_output_node_base_path,
    get_output_node_file_slots,
    get_slot_path,
    set_output_node_base_path,
    set_slot_path,
)


def find_file_output_node(context, render_set=None):
    """Find the configured File Output node in the compositor.

    Returns (node, None) on success or (None, error_message).
    render_set: optional set whose output-node override should be used.
    """
    scene = context.scene

    # Scene.use_nodes is deprecated and slated for removal in Blender 6.0
    if hasattr(scene, 'use_nodes') and not scene.use_nodes:
        return None, ("Compositor 'Use Nodes' is not enabled. "
                      "Enable it in the Compositor workspace.")

    node_tree = get_compositor_node_tree(scene)
    if not node_tree:
        return None, ("No compositor node tree found. Ensure 'Use Nodes' is "
                      "enabled in the Compositor workspace.")

    if render_set and render_set.override_output_settings:
        node_name = render_set.output_node_name_override
        dbg(f"[FIND NODE] Using per-set override for '{render_set.name}'")
    else:
        node_name = context.scene.compositor_render_sets.settings.output_node_name

    dbg(f"[FIND NODE] Looking for File Output node named: '{node_name}'")

    file_output_nodes = [n for n in node_tree.nodes if n.type == 'OUTPUT_FILE']
    for node in file_output_nodes:
        if node.name == node_name:
            dbg(f"[FIND NODE] Found '{node.name}' "
                f"(base path: {get_output_node_base_path(node)})")
            return node, None

    if file_output_nodes:
        names = ', '.join(n.name for n in file_output_nodes)
        return None, (f"File Output node '{node_name}' not found. "
                      f"Available File Output nodes: {names}")
    return None, ("No File Output nodes found in compositor. "
                  f"Please add one and name it '{node_name}'")


def snapshot_output_nodes_mute(context):
    """Record {node_name: mute} for every File Output node (no changes)."""
    node_tree = get_compositor_node_tree(context.scene)
    if not node_tree:
        return {}
    return {node.name: node.mute for node in node_tree.nodes
            if node.type == 'OUTPUT_FILE'}


def mute_unused_output_nodes(context, active_node_name):
    """Mute all File Output nodes except the named one."""
    node_tree = get_compositor_node_tree(context.scene)
    if not node_tree:
        return

    dbg(f"[MUTE] Muting all File Output nodes except '{active_node_name}'")
    for node in node_tree.nodes:
        if node.type == 'OUTPUT_FILE':
            node.mute = node.name != active_node_name


def restore_output_nodes_mute_state(context, original_states):
    """Restore mute states captured by snapshot_output_nodes_mute."""
    if not original_states:
        return
    node_tree = get_compositor_node_tree(context.scene)
    if not node_tree:
        return

    dbg("[RESTORE] Restoring File Output node mute states")
    for node in node_tree.nodes:
        if node.type == 'OUTPUT_FILE' and node.name in original_states:
            node.mute = original_states[node.name]


def cache_node_state(node):
    """Cache a File Output node's user-facing state as a plain dict."""
    state = {
        'base_path': get_output_node_base_path(node),
        'file_slots': [],
    }
    # Blender 5's per-node filename field must round-trip too, otherwise a
    # user-set filename is wiped on restore.
    if hasattr(node, 'file_name'):
        state['file_name'] = node.file_name

    file_slots = get_output_node_file_slots(node)
    dbg(f"[CACHE] Caching node '{node.name}' "
        f"({len(file_slots)} slot(s), base path '{state['base_path']}')")
    for i, slot in enumerate(file_slots):
        state['file_slots'].append({'path': get_slot_path(slot), 'index': i})

    return state


def restore_node_state(node, state):
    """Restore a File Output node from a cache_node_state dict."""
    dbg(f"[RESTORE] Restoring node '{node.name}' "
        f"(base path '{state['base_path']}')")
    set_output_node_base_path(node, state['base_path'])

    if hasattr(node, 'file_name'):
        node.file_name = state.get('file_name', "")

    file_slots = get_output_node_file_slots(node)
    for slot_data in state['file_slots']:
        idx = slot_data['index']
        if idx < len(file_slots):
            set_slot_path(file_slots[idx], slot_data['path'])


def configure_node_for_set(node, render_set, context):
    """Point a File Output node at a render set's path and slot names.

    Returns the list of output names that will be written.
    """
    dbg(f"[CONFIGURE] Configuring File Output node for set: {render_set.name}")

    output_path = naming.ensure_trailing_slash(
        bpy.path.abspath(render_set.output_path), os.sep)
    set_output_node_base_path(node, output_path)

    try:
        os.makedirs(output_path, exist_ok=True)
    except OSError as e:
        print(f"[COMPRS WARNING] Could not create directory {output_path}: {e}")

    file_slots = get_output_node_file_slots(node)
    slot_paths = [get_slot_path(slot) for slot in file_slots]

    # Blender 5: one filename field per node; slots stay untouched.
    if hasattr(node, 'file_name'):
        node.file_name = render_set.name
        output_names = naming.compute_output_names(slot_paths, render_set.name)
        dbg(f"  [BLENDER 5] file_name = '{render_set.name}', "
            f"outputs: {output_names}")
        return output_names

    # Blender 4.x: rewrite each slot path by swapping the prefix.
    settings = context.scene.compositor_render_sets.settings
    prefix = naming.resolve_prefix(
        settings.name_prefix,
        render_set.override_output_settings,
        render_set.name_prefix_override,
    )
    dbg(f"  [BLENDER 4.x] Renaming {len(slot_paths)} slot(s) "
        f"with prefix '{prefix}'")

    output_names = []
    renames = naming.compute_slot_renames(slot_paths, prefix, render_set.name)
    for slot, (old_path, new_path) in zip(file_slots, renames):
        if new_path is None:
            dbg(f"    '{old_path}' (no prefix match, keeping as-is)")
            output_names.append(old_path)
        elif set_slot_path(slot, new_path):
            dbg(f"    '{old_path}' -> '{new_path}'")
            output_names.append(new_path)
        else:
            print(f"[COMPRS ERROR] Failed to rename slot '{old_path}'")
            output_names.append(old_path)

    return output_names
