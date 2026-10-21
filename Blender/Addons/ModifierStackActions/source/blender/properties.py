"""Per-object storage for an active "Show Up To Here" preview."""

import bpy

from ..core import stack


def get_state(obj):
    """Decoded preview state of ``obj`` or None."""
    return stack.decode_state(getattr(obj, "modifier_stack_actions_state", ""))


def set_state(obj, target, hidden_names):
    obj.modifier_stack_actions_state = stack.encode_state(target, hidden_names)


def clear_state(obj):
    obj.modifier_stack_actions_state = ""


def register():
    # JSON (see core.stack.encode_state); saved with the .blend so a preview
    # left on can still be restored after reopening the file.
    bpy.types.Object.modifier_stack_actions_state = bpy.props.StringProperty(
        name="Modifier Stack Actions State",
        options={'HIDDEN'},
    )


def unregister():
    del bpy.types.Object.modifier_stack_actions_state
