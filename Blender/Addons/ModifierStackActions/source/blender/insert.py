"""Add Modifier Before / After: Blender's own Add Modifier menu, inserted at a slot.

Blender always appends new modifiers to the end of the stack, and the
Geometry Nodes asset entries of its Add Modifier menu are drawn in C, so the
menu items can't be redirected. Instead our submenu draws the native menu
unchanged and arms a pending insert; the next depsgraph update that shows
exactly one new modifier on that object moves it into place.

The pending insert is dropped when anything else happens: any other change to
that object's stack, the native menu opened from anywhere else, a file load,
or a timeout. Updates that leave the stack alone (selection, a stray update
flushed inside the add operator before the modifier exists) keep it armed.
"""

import time

import bpy
from bpy.app.handlers import persistent

from ..core import stack

NATIVE_MENU = "OBJECT_MT_modifier_add"
TIMEOUT = 120.0  # seconds; a menu left open longer than this does not insert

_pending = None
_drawing_wrapper = False


def arm(obj, anchor_name, position):
    global _pending
    _pending = {
        "object": obj.name,
        "anchor": anchor_name,
        "position": position,
        "names": [m.name for m in obj.modifiers],
        "time": time.monotonic(),
    }


def disarm():
    global _pending
    _pending = None


def _push_undo():
    try:
        bpy.ops.ed.undo_push(message="Insert Modifier")
    except RuntimeError:
        pass
    return None  # one-shot timer


@persistent
def _on_depsgraph_update(_scene, _depsgraph):
    pending = _pending
    if pending is None:
        return
    obj = bpy.data.objects.get(pending["object"])
    if obj is None or time.monotonic() - pending["time"] > TIMEOUT:
        disarm()
        return
    names = [m.name for m in obj.modifiers]
    if names == pending["names"]:
        return
    disarm()
    added = stack.find_added(pending["names"], names)
    if added is None or pending["anchor"] not in names:
        return
    target = stack.insert_index(names.index(pending["anchor"]), pending["position"])
    source = names.index(added)
    if source == target:
        return
    obj.modifiers.move(source, target)
    obj.modifiers.active = obj.modifiers[added]
    # The add operator already pushed its undo step with the modifier at the
    # end; record the moved state too, so undo/redo never lands in between.
    if not bpy.app.background:
        bpy.app.timers.register(_push_undo, first_interval=0.0)


@persistent
def _on_load(_dummy):
    disarm()


def _disarm_on_native_menu(_self, _context):
    """Prepended to the native menu: opened anywhere but our submenu -> disarm."""
    if not _drawing_wrapper:
        disarm()


class _AddModifierAt:
    bl_options = {'SEARCH_ON_KEY_PRESS'}
    position = 'AFTER'

    def draw(self, context):
        global _drawing_wrapper
        layout = self.layout
        mod = getattr(context, "modifier", None)
        # Menu search re-draws this menu without the panel's context pointers;
        # keep the insert armed by the real open in that case.
        if isinstance(mod, bpy.types.Modifier) and isinstance(mod.id_data, bpy.types.Object):
            arm(mod.id_data, mod.name, self.position)

        # Search over this menu (not the native one, which would disarm).
        layout.operator_context = 'INVOKE_REGION_WIN'
        layout.operator("WM_OT_search_single_menu", text="Search...",
                        icon='VIEWZOOM').menu_idname = self.bl_idname
        layout.separator()

        # INVOKE context hides the native menu's own Search entry.
        _drawing_wrapper = True
        try:
            layout.menu_contents(NATIVE_MENU)
        finally:
            _drawing_wrapper = False


class OBJECT_MT_modifier_stack_add_before(_AddModifierAt, bpy.types.Menu):
    bl_label = "Add Modifier Before"
    position = 'BEFORE'


class OBJECT_MT_modifier_stack_add_after(_AddModifierAt, bpy.types.Menu):
    bl_label = "Add Modifier After"
    position = 'AFTER'


def draw_menu_entries(layout, obj, mod):
    """The two submenu entries, for the modifier right-click menu."""
    layout.context_pointer_set("object", obj)
    layout.context_pointer_set("modifier", mod)
    layout.menu(OBJECT_MT_modifier_stack_add_before.__name__, icon='TRIA_UP')
    layout.menu(OBJECT_MT_modifier_stack_add_after.__name__, icon='TRIA_DOWN')


classes = (
    OBJECT_MT_modifier_stack_add_before,
    OBJECT_MT_modifier_stack_add_after,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    getattr(bpy.types, NATIVE_MENU).prepend(_disarm_on_native_menu)
    bpy.app.handlers.depsgraph_update_post.append(_on_depsgraph_update)
    bpy.app.handlers.load_post.append(_on_load)


def unregister():
    disarm()
    for handlers, fn in ((bpy.app.handlers.load_post, _on_load),
                         (bpy.app.handlers.depsgraph_update_post, _on_depsgraph_update)):
        if fn in handlers:
            handlers.remove(fn)
    getattr(bpy.types, NATIVE_MENU).remove(_disarm_on_native_menu)
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
