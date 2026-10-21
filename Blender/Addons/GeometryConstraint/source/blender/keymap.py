"""Hotkeys: unassigned keymap entries for the toggle / type / cycle operators.

They live in the add-on keyconfig's 3D View keymap, the same keymap Blender's
right-click > Assign Shortcut picks for VIEW3D_OT_* buttons, so a key set
either way shows up in the same place. Set a key in Preferences > Add-ons >
Geometry Constraint, in Preferences > Keymap, or by right-clicking a button.
"""

import bpy
import rna_keymap_ui
from bpy.types import AddonPreferences

KEYMAP = ("3D View", 'VIEW_3D')

# Operators without properties on purpose: drawing a user keymap item's
# properties right after the add-on re-registers reads freed memory and
# crashes Blender, so items are matched by idname alone.
HOTKEYS = (
    "view3d.geometry_constraint_toggle",
    "view3d.geometry_constraint_edge",
    "view3d.geometry_constraint_face",
    "view3d.geometry_constraint_normal",
    "view3d.geometry_constraint_cycle_full",
    "view3d.geometry_constraint_cycle_surface",
)

_items = []     # (keymap, keymap item) added to the add-on keyconfig


class GeometryConstraintPreferences(AddonPreferences):
    bl_idname = __package__.rpartition(".")[0]

    def draw(self, context):
        layout = self.layout
        layout.label(text="Hotkeys (Mesh Edit mode). Click a key field and press the key, or "
                          "right-click a button > Assign Shortcut.")
        kc = context.window_manager.keyconfigs.user
        km = kc.keymaps.get(KEYMAP[0]) if kc else None
        col = layout.column()
        for idname in HOTKEYS:
            kmi = next((k for k in km.keymap_items if k.idname == idname), None) if km else None
            if kmi is None:
                col.label(text=f"{idname}: removed, restore it in Preferences > Keymap")
                continue
            col.context_pointer_set("keymap", km)
            rna_keymap_ui.draw_kmi([], kc, km, kmi, col, 0)


def register():
    bpy.utils.register_class(GeometryConstraintPreferences)
    kc = bpy.context.window_manager.keyconfigs.addon
    if kc is None:          # background mode
        return
    km = kc.keymaps.new(name=KEYMAP[0], space_type=KEYMAP[1])
    for idname in HOTKEYS:
        _items.append((km, km.keymap_items.new(idname, 'NONE', 'PRESS')))


def unregister():
    for km, kmi in _items:
        km.keymap_items.remove(kmi)
    _items.clear()
    bpy.utils.unregister_class(GeometryConstraintPreferences)
