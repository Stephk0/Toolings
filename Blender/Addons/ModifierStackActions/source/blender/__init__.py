"""Blender UI + bpy boundary."""

from . import insert, operators, properties, ui

_modules = (properties, operators, insert, ui)


def register():
    for m in _modules:
        m.register()


def unregister():
    for m in reversed(_modules):
        m.unregister()
