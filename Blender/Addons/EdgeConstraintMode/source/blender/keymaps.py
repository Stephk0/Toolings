"""Addon keymap: G / R / S in Mesh Edit mode route through the constrained
transform. The operator's poll() fails while the constraint is None, so the
key then falls through to Blender's own transform - no install/uninstall
dance on every toggle."""

import bpy

from .operators import MESH_OT_edge_constraint_transform

_items = []


def register():
    kc = bpy.context.window_manager.keyconfigs.addon
    if kc is None:          # background mode
        return
    km = kc.keymaps.new(name='Mesh', space_type='EMPTY')
    for key, ttype in (('G', 'TRANSLATE'), ('R', 'ROTATE'), ('S', 'RESIZE')):
        kmi = km.keymap_items.new(MESH_OT_edge_constraint_transform.bl_idname, key, 'PRESS')
        kmi.properties.transform_type = ttype
        _items.append((km, kmi))


def unregister():
    while _items:
        km, kmi = _items.pop()
        try:
            km.keymap_items.remove(kmi)
        except (ReferenceError, RuntimeError):
            pass
