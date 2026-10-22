"""Right-click menu entries on modifier panels + "preview active" banner."""

import bpy

from ..core import stack
from . import clipboard, insert, operators, properties


def context_modifier(context):
    """The modifier whose panel was right-clicked, or None.

    ``button_pointer`` is the struct owning the clicked property (also for
    Geometry Nodes inputs); ``modifier`` is the panel's context pointer.
    """
    for attr in ("button_pointer", "modifier"):
        ptr = getattr(context, attr, None)
        if isinstance(ptr, bpy.types.Modifier) and isinstance(ptr.id_data, bpy.types.Object):
            return ptr
    return None


def _target(op, obj, mod):
    op.object_name = obj.name
    op.modifier_name = mod.name


def draw_button_context_menu(self, context):
    mod = context_modifier(context)
    if mod is None:
        return
    obj = mod.id_data
    state = properties.get_state(obj)
    layout = self.layout
    layout.separator()

    if state is not None and state["target"] == mod.name:
        _target(layout.operator(operators.OBJECT_OT_modifier_up_to_here.bl_idname,
                                text="Restore Modifier Stack", icon='LOOP_BACK'), obj, mod)
    else:
        _target(layout.operator(operators.OBJECT_OT_modifier_up_to_here.bl_idname,
                                icon='HIDE_OFF'), obj, mod)
        if state is not None:
            layout.operator(operators.OBJECT_OT_modifier_up_to_here_restore.bl_idname,
                            icon='LOOP_BACK').object_name = obj.name

    if obj.type in operators.EXTRACT_TYPES:
        extract = operators.OBJECT_OT_modifier_extract_up_to_here.bl_idname
        _target(layout.operator(extract, icon='DUPLICATE'), obj, mod)
        col = layout.column()
        col.operator_context = 'INVOKE_DEFAULT'
        op = col.operator(extract, text="Extract Up To Here As...", icon='GREASEPENCIL')
        _target(op, obj, mod)
        op.ask_name = True

    index = obj.modifiers.find(mod.name)
    col = layout.column()
    col.enabled = index > 0
    col.operator_context = 'INVOKE_DEFAULT'  # shared data asks before applying
    _target(col.operator(operators.OBJECT_OT_modifier_apply_above.bl_idname,
                         icon='CHECKMARK'), obj, mod)

    layout.separator()
    insert.draw_menu_entries(layout, obj, mod)
    layout.separator()
    clipboard.draw_menu_entries(layout, obj, mod)
    layout.separator()

    pinned = operators.pin_flags(obj.modifiers)
    if not any(pinned):
        entries = (
            ('FIRST', "Move to First", 'TRIA_UP_BAR'),
            ('UP', "Move Up", 'TRIA_UP'),
            ('DOWN', "Move Down", 'TRIA_DOWN'),
            ('LAST', "Move to Last", 'TRIA_DOWN_BAR'),
        )
    elif pinned[index]:
        entries = (
            ('FIRST', "Move to First (Unpin)", 'TRIA_UP_BAR'),
            ('UP', "Move Up", 'TRIA_UP'),
            ('DOWN', "Move Down", 'TRIA_DOWN'),
            ('BEFORE_PINNED', "Move Before Pinned (Unpin)", 'UNPINNED'),
            ('LAST', "Move to Last", 'TRIA_DOWN_BAR'),
        )
    else:
        entries = (
            ('FIRST', "Move to First", 'TRIA_UP_BAR'),
            ('UP', "Move Up", 'TRIA_UP'),
            ('DOWN', "Move Down", 'TRIA_DOWN'),
            ('LAST', "Move to Last (Before Pinned)", 'TRIA_DOWN_BAR'),
            ('AFTER_PINNED', "Move After Pinned (Pin)", 'PINNED'),
        )
    for position, text, icon in entries:
        row = layout.row()
        row.enabled = stack.move_changes(pinned, index, position)
        op = row.operator(operators.OBJECT_OT_modifier_stack_move.bl_idname, text=text, icon=icon)
        _target(op, obj, mod)
        op.position = position


def draw_modifiers_banner(self, context):
    obj = context.object
    state = properties.get_state(obj) if obj else None
    if state is None:
        return
    row = self.layout.box().row(align=True)
    row.alert = True
    row.label(text=f"Showing up to '{state['target']}'", icon='HIDE_OFF')
    row.operator(operators.OBJECT_OT_modifier_up_to_here_restore.bl_idname,
                 text="Restore", icon='LOOP_BACK').object_name = obj.name


def register():
    bpy.types.UI_MT_button_context_menu.append(draw_button_context_menu)
    bpy.types.DATA_PT_modifiers.prepend(draw_modifiers_banner)


def unregister():
    bpy.types.DATA_PT_modifiers.remove(draw_modifiers_banner)
    bpy.types.UI_MT_button_context_menu.remove(draw_button_context_menu)
