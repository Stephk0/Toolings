bl_info = {
    "name": "Modifier Stack Actions",
    "author": "Stephan Viranyi",
    "version": (1, 0, 0),
    "blender": (4, 5, 0),
    "location": "Properties > Modifiers > right-click a modifier",
    "description": (
        "Right-click a modifier to preview the stack up to it (hides everything "
        "after, restorable) or extract the mesh as it is at that point."
    ),
    "category": "Object",
}

from . import blender


def register():
    blender.register()


def unregister():
    blender.unregister()
