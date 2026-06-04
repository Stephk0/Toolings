bl_info = {
    "name": "Smart Collapse",
    "author": "Stephan Viranyi + Claude",
    "version": (1, 0, 0),
    "blender": (4, 0, 0),
    "location": "View3D > Edit Mode > Mesh Menu > Delete > Smart Collapse",
    "description": "Intelligently collapses edges or merges vertices at center based on topology",
    "warning": "",
    "doc_url": "https://github.com/Stephk0/Toolings",
    "category": "Mesh",
}

import bpy
import bmesh
from bpy.types import Operator


class MESH_OT_smart_collapse(Operator):
    """Smart Collapse: Collapse edges if topology exists, otherwise merge at center"""
    bl_idname = "mesh.smart_collapse"
    bl_label = "Smart Collapse"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return (context.mode == 'EDIT_MESH' and 
                context.active_object and 
                context.active_object.type == 'MESH')

    def execute(self, context):
        obj = context.active_object
        mesh = obj.data
        bm = bmesh.from_edit_mesh(mesh)
        
        # Get selected vertices
        selected_verts = [v for v in bm.verts if v.select]
        selected_edges = [e for e in bm.edges if e.select]
        
        if len(selected_verts) < 2:
            self.report({'WARNING'}, "Select at least 2 vertices")
            return {'CANCELLED'}
        
        # Try to determine if there's topology between selected elements
        # Check if selected edges exist - if they do, we have topology
        has_topology = len(selected_edges) > 0
        
        # Additional check: see if selected vertices are connected
        if not has_topology and len(selected_verts) == 2:
            # Check if these two vertices share an edge
            v1, v2 = selected_verts[0], selected_verts[1]
            for edge in v1.link_edges:
                if edge.other_vert(v1) == v2:
                    has_topology = True
                    break
        
        if has_topology:
            # There's topology - try standard collapse
            try:
                # Use Blender's collapse operator
                bpy.ops.mesh.merge(type='COLLAPSE')
                self.report({'INFO'}, "Collapsed with topology")
                return {'FINISHED'}
            except Exception as e:
                # If collapse fails, fall back to merge at center
                self.report({'WARNING'}, f"Collapse failed, merging at center: {str(e)}")
                bpy.ops.mesh.merge(type='CENTER')
                return {'FINISHED'}
        else:
            # No topology between vertices - merge at center
            bpy.ops.mesh.merge(type='CENTER')
            self.report({'INFO'}, "Merged at center (no topology)")
            return {'FINISHED'}


def menu_func(self, context):
    """Add operator to Delete menu"""
    self.layout.operator(MESH_OT_smart_collapse.bl_idname, icon='AUTOMERGE_ON')


# Keymap
addon_keymaps = []


def register():
    bpy.utils.register_class(MESH_OT_smart_collapse)
    
    # Add to Delete menu
    bpy.types.VIEW3D_MT_edit_mesh_delete.append(menu_func)
    
    # Add keymap
    wm = bpy.context.window_manager
    kc = wm.keyconfigs.addon
    if kc:
        km = kc.keymaps.new(name='Mesh', space_type='EMPTY')
        kmi = km.keymap_items.new(MESH_OT_smart_collapse.bl_idname, 'X', 'PRESS', ctrl=True, alt=True)
        addon_keymaps.append((km, kmi))


def unregister():
    # Remove keymap
    for km, kmi in addon_keymaps:
        km.keymap_items.remove(kmi)
    addon_keymaps.clear()
    
    # Remove from Delete menu
    bpy.types.VIEW3D_MT_edit_mesh_delete.remove(menu_func)
    
    bpy.utils.unregister_class(MESH_OT_smart_collapse)


if __name__ == "__main__":
    register()
