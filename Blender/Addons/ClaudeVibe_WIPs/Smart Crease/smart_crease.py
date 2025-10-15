"""
Smart Crease - Context-Sensitive Crease Tool for Blender
=========================================================

A modal operator that intelligently adjusts vertex or edge crease values based on
the current selection mode (Vertex/Edge/Face), with mouse drag control, 0/1 toggle,
and on-screen HUD display.

Features:
- Vertex mode: edits vertex crease on selected vertices
- Edge mode: edits edge crease on selected edges
- Face mode: edits edge crease on boundary edges of selected faces
- Modal mouse drag with precision/snap modifiers
- Quick preset keys: 1-9 set crease to 0.1-0.9, 0 sets to 1.0 (full crease)
- Alt key toggles between 0 and 1
- Live HUD display at drag position

Author: Stephan Viranyi + Claude
Version: 1.4.0
Blender: 4.0+
Link: https://github.com/Stephk0/Toolings
"""

bl_info = {
    "name": "Smart Crease",
    "author": "Stephan Viranyi + Claude",
    "version": (1, 4, 0),
    "blender": (4, 0, 0),
    "location": "Edit Mode > Mesh > Shift+E",
    "description": "Context-sensitive crease tool with modal control, quick presets (1-9, 0), and Alt toggle (0/1)",
    "category": "Mesh",
    "doc_url": "https://github.com/Stephk0/Toolings",
}

import bpy
import bmesh
import blf
import gpu
from gpu_extras.batch import batch_for_shader
from bpy.props import FloatProperty, IntProperty
from mathutils import Vector
import math


# Global storage for HUD drawing
_hud_data = {
    'active': False,
    'position': (0, 0),
    'value': 0.0,
    'domain': 'Edge',
    'font_id': 0
}


def draw_hud():
    """Draw HUD overlay showing current crease value"""
    if not _hud_data['active']:
        return
    
    font_id = _hud_data['font_id']
    x, y = _hud_data['position']
    value = _hud_data['value']
    domain = _hud_data['domain']
    
    # Set font properties
    blf.size(font_id, 16)
    blf.color(font_id, 1.0, 1.0, 1.0, 1.0)
    
    # Draw text
    text = f"Smart Crease — {domain}: {value:.2f}"
    blf.position(font_id, x + 20, y + 20, 0)
    blf.draw(font_id, text)


# HUD drawing handler
_draw_handler = None


def enable_hud():
    """Enable HUD drawing"""
    global _draw_handler
    if _draw_handler is None:
        _draw_handler = bpy.types.SpaceView3D.draw_handler_add(
            draw_hud, (), 'WINDOW', 'POST_PIXEL'
        )
        _hud_data['active'] = True


def disable_hud():
    """Disable HUD drawing"""
    global _draw_handler
    if _draw_handler is not None:
        bpy.types.SpaceView3D.draw_handler_remove(_draw_handler, 'WINDOW')
        _draw_handler = None
    _hud_data['active'] = False


class MESH_OT_smart_crease(bpy.types.Operator):
    """Context-sensitive crease tool with modal control
    
    Keyboard Shortcuts:
    - Numbers 1-9: Set crease to 0.1-0.9
    - Number 0: Set crease to 1.0 (full crease)
    - Alt: Toggle between 0 and 1
    - Shift+Numbers or Numpad: Enter decimal values (e.g., 0.75)
    - Shift: Precision mode (fine control)
    - Ctrl: Snap mode (0.1 increments)
    - Mouse: Drag to adjust value
    - Enter/Space/LMB: Confirm
    - Esc/RMB: Cancel
    """
    bl_idname = "mesh.smart_crease"
    bl_label = "Smart Crease"
    bl_options = {'REGISTER', 'UNDO', 'GRAB_CURSOR', 'BLOCKING'}
    
    @classmethod
    def poll(cls, context):
        return (context.mode == 'EDIT_MESH' and 
                context.active_object and 
                context.active_object.type == 'MESH')
        
    def invoke(self, context, event):
        """Initialize operator on invocation"""
        # Initialize instance variables
        self.initial_mouse_x = 0
        self.initial_mouse_y = 0
        self.initial_values = {}
        self.target_elements = []
        self.domain = 'EDGE'  # 'VERTEX' or 'EDGE'
        self.display_value = 0.0
        self.base_value = 0.0
        self.bm = None
        self.numeric_input = ""
        self.has_numeric = False
        self.toggle_state = None  # For alternating 0/1
        self.sensitivity = 0.005
        self.precision_mode = False
        self.snap_mode = False
        
        self.obj = context.active_object
        
        # Enter edit mode if needed
        if context.mode != 'EDIT_MESH':
            bpy.ops.object.mode_set(mode='EDIT')
        
        # Get mesh and bmesh
        me = self.obj.data
        self.bm = bmesh.from_edit_mesh(me)
        
        # Ensure bmesh is up to date
        self.bm.verts.ensure_lookup_table()
        self.bm.edges.ensure_lookup_table()
        self.bm.faces.ensure_lookup_table()
        
        # Determine selection mode and target domain
        select_mode = context.tool_settings.mesh_select_mode
        
        if select_mode[0]:  # Vertex mode
            self.domain = 'VERTEX'
            domain_name = 'Vertex'
        elif select_mode[1]:  # Edge mode
            self.domain = 'EDGE'
            domain_name = 'Edge'
        elif select_mode[2]:  # Face mode
            self.domain = 'EDGE'  # Boundary edges
            domain_name = 'Face→Boundary'
        else:
            self.domain = 'EDGE'
            domain_name = 'Edge'
        
        # Build target element set
        success = self.build_target_set(context)
        if not success:
            self.report({'WARNING'}, "No selected elements")
            return {'CANCELLED'}
        
        # Store initial mouse position
        self.initial_mouse_x = event.mouse_x
        self.initial_mouse_y = event.mouse_y
        
        # Calculate initial/median value
        self.base_value = self.get_median_value()
        self.display_value = self.base_value
        
        # Get addon preferences
        prefs = context.preferences.addons.get(__name__)
        if prefs:
            self.sensitivity = prefs.preferences.sensitivity
        
        # Setup HUD
        _hud_data['position'] = (event.mouse_region_x, event.mouse_region_y)
        _hud_data['value'] = self.display_value
        _hud_data['domain'] = domain_name
        enable_hud()
        
        # Add modal handler
        context.window_manager.modal_handler_add(self)
        return {'RUNNING_MODAL'}
    
    def build_target_set(self, context):
        """Build list of target elements based on selection mode"""
        select_mode = context.tool_settings.mesh_select_mode
        self.target_elements = []
        
        if select_mode[0]:  # Vertex mode
            # Get or create vertex crease layer FIRST (before getting elements)
            crease_layer = self.bm.verts.layers.float.get('crease_vert')
            if crease_layer is None:
                crease_layer = self.bm.verts.layers.float.new('crease_vert')
                # Update lookup table after creating layer
                self.bm.verts.ensure_lookup_table()
            self.crease_layer = crease_layer
            
            # NOW get the target elements (after layer creation)
            self.target_elements = [v for v in self.bm.verts if v.select and not v.hide]
            if not self.target_elements:
                return False
            
            # Store initial values
            for v in self.target_elements:
                self.initial_values[v.index] = v[self.crease_layer]
        
        elif select_mode[1]:  # Edge mode
            # Get or create edge crease layer FIRST (before getting elements)
            crease_layer = self.bm.edges.layers.float.get('crease_edge')
            if crease_layer is None:
                crease_layer = self.bm.edges.layers.float.new('crease_edge')
                # Update lookup table after creating layer
                self.bm.edges.ensure_lookup_table()
            self.crease_layer = crease_layer
            
            # NOW get the target elements (after layer creation)
            self.target_elements = [e for e in self.bm.edges if e.select and not e.hide]
            if not self.target_elements:
                return False
            
            # Store initial values
            for e in self.target_elements:
                self.initial_values[e.index] = e[self.crease_layer]
        
        elif select_mode[2]:  # Face mode - boundary edges
            # Get or create edge crease layer FIRST
            crease_layer = self.bm.edges.layers.float.get('crease_edge')
            if crease_layer is None:
                crease_layer = self.bm.edges.layers.float.new('crease_edge')
                # Update lookup tables after creating layer
                self.bm.edges.ensure_lookup_table()
                self.bm.faces.ensure_lookup_table()
            self.crease_layer = crease_layer
            
            # NOW get the selected faces (after layer creation)
            selected_faces = [f for f in self.bm.faces if f.select and not f.hide]
            if not selected_faces:
                return False
            
            # Find boundary edges (exactly one adjacent face is selected)
            boundary_edges = set()
            for edge in self.bm.edges:
                if edge.hide:
                    continue
                selected_count = sum(1 for f in edge.link_faces if f.select)
                if selected_count == 1:
                    boundary_edges.add(edge)
            
            self.target_elements = list(boundary_edges)
            if not self.target_elements:
                self.report({'WARNING'}, "No boundary edges found (entire mesh selected?)")
                return False
            
            # Store initial values
            for e in self.target_elements:
                self.initial_values[e.index] = e[self.crease_layer]
        
        return len(self.target_elements) > 0
    
    def get_median_value(self):
        """Calculate median crease value of target elements"""
        if not self.target_elements:
            return 0.0
        
        values = [elem[self.crease_layer] for elem in self.target_elements]
        return sum(values) / len(values) if values else 0.0
    
    def apply_value(self, value):
        """Apply crease value to all target elements"""
        value = max(0.0, min(1.0, value))  # Clamp to [0, 1]
        
        for elem in self.target_elements:
            elem[self.crease_layer] = value
        
        # Update mesh
        bmesh.update_edit_mesh(self.obj.data)
        
        # Update HUD
        _hud_data['value'] = value
    
    def restore_initial_values(self):
        """Restore initial crease values (for cancel)"""
        for elem in self.target_elements:
            elem[self.crease_layer] = self.initial_values[elem.index]
        
        bmesh.update_edit_mesh(self.obj.data)
    
    def toggle_zero_one(self):
        """Toggle between 0 and 1"""
        current = self.get_median_value()
        
        # Determine toggle target
        if abs(current - 0.0) < 0.01:
            target = 1.0
            self.toggle_state = 1.0
        elif abs(current - 1.0) < 0.01:
            target = 0.0
            self.toggle_state = 0.0
        else:
            # First press goes to 1, then alternates
            if self.toggle_state is None or self.toggle_state == 0.0:
                target = 1.0
                self.toggle_state = 1.0
            else:
                target = 0.0
                self.toggle_state = 0.0
        
        self.display_value = target
        self.apply_value(target)
    
    def modal(self, context, event):
        """Handle modal events"""
        context.area.tag_redraw()
        
        # Check for precision/snap modifiers
        self.precision_mode = event.shift
        self.snap_mode = event.ctrl
        
        # Mouse move - update value
        if event.type == 'MOUSEMOVE':
            if not self.has_numeric:
                # Calculate delta
                delta_x = event.mouse_x - self.initial_mouse_x
                delta_y = event.mouse_y - self.initial_mouse_y
                delta = (delta_x - delta_y) * self.sensitivity
                
                # Apply precision modifier
                if self.precision_mode:
                    delta *= 0.1
                
                # Calculate new value
                new_value = self.base_value + delta
                
                # Apply snap modifier
                if self.snap_mode:
                    new_value = round(new_value * 10) / 10
                
                self.display_value = max(0.0, min(1.0, new_value))
                self.apply_value(self.display_value)
        
        # Alt - toggle between 0 and 1
        elif event.type == 'LEFT_ALT' and event.value == 'PRESS':
            self.toggle_zero_one()
            self.has_numeric = False
            self.numeric_input = ""
            return {'RUNNING_MODAL'}
        
        # Quick preset keys (1-9 = 0.1-0.9, 0 = 1.0)
        elif event.type in {'ONE', 'TWO', 'THREE', 'FOUR', 'FIVE', 'SIX', 'SEVEN', 'EIGHT', 'NINE'} and event.value == 'PRESS' and not event.shift and not event.ctrl:
            # Map key to crease value: 1→0.1, 2→0.2, etc.
            key_map = {
                'ONE': 0.1, 'TWO': 0.2, 'THREE': 0.3, 'FOUR': 0.4, 'FIVE': 0.5,
                'SIX': 0.6, 'SEVEN': 0.7, 'EIGHT': 0.8, 'NINE': 0.9
            }
            self.display_value = key_map[event.type]
            self.apply_value(self.display_value)
            self.has_numeric = False
            self.numeric_input = ""
            return {'RUNNING_MODAL'}
        
        # Zero key = full crease (1.0)
        elif event.type == 'ZERO' and event.value == 'PRESS' and not event.shift and not event.ctrl:
            self.display_value = 1.0
            self.apply_value(1.0)
            self.has_numeric = False
            self.numeric_input = ""
            return {'RUNNING_MODAL'}
        
        # Numeric input (numpad for decimal values)
        elif event.type in {'NUMPAD_0', 'NUMPAD_1', 'NUMPAD_2', 'NUMPAD_3', 'NUMPAD_4', 'NUMPAD_5', 
                            'NUMPAD_6', 'NUMPAD_7', 'NUMPAD_8', 'NUMPAD_9', 'PERIOD', 'NUMPAD_PERIOD'} and event.value == 'PRESS':
            if event.type == 'PERIOD' or event.type == 'NUMPAD_PERIOD':
                char = '.'
            else:
                # Extract number from numpad key (e.g., 'NUMPAD_5' -> '5')
                char = event.type.split('_')[1]
            
            self.numeric_input += char
            self.has_numeric = True
            
            # Try to parse and apply
            try:
                value = float(self.numeric_input)
                self.display_value = max(0.0, min(1.0, value))
                self.apply_value(self.display_value)
            except ValueError:
                pass
        
        # Shift+number keys for decimal input (alternative to numpad)
        elif event.type in {'ZERO', 'ONE', 'TWO', 'THREE', 'FOUR', 'FIVE', 
                            'SIX', 'SEVEN', 'EIGHT', 'NINE'} and event.value == 'PRESS' and event.shift:
            key_to_num = {
                'ZERO': '0', 'ONE': '1', 'TWO': '2', 'THREE': '3', 'FOUR': '4',
                'FIVE': '5', 'SIX': '6', 'SEVEN': '7', 'EIGHT': '8', 'NINE': '9'
            }
            char = key_to_num[event.type]
            self.numeric_input += char
            self.has_numeric = True
            
            # Try to parse and apply
            try:
                value = float(self.numeric_input)
                self.display_value = max(0.0, min(1.0, value))
                self.apply_value(self.display_value)
            except ValueError:
                pass
        
        # Backspace - clear numeric input
        elif event.type == 'BACK_SPACE' and event.value == 'PRESS':
            if self.numeric_input:
                self.numeric_input = self.numeric_input[:-1]
                if self.numeric_input:
                    try:
                        value = float(self.numeric_input)
                        self.display_value = max(0.0, min(1.0, value))
                        self.apply_value(self.display_value)
                    except ValueError:
                        pass
                else:
                    self.has_numeric = False
                    self.display_value = self.base_value
                    self.apply_value(self.display_value)
        
        # Confirm
        elif event.type in {'LEFTMOUSE', 'RET', 'SPACE'} and event.value == 'PRESS':
            disable_hud()
            return {'FINISHED'}
        
        # Cancel
        elif event.type in {'RIGHTMOUSE', 'ESC'}:
            self.restore_initial_values()
            disable_hud()
            return {'CANCELLED'}
        
        return {'RUNNING_MODAL'}


class SmartCreasePreferences(bpy.types.AddonPreferences):
    """Preferences for Smart Crease addon"""
    bl_idname = __name__
    
    sensitivity: FloatProperty(
        name="Mouse Sensitivity",
        description="Sensitivity for mouse drag control",
        default=0.005,
        min=0.001,
        max=0.02,
    )
    
    snap_increment: FloatProperty(
        name="Snap Increment",
        description="Snap increment when Ctrl is held",
        default=0.1,
        min=0.01,
        max=0.5,
    )
    
    hud_font_size: IntProperty(
        name="HUD Font Size",
        description="Font size for HUD display",
        default=16,
        min=10,
        max=30,
    )
    
    def draw(self, context):
        layout = self.layout
        
        # Main settings
        box = layout.box()
        box.label(text="Smart Crease Settings:", icon='PREFERENCES')
        box.prop(self, "sensitivity")
        box.prop(self, "snap_increment")
        box.prop(self, "hud_font_size")
        
        # Usage info
        layout.separator()
        info_box = layout.box()
        info_box.label(text="Usage (during Smart Crease operation):", icon='INFO')
        col = info_box.column(align=True)
        col.label(text="• 1-9: Set crease to 0.1-0.9")
        col.label(text="• 0: Set crease to 1.0 (full crease)")
        col.label(text="• Alt: Toggle between 0 and 1")
        col.label(text="• Shift: Precision mode")
        col.label(text="• Ctrl: Snap mode")
        col.label(text="• Mouse drag: Adjust value")
        
        # Links
        layout.separator()
        links_box = layout.box()
        links_box.label(text="Links:", icon='URL')
        row = links_box.row()
        row.operator("wm.url_open", text="Github", icon='URL').url = "https://github.com/Stephk0/Toolings"
        row.operator("wm.url_open", text="My Artstation", icon='URL').url = "https://www.artstation.com/stephko"


# Keymap storage
addon_keymaps = []


def register():
    """Register addon"""
    bpy.utils.register_class(MESH_OT_smart_crease)
    bpy.utils.register_class(SmartCreasePreferences)
    
    # Add keymap
    wm = bpy.context.window_manager
    kc = wm.keyconfigs.addon
    if kc:
        km = kc.keymaps.new(name='Mesh', space_type='EMPTY')
        kmi = km.keymap_items.new(
            MESH_OT_smart_crease.bl_idname,
            type='E',
            value='PRESS',
            shift=True
        )
        addon_keymaps.append((km, kmi))


def unregister():
    """Unregister addon"""
    # Remove HUD if active
    disable_hud()
    
    # Remove keymaps
    for km, kmi in addon_keymaps:
        km.keymap_items.remove(kmi)
    addon_keymaps.clear()
    
    bpy.utils.unregister_class(SmartCreasePreferences)
    bpy.utils.unregister_class(MESH_OT_smart_crease)


if __name__ == "__main__":
    register()
