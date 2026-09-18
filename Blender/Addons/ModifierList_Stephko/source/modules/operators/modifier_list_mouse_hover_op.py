import bpy
import ctypes
import os

from ... import __package__ as base_package

# this tries to re-create the default behavior applying/removing a modifier when hovering
# over it and pressing Ctrl A or Ctrl X, its hacky and not perfect, but it seems to work on Windows

class MouseHoverOp(bpy.types.Operator):
    bl_idname = "object.ml_mouse_hover_op"
    bl_label = "Apply/Remove Modifier on Mouse Hover"
    bl_options = {'INTERNAL'}

    type: bpy.props.StringProperty() #type: ignore

    def execute(self, context):
        prefs = bpy.context.preferences.addons[base_package].preferences
        if prefs.properties_editor_style == 'LIST':
            os_type = os.name
            if os_type == 'nt':
                    MOUSEEVENTF_LEFTDOWN = 0x0002 # left button down 
                    MOUSEEVENTF_LEFTUP = 0x0004 # left button up 
                    
                    # simulate mouse button press with ctypes
                    # alt key, needs it, otherwise the modifier will be re-named instead of applied
                    ctypes.windll.user32.keybd_event(0x12, 0, 0, 0)

                    ctypes.windll.user32.mouse_event(MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
                    ctypes.windll.user32.mouse_event(MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
                    # release alt key
                    ctypes.windll.user32.keybd_event(0x12, 0, 2, 0)

                    def apply_modifier():
                        bpy.ops.object.ml_modifier_apply('INVOKE_DEFAULT')
                    
                    def remove_modifier():
                        bpy.ops.object.ml_modifier_remove('INVOKE_DEFAULT')

                    # apply the modifier, aftera a small delay
                    if self.type == 'apply modifier':
                        bpy.app.timers.register(apply_modifier, first_interval=0.001)
                    elif self.type == 'remove modifier':
                        bpy.app.timers.register(remove_modifier, first_interval=0.001)
                    return {'FINISHED'}

            else:
                self.report({'ERROR'}, "The apply/remove modifier on mouse hover feature is only available on Windows")
                return {'CANCELLED'}
        else:
            if self.type == 'apply modifier':
                bpy.ops.object.modifier_apply('INVOKE_DEFAULT')
            elif self.type == 'remove modifier':
                bpy.ops.object.modifier_remove('INVOKE_DEFAULT')
        return {'CANCELLED'}
