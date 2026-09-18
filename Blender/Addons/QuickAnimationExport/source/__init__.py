bl_info = {
    "name": "Quick Animation Export",
    "author": "Stephan Viranyi",
    "version": (1, 0, 9),
    "blender": (4, 2, 0),
    "location": "View3D > Sidebar > Animation > Quick Animation Export + Header button",
    "description": (
        "One-click FBX export for rigs. Standalone vanilla mode plus optional "
        "non-destructive merge/bake when the Animation Layers addon is enabled."
    ),
    "category": "Animation",
}

if "bpy" in locals():
    import importlib
    for mod_name in ("al_bridge", "properties", "operators", "ui"):
        if mod_name in locals():
            importlib.reload(locals()[mod_name])

import bpy

from . import al_bridge
from . import properties
from . import operators
from . import ui


def register():
    properties.register()
    operators.register()
    ui.register()


def unregister():
    ui.unregister()
    operators.unregister()
    properties.unregister()


if __name__ == "__main__":
    register()
