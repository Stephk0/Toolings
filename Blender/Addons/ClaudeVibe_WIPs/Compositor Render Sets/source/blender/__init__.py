"""bpy boundary for Compositor Render Sets: properties, operators, panels."""

import bpy
from bpy.props import PointerProperty

from . import operators, panels, properties

classes = properties.classes + operators.classes + panels.classes


def register():
    for cls in classes:
        bpy.utils.register_class(cls)

    bpy.types.Scene.compositor_render_sets = PointerProperty(
        type=properties.COMPRS_Properties)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)

    del bpy.types.Scene.compositor_render_sets
