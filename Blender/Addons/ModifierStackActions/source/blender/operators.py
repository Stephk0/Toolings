"""Show Up To Here / Restore / Extract Up To Here / Apply Above / Move operators."""

import bpy
from bpy.props import BoolProperty, EnumProperty, StringProperty

from ..core import stack
from . import insert, properties

EXTRACT_TYPES = {'MESH', 'CURVE', 'SURFACE', 'FONT'}


def resolve(context, object_name, modifier_name):
    """(object, modifier index) from operator props, else the active modifier.

    The context menu always passes both names; empty names (F3, scripts) fall
    back to the active object and its active modifier.
    """
    obj = bpy.data.objects.get(object_name) if object_name else context.object
    if obj is None or not hasattr(obj, "modifiers"):
        return None, -1
    if modifier_name:
        idx = obj.modifiers.find(modifier_name)
    else:
        active = obj.modifiers.active
        idx = obj.modifiers.find(active.name) if active else -1
    return obj, idx


def restore_stack(obj):
    """Show every modifier the preview hid. Returns how many were shown."""
    state = properties.get_state(obj)
    properties.clear_state(obj)
    if state is None:
        return 0
    mods = obj.modifiers
    shown = stack.restore_plan([m.name for m in mods], state["hidden"])
    for i in shown:
        mods[i].show_viewport = True
    return len(shown)


class _Target:
    object_name: StringProperty(options={'HIDDEN', 'SKIP_SAVE'})
    modifier_name: StringProperty(options={'HIDDEN', 'SKIP_SAVE'})


class OBJECT_OT_modifier_up_to_here(_Target, bpy.types.Operator):
    """Hide every modifier after this one in the viewport, to see the stack up to here.
    Run again on the same modifier to bring them back"""

    bl_idname = "object.modifier_up_to_here"
    bl_label = "Show Up To Here"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        obj, idx = resolve(context, self.object_name, self.modifier_name)
        if idx < 0:
            self.report({'WARNING'}, "No modifier to show up to")
            return {'CANCELLED'}
        mods = obj.modifiers
        target = mods[idx].name

        state = properties.get_state(obj)
        restore_stack(obj)
        if state is not None and state["target"] == target:
            self.report({'INFO'}, f"Restored modifier stack of '{obj.name}'")
            return {'FINISHED'}

        hide = stack.hide_after_plan([m.show_viewport for m in mods], idx)
        if not hide:
            self.report({'INFO'}, f"Nothing visible after '{target}'")
            return {'FINISHED'}
        for i in hide:
            mods[i].show_viewport = False
        properties.set_state(obj, target, [mods[i].name for i in hide])
        self.report({'INFO'}, f"Showing '{obj.name}' up to '{target}' ({len(hide)} hidden)")
        return {'FINISHED'}


class OBJECT_OT_modifier_up_to_here_restore(_Target, bpy.types.Operator):
    """Show the modifiers hidden by Show Up To Here again"""

    bl_idname = "object.modifier_up_to_here_restore"
    bl_label = "Restore Modifier Stack"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        obj = bpy.data.objects.get(self.object_name) if self.object_name else context.object
        if obj is None or properties.get_state(obj) is None:
            self.report({'INFO'}, "No modifier preview to restore")
            return {'CANCELLED'}
        count = restore_stack(obj)
        self.report({'INFO'}, f"Restored {count} modifier(s) on '{obj.name}'")
        return {'FINISHED'}


class OBJECT_OT_modifier_extract_up_to_here(_Target, bpy.types.Operator):
    """Create a new object from the stack evaluated up to and including this modifier.
    The source object is not changed"""

    bl_idname = "object.modifier_extract_up_to_here"
    bl_label = "Extract Up To Here"
    bl_options = {'REGISTER', 'UNDO'}

    select_new: BoolProperty(
        name="Select Result",
        description="Make the extracted object the only selected and active object (Object Mode only)",
        default=True,
    )
    hide_source: BoolProperty(
        name="Hide Source",
        description="Hide the source object in the viewport after extracting",
        default=False,
    )
    new_name: StringProperty(
        name="Name",
        description="Name of the extracted object and mesh. Empty uses <Object>_<Modifier>",
        options={'SKIP_SAVE'},
    )
    ask_name: BoolProperty(
        description="Ask for the name in a dialog before extracting",
        options={'HIDDEN', 'SKIP_SAVE'},
    )

    def invoke(self, context, event):
        if not self.ask_name:
            return self.execute(context)
        obj, idx = resolve(context, self.object_name, self.modifier_name)
        if idx >= 0 and not self.new_name:
            self.new_name = stack.extract_name(obj.name, obj.modifiers[idx].name)
        return context.window_manager.invoke_props_dialog(self, title="Extract Up To Here")

    def draw(self, context):
        layout = self.layout
        row = layout.row()
        # Dialog opens with the name field in edit mode, text selected. Needs a
        # row, and breaks under use_property_split (Blender 5.0).
        row.activate_init = self.ask_name
        row.prop(self, "new_name")
        layout.prop(self, "select_new")
        layout.prop(self, "hide_source")

    def execute(self, context):
        obj, idx = resolve(context, self.object_name, self.modifier_name)
        if idx < 0:
            self.report({'WARNING'}, "No modifier to extract from")
            return {'CANCELLED'}
        if obj.type not in EXTRACT_TYPES:
            self.report({'WARNING'}, f"Cannot extract a mesh from a {obj.type.title()} object")
            return {'CANCELLED'}

        mods = obj.modifiers
        mod_name = mods[idx].name
        changes = stack.extract_plan([m.show_viewport for m in mods], idx)
        saved = {i: mods[i].show_viewport for i in changes}
        try:
            for i, show in changes.items():
                mods[i].show_viewport = show
            depsgraph = context.evaluated_depsgraph_get()
            mesh = bpy.data.meshes.new_from_object(
                obj.evaluated_get(depsgraph),
                preserve_all_data_layers=True,
                depsgraph=depsgraph,
            )
        finally:
            for i, show in saved.items():
                mods[i].show_viewport = show

        name = self.new_name.strip() or stack.extract_name(obj.name, mod_name)
        mesh.name = name
        new_obj = bpy.data.objects.new(name, mesh)
        new_obj.matrix_world = obj.matrix_world.copy()
        for coll in obj.users_collection or (context.collection,):
            coll.objects.link(new_obj)

        if self.hide_source:
            obj.hide_set(True)
        if self.select_new and context.mode == 'OBJECT':
            for o in context.selected_objects:
                o.select_set(False)
            new_obj.select_set(True)
            context.view_layer.objects.active = new_obj

        self.report({'INFO'}, f"Extracted '{name}' ({len(mesh.vertices)} verts)")
        return {'FINISHED'}


class OBJECT_OT_modifier_apply_above(_Target, bpy.types.Operator):
    """Apply every modifier above this one into the mesh, top to bottom.
    This modifier and the ones below it stay"""

    bl_idname = "object.modifier_apply_above"
    bl_label = "Apply Modifiers Above"
    bl_options = {'REGISTER', 'UNDO'}

    single_user: BoolProperty(
        name="Make Single User",
        description="The object data is shared with other objects: give this object its own "
                    "copy before applying, the others keep the original",
        options={'SKIP_SAVE'},
    )

    def invoke(self, context, event):
        obj, idx = resolve(context, self.object_name, self.modifier_name)
        data = getattr(obj, "data", None) if idx >= 0 else None
        if data is not None and data.users > 1 and not self.single_user:
            # Same question as Blender's own Apply on shared data.
            self.single_user = True
            return context.window_manager.invoke_confirm(
                self, event, title="Apply Modifiers Above",
                message=f"'{data.name}' is used by {data.users} objects. "
                        "Make it single user and apply?",
                confirm_text="Make Single User and Apply")
        return self.execute(context)

    def execute(self, context):
        obj, idx = resolve(context, self.object_name, self.modifier_name)
        if idx < 0:
            self.report({'WARNING'}, "No modifier to apply up to")
            return {'CANCELLED'}
        mods = obj.modifiers
        target = mods[idx].name

        # A Show Up To Here preview hid these; applying would skip them as off.
        state = properties.get_state(obj)
        if state is not None and set(state["hidden"]) & {m.name for m in mods[:idx]}:
            restore_stack(obj)

        apply, skip = stack.apply_plan([m.show_viewport for m in mods], idx)
        if not apply:
            self.report({'INFO'}, f"Nothing to apply above '{target}'")
            return {'CANCELLED'}
        # A pending Add Before/After would take the stack change for its insert.
        insert.disarm()
        names = [mods[i].name for i in apply]
        applied = 0
        error = ""
        with context.temp_override(object=obj, active_object=obj):
            for name in names:
                try:
                    bpy.ops.object.modifier_apply(modifier=name, single_user=self.single_user)
                except RuntimeError as exc:
                    error = f"'{name}': " + str(exc).strip().removeprefix("Error: ")
                    break
                applied += 1

        if target in mods:
            mods.active = mods[target]
        if not applied:
            self.report({'WARNING'}, f"Couldn't apply {error}")
            return {'CANCELLED'}
        msg = f"Applied {applied} modifier(s) above '{target}'"
        if skip:
            msg += f", left {len(skip)} switched-off one(s) in place"
        if error:
            self.report({'WARNING'}, f"{msg}; stopped at {error}")
        else:
            self.report({'INFO'}, msg)
        return {'FINISHED'}


def pin_flags(mods):
    """Pin to Last flag of every modifier, in stack order."""
    return [m.use_pin_to_last for m in mods]


def move_to(mods, name, target):
    """Move modifier ``name`` to ``target``. False when Blender didn't move it.

    ``ObjectModifiers.move`` does nothing, without an error, for a move across
    the pinned block.
    """
    source = mods.find(name)
    if source != target:
        mods.move(source, target)
    return mods.find(name) == target


class OBJECT_OT_modifier_stack_move(_Target, bpy.types.Operator):
    """Move this modifier one slot up or down, to the top or bottom of the stack,
    or before or after the modifiers pinned to last"""

    bl_idname = "object.modifier_stack_move"
    bl_label = "Move Modifier"
    bl_options = {'REGISTER', 'UNDO'}

    position: EnumProperty(
        name="Position",
        items=(
            ('FIRST', "First", "Move to the top of the stack"),
            ('LAST', "Last", "Move to the bottom of the stack"),
            ('UP', "Up", "Move one slot up the stack"),
            ('DOWN', "Down", "Move one slot down the stack"),
            ('BEFORE_PINNED', "Before Pinned", "Unpin and move right above the pinned modifiers"),
            ('AFTER_PINNED', "After Pinned", "Pin to last, below the pinned modifiers"),
        ),
        default='FIRST',
    )

    @classmethod
    def description(cls, _context, props):
        return {
            'FIRST': "Move this modifier to the top of the stack. A pinned modifier is unpinned",
            'LAST': "Move this modifier to the bottom of the stack, above any modifiers "
                    "pinned to last",
            'UP': "Move this modifier one slot up the stack",
            'DOWN': "Move this modifier one slot down the stack",
            'BEFORE_PINNED': "Unpin this modifier and move it right above the modifiers "
                             "pinned to last",
            'AFTER_PINNED': "Pin this modifier to last, below the modifiers already pinned",
        }[props.position]

    def execute(self, context):
        obj, idx = resolve(context, self.object_name, self.modifier_name)
        if idx < 0:
            self.report({'WARNING'}, "No modifier to move")
            return {'CANCELLED'}
        mods = obj.modifiers
        target, pin = stack.move_plan(pin_flags(mods), idx, self.position)
        if idx == target and pin is None:
            return {'CANCELLED'}
        name = mods[idx].name
        if pin is not None:
            # Blender re-slots it at the pinned-block boundary; move_to places it.
            mods[name].use_pin_to_last = pin
        try:
            # Blender raises for some moves it refuses and silently ignores others.
            moved = move_to(mods, name, target)
        except RuntimeError as exc:
            self.report({'WARNING'}, str(exc).strip().removeprefix("Error: "))
            moved = False
        if not moved:
            if pin is None:
                self.report({'WARNING'}, f"Blender didn't allow moving '{name}' there")
                return {'CANCELLED'}
            self.report({'WARNING'}, f"'{name}' was re-pinned but couldn't be moved")
        mods.active = mods[name]
        return {'FINISHED'}


classes = (
    OBJECT_OT_modifier_up_to_here,
    OBJECT_OT_modifier_up_to_here_restore,
    OBJECT_OT_modifier_extract_up_to_here,
    OBJECT_OT_modifier_apply_above,
    OBJECT_OT_modifier_stack_move,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
