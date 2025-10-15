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
    "name": "Modifier Display Toggle (Edit Mode)",
    "author": "Stephan Viranyi, Blender MCP",
    "version": (1, 3, 0),
    "blender": (2, 80, 0),
    "location": "3D Viewport > D Key (Edit Mode only)",
    "description": "Toggle modifier display in edit mode with viewport parity",
    "warning": "",
    "doc_url": "",
    "category": "3D View",
    "support": "COMMUNITY",
}

import bpy
from bpy.types import Operator, AddonPreferences
from bpy.props import StringProperty, BoolProperty


class MESH_OT_toggle_modifier_display(Operator):
    """Toggle modifier display in edit mode"""
    bl_idname = "mesh.toggle_modifier_display"
    bl_label = "Toggle Modifier Display (Edit Mode)"
    bl_description = "In Edit Mode: Sync edit mode display with viewport or disable all"
    bl_options = {'REGISTER', 'UNDO'}
    
    @classmethod
    def poll(cls, context):
        """Check if operator can run - only in edit mode"""
        obj = context.active_object
        return (
            obj is not None and 
            hasattr(obj, 'modifiers') and 
            obj.type in {'MESH', 'CURVE', 'SURFACE', 'FONT', 'LATTICE'} and
            context.mode in {'EDIT_MESH', 'EDIT_CURVE', 'EDIT_SURFACE', 'EDIT_TEXT', 'EDIT_LATTICE'}
        )
    
    def execute(self, context):
        obj = context.active_object
        
        # Check if object has modifiers
        if not obj.modifiers:
            self.report({'INFO'}, "No modifiers found on active object")
            return {'CANCELLED'}
        
        # Handle edit mode modifier toggling
        result = self._toggle_edit_mode_modifiers(obj)
        self.report({'INFO'}, result)
        
        # Force viewport update
        context.area.tag_redraw()
        
        return {'FINISHED'}
    
    def _toggle_edit_mode_modifiers(self, obj):
        """Handle modifier toggling in edit mode"""
        # Check if edit mode display already matches viewport display (parity exists)
        parity_exists = all(
            mod.show_viewport == mod.show_in_editmode 
            for mod in obj.modifiers
        )
        
        # Check if any viewport-visible modifier has edit mode enabled
        any_edit_mode_enabled = any(
            mod.show_viewport and mod.show_in_editmode 
            for mod in obj.modifiers
        )
        
        if parity_exists and any_edit_mode_enabled:
            # Parity exists and some edit mode modifiers are on - disable all edit mode display
            count = sum(
                1 for mod in obj.modifiers 
                if mod.show_in_editmode and self._set_edit_mode(mod, False)
            )
            return f"Disabled edit mode display for {count} modifier{'s' if count != 1 else ''}"
        else:
            # Create parity: make edit mode match viewport settings
            count = 0
            for mod in obj.modifiers:
                # Only change edit mode to match viewport
                if mod.show_viewport != mod.show_in_editmode:
                    mod.show_in_editmode = mod.show_viewport
                    count += 1
            
            return f"Synced edit mode display to match viewport: {count} modifier{'s' if count != 1 else ''} updated"
    
    def _set_edit_mode(self, modifier, state):
        """Safely set edit mode visibility"""
        try:
            modifier.show_in_editmode = state
            return True
        except:
            return False


class MESH_OT_toggle_on_cage_display(Operator):
    """Toggle on cage modifier display in edit mode"""
    bl_idname = "mesh.toggle_on_cage_display"
    bl_label = "Toggle On Cage Modifier Display (Edit Mode)"
    bl_description = "In Edit Mode: Sync on cage display with viewport or disable all"
    bl_options = {'REGISTER', 'UNDO'}
    
    @classmethod
    def poll(cls, context):
        """Check if operator can run - only in edit mode"""
        obj = context.active_object
        return (
            obj is not None and 
            hasattr(obj, 'modifiers') and 
            obj.type in {'MESH', 'CURVE', 'SURFACE', 'FONT', 'LATTICE'} and
            context.mode in {'EDIT_MESH', 'EDIT_CURVE', 'EDIT_SURFACE', 'EDIT_TEXT', 'EDIT_LATTICE'}
        )
    
    def execute(self, context):
        obj = context.active_object
        
        # Check if object has modifiers
        if not obj.modifiers:
            self.report({'INFO'}, "No modifiers found on active object")
            return {'CANCELLED'}
        
        # Handle on cage modifier toggling
        result = self._toggle_on_cage_modifiers(obj)
        self.report({'INFO'}, result)
        
        # Force viewport update
        context.area.tag_redraw()
        
        return {'FINISHED'}
    
    def _toggle_on_cage_modifiers(self, obj):
        """Handle on cage toggling in edit mode"""
        # Check if on cage display already matches viewport display (parity exists)
        parity_exists = all(
            mod.show_viewport == mod.show_on_cage 
            for mod in obj.modifiers
            if hasattr(mod, 'show_on_cage')  # Not all modifiers have this property
        )
        
        # Check if any viewport-visible modifier has on cage enabled
        any_on_cage_enabled = any(
            mod.show_viewport and mod.show_on_cage 
            for mod in obj.modifiers
            if hasattr(mod, 'show_on_cage')
        )
        
        if parity_exists and any_on_cage_enabled:
            # Parity exists and some on cage modifiers are on - disable all on cage display
            count = sum(
                1 for mod in obj.modifiers 
                if hasattr(mod, 'show_on_cage') and mod.show_on_cage and self._set_on_cage(mod, False)
            )
            return f"Disabled on cage display for {count} modifier{'s' if count != 1 else ''}"
        else:
            # Create parity: make on cage match viewport settings
            count = 0
            for mod in obj.modifiers:
                if hasattr(mod, 'show_on_cage'):
                    # Only change on cage to match viewport
                    if mod.show_viewport != mod.show_on_cage:
                        mod.show_on_cage = mod.show_viewport
                        count += 1
            
            return f"Synced on cage display to match viewport: {count} modifier{'s' if count != 1 else ''} updated"
    
    def _set_on_cage(self, modifier, state):
        """Safely set on cage visibility"""
        try:
            if hasattr(modifier, 'show_on_cage'):
                modifier.show_on_cage = state
                return True
            return False
        except:
            return False


class MODIFIER_TOGGLE_preferences(AddonPreferences):
    """Addon preferences for Modifier Display Toggle"""
    bl_idname = __name__
    
    show_info: BoolProperty(
        name="Show Usage Info",
        description="Display usage information in preferences",
        default=True
    )
    
    def draw(self, context):
        layout = self.layout
        
        if self.show_info:
            col = layout.column()
            col.label(text="Modifier Display Toggle (Edit Mode Only)", icon='MODIFIER')
            
            box = col.box()
            box.label(text="Usage:", icon='INFO')
            box.label(text="• Press 'D' in Edit Mode to toggle modifiers")
            box.label(text="• First press: Syncs edit display with viewport visibility")
            box.label(text="• Second press: Disables all edit mode display")
            box.separator()
            box.label(text="• Press 'Shift+D' in Edit Mode to toggle on cage display")
            box.label(text="• First press: Syncs on cage with viewport visibility")
            box.label(text="• Second press: Disables all on cage display")
            
            box = col.box()
            box.label(text="Supported object types:", icon='OBJECT_DATA')
            box.label(text="• Mesh, Curve, Surface, Font, Lattice")
            
            box = col.box()
            box.label(text="Note:", icon='ERROR')
            box.label(text="This operator only works in Edit Mode")


# Keymap management
addon_keymaps = []


def register_keymaps():
    """Register keymaps for the addon"""
    wm = bpy.context.window_manager
    if not wm.keyconfigs.addon:
        return
        
    kc = wm.keyconfigs.addon
    
    # 3D View keymap
    km = kc.keymaps.new(name='3D View', space_type='VIEW_3D')
    
    # Regular modifier toggle (D key)
    kmi = km.keymap_items.new(
        MESH_OT_toggle_modifier_display.bl_idname,
        type='D',
        value='PRESS'
    )
    addon_keymaps.append((km, kmi))
    
    # On cage toggle (Shift+D)
    kmi = km.keymap_items.new(
        MESH_OT_toggle_on_cage_display.bl_idname,
        type='D',
        value='PRESS',
        shift=True
    )
    addon_keymaps.append((km, kmi))


def unregister_keymaps():
    """Unregister keymaps for the addon"""
    for km, kmi in addon_keymaps:
        km.keymap_items.remove(kmi)
    addon_keymaps.clear()


# Registration
classes = (
    MESH_OT_toggle_modifier_display,
    MESH_OT_toggle_on_cage_display,
    MODIFIER_TOGGLE_preferences,
)


def register():
    """Register the addon"""
    for cls in classes:
        bpy.utils.register_class(cls)
    
    register_keymaps()
    print("Modifier Display Toggle (Edit Mode): Add-on registered")


def unregister():
    """Unregister the addon"""
    unregister_keymaps()
    
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
    
    print("Modifier Display Toggle (Edit Mode): Add-on unregistered")


if __name__ == "__main__":
    register()
