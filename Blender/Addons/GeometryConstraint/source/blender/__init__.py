"""Blender UI + bpy boundary."""

from . import live, operators, properties, ui

_modules = (properties, operators, ui, live)


def register():
    for m in _modules:
        m.register()


def unregister():
    for m in reversed(_modules):
        m.unregister()
