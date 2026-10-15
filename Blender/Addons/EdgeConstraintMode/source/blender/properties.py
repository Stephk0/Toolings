"""Scene settings for the constraint mode."""

import bpy
from bpy.props import BoolProperty, EnumProperty, IntProperty
from bpy.types import PropertyGroup

from ..core import constraint as C

CONSTRAINT_ITEMS = (
    (C.MODE_NONE, "None", "No constraint: G / R / S behave as usual", 'CANCEL', 0),
    (C.MODE_EDGE, "Edge", "Constrain Move / Rotate / Scale to the mesh edges (3ds Max Edge constraint)", 'SNAP_EDGE', 1),
    (C.MODE_FACE, "Face", "Constrain Move / Rotate / Scale to the surrounding face surfaces (3ds Max Face constraint)", 'SNAP_FACE', 2),
    (C.MODE_NORMAL, "Normal", "Constrain Move / Rotate / Scale to each vertex normal (3ds Max Normal constraint)", 'NORMALS_VERTEX', 3),
)


def _redraw(_self, context):
    screen = getattr(context, "screen", None)
    if screen is None:
        return
    for area in screen.areas:
        if area.type == 'VIEW_3D':
            area.tag_redraw()


class EdgeConstraintModeSettings(PropertyGroup):
    mode: EnumProperty(
        name="Constraint",
        description="Sub-object transform constraint used by G / R / S in Mesh Edit mode",
        items=CONSTRAINT_ITEMS,
        default=C.MODE_NONE,
        update=_redraw,
    )
    stop_at_selected: BoolProperty(
        name="Stop at Selected",
        description="A sliding vertex stops when it reaches another selected vertex (keeps parallel loops from crossing)",
        default=True,
    )
    reach: IntProperty(
        name="Reach",
        description="How many edges (Edge) or face rings (Face) a vertex may slide across in one transform",
        default=C.DEFAULT_REACH, min=1, soft_max=16, max=64,
    )
    debug: BoolProperty(
        name="Debug Logging",
        description="Print solver timing and per-transform info to the system console",
        default=False,
    )


classes = (EdgeConstraintModeSettings,)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.Scene.edge_constraint_mode = bpy.props.PointerProperty(type=EdgeConstraintModeSettings)


def unregister():
    del bpy.types.Scene.edge_constraint_mode
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
