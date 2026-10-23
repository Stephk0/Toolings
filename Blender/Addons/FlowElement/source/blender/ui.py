"""Menu entries: Vertex / Edge / Face menus and the edit-mode context menu."""

import bpy

from .operators import MESH_OT_st3e_flow_element as OP

_MENUS = (
    ("VIEW3D_MT_edit_mesh_vertices", 'VERTEX'),
    ("VIEW3D_MT_edit_mesh_edges", 'EDGE'),
    ("VIEW3D_MT_edit_mesh_faces", 'FACE'),
)


def _entry(mode):
    def draw(self, context):
        self.layout.separator()
        self.layout.operator(OP.bl_idname, icon='MOD_SMOOTH').mode = mode
    return draw


def _context_entry(self, context):
    self.layout.separator()
    self.layout.operator(OP.bl_idname, icon='MOD_SMOOTH').mode = 'AUTO'


_draw_funcs = []


def register():
    for menu, mode in _MENUS:
        fn = _entry(mode)
        getattr(bpy.types, menu).append(fn)
        _draw_funcs.append((menu, fn))
    bpy.types.VIEW3D_MT_edit_mesh_context_menu.append(_context_entry)
    _draw_funcs.append(("VIEW3D_MT_edit_mesh_context_menu", _context_entry))


def unregister():
    for menu, fn in _draw_funcs:
        getattr(bpy.types, menu).remove(fn)
    _draw_funcs.clear()
