"""Scene settings for the constraint mode."""

import bpy
from bpy.props import BoolProperty, EnumProperty, IntProperty
from bpy.types import PropertyGroup

from ..core import constraint as C

TYPE_ITEMS = (
    (C.MODE_EDGE, "Edge", "Constrain Move / Rotate / Scale to the mesh edges (3ds Max Edge constraint)", 'SNAP_EDGE', 1),
    (C.MODE_FACE, "Face", "Constrain Move / Rotate / Scale to the surrounding face surfaces (3ds Max Face constraint)", 'SNAP_FACE', 2),
    (C.MODE_NORMAL, "Normal", "Constrain Move / Rotate / Scale to each vertex normal (3ds Max Normal constraint)", 'NORMALS_VERTEX', 3),
)
# Operator-level choice (scripts can ask for no constraint explicitly).
CONSTRAINT_ITEMS = ((C.MODE_NONE, "None", "No constraint", 'CANCEL', 0),) + TYPE_ITEMS
TYPE_ICONS = {i[0]: i[3] for i in TYPE_ITEMS}


def active_mode(settings):
    """The constraint in force: the chosen type while enabled, else NONE."""
    if settings is None or not settings.enabled:
        return C.MODE_NONE
    return settings.mode


def _changed(_self, context):
    from . import live
    live.reset()
    screen = getattr(context, "screen", None)
    if screen is None:
        return
    for area in screen.areas:
        if area.type == 'VIEW_3D':
            area.tag_redraw()


class EdgeConstraintModeSettings(PropertyGroup):
    enabled: BoolProperty(
        name="Transform Constraint",
        description=(
            "Constrain every Move / Rotate / Scale in Mesh Edit mode (keys, gizmos, "
            "menus, any keymap) to the chosen Edge / Face / Normal constraint"
        ),
        default=False,
        update=_changed,
    )
    mode: EnumProperty(
        name="Constraint Type",
        description="What the selection is constrained to while the constraint is on",
        items=TYPE_ITEMS,
        default=C.MODE_EDGE,
        update=_changed,
    )
    live: BoolProperty(
        name="Constrain Blender Transforms",
        description=(
            "Apply the constraint to Blender's own transforms (G/R/S, W/E/R, gizmos, menus). "
            "Turn off to only constrain the Constrained Transform operator"
        ),
        default=True,
        update=_changed,
    )
    stop_at_vertices: BoolProperty(
        name="Stop at Vertices",
        description=(
            "Edge: a sliding vertex stops at the end of its edge, so it never slides through "
            "an existing loop (3ds Max behavior). Turn off to keep sliding along the next "
            "edges, up to Reach"
        ),
        default=True,
        update=_changed,
    )
    stop_at_selected: BoolProperty(
        name="Stop at Selected",
        description="A sliding vertex stops when it reaches another selected vertex (keeps parallel loops from crossing)",
        default=True,
        update=_changed,
    )
    reach: IntProperty(
        name="Reach",
        description="How many edges (Edge) or face rings (Face) a vertex may slide across in one transform",
        default=C.DEFAULT_REACH, min=1, soft_max=16, max=64,
        update=_changed,
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
