"""Thin wrapper over the Animation Layers addon.

The addon works without Animation Layers (vanilla FBX export only). When AL is
detected, this module exposes its merge/bake operator and provides a
non-destructive snapshot/restore round-trip.

The snapshot deep-copies every layer/strip action via `action.copy()` because
AL's `AL_bake()` mutates the action at `obj.als.layer_index` in place — the
layer's own action datablock ends up containing the merged keyframes. Without
the deep copy, restoring would re-attach that mutated action and the top layer
would come back filled with the baked-down combined keys (the bug we hit).
"""

import addon_utils

ANIMATION_LAYERS_MODULE = "Animation_Layers"

_TEMP_NAME_PREFIX = "__qae_pre_remove__"


def is_animation_layers_installed():
    """True when the AL addon is *registered* with Blender (whether enabled or not)."""
    for mod in addon_utils.modules(refresh=False):
        if mod.__name__ == ANIMATION_LAYERS_MODULE:
            return True
    return False


def is_animation_layers_enabled():
    """True when the AL addon is currently *enabled*."""
    _default, loaded = addon_utils.check(ANIMATION_LAYERS_MODULE)
    return loaded


# Backwards compatibility for code that asked the older question.
def is_animation_layers_available():
    return is_animation_layers_enabled()


def get_layer_count(obj):
    if obj is None:
        return 0
    layers = getattr(obj, "Anim_Layers", None)
    if layers is None:
        return 0
    return len(layers)


def has_animation_layers(obj):
    return get_layer_count(obj) > 0


def apply_bake_props_to_als(obj, scene, props):
    """Push the QAE bake-mirror props onto AL's `obj.als` / `scene.als`.

    Called right before invoking `anim.layers_merge_down`. The original AL
    values are part of the snapshot, so they get restored along with the rest.
    """
    als = obj.als
    als.baketype = props.al_baketype
    als.operator = props.al_operator
    als.direction = props.al_direction
    als.mergefcurves = props.al_mergefcurves
    als.smartbake = props.al_smartbake
    als.onlyselected = props.al_onlyselected
    als.clearconstraints = props.al_clearconstraints

    scene_als = getattr(scene, "als", None)
    if scene_als is not None:
        try:
            scene_als.bake_range_type = props.al_bake_range_type
            if props.al_bake_range_type == "CUSTOM":
                scene_als.bake_range = (
                    int(props.al_bake_range_custom[0]),
                    int(props.al_bake_range_custom[1]),
                )
            scene_als.handles_type = props.al_handles_type
        except (AttributeError, TypeError):
            pass


def merge_all_layers(obj, *, props=None, baketype="AL", smartbake=False, step=1, actioncopy=False):
    """Trigger AL's `anim.layers_merge_down`.

    When `props` is given, the full QAE bake mirror is applied to AL first.
    Otherwise the legacy minimal field set is used (kept for callers that just
    want a default 'merge all into one' without exposing the dialog options).
    """
    import bpy

    als = obj.als

    if props is not None:
        apply_bake_props_to_als(obj, bpy.context.scene, props)
        # We want every layer collapsed into one — pin the index to the top so
        # AL's "merge down ALL" lands its result on the top layer's track.
        if obj.Anim_Layers:
            als.layer_index = len(obj.Anim_Layers) - 1
        return bpy.ops.anim.layers_merge_down(
            step=props.al_step,
            actioncopy=props.al_actioncopy,
        )

    als.direction = "ALL"
    als.baketype = baketype
    als.operator = "MERGE"
    als.smartbake = smartbake
    if obj.Anim_Layers:
        als.layer_index = len(obj.Anim_Layers) - 1
    return bpy.ops.anim.layers_merge_down(step=step, actioncopy=actioncopy)


_ALS_FIELDS = (
    "layer_index", "data_type", "direction", "baketype", "operator",
    "smartbake", "onlyselected", "clearconstraints", "mergefcurves",
    "blend_type", "auto_rename",
)
_LAYER_FIELDS = (
    "name", "mute", "lock", "solo", "influence",
    "custom_frame_range", "frame_start", "frame_end",
    "speed", "offset", "repeat",
)
_TRACK_FIELDS = ("name", "mute", "lock", "is_solo")
_STRIP_FIELDS = (
    "name", "blend_type",
    "action_frame_start", "action_frame_end",  # set BEFORE frame_start/end so
    "frame_start", "frame_end",                #  strip range can extend that far
    "scale", "repeat", "extrapolation", "mute",
    "blend_in", "blend_out", "use_auto_blend",
    "influence",
    # use_animated_influence is intentionally NOT restored: AL creates strips
    # with animated influence backed by an empty fcurve, which evaluates to 0
    # on a freshly created strip and leaves the rig in T-pose. We force static
    # influence below using the snapshotted layer.influence values instead.
)


def _copy_action(action, registry):
    """Return a pristine duplicate of `action`, dedup'd via `registry`.

    Linked actions (one datablock used by several layers) are copied once and
    re-used. Setting `use_fake_user=True` keeps the copy alive across the bake.
    """
    if action is None:
        return None
    key = action.as_pointer()  # stable across renames
    if key in registry:
        return registry[key]
    copy = action.copy()
    copy.use_fake_user = True
    registry[key] = copy
    return copy


def snapshot_state(obj):
    """Capture the AL data surface AND pristine copies of every action."""
    if obj is None:
        return None

    state = {
        "als": {f: getattr(obj.als, f) for f in _ALS_FIELDS if hasattr(obj.als, f)},
        "anim_layers": [],
        "nla_tracks": [],
        "_action_copies": {},  # pointer -> copied Action datablock
        "_action_originals": {},  # pointer -> (datablock, original_name)
    }

    registry = state["_action_copies"]
    originals = state["_action_originals"]

    def _track_original(action):
        if action is None:
            return
        key = action.as_pointer()
        if key not in originals:
            originals[key] = (action, action.name)

    for layer in obj.Anim_Layers:
        layer_state = {f: getattr(layer, f) for f in _LAYER_FIELDS if hasattr(layer, f)}
        a = layer.action
        _track_original(a)
        layer_state["_action_copy"] = _copy_action(a, registry)
        state["anim_layers"].append(layer_state)

    if obj.animation_data:
        for track in obj.animation_data.nla_tracks:
            track_state = {f: getattr(track, f) for f in _TRACK_FIELDS if hasattr(track, f)}
            track_state["strips"] = []
            for strip in track.strips:
                strip_state = {f: getattr(strip, f) for f in _STRIP_FIELDS if hasattr(strip, f)}
                a = strip.action
                _track_original(a)
                strip_state["_action_copy"] = _copy_action(a, registry)
                track_state["strips"].append(strip_state)
            state["nla_tracks"].append(track_state)

        active_action = obj.animation_data.action
        _track_original(active_action)
        state["_active_action_copy"] = _copy_action(active_action, registry)
    else:
        state["_active_action_copy"] = None

    return state


def _clear_anim_layers(obj):
    obj.Anim_Layers.clear()


def _clear_nla_tracks(obj):
    if obj.animation_data is None:
        return
    while obj.animation_data.nla_tracks:
        obj.animation_data.nla_tracks.remove(obj.animation_data.nla_tracks[0])


def _swap_in_pristine_actions(state):
    """Replace mutated originals with our pristine copies, restoring names.

    AL's bake mutates action datablocks in place. We have a clean copy of each
    original. To make the rest of restore work transparently (strips/layers
    referencing actions by name still resolve correctly), we:
      1. Move the (mutated) original out of the way (rename)
      2. Delete it
      3. Rename the copy back to the original name
    """
    import bpy

    originals = state.get("_action_originals", {})
    copies = state.get("_action_copies", {})

    for key, (original_ref, original_name) in originals.items():
        copy = copies.get(key)
        if copy is None:
            continue
        # Validate `original_ref` is still a live datablock; if AL deleted it,
        # the copy can just take the original name directly.
        original_alive = True
        try:
            _ = original_ref.name
        except (ReferenceError, RuntimeError):
            original_alive = False

        if original_alive and original_ref is not copy:
            try:
                original_ref.name = f"{_TEMP_NAME_PREFIX}{original_name}"
                bpy.data.actions.remove(original_ref)
            except (RuntimeError, ReferenceError):
                pass

        try:
            copy.name = original_name
            copy.use_fake_user = False
        except (AttributeError, TypeError):
            pass


def restore_state(obj, state):
    """Reverse of snapshot_state — clears merged data and rebuilds from snapshot."""
    import bpy

    if obj is None or state is None:
        return

    # Step 1: swap pristine action copies back in place of the mutated originals.
    _swap_in_pristine_actions(state)

    # Step 2: rebuild Anim_Layers and NLA stack referring to those copies.
    if obj.animation_data is None:
        obj.animation_data_create()

    _clear_anim_layers(obj)
    _clear_nla_tracks(obj)

    layer_states = state["anim_layers"]
    track_states = state["nla_tracks"]

    for track_state in track_states:
        track = obj.animation_data.nla_tracks.new()
        track.name = track_state.get("name", "Track")
        for strip_state in track_state["strips"]:
            action = strip_state.get("_action_copy")
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

    active_action = state.get("_active_action_copy")
    if active_action is not None and obj.animation_data:
        try:
            obj.animation_data.action = active_action
        except (AttributeError, TypeError, RuntimeError):
            pass

    for layer_state in layer_states:
        item = obj.Anim_Layers.add()
        for f in _LAYER_FIELDS:
            if f in layer_state and hasattr(item, f):
                try:
                    setattr(item, f, layer_state[f])
                except (AttributeError, TypeError):
                    pass
        action = layer_state.get("_action_copy")
        if action is not None:
            try:
                item.action = action
            except (AttributeError, TypeError):
                pass

    # Restore each strip's influence to match the snapshotted per-layer value.
    #
    # Three constraints to satisfy simultaneously:
    #  1. Pose must come back correctly. An empty animated influence fcurve
    #     evaluates to 0 → T-pose, so we can't just leave the fcurve empty.
    #  2. A subsequent merge from the AL UI must not crash. AL's `smart_bake()`
    #     uses `for strip_fcu in strip.fcurves: strip_keyframes = ...` and then
    #     references `strip_keyframes` after the loop. If `strip.fcurves` is
    #     empty (i.e. `use_animated_influence=False`), `strip_keyframes` is
    #     never bound and AL raises UnboundLocalError on the next merge. So
    #     `strip.fcurves` must contain the influence fcurve.
    #  3. No visible keyframe should appear on the influence slider — the user
    #     does not want post-export animation data they didn't author.
    #
    # Solution: enable animated_influence (creates the fcurve, satisfies #2),
    # clear the auto-keyframe Blender inserts (satisfies #3), and *mute* the
    # fcurve so Blender's NLA evaluator falls back to the static `strip.influence`
    # value (satisfies #1). AL's smart_bake skips muted fcurves but still binds
    # the loop variable — `not strip_fcu.mute` is checked inside the comprehension,
    # so the loop body still runs and assigns `strip_keyframes`.
    if obj.animation_data:
        for i, track in enumerate(obj.animation_data.nla_tracks):
            if not track.strips:
                continue
            target_influence = (
                layer_states[i].get("influence", 1.0) if i < len(layer_states) else 1.0
            )
            for strip in track.strips:
                try:
                    strip.influence = target_influence
                    strip.use_animated_influence = True
                    if strip.fcurves:
                        try:
                            strip.fcurves[0].keyframe_points.clear()
                        except (AttributeError, RuntimeError):
                            pass
                        try:
                            strip.fcurves[0].mute = True
                        except (AttributeError, TypeError):
                            pass
                    strip.influence = target_influence
                except (AttributeError, TypeError, RuntimeError):
                    pass

    # Restore als fields via ID-property dict access to BYPASS AL's update
    # callbacks. AL has aggressive cross-cutting callbacks — `auto_rename`
    # renames layers/actions to match `anim_data.action.name` based on the
    # *current* layer_index (which hasn't been restored yet at that moment),
    # and `data_type_update` calls `register_layers` and resets layer_index
    # to 0. Setting via setattr fires those callbacks and corrupts the layer
    # we just rebuilt. Direct dict access stores the value without triggering
    # the update callback, leaving AL's state intact.
    saved_layer_index = state["als"].get("layer_index")
    for f, v in state["als"].items():
        if f == "layer_index":
            continue
        if not hasattr(obj.als, f):
            continue
        try:
            obj.als[f] = v
        except (KeyError, TypeError):
            try:
                setattr(obj.als, f, v)
            except (AttributeError, TypeError):
                pass

    # Layer_index goes through the proper setter — its callback (`update_layer_index`)
    # is the one we *want* to fire, so the active layer's strip becomes selected
    # and the rig re-enters the correct tweak mode for the user.
    if saved_layer_index is not None and 0 <= saved_layer_index < len(obj.Anim_Layers):
        try:
            obj.als.layer_index = saved_layer_index
        except (AttributeError, TypeError):
            pass
