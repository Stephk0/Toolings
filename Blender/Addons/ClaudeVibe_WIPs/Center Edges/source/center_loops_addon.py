bl_info = {
    "name": "Center Loops",
    "author": "Stephko, Claude AI",
    "version": (1, 5, 1),
    "blender": (2, 80, 0),
    "location": "Edit Mode > Edge Menu, Context Menu, Hotkey (Ctrl+Shift+C)",
    "description": "Center edge or vertex loops between perpendicular edges (works with tris, quads, and ngons)",
    "warning": "",
    "doc_url": "",
    "tracker_url": "",
    "category": "Mesh",
}

import bpy
import bmesh
from mathutils import Vector
from collections import defaultdict
from bpy.types import Operator
from bpy.props import EnumProperty, BoolProperty

addon_keymaps = []


def get_loop_vertices_for_vert(vert, edge, face):
    """
    For a vertex of an edge in a face, find the vertices that form the perpendicular edge loop.
    Works with any face type (tri, quad, n-gon).
    
    Args:
        vert: BMVert - The vertex to find perpendicular vertices for
        edge: BMEdge - The main edge containing the vertex
        face: BMFace - The face to search within
        
    Returns:
        list: List of BMVert objects that are perpendicular to the main edge
    """
    # Find edges in this face that connect to our vertex but aren't the main edge
    connected_edges = [e for e in face.edges if vert in e.verts and e != edge]
    
    if not connected_edges:
        return []
    
    # Get the other vertices from these edges (the perpendicular vertices)
    perp_verts = []
    for e in connected_edges:
        other_vert = e.other_vert(vert)
        if other_vert not in edge.verts:  # Make sure it's not the other vertex of our edge
            perp_verts.append(other_vert)
    
    return perp_verts


def get_edge_loop_neighbors(edge):
    """
    Get the neighboring vertices for edge loop centering.
    
    Args:
        edge: BMEdge - The edge to find neighbors for
        
    Returns:
        dict: Mapping each vertex to its perpendicular neighbors across all faces
    """
    v0, v1 = edge.verts
    neighbors = {v0: [], v1: []}
    
    # Process each adjacent face
    for face in edge.link_faces:
        # For v0
        v0_neighbors = get_loop_vertices_for_vert(v0, edge, face)
        neighbors[v0].extend(v0_neighbors)
        
        # For v1
        v1_neighbors = get_loop_vertices_for_vert(v1, edge, face)
        neighbors[v1].extend(v1_neighbors)
    
    return neighbors


def get_perpendicular_positions_for_edge(edge):
    """
    Calculate where edge vertices should be positioned based on perpendicular vertices.
    Works with triangles, quads, and n-gons.
    
    Args:
        edge: BMEdge - The edge to calculate positions for
        
    Returns:
        dict: Mapping vertices to lists of perpendicular positions
    """
    neighbors = get_edge_loop_neighbors(edge)
    positions = {}
    
    for vert, neighbor_verts in neighbors.items():
        if neighbor_verts:
            # Get unique positions (in case of duplicates)
            unique_positions = []
            seen_positions = set()
            
            for n_vert in neighbor_verts:
                pos_tuple = tuple(round(x, 6) for x in n_vert.co)
                if pos_tuple not in seen_positions:
                    seen_positions.add(pos_tuple)
                    unique_positions.append(n_vert.co.copy())
            
            if unique_positions:
                positions[vert] = unique_positions
    
    return positions


class MESH_OT_center_edge_loops(Operator):
    """Center edge loops between perpendicular edges"""
    bl_idname = "mesh.center_edge_loops"
    bl_label = "Center Loops"
    bl_description = "Center selected edge loops between their perpendicular edges"
    bl_options = {'REGISTER', 'UNDO'}
    
    centering_mode: EnumProperty(
        name="Centering Mode",
        description="How to calculate the center position",
        items=[
            ('AVERAGE', "Average", "Use average of all perpendicular vertices"),
            ('OPPOSITE_PAIRS', "Opposite Pairs", "Average pairs of opposite vertices (best for quads)"),
        ],
        default='AVERAGE'
    )

    @classmethod
    def poll(cls, context):
        """Check if operator can run"""
        return (context.active_object is not None and
                context.active_object.type == 'MESH' and
                context.mode == 'EDIT_MESH')

    def execute(self, context):
        """Main execution method"""
        obj = context.active_object
        me = obj.data
        bm = bmesh.from_edit_mesh(me)
        
        # Ensure lookup tables are valid
        bm.verts.ensure_lookup_table()
        bm.edges.ensure_lookup_table()
        bm.faces.ensure_lookup_table()

        # Get selected edges that are manifold
        selected_edges = [e for e in bm.edges if e.select and e.is_manifold]
        
        if not selected_edges:
            self.report({'WARNING'}, "No valid edges selected")
            return {'CANCELLED'}

        # Collect all position updates
        vert_positions = defaultdict(list)
        edges_processed = 0
        edge_types = defaultdict(int)  # Track face types

        for edge in selected_edges:
            # Track what types of faces we're dealing with
            for face in edge.link_faces:
                face_vert_count = len(face.verts)
                if face_vert_count == 3:
                    edge_types['triangles'] += 1
                elif face_vert_count == 4:
                    edge_types['quads'] += 1
                else:
                    edge_types['ngons'] += 1
            
            # Get the perpendicular positions
            positions = get_perpendicular_positions_for_edge(edge)
            
            if (self.centering_mode == 'OPPOSITE_PAIRS' and 
                all(len(face.verts) == 4 for face in edge.link_faces)):
                # Special handling for quad-only edges to maintain better shape
                for vert, perp_positions in positions.items():
                    if len(perp_positions) == 2:
                        # For quads with 2 perpendicular verts, just average them
                        avg_pos = (perp_positions[0] + perp_positions[1]) / 2.0
                        vert_positions[vert].append(avg_pos)
                    elif len(perp_positions) > 0:
                        # Fallback to average for other cases
                        avg_pos = sum(perp_positions, Vector()) / len(perp_positions)
                        vert_positions[vert].append(avg_pos)
            else:
                # Average mode - works well for all face types
                for vert, perp_positions in positions.items():
                    if perp_positions:
                        avg_pos = sum(perp_positions, Vector()) / len(perp_positions)
                        vert_positions[vert].append(avg_pos)
            
            if positions:
                edges_processed += 1

        # Apply the new positions
        for vert, positions in vert_positions.items():
            if positions:
                # Average all the positions if the vertex is part of multiple selected edges
                vert.co = sum(positions, Vector()) / len(positions)

        # Update the mesh
        bmesh.update_edit_mesh(me, loop_triangles=False)
        
        if edges_processed > 0:
            # Create detailed report
            face_info = []
            if edge_types['triangles'] > 0:
                face_info.append(f"{edge_types['triangles']} triangles")
            if edge_types['quads'] > 0:
                face_info.append(f"{edge_types['quads']} quads")
            if edge_types['ngons'] > 0:
                face_info.append(f"{edge_types['ngons']} n-gons")
            
            face_str = ", ".join(face_info) if face_info else "various faces"
            self.report({'INFO'}, f"Centered {edges_processed} edge(s) across {face_str}")
        else:
            self.report({'WARNING'}, "No edges could be centered")
            
        return {'FINISHED'}


class MESH_OT_center_vertex_loops(Operator):
    """Center selected vertices based on their neighbors"""
    bl_idname = "mesh.center_vertex_loops"
    bl_label = "Center Vertices"
    bl_description = "Center selected vertices between their connected vertices"
    bl_options = {'REGISTER', 'UNDO'}
    
    weight_by_edge_length: BoolProperty(
        name="Weight by Edge Length",
        description="Weight neighbor influence by edge length (shorter edges have more influence)",
        default=False
    )

    @classmethod
    def poll(cls, context):
        """Check if operator can run"""
        return (context.active_object is not None and
                context.active_object.type == 'MESH' and
                context.mode == 'EDIT_MESH')

    def execute(self, context):
        """Main execution method"""
        obj = context.active_object
        me = obj.data
        bm = bmesh.from_edit_mesh(me)
        bm.verts.ensure_lookup_table()

        selected_verts = [v for v in bm.verts if v.select]
        moved = 0

        for v in selected_verts:
            # Get connected vertices through manifold edges
            neighbor_data = []
            for e in v.link_edges:
                if e.is_manifold:
                    other = e.other_vert(v)
                    if self.weight_by_edge_length:
                        # Weight by inverse edge length
                        length = e.calc_length()
                        if length > 0.0001:  # Avoid division by zero
                            weight = 1.0 / length
                            neighbor_data.append((other.co, weight))
                    else:
                        neighbor_data.append((other.co, 1.0))
            
            if len(neighbor_data) >= 2:
                # Calculate weighted average
                total_weight = sum(weight for _, weight in neighbor_data)
                if total_weight > 0:
                    weighted_sum = Vector()
                    for co, weight in neighbor_data:
                        weighted_sum += co * weight
                    v.co = weighted_sum / total_weight
                    moved += 1

        bmesh.update_edit_mesh(me, loop_triangles=False)
        
        if moved == 1:
            self.report({'INFO'}, "Centered 1 vertex")
        else:
            self.report({'INFO'}, f"Centered {moved} vertices")
            
        return {'FINISHED'}


def edge_menu_func(self, context):
    """Add operators to edge menu"""
    self.layout.separator()
    self.layout.operator(MESH_OT_center_edge_loops.bl_idname, text="Center Loops")
    self.layout.operator(MESH_OT_center_vertex_loops.bl_idname, text="Center Vertices")


def context_menu_func(self, context):
    """Add operators to context menu based on selection mode"""
    layout = self.layout
    
    # Check if we're in mesh edit mode
    if context.mode != 'EDIT_MESH':
        return
        
    layout.separator()
    
    if context.tool_settings.mesh_select_mode[1]:  # Edge mode
        layout.operator(MESH_OT_center_edge_loops.bl_idname, text="Center Loops")
    if context.tool_settings.mesh_select_mode[0]:  # Vertex mode
        layout.operator(MESH_OT_center_vertex_loops.bl_idname, text="Center Vertices")


# Registration
classes = (
    MESH_OT_center_edge_loops,
    MESH_OT_center_vertex_loops,
)


def register():
    """Register the add-on"""
    # Register classes
    for cls in classes:
        bpy.utils.register_class(cls)
    
    # Add menu entries
    bpy.types.VIEW3D_MT_edit_mesh_edges.append(edge_menu_func)
    bpy.types.VIEW3D_MT_edit_mesh_context_menu.append(context_menu_func)

    # Register hotkey
    wm = bpy.context.window_manager
    if wm.keyconfigs.addon:
        km = wm.keyconfigs.addon.keymaps.new(name='Mesh', space_type='EMPTY')
        kmi = km.keymap_items.new(
            MESH_OT_center_edge_loops.bl_idname,
            type='C', 
            value='PRESS', 
            ctrl=True, 
            shift=True
        )
        addon_keymaps.append((km, kmi))


def unregister():
    """Unregister the add-on"""
    # Unregister classes
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
    
    # Remove menu entries
    bpy.types.VIEW3D_MT_edit_mesh_edges.remove(edge_menu_func)
    bpy.types.VIEW3D_MT_edit_mesh_context_menu.remove(context_menu_func)

    # Unregister hotkeys
    for km, kmi in addon_keymaps:
        km.keymap_items.remove(kmi)
    addon_keymaps.clear()


if __name__ == "__main__":
    register()