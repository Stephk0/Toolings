import bpy
from bpy.types import Panel

from . import al_bridge


def _draw_viewport_header_quick_export(self, context):
    """Header button — sits at the right of the 3D View header."""
    obj = context.active_object
    layout = self.layout
    row = layout.row(align=True)
    row.separator()
    sub = row.row(align=True)
    sub.enabled = (
        al_bridge.is_animation_layers_available()
        and obj is not None
        and obj.type == "ARMATURE"
        and al_bridge.has_animation_layers(obj)
    )
    sub.operator("alqe.quick_export", text="", icon="EXPORT")


class ALQE_PT_quick_export(Panel):
    bl_label = "Quick Export"
    bl_idname = "ALQE_PT_quick_export"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_parent_id = "ANIMLAYERS_PT_VIEW_3D_List"
    bl_options = {"DEFAULT_CLOSED"}

    @classmethod
    def poll(cls, context):
        return al_bridge.is_animation_layers_available()

    def draw(self, context):
        layout = self.layout
        props = context.scene.alqe_props

        if not al_bridge.is_animation_layers_available():
            layout.label(text="Animation Layers addon not detected", icon="ERROR")
            return

        col = layout.column(align=True)
        col.prop(props, "export_path")

        layout.prop(props, "export_mode", expand=True)

        box = layout.box()
        box.label(text="Filename")
        box.prop(props, "filename_source", text="Source")
        if props.filename_source == "CUSTOM":
            box.prop(props, "custom_filename", text="Name")
        if props.filename_source == "ACTION" and props.export_mode == "MERGED":
            box.prop(props, "filename_layer_source", expand=True)
        row = box.row(align=True)
        row.prop(props, "filename_prefix")
        row.prop(props, "filename_suffix")
        if props.export_mode == "PER_LAYER":
            box.label(text="Per Layer: filename gets the layer/action name", icon="INFO")

        layout.prop(props, "scope")

        bake_box = layout.box()
        bake_box.label(text="Bake")
        bake_box.prop(props, "bake_step")
        bake_box.prop(props, "smartbake")

        anim_box = layout.box()
        anim_box.prop(
            props, "show_fbx_animation_settings",
            icon="TRIA_DOWN" if props.show_fbx_animation_settings else "TRIA_RIGHT",
            emboss=False, text="FBX Animation",
        )
        if props.show_fbx_animation_settings:
            anim_box.prop(props, "bake_anim_use_all_bones")
            anim_box.prop(props, "bake_anim_use_nla_strips")
            anim_box.prop(props, "bake_anim_use_all_actions")
            anim_box.prop(props, "bake_anim_force_startend_keying")
            anim_box.prop(props, "bake_anim_step")
            anim_box.prop(props, "bake_anim_simplify_factor")

        arm_box = layout.box()
        arm_box.prop(
            props, "show_fbx_armature_settings",
            icon="TRIA_DOWN" if props.show_fbx_armature_settings else "TRIA_RIGHT",
            emboss=False, text="FBX Armature",
        )
        if props.show_fbx_armature_settings:
            arm_box.prop(props, "add_leaf_bones")
            arm_box.prop(props, "primary_bone_axis")
            arm_box.prop(props, "secondary_bone_axis")
            arm_box.prop(props, "armature_nodetype")

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
        layout.operator("alqe.quick_export", icon="EXPORT")


classes = (ALQE_PT_quick_export,)


def register():
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
