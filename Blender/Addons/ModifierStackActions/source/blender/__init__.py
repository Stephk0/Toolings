"""Blender UI + bpy boundary."""

from . import clipboard, insert, operators, properties, ui

_modules = (properties, operators, insert, clipboard, ui)


def register():
    for m in _modules:
        m.register()


def unregister():
    for m in reversed(_modules):
        m.unregister()
