# import bpy
# from ...modules import modifier_categories

# def ml_modifier_add_menu(self, context):
#     layout = self.layout
#     col = layout.column(align=True)

#     # Add a separator between the two sections
#     col.separator()

#     # Add the Edit Mesh modifier to the menu
#     col.menu(MLNewModifierAddMenu.bl_idname, text="Modifier List")

    
# # ML menu class
# class MLNewModifierAddMenu(bpy.types.Menu):
#     bl_label = "ML New Modifier Add Menu"
#     bl_idname = "OBJECT_MT_ml_modifier_add_menu"

#     def draw(self, context):
#         layout = self.layout

#         col = layout.column(align=True)
#         col.label(text="ML Modifiers")
#         col.separator()

#         for modifier_type in modifier_categories.MESH_ALL_NAMES_ICONS_TYPES:
#             modifier_name, modifier_icon, modifier_type = modifier_type
#             col.operator("object.ml_modifier_add", text=modifier_name, icon=modifier_icon).modifier_type = modifier_type

# def register():
#     bpy.types.OBJECT_MT_modifier_add.append(ml_modifier_add_menu)

# def unregister():
#     bpy.types.OBJECT_MT_modifier_add.remove(ml_modifier_add_menu)
