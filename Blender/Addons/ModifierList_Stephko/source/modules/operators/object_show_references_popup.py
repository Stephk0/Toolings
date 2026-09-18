import bpy
from ..utils import get_ml_active_object


def find_object_references_modifiers(target_obj):
    references = set()

    for obj in bpy.data.objects:
        # Modifiers
        for mod in obj.modifiers:
            if hasattr(mod, "object") and mod.object == target_obj:
                references.add((obj, f"Modifier: {mod.name}"))

        # Geometry Nodes
        for mod in obj.modifiers:
            if mod.type == 'NODES' and hasattr(mod, "node_group") and mod.node_group:
                for node in mod.node_group.nodes:
                    if hasattr(node, "inputs"):
                        for input_socket in node.inputs:
                            if input_socket.type == 'OBJECT' and input_socket.default_value == target_obj:
                                references.add((obj, f"Geometry Nodes: {mod.name}, Node: {node.name}"))

        # # Parent
        # if obj.parent == target_obj:
        #     references.add((obj, "Parented To"))

        # # Children
        # if target_obj.parent == obj:
        #     references.add((obj, "Child Of"))

    return references

def find_parent_references(target_obj):
    references = set()

    def recursive_find_parents(obj):
        if obj.parent:
            references.add((obj.parent, "Parented To"))
            recursive_find_parents(obj.parent)

    recursive_find_parents(target_obj)
    return references


def find_child_references(target_obj):
    references = set()

    def recursive_find_children(obj):
        for child in obj.children:
            references.add((child, "Child Of"))
            recursive_find_children(child)

    recursive_find_children(target_obj)
    return references


class OBJECT_OT_ShowReferencesPopup(bpy.types.Operator):
    bl_idname = "object.show_references_popup"
    bl_label = "Object References"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        return {'FINISHED'}

    def invoke(self, context, event):
        wm = context.window_manager
        return wm.invoke_popup(self, width=400)

    def draw(self, context):
        layout = self.layout
        obj = get_ml_active_object()
        if not obj:
            layout.label(text="No active object found.")
            return
        
        references = find_object_references_modifiers(obj)
        # print(references)

        layout.label(text=f"References to: {obj.name}", icon='OBJECT_DATA')

        box = layout.box()
        box.label(text="Modifiers:")
        if not references:
            box.label(text="No references found.")
        
        displayed_objects = set()

        for ref_obj, relation in references:
            if ref_obj in displayed_objects:
                continue
            displayed_objects.add(ref_obj)

            box2 = box.box()
            row = box2.row(align=True)
            row.label(text=f"{ref_obj.name}", icon='OBJECT_DATA')
            row.alignment = 'LEFT'
            row.operator("object.ml_select", text="Select", icon='RESTRICT_SELECT_OFF').object_name = ref_obj.name

            # Ensure modifiers are only shown once per object
            if hasattr(ref_obj, "modifiers"):
                for mod in ref_obj.modifiers:
                    if hasattr(mod, "object") and mod.object == obj:
                        mod_row = box2.row()
                        mod_row.label(icon=bpy.types.Modifier.bl_rna.properties['type'].enum_items[mod.type].icon)
                        mod_row.label(text=f"Modifier: {mod.name}")
                        mod_row.prop(mod, "show_viewport", text="Show Viewport", toggle=True)

                    # # Handle Geometry Nodes
                    # if mod.type == 'NODES' and hasattr(mod, "node_group") and mod.node_group:
                    #     for node in mod.node_group.nodes:
                    #             for input_socket in node.inputs:
                    #                 if input_socket.type == 'OBJECT':
                    #                     print(input_socket)
                    #                     if input_socket.default_value == obj:
                    #                         node_row = box2.row()
                    #                         node_row.label(icon='NODETREE')
                    #                         node_row.label(text=f"{mod.name}, Node: {node.name}")
                    #                         node_row.prop(input_socket, "default_value", text="Object", icon='OBJECT_DATA')
        displayed_objects = set()

        parants = find_parent_references(obj)
        if parants:
            box = layout.box()
            box.label(text="Children:")
            for ref_obj, relation in parants:
                if ref_obj in displayed_objects:
                    continue
                displayed_objects.add(ref_obj)

                box = box.box()
                row = box.row(align=True)
                row.label(text=f"{ref_obj.name}", icon='OBJECT_DATA')
                row.alignment = 'LEFT'
                row.operator("object.ml_select", text="Select", icon='RESTRICT_SELECT_OFF').object_name = ref_obj.name

        displayed_objects = set()

        children = find_child_references(obj)
        if children:
            box = layout.box()
            box.label(text="Parented To:")
            for ref_obj, relation in children:
                if ref_obj in displayed_objects:
                    continue
                displayed_objects.add(ref_obj)

                box = box.box()
                row = box.row(align=True)
                row.label(text=f"{ref_obj.name}", icon='OBJECT_DATA')
                row.alignment = 'LEFT'
                row.operator("object.ml_select", text="Select", icon='RESTRICT_SELECT_OFF').object_name = ref_obj.name


class OBJECT_OT_UnparentCustom(bpy.types.Operator):
    bl_idname = "object.unparent_custom"
    bl_label = "Unparent Object"

    target: bpy.props.StringProperty()

    def execute(self, context):
        obj = bpy.data.objects[self.target]
        obj.parent = None
        self.report({'INFO'}, f"Unparented {obj.name}")
        return {'FINISHED'}
