"""bpy boundary for Library Relink: properties, operators, panel."""

import bpy
from bpy.props import PointerProperty

from . import operators, panels, properties

classes = properties.classes + operators.classes + panels.classes


def register():
    for cls in classes:
        bpy.utils.register_class(cls)

    bpy.types.Scene.library_relink = PointerProperty(
        type=properties.LIBRELINK_PG_settings)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)

    del bpy.types.Scene.library_relink
