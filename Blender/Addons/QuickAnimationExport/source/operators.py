import os

import bpy
from bpy.types import Operator

from . import al_bridge


# ---- Filename / scope helpers ----------------------------------------------

def _apply_prefix_suffix(props, base):
    return f"{props.filename_prefix}{base}{props.filename_suffix}"


def _pick_layer_for_name(obj, props):
    return _pick_layer_by_source(obj, props.filename_layer_source)


def _pick_clip_layer_for_name(obj, props):
    return _pick_layer_by_source(obj, props.clip_layer_source)


def _pick_layer_by_source(obj, source):
    layers = getattr(obj, "Anim_Layers", None)
    if not layers:
        return None
    if source == "BASE":
        return layers[0]
    idx = max(0, min(obj.als.layer_index, len(layers) - 1))
    return layers[idx]


def _merged_filename_basename(obj, props, *, has_al):
    """Inner base of the merged-mode filename, before filename prefix/suffix.

    Exposed so the clip-name resolver can re-use the same source picker
    (e.g. SAME_AS_FILENAME → use 'idleLayered', not 'anim_idleLayered').
    """
    if props.filename_source == "ACTION":
        if has_al:
            # With Animation Layers active, prefer the layer's *display name*.
            # The layer name is what the user sees and edits in the AL list and
            # it's stable across action renames / reassignments (which the user
            # rarely tracks). The underlying `layer.action.name` is decoupled
            # and often surprises (e.g. an action named "idle" attached to a
            # layer renamed "Base Layer" produced "idle.fbx" — confusing).
            layer = _pick_layer_for_name(obj, props)
            if layer is not None and (layer.name or layer.action is not None):
                return layer.name or layer.action.name
            return _active_action_name(obj) or obj.name
        return _active_action_name(obj) or obj.name
    if props.filename_source == "ARMATURE":
        return obj.name
    return props.custom_filename or obj.name


def _resolve_merged_filename_base(obj, props, *, has_al):
    return _apply_prefix_suffix(props, _merged_filename_basename(obj, props, has_al=has_al))


def _per_layer_filename_basename(armature, layer, props):
    if props.filename_source == "ACTION":
        # Same rationale as _merged_filename_basename — prefer the layer's
        # display name when it's set; fall back to the action name only if not.
        return layer.name or (layer.action.name if layer.action else armature.name)
    if props.filename_source == "ARMATURE":
        return f"{armature.name}_{layer.name or 'layer'}"
    return f"{props.custom_filename or armature.name}_{layer.name or 'layer'}"


def _resolve_per_layer_filename_base(armature, layer, props):
    return _apply_prefix_suffix(props, _per_layer_filename_basename(armature, layer, props))


def _active_action_name(obj):
    anim = getattr(obj, "animation_data", None)
    action = anim.action if anim else None
    return action.name if action is not None else None


# ---- Clip name (FBX AnimStack label) ---------------------------------------
#
# The clip name is what an engine like Unity/Unreal sees when it imports the
# FBX. Historically the addon set it to the filename via _scene_named_as. The
# user wanted independent control: e.g. file `human_idle.fbx` containing a
# clip named `00_BasePose` for an Animation Layers project.

def _format_layer_token(layer_index, layer, props, *, prepend_separator):
    """Build the layer-discriminator token (e.g. '_00_BasePose').

    `prepend_separator` controls whether to add a leading separator. We skip
    it when the base name is empty so the user can put their convention
    entirely in the prefix (e.g. prefix='animclip_human_', base='', token
    starts with '00_BasePose' → no double underscore).
    """
    token_kind = props.clip_layer_token
    if token_kind == "NONE":
        return ""

    sep = props.clip_index_separator or "_"
    pad = max(0, props.clip_index_padding)
    idx_str = f"{layer_index:0{pad}d}" if pad else str(layer_index)
    name_str = layer.name if (layer is not None and getattr(layer, "name", "")) else ""
    leading = sep if prepend_separator else ""

    if token_kind == "LAYER_NAME":
        return f"{leading}{name_str}" if name_str else ""
    if token_kind == "LAYER_INDEX":
        return f"{leading}{idx_str}"
    if token_kind == "INDEX_NAME":
        if name_str:
            return f"{leading}{idx_str}{sep}{name_str}"
        return f"{leading}{idx_str}"
    if token_kind == "NAME_INDEX":
        if name_str:
            return f"{leading}{name_str}{sep}{idx_str}"
        return f"{leading}{idx_str}"
    return ""


def _resolve_clip_name(armature, layer, layer_index, props, *, has_al, fallback_basename, multi_clip):
    """Resolve the AnimStack name for one clip.

    `layer` is the AL layer object (or None outside of an AL context).
    `layer_index` is its position in the stack (0 for non-AL contexts).
    `fallback_basename` is the filename's INNER base name (before filename
    prefix/suffix), used when clip_name_source is SAME_AS_FILENAME. The clip
    still gets its own clip_prefix / clip_suffix / layer-token applied on top
    of that base — that's what lets the user ship `anim_idleLayered.fbx`
    containing clips named `animClip_idleLayered_Base_Layer`.
    `multi_clip` indicates whether we're emitting one of several clips in this
    file (per-layer modes) vs a single clip (merged / vanilla). When it's
    False AND the source is ACTION, the layer token is suppressed because the
    base already encodes the layer — appending it again would be redundant.
    """
    source = props.clip_name_source

    if source == "SAME_AS_FILENAME":
        base = fallback_basename or ""
    elif source == "ACTION":
        if has_al and layer is not None:
            base = layer.name or (layer.action.name if getattr(layer, "action", None) else armature.name)
        else:
            base = _active_action_name(armature) or armature.name
    elif source == "ARMATURE":
        base = armature.name
    else:  # CUSTOM
        base = props.clip_custom_name or ""

    if source == "ACTION" and not multi_clip:
        token = ""
    else:
        token = _format_layer_token(layer_index, layer, props, prepend_separator=bool(base))
    return f"{props.clip_prefix}{base}{token}{props.clip_suffix}"


def _strip_for_layer(armature, layer_index):
    """Return the NLA strip Animation Layers uses to drive this layer, or None.

    AL pairs each `Anim_Layers[i]` with `nla_tracks[i]`, each of which has a
    single strip. The strip's `name` is what the FBX exporter writes as the
    AnimStack label when `bake_anim_use_nla_strips=True`.
    """
    anim = armature.animation_data
    if anim is None or layer_index >= len(anim.nla_tracks):
        return None
    track = anim.nla_tracks[layer_index]
    if not track.strips:
        return None
    return track.strips[0]


def _resolve_armatures(context, props, *, require_layers):
    obj = context.active_object
    if props.scope == "SELECTED_ARMATURES":
        candidates = [o for o in context.selected_objects if o.type == "ARMATURE"]
    elif obj is not None and obj.type == "ARMATURE":
        candidates = [obj]
    else:
        candidates = []
    if require_layers:
        candidates = [o for o in candidates if al_bridge.has_animation_layers(o)]
    return candidates


def _resolve_export_objects(context, props, armatures):
    if not armatures:
        return []
    if props.scope == "ACTIVE_ONLY":
        return list(armatures)
    objects = set(armatures)
    for arm in armatures:
        for child in arm.children_recursive:
            objects.add(child)
    return list(objects)


def _build_fbx_kwargs(props, filepath, *, force_active_action=False):
    kwargs = {
        "filepath": filepath,
        "use_selection": True,
        "object_types": {"ARMATURE", "MESH", "EMPTY"},
        "bake_anim": props.bake_anim,
        "bake_anim_use_all_bones": props.bake_anim_use_all_bones,
        "bake_anim_use_nla_strips": props.bake_anim_use_nla_strips,
        "bake_anim_use_all_actions": props.bake_anim_use_all_actions,
        "bake_anim_force_startend_keying": props.bake_anim_force_startend_keying,
        "bake_anim_step": props.bake_anim_step,
        "bake_anim_simplify_factor": props.bake_anim_simplify_factor,
        "add_leaf_bones": props.add_leaf_bones,
        "use_armature_deform_only": props.use_armature_deform_only,
        "primary_bone_axis": props.primary_bone_axis,
        "secondary_bone_axis": props.secondary_bone_axis,
        "armature_nodetype": props.armature_nodetype,
        "apply_unit_scale": props.apply_unit_scale,
        "apply_scale_options": props.apply_scale_options,
        "bake_space_transform": props.bake_space_transform,
        "axis_forward": props.axis_forward,
        "axis_up": props.axis_up,
        "path_mode": props.path_mode,
    }
    if force_active_action:
        # Per-layer mode: bake only the active action, ignore NLA stack and other actions.
        kwargs["bake_anim_use_nla_strips"] = False
        kwargs["bake_anim_use_all_actions"] = False
    return kwargs


def _ensure_export_dir(path):
    abs_path = bpy.path.abspath(path)
    os.makedirs(abs_path, exist_ok=True)
    return abs_path


def _ensure_object_mode(context):
    """Force the active object out of pose / edit mode.

    Animation Layers' merge leaves armatures in pose mode, which makes operators
    like `object.select_all` and `export_scene.fbx` fail their poll() checks.
    """
    active = context.view_layer.objects.active
    if active is None:
        return
    try:
        if active.mode != "OBJECT":
            bpy.ops.object.mode_set(mode="OBJECT")
    except RuntimeError:
        pass


class _scene_named_as:
    """Context manager that temporarily renames the scene.

    Blender's FBX exporter labels the AnimStack (= Unity animation clip name)
    after `scene.name` unless `bake_anim_use_all_actions=True` or NLA strips
    are used. Renaming the scene to the desired clip name during export gives
    us a predictable label without disturbing actions or NLA tracks.
    """

    def __init__(self, scene, new_name):
        self.scene = scene
        self.new_name = new_name
        self._saved_name = None

    def __enter__(self):
        self._saved_name = self.scene.name
        try:
            self.scene.name = self.new_name
        except (AttributeError, RuntimeError):
            pass
        return self.scene

    def __exit__(self, exc_type, exc, tb):
        try:
            self.scene.name = self._saved_name
        except (AttributeError, RuntimeError):
            pass
        return False


def _set_selection(context, objects, *, active=None):
    """Select exactly the given objects without going through bpy.ops.

    Direct API selection (`obj.select_set(...)`) works in any mode, while
    `bpy.ops.object.select_all` requires Object mode and a 3D View context.
    """
    _ensure_object_mode(context)
    for obj in context.view_layer.objects:
        try:
            obj.select_set(False)
        except (ReferenceError, RuntimeError):
            pass
    for obj in objects:
        try:
            obj.select_set(True)
        except (ReferenceError, RuntimeError):
            pass
    if active is not None:
        try:
            context.view_layer.objects.active = active
        except (ReferenceError, RuntimeError):
            pass


# ---- Operator --------------------------------------------------------------

class QAE_OT_quick_export(Operator):
    bl_idname = "qae.quick_export"
    bl_label = "Quick Export Animation"
    bl_description = (
        "Export the active armature (and its hierarchy) to FBX. With Animation Layers enabled, "
        "Merged mode bakes the whole stack into one file and Per Layer exports each layer as "
        "its own FBX. The layer stack is always restored after export"
    )
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return obj is not None and obj.type == "ARMATURE"

    def execute(self, context):
        props = context.scene.qae_props

        try:
            export_dir = _ensure_export_dir(props.export_path)
        except OSError as exc:
            self.report({"ERROR"}, f"Could not create export folder: {exc}")
            return {"CANCELLED"}

        al_active = al_bridge.is_animation_layers_enabled()

        # AL-aware path: only fires if AL is enabled AND the rig has layers.
        armatures_with_layers = (
            _resolve_armatures(context, props, require_layers=True) if al_active else []
        )

        if armatures_with_layers:
            return self._execute_with_al(context, props, armatures_with_layers, export_dir)
        return self._execute_vanilla(context, props, export_dir)

    # ---- Vanilla path ------------------------------------------------------

    def _execute_vanilla(self, context, props, export_dir):
        armatures = _resolve_armatures(context, props, require_layers=False)
        if not armatures:
            self.report({"ERROR"}, "No armature in scope")
            return {"CANCELLED"}

        export_objects = _resolve_export_objects(context, props, armatures)
        saved_active = context.view_layer.objects.active
        saved_selection = list(context.selected_objects)
        saved_mode = saved_active.mode if saved_active is not None else "OBJECT"

        filename_basename = _merged_filename_basename(armatures[0], props, has_al=False)
        filename_base = _apply_prefix_suffix(props, filename_basename)
        filepath = os.path.join(export_dir, f"{filename_base}.fbx")
        clip_name = _resolve_clip_name(
            armatures[0], None, 0, props, has_al=False,
            fallback_basename=filename_basename, multi_clip=False,
        )

        _set_selection(context, export_objects, active=armatures[0])

        try:
            with _scene_named_as(context.scene, clip_name):
                bpy.ops.export_scene.fbx(**_build_fbx_kwargs(props, filepath))
        except Exception as exc:
            self._restore_selection(saved_active, saved_selection, saved_mode)
            self.report({"ERROR"}, f"FBX export failed: {exc}")
            return {"CANCELLED"}

        self._restore_selection(saved_active, saved_selection, saved_mode)
        self.report(
            {"INFO"},
            f"Exported {os.path.basename(filepath)} (vanilla mode, {len(armatures)} armature(s))",
        )
        return {"FINISHED"}

    # ---- AL path -----------------------------------------------------------

    def _execute_with_al(self, context, props, armatures, export_dir):
        export_objects = _resolve_export_objects(context, props, armatures)
        if not export_objects:
            self.report({"ERROR"}, "Nothing to export")
            return {"CANCELLED"}

        # Resolve merged filename BEFORE the merge runs — once the merge has
        # rewritten/renamed the active layer's action we lose access to the
        # original active/base layer's action name.
        merged_filename_basename = _merged_filename_basename(armatures[0], props, has_al=True)
        merged_filename_base = _apply_prefix_suffix(props, merged_filename_basename)

        snapshots = {arm.name: al_bridge.snapshot_state(arm) for arm in armatures}
        saved_active = context.view_layer.objects.active
        saved_selection = list(context.selected_objects)
        saved_mode = saved_active.mode if saved_active is not None else "OBJECT"

        bpy.ops.ed.undo_push(message="QAE: Quick Export")

        try:
            if props.export_mode == "PER_LAYER":
                if props.bundle_per_layer:
                    summary = self._export_per_layer_bundled(
                        context, props, armatures, export_objects, export_dir,
                        merged_filename_base, merged_filename_basename,
                    )
                else:
                    summary = self._export_per_layer(context, props, armatures, export_objects, export_dir)
            else:
                summary = self._export_merged(
                    context, props, armatures, export_objects, export_dir,
                    merged_filename_base, merged_filename_basename,
                )
        except Exception as exc:
            self.report({"ERROR"}, f"Quick export failed: {exc}")
            return self._restore_and_return(snapshots, saved_active, saved_selection, saved_mode, "CANCELLED")

        return self._restore_and_return(
            snapshots, saved_active, saved_selection, saved_mode, "FINISHED",
            success_message=summary,
        )

    def _export_merged(self, context, props, armatures, export_objects, export_dir, filename_base, filename_basename):
        # Capture the layer used for clip naming BEFORE the merge collapses
        # the stack — once AL has merged everything down, "active layer"
        # loses meaning and any clip-name source pointing at it would resolve
        # to the merged result. The clip respects its own ACTIVE/BASE picker
        # (clip_layer_source), independent from the filename's picker.
        primary = armatures[0]
        clip_layer, clip_layer_index = self._clip_layer(primary, props)

        merged_layer_total = 0
        for armature in armatures:
            merged_layer_total += al_bridge.get_layer_count(armature)
            context.view_layer.objects.active = armature
            al_bridge.merge_all_layers(armature, props=props)

        _set_selection(context, export_objects, active=primary)

        filepath = os.path.join(export_dir, f"{filename_base}.fbx")
        clip_name = _resolve_clip_name(
            primary, clip_layer, clip_layer_index, props, has_al=True,
            fallback_basename=filename_basename, multi_clip=False,
        )
        with _scene_named_as(context.scene, clip_name):
            bpy.ops.export_scene.fbx(**_build_fbx_kwargs(props, filepath))
        return f"Exported {os.path.basename(filepath)} ({len(armatures)} armature(s), {merged_layer_total} layers merged)"

    def _export_per_layer(self, context, props, armatures, export_objects, export_dir):
        _set_selection(context, export_objects, active=armatures[0])

        files_written = 0
        skipped_muted = 0
        seen_paths = set()

        for armature in armatures:
            context.view_layer.objects.active = armature
            n_layers = al_bridge.get_layer_count(armature)
            for layer_index in range(n_layers):
                layer = armature.Anim_Layers[layer_index]
                if layer.action is None:
                    continue
                if props.per_layer_only_visible and getattr(layer, "mute", False):
                    skipped_muted += 1
                    continue
                try:
                    armature.als.layer_index = layer_index
                except (AttributeError, TypeError):
                    pass

                filename_basename = _per_layer_filename_basename(armature, layer, props)
                filename = _apply_prefix_suffix(props, filename_basename)
                filepath = os.path.join(export_dir, f"{filename}.fbx")
                if filepath in seen_paths:
                    filepath = os.path.join(export_dir, f"{filename}_{layer_index}.fbx")
                seen_paths.add(filepath)

                clip_name = _resolve_clip_name(
                    armature, layer, layer_index, props, has_al=True,
                    fallback_basename=filename_basename, multi_clip=True,
                )
                with _scene_named_as(context.scene, clip_name):
                    bpy.ops.export_scene.fbx(**_build_fbx_kwargs(props, filepath, force_active_action=True))
                files_written += 1

        suffix = f", skipped {skipped_muted} muted" if skipped_muted else ""
        return f"Exported {files_written} layer file(s) to {export_dir}{suffix}"

    def _export_per_layer_bundled(self, context, props, armatures, export_objects, export_dir, filename_base, filename_basename):
        """All AL layers as separate clips inside a single FBX.

        Strategy: rename each layer's NLA strip to its target clip name and
        let the FBX exporter's `bake_anim_use_nla_strips=True` mode emit one
        AnimStack per non-muted strip. Strip mutes flow from the layer mute
        state when `per_layer_only_visible` is on. Cleanup is handled by the
        snapshot/restore wrapping in `_execute_with_al`.
        """
        _set_selection(context, export_objects, active=armatures[0])

        clips_named = 0
        clips_muted = 0
        for armature in armatures:
            n_layers = al_bridge.get_layer_count(armature)
            for layer_index in range(n_layers):
                layer = armature.Anim_Layers[layer_index]
                strip = _strip_for_layer(armature, layer_index)
                if strip is None:
                    continue
                hide = props.per_layer_only_visible and getattr(layer, "mute", False)
                clip_name = _resolve_clip_name(
                    armature, layer, layer_index, props, has_al=True,
                    fallback_basename=filename_basename, multi_clip=True,
                )
                try:
                    strip.name = clip_name
                except (AttributeError, TypeError):
                    pass
                if hide:
                    try:
                        strip.mute = True
                        clips_muted += 1
                    except (AttributeError, TypeError):
                        pass
                else:
                    clips_named += 1

        filepath = os.path.join(export_dir, f"{filename_base}.fbx")
        kwargs = _build_fbx_kwargs(props, filepath)
        # NLA-strip mode is what makes Blender emit one AnimStack per strip;
        # all-actions mode would clash with it, so explicitly disable.
        kwargs["bake_anim_use_nla_strips"] = True
        kwargs["bake_anim_use_all_actions"] = False
        with _scene_named_as(context.scene, filename_base):
            bpy.ops.export_scene.fbx(**kwargs)

        skipped = f", skipped {clips_muted} muted" if clips_muted else ""
        return (
            f"Exported {os.path.basename(filepath)} with {clips_named} clip(s){skipped}"
        )

    @staticmethod
    def _active_layer(armature):
        layers = getattr(armature, "Anim_Layers", None)
        if not layers:
            return None, 0
        idx = max(0, min(getattr(armature.als, "layer_index", 0), len(layers) - 1))
        return layers[idx], idx

    @staticmethod
    def _clip_layer(armature, props):
        """Return (layer, index) used for clip naming under clip_layer_source."""
        layers = getattr(armature, "Anim_Layers", None)
        if not layers:
            return None, 0
        if props.clip_layer_source == "BASE":
            return layers[0], 0
        idx = max(0, min(getattr(armature.als, "layer_index", 0), len(layers) - 1))
        return layers[idx], idx

    # ---- Restoration -------------------------------------------------------

    def _restore_selection(self, saved_active, saved_selection, saved_mode):
        try:
            _set_selection(
                bpy.context,
                [o for o in saved_selection if o.name in bpy.data.objects],
                active=saved_active if saved_active is not None and saved_active.name in bpy.data.objects else None,
            )
            if saved_mode and saved_mode != "OBJECT":
                try:
                    bpy.ops.object.mode_set(mode=saved_mode)
                except RuntimeError:
                    pass
        except (ReferenceError, RuntimeError):
            pass

    def _restore_and_return(self, snapshots, saved_active, saved_selection, saved_mode, retval, success_message=None):
        for name, snapshot in snapshots.items():
            arm = bpy.data.objects.get(name)
            if arm is not None:
                al_bridge.restore_state(arm, snapshot)

        self._restore_selection(saved_active, saved_selection, saved_mode)

        if success_message:
            self.report({"INFO"}, success_message)

        return {retval}


classes = (QAE_OT_quick_export,)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
