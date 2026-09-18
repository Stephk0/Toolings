"""Slot-name and output-path computations. No bpy imports."""

FALLBACK_PREFIX = "XXX"


def ensure_trailing_slash(path, sep='/'):
    """Return path guaranteed to end with a directory separator.

    File Output nodes treat the base path as a directory only when it ends
    with a separator, so this must run before assigning it to the node.
    """
    if not path:
        return path
    if path.endswith('/') or path.endswith('\\'):
        return path
    return path + sep


def resolve_prefix(global_prefix, override_enabled, override_prefix):
    """Pick the slot-name prefix: per-set override > global > fallback."""
    if override_enabled and override_prefix:
        return override_prefix
    return global_prefix or FALLBACK_PREFIX


def replace_prefix(slot_path, prefix, set_name):
    """Rename a slot path by swapping its prefix for the render set name.

    Returns the new name, or None when the slot doesn't start with the
    prefix (meaning: leave the slot untouched).
    """
    if prefix and slot_path and slot_path.startswith(prefix):
        return set_name + slot_path[len(prefix):]
    return None


def compute_slot_renames(slot_paths, prefix, set_name):
    """Blender 4.x mode: [(old_path, new_path_or_None), ...] for all slots."""
    return [(path, replace_prefix(path, prefix, set_name)) for path in slot_paths]


def compute_output_names(slot_paths, set_name):
    """Blender 5 file_name-field mode: final outputs are '<set>_<slot>'."""
    return [f"{set_name}_{path}" if path else set_name for path in slot_paths]
