import bpy

_items = []


def register():
    kc = bpy.context.window_manager.keyconfigs.addon
    if kc is None:  # background mode
        return
    km = kc.keymaps.new(name="3D View", space_type="VIEW_3D")
    # Shift+Alt+Z is Blender's overlay toggle; the cycle takes it over.
    kmi = km.keymap_items.new("view3d.smart_wireframe_cycle", "Z", "PRESS", shift=True, alt=True)
    _items.append((km, kmi))
    kmi = km.keymap_items.new("view3d.smart_wireframe_cycle", "Z", "PRESS", shift=True, alt=True, ctrl=True)
    kmi.properties.reverse = True
    _items.append((km, kmi))


def unregister():
    for km, kmi in _items:
        km.keymap_items.remove(kmi)
    _items.clear()


def draw(layout, context):
    layout.label(text="Hotkeys")
    for km, kmi in _items:
        row = layout.row()
        row.prop(kmi, "active", text="")
        row.label(text="Cycle Backwards" if kmi.properties.reverse else "Cycle")
        row.prop(kmi, "type", text="", full_event=True)
