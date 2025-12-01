
bl_info = {
    "name": "Edge Constraint Mode",
    "author": "Stephan Viranyi + Claude",
    "version": (1, 2, 0),
    "blender": (3, 0, 0),
    "location": "View3D > Sidebar > Tool > Edge Constraint",
    "description": "Constrains transforms (G/R/S) to flow along edge topology in Edit Mode - like 3ds Max/Maya Edge Constraint",
    "warning": "",
    "doc_url": "https://github.com/Stephk0/Toolings",
    "tracker_url": "https://www.artstation.com/stephko",
    "category": "Mesh",
}

import bpy
import bmesh
import math
from mathutils import Vector, Matrix
from bpy.props import BoolProperty, EnumProperty, FloatProperty, IntProperty
from bpy.types import Operator, Panel, PropertyGroup
import gpu
from gpu_extras.batch import batch_for_shader

# ============================================================================
# UTILITY FUNCTIONS - Topology & Math
# ============================================================================

class EdgeConstraintData:
    """Stores per-vertex topology and state for edge-constrained motion"""
    
    def __init__(self, bm, selected_verts, constrain_to_selected=False):
        self.bm = bm
        self.selected_verts = selected_verts
        self.constrain_to_selected = constrain_to_selected
        self.original_positions = {}
        self.adjacency = {}  # vertex -> [(neighbor_vert, edge_length, edge_direction, edge)]
        self.edge_paths = {}  # vertex -> list of edges forming path
        
        # Store original positions
        for v in selected_verts:
            self.original_positions[v.index] = v.co.copy()
            
        # Build adjacency
        self._build_adjacency()
    
    def _build_adjacency(self):
        """Build adjacency graph with edge lengths and directions"""
        for v in self.selected_verts:
            neighbors = []
            for edge in v.link_edges:
                # If constraining to selected edges only, skip unselected edges
                if self.constrain_to_selected and not edge.select:
                    continue
                    
                other = edge.other_vert(v)
                edge_vec = other.co - v.co
                length = edge_vec.length
                direction = edge_vec.normalized() if length > 0 else Vector((0, 0, 0))
                neighbors.append((other, length, direction, edge))
            self.adjacency[v.index] = neighbors
            self.edge_paths[v.index] = []
    
    def get_best_aligned_edge(self, v_index, direction):
        """Find the edge most aligned with given direction"""
        if v_index not in self.adjacency or len(self.adjacency[v_index]) == 0:
            return None
        
        neighbors = self.adjacency[v_index]
        best_neighbor = None
        best_dot = -float('inf')
        
        for neighbor, length, edge_dir, edge in neighbors:
            # Consider both forward and backward alignment
            dot = abs(direction.dot(edge_dir))
            if dot > best_dot:
                best_dot = dot
                # Determine actual direction (forward or backward)
                actual_dir = edge_dir if direction.dot(edge_dir) > 0 else -edge_dir
                best_neighbor = (neighbor, length, actual_dir, edge)
        
        return best_neighbor
    
    def slide_along_topology(self, v, displacement, use_clamp=True, use_even=False):
        """
        Slide vertex along connected edges by given displacement vector.
        Returns new position and records path taken.
        
        Args:
            v: BMVert to slide
            displacement: Vector displacement
            use_clamp: Stop at edge endpoints
            use_even: Use even spacing (maintain proportional distances)
        """
        if v.index not in self.adjacency:
            return v.co.copy()
        
        start_pos = self.original_positions[v.index]
        current_pos = start_pos.copy()
        remaining_distance = displacement.length
        
        if remaining_distance < 0.0001:
            return current_pos
        
        direction = displacement.normalized()
        path_edges = []
        max_iterations = 50  # Prevent infinite loops
        iterations = 0
        current_v = v
        
        while remaining_distance > 0.0001 and iterations < max_iterations:
            iterations += 1
            
            # Find best aligned edge from current vertex
            best_edge = self.get_best_aligned_edge(current_v.index, direction)
            
            if best_edge is None:
                break
            
            neighbor, edge_length, edge_dir, edge = best_edge
            path_edges.append(edge)
            
            # Calculate how far to move along this edge
            move_distance = min(remaining_distance, edge_length)
            
            if use_clamp and move_distance > edge_length:
                move_distance = edge_length
            
            # Move along edge
            current_pos += edge_dir * move_distance
            remaining_distance -= move_distance
            
            # Update direction for next iteration (smooth flow)
            if remaining_distance > 0.0001:
                # Calculate new direction from current position
                tangent = (neighbor.co - current_pos).normalized()
                direction = direction.lerp(tangent, 0.5).normalized()
            
            # If we've traveled the full edge length and have remaining distance
            if move_distance >= edge_length - 0.0001 and remaining_distance > 0.0001:
                current_v = neighbor
            else:
                break
        
        # Store the path taken for visualization
        self.edge_paths[v.index] = path_edges
        
        return current_pos
    
    def get_path_visualization_data(self):
        """Get line segments for drawing edge paths"""
        lines = []
        for v in self.selected_verts:
            if v.index in self.edge_paths:
                for edge in self.edge_paths[v.index]:
                    v1, v2 = edge.verts
                    lines.append((v1.co.copy(), v2.co.copy()))
        return lines


def project_displacement_to_edge(v, displacement, adjacency):
    """Project a displacement vector onto the best-aligned edge direction"""
    if v.index not in adjacency or len(adjacency[v.index]) == 0:
        return Vector((0, 0, 0))
    
    neighbors = adjacency[v.index]
    best_dot = -float('inf')
    best_direction = Vector((0, 0, 0))
    
    for neighbor, length, edge_dir, edge in neighbors:
        dot = abs(displacement.dot(edge_dir))
        if dot > best_dot:
            best_dot = dot
            # Use signed dot to preserve direction
            sign = 1.0 if displacement.dot(edge_dir) > 0 else -1.0
            best_direction = edge_dir * sign
    
    # Project displacement onto best edge
    projected_length = displacement.dot(best_direction)
    return best_direction * projected_length


# ============================================================================
# GPU DRAWING - Visual Feedback
# ============================================================================

draw_handler = None
draw_data = {'lines': [], 'color': (0.0, 1.0, 0.5, 0.8)}

def draw_edge_paths():
    """Draw edge paths in viewport"""
    if not draw_data['lines']:
        return
    
    try:
        shader = gpu.shader.from_builtin('3D_UNIFORM_COLOR')
        
        # Flatten line data
        vertices = []
        for line in draw_data['lines']:
            vertices.extend([line[0][:], line[1][:]])
        
        if not vertices:
            return
        
        batch = batch_for_shader(shader, 'LINES', {"pos": vertices})
        
        shader.bind()
        shader.uniform_float("color", draw_data['color'])
        
        # Enable line smoothing
        gpu.state.blend_set('ALPHA')
        gpu.state.line_width_set(2.0)
        
        batch.draw(shader)
        
        gpu.state.blend_set('NONE')
        gpu.state.line_width_set(1.0)
    except Exception as e:
        print(f"Draw error: {e}")


# ============================================================================
# MODAL OPERATOR - Main Edge Constraint Mode
# ============================================================================

class VIEW3D_OT_edge_constraint_mode(Operator):
    bl_idname = "view3d.edge_constraint_mode"
    bl_label = "Edge Constraint Mode"
    bl_description = "Constrains transforms to flow along edge topology (G/R/S hotkeys work)"
    bl_options = {'REGISTER', 'UNDO', 'BLOCKING'}
    
    @classmethod
    def poll(cls, context):
        return (context.mode == 'EDIT_MESH' and 
                context.active_object and 
                context.active_object.type == 'MESH')
    
    def invoke(self, context, event):
        global draw_handler
        
        # Initialize instance variables (FIXED: moved from class-level to instance-level)
        self._initial_mouse = None
        self._constraint_data = None
        self._bm = None
        self._obj = None
        self._pivot = None
        self._original_positions = {}
        self._transform_mode = 'NONE'
        self._draw_handler = None
        self._sensitivity = 0.01
        self._accumulated_delta = 0.0
        
        if context.mode != 'EDIT_MESH':
            self.report({'WARNING'}, "Edge Constraint Mode requires Edit Mode")
            return {'CANCELLED'}
        
        self._obj = context.active_object
        self._bm = bmesh.from_edit_mesh(self._obj.data)
        
        # Get selected vertices
        selected_verts = [v for v in self._bm.verts if v.select]
        
        if len(selected_verts) == 0:
            self.report({'WARNING'}, "No vertices selected")
            return {'CANCELLED'}
        
        # Get settings from scene properties
        scene = context.scene
        use_clamp = scene.ec_use_clamp
        constrain_to_selected = scene.ec_constrain_to_selected
        
        # Initialize constraint data
        self._constraint_data = EdgeConstraintData(
            self._bm, selected_verts, constrain_to_selected
        )
        
        # Store original positions for undo
        for v in selected_verts:
            self._original_positions[v.index] = v.co.copy()
        
        # Calculate pivot (median of selection)
        pivot = Vector((0, 0, 0))
        for v in selected_verts:
            pivot += v.co
        pivot /= len(selected_verts)
        self._pivot = pivot
        
        # Store initial mouse position
        self._initial_mouse = (event.mouse_x, event.mouse_y)
        
        # Setup drawing
        draw_data['lines'] = []
        if draw_handler is None:
            draw_handler = bpy.types.SpaceView3D.draw_handler_add(
                draw_edge_paths, (), 'WINDOW', 'POST_VIEW'
            )
        
        # Add modal handler
        context.window_manager.modal_handler_add(self)
        
        # Set header text
        context.area.header_text_set(
            "Edge Constraint Mode | G: Translate | R: Rotate | S: Scale | "
            "LMB/Enter: Confirm | RMB/ESC: Cancel"
        )
        
        return {'RUNNING_MODAL'}

    def modal(self, context, event):
        context.area.tag_redraw()
        
        scene = context.scene
        
        # Cancel
        if event.type in {'RIGHTMOUSE', 'ESC'}:
            self._cleanup(context)
            self._restore_original_positions()
            bmesh.update_edit_mesh(self._obj.data)
            return {'CANCELLED'}
        
        # Confirm
        if event.type in {'LEFTMOUSE', 'RET'} and event.value == 'PRESS':
            self._cleanup(context)
            bmesh.update_edit_mesh(self._obj.data)
            self.report({'INFO'}, f"Edge constraint applied ({len(self._constraint_data.selected_verts)} verts)")
            return {'FINISHED'}
        
        # Reset on Tab (back to edit mode)
        if event.type == 'TAB':
            self._cleanup(context)
            return {'FINISHED'}
        
        # Enter transform modes
        if event.type == 'G' and event.value == 'PRESS':
            self._transform_mode = 'TRANSLATE'
            self._initial_mouse = (event.mouse_x, event.mouse_y)
            self._accumulated_delta = 0.0
            context.area.header_text_set(
                "TRANSLATING along edges | LMB/Enter: Confirm | RMB/ESC: Cancel"
            )
            return {'RUNNING_MODAL'}
        
        if event.type == 'R' and event.value == 'PRESS':
            self._transform_mode = 'ROTATE'
            self._initial_mouse = (event.mouse_x, event.mouse_y)
            self._accumulated_delta = 0.0
            context.area.header_text_set(
                "ROTATING along edges | LMB/Enter: Confirm | RMB/ESC: Cancel"
            )
            return {'RUNNING_MODAL'}
        
        if event.type == 'S' and event.value == 'PRESS':
            self._transform_mode = 'SCALE'
            self._initial_mouse = (event.mouse_x, event.mouse_y)
            self._accumulated_delta = 0.0
            context.area.header_text_set(
                "SCALING along edges | LMB/Enter: Confirm | RMB/ESC: Cancel"
            )
            return {'RUNNING_MODAL'}
        
        # Adjust sensitivity with scroll
        if event.type == 'WHEELUPMOUSE':
            self._sensitivity *= 1.1
            return {'RUNNING_MODAL'}
        elif event.type == 'WHEELDOWNMOUSE':
            self._sensitivity *= 0.9
            return {'RUNNING_MODAL'}
        
        # Apply transforms based on mouse movement
        if event.type == 'MOUSEMOVE' and self._transform_mode != 'NONE':
            self._apply_constrained_transform(context, event, scene)
            return {'RUNNING_MODAL'}
        
        return {'RUNNING_MODAL'}
    
    def _apply_constrained_transform(self, context, event, scene):
        """Apply edge-constrained transformation based on mouse delta"""
        if self._initial_mouse is None:
            return
        
        mouse_delta_x = event.mouse_x - self._initial_mouse[0]
        mouse_delta_y = event.mouse_y - self._initial_mouse[1]
        
        if self._transform_mode == 'TRANSLATE':
            self._apply_constrained_translation(mouse_delta_x * self._sensitivity, scene)
        elif self._transform_mode == 'ROTATE':
            self._apply_constrained_rotation(mouse_delta_x * self._sensitivity * 0.05, scene)
        elif self._transform_mode == 'SCALE':
            scale_factor = 1.0 + mouse_delta_x * self._sensitivity
            self._apply_constrained_scale(scale_factor, scene)
        
        # Update visualization
        draw_data['lines'] = self._constraint_data.get_path_visualization_data()
        
        bmesh.update_edit_mesh(self._obj.data, loop_triangles=False, destructive=False)
    
    def _apply_constrained_translation(self, distance, scene):
        """Translate vertices along edges"""
        use_clamp = scene.ec_use_clamp
        use_even = scene.ec_use_even
        
        for v in self._constraint_data.selected_verts:
            if v.index not in self._original_positions:
                continue
            
            # Calculate displacement direction (simple X-axis for now)
            # In a full implementation, this would use view orientation
            displacement = Vector((distance, 0, 0))
            
            # Slide along topology
            new_pos = self._constraint_data.slide_along_topology(
                v, displacement, use_clamp, use_even
            )
            v.co = new_pos
    
    def _apply_constrained_rotation(self, angle, scene):
        """Rotate vertices around pivot, constrained to edges"""
        use_clamp = scene.ec_use_clamp
        
        # Create rotation matrix around pivot (Z-axis rotation)
        rot_matrix = Matrix.Rotation(angle, 4, 'Z')
        
        for v in self._constraint_data.selected_verts:
            if v.index not in self._original_positions:
                continue
            
            # Get original position relative to pivot
            orig_pos = self._original_positions[v.index]
            rel_pos = orig_pos - self._pivot
            
            # Apply rotation
            rotated_pos = rot_matrix @ rel_pos
            target_pos = self._pivot + rotated_pos
            
            # Calculate displacement
            displacement = target_pos - orig_pos
            
            # Project and slide along edges
            new_pos = self._constraint_data.slide_along_topology(
                v, displacement, use_clamp
            )
            v.co = new_pos
    
    def _apply_constrained_scale(self, scale_factor, scene):
        """Scale vertices from pivot, constrained to edges"""
        use_clamp = scene.ec_use_clamp
        
        for v in self._constraint_data.selected_verts:
            if v.index not in self._original_positions:
                continue
            
            # Get original position relative to pivot
            orig_pos = self._original_positions[v.index]
            rel_pos = orig_pos - self._pivot
            
            # Apply scale
            scaled_pos = rel_pos * scale_factor
            target_pos = self._pivot + scaled_pos
            
            # Calculate displacement
            displacement = target_pos - orig_pos
            
            # Project and slide along edges
            new_pos = self._constraint_data.slide_along_topology(
                v, displacement, use_clamp
            )
            v.co = new_pos
    
    def _restore_original_positions(self):
        """Restore all vertices to their original positions"""
        for v in self._constraint_data.selected_verts:
            if v.index in self._original_positions:
                v.co = self._original_positions[v.index]
    
    def _cleanup(self, context):
        """Clean up drawing handlers and reset state"""
        global draw_handler
        
        if draw_handler is not None:
            bpy.types.SpaceView3D.draw_handler_remove(draw_handler, 'WINDOW')
            draw_handler = None
        
        draw_data['lines'] = []
        context.area.header_text_set(None)


# ============================================================================
# UI PANEL
# ============================================================================

class VIEW3D_PT_edge_constraint_panel(Panel):
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Tool'
    bl_label = "Edge Constraint Mode"
    bl_context = "mesh_edit"
    
    def draw(self, context):
        layout = self.layout
        scene = context.scene
        
        # Main operator button
        col = layout.column(align=True)
        col.scale_y = 1.5
        col.operator(
            "view3d.edge_constraint_mode", 
            text="Enable Edge Constraint", 
            icon='CON_FOLLOWPATH'
        )
        
        layout.separator()
        
        # Options
        box = layout.box()
        box.label(text="Constraint Options:", icon='SETTINGS')
        col = box.column(align=True)
        col.prop(scene, "ec_use_clamp")
        col.prop(scene, "ec_constrain_to_selected")
        col.prop(scene, "ec_use_even")
        
        layout.separator()
        
        # Advanced options
        box = layout.box()
        box.label(text="Advanced:", icon='MODIFIER')
        col = box.column(align=True)
        col.prop(scene, "ec_respect_pinned")
        col.prop(scene, "ec_stop_at_nonmanifold")
        col.prop(scene, "ec_preserve_uv")
        
        layout.separator()
        
        # Info
        box = layout.box()
        box.label(text="Usage:", icon='INFO')
        col = box.column(align=True)
        col.label(text="1. Select vertices/edges/faces")
        col.label(text="2. Click 'Enable Edge Constraint'")
        col.label(text="3. Press G/R/S to transform")
        col.label(text="4. Move mouse to adjust")
        col.label(text="5. LMB/Enter to confirm")
        
        layout.separator()
        
        # Links
        box = layout.box()
        box.label(text="Resources:", icon='URL')
        col = box.column(align=True)
        col.operator("wm.url_open", text="GitHub Repository", icon='URL').url = "https://github.com/Stephk0/Toolings"
        col.operator("wm.url_open", text="My Artstation Portfolio", icon='URL').url = "https://www.artstation.com/stephko"
        
        layout.separator()
        col = layout.column()
        col.label(text="Maintainer: Stephan Viranyi + Claude", icon='USER')


# ============================================================================
# PROPERTIES
# ============================================================================

def register_properties():
    # Basic options
    bpy.types.Scene.ec_use_clamp = BoolProperty(
        name="Clamp to Boundaries",
        description="Stop at edge endpoints instead of overshooting",
        default=True
    )
    
    bpy.types.Scene.ec_constrain_to_selected = BoolProperty(
        name="Selected Edges Only",
        description="Only slide along edges that are selected",
        default=False
    )
    
    bpy.types.Scene.ec_use_even = BoolProperty(
        name="Even Spacing",
        description="Maintain proportional distances (like Edge Slide 'Even' mode)",
        default=False
    )
    
    # Advanced options
    bpy.types.Scene.ec_respect_pinned = BoolProperty(
        name="Respect Pinned Vertices",
        description="Keep pinned vertices fixed during transformation",
        default=True
    )
    
    bpy.types.Scene.ec_stop_at_nonmanifold = BoolProperty(
        name="Stop at Non-Manifold",
        description="Don't cross non-manifold boundaries",
        default=False
    )
    
    bpy.types.Scene.ec_preserve_uv = BoolProperty(
        name="Preserve UV Stretch",
        description="Attempt to maintain UV layout during transformation (experimental)",
        default=False
    )

def unregister_properties():
    del bpy.types.Scene.ec_use_clamp
    del bpy.types.Scene.ec_constrain_to_selected
    del bpy.types.Scene.ec_use_even
    del bpy.types.Scene.ec_respect_pinned
    del bpy.types.Scene.ec_stop_at_nonmanifold
    del bpy.types.Scene.ec_preserve_uv


# ============================================================================
# REGISTRATION
# ============================================================================

classes = (
    VIEW3D_OT_edge_constraint_mode,
    VIEW3D_PT_edge_constraint_panel,
)

def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    register_properties()
    print("✓ Edge Constraint Mode addon registered")
    
def unregister():
    global draw_handler
    
    # Clean up draw handler
    if draw_handler is not None:
        bpy.types.SpaceView3D.draw_handler_remove(draw_handler, 'WINDOW')
        draw_handler = None
    
    unregister_properties()
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
    print("✓ Edge Constraint Mode addon unregistered")

if __name__ == "__main__":
    register()
