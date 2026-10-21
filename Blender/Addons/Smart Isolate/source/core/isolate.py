"""Smart Isolate decision logic. bpy-free.

The isolation state of one viewport is a stack of levels. Each level is the
frozenset of object keys the user isolated at that step (extras such as kept
cameras/lights are added by the Blender layer and are not part of a level).
"""

from dataclasses import dataclass

# Actions
NONE = "NONE"        # nothing to do (not isolated and nothing selected)
ENTER = "ENTER"      # enter isolation with the selection as level 1
DEEPER = "DEEPER"    # push the selection as a new, deeper level
REPLACE = "REPLACE"  # swap the current level for the selection
BACK = "BACK"        # pop one level (exits when leaving level 1)
EXIT = "EXIT"        # leave isolation completely

# Preference values for empty / same selection
STEP_BACK = "BACK"
EXIT_ALL = "EXIT"


@dataclass(frozen=True)
class Settings:
    nested: bool = True                # subset of the current level goes one deeper
    empty_selection: str = EXIT_ALL    # what pressing with nothing selected does
    same_selection: str = STEP_BACK    # what pressing with an unchanged selection does


def decide(selection, stack, settings=Settings()):
    """Return the action for one press of the Smart Isolate key."""
    selection = frozenset(selection)
    if not stack:
        return ENTER if selection else NONE
    top = stack[-1]
    if not selection:
        return _back_or_exit(settings.empty_selection, stack)
    if selection == top:
        return _back_or_exit(settings.same_selection, stack)
    if settings.nested and selection < top:
        return DEEPER
    return REPLACE


def _back_or_exit(choice, stack):
    if choice == STEP_BACK and len(stack) > 1:
        return BACK
    return EXIT


def apply(action, selection, stack):
    """Return the new stack after `action`. Does not mutate `stack`."""
    stack = list(stack)
    selection = frozenset(selection)
    if action == ENTER:
        return [selection]
    if action == DEEPER:
        return stack + [selection]
    if action == REPLACE:
        return stack[:-1] + [selection]
    if action == BACK:
        return stack[:-1]
    if action == EXIT:
        return []
    return stack


def prune(stack, existing):
    """Drop deleted objects from every level, then drop levels that became empty."""
    existing = frozenset(existing)
    out = []
    for level in stack:
        level = level & existing
        if level:
            out.append(level)
    return out
