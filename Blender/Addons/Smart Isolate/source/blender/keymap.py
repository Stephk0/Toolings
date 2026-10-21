import bpy

# Same keys as Blender's Local View, so Smart Isolate takes them over.
_KEYS = ("NUMPAD_SLASH", "SLASH")

_items = []


def register():
    kc = bpy.context.window_manager.keyconfigs.addon
    if kc is None:  # background mode
        return
    km = kc.keymaps.new(name="3D View", space_type="VIEW_3D")
    for key in _KEYS:
        _items.append((km, km.keymap_items.new("view3d.smart_isolate", key, "PRESS")))


def unregister():
    for km, kmi in _items:
        km.keymap_items.remove(kmi)
    _items.clear()


def draw(layout, context):
    layout.label(text="Hotkeys (replace Local View)")
    for km, kmi in _items:
        row = layout.row()
        row.prop(kmi, "active", text="")
        row.label(text=kmi.name)
        row.prop(kmi, "type", text="", full_event=True)
