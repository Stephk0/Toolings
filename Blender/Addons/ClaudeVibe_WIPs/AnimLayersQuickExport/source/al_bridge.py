"""Thin wrapper over the Animation Layers addon.

Keeps every reference to the third-party `Animation_Layers` package isolated
to this module so the rest of the addon can stay agnostic to its API.

Restoration strategy: instead of relying on Blender's undo stack (which doesn't
reliably isolate the merge operator's effects), we explicitly snapshot the AL
data surface before the merge and replay it after the export. This covers the
typical AL setup (one strip per track, default field layout). Edge cases like
multi-strip tracks or custom NLA modifiers may need follow-up work.
"""

import addon_utils

ANIMATION_LAYERS_MODULE = "Animation_Layers"


def is_animation_layers_available():
    _default, loaded = addon_utils.check(ANIMATION_LAYERS_MODULE)
    return loaded


def get_layer_count(obj):
    if obj is None:
        return 0
    layers = getattr(obj, "Anim_Layers", None)
    if layers is None:
        return 0
    return len(layers)


def has_animation_layers(obj):
    return get_layer_count(obj) > 0


def merge_all_layers(obj, *, baketype="AL", smartbake=False, step=1, actioncopy=True):
    """Mutates `obj.als` then triggers AL's `anim.layers_merge_down` with direction=ALL."""
    import bpy

    als = obj.als
    als.direction = "ALL"
    als.baketype = baketype
    als.operator = "MERGE"
    als.smartbake = smartbake
    if obj.Anim_Layers:
        als.layer_index = len(obj.Anim_Layers) - 1

    return bpy.ops.anim.layers_merge_down(step=step, actioncopy=actioncopy)


_ALS_FIELDS = (
    "layer_index", "data_type", "direction", "baketype", "operator",
    "smartbake", "blend_type", "auto_rename",
)
_LAYER_FIELDS = (
    "name", "mute", "lock", "solo", "influence",
    "custom_frame_range", "frame_start", "frame_end",
    "speed", "offset", "repeat",
)
_TRACK_FIELDS = ("name", "mute", "lock", "is_solo")
_STRIP_FIELDS = (
    "name", "blend_type", "frame_start", "frame_end",
    "scale", "repeat", "extrapolation", "mute",
    "blend_in", "blend_out", "use_auto_blend",
    "influence",
    # Deliberately not restoring use_animated_influence / use_animated_time:
    # AL creates strips with animated influence backed by an empty fcurve,
    # which evaluates to 0 when replayed on a freshly created strip and
    # leaves the rig in T-pose. Static influence is the only field worth
    # preserving for the snapshot/restore round-trip.
)


def snapshot_state(obj):
    """Capture the AL data surface for later restoration."""
    if obj is None:
        return None

    state = {
        "als": {f: getattr(obj.als, f) for f in _ALS_FIELDS if hasattr(obj.als, f)},
        "active_action": (
            obj.animation_data.action.name
            if obj.animation_data and obj.animation_data.action else None
        ),
        "anim_layers": [],
        "nla_tracks": [],
    }

    # Store actual datablock references — they survive Animation Layers
    # renaming actions during the merge, which name-based lookup does not.
    for layer in obj.Anim_Layers:
        layer_state = {f: getattr(layer, f) for f in _LAYER_FIELDS if hasattr(layer, f)}
        layer_state["_action_ref"] = layer.action
        state["anim_layers"].append(layer_state)

    if obj.animation_data:
        for track in obj.animation_data.nla_tracks:
            track_state = {f: getattr(track, f) for f in _TRACK_FIELDS if hasattr(track, f)}
            track_state["strips"] = []
            for strip in track.strips:
                strip_state = {f: getattr(strip, f) for f in _STRIP_FIELDS if hasattr(strip, f)}
                strip_state["_action_ref"] = strip.action
                track_state["strips"].append(strip_state)
            state["nla_tracks"].append(track_state)

    state["_active_action_ref"] = (
        obj.animation_data.action if obj.animation_data and obj.animation_data.action else None
    )

    return state


def _clear_anim_layers(obj):
    obj.Anim_Layers.clear()


def _clear_nla_tracks(obj):
    if obj.animation_data is None:
        return
    while obj.animation_data.nla_tracks:
        obj.animation_data.nla_tracks.remove(obj.animation_data.nla_tracks[0])


def _resolve_action_ref(ref):
    """Validate a stored action reference is still a live datablock."""
    if ref is None:
        return None
    try:
        _ = ref.name  # touching the ref raises if it was unlinked
        return ref
    except (ReferenceError, RuntimeError):
        return None


def restore_state(obj, state):
    """Reverse of snapshot_state — clears merged data and rebuilds from snapshot."""
    import bpy

    if obj is None or state is None:
        return

    if obj.animation_data is None:
        obj.animation_data_create()

    _clear_anim_layers(obj)
    _clear_nla_tracks(obj)

    for track_state in state["nla_tracks"]:
        track = obj.animation_data.nla_tracks.new()
        track.name = track_state.get("name", "Track")
        for strip_state in track_state["strips"]:
            action = _resolve_action_ref(strip_state.get("_action_ref"))
            if action is None:
                continue
            try:
                strip = track.strips.new(
                    strip_state.get("name", action.name),
                    int(strip_state["frame_start"]),
                    action,
                )
            except RuntimeError:
                continue
            for f in _STRIP_FIELDS:
                if f in strip_state and hasattr(strip, f):
                    try:
                        setattr(strip, f, strip_state[f])
                    except (AttributeError, TypeError):
                        pass
        for f in _TRACK_FIELDS:
            if f in track_state and f != "name" and hasattr(track, f):
                try:
                    setattr(track, f, track_state[f])
                except (AttributeError, TypeError):
                    pass

    active_action = _resolve_action_ref(state.get("_active_action_ref"))
    if active_action and obj.animation_data:
        try:
            obj.animation_data.action = active_action
        except (AttributeError, TypeError, RuntimeError):
            pass

    for layer_state in state["anim_layers"]:
        item = obj.Anim_Layers.add()
        for f in _LAYER_FIELDS:
            if f in layer_state and hasattr(item, f):
                try:
                    setattr(item, f, layer_state[f])
                except (AttributeError, TypeError):
                    pass
        action = _resolve_action_ref(layer_state.get("_action_ref"))
        if action is not None:
            try:
                item.action = action
            except (AttributeError, TypeError):
                pass

    # AL's setters re-enable animated influence on restored strips, but those
    # strips have empty influence fcurves (= evaluates to 0 = T-pose). Force
    # static influence instead, matched to the snapshot's per-layer value.
    if obj.animation_data:
        layer_states = state["anim_layers"]
        for i, track in enumerate(obj.animation_data.nla_tracks):
            if not track.strips:
                continue
            target_influence = (
                layer_states[i].get("influence", 1.0) if i < len(layer_states) else 1.0
            )
            for strip in track.strips:
                try:
                    strip.use_animated_influence = False
                    strip.influence = target_influence
                except (AttributeError, TypeError):
                    pass

    # Restore everything else first, then layer_index last — AL callbacks
    # triggered by other field setters can otherwise stomp the index.
    saved_layer_index = state["als"].get("layer_index")
    for f, v in state["als"].items():
        if f == "layer_index" or not hasattr(obj.als, f):
            continue
        try:
            setattr(obj.als, f, v)
        except (AttributeError, TypeError):
            pass
    if saved_layer_index is not None and 0 <= saved_layer_index < len(obj.Anim_Layers):
        try:
            obj.als.layer_index = saved_layer_index
        except (AttributeError, TypeError):
            pass
