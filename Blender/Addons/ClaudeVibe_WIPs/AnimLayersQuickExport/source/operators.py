import os

import bpy
from bpy.types import Operator

from . import al_bridge


def _apply_prefix_suffix(props, base):
    return f"{props.filename_prefix}{base}{props.filename_suffix}"


def _pick_layer_for_name(obj, props):
    """Return the AnimLayersItem whose action name should drive the filename."""
    layers = getattr(obj, "Anim_Layers", None)
    if not layers:
        return None
    if props.filename_layer_source == "BASE":
        return layers[0]
    idx = max(0, min(obj.als.layer_index, len(layers) - 1))
    return layers[idx]


def _resolve_merged_filename_base(obj, props):
    if props.filename_source == "ACTION":
        layer = _pick_layer_for_name(obj, props)
        if layer is not None and layer.action is not None:
            base = layer.action.name
        else:
            anim = getattr(obj, "animation_data", None)
            action = anim.action if anim else None
            base = action.name if action is not None else obj.name
    elif props.filename_source == "ARMATURE":
        base = obj.name
    else:
        base = props.custom_filename or obj.name
    return _apply_prefix_suffix(props, base)


def _resolve_per_layer_filename_base(armature, layer, props):
    if props.filename_source == "ACTION":
        base = layer.action.name if layer.action else (layer.name or armature.name)
    elif props.filename_source == "ARMATURE":
        base = f"{armature.name}_{layer.name or 'layer'}"
    else:
        base = f"{props.custom_filename or armature.name}_{layer.name or 'layer'}"
    return _apply_prefix_suffix(props, base)


def _resolve_armatures(context, props):
    obj = context.active_object
    if props.scope == "SELECTED_ARMATURES":
        return [
            o for o in context.selected_objects
            if o.type == "ARMATURE" and al_bridge.has_animation_layers(o)
        ]
    if obj is None or obj.type != "ARMATURE":
        return []
    return [obj]


def _resolve_export_objects(context, props):
    armatures = _resolve_armatures(context, props)
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
        "bake_anim": True,
        "bake_anim_use_all_bones": props.bake_anim_use_all_bones,
        "bake_anim_use_nla_strips": props.bake_anim_use_nla_strips,
        "bake_anim_use_all_actions": props.bake_anim_use_all_actions,
        "bake_anim_force_startend_keying": props.bake_anim_force_startend_keying,
        "bake_anim_step": props.bake_anim_step,
        "bake_anim_simplify_factor": props.bake_anim_simplify_factor,
        "add_leaf_bones": props.add_leaf_bones,
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


class ALQE_OT_quick_export(Operator):
    bl_idname = "alqe.quick_export"
    bl_label = "Quick Export Animation"
    bl_description = (
        "Export the active armature's Animation Layers to FBX. "
        "Merged mode bakes the whole stack into one file; Per Layer exports each layer as its own FBX. "
        "Either way the layer stack is restored after export"
    )
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return (
            al_bridge.is_animation_layers_available()
            and obj is not None
            and obj.type == "ARMATURE"
            and al_bridge.has_animation_layers(obj)
        )

    def execute(self, context):
        props = context.scene.alqe_props

        armatures_to_merge = _resolve_armatures(context, props)
        if not armatures_to_merge:
            self.report({"ERROR"}, "No armature with Animation Layers found in scope")
            return {"CANCELLED"}

        export_objects = _resolve_export_objects(context, props)
        if not export_objects:
            self.report({"ERROR"}, "Nothing to export")
            return {"CANCELLED"}

        try:
            export_dir = _ensure_export_dir(props.export_path)
        except OSError as exc:
            self.report({"ERROR"}, f"Could not create export folder: {exc}")
            return {"CANCELLED"}

        # Resolve the merged filename BEFORE the merge runs — once the merge
        # has rewritten the active action, we lose access to the original
        # active/base layer's action name.
        merged_filename_base = _resolve_merged_filename_base(armatures_to_merge[0], props)

        snapshots = {arm.name: al_bridge.snapshot_state(arm) for arm in armatures_to_merge}
        saved_active = context.view_layer.objects.active
        saved_selection = list(context.selected_objects)
        saved_mode = saved_active.mode if saved_active is not None else "OBJECT"

        bpy.ops.ed.undo_push(message="ALQE: Quick Export")

        try:
            if props.export_mode == "PER_LAYER":
                summary = self._export_per_layer(
                    context, props, armatures_to_merge, export_objects, export_dir,
                )
            else:
                summary = self._export_merged(
                    context, props, armatures_to_merge, export_objects, export_dir,
                    merged_filename_base,
                )
        except Exception as exc:
            self.report({"ERROR"}, f"Quick export failed: {exc}")
            return self._restore_and_return(snapshots, saved_active, saved_selection, saved_mode, "CANCELLED")

        return self._restore_and_return(
            snapshots, saved_active, saved_selection, saved_mode, "FINISHED",
            success_message=summary,
        )

    def _export_merged(self, context, props, armatures, export_objects, export_dir, filename_base):
        merged_layer_total = 0
        for armature in armatures:
            merged_layer_total += al_bridge.get_layer_count(armature)
            context.view_layer.objects.active = armature
            al_bridge.merge_all_layers(
                armature,
                baketype="AL",
                smartbake=props.smartbake,
                step=props.bake_step,
                actioncopy=True,
            )

        _set_selection(context, export_objects, active=armatures[0])

        filepath = os.path.join(export_dir, f"{filename_base}.fbx")
        with _scene_named_as(context.scene, filename_base):
            bpy.ops.export_scene.fbx(**_build_fbx_kwargs(props, filepath))
        return f"Exported {os.path.basename(filepath)} ({len(armatures)} armature(s), {merged_layer_total} layers merged)"

    def _export_per_layer(self, context, props, armatures, export_objects, export_dir):
        _set_selection(context, export_objects, active=armatures[0])

        files_written = 0
        seen_paths = set()

        for armature in armatures:
            context.view_layer.objects.active = armature
            n_layers = al_bridge.get_layer_count(armature)
            for layer_index in range(n_layers):
                layer = armature.Anim_Layers[layer_index]
                if layer.action is None:
                    continue
                try:
                    armature.als.layer_index = layer_index
                except (AttributeError, TypeError):
                    pass

                filename = _resolve_per_layer_filename_base(armature, layer, props)
                filepath = os.path.join(export_dir, f"{filename}.fbx")
                if filepath in seen_paths:
                    filepath = os.path.join(export_dir, f"{filename}_{layer_index}.fbx")
                seen_paths.add(filepath)

                with _scene_named_as(context.scene, filename):
                    bpy.ops.export_scene.fbx(**_build_fbx_kwargs(props, filepath, force_active_action=True))
                files_written += 1

        return f"Exported {files_written} layer file(s) to {export_dir}"

    def _restore_and_return(self, snapshots, saved_active, saved_selection, saved_mode, retval, success_message=None):
        for name, snapshot in snapshots.items():
            arm = bpy.data.objects.get(name)
            if arm is not None:
                al_bridge.restore_state(arm, snapshot)

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

        if success_message:
            self.report({"INFO"}, success_message)

        return {retval}


classes = (ALQE_OT_quick_export,)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
