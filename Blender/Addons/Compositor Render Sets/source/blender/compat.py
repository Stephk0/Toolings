"""Blender version compatibility layer for compositor / File Output APIs.

Blender 5.0 renamed several compositor APIs:
  scene.node_tree      -> scene.compositing_node_group
  node.base_path       -> node.directory
  node.file_slots      -> node.file_output_items
  (new) node.file_name -> single filename field per node
All access to those goes through this module.
"""

import bpy


def debug_enabled():
    """Read the addon's debug toggle; False when unavailable (startup, tests)."""
    try:
        return bpy.context.scene.compositor_render_sets.settings.enable_debug
    except (AttributeError, KeyError):
        return False


def dbg(message):
    """Print verbose diagnostics only when the user enabled debug output."""
    if debug_enabled():
        print(message)


def get_compositor_node_tree(scene):
    """Return the compositor node tree, or None (handles 4.x and 5.0+ APIs)."""
    if getattr(scene, 'compositing_node_group', None):
        return scene.compositing_node_group
    if getattr(scene, 'node_tree', None):
        return scene.node_tree
    return None


def get_output_node_base_path(node):
    """Get base path from a File Output node."""
    if hasattr(node, 'directory'):
        return node.directory
    if hasattr(node, 'base_path'):
        return node.base_path
    return ""


def set_output_node_base_path(node, path):
    """Set base path on a File Output node."""
    if hasattr(node, 'directory'):
        node.directory = path
    elif hasattr(node, 'base_path'):
        node.base_path = path
    else:
        print("[COMPRS WARNING] Could not set base path on node - unknown API")


def get_output_node_file_slots(node):
    """Get the file slot collection from a File Output node."""
    slots = getattr(node, 'file_slots', None)
    if slots is not None:
        return slots
    slots = getattr(node, 'file_output_items', None)
    if slots is not None:
        return slots
    print("[COMPRS WARNING] Could not find file slots attribute on node "
          f"'{node.name}'")
    return []


def get_slot_path(slot):
    """Get the subpath/filename from a file slot."""
    if hasattr(slot, 'path'):
        return slot.path
    if hasattr(slot, 'name'):
        return slot.name
    print("[COMPRS WARNING] Could not find path attribute on slot "
          f"(type: {type(slot)})")
    return ""


def set_slot_path(slot, path):
    """Set the subpath/filename on a file slot. Returns True on success."""
    for attr in ('path', 'name'):
        if hasattr(slot, attr):
            try:
                setattr(slot, attr, path)
                return True
            except (AttributeError, TypeError) as e:
                print(f"[COMPRS ERROR] Could not set {attr} on slot: {e}")
                return False
    print("[COMPRS WARNING] Could not set path on slot - no suitable attribute")
    return False
