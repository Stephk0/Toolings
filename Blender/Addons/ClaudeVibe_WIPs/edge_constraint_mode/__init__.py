# ##### BEGIN GPL LICENSE BLOCK #####
#
#  This program is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either version 2
#  of the License, or (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software Foundation,
#  Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#
# ##### END GPL LICENSE BLOCK #####

bl_info = {
    "name": "Edge Constraint Mode",
    "author": "Stephan Viranyi + Claude",
    "version": (1, 0, 0),
    "blender": (3, 0, 0),
    "location": "View3D > Sidebar > Tool > Edge Constraint",
    "description": "Constrain transforms (Translate, Rotate, Scale) to flow along existing edge topology",
    "warning": "",
    "doc_url": "https://github.com/Stephk0/Toolings",
    "tracker_url": "https://github.com/Stephk0/Toolings/issues",
    "category": "Mesh",
}

import bpy
import bmesh
import gpu
import mathutils
from mathutils import Vector, Matrix
from gpu_extras.batch import batch_for_shader
from bpy.props import BoolProperty, EnumProperty, FloatProperty
import math

# Global variables for drawing
_draw_handler = None
_edge_paths = []


# ============================================================================
# Edge Constraint Math & Topology
# ============================================================================

class EdgeConstraintSolver:
    """Handles the mathematical projection and sliding along edge topology."""
    
    def __init__(self, bm, selected_verts, settings):
        self.bm = bm
        self.selected_verts = selected_verts
        self.settings = settings
        
        # Build adjacency and cache original positions
        self.original_positions = {v: v.co.copy() for v in selected_verts}
        self.vertex_edges = self._build_adjacency()
        
    def _build_adjacency(self):
        """Build adjacency map: vertex -> list of (connected_vertex, edge, length)."""
        adjacency = {}
        
        for v in self.selected_verts:
            edges_info = []
            for edge in v.link_edges:
                # Check if we should constrain to selected edges only
                if self.settings.constrain_to_selected and not edge.select:
                    continue
                    
                other_v = edge.other_vert(v)
                length = (other_v.co - v.co).length
                direction = (other_v.co - v.co).normalized()
                
                edges_info.append({
                    'vertex': other_v,
                    'edge': edge,
                    'length': length,
                    'direction': direction
                })
            
            adjacency[v] = edges_info
        
        return adjacency
    
    def get_edge_tangent_subspace(self, v):
        """Get the allowed motion directions for a vertex (edge tangent directions)."""
        if v not in self.vertex_edges or not self.vertex_edges[v]:
            return []
        
        return [info['direction'] for info in self.vertex_edges[v]]
    
    def project_to_edge_space(self, v, desired_displacement):
        """Project a desired displacement onto the edge tangent subspace."""
        tangents = self.get_edge_tangent_subspace(v)
        
        if not tangents:
            return Vector((0, 0, 0)), None
        
        # Find the edge direction that best aligns with the desired displacement
        best_abs_dot = 0.0
        best_tangent = None
        best_edge_info = None
        
        for i, tangent in enumerate(tangents):
            dot = desired_displacement.dot(tangent)
            abs_dot = abs(dot)
            if abs_dot > best_abs_dot:
                best_abs_dot = abs_dot
                best_tangent = tangent
                best_edge_info = self.vertex_edges[v][i]
        
        if best_tangent is None or best_abs_dot < 0.001:
            return Vector((0, 0, 0)), None
        
        # Project displacement onto the best-aligned edge
        projected_magnitude = desired_displacement.dot(best_tangent)
        projected_displacement = best_tangent * projected_magnitude
        
        return projected_displacement, best_edge_info
    
    def slide_along_topology(self, v, distance, direction_hint=None):
        """
        Slide a vertex along its edge topology by a given distance.
        Returns the new position and whether we hit a boundary.
        """
        if v not in self.vertex_edges or not self.vertex_edges[v]:
            return v.co.copy(), True
        
        current_pos = v.co.copy()
        remaining_distance = abs(distance)
        direction_sign = 1.0 if distance >= 0 else -1.0
        
        # Choose initial edge based on direction hint
        edge_info = None
        if direction_hint is not None:
            best_dot = -1.0
            for info in self.vertex_edges[v]:
                dot = abs(direction_hint.dot(info['direction']))
                if dot > best_dot:
                    best_dot = dot
                    edge_info = info
        else:
            edge_info = self.vertex_edges[v][0] if self.vertex_edges[v] else None
        
        if edge_info is None:
            return current_pos, True
        
        # Start sliding
        visited_edges = set()
        max_iterations = 100  # Prevent infinite loops
        iteration = 0
        hit_boundary = False
        
        while remaining_distance > 0.001 and iteration < max_iterations:
            iteration += 1
            
            # Check if we've visited this edge already (prevent loops)
            edge_key = (edge_info['edge'].index, direction_sign > 0)
            if edge_key in visited_edges:
                hit_boundary = True
                break
            visited_edges.add(edge_key)
            
            # Get the effective direction (may need to flip)
            effective_direction = edge_info['direction'] * direction_sign
            edge_length = edge_info['length']
            
            if remaining_distance <= edge_length:
                # Can complete the slide on this edge
                current_pos += effective_direction * remaining_distance
                remaining_distance = 0
            else:
                # Slide to the end of this edge and continue
                current_pos += effective_direction * edge_length
                remaining_distance -= edge_length
                
                # Find the next edge at the target vertex
                next_vertex = edge_info['vertex']
                if next_vertex not in self.vertex_edges or not self.vertex_edges[next_vertex]:
                    hit_boundary = True
                    break
                
                # Choose next edge that continues in the same general direction
                next_edge_info = None
                best_continuity = -2.0
                
                for next_info in self.vertex_edges[next_vertex]:
                    # Skip the edge we just came from
                    if next_info['edge'] == edge_info['edge']:
                        continue
                    
                    continuity = effective_direction.dot(next_info['direction'])
                    if continuity > best_continuity:
                        best_continuity = continuity
                        next_edge_info = next_info
                
                if next_edge_info is None or (self.settings.stop_at_nonmanifold and best_continuity < 0.1):
                    hit_boundary = True
                    break
                
                edge_info = next_edge_info
        
        # Apply clamping if enabled
        if self.settings.use_clamp and hit_boundary:
            pass  # Position is already at boundary
        
        return current_pos, hit_boundary
    
    def apply_constrained_translation(self, delta):
        """Apply a translation constrained to edges."""
        for v in self.selected_verts:
            projected_delta, edge_info = self.project_to_edge_space(v, delta)
            
            if edge_info:
                distance = projected_delta.length
                if delta.dot(projected_delta) < 0:
                    distance = -distance
                
                new_pos, _ = self.slide_along_topology(v, distance, projected_delta.normalized())
                v.co = new_pos
    
    def apply_constrained_rotation(self, pivot, axis, angle):
        """Apply a rotation constrained to edges."""
        rot_matrix = Matrix.Rotation(angle, 3, axis)
        
        for v in self.selected_verts:
            # Compute unconstrained rotated position
            relative_pos = v.co - pivot
            rotated_relative = rot_matrix @ relative_pos
            unconstrained_target = pivot + rotated_relative
            
            # Desired displacement
            desired_delta = unconstrained_target - v.co
            
            # Project and slide along edges
            projected_delta, edge_info = self.project_to_edge_space(v, desired_delta)
            
            if edge_info:
                distance = projected_delta.length
                if desired_delta.dot(projected_delta) < 0:
                    distance = -distance
                
                new_pos, _ = self.slide_along_topology(v, distance, projected_delta.normalized())
                v.co = new_pos
    
    def apply_constrained_scale(self, pivot, scale_factors):
        """Apply a scale constrained to edges."""
        # For uniform scaling, use the average scale factor
        avg_scale = sum(scale_factors) / len(scale_factors)
        
        for v in self.selected_verts:
            # Compute unconstrained scaled position
            relative_pos = v.co - pivot
            scaled_relative = relative_pos * avg_scale
            unconstrained_target = pivot + scaled_relative
            
            # Desired displacement
            desired_delta = unconstrained_target - v.co
            
            # Project and slide along edges
            projected_delta, edge_info = self.project_to_edge_space(v, desired_delta)
            
            if edge_info:
                distance = projected_delta.length
                if desired_delta.dot(projected_delta) < 0:
                    distance = -distance
                
                new_pos, _ = self.slide_along_topology(v, distance, projected_delta.normalized())
                v.co = new_pos
    
    def restore_original_positions(self):
        """Restore vertices to their original positions."""
        for v, pos in self.original_positions.items():
            v.co = pos


# ============================================================================
# Visual Feedback
# ============================================================================

def draw_edge_paths():
    """Draw edge path hints in the viewport."""
    global _edge_paths
    
    if not _edge_paths:
        return
    
    shader = gpu.shader.from_builtin('UNIFORM_COLOR')
    
    # Draw paths
    for path in _edge_paths:
        if len(path) < 2:
            continue
        
        batch = batch_for_shader(shader, 'LINE_STRIP', {"pos": path})
        shader.bind()
        shader.uniform_float("color", (0.2, 0.8, 1.0, 0.8))
        batch.draw(shader)


def update_edge_path_visualization(bm, selected_verts, solver):
    """Update the edge paths for visualization."""
    global _edge_paths
    _edge_paths = []
    
    for v in selected_verts:
        if v not in solver.vertex_edges or not solver.vertex_edges[v]:
            continue
        
        # Draw paths along each connected edge
        for edge_info in solver.vertex_edges[v]:
            path = [v.co.copy(), edge_info['vertex'].co.copy()]
            _edge_paths.append(path)


# ============================================================================
# Modal Operator
# ============================================================================

class VIEW3D_OT_edge_constraint_mode(bpy.types.Operator):
    """Edge-constrained transform mode for mesh editing"""
    bl_idname = "view3d.edge_constraint_mode"
    bl_label = "Edge Constraint Mode"
    bl_options = {'REGISTER', 'UNDO'}
    
    # Transform type
    transform_type: EnumProperty(
        name="Transform Type",
        items=[
            ('TRANSLATE', "Translate", ""),
            ('ROTATE', "Rotate", ""),
            ('SCALE', "Scale", ""),
        ],
        default='TRANSLATE'
    )
    
    def __init__(self):
        self.bm = None
        self.obj = None
        self.selected_verts = []
        self.solver = None
        self.initial_mouse = None
        self.current_mouse = None
        self.pivot = Vector((0, 0, 0))
        self.transform_started = False
        self.draw_handler = None
        self.settings = None
    
    def invoke(self, context, event):
        # Verify we're in Edit Mode with a mesh
        if context.mode != 'EDIT_MESH':
            self.report({'WARNING'}, "Must be in Edit Mode on a mesh object")
            return {'CANCELLED'}
        
        self.obj = context.edit_object
        if self.obj.type != 'MESH':
            self.report({'WARNING'}, "Active object must be a mesh")
            return {'CANCELLED'}
        
        # Get BMesh
        self.bm = bmesh.from_edit_mesh(self.obj.data)
        
        # Get selected vertices
        self.selected_verts = [v for v in self.bm.verts if v.select]
        
        if not self.selected_verts:
            self.report({'WARNING'}, "No vertices selected")
            return {'CANCELLED'}
        
        # Get settings from scene
        self.settings = context.scene.edge_constraint_settings
        
        # Initialize solver
        self.solver = EdgeConstraintSolver(self.bm, self.selected_verts, self.settings)
        
        # Calculate pivot (use 3D cursor or selection center)
        if self.settings.pivot_mode == 'CURSOR':
            self.pivot = context.scene.cursor.location.copy()
        else:  # CENTER
            self.pivot = sum((v.co for v in self.selected_verts), Vector()) / len(self.selected_verts)
        
        # Store initial mouse position
        self.initial_mouse = Vector((event.mouse_region_x, event.mouse_region_y))
        self.current_mouse = self.initial_mouse.copy()
        
        # Setup visual feedback
        global _draw_handler
        if _draw_handler is None:
            _draw_handler = bpy.types.SpaceView3D.draw_handler_add(
                draw_edge_paths, (), 'WINDOW', 'POST_VIEW'
            )
        
        update_edge_path_visualization(self.bm, self.selected_verts, self.solver)
        
        # Add modal handler
        context.window_manager.modal_handler_add(self)
        
        # Update header
        context.area.header_text_set("Edge Constraint Mode: Moving | Confirm: LMB/Enter | Cancel: RMB/Esc")
        
        return {'RUNNING_MODAL'}
    
    def modal(self, context, event):
        context.area.tag_redraw()
        
        # Update current mouse
        self.current_mouse = Vector((event.mouse_region_x, event.mouse_region_y))
        
        # Handle events
        if event.type in {'ESC', 'RIGHTMOUSE'}:
            # Cancel
            self.cleanup(context)
            self.solver.restore_original_positions()
            bmesh.update_edit_mesh(self.obj.data)
            self.report({'INFO'}, "Edge Constraint Mode cancelled")
            return {'CANCELLED'}
        
        elif event.type in {'LEFTMOUSE', 'RET'} and event.value == 'PRESS':
            # Confirm
            self.cleanup(context)
            bmesh.update_edit_mesh(self.obj.data)
            self.report({'INFO'}, "Edge Constraint Mode confirmed")
            return {'FINISHED'}
        
        elif event.type == 'MOUSEMOVE':
            # Apply transform based on mouse movement
            self.apply_transform(context, event)
            bmesh.update_edit_mesh(self.obj.data)
            update_edge_path_visualization(self.bm, self.selected_verts, self.solver)
            return {'RUNNING_MODAL'}
        
        elif event.type == 'G' and event.value == 'PRESS':
            self.transform_type = 'TRANSLATE'
            self.initial_mouse = self.current_mouse.copy()
            self.solver.restore_original_positions()
            context.area.header_text_set("Edge Constraint Mode: Translate | Confirm: LMB/Enter | Cancel: RMB/Esc")
            return {'RUNNING_MODAL'}
        
        elif event.type == 'R' and event.value == 'PRESS':
            self.transform_type = 'ROTATE'
            self.initial_mouse = self.current_mouse.copy()
            self.solver.restore_original_positions()
            context.area.header_text_set("Edge Constraint Mode: Rotate | Confirm: LMB/Enter | Cancel: RMB/Esc")
            return {'RUNNING_MODAL'}
        
        elif event.type == 'S' and event.value == 'PRESS':
            self.transform_type = 'SCALE'
            self.initial_mouse = self.current_mouse.copy()
            self.solver.restore_original_positions()
            context.area.header_text_set("Edge Constraint Mode: Scale | Confirm: LMB/Enter | Cancel: RMB/Esc")
            return {'RUNNING_MODAL'}
        
        return {'RUNNING_MODAL'}
    
    def apply_transform(self, context, event):
        """Apply the current transform based on mouse delta."""
        mouse_delta = self.current_mouse - self.initial_mouse
        
        if self.transform_type == 'TRANSLATE':
            # Convert 2D mouse delta to 3D world delta
            # Use view direction and up vector
            region = context.region
            rv3d = context.region_data
            
            # Simple approach: use horizontal and vertical screen space
            sensitivity = self.settings.translate_sensitivity
            delta_3d = Vector((mouse_delta.x * sensitivity, 0, mouse_delta.y * sensitivity))
            
            # Transform to world space (approximate)
            view_matrix = rv3d.view_matrix.inverted()
            delta_world = view_matrix.to_3x3() @ delta_3d
            
            self.solver.apply_constrained_translation(delta_world)
        
        elif self.transform_type == 'ROTATE':
            # Rotation angle based on horizontal mouse movement
            angle = mouse_delta.x * self.settings.rotate_sensitivity * 0.01
            
            # Use view normal as rotation axis
            rv3d = context.region_data
            view_axis = rv3d.view_rotation @ Vector((0, 0, 1))
            
            self.solver.apply_constrained_rotation(self.pivot, view_axis, angle)
        
        elif self.transform_type == 'SCALE':
            # Scale factor based on horizontal mouse movement
            scale_delta = 1.0 + (mouse_delta.x * self.settings.scale_sensitivity * 0.001)
            scale_delta = max(0.01, scale_delta)  # Prevent negative scale
            
            self.solver.apply_constrained_scale(self.pivot, [scale_delta, scale_delta, scale_delta])
    
    def cleanup(self, context):
        """Clean up the operator."""
        global _draw_handler
        
        # Remove draw handler
        if _draw_handler is not None:
            bpy.types.SpaceView3D.draw_handler_remove(_draw_handler, 'WINDOW')
            _draw_handler = None
        
        # Clear header
        context.area.header_text_set(None)
        
        # Clear paths
        global _edge_paths
        _edge_paths = []


# ============================================================================
# Settings
# ============================================================================

class EdgeConstraintSettings(bpy.types.PropertyGroup):
    """Settings for Edge Constraint Mode."""
    
    constrain_to_selected: BoolProperty(
        name="Constrain to Selected Edges Only",
        description="Only slide along edges that are selected",
        default=False
    )
    
    use_even: BoolProperty(
        name="Even Spacing",
        description="Maintain even spacing along edges (like Edge Slide)",
        default=False
    )
    
    use_clamp: BoolProperty(
        name="Clamp to Boundaries",
        description="Stop at edge endpoints instead of allowing overshoot",
        default=True
    )
    
    stop_at_nonmanifold: BoolProperty(
        name="Stop at Non-Manifold",
        description="Stop sliding at non-manifold boundaries",
        default=True
    )
    
    pivot_mode: EnumProperty(
        name="Pivot Mode",
        description="Pivot point for rotation and scale",
        items=[
            ('CENTER', "Selection Center", "Use center of selection"),
            ('CURSOR', "3D Cursor", "Use 3D cursor location"),
        ],
        default='CENTER'
    )
    
    translate_sensitivity: FloatProperty(
        name="Translate Sensitivity",
        description="Mouse sensitivity for translation",
        default=0.01,
        min=0.001,
        max=1.0
    )
    
    rotate_sensitivity: FloatProperty(
        name="Rotate Sensitivity",
        description="Mouse sensitivity for rotation",
        default=1.0,
        min=0.1,
        max=10.0
    )
    
    scale_sensitivity: FloatProperty(
        name="Scale Sensitivity",
        description="Mouse sensitivity for scaling",
        default=1.0,
        min=0.1,
        max=10.0
    )


# ============================================================================
# UI Panel
# ============================================================================

class VIEW3D_PT_edge_constraint(bpy.types.Panel):
    """Panel for Edge Constraint Mode controls."""
    bl_label = "Edge Constraint Mode"
    bl_idname = "VIEW3D_PT_edge_constraint"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Tool'
    bl_context = 'mesh_edit'
    
    def draw(self, context):
        layout = self.layout
        settings = context.scene.edge_constraint_settings
        
        # Main operator button
        layout.operator("view3d.edge_constraint_mode", text="Activate Edge Constraint Mode", icon='CON_FOLLOWPATH')
        
        layout.separator()
        
        # Settings
        box = layout.box()
        box.label(text="Settings:", icon='SETTINGS')
        
        box.prop(settings, "constrain_to_selected")
        box.prop(settings, "use_even")
        box.prop(settings, "use_clamp")
        box.prop(settings, "stop_at_nonmanifold")
        box.prop(settings, "pivot_mode")
        
        box.separator()
        
        # Sensitivity settings
        col = box.column(align=True)
        col.label(text="Sensitivity:")
        col.prop(settings, "translate_sensitivity")
        col.prop(settings, "rotate_sensitivity")
        col.prop(settings, "scale_sensitivity")
        
        layout.separator()
        
        # Links
        box = layout.box()
        box.label(text="Resources:", icon='URL')
        row = box.row()
        row.operator("wm.url_open", text="GitHub", icon='URL').url = "https://github.com/Stephk0/Toolings"
        row.operator("wm.url_open", text="My ArtStation", icon='URL').url = "https://www.artstation.com/stephko"
        
        # Instructions
        layout.separator()
        box = layout.box()
        box.label(text="Usage:", icon='INFO')
        col = box.column(align=True)
        col.label(text="1. Select vertices/edges/faces")
        col.label(text="2. Click 'Activate Edge Constraint Mode'")
        col.label(text="3. Move mouse to transform")
        col.label(text="4. Press G/R/S to switch modes")
        col.label(text="5. Confirm with LMB or Enter")
        col.label(text="6. Cancel with RMB or Esc")


# ============================================================================
# Registration
# ============================================================================

classes = (
    EdgeConstraintSettings,
    VIEW3D_OT_edge_constraint_mode,
    VIEW3D_PT_edge_constraint,
)

def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    
    bpy.types.Scene.edge_constraint_settings = bpy.props.PointerProperty(type=EdgeConstraintSettings)

def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
    
    del bpy.types.Scene.edge_constraint_settings
    
    # Clean up draw handler
    global _draw_handler
    if _draw_handler is not None:
        bpy.types.SpaceView3D.draw_handler_remove(_draw_handler, 'WINDOW')
        _draw_handler = None

if __name__ == "__main__":
    register()
