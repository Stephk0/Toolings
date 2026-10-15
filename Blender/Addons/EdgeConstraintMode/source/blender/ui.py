"""Viewport header buttons + settings popover."""

import bpy
from bpy.types import Panel

from ..core import constraint as C


class VIEW3D_PT_edge_constraint(Panel):
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'HEADER'
    bl_label = "Transform Constraint"

    def draw(self, context):
        s = context.scene.edge_constraint_mode
        layout = self.layout
        layout.prop(s, "mode", expand=True)
        col = layout.column()
        col.active = s.mode in {C.MODE_EDGE, C.MODE_FACE}
        col.prop(s, "reach")
        col.prop(s, "stop_at_selected")
        layout.separator()
        layout.label(text="G / R / S use the constraint while it is not None", icon='INFO')
        layout.prop(s, "debug")


def draw_header(self, context):
    if context.mode != 'EDIT_MESH':
        return
    s = context.scene.edge_constraint_mode
    row = self.layout.row(align=True)
    row.prop(s, "mode", expand=True, icon_only=True)
    row.popover(panel="VIEW3D_PT_edge_constraint", text="")


classes = (VIEW3D_PT_edge_constraint,)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.VIEW3D_HT_header.append(draw_header)


def unregister():
    bpy.types.VIEW3D_HT_header.remove(draw_header)
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
