"""Blender UI + bpy boundary."""

from . import keymap, live, operators, overlay, properties, ui

_modules = (properties, operators, ui, live, overlay, keymap)


def register():
    for m in _modules:
        m.register()


def unregister():
    for m in reversed(_modules):
        m.unregister()
