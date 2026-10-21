"""Modifier-stack planning, bpy-free.

The Blender side reads the stack into plain lists (names, viewport flags),
asks these functions what to change, and applies the answer.
"""

import json

STATE_VERSION = 1


def hide_after_plan(visible, index):
    """Indices after ``index`` that are visible and must be hidden.

    Modifiers the user already disabled are left out, so restoring never
    turns on something that was off before.
    """
    if not 0 <= index < len(visible):
        raise IndexError(f"modifier index {index} out of range ({len(visible)})")
    return [i for i in range(index + 1, len(visible)) if visible[i]]


def encode_state(target, hidden_names):
    """Serialize an active "up to here" preview for storage on the object."""
    return json.dumps({"v": STATE_VERSION, "target": target, "hidden": list(hidden_names)})


def decode_state(raw):
    """Inverse of :func:`encode_state`. Empty or unreadable state -> None."""
    if not raw:
        return None
    try:
        data = json.loads(raw)
    except ValueError:
        return None
    if not isinstance(data, dict) or not isinstance(data.get("hidden"), list):
        return None
    return {"target": str(data.get("target", "")), "hidden": [str(n) for n in data["hidden"]]}


def restore_plan(current_names, hidden_names):
    """Indices of modifiers to show again.

    Matches by name; modifiers deleted since the preview started are skipped.
    """
    wanted = set(hidden_names)
    return [i for i, name in enumerate(current_names) if name in wanted]


def extract_plan(visible, index):
    """Viewport flags to set for evaluating the stack up to ``index``.

    Returns ``{modifier_index: show_viewport}`` for only the flags that change:
    the target is forced on, everything after it off, earlier modifiers keep
    the user's state.
    """
    changes = {i: False for i in hide_after_plan(visible, index)}
    if not visible[index]:
        changes[index] = True
    return changes


def extract_name(object_name, modifier_name):
    """Name for the extracted object/mesh."""
    return f"{object_name}_{modifier_name}"


def insert_index(anchor_index, position):
    """Stack index for a modifier inserted ``'BEFORE'`` or ``'AFTER'`` the anchor."""
    if position == 'BEFORE':
        return anchor_index
    if position == 'AFTER':
        return anchor_index + 1
    raise ValueError(f"position must be 'BEFORE' or 'AFTER', not {position!r}")


def find_added(before, after):
    """Name of the single modifier added between two snapshots of a stack, else None.

    None when nothing was added, more than one was, or an old one disappeared,
    so an unrelated stack edit is never mistaken for the insert.
    """
    if len(after) != len(before) + 1:
        return None
    old = set(before)
    if not old.issubset(after):
        return None
    new = [n for n in after if n not in old]
    return new[0] if len(new) == 1 else None


def move_index(count, position):
    """Target index for moving a modifier ``'FIRST'`` or ``'LAST'`` in a stack of ``count``."""
    if position == 'FIRST':
        return 0
    if position == 'LAST':
        return count - 1
    raise ValueError(f"position must be 'FIRST' or 'LAST', not {position!r}")
