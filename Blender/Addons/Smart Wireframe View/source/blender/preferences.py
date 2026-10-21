import bpy

from ..core import cycle

ADDON_ID = __package__.rsplit(".", 1)[0]


class SmartWireframePreferences(bpy.types.AddonPreferences):
    bl_idname = ADDON_ID

    use_off: bpy.props.BoolProperty(
        name="Overlays Off", description="Include 'overlays off' in the cycle", default=True,
    )
    use_overlays: bpy.props.BoolProperty(
        name="Overlays", description="Include 'overlays on' in the cycle", default=True,
    )
    use_wireframe: bpy.props.BoolProperty(
        name="Overlays + Wireframe",
        description="Include 'overlays on with the geometry wireframe' in the cycle",
        default=True,
    )
    all_viewports: bpy.props.BoolProperty(
        name="All 3D Viewports",
        description="Apply the new state to every 3D Viewport in the window, not just the one under the mouse",
        default=False,
    )

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        col = layout.column(heading="Cycle")
        col.prop(self, "use_off")
        col.prop(self, "use_overlays")
        col.prop(self, "use_wireframe")
        layout.prop(self, "all_viewports")

        from . import keymap
        keymap.draw(layout.box(), context)

    def enabled(self):
        flags = {cycle.OFF: self.use_off, cycle.OVERLAYS: self.use_overlays,
                 cycle.WIREFRAME: self.use_wireframe}
        return tuple(s for s in cycle.ORDER if flags[s])


def get(context):
    return context.preferences.addons[ADDON_ID].preferences
