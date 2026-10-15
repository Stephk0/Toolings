"""Blender UI + bpy boundary."""

from . import keymaps, operators, properties, ui

_modules = (properties, operators, ui, keymaps)


def register():
    for m in _modules:
        m.register()


def unregister():
    for m in reversed(_modules):
        m.unregister()
