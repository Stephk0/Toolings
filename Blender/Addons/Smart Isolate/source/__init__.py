bl_info = {
    "name": "Smart Isolate",
    "author": "Stephan Viranyi",
    "version": (1, 0, 1),
    "blender": (4, 5, 0),
    "location": "3D Viewport > Numpad / (replaces Local View)",
    "description": (
        "Local View that toggles and nests: isolate the selection, isolate a "
        "part of it deeper, same or no selection steps back / exits. Optionally "
        "keeps cameras and lights."
    ),
    "category": "3D View",
}

from . import blender


def register():
    blender.register()


def unregister():
    blender.unregister()
