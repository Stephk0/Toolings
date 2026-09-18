import bpy
from ..utils import get_ml_active_object

def update_atri_float_value(self, context):
    wm = context.window_manager
    bpy.ops.mesh.attribute_set('EXEC_DEFAULT', True, value_float=wm.atri_float_value)

def atri_update_float_color_value(self, context):
    wm = context.window_manager
    bpy.ops.mesh.attribute_set('EXEC_DEFAULT', True, value_color=wm.atri_float_color_value)

def attributes_ui(context, layout, num_of_rows=5):
    mesh = get_ml_active_object().data
    row = layout.row()

    col = row.column()
    col.template_list(
        "MESH_UL_attributes",
        "attributes",
        mesh,
        "attributes",
        mesh.attributes,
        "active_index",
        rows=num_of_rows
    )

    col = row.column(align=True)
    col.operator("geometry.attribute_add", icon='ADD', text="")
    col.operator("geometry.attribute_remove", icon='REMOVE', text="")

    col.separator()

    col.menu("MESH_MT_attribute_context_menu", icon='DOWNARROW_HLT', text="")

    if context.active_object.mode == 'EDIT':
        wm = context.window_manager
        row = layout.row(align=True)
        if bpy.context.object.data.attributes.active and bpy.context.object.data.attributes.active.data_type == "BOOLEAN":
            row.operator("object.ml_atri_op", text="Assign").type = "Assign"
            row.operator("object.ml_atri_op", text="Remove").type = "Remove"
            row.operator("object.ml_atri_op", text="Select").type = "Select"
        if bpy.context.object.data.attributes.active and bpy.context.object.data.attributes.active.data_type == "FLOAT":
            row.prop(wm, "atri_float_value", text="Float Value")
        if bpy.context.object.data.attributes.active and bpy.context.object.data.attributes.active.data_type == "FLOAT_COLOR":
            row.operator("object.ml_atri_op", text="Assign").type = "Assign"
            row.operator("object.ml_atri_op", text="Remove").type = "Remove"
            row.prop(wm, "atri_float_color_value", text="")

        row = layout.row(align=True)
        row.operator("object.ml_atri_op", text="Vertex Group", icon="VERTEXSEL").type = "Vertex"
        row.operator("object.ml_atri_op", text="Edge Group", icon="EDGESEL").type = "Edge"
        row.operator("object.ml_atri_op", text="Face Group", icon="FACESEL").type = "Face"



class AtriOP(bpy.types.Operator):
    bl_idname = "object.ml_atri_op"
    bl_label = "Attribute Operations"
    bl_description = "Atributte Operations"
    bl_options = {'REGISTER', 'UNDO'}

    type: bpy.props.StringProperty(default="") # type:ignore

    @classmethod
    def poll(cls, context):
        return context.active_object is not None and context.active_object.mode == 'EDIT'

    def execute(self, context):
        wm = context.window_manager
        sel_mode = context.tool_settings.mesh_select_mode[:]
        active_type = bpy.context.object.data.attributes.active
        if self.type == "Assign":
            if active_type and active_type.data_type == "BOOLEAN":
                bpy.ops.mesh.attribute_set('EXEC_DEFAULT', True, value_bool=True)
            if active_type and active_type.data_type == "FLOAT":
                bpy.ops.mesh.attribute_set('EXEC_DEFAULT', True, value_float=wm.atri_float_value)
            if active_type and active_type.data_type == "FLOAT_COLOR":
                bpy.ops.mesh.attribute_set('EXEC_DEFAULT', True, value_color=wm.atri_float_color_value)
        elif self.type == "Remove":
            if active_type and active_type.data_type == "BOOLEAN":
                bpy.ops.mesh.attribute_set('EXEC_DEFAULT', True, value_bool=False)
            if active_type and active_type.data_type == "FLOAT":
                bpy.ops.mesh.attribute_set('EXEC_DEFAULT', True, value_float=0.0)
            if active_type and active_type.data_type == "FLOAT_COLOR":
                bpy.ops.mesh.attribute_set('EXEC_DEFAULT', True, value_color=(0.0, 0.0, 0.0, 0.0))
        elif self.type == "Select":
            # need to change to the select mode first of the attribute, otherwise it will not work
            if active_type and active_type.domain == "POINT":
                context.tool_settings.mesh_select_mode = (True, False, False)
            elif active_type and active_type.domain == "EDGE":
                context.tool_settings.mesh_select_mode = (False, True, False)
            elif active_type and active_type.domain == "FACE":
                context.tool_settings.mesh_select_mode = (False, False, True)
            bpy.ops.mesh.select_by_attribute()
           

        elif self.type == "Vertex":
            context.tool_settings.mesh_select_mode = (True, False, False)
            bpy.ops.geometry.attribute_add(name="Vertex_Group", data_type='BOOLEAN', domain='POINT')
            bpy.ops.object.ml_atri_op(type="Assign")
            context.tool_settings.mesh_select_mode = (sel_mode[0], sel_mode[1], sel_mode[2])
        elif self.type == "Edge":
            context.tool_settings.mesh_select_mode = (False, True, False)
            bpy.ops.geometry.attribute_add(name="Edge_Group", data_type='BOOLEAN', domain='EDGE')
            bpy.ops.object.ml_atri_op(type="Assign")
            context.tool_settings.mesh_select_mode = (sel_mode[0], sel_mode[1], sel_mode[2])
        elif self.type == "Face":
            context.tool_settings.mesh_select_mode = (False, False, True)
            bpy.ops.geometry.attribute_add(name="Face_Group", data_type='BOOLEAN', domain='FACE')
            bpy.ops.object.ml_atri_op(type="Assign")
            context.tool_settings.mesh_select_mode = (sel_mode[0], sel_mode[1], sel_mode[2])

        return {'FINISHED'}

def register():
    bpy.types.WindowManager.atri_float_value = bpy.props.FloatProperty(name="Float Value", default=1.0, update=update_atri_float_value)
    bpy.types.WindowManager.atri_float_color_value = bpy.props.FloatVectorProperty(size=4, subtype="COLOR", name="Float Color Value", default=(1.0, 1.0, 1.0, 1.0), min=0.0, max=1.0, update=atri_update_float_color_value)

def unregister():
    del bpy.types.WindowManager.atri_float_value
    del bpy.types.WindowManager.atri_float_color_value


