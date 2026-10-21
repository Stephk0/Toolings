"""Blender UI + bpy boundary."""

from . import live, operators, overlay, properties, ui

_modules = (properties, operators, ui, live, overlay)


def register():
    for m in _modules:
        m.register()


def unregister():
    for m in reversed(_modules):
        m.unregister()
