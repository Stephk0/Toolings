import bpy

from ..core import isolate
from . import preferences

# Isolation stacks per 3D Viewport (SpaceView3D pointer -> list of frozensets of
# Object.session_uid). Session-only: after a file reload a still-active local
# view is adopted as level 1.
_stacks = {}

_EXTRA_TYPES = {"keep_cameras": "CAMERA", "keep_lights": "LIGHT"}


def depth(space):
    if space.local_view is None:
        return 0
    return len(_stacks.get(space.as_pointer(), ())) or 1


def _current_stack(context, space):
    key = space.as_pointer()
    if space.local_view is None:  # left local view by other means
        _stacks.pop(key, None)
        return []
    objects = context.view_layer.objects
    stack = _stacks.get(key)
    if not stack:  # native local view, or a reloaded file
        members = frozenset(o.session_uid for o in objects if o.local_view_get(space))
        stack = [members] if members else []
    return isolate.prune(stack, (o.session_uid for o in objects))


def _extras(context, prefs):
    types = {t for attr, t in _EXTRA_TYPES.items() if getattr(prefs, attr)}
    if not types:
        return set()
    return {o.session_uid for o in context.view_layer.objects if o.type in types}


def _show_level(context, space, level, prefs):
    visible = set(level) | _extras(context, prefs)
    for ob in context.view_layer.objects:
        ob.local_view_set(space, ob.session_uid in visible)


def _exit(context, space, prefs):
    rv3d = context.region_data
    saved = None
    if prefs.keep_view_on_exit and rv3d is not None:
        saved = (rv3d.view_location.copy(), rv3d.view_rotation.copy(),
                 rv3d.view_distance, rv3d.view_perspective)
    view_prefs = context.preferences.view
    smooth = view_prefs.smooth_view
    try:
        if saved:
            view_prefs.smooth_view = 0  # no animation back to the stored view
        bpy.ops.view3d.localview(frame_selected=False)
    finally:
        view_prefs.smooth_view = smooth
    if saved:
        rv3d.view_location, rv3d.view_rotation, rv3d.view_distance, rv3d.view_perspective = saved


class VIEW3D_OT_smart_isolate(bpy.types.Operator):
    """Isolate the selection. Press again with part of it selected to isolate deeper; """ \
        """with the same or no selection to step back / exit"""
    bl_idname = "view3d.smart_isolate"
    bl_label = "Smart Isolate"
    bl_options = {"REGISTER"}

    @classmethod
    def poll(cls, context):
        return context.area is not None and context.area.type == "VIEW_3D"

    def execute(self, context):
        prefs = preferences.get(context)
        space = context.space_data
        key = space.as_pointer()
        stack = _current_stack(context, space)
        selection = frozenset(o.session_uid for o in context.selected_objects)

        action = isolate.decide(selection, stack, preferences.settings(prefs))
        if action == isolate.NONE:
            self.report({"INFO"}, "Nothing selected to isolate")
            return {"CANCELLED"}

        new_stack = isolate.apply(action, selection, stack)
        if action == isolate.EXIT:
            _exit(context, space, prefs)
            _stacks.pop(key, None)
        else:
            if action == isolate.ENTER:
                bpy.ops.view3d.localview(frame_selected=prefs.frame_selected)
                if space.local_view is None:
                    self.report({"WARNING"}, "Could not isolate the selection")
                    return {"CANCELLED"}
            _show_level(context, space, new_stack[-1], prefs)
            if prefs.frame_selected and action in (isolate.DEEPER, isolate.REPLACE):
                bpy.ops.view3d.view_selected()
            _stacks[key] = new_stack

        for region in context.area.regions:
            region.tag_redraw()
        return {"FINISHED"}


class VIEW3D_OT_smart_isolate_exit(bpy.types.Operator):
    """Leave Smart Isolate and show everything again"""
    bl_idname = "view3d.smart_isolate_exit"
    bl_label = "Exit Smart Isolate"
    bl_options = {"REGISTER"}

    @classmethod
    def poll(cls, context):
        space = context.space_data
        return space is not None and space.type == "VIEW_3D" and space.local_view is not None

    def execute(self, context):
        space = context.space_data
        _exit(context, space, preferences.get(context))
        _stacks.pop(space.as_pointer(), None)
        return {"FINISHED"}


classes = (VIEW3D_OT_smart_isolate, VIEW3D_OT_smart_isolate_exit)
