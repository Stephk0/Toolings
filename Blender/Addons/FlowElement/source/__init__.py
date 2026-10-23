bl_info = {
    "name": "Flow Element",
    "author": "Stephan Viranyi",
    "version": (1, 0, 0),
    "blender": (4, 5, 0),
    "location": "Edit Mode > Vertex / Edge / Face menu, right-click menu > Flow Element",
    "description": (
        "Rebuild lost curvature of vertices, edge loops and faces from the surrounding "
        "geometry, like 3ds Max Edge Flow / Vertex Flow."
    ),
    "category": "Mesh",
}

from . import blender


def register():
    blender.register()


def unregister():
    blender.unregister()
