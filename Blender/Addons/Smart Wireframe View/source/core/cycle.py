"""Smart Wireframe View cycle logic. bpy-free.

Three viewport display states, cycled in this order:
OFF        overlays off
OVERLAYS   overlays on, geometry wireframe off
WIREFRAME  overlays on, geometry wireframe on
"""

OFF = "OFF"
OVERLAYS = "OVERLAYS"
WIREFRAME = "WIREFRAME"

ORDER = (OFF, OVERLAYS, WIREFRAME)


def state_of(show_overlays, show_wireframes):
    """Map the two viewport flags to a state."""
    if not show_overlays:
        return OFF
    return WIREFRAME if show_wireframes else OVERLAYS


def flags_of(state):
    """Return (show_overlays, show_wireframes) for a state."""
    return {OFF: (False, False), OVERLAYS: (True, False), WIREFRAME: (True, True)}[state]


def next_state(current, enabled=ORDER, reverse=False):
    """Next enabled state after `current` (before it when `reverse`).

    `current` need not be enabled itself; the walk starts from its position in
    ORDER. With nothing enabled the current state is kept.
    """
    enabled = [s for s in ORDER if s in enabled]
    if not enabled:
        return current
    step = -1 if reverse else 1
    i = ORDER.index(current)
    for _ in range(len(ORDER)):
        i = (i + step) % len(ORDER)
        if ORDER[i] in enabled:
            return ORDER[i]
    return current
