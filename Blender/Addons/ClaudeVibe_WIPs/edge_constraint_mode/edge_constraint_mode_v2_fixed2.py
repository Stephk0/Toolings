
bl_info = {
    "name": "Edge Constraint Mode V2 - Persistent",
    "author": "Stephan Viranyi + Claude",
    "version": (2, 0, 0),
    "blender": (3, 0, 0),
    "location": "View3D > Sidebar > Tool > Edge Constraint",
    "description": "Persistent edge constraint mode that stays active across tool switches (G/R/S) with multi-lane edge support",
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
# GLOBAL STATE - Persistent Mode Management
# ============================================================================

class EdgeConstraintState:
    """Global state for persistent edge constraint mode"""
    enabled = False
    active_object = None
    modal_operator = None
    draw_handler = None
    
    @classmethod
    def reset(cls):
        cls.enabled = False
        cls.active_object = None
        cls.modal_operator = None
        if cls.draw_handler:
            try:
                bpy.types.SpaceView3D.draw_handler_remove(cls.draw_handler, 'WINDOW')
            except:
                pass
            cls.draw_handler = None

# ============================================================================
# UTILITY FUNCTIONS - Multi-Lane Topology & Math
# ============================================================================

class MultiLaneEdgeData:
    """Stores multi-lane edge topology for better constraint flow"""
    
    def __init__(self, bm, selected_verts, constrain_to_selected=False):
        self.bm = bm
        self.selected_verts = selected_verts
        self.constrain_to_selected = constrain_to_selected
        self.original_positions = {}
        self.multi_lane_adjacency = {}  # vertex -> [all connected edges with data]
        self.edge_rings = {}  # vertex -> edge rings around it
        
        # Store original positions
        for v in selected_verts:
            self.original_positions[v.index] = v.co.copy()
            
        # Build multi-lane adjacency
        self._build_multi_lane_adjacency()
    
    def _build_multi_lane_adjacency(self):
        """Build adjacency considering ALL surrounding edge lanes"""
        for v in self.selected_verts:
            all_edges = []
            
            # Get all directly connected edges
            for edge in v.link_edges:
                if self.constrain_to_selected and not edge.select:
                    continue
                    
                other = edge.other_vert(v)
                edge_vec = other.co - v.co
                length = edge_vec.length
                direction = edge_vec.normalized() if length > 0 else Vector((0, 0, 0))
                
                # Calculate edge properties
                all_edges.append({
                    'other': other,
                    'length': length,
                    'direction': direction,
                    'edge': edge,
                    'flow_score': 0.0  # Will be calculated based on movement
                })
            
            self.multi_lane_adjacency[v.index] = all_edges
            
            # Build edge rings for smoother flow
            self._build_edge_rings(v)
    
    def _build_edge_rings(self, v):
        """Build edge rings around a vertex for multi-directional flow"""
        rings = []
        
        # Get faces connected to this vertex
        for face in v.link_faces:
            face_edges = []
            for edge in face.edges:
                if v in edge.verts:
                    face_edges.append(edge)
            if face_edges:
                rings.append(face_edges)
        
        self.edge_rings[v.index] = rings
    
    def get_multi_lane_edges(self, v_index, direction, threshold=0.3):
        """
        Get ALL edges aligned with direction above threshold.
        This allows flow across multiple parallel lanes.
        
        Args:
            v_index: Vertex index
            direction: Movement direction
            threshold: Minimum alignment (0-1, lower = more permissive)
        """
        if v_index not in self.multi_lane_adjacency:
            return []
        
        aligned_edges = []
        all_edges = self.multi_lane_adjacency[v_index]
        
        for edge_data in all_edges:
            # Calculate alignment score (considering both directions)
            dot_forward = direction.dot(edge_data['direction'])
            dot_backward = direction.dot(-edge_data['direction'])
            alignment = max(abs(dot_forward), abs(dot_backward))
            
            if alignment >= threshold:
                # Determine actual direction
                if abs(dot_forward) > abs(dot_backward):
                    actual_dir = edge_data['direction']
                else:
                    actual_dir = -edge_data['direction']
                
                aligned_edges.append({
                    'other': edge_data['other'],
                    'length': edge_data['length'],
                    'direction': actual_dir,
                    'edge': edge_data['edge'],
                    'alignment': alignment
                })
        
        # Sort by alignment (best first)
        aligned_edges.sort(key=lambda x: x['alignment'], reverse=True)
        return aligned_edges
    
    def slide_multi_lane(self, v, displacement, use_clamp=True):
        """
        Slide vertex along topology using multi-lane approach.
        Can flow across parallel edges simultaneously.
        """
        if v.index not in self.multi_lane_adjacency:
            return v.co.copy()
        
        start_pos = self.original_positions[v.index]
        current_pos = start_pos.copy()
        remaining_distance = displacement.length
        
        if remaining_distance < 0.0001:
            return current_pos
        
        direction = displacement.normalized()
        max_iterations = 100  # Higher for multi-lane
        iterations = 0
        current_v = v
        visited = set()
        
        while remaining_distance > 0.0001 and iterations < max_iterations:
            iterations += 1
            
            if current_v.index in visited and iterations > 5:
                # Avoid circular paths
                break
            visited.add(current_v.index)
            
            # Get all aligned edges (multi-lane)
            aligned_edges = self.get_multi_lane_edges(
                current_v.index, 
                direction, 
                threshold=0.2  # Permissive threshold for multi-lane
            )
            
            if not aligned_edges:
                break
            
            # Take the best aligned edge for primary movement
            best_edge = aligned_edges[0]
            edge_length = best_edge['length']
            edge_dir = best_edge['direction']
            
            # Calculate movement
            move_distance = min(remaining_distance, edge_length)
            
            if use_clamp and move_distance > edge_length:
                move_distance = edge_length
            
            # Move along edge
            current_pos += edge_dir * move_distance
            remaining_distance -= move_distance
            
            # Smooth direction transition considering all lanes
            if remaining_distance > 0.0001 and len(aligned_edges) > 1:
                # Blend direction from multiple lanes for smoother flow
                blended_dir = Vector((0, 0, 0))
                total_weight = 0.0
                
                for lane in aligned_edges[:3]:  # Use top 3 lanes
                    weight = lane['alignment']
                    blended_dir += lane['direction'] * weight
                    total_weight += weight
                
                if total_weight > 0:
                    blended_dir = (blended_dir / total_weight).normalized()
                    direction = direction.lerp(blended_dir, 0.6).normalized()
            
            # Move to next vertex if needed
            if move_distance >= edge_length - 0.0001 and remaining_distance > 0.0001:
                current_v = best_edge['other']
            else:
                break
        
        return current_pos
    
    def get_weighted_direction(self, v_index, displacement):
        """Get weighted average direction from all aligned edges"""
        if v_index not in self.multi_lane_adjacency:
            return displacement.normalized()
        
        aligned = self.get_multi_lane_edges(v_index, displacement.normalized(), threshold=0.2)
        
        if not aligned:
            return displacement.normalized()
        
        # Weight by alignment
        weighted_dir = Vector((0, 0, 0))
        total_weight = 0.0
        
        for edge in aligned:
            weight = edge['alignment'] ** 2  # Square for emphasis
            weighted_dir += edge['direction'] * weight
            total_weight += weight
        
        if total_weight > 0:
            return (weighted_dir / total_weight).normalized()
        
        return displacement.normalized()


# ============================================================================
# GPU DRAWING - Visual Feedback
# ============================================================================

draw_data = {
    'active_edges': [],
    'color_active': (0.0, 1.0, 0.5, 0.9),
    'color_available': (0.3, 0.7, 1.0, 0.5)
}

def draw_constraint_visualization():
    """Draw active constraint edges"""
    if not draw_data['active_edges']:
        return
    
    try:
        shader = gpu.shader.from_builtin('3D_UNIFORM_COLOR')
        
        # Draw active edges
        vertices = []
        for edge in draw_data['active_edges']:
            v1, v2 = edge.verts
            vertices.extend([v1.co[:], v2.co[:]])
        
        if not vertices:
            return
        
        batch = batch_for_shader(shader, 'LINES', {"pos": vertices})
        
        shader.bind()
        shader.uniform_float("color", draw_data['color_active'])
        
        gpu.state.blend_set('ALPHA')
        gpu.state.line_width_set(3.0)
        
        batch.draw(shader)
        
        gpu.state.blend_set('NONE')
        gpu.state.line_width_set(1.0)
    except Exception as e:
        print(f"Draw error: {e}")


# ============================================================================
# PERSISTENT MODAL OPERATOR
# ============================================================================

class VIEW3D_OT_edge_constraint_mode_persistent(Operator):
    """Persistent edge constraint modal operator"""
    bl_idname = "view3d.edge_constraint_mode_persistent"
    bl_label = "Edge Constraint Mode (Persistent)"
    bl_description = "Persistent edge constraint - stays active across tool switches"
    bl_options = {'REGISTER', 'UNDO', 'BLOCKING'}
    
    def invoke(self, context, event):
        # Initialize instance variables
        self._timer = None
        self._constraint_data = None
        self._in_transform = False
        self._transform_type = None  # 'MOVE', 'ROTATE', 'SCALE'
        self._original_positions = {}
        self._pivot = Vector((0, 0, 0))
        self._initial_mouse = Vector((0, 0))
        self._last_mouse = Vector((0, 0))
        self._accumulated_delta = Vector((0, 0))
        
        if context.mode != 'EDIT_MESH':
            self.report({'WARNING'}, "Must be in Edit Mode")
            return {'CANCELLED'}
        
        obj = context.active_object
        if not obj or obj.type != 'MESH':
            self.report({'WARNING'}, "Active object must be a mesh")
            return {'CANCELLED'}
        
        # Store in global state
        EdgeConstraintState.enabled = True
        EdgeConstraintState.active_object = obj
        EdgeConstraintState.modal_operator = self
        
        # Setup
        self._setup_constraint_data(context)
        
        # Add modal handler
        context.window_manager.modal_handler_add(self)
        
        # Add timer for continuous updates
        self._timer = context.window_manager.event_timer_add(0.016, window=context.window)
        
        # Setup draw handler
        self._setup_draw_handler(context)
        
        # UI feedback
        context.area.header_text_set("⚡ Edge Constraint ACTIVE | G/R/S = Transform | ESC = Exit Mode")
        
        self.report({'INFO'}, "Edge Constraint Mode ENABLED - Press G/R/S to transform")
        
        return {'RUNNING_MODAL'}
    
    def modal(self, context, event):
        # Check if mode is still enabled
        if not EdgeConstraintState.enabled:
            return self._exit_modal(context)
        
        # Check if still in edit mode
        if context.mode != 'EDIT_MESH':
            EdgeConstraintState.enabled = False
            return self._exit_modal(context)
        
        # Update constraint data if selection changed
        if event.type == 'TIMER':
            self._check_selection_change(context)
        
        # Handle tool activation
        if not self._in_transform:
            # Listen for G/R/S keys to start transform
            if event.type == 'G' and event.value == 'PRESS':
                return self._start_transform(context, event, 'MOVE')
            elif event.type == 'R' and event.value == 'PRESS':
                return self._start_transform(context, event, 'ROTATE')
            elif event.type == 'S' and event.value == 'PRESS':
                return self._start_transform(context, event, 'SCALE')
            
            # Exit mode
            if event.type == 'ESC' and event.value == 'PRESS':
                EdgeConstraintState.enabled = False
                self.report({'INFO'}, "Edge Constraint Mode DISABLED")
                return self._exit_modal(context)
        
        else:
            # Handle active transform
            return self._handle_transform(context, event)
        
        return {'PASS_THROUGH'}
    
    def _setup_constraint_data(self, context):
        """Setup or refresh constraint data"""
        obj = context.active_object
        bm = bmesh.from_edit_mesh(obj.data)
        
        selected_verts = [v for v in bm.verts if v.select]
        
        if not selected_verts:
            return
        
        scene = context.scene
        self._constraint_data = MultiLaneEdgeData(
            bm, 
            selected_verts,
            constrain_to_selected=scene.ec_constrain_to_selected
        )
        
        # Update visualization
        if self._constraint_data:
            all_edges = []
            for v in selected_verts:
                all_edges.extend(v.link_edges)
            draw_data['active_edges'] = list(set(all_edges))
    
    def _check_selection_change(self, context):
        """Check if selection changed and update constraint data"""
        obj = context.active_object
        if not obj:
            return
        
        bm = bmesh.from_edit_mesh(obj.data)
        current_selected = [v for v in bm.verts if v.select]
        
        # Check if selection changed
        if self._constraint_data:
            old_indices = set(v.index for v in self._constraint_data.selected_verts)
            new_indices = set(v.index for v in current_selected)
            
            if old_indices != new_indices:
                self._setup_constraint_data(context)
    
    def _start_transform(self, context, event, transform_type):
        """Start a constrained transform operation"""
        if not self._constraint_data or not self._constraint_data.selected_verts:
            return {'PASS_THROUGH'}
        
        self._in_transform = True
        self._transform_type = transform_type
        self._initial_mouse = Vector((event.mouse_region_x, event.mouse_region_y))
        self._last_mouse = self._initial_mouse.copy()
        self._accumulated_delta = Vector((0, 0))
        
        # Store original positions
        self._original_positions = {}
        for v in self._constraint_data.selected_verts:
            self._original_positions[v.index] = v.co.copy()
        
        # Calculate pivot point
        pivot_sum = Vector((0, 0, 0))
        for v in self._constraint_data.selected_verts:
            pivot_sum += v.co
        self._pivot = pivot_sum / len(self._constraint_data.selected_verts)
        
        # UI feedback
        tool_name = {'MOVE': 'Move', 'ROTATE': 'Rotate', 'SCALE': 'Scale'}[transform_type]
        context.area.header_text_set(
            f"⚡ Edge Constraint: {tool_name} | LMB/Enter = Confirm | RMB/ESC = Cancel"
        )
        
        return {'RUNNING_MODAL'}
    
    def _handle_transform(self, context, event):
        """Handle active transform with edge constraint"""
        # Confirm
        if event.type in {'LEFTMOUSE', 'RET'} and event.value == 'PRESS':
            return self._confirm_transform(context)
        
        # Cancel
        if event.type in {'RIGHTMOUSE', 'ESC'} and event.value == 'PRESS':
            return self._cancel_transform(context)
        
        # Update transform based on mouse movement
        if event.type == 'MOUSEMOVE':
            current_mouse = Vector((event.mouse_region_x, event.mouse_region_y))
            delta = current_mouse - self._last_mouse
            self._accumulated_delta += delta
            self._last_mouse = current_mouse
            
            # Apply constrained transform
            self._apply_constrained_transform(context, event)
            
            # Update mesh
            obj = context.active_object
            bmesh.update_edit_mesh(obj.data)
            context.area.tag_redraw()
        
        return {'RUNNING_MODAL'}
    
    def _apply_constrained_transform(self, context, event):
        """Apply transform with edge constraint"""
        obj = context.active_object
        bm = bmesh.from_edit_mesh(obj.data)
        scene = context.scene
        
        if self._transform_type == 'MOVE':
            self._apply_constrained_move(context, scene)
        elif self._transform_type == 'ROTATE':
            self._apply_constrained_rotate(context, scene)
        elif self._transform_type == 'SCALE':
            self._apply_constrained_scale(context, scene)
    
    def _apply_constrained_move(self, context, scene):
        """Move with multi-lane edge constraint"""
        use_clamp = scene.ec_use_clamp
        
        # Calculate 3D displacement from 2D mouse movement
        region = context.region
        rv3d = context.region_data
        
        # Simple scaling factor for movement
        sensitivity = 0.01
        mouse_delta_3d = Vector((
            self._accumulated_delta.x * sensitivity,
            self._accumulated_delta.y * sensitivity,
            0
        ))
        
        # Transform to world space
        view_matrix = rv3d.view_matrix.inverted()
        displacement = view_matrix @ mouse_delta_3d
        displacement.z = 0  # Keep in XY plane mostly
        
        for v in self._constraint_data.selected_verts:
            if v.index not in self._original_positions:
                continue
            
            orig_pos = self._original_positions[v.index]
            
            # Use multi-lane slide
            new_pos = self._constraint_data.slide_multi_lane(
                v, displacement, use_clamp
            )
            v.co = new_pos
    
    def _apply_constrained_rotate(self, context, scene):
        """Rotate with edge constraint"""
        use_clamp = scene.ec_use_clamp
        
        # Calculate rotation angle from mouse delta
        sensitivity = 0.01
        angle = self._accumulated_delta.x * sensitivity
        
        rot_matrix = Matrix.Rotation(angle, 4, 'Z')
        
        for v in self._constraint_data.selected_verts:
            if v.index not in self._original_positions:
                continue
            
            orig_pos = self._original_positions[v.index]
            rel_pos = orig_pos - self._pivot
            rotated_pos = rot_matrix @ rel_pos
            target_pos = self._pivot + rotated_pos
            displacement = target_pos - orig_pos
            
            new_pos = self._constraint_data.slide_multi_lane(
                v, displacement, use_clamp
            )
            v.co = new_pos
    
    def _apply_constrained_scale(self, context, scene):
        """Scale with edge constraint"""
        use_clamp = scene.ec_use_clamp
        
        # Calculate scale from mouse delta
        sensitivity = 0.01
        scale_factor = 1.0 + (self._accumulated_delta.x * sensitivity)
        scale_factor = max(0.1, scale_factor)  # Prevent negative scale
        
        for v in self._constraint_data.selected_verts:
            if v.index not in self._original_positions:
                continue
            
            orig_pos = self._original_positions[v.index]
            rel_pos = orig_pos - self._pivot
            scaled_pos = rel_pos * scale_factor
            target_pos = self._pivot + scaled_pos
            displacement = target_pos - orig_pos
            
            new_pos = self._constraint_data.slide_multi_lane(
                v, displacement, use_clamp
            )
            v.co = new_pos
    
    def _confirm_transform(self, context):
        """Confirm transform and return to constraint mode"""
        self._in_transform = False
        self._transform_type = None
        self._original_positions = {}
        
        # Reset accumulated delta
        self._accumulated_delta = Vector((0, 0))
        
        # Update constraint data with new positions
        self._setup_constraint_data(context)
        
        # UI feedback
        context.area.header_text_set("⚡ Edge Constraint ACTIVE | G/R/S = Transform | ESC = Exit Mode")
        
        return {'RUNNING_MODAL'}
    
    def _cancel_transform(self, context):
        """Cancel transform and restore positions"""
        # Restore original positions
        for v in self._constraint_data.selected_verts:
            if v.index in self._original_positions:
                v.co = self._original_positions[v.index]
        
        # Update mesh
        obj = context.active_object
        bmesh.update_edit_mesh(obj.data)
        
        self._in_transform = False
        self._transform_type = None
        self._original_positions = {}
        self._accumulated_delta = Vector((0, 0))
        
        # UI feedback
        context.area.header_text_set("⚡ Edge Constraint ACTIVE | G/R/S = Transform | ESC = Exit Mode")
        
        return {'RUNNING_MODAL'}
    
    def _setup_draw_handler(self, context):
        """Setup viewport drawing"""
        if EdgeConstraintState.draw_handler is None:
            EdgeConstraintState.draw_handler = bpy.types.SpaceView3D.draw_handler_add(
                draw_constraint_visualization, 
                (), 
                'WINDOW', 
                'POST_VIEW'
            )
    
    def _exit_modal(self, context):
        """Clean exit from modal"""
        # Remove timer
        if self._timer:
            context.window_manager.event_timer_remove(self._timer)
            self._timer = None
        
        # Remove draw handler
        if EdgeConstraintState.draw_handler:
            try:
                bpy.types.SpaceView3D.draw_handler_remove(EdgeConstraintState.draw_handler, 'WINDOW')
            except:
                pass
            EdgeConstraintState.draw_handler = None
        
        # Clear draw data
        draw_data['active_edges'] = []
        
        # Reset state
        EdgeConstraintState.reset()
        
        # Clear header
        context.area.header_text_set(None)
        context.area.tag_redraw()
        
        return {'FINISHED'}


# ============================================================================
# TOGGLE OPERATOR
# ============================================================================

class VIEW3D_OT_toggle_edge_constraint(Operator):
    """Toggle Edge Constraint Mode on/off"""
    bl_idname = "view3d.toggle_edge_constraint"
    bl_label = "Toggle Edge Constraint"
    bl_description = "Toggle persistent edge constraint mode"
    bl_options = {'REGISTER'}
    
    def execute(self, context):
        if EdgeConstraintState.enabled:
            # Disable
            EdgeConstraintState.enabled = False
            self.report({'INFO'}, "Edge Constraint Mode DISABLED")
        else:
            # Enable
            bpy.ops.view3d.edge_constraint_mode_persistent('INVOKE_DEFAULT')
        
        return {'FINISHED'}


# ============================================================================
# UI PANEL
# ============================================================================

class VIEW3D_PT_edge_constraint_panel_v2(Panel):
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Tool'
    bl_label = "Edge Constraint V2"
    bl_context = "mesh_edit"
    
    def draw(self, context):
        layout = self.layout
        scene = context.scene
        
        # Status indicator
        if EdgeConstraintState.enabled:
            box = layout.box()
            box.alert = True
            col = box.column(align=True)
            col.label(text="⚡ MODE ACTIVE", icon='PLAY')
            col.label(text="Press G/R/S to transform")
        
        # Main toggle button
        col = layout.column(align=True)
        col.scale_y = 1.8
        
        if EdgeConstraintState.enabled:
            col.operator(
                "view3d.toggle_edge_constraint",
                text="Disable Edge Constraint",
                icon='PAUSE',
                depress=True
            )
        else:
            col.operator(
                "view3d.toggle_edge_constraint",
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
        
        layout.separator()
        
        # Features
        box = layout.box()
        box.label(text="Features:", icon='OPTIONS')
        col = box.column(align=True)
        col.label(text="✓ Persistent mode - stays active")
        col.label(text="✓ Works with G/R/S tools")
        col.label(text="✓ Multi-lane edge support")
        col.label(text="✓ Real-time selection update")
        
        layout.separator()
        
        # Usage
        box = layout.box()
        box.label(text="Usage:", icon='INFO')
        col = box.column(align=True)
        col.label(text="1. Select vertices/edges")
        col.label(text="2. Click 'Enable'")
        col.label(text="3. Press G/R/S anytime")
        col.label(text="4. Move mouse to adjust")
        col.label(text="5. LMB to confirm")
        col.label(text="6. ESC to exit mode")
        
        layout.separator()
        
        # Links
        box = layout.box()
        box.label(text="Resources:", icon='URL')
        col = box.column(align=True)
        col.operator("wm.url_open", text="GitHub", icon='URL').url = "https://github.com/Stephk0/Toolings"
        col.operator("wm.url_open", text="My Artstation", icon='URL').url = "https://www.artstation.com/stephko"
        
        layout.separator()
        col = layout.column()
        col.label(text="Maintainer: Stephan Viranyi + Claude", icon='USER')


# ============================================================================
# PROPERTIES
# ============================================================================

def register_properties():
    bpy.types.Scene.ec_use_clamp = BoolProperty(
        name="Clamp to Boundaries",
        description="Stop at edge endpoints",
        default=True
    )
    
    bpy.types.Scene.ec_constrain_to_selected = BoolProperty(
        name="Selected Edges Only",
        description="Only slide along selected edges",
        default=False
    )

def unregister_properties():
    del bpy.types.Scene.ec_use_clamp
    del bpy.types.Scene.ec_constrain_to_selected


# ============================================================================
# REGISTRATION
# ============================================================================

classes = (
    VIEW3D_OT_edge_constraint_mode_persistent,
    VIEW3D_OT_toggle_edge_constraint,
    VIEW3D_PT_edge_constraint_panel_v2,
)

def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    register_properties()
    print("✓ Edge Constraint Mode V2 (Persistent) registered")
    
def unregister():
    # Clean up state
    EdgeConstraintState.reset()
    
    unregister_properties()
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
    print("✓ Edge Constraint Mode V2 unregistered")

if __name__ == "__main__":
    register()
