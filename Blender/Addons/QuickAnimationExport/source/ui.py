import os

import bpy
import bpy.utils.previews
from bpy.types import Panel

from . import al_bridge


# Custom composite icon: sine wave flowing into an export arrow head. Loaded
# once at register() and used via `icon_value=` on the header button.
_PREVIEW_COLLECTION = None
_ICON_DIR = os.path.join(os.path.dirname(__file__), "icons")


def _qae_icon_id():
    if _PREVIEW_COLLECTION is None:
        return 0
    entry = _PREVIEW_COLLECTION.get("anim_export")
    return entry.icon_id if entry is not None else 0


def _draw_viewport_header_quick_export(self, context):
    obj = context.active_object
    layout = self.layout
    row = layout.row(align=True)
    row.separator()
    sub = row.row(align=True)
    sub.enabled = obj is not None and obj.type == "ARMATURE"
    icon_id = _qae_icon_id()
    if icon_id:
        sub.operator("qae.quick_export", text="", icon_value=icon_id)
    else:
        # Fallback to a built-in icon if the preview failed to load (e.g. on a
        # platform where the PNG isn't readable). No silent failure for the user.
        sub.operator("qae.quick_export", text="", icon="ARMATURE_DATA")


def _al_status(obj):
    """Return (icon, message, has_layers_on_active) for the panel status box."""
    installed = al_bridge.is_animation_layers_installed()
    enabled = al_bridge.is_animation_layers_enabled()
    has_layers = obj is not None and obj.type == "ARMATURE" and al_bridge.has_animation_layers(obj)

    if not installed:
        return "INFO", "Animation Layers not detected — vanilla FBX export only", False
    if not enabled:
        return "ERROR", "Animation Layers installed but turned off — enable in Preferences", False
    if not has_layers:
        return "INFO", "Animation Layers active — this rig has no layers (vanilla export)", False
    return "CHECKMARK", "Animation Layers detected — bake/merge available", True


class QAE_PT_quick_export(Panel):
    bl_label = "Quick Animation Export"
    bl_idname = "QAE_PT_quick_export"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Animation"
    bl_options = {"DEFAULT_CLOSED"}

    def draw(self, context):
        layout = self.layout
        props = context.scene.qae_props
        obj = context.active_object

        # Status — always visible so the user can see whether the AL bridge is live.
        icon, msg, has_layers = _al_status(obj)
        status_box = layout.box()
        status_box.label(text=msg, icon=icon)

        layout.separator()

        # Output
        col = layout.column(align=True)
        col.prop(props, "export_path")

        if has_layers:
            layout.prop(props, "export_mode", expand=True)
            if props.export_mode == "PER_LAYER":
                # Sub-toggles only meaningful in PER_LAYER + AL.
                pl_box = layout.box()
                pl_box.label(text="Per-Layer Options", icon="NLA")
                pl_box.prop(props, "bundle_per_layer")
                pl_box.prop(props, "per_layer_only_visible")
                if props.bundle_per_layer:
                    pl_box.label(
                        text="Single FBX, one clip per layer (NLA-strip bake)",
                        icon="INFO",
                    )

        # Filename
        fn_box = layout.box()
        fn_box.label(text="Filename")
        fn_box.prop(props, "filename_source", text="Source")
        if props.filename_source == "CUSTOM":
            fn_box.prop(props, "custom_filename", text="Name")
        if has_layers and props.filename_source == "ACTION" and props.export_mode == "MERGED":
            fn_box.prop(props, "filename_layer_source", expand=True)
        row = fn_box.row(align=True)
        row.prop(props, "filename_prefix")
        row.prop(props, "filename_suffix")
        if has_layers and props.export_mode == "PER_LAYER" and not props.bundle_per_layer:
            fn_box.label(text="Per Layer: filename gets the layer/action name", icon="INFO")

        # Clip Name (FBX AnimStack label)
        clip_box = layout.box()
        clip_box.prop(
            props, "show_clip_settings",
            icon="TRIA_DOWN" if props.show_clip_settings else "TRIA_RIGHT",
            emboss=False, text="Clip Name (in FBX)",
        )
        if props.show_clip_settings:
            self._draw_clip_settings(clip_box, props, has_layers)

        layout.prop(props, "scope")

        # AL bake/merge — full mirror of AL's merge dialog.
        if has_layers:
            bake_box = layout.box()
            bake_box.prop(
                props, "show_bake_settings",
                icon="TRIA_DOWN" if props.show_bake_settings else "TRIA_RIGHT",
                emboss=False, text="Bake / Merge (Animation Layers)",
            )
            if props.show_bake_settings:
                self._draw_bake_settings(bake_box, props, obj)

        # FBX (animation)
        anim_box = layout.box()
        anim_box.prop(
            props, "show_fbx_animation_settings",
            icon="TRIA_DOWN" if props.show_fbx_animation_settings else "TRIA_RIGHT",
            emboss=False, text="FBX Animation",
        )
        if props.show_fbx_animation_settings:
            anim_box.prop(props, "bake_anim")
            sub = anim_box.column(align=True)
            sub.enabled = props.bake_anim
            sub.prop(props, "bake_anim_use_all_bones")
            sub.prop(props, "bake_anim_use_nla_strips")
            sub.prop(props, "bake_anim_use_all_actions")
            sub.prop(props, "bake_anim_force_startend_keying")
            sub.prop(props, "bake_anim_step")
            sub.prop(props, "bake_anim_simplify_factor")

        # FBX (armature)
        arm_box = layout.box()
        arm_box.prop(
            props, "show_fbx_armature_settings",
            icon="TRIA_DOWN" if props.show_fbx_armature_settings else "TRIA_RIGHT",
            emboss=False, text="FBX Armature",
        )
        if props.show_fbx_armature_settings:
            arm_box.prop(props, "use_armature_deform_only")
            arm_box.prop(props, "add_leaf_bones")
            arm_box.prop(props, "primary_bone_axis")
            arm_box.prop(props, "secondary_bone_axis")
            arm_box.prop(props, "armature_nodetype")

        # FBX (general)
        gen_box = layout.box()
        gen_box.prop(
            props, "show_fbx_general_settings",
            icon="TRIA_DOWN" if props.show_fbx_general_settings else "TRIA_RIGHT",
            emboss=False, text="FBX General",
        )
        if props.show_fbx_general_settings:
            gen_box.prop(props, "apply_unit_scale")
            gen_box.prop(props, "apply_scale_options")
            gen_box.prop(props, "bake_space_transform")
            gen_box.prop(props, "axis_forward")
            gen_box.prop(props, "axis_up")
            gen_box.prop(props, "path_mode")

        layout.separator()
        layout.operator("qae.quick_export", icon="EXPORT")

    def _draw_clip_settings(self, box, props, has_layers):
        col = box.column(align=True)
        col.prop(props, "clip_name_source", text="Source")

        is_per_layer_context = has_layers and props.export_mode == "PER_LAYER"
        is_action_single_clip = (
            props.clip_name_source == "ACTION" and not is_per_layer_context
        )

        if props.clip_name_source == "SAME_AS_FILENAME":
            col.label(
                text="Base = filename (without filename prefix/suffix)",
                icon="INFO",
            )
        elif props.clip_name_source == "CUSTOM":
            col.prop(props, "clip_custom_name", text="Name")
        elif props.clip_name_source == "ACTION" and has_layers and props.export_mode == "MERGED":
            # Mirror of the filename's ACTIVE/BASE picker, scoped to the clip.
            col.prop(props, "clip_layer_source", expand=True)

        # Prefix / suffix / token are always available — they layer on top of
        # whichever base the source produces. This is what lets the user ship
        # `anim_idleLayered.fbx` with clips named `animClip_idleLayered_<layer>`.
        row = col.row(align=True)
        row.prop(props, "clip_prefix")
        row.prop(props, "clip_suffix")

        # Layer token is only meaningful in multi-clip contexts (per-layer
        # exports) or when the base doesn't already encode the layer. With
        # source=ACTION in merged/vanilla single-clip mode, the base IS the
        # layer name — adding the token would be redundant, so we hide the
        # controls. The resolver also enforces this defensively.
        if not is_action_single_clip:
            col.separator()
            col.prop(props, "clip_layer_token", text="Layer Token")
            if props.clip_layer_token != "NONE":
                row = col.row(align=True)
                row.prop(props, "clip_index_padding")
                row.prop(props, "clip_index_separator", text="Sep")

            if not has_layers and props.clip_layer_token != "NONE":
                col.label(
                    text="Layer token only resolves with Animation Layers active",
                    icon="ERROR",
                )
        elif has_layers:
            col.label(
                text="Layer token disabled — base already uses the layer name",
                icon="INFO",
            )

    def _draw_bake_settings(self, box, props, obj):
        col = box.column(align=True)

        split = col.split(factor=0.5, align=True)
        split.label(text="Bake Type:")
        split.prop(props, "al_baketype", text="")

        split = col.split(factor=0.5, align=True)
        split.label(text="Bake Operator:")
        split.prop(props, "al_operator", text="")

        split = col.split(factor=0.5, align=True)
        split.label(text="Direction:")
        split.prop(props, "al_direction", text="")

        col.separator()
        col.prop(props, "al_mergefcurves")

        if props.al_baketype == "AL":
            row = col.row(align=True)
            row.prop(props, "al_smartbake")
            if props.al_smartbake:
                row.prop_menu_enum(props, "al_handles_type")
            else:
                row.prop(props, "al_step")
        else:
            col.prop(props, "al_step")
            col.prop(props, "al_clearconstraints")

        if obj is not None and obj.mode == "POSE":
            col.prop(props, "al_onlyselected")

        if props.al_operator == "MERGE":
            col.prop(props, "al_actioncopy")

        col.separator()
        split = col.split(factor=0.5, align=True)
        split.label(text="Frame Range:")
        split.prop(props, "al_bake_range_type", text="")
        if props.al_bake_range_type == "CUSTOM":
            col.prop(props, "al_bake_range_custom", text="")


classes = (QAE_PT_quick_export,)


def register():
    global _PREVIEW_COLLECTION
    _PREVIEW_COLLECTION = bpy.utils.previews.new()
    icon_path = os.path.join(_ICON_DIR, "anim_export.png")
    if os.path.isfile(icon_path):
        try:
            _PREVIEW_COLLECTION.load("anim_export", icon_path, "IMAGE")
        except KeyError:
            # Already loaded (e.g. on a re-register without proper teardown).
            pass

    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.VIEW3D_HT_header.append(_draw_viewport_header_quick_export)


def unregister():
    try:
        bpy.types.VIEW3D_HT_header.remove(_draw_viewport_header_quick_export)
    except (ValueError, AttributeError):
        pass
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)

    global _PREVIEW_COLLECTION
    if _PREVIEW_COLLECTION is not None:
        try:
            bpy.utils.previews.remove(_PREVIEW_COLLECTION)
        except (KeyError, RuntimeError):
            pass
        _PREVIEW_COLLECTION = None
