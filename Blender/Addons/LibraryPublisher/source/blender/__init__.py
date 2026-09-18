"""The bpy boundary. Everything here may import bpy; nothing in core/ may."""

from . import operators, panels, properties

_MODULES = (properties, operators, panels)


def register():
    for module in _MODULES:
        module.register()


def unregister():
    for module in reversed(_MODULES):
        module.unregister()
