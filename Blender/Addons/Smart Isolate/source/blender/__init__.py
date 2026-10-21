import bpy

from . import keymap, operators, preferences, ui

_classes = (preferences.SmartIsolatePreferences, *operators.classes)


def register():
    for cls in _classes:
        bpy.utils.register_class(cls)
    ui.register()
    keymap.register()


def unregister():
    keymap.unregister()
    ui.unregister()
    for cls in reversed(_classes):
        bpy.utils.unregister_class(cls)
