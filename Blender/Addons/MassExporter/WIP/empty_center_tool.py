import bpy
from bpy.types import Panel, Operator
from bpy.props import StringProperty

# Operator to center selected empty to origin
class OBJECT_OT_center_empty_to_origin(Operator):
    """Center selected empty object to origin (0,0,0)"""
    bl_idname = "object.center_empty_to_origin"
    bl_label = "Center Empty to Origin"
    bl_options = {'REGISTER', 'UNDO'}
    
    @classmethod
    def poll(cls, context):
        return context.active_object is not None
    
    def execute(self, context):
        obj = context.active_object
        
        # Check if object is selected and is an empty
        if obj and obj.select_get() and obj.type == 'EMPTY':
            # Set location to origin
            obj.location = (0.0, 0.0, 0.0)
            self.report({'INFO'}, f"Centered '{obj.name}' to origin")
            return {'FINISHED'}
        else:
            self.report({'WARNING'}, "Please select an Empty object")
            return {'CANCELLED'}

# Panel for the N panel menu
class VIEW3D_PT_empty_tools(Panel):
    """Creates a Panel in the N-Panel"""
    bl_label = "Empty Tools"
    bl_idname = "VIEW3D_PT_empty_tools"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Empty Tools"
    
    def draw(self, context):
        layout = self.layout
        
        # Add some info text
        layout.label(text="Empty Object Tools:")
        
        # Add the center button
        row = layout.row()
        row.scale_y = 1.5
        row.operator("object.center_empty_to_origin", text="Center Empty to Origin", icon='EMPTY_AXIS')
        
        # Show info about selected object
        if context.active_object:
            obj = context.active_object
            box = layout.box()
            box.label(text=f"Selected: {obj.name}")
            box.label(text=f"Type: {obj.type}")
            if obj.type == 'EMPTY':
                box.label(text=f"Location: {obj.location.x:.2f}, {obj.location.y:.2f}, {obj.location.z:.2f}")
            else:
                box.label(text="Select an Empty object", icon='INFO')

# Registration
def register():
    bpy.utils.register_class(OBJECT_OT_center_empty_to_origin)
    bpy.utils.register_class(VIEW3D_PT_empty_tools)

def unregister():
    bpy.utils.unregister_class(OBJECT_OT_center_empty_to_origin)
    bpy.utils.unregister_class(VIEW3D_PT_empty_tools)

# Register the classes
if __name__ == "__main__":
    register()
    print("Empty Tools panel registered successfully!")
