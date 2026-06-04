bl_info = {
    "name": "Animation Layers Quick Export",
    "author": "Stephan Viranyi",
    "version": (0, 3, 0),
    "blender": (4, 2, 0),
    "location": "View3D > Sidebar > Animation > Animation Layers (sub-panel) + Header button",
    "description": "One-click non-destructive merge + FBX export for rigs using the Animation Layers addon",
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
