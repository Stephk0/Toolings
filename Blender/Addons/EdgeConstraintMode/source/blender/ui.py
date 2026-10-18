"""Viewport header toggle + settings popover."""

import bpy
from bpy.types import Panel

from ..core import constraint as C
from .properties import TYPE_ICONS


class VIEW3D_PT_edge_constraint(Panel):
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'HEADER'
    bl_label = "Transform Constraint"

    def draw(self, context):
        s = context.scene.edge_constraint_mode
        layout = self.layout
        layout.prop(s, "enabled", text="Constraint On")
        layout.prop(s, "mode", expand=True)
        is_edge = s.mode == C.MODE_EDGE
        col = layout.column()
        col.active = is_edge
        col.prop(s, "stop_at_vertices")
        col = layout.column()
        col.active = s.mode == C.MODE_FACE or (is_edge and not s.stop_at_vertices)
        col.prop(s, "reach")
        sub = col.column()
        sub.active = is_edge and not s.stop_at_vertices
        sub.prop(s, "stop_at_selected")
        layout.separator()
        layout.prop(s, "live")
        layout.prop(s, "debug")


def draw_header(self, context):
    # Drawn after the Edit-mode menus (View ... UV): VIEW3D_HT_header.append
    # lands past the shading buttons, where normal window widths clip it.
    if context.mode != 'EDIT_MESH':
        return
    s = context.scene.edge_constraint_mode
    self.layout.separator()
    row = self.layout.row(align=True)
    row.prop(s, "enabled", text="", icon=TYPE_ICONS.get(s.mode, 'SNAP_EDGE'))
    sub = row.row(align=True)
    sub.active = s.enabled
    sub.prop(s, "mode", text="")
    row.popover(panel="VIEW3D_PT_edge_constraint", text="")


classes = (VIEW3D_PT_edge_constraint,)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.VIEW3D_MT_editor_menus.append(draw_header)


def unregister():
    bpy.types.VIEW3D_MT_editor_menus.remove(draw_header)
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
