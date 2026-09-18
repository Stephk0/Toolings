import bpy
from bpy.types import Operator
from ..utils import get_ml_active_object
from bpy.props import *


class OBJECT_OT_ml_modifier_add(Operator):
    bl_idname = "object.ml_modifier_bake"
    bl_label = "Bake"
    bl_description = ("bake modifiers")

    bl_options = {'REGISTER', 'UNDO'}

    bake_id: IntProperty(name="Bake_ID", default=0)#type: ignore

    def draw(self, context):
        layout = self.layout
        row = layout.row(align = True)
        row.prop(self,"bake_id")

    def execute(self, context):
        ob = get_ml_active_object()

        if not ob:
            return False

        md = ob.modifiers[ob.ml_modifier_active_index]

        if bpy.data.is_saved:
            bpy.ops.object.geometry_node_bake_single(session_uid = int(md.id_data.session_uid), modifier_name = str(md.name), bake_id = int(md.bakes[self.bake_id].bake_id))

        active_index = md.name 
        for mod in ob.modifiers:
            if mod.name != active_index:
                mod.show_viewport = False
            else:
                break

        md.show_viewport = True
        return {'FINISHED'}
