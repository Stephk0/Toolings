"""Copy Modifier / Paste Modifier Before / After / Duplicate Modifier.

The clipboard holds a reference (object name + modifier name), not a snapshot:
the paste copies the modifier as it is at paste time. Blender does the copy
(``modifier_copy`` on the same object, ``modifier_copy_to_selected`` across
objects, so every setting and Geometry Nodes input comes along); the new
modifier is then moved next to the right-clicked one.
"""

import bpy
from bpy.app.handlers import persistent
from bpy.props import EnumProperty

from ..core import stack
from . import insert
from .operators import _Target, move_to, resolve

_clipboard = {"object": "", "modifier": ""}


def copied():
    """(object, modifier) on the clipboard, or (None, None) when empty or gone."""
    obj = bpy.data.objects.get(_clipboard["object"]) if _clipboard["object"] else None
    mod = obj.modifiers.get(_clipboard["modifier"]) if obj is not None else None
    return (obj, mod) if mod is not None else (None, None)


def _clear():
    _clipboard["object"] = _clipboard["modifier"] = ""


@persistent
def _on_load(_dummy):
    # Names from the previous file could match unrelated data in the new one.
    _clear()


class OBJECT_OT_modifier_stack_copy(_Target, bpy.types.Operator):
    """Copy this modifier, to paste it before or after another modifier"""

    bl_idname = "object.modifier_stack_copy"
    bl_label = "Copy Modifier"

    def execute(self, context):
        obj, idx = resolve(context, self.object_name, self.modifier_name)
        if idx < 0:
            self.report({'WARNING'}, "No modifier to copy")
            return {'CANCELLED'}
        _clipboard["object"] = obj.name
        _clipboard["modifier"] = obj.modifiers[idx].name
        self.report({'INFO'}, f"Copied '{_clipboard['modifier']}' from '{obj.name}'")
        return {'FINISHED'}


class OBJECT_OT_modifier_stack_paste(_Target, bpy.types.Operator):
    """Paste the copied modifier before or after this one"""

    bl_idname = "object.modifier_stack_paste"
    bl_label = "Paste Modifier"
    bl_options = {'REGISTER', 'UNDO'}

    position: EnumProperty(
        name="Position",
        items=(
            ('BEFORE', "Before", "Paste above this modifier"),
            ('AFTER', "After", "Paste below this modifier"),
        ),
        default='AFTER',
    )

    @classmethod
    def description(cls, _context, props):
        where = "before" if props.position == 'BEFORE' else "after"
        return f"Paste the copied modifier {where} this one"

    @classmethod
    def poll(cls, context):
        return copied()[1] is not None

    def execute(self, context):
        src_obj, src_mod = copied()
        if src_mod is None:
            self.report({'WARNING'}, "The copied modifier no longer exists")
            return {'CANCELLED'}
        obj, idx = resolve(context, self.object_name, self.modifier_name)
        if obj is None:
            self.report({'WARNING'}, "No object to paste to")
            return {'CANCELLED'}
        # A pending Add Before/After would grab the pasted modifier as its insert.
        insert.disarm()
        mods = obj.modifiers
        anchor = mods[idx].name if idx >= 0 else None
        before = [m.name for m in mods]

        if src_obj == obj:
            with context.temp_override(object=obj, active_object=obj):
                bpy.ops.object.modifier_copy(modifier=src_mod.name)
        else:
            with context.temp_override(object=src_obj, active_object=src_obj,
                                       selected_objects=[obj],
                                       selected_editable_objects=[obj]):
                bpy.ops.object.modifier_copy_to_selected(modifier=src_mod.name)
        new = stack.find_added(before, [m.name for m in mods])
        if new is None:
            self.report({'WARNING'}, f"Couldn't paste '{src_mod.name}' to '{obj.name}'")
            return {'CANCELLED'}

        if anchor is not None:
            # Match the anchor's Pin to Last, else Blender won't let the copy
            # sit next to it (pinned modifiers stay a block at the end).
            mods[new].use_pin_to_last = mods[anchor].use_pin_to_last
            target = stack.insert_target([m.name for m in mods], new, anchor, self.position)
            if not move_to(mods, new, target):
                self.report({'WARNING'}, f"Couldn't move '{new}' next to '{anchor}'")
        mods.active = mods[new]
        return {'FINISHED'}


class OBJECT_OT_modifier_stack_duplicate(_Target, bpy.types.Operator):
    """Duplicate this modifier with all its settings, directly below it"""

    bl_idname = "object.modifier_stack_duplicate"
    bl_label = "Duplicate Modifier"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        obj, idx = resolve(context, self.object_name, self.modifier_name)
        if idx < 0:
            self.report({'WARNING'}, "No modifier to duplicate")
            return {'CANCELLED'}
        # A pending Add Before/After would grab the copy as its insert.
        insert.disarm()
        mods = obj.modifiers
        src = mods[idx].name
        before = [m.name for m in mods]
        with context.temp_override(object=obj, active_object=obj):
            bpy.ops.object.modifier_copy(modifier=src)
        new = stack.find_added(before, [m.name for m in mods])
        if new is None:
            self.report({'WARNING'}, f"Couldn't duplicate '{src}'")
            return {'CANCELLED'}
        # modifier_copy puts it right after the source (same pin); keep that explicit.
        move_to(mods, new, stack.insert_target([m.name for m in mods], new, src, 'AFTER'))
        mods.active = mods[new]
        return {'FINISHED'}


def draw_menu_entries(layout, obj, mod):
    """Duplicate + Copy + Paste Before / After, for the modifier right-click menu."""
    op = layout.operator(OBJECT_OT_modifier_stack_duplicate.bl_idname, icon='COPY_ID')
    op.object_name, op.modifier_name = obj.name, mod.name
    op = layout.operator(OBJECT_OT_modifier_stack_copy.bl_idname, icon='COPYDOWN')
    op.object_name, op.modifier_name = obj.name, mod.name
    _src_obj, src_mod = copied()
    label = f"'{src_mod.name}'" if src_mod is not None else "Modifier"
    for position, word in (('BEFORE', "Before"), ('AFTER', "After")):
        op = layout.operator(OBJECT_OT_modifier_stack_paste.bl_idname,
                             text=f"Paste {label} {word}", icon='PASTEDOWN')
        op.object_name, op.modifier_name = obj.name, mod.name
        op.position = position


classes = (
    OBJECT_OT_modifier_stack_duplicate,
    OBJECT_OT_modifier_stack_copy,
    OBJECT_OT_modifier_stack_paste,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.app.handlers.load_post.append(_on_load)


def unregister():
    if _on_load in bpy.app.handlers.load_post:
        bpy.app.handlers.load_post.remove(_on_load)
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
    _clear()
