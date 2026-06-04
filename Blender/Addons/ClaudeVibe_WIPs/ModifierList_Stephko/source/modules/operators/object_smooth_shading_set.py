import bpy
from bpy.props import *
from bpy.types import Operator


class OBJECT_OT_ml_smooth_shading_set(Operator):
    bl_idname = "object.ml_smooth_shading_set"
    bl_label = "Set Smooth Shading"
    bl_description = "Set smooth shading"
    bl_options = {'REGISTER', 'UNDO', 'INTERNAL'}

    auto_smooth: BoolProperty(options={'HIDDEN', 'SKIP_SAVE'})
    object_name: StringProperty(options={'HIDDEN', 'SKIP_SAVE'})
    shade_smooth: BoolProperty(options={'HIDDEN', 'SKIP_SAVE'})

    def execute(self, context):
        if self.auto_smooth:
            selected_objects = bpy.context.selected_objects
            active_ob = context.view_layer.objects.active
            bpy.ops.object.select_all(action='DESELECT')

            ob = bpy.data.objects[self.object_name]
            context.view_layer.objects.active = ob
            ob.select_set(True)
            bpy.ops.object.shade_auto_smooth('INVOKE_DEFAULT')
            ob.select_set(False)
            context.view_layer.objects.active = active_ob
            for ob in selected_objects:
                ob.select_set(True)
        else:
            ob = bpy.data.objects[self.object_name]

            # if auto_smooth is enabled, remove auto_smooth
            for mod in ob.modifiers:
                if mod.name == 'Smooth by Angle':
                    ob.modifiers.remove(mod)

            for p in ob.data.polygons:
                p.use_smooth = self.shade_smooth


        return {'FINISHED'}
