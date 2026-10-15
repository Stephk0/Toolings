bl_info = {
    "name": "Edge Constraint Mode",
    "author": "Stephan Viranyi",
    "version": (2, 0, 0),
    "blender": (4, 5, 0),
    "location": "View3D > Header (Mesh Edit mode) — constraint buttons, then G / R / S",
    "description": (
        "3ds Max-style sub-object constraints (Edge / Face / Normal): Move, "
        "Rotate and Scale of the selection slide along the mesh instead of "
        "leaving it."
    ),
    "category": "Mesh",
}

from . import blender


def register():
    blender.register()


def unregister():
    blender.unregister()
