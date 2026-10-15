bl_info = {
    "name": "Edge Constraint Mode",
    "author": "Stephan Viranyi",
    "version": (2, 1, 0),
    "blender": (4, 5, 0),
    "location": "View3D > Header (Mesh Edit mode): constraint toggle + Edge / Face / Normal",
    "description": (
        "3ds Max-style constraint toggle (Edge / Face / Normal): every Move, "
        "Rotate and Scale in Mesh Edit mode - keys, gizmos, menus - stays on "
        "the mesh."
    ),
    "category": "Mesh",
}

from . import blender


def register():
    blender.register()


def unregister():
    blender.unregister()
