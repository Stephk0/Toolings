import bpy

from . import keymap, operators, preferences

_classes = (preferences.SmartWireframePreferences, *operators.classes)


def register():
    for cls in _classes:
        bpy.utils.register_class(cls)
    keymap.register()


def unregister():
    keymap.unregister()
    for cls in reversed(_classes):
        bpy.utils.unregister_class(cls)
