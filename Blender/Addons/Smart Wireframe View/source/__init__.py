bl_info = {
    "name": "Smart Wireframe View",
    "author": "Stephan Viranyi",
    "version": (1, 0, 0),
    "blender": (4, 5, 0),
    "location": "3D Viewport > Shift+Alt+Z (replaces Toggle Overlays)",
    "description": (
        "One hotkey cycles the viewport: overlays off, overlays on, overlays "
        "+ geometry wireframe. Port of the 3ds Max WireframeEdgeFaceOff macro."
    ),
    "category": "3D View",
}

from . import blender


def register():
    blender.register()


def unregister():
    blender.unregister()
