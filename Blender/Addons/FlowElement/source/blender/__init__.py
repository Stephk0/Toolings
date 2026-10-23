"""Blender UI + bpy boundary."""

from . import operators, ui

_modules = (operators, ui)


def register():
    for m in _modules:
        m.register()


def unregister():
    for m in reversed(_modules):
        m.unregister()
