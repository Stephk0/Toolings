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
    "name": "Smart Set Orientation",
    "author": "Stephko, Claude AI",
    "version": (1, 5, 0),
    "blender": (3, 0, 0),
    "location": "3D Viewport > Ctrl+D",
    "description": "Intelligently set transform orientation based on context and selection",
    "warning": "",
    "doc_url": "",
    "category": "3D View",
}

import bpy
import bmesh
from bpy.types import Operator, AddonPreferences
from bpy.props import StringProperty, BoolProperty
import hashlib


class MESH_OT_smart_set_orientation(Operator):
    """Set transform orientation intelligently based on context"""
    bl_idname = "mesh.smart_set_orientation"
    bl_label = "Smart Set Orientation"
    bl_description = "Toggle transform orientation based on mode and selection"
    bl_options = {'REGISTER', 'UNDO'}
    
    # Class variable to store the last selection hash
    _last_selection_hash = None
    
    @classmethod
    def poll(cls, context):
        """Check if operator can run"""
        return (context.area is not None and 
                context.area.type == 'VIEW_3D' and
                context.region is not None)
    
    def get_selection_hash(self, context):
        """Generate a hash of the current selection to detect changes"""
        if context.mode != 'EDIT_MESH' or not context.active_object:
            return None
            
        obj = context.active_object
        if obj.type != 'MESH':
            return None
            
        me = obj.data
        if not me.is_editmode:
            return None
            
        bm = bmesh.from_edit_mesh(me)
        
        # Ensure internal indices are updated
        bm.verts.ensure_lookup_table()
        bm.edges.ensure_lookup_table()
        bm.faces.ensure_lookup_table()
        
        # Get indices of selected elements
        selected_verts = tuple(sorted(v.index for v in bm.verts if v.select))
        selected_edges = tuple(sorted(e.index for e in bm.edges if e.select))
        selected_faces = tuple(sorted(f.index for f in bm.faces if f.select))
        
        # Create a string representation of the selection
        selection_str = f"v{selected_verts}_e{selected_edges}_f{selected_faces}"
        
        # Return hash of the selection
        return hashlib.md5(selection_str.encode()).hexdigest()
    
    def create_orientation_from_selection(self, context):
        """Create a custom orientation from the current selection"""
        try:
            # Store current area
            original_area = context.area
            
            # Find a 3D viewport
            for area in context.screen.areas:
                if area.type == 'VIEW_3D':
                    # Find the main region (not header, not tools)
                    region = None
                    for r in area.regions:
                        if r.type == 'WINDOW':
                            region = r
                            break
                    
                    if region is None:
                        continue
                    
                    # Create override context
                    override = {
                        'area': area,
                        'region': region,
                        'space_data': area.spaces.active,
                    }
                    
                    try:
                        # Use the override context
                        with context.temp_override(**override):
                            result = bpy.ops.transform.create_orientation(
                                use=True, 
                                overwrite=True
                            )
                            return result == {'FINISHED'}
                    except Exception as e:
                        self.report({'WARNING'}, f"Failed to create orientation: {str(e)}")
                        return False
            
            self.report({'WARNING'}, "No suitable 3D viewport found")
            return False
            
        except Exception as e:
            self.report({'ERROR'}, f"Error creating orientation: {str(e)}")
            return False
    
    def get_current_orientation_name(self, context):
        """Get the name of the current transform orientation"""
        try:
            slot = context.scene.transform_orientation_slots[0]
            if slot.type == 'DEFAULT':
                # It's a custom orientation
                if slot.custom_orientation:
                    return slot.custom_orientation.name
            return slot.type
        except:
            return 'GLOBAL'
    
    def get_latest_custom_orientation(self, context):
        """Get the most recently created custom orientation"""
        try:
            # Get all custom orientations
            custom_orientations = []
            for orientation in context.scene.orientations:
                custom_orientations.append(orientation.name)
            
            if custom_orientations:
                # Return the last one (most recent)
                return custom_orientations[-1]
        except Exception as e:
            self.report({'DEBUG'}, f"Error getting custom orientation: {str(e)}")
        
        return None
    
    def set_orientation(self, context, orientation_type):
        """Safely set the transform orientation"""
        try:
            slot = context.scene.transform_orientation_slots[0]
            
            if orientation_type in ['GLOBAL', 'LOCAL', 'NORMAL', 'GIMBAL', 'VIEW', 'CURSOR']:
                slot.type = orientation_type
                return True
            else:
                # It's a custom orientation name - check if it exists
                for orientation in context.scene.orientations:
                    if orientation.name == orientation_type:
                        slot.type = 'DEFAULT'
                        slot.custom_orientation = orientation
                        return True
                
                self.report({'WARNING'}, f"Custom orientation '{orientation_type}' not found")
                return False
                
        except Exception as e:
            self.report({'WARNING'}, f"Failed to set orientation: {str(e)}")
            return False
    
    def handle_edit_mode_with_selection(self, context):
        """Handle edit mode when there is a selection"""
        # Get current selection hash
        current_selection_hash = self.get_selection_hash(context)
        
        # Check if selection has changed from last time
        selection_changed = (
            MESH_OT_smart_set_orientation._last_selection_hash is None or 
            current_selection_hash != MESH_OT_smart_set_orientation._last_selection_hash
        )
        
        current_orientation = self.get_current_orientation_name(context)
        
        if selection_changed:
            # Selection has changed - always create new orientation from selection
            if self.create_orientation_from_selection(context):
                self.report({'INFO'}, "Created orientation from selection")
                # Store selection hash only after successful orientation creation
                MESH_OT_smart_set_orientation._last_selection_hash = current_selection_hash
            else:
                self.set_orientation(context, 'LOCAL')
                self.report({'WARNING'}, "Failed to create orientation, set to Local")
        else:
            # Same selection - toggle between custom and local
            if current_orientation == 'LOCAL':
                # Try to switch to the most recent custom orientation
                custom_name = self.get_latest_custom_orientation(context)
                if custom_name:
                    if self.set_orientation(context, custom_name):
                        self.report({'INFO'}, f"Switched to custom: {custom_name}")
                    else:
                        self.report({'WARNING'}, "Failed to switch to custom orientation")
                else:
                    # No custom orientation available, create one
                    if self.create_orientation_from_selection(context):
                        self.report({'INFO'}, "Created custom orientation")
                    else:
                        self.report({'WARNING'}, "Failed to create orientation")
            else:
                # Switch back to local
                self.set_orientation(context, 'LOCAL')
                self.report({'INFO'}, "Switched to Local")
    
    def handle_edit_mode_no_selection(self, context):
        """Handle edit mode when there is no selection"""
        # Clear selection hash when nothing is selected
        MESH_OT_smart_set_orientation._last_selection_hash = None
        
        # No selection in edit mode - toggle between local and global
        current_orientation = self.get_current_orientation_name(context)
        
        # Check if we're coming from a custom orientation
        is_custom = current_orientation not in ['GLOBAL', 'LOCAL', 'NORMAL', 'GIMBAL', 'VIEW', 'CURSOR']
        
        if is_custom or current_orientation == 'GLOBAL':
            # Set to local (first step after custom, or from global)
            self.set_orientation(context, 'LOCAL')
            self.report({'INFO'}, "No selection - set to Local")
        elif current_orientation == 'LOCAL':
            # Toggle to global
            self.set_orientation(context, 'GLOBAL')
            self.report({'INFO'}, "No selection - set to Global")
        else:
            # Default fallback to local
            self.set_orientation(context, 'LOCAL')
            self.report({'INFO'}, "Set to Local")
    
    def handle_object_mode_with_selection(self, context):
        """Handle object mode when objects are selected"""
        current_orientation = self.get_current_orientation_name(context)
        
        # Toggle between local and global orientation
        if current_orientation == 'LOCAL':
            self.set_orientation(context, 'GLOBAL')
            self.report({'INFO'}, "Object mode - set to Global")
        else:
            # From any other orientation, go to LOCAL
            self.set_orientation(context, 'LOCAL')
            self.report({'INFO'}, "Object mode - set to Local")
    
    def handle_object_mode_no_selection(self, context):
        """Handle object mode when no objects are selected"""
        # No objects selected - set to global
        self.set_orientation(context, 'GLOBAL')
        self.report({'INFO'}, "No selection - set to Global")
    
    def handle_other_modes(self, context):
        """Handle modes other than EDIT_MESH and OBJECT"""
        # Other modes - default to global
        self.set_orientation(context, 'GLOBAL')
        self.report({'INFO'}, f"Mode: {context.mode} - set to Global")
    
    def execute(self, context):
        """Main execution method"""
        # Ensure we have a valid context
        if not context.area or context.area.type != 'VIEW_3D':
            self.report({'WARNING'}, "This operator must be called from a 3D Viewport")
            return {'CANCELLED'}
        
        try:
            if context.mode == 'EDIT_MESH' and context.active_object and context.active_object.type == 'MESH':
                obj = context.active_object
                me = obj.data
                bm = bmesh.from_edit_mesh(me)
                
                # Ensure internal indices are updated
                bm.verts.ensure_lookup_table()
                bm.edges.ensure_lookup_table()
                bm.faces.ensure_lookup_table()
                
                # Check for selection
                has_selection = any(
                    v.select for v in bm.verts
                ) or any(
                    e.select for e in bm.edges
                ) or any(
                    f.select for f in bm.faces
                )
                
                if has_selection:
                    self.handle_edit_mode_with_selection(context)
                else:
                    self.handle_edit_mode_no_selection(context)
                    
            elif context.mode == 'OBJECT':
                if context.selected_objects:
                    self.handle_object_mode_with_selection(context)
                else:
                    self.handle_object_mode_no_selection(context)
            else:
                self.handle_other_modes(context)
            
            # Force UI update
            for area in context.screen.areas:
                if area.type == 'VIEW_3D':
                    area.tag_redraw()
            
            return {'FINISHED'}
            
        except Exception as e:
            self.report({'ERROR'}, f"Unexpected error: {str(e)}")
            return {'CANCELLED'}


class SmartOrientationPreferences(AddonPreferences):
    """Addon preferences for Smart Set Orientation"""
    bl_idname = __name__
    
    def draw(self, context):
        layout = self.layout
        
        col = layout.column()
        col.label(text="Smart Set Orientation", icon='ORIENTATION_LOCAL')
        col.separator()
        
        box = col.box()
        box.label(text="Usage:", icon='INFO')
        box.label(text="• Press Ctrl+D to toggle orientation")
        box.label(text="• In Edit Mode with selection: Creates custom orientation")
        box.label(text="• In Edit Mode no selection: Toggles Local/Global")
        box.label(text="• In Object Mode: Toggles Local/Global")
        
        col.separator()
        col.label(text="Authors: Stephko, Claude AI", icon='USER')


# Registration
classes = (
    MESH_OT_smart_set_orientation,
    SmartOrientationPreferences,
)

addon_keymaps = []


def register():
    """Register the addon"""
    for cls in classes:
        bpy.utils.register_class(cls)
    
    # Add keymap
    wm = bpy.context.window_manager
    kc = wm.keyconfigs.addon
    if kc:
        km = kc.keymaps.new(name='3D View', space_type='VIEW_3D')
        kmi = km.keymap_items.new(
            MESH_OT_smart_set_orientation.bl_idname, 
            type='D', 
            value='PRESS', 
            ctrl=True
        )
        addon_keymaps.append((km, kmi))


def unregister():
    """Unregister the addon"""
    # Remove keymap
    for km, kmi in addon_keymaps:
        km.keymap_items.remove(kmi)
    addon_keymaps.clear()
    
    # Unregister classes
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)


if __name__ == "__main__":
    register()