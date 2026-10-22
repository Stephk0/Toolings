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


def apply_plan(visible, index):
    """``(apply, skip)``: indices above ``index`` to apply top to bottom, and the
    switched-off ones to leave in place.

    Blender applies a modifier even when it is off in the viewport, which would
    bake in something the stack doesn't show, so those are skipped.
    """
    if not 0 <= index < len(visible):
        raise IndexError(f"modifier index {index} out of range ({len(visible)})")
    apply = [i for i in range(index) if visible[i]]
    skip = [i for i in range(index) if not visible[i]]
    return apply, skip


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


def insert_target(names, new, anchor, position):
    """Final index for moving ``new`` directly ``'BEFORE'`` or ``'AFTER'`` ``anchor``.

    ``names`` is the current stack, already holding ``new``.
    """
    rest = [n for n in names if n != new]
    return insert_index(rest.index(anchor), position)


MOVE_POSITIONS = ('FIRST', 'LAST', 'UP', 'DOWN', 'BEFORE_PINNED', 'AFTER_PINNED')


def move_plan(pinned, index, position):
    """``(target index, new pin state or None)`` for moving the modifier at ``index``.

    ``pinned`` holds each modifier's Pin to Last flag. Blender keeps pinned
    modifiers as a block at the end of the stack and refuses (silently) any
    move across that block, so plain moves stay inside the modifier's own
    block. Crossing it changes the pin:

    - ``'FIRST'`` on a pinned modifier unpins it and moves it to the top.
    - ``'BEFORE_PINNED'`` unpins it and puts it right above the pinned block.
    - ``'AFTER_PINNED'`` pins an unpinned modifier and puts it at the very end.

    ``'LAST'`` on an unpinned modifier is the slot right above the pinned block.
    UP / DOWN stay put at the ends of the block.
    """
    count = len(pinned)
    if not 0 <= index < count:
        raise IndexError(f"modifier index {index} out of range ({count})")
    if position not in MOVE_POSITIONS:
        raise ValueError(f"position must be one of {MOVE_POSITIONS}, not {position!r}")
    first_pinned = count - sum(1 for p in pinned if p)
    is_pinned = bool(pinned[index])
    low, high = (first_pinned, count - 1) if is_pinned else (0, first_pinned - 1)

    if position == 'FIRST':
        return (0, False) if is_pinned else (0, None)
    if position == 'LAST':
        return high, None
    if position == 'UP':
        return max(index - 1, low), None
    if position == 'DOWN':
        return min(index + 1, high), None
    if position == 'BEFORE_PINNED':
        # Unpinning grows the unpinned block by one; its last slot is first_pinned.
        return (first_pinned, False) if is_pinned else (high, None)
    # AFTER_PINNED
    return (count - 1, None) if is_pinned else (count - 1, True)


def move_changes(pinned, index, position):
    """True when :func:`move_plan` would change anything (used to grey out menu entries)."""
    target, pin = move_plan(pinned, index, position)
    return target != index or pin is not None
