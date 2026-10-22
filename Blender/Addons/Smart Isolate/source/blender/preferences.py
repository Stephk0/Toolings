import bpy

from ..core import isolate

ADDON_ID = __package__.rsplit(".", 1)[0]

_BACK_OR_EXIT = [
    (isolate.STEP_BACK, "Step Back One Level", "Return to the previous isolation level (exits from the first level)"),
    (isolate.EXIT_ALL, "Exit Isolation", "Leave isolation completely and show everything again"),
]


class SmartIsolatePreferences(bpy.types.AddonPreferences):
    bl_idname = ADDON_ID

    nested: bpy.props.BoolProperty(
        name="Nested Isolation",
        description=(
            "Selecting part of the isolated objects and pressing the key again "
            "isolates deeper. Off: a new selection replaces the isolation, like 3ds Max"
        ),
        default=True,
    )
    same_selection: bpy.props.EnumProperty(
        name="Same Selection",
        description="What pressing the key with an unchanged selection does",
        items=_BACK_OR_EXIT,
        default=isolate.STEP_BACK,
    )
    empty_selection: bpy.props.EnumProperty(
        name="Nothing Selected",
        description="What pressing the key with nothing selected does",
        items=_BACK_OR_EXIT,
        default=isolate.EXIT_ALL,
    )
    keep_cameras: bpy.props.BoolProperty(
        name="Keep Cameras",
        description="Cameras stay visible in isolation",
        default=True,
    )
    keep_lights: bpy.props.BoolProperty(
        name="Keep Lights",
        description="Lights stay visible and keep lighting the isolated objects",
        default=True,
    )
    frame_selected: bpy.props.BoolProperty(
        name="Frame Selection",
        description="Zoom to the isolated objects. Off: the view does not move, like 3ds Max",
        default=False,
    )
    keep_view_on_exit: bpy.props.BoolProperty(
        name="Keep View on Exit",
        description=(
            "Leaving isolation keeps the current view. "
            "Off: jump back to the view from before isolating (Blender default)"
        ),
        default=True,
    )
    show_header: bpy.props.BoolProperty(
        name="Header Indicator",
        description="Show the isolation level in the 3D Viewport header (click it to exit)",
        default=True,
    )

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        col = layout.column(heading="Isolation")
        col.prop(self, "nested")
        col.prop(self, "same_selection")
        col.prop(self, "empty_selection")
        col = layout.column(heading="Always Show")
        col.prop(self, "keep_cameras")
        col.prop(self, "keep_lights")
        col = layout.column(heading="View")
        col.prop(self, "frame_selected")
        col.prop(self, "keep_view_on_exit")
        col.prop(self, "show_header")

        from . import keymap
        keymap.draw(layout.box(), context)


def get(context):
    return context.preferences.addons[ADDON_ID].preferences


def settings(prefs):
    return isolate.Settings(
        nested=prefs.nested,
        empty_selection=prefs.empty_selection,
        same_selection=prefs.same_selection,
    )
