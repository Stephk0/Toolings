# import bpy
# import bmesh
# from ... import __package__ as base_package

# from ..utils import get_ml_active_object, is_edit_mesh_modifier

# def edit_mesh_node_group():
#     edit_mesh = bpy.data.node_groups.new(type = 'GeometryNodeTree', name = "Edit Mesh")

#     edit_mesh.color_tag = 'NONE'
#     edit_mesh.description = ""
#     edit_mesh.is_modifier = True

#     #edit_mesh interface
#     #Socket Geometry
#     geometry_socket = edit_mesh.interface.new_socket(name = "Geometry", in_out='OUTPUT', socket_type = 'NodeSocketGeometry')
#     geometry_socket.attribute_domain = 'POINT'

#     #Socket Geometry
#     geometry_socket_1 = edit_mesh.interface.new_socket(name = "Geometry", in_out='INPUT', socket_type = 'NodeSocketGeometry')
#     geometry_socket_1.attribute_domain = 'POINT'


#     #initialize edit_mesh nodes
#     #node Group Input
#     group_input = edit_mesh.nodes.new("NodeGroupInput")
#     group_input.name = "Group Input"

#     #Socket Index
#     index_socket = edit_mesh.interface.new_socket(name = "Index", in_out='INPUT', socket_type = 'NodeSocketInt')
#     index_socket.default_value = 0
#     index_socket.min_value = -2147483648
#     index_socket.max_value = 2147483647
#     index_socket.subtype = 'NONE'
#     index_socket.attribute_domain = 'POINT'
   
    
#     #node Group Output
#     group_output = edit_mesh.nodes.new("NodeGroupOutput")
#     group_output.name = "Group Output"
#     group_output.is_active_output = True

#     #Set locations
#     group_input.location = (-340.0, 0.0)
#     group_output.location = (200.0, 0.0)

#     #Set dimensions
#     group_input.width, group_input.height = 140.0, 100.0
#     group_output.width, group_output.height = 140.0, 100.0

#     #initialize edit_mesh links
#     #group_input.Geometry -> group_output.Geometry
#     edit_mesh.links.new(group_input.outputs[0], group_output.inputs[0])
#     return edit_mesh

# def apply_modifiers(obj):
#     if obj:
#         if obj.type == 'MESH':
#             depsgraph = bpy.context.evaluated_depsgraph_get()
#             object_eval = obj.evaluated_get(depsgraph)
#             mesh_from_eval = bpy.data.meshes.new_from_object(object_eval, depsgraph=depsgraph)

#             if obj.mode == 'EDIT':
#                 bm = bmesh.from_edit_mesh(obj.data)
#                 bm.clear()
#                 bm.from_mesh(mesh_from_eval)
#                 bmesh.update_edit_mesh(obj.data)
#             else:
#                 obj.data = mesh_from_eval

#             for mod in obj.modifiers:
#                 # hide all modifiers
#                 mod.show_viewport = False
#                 mod.show_render = False

#             active_object = obj

#         elif obj.type == 'CURVE':
#             name = obj.name
        
#             object_collection = obj.users_collection[0]

#             object_eval = obj.evaluated_get(depsgraph)
#             mesh_from_eval = bpy.data.meshes.new_from_object(object_eval, depsgraph=depsgraph)

#             new_obj = bpy.data.objects.new("temp_mesh", mesh_from_eval)
#             object_collection.objects.link(new_obj)

#             new_obj.matrix_world = obj.matrix_world
#             new_obj.select_set(True)
#             bpy.data.objects.remove(obj)

#             new_obj.name = name # restore the original name

#             if obj == active_object:  #set the new object as active if the old object was active
#                 active_object = new_obj
    
#         #clear the evaluated mesh
#         object_eval.to_mesh_clear()
#         bpy.context.view_layer.objects.active = active_object
#         return active_object

# def draw_edit_mesh_modifier(self, context):
#     prefs = bpy.context.preferences.addons[base_package].preferences
#     obj = context.active_object
#     # only works in list mode
#     if prefs.properties_editor_style == 'LIST' and obj and obj.type == 'MESH':
#         layout = self.layout
#         layout.operator("object.edit_mesh_modifier", icon='EDITMODE_HLT')
# ev = []
# def create_mesh_backup(obj, create_new_modifier=True, object_index=None, after_active_modifier=False):   
#     global ev

#     if obj.mode == 'EDIT':
#         obj.update_from_editmode()  #update mesh data, so it works in edit mode
    
#     backup_mesh_data = obj.data.copy()
#     backup_mesh_data.use_fake_user = True
#     base_name = obj.data.name.split("_edit_mesh_")[0]
#     backup_mesh_data.name = base_name + "_edit_mesh_" + str(len([block for block in bpy.data.meshes if block.name.startswith(base_name + "_edit_mesh_")]))

#     # add obj.data as a new object data block, to be used as backup keeping the original mesh data
#     index = 0
#     while "edit_mesh_data_" + str(index) in obj:
#         index += 1
    
#     # Create a custom property for the object
#     if object_index is None:
#         prop_name = "edit_mesh_data_" +  str(index)
#         setattr(bpy.types.Object, prop_name, bpy.props.PointerProperty(
#             name="Edit Mesh Data" + str(index), 
#             description=str(index),
#             type=bpy.types.Mesh
#         ))
#         # Assign the custom property to the object
#         setattr(obj, prop_name, backup_mesh_data)

#     else:
#         prop_name = "edit_mesh_data_" + str(object_index)
#         # update the existing object property using the new backuop data
#         if prop_name in obj:
#             data = (obj[prop_name])
#             if data:
#                 # update the mesh data to the current mesh data
#                 obj[prop_name] = backup_mesh_data # update the object property to the new backup data
#                 # obj.data = backup_mesh_data # set the mesh data to the new backup data
#         return
#     mod_is_visiable = []

#     if "CTRL" in ev or after_active_modifier:
#         active_mod_index = obj.ml_modifier_active_index
#         modifier_index_map = {mod: i for i, mod in enumerate(obj.modifiers)}

#         for mod in reversed(obj.modifiers):
#             if modifier_index_map[mod] == active_mod_index:
#                 break
#             if mod.show_viewport:
#                 mod_is_visiable.append(mod)
#             mod.show_viewport = False
#             mod.show_render = False
    
#     obj = apply_modifiers(obj)  # apply all modifiers with current modifers, either in edit mode or object mode

#     for mod in obj.modifiers:
#         if mod.use_pin_to_last:
#             mod.use_pin_to_last = False # set all pined modifes to unpinned, since otherwise it will be before the edit mesh modifier

#     if not "Edit Mesh" in bpy.data.node_groups:
#         edit_mesh_node_group()

#     if create_new_modifier:
#         edit_mesh_modifier = obj.modifiers.new(name="Edit Mesh", type='NODES')
#         if "CTRL" in ev: # move the edit_mesh_modifier after the active modifier
#             obj.modifiers.move(len(obj.modifiers) - 1, active_mod_index + 1)

#     # add new node group to the modifier
#         edit_mesh_modifier.node_group = bpy.data.node_groups['Edit Mesh']
#         edit_mesh_modifier.show_group_selector = False
#         edit_mesh_modifier["Socket_2"] = index # we store a index of the number of the mesh data block
#         edit_mesh_modifier.show_viewport = False

#     if mod_is_visiable:
#         for mod in mod_is_visiable:  # restore the visibility of the modifiers
#             mod.show_viewport = True
#             mod.show_render = True

# def restore_previous_mesh_data(self, context, obj):
#     active_mod_index = obj.ml_modifier_active_index
#     active_mod = obj.modifiers[active_mod_index]
#     property_index = str(active_mod["Socket_2"])

#     if obj and active_mod:
#         if active_mod.type == 'NODES':
#             if active_mod.node_group.name == "Edit Mesh":
#                 amount_of_edit_mesh_modifiers = 0
#                 old_mesh_data = obj.data

#                 obj.modifiers.remove(active_mod) # remove Edit Mesh Modifier

#                 object_mode = True
#                 if context.mode != 'OBJECT':
#                     object_mode = False
#                     bpy.ops.object.editmode_toggle()

#                 prop_name = "edit_mesh_data_" + str(property_index)  # get the obj.data index 

#                 if prop_name in obj:
#                     data = (obj[prop_name])
#                     obj.data = data # restore the original mesh data

#                     del obj[prop_name]
                    
#                     if not object_mode:
#                         bpy.ops.ed.undo_push()
#                         bpy.ops.object.editmode_toggle()
                
#                     # restore modifiers, we only do it until the next Edit Mesh Modifier!
#                     for mod in reversed(obj.modifiers):
#                         if mod.type == 'NODES':
#                             if mod.node_group and mod.node_group.name == "Edit Mesh":
#                                 break # we reached another Edit Mesh mod, break loop
#                             else:
#                                 mod.show_viewport = True
#                                 mod.show_render = True
#                         else:
#                             mod.show_viewport = True
#                             mod.show_render = True

#                     # if not used by another object, delete the old mesh data
#                     if data.users == 1 or data.users == 0:
#                         bpy.data.meshes.remove(old_mesh_data) # delete old mesh data

#                 else:
#                     self.report({'ERROR'}, "No mesh data was found")
#                     return {'CANCELLED'}
                
#                 # cleanup obj properites if no edit mesh modifiers
#                 for m in obj.modifiers:
#                     if m.type == 'NODES' and m.node_group:
#                         if "Edit Mesh" in m.node_group.name:
#                             amount_of_edit_mesh_modifiers += 1
                
#                 # if no edit mesh mdifers left, cleanup and delete all edit_mesh_data_ obj properties, just in case
#                 if amount_of_edit_mesh_modifiers == 0:
#                     keys_to_delete = [prop_name for prop_name in obj.keys() if prop_name.startswith("edit_mesh_data_")]
#                     for prop_name in keys_to_delete:
#                         # old_data = (obj[prop_name]) # might not be safe, check amount of users first?
#                         # bpy.data.meshes.remove(old_data) # delete old mesh data
#                         del obj[prop_name]
#             else:
#                 self.report({'ERROR'}, "No Edit Mesh Modifier found")
#                 return {'CANCELLED'}
            
# def update_existing_backup_mesh_data_to_current_mesh_data(obj, index):
#     prop_name = "edit_mesh_data_" + str(index)
#     if prop_name in obj:
#         if obj.mode == 'EDIT':
#             obj.update_from_editmode()  # Update mesh data from edit mode
#         updated_mesh = obj.data.copy()  # Create a new mesh from the updated data
#         obj[prop_name] = updated_mesh  # Assign the new mesh to the property

# class EditmeshClear(bpy.types.Operator):
#     bl_idname = "object.edit_mesh_clear"
#     bl_label = "Clear edit mesh"
#     bl_description = "Clear edit mesh Modifier"
#     bl_options = {'REGISTER', 'UNDO'}

#     def execute(self, context):
#         obj = get_ml_active_object()
#         restore_previous_mesh_data(self, context, obj) # restore the original mesh data
#         return {'FINISHED'}

# class EditmeshModifier(bpy.types.Operator):
#     bl_idname = "object.edit_mesh_modifier"
#     bl_label = "Edit Mesh"
#     bl_description = """Adds a Edit Mesh Modifier

#     Ctrl - Add after active modifier"""
#     bl_options = {'REGISTER', 'UNDO'}

#     insert_after_active: bpy.props.BoolProperty(default=False, options={'HIDDEN', 'SKIP_SAVE'}) #type: ignore

#     def invoke(self, context, event):
#         global ev 
#         ev = []
#         if event.ctrl:
#             ev.append("CTRL")
        
#         return self.execute(context)

#     def execute(self, context):
#         obj = get_ml_active_object()
#         create_mesh_backup(obj) # create a backup of the mesh data
#         return {'FINISHED'}
    
# class ToggleEditMeshVisibility(bpy.types.Operator):
#     bl_idname = "object.toggle_edit_mesh_visibility"
#     bl_label = "Toggle Edit Mesh Visibility"
#     bl_description = "Toggle Edit Mesh Modifier Visibility"
#     bl_options = {'REGISTER', 'UNDO'}

#     mod_name: bpy.props.StringProperty(options={'HIDDEN'}) # type: ignore
#     delete_edit_mesh: bpy.props.BoolProperty(default=False, options={'HIDDEN', 'SKIP_SAVE'}) # type: ignore

#     def execute(self, context):
#         obj = get_ml_active_object()
#         amount_of_edit_mesh_modifiers = 0

#         current_active_edit_mesh_modifier = None
#         for mod in reversed(obj.modifiers):
#             if mod.type == 'NODES':
#                 if mod.node_group and mod.node_group.name == "Edit Mesh" and mod.show_render:
#                     current_active_edit_mesh_modifier = mod
#                     break

#         if self.delete_edit_mesh:
#             for m in obj.modifiers:
#                 if m.type == 'NODES' and m.node_group:
#                     if "Edit Mesh" in m.node_group.name:
#                         amount_of_edit_mesh_modifiers += 1

#             active_modifier = obj.modifiers.active
#             for mod in reversed(obj.modifiers):
#                 if mod.type == 'NODES':
#                     if mod.node_group and mod.node_group.name == "Edit Mesh" and mod != active_modifier or amount_of_edit_mesh_modifiers == 1:
#                         self.mod_name = mod.name
#                         break

#             # remove the mesh data and the object property
#             prop_name = "edit_mesh_data_" + str(active_modifier["Socket_2"])
#             if prop_name in obj:
#                 data = (obj[prop_name])
#                 if data:
#                     # if not used by another object, delete the old mesh data
#                     if data.users == 1 or data.users == 0:
#                         bpy.data.meshes.remove(data)
#                     del obj[prop_name]
#             if amount_of_edit_mesh_modifiers != 1:
#                 obj.modifiers.remove(active_modifier) # remove Edit Mesh Modifier

#         if self.mod_name:
#             active_mod = self.mod_name
#             active_mod = obj.modifiers[active_mod] 

#         if not active_mod.show_render:
#             if current_active_edit_mesh_modifier:
#                 update_existing_backup_mesh_data_to_current_mesh_data(obj, current_active_edit_mesh_modifier["Socket_2"])

#             if is_edit_mesh_modifier(active_mod):
#                 current_active_mesh_data_index = 0
#                 for mod in obj.modifiers:
#                     if is_edit_mesh_modifier(mod) and mod.show_render:
#                         current_active_mesh_data_index = mod["Socket_2"]
#                         break
#             if self.delete_edit_mesh:
#                 current_active_mesh_data_index = -1

#             for mod in obj.modifiers:
#                 if is_edit_mesh_modifier(mod) and not mod == active_mod:
#                     mod.show_viewport = False
#                     mod.show_render = False

#             # create_mesh_backup(obj, create_new_modifier=False, object_index=current_active_mesh_data_index, after_active_modifier=True)
#             active_mod.show_viewport = True
#             active_mod.show_render = True
#             # set the mesh data to the active modifier backup mesh data
#             prop_name = "edit_mesh_data_" + str(active_mod["Socket_2"])
#             if prop_name in obj:
#                 data = (obj[prop_name])
#                 obj.data = data
#         else:
#             update_existing_backup_mesh_data_to_current_mesh_data(obj, active_mod["Socket_2"])

#             active_mod.show_viewport = False
#             active_mod.show_render = False

#             # revert back to the first backup mesh data
#             for mod in obj.modifiers:
#                 if is_edit_mesh_modifier(mod):
#                     if mod["Socket_2"] == 0:
#                         prop_name = "edit_mesh_data_" + str(mod["Socket_2"])
#                         if prop_name in obj:
#                             data = (obj[prop_name])
#                             obj.data = data
#                             break
#         if amount_of_edit_mesh_modifiers == 1:
#             obj.modifiers.remove(active_modifier) # remove Edit Mesh Modifier

#         return {'FINISHED'}
        
# def register():
#     bpy.types.OBJECT_MT_modifier_add_edit.prepend(draw_edit_mesh_modifier)

# def unregister():
#     bpy.types.OBJECT_MT_modifier_add_edit.remove(draw_edit_mesh_modifier)

import bpy
import bmesh
from ... import __package__ as base_package

def edit_mesh_node_group():
    edit_mesh = bpy.data.node_groups.new(type = 'GeometryNodeTree', name = "Edit Mesh")

    edit_mesh.color_tag = 'NONE'
    edit_mesh.description = ""
    edit_mesh.is_modifier = True

    #edit_mesh interface
    #Socket Geometry
    geometry_socket = edit_mesh.interface.new_socket(name = "Geometry", in_out='OUTPUT', socket_type = 'NodeSocketGeometry')
    geometry_socket.attribute_domain = 'POINT'

    #Socket Geometry
    geometry_socket_1 = edit_mesh.interface.new_socket(name = "Geometry", in_out='INPUT', socket_type = 'NodeSocketGeometry')
    geometry_socket_1.attribute_domain = 'POINT'


    #initialize edit_mesh nodes
    #node Group Input
    group_input = edit_mesh.nodes.new("NodeGroupInput")
    group_input.name = "Group Input"

    #Socket Index
    index_socket = edit_mesh.interface.new_socket(name = "Index", in_out='INPUT', socket_type = 'NodeSocketInt')
    index_socket.default_value = 0
    index_socket.min_value = -2147483648
    index_socket.max_value = 2147483647
    index_socket.subtype = 'NONE'
    index_socket.attribute_domain = 'POINT'
   
    
    #node Group Output
    group_output = edit_mesh.nodes.new("NodeGroupOutput")
    group_output.name = "Group Output"
    group_output.is_active_output = True

    #Set locations
    group_input.location = (-340.0, 0.0)
    group_output.location = (200.0, 0.0)

    #Set dimensions
    group_input.width, group_input.height = 140.0, 100.0
    group_output.width, group_output.height = 140.0, 100.0

    #initialize edit_mesh links
    #group_input.Geometry -> group_output.Geometry
    edit_mesh.links.new(group_input.outputs[0], group_output.inputs[0])
    return edit_mesh

def apply_modifiers(obj):
    if obj:
        if obj.type == 'MESH':
            depsgraph = bpy.context.evaluated_depsgraph_get()
            object_eval = obj.evaluated_get(depsgraph)
            mesh_from_eval = bpy.data.meshes.new_from_object(object_eval, depsgraph=depsgraph)

            if obj.mode == 'EDIT':
                bm = bmesh.from_edit_mesh(obj.data)
                bm.clear()
                bm.from_mesh(mesh_from_eval)
                bmesh.update_edit_mesh(obj.data)
            else:
                obj.data = mesh_from_eval

            for mod in obj.modifiers:
                # hide all modifiers
                mod.show_viewport = False
                mod.show_render = False

            active_object = obj

        elif obj.type == 'CURVE':
            name = obj.name
        
            object_collection = obj.users_collection[0]

            object_eval = obj.evaluated_get(depsgraph)
            mesh_from_eval = bpy.data.meshes.new_from_object(object_eval, depsgraph=depsgraph)

            new_obj = bpy.data.objects.new("temp_mesh", mesh_from_eval)
            object_collection.objects.link(new_obj)

            new_obj.matrix_world = obj.matrix_world
            new_obj.select_set(True)
            bpy.data.objects.remove(obj)

            new_obj.name = name # restore the original name

            if obj == active_object:  #set the new object as active if the old object was active
                active_object = new_obj
    
        #clear the evaluated mesh
        object_eval.to_mesh_clear()
        bpy.context.view_layer.objects.active = active_object
        return active_object

def draw_edit_mesh_modifier(self, context):
    prefs = bpy.context.preferences.addons[base_package].preferences
    obj = context.active_object
    # only works in list mode
    if prefs.properties_editor_style == 'LIST' and obj and obj.type == 'MESH':
        layout = self.layout
        layout.operator("object.edit_mesh_modifier", icon='EDITMODE_HLT')
class EditmeshClear(bpy.types.Operator):
    bl_idname = "object.edit_mesh_clear"
    bl_label = "Clear edit mesh"
    bl_description = "Clear edit mesh Modifier"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        obj = context.active_object
        active_mod_index = obj.ml_modifier_active_index
        active_mod = obj.modifiers[active_mod_index]
        property_index = str(active_mod["Socket_2"])

        if obj and active_mod:
            if active_mod.type == 'NODES':
                if active_mod.node_group.name == "Edit Mesh":
                    amount_of_edit_mesh_modifiers = 0
                    old_mesh_data = obj.data

                    obj.modifiers.remove(active_mod) # remove Edit Mesh Modifier

                    object_mode = True
                    if context.mode != 'OBJECT':
                        object_mode = False
                        bpy.ops.object.editmode_toggle()

                    prop_name = "edit_mesh_data_" + str(property_index)  # get the obj.data index 

                    if prop_name in obj:
                        data = (obj[prop_name])
                        obj.data = data # restore the original mesh data

                        del obj[prop_name]
                        
                        if not object_mode:
                            bpy.ops.ed.undo_push()
                            bpy.ops.object.editmode_toggle()
                      
                        # restore modifiers, we only do it until the next Edit Mesh Modifier!
                        for mod in reversed(obj.modifiers):
                            if mod.type == 'NODES':
                                if mod.node_group and mod.node_group.name == "Edit Mesh":
                                    break # we reached another Edit Mesh mod, break loop
                                else:
                                    mod.show_viewport = True
                                    mod.show_render = True
                            else:
                                mod.show_viewport = True
                                mod.show_render = True

                        # if not used by another object, delete the old mesh data
                        if data.users == 1 or data.users == 0:
                            bpy.data.meshes.remove(old_mesh_data) # delete old mesh data

                    else:
                        self.report({'ERROR'}, "No mesh data was found")
                        return {'CANCELLED'}
                    
                    # cleanup obj properites if no edit mesh modifiers
                    for m in obj.modifiers:
                        if m.type == 'NODES' and m.node_group:
                            if "Edit Mesh" in m.node_group.name:
                                amount_of_edit_mesh_modifiers += 1
                    
                    # if no edit mesh mdifers left, cleanup and delete all edit_mesh_data_ obj properties, just in case
                    if amount_of_edit_mesh_modifiers == 0:
                        for prop_name in obj.keys():
                            if prop_name.startswith("edit_mesh_data_"):
                                # old_data = (obj[prop_name]) # might not be safe, check amount of users first?
                                # bpy.data.meshes.remove(old_data) # delete old mesh data
                                del obj[prop_name]
   
        return {'FINISHED'}

class EditmeshModifier(bpy.types.Operator):
    bl_idname = "object.edit_mesh_modifier"
    bl_label = "Edit Mesh"
    bl_description = """Adds a Edit Mesh Modifier

    Ctrl - Add after active modifier
    Alt - Add to all selected objects"""
    bl_options = {'REGISTER', 'UNDO'}

    insert_after_active: bpy.props.BoolProperty(default=False, options={'HIDDEN', 'SKIP_SAVE'}) #type: ignore
    use_selected_objects: bpy.props.BoolProperty(default=False, options={'HIDDEN', 'SKIP_SAVE'}) # type: ignore

    def invoke(self, context, event):
        global ev 
        ev = []
        if event.ctrl:
            self.insert_after_active = True
            ev.append("CTRL")
        if event.alt:
            self.use_selected_objects = True
            ev.append("ALT")
        
        return self.execute(context)

    def execute(self, context):
        global ev
        if not context.active_object:
            self.report({'ERROR'}, "No active object found")
            return {'CANCELLED'}
        
        active = context.active_object
        selected = {active}
        if self.use_selected_objects:
            selected.update(context.selected_objects)
            
        for obj in selected:
            if obj.type != 'MESH':
                continue
            if obj.mode == 'EDIT':
                obj.update_from_editmode()  #update mesh data, so it works in edit mode
            
            backup_mesh_data = obj.data.copy()
            backup_mesh_data.use_fake_user = True
            base_name = obj.data.name.split("_edit_mesh_")[0]
            backup_mesh_data.name = base_name + "_edit_mesh_" + str(len([block for block in bpy.data.meshes if block.name.startswith(base_name + "_edit_mesh_")]))

            # add obj.data as a new object data block, to be used as backup keeping the original mesh data
            index = 0
            while "edit_mesh_data_" + str(index) in obj:
                index += 1
            
            # Create a custom property for the object
            prop_name = "edit_mesh_data_" +  str(index)
            setattr(bpy.types.Object, prop_name, bpy.props.PointerProperty(
                name="Edit Mesh Data" + str(index), 
                description=str(index),
                type=bpy.types.Mesh
            ))
            
            # Assign the custom property to the object
            obj[prop_name] = backup_mesh_data

            mod_is_visiable = []

            if self.insert_after_active or "CTRL" in ev:
                active_mod_index = obj.ml_modifier_active_index
                modifier_index_map = {mod: i for i, mod in enumerate(obj.modifiers)}

                for mod in reversed(obj.modifiers):
                    if modifier_index_map[mod] == active_mod_index:
                        break
                    if mod.show_viewport:
                        mod_is_visiable.append(mod)
                    mod.show_viewport = False
                    mod.show_render = False
            
            obj = apply_modifiers(obj)  # apply all modifiers with current modifers, either in edit mode or object mode

            for mod in obj.modifiers:
                if mod.use_pin_to_last:
                    mod.use_pin_to_last = False # set all pined modifes to unpinned, since otherwise it will be before the edit mesh modifier

            if not "Edit Mesh" in bpy.data.node_groups:
                edit_mesh_node_group()

            edit_mesh_modifier = obj.modifiers.new(name="Edit Mesh", type='NODES')
            if "CTRL" in ev: # move the edit_mesh_modifier after the active modifier
                obj.modifiers.move(len(obj.modifiers) - 1, active_mod_index + 1)

            # add new node group to the modifier
            edit_mesh_modifier.node_group = bpy.data.node_groups['Edit Mesh']
            edit_mesh_modifier.show_group_selector = False
            edit_mesh_modifier["Socket_2"] = index # we store a index of the number of the mesh data block
            edit_mesh_modifier.show_viewport = False

            if mod_is_visiable:
                for mod in mod_is_visiable:  # restore the visibility of the modifiers
                    mod.show_viewport = True
                    mod.show_render = True
        return {'FINISHED'}
        
    def register():
        bpy.types.OBJECT_MT_modifier_add_edit.prepend(draw_edit_mesh_modifier)

    def unregister():
        bpy.types.OBJECT_MT_modifier_add_edit.remove(draw_edit_mesh_modifier)

