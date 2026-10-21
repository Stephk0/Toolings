import bpy

from ..core import cycle
from . import preferences

_LABELS = {
    cycle.OFF: "Overlays Off",
    cycle.OVERLAYS: "Overlays",
    cycle.WIREFRAME: "Overlays + Wireframe",
}


def _spaces(context, all_viewports):
    if not all_viewports:
        return [context.space_data]
    return [a.spaces.active for a in context.screen.areas if a.type == "VIEW_3D"]


class VIEW3D_OT_smart_wireframe_cycle(bpy.types.Operator):
    """Cycle the viewport between overlays off, overlays on, and overlays with geometry wireframe"""
    bl_idname = "view3d.smart_wireframe_cycle"
    bl_label = "Smart Wireframe View"
    bl_options = {"REGISTER"}

    reverse: bpy.props.BoolProperty(name="Reverse", description="Cycle backwards", default=False)

    @classmethod
    def poll(cls, context):
        return context.space_data is not None and context.space_data.type == "VIEW_3D"

    def execute(self, context):
        prefs = preferences.get(context)
        overlay = context.space_data.overlay
        current = cycle.state_of(overlay.show_overlays, overlay.show_wireframes)
        state = cycle.next_state(current, prefs.enabled(), self.reverse)
        show_overlays, show_wireframes = cycle.flags_of(state)
        for space in _spaces(context, prefs.all_viewports):
            space.overlay.show_overlays = show_overlays
            space.overlay.show_wireframes = show_wireframes
        self.report({"INFO"}, _LABELS[state])
        return {"FINISHED"}


classes = (VIEW3D_OT_smart_wireframe_cycle,)
