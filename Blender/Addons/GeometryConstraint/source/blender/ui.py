"""Viewport header toggle, settings popover and right-click menu entries."""

import bpy
from bpy.types import Menu, Panel

from ..core import constraint as C
from .properties import TYPE_ICONS, TYPE_ITEMS

TYPE_LABELS = {i[0]: i[1] for i in TYPE_ITEMS}


class VIEW3D_PT_geometry_constraint(Panel):
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'HEADER'
    bl_label = "Transform Constraint"

    def draw(self, context):
        s = context.scene.geometry_constraint
        layout = self.layout
        layout.prop(s, "enabled", text="Constraint On")
        layout.prop(s, "mode", expand=True)
        is_edge = s.mode == C.MODE_EDGE
        col = layout.column()
        col.active = is_edge
        col.prop(s, "even_slide")
        col.prop(s, "stop_at_vertices")
        col = layout.column()
        col.active = s.mode == C.MODE_FACE or (is_edge and not s.stop_at_vertices)
        col.prop(s, "reach")
        sub = col.column()
        sub.active = is_edge and not s.stop_at_vertices
        sub.prop(s, "stop_at_selected")
        layout.separator()
        layout.prop(s, "show_constraint")
        layout.prop(s, "live")
        layout.prop(s, "debug")


def draw_header(self, context):
    # Drawn after the Edit-mode menus (View ... UV): VIEW3D_HT_header.append
    # lands past the shading buttons, where normal window widths clip it.
    if context.mode != 'EDIT_MESH':
        return
    s = context.scene.geometry_constraint
    self.layout.separator()
    row = self.layout.row(align=True)
    row.prop(s, "enabled", text="", icon=TYPE_ICONS.get(s.mode, 'SNAP_EDGE'))
    sub = row.row(align=True)
    sub.active = s.enabled
    sub.prop(s, "mode", text="")
    row.popover(panel="VIEW3D_PT_geometry_constraint", text="")


class VIEW3D_MT_geometry_constraint(Menu):
    """Every constraint hotkey as a button: right-click one > Assign Shortcut."""
    bl_label = "Geometry Constraint"

    def draw(self, context):
        s = context.scene.geometry_constraint
        layout = self.layout
        for mode, label, _desc, icon, _n in TYPE_ITEMS:
            on = s.enabled and s.mode == mode
            layout.operator(f"view3d.geometry_constraint_{mode.lower()}",
                            text=label, icon=icon, depress=on)
        layout.separator()
        layout.operator("view3d.geometry_constraint_cycle_full",
                        text="Cycle: Off > Edge > Face > Normal")
        layout.operator("view3d.geometry_constraint_cycle_surface",
                        text="Cycle: Off > Edge > Face")


def draw_context_menu(self, context):
    # Operator buttons (not the property), so right-click > Assign Shortcut
    # binds the same toggle the hotkey list shows.
    s = context.scene.geometry_constraint
    layout = self.layout
    layout.separator()
    label = f"Geometry Constraint ({TYPE_LABELS[s.mode]})"
    layout.operator("view3d.geometry_constraint_toggle", text=label,
                    icon='CHECKBOX_HLT' if s.enabled else 'CHECKBOX_DEHLT')
    layout.menu("VIEW3D_MT_geometry_constraint", icon=TYPE_ICONS.get(s.mode, 'SNAP_EDGE'))


classes = (VIEW3D_PT_geometry_constraint, VIEW3D_MT_geometry_constraint)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.VIEW3D_MT_editor_menus.append(draw_header)
    bpy.types.VIEW3D_MT_edit_mesh_context_menu.append(draw_context_menu)


def unregister():
    bpy.types.VIEW3D_MT_edit_mesh_context_menu.remove(draw_context_menu)
    bpy.types.VIEW3D_MT_editor_menus.remove(draw_header)
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
