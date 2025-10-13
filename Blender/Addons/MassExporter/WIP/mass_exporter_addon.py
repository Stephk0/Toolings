"""
Mass Exporter v3 - Proper Blender Addon
Simple: Move parent empties to center, children follow automatically via parent-child relationship
"""

import bpy
from mathutils import Vector
from bpy.types import Operator, Panel
from bpy.props import BoolProperty

bl_info = {
    "name": "Mass Exporter v3 - Parent Empty Fix",
    "author": "Claude AI Assistant",
    "version": (3, 0, 0),
    "blender": (4, 0, 0),
    "location": "View3D > Sidebar > Mass Export Tab",
    "description": "Move parent empties to center for export, then restore positions",
    "warning": "",
    "doc_url": "",
    "category": "Import-Export",
}

# Global storage for original empty positions
original_empty_positions = {}

def prepare_for_export():
    """Move parent empties in subcollections to scene center - children follow automatically"""
    global original_empty_positions
    original_empty_positions.clear()
    
    print("=== PREPARING FOR EXPORT ===")
    
    # Find subcollections (not main scene collection)
    def get_subcollections(collection, level=0):
        collections = []
        if level > 0:  # Skip scene collection
            collections.append(collection)
        for child in collection.children:
            collections.extend(get_subcollections(child, level + 1))
        return collections
    
    subcollections = get_subcollections(bpy.context.scene.collection)
    
    moved_count = 0
    for collection in subcollections:
        for obj in collection.objects:
            if obj.type == 'EMPTY' and len(obj.children) > 0:
                # Store original position
                original_empty_positions[obj.name] = obj.location.copy()
                
                print(f"Moving parent empty '{obj.name}' from {obj.location} to center")
                print(f"  → {len(obj.children)} children will follow automatically")
                
                # Move parent to center - children follow automatically
                obj.location = Vector((0.0, 0.0, 0.0))
                moved_count += 1
    
    bpy.context.view_layer.update()
    print(f"✓ Moved {moved_count} parent empties to center - READY FOR EXPORT")
    return moved_count > 0

def restore_after_export():
    """Restore parent empties to original positions - children follow automatically"""
    global original_empty_positions
    
    print("=== RESTORING AFTER EXPORT ===")
    
    if not original_empty_positions:
        print("Nothing to restore")
        return
    
    restored_count = 0
    for empty_name, original_pos in original_empty_positions.items():
        if empty_name in bpy.data.objects:
            empty_obj = bpy.data.objects[empty_name]
            print(f"Restoring '{empty_name}' from {empty_obj.location} to {original_pos}")
            print(f"  → {len(empty_obj.children)} children will follow automatically")
            
            # Restore parent - children follow automatically
            empty_obj.location = original_pos
            restored_count += 1
        else:
            print(f"Warning: '{empty_name}' no longer exists")
    
    bpy.context.view_layer.update()
    original_empty_positions.clear()
    print(f"✓ Restored {restored_count} parent empties - children followed automatically")

class MASSEXP_OT_prepare_export(Operator):
    """Move parent empties to center for export"""
    bl_idname = "massexp.prepare_export"
    bl_label = "Prepare for Export"
    bl_description = "Move parent empties to scene center - children follow automatically"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        moved = prepare_for_export()
        if moved:
            self.report({'INFO'}, "Parent empties moved to center - ready for export!")
        else:
            self.report({'INFO'}, "No parent empties found in subcollections")
        return {'FINISHED'}

class MASSEXP_OT_restore_positions(Operator):
    """Restore parent empties to original positions"""
    bl_idname = "massexp.restore_positions" 
    bl_label = "Restore Positions"
    bl_description = "Restore parent empties to original positions after export"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        restore_after_export()
        if original_empty_positions:
            self.report({'INFO'}, "Positions restored successfully!")
        else:
            self.report({'INFO'}, "No positions to restore")
        return {'FINISHED'}

class MASSEXP_OT_show_positions(Operator):
    """Show world positions of parent empties and children"""
    bl_idname = "massexp.show_positions"
    bl_label = "Show World Positions"
    bl_description = "Print world positions to console"
    bl_options = {'REGISTER'}
    
    def execute(self, context):
        print("=== WORLD POSITIONS (ACTUAL LOCATIONS IN SCENE) ===")
        count = 0
        for obj in bpy.context.scene.objects:
            if obj.type == 'EMPTY' and len(obj.children) > 0:
                print(f"Empty '{obj.name}': {obj.location}")
                for child in obj.children:
                    world_pos = child.matrix_world.translation
                    print(f"  Child '{child.name}': {world_pos}")
                count += 1
        
        if count == 0:
            self.report({'INFO'}, "No parent empties found")
        else:
            self.report({'INFO'}, f"Found {count} parent empties - check console for details")
        return {'FINISHED'}

class MASSEXP_PT_panel(Panel):
    """Panel in 3D Viewport sidebar"""
    bl_label = "Mass Exporter v3"
    bl_idname = "MASSEXP_PT_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Mass Export"
    
    def draw(self, context):
        layout = self.layout
        
        # Info section
        box = layout.box()
        box.label(text="Parent Empty Fix", icon='EMPTY_AXIS')
        box.label(text="Children follow parents automatically")
        
        # Main buttons
        layout.separator()
        col = layout.column(align=True)
        col.operator("massexp.prepare_export", icon='EXPORT')
        col.operator("massexp.restore_positions", icon='LOOP_BACK')
        
        layout.separator()
        layout.operator("massexp.show_positions", icon='CONSOLE')
        
        # Status info
        layout.separator()
        box = layout.box()
        if original_empty_positions:
            box.label(text=f"Stored: {len(original_empty_positions)} empties", icon='CHECKMARK')
        else:
            box.label(text="No positions stored", icon='X')

# Registration
classes = (
    MASSEXP_OT_prepare_export,
    MASSEXP_OT_restore_positions,
    MASSEXP_OT_show_positions,
    MASSEXP_PT_panel,
)

def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    print("Mass Exporter v3 addon registered successfully!")

def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
    print("Mass Exporter v3 addon unregistered")

if __name__ == "__main__":
    register()
    print("🎯 Mass Exporter v3 - Proper Blender Addon")
    print("✨ Now available in View3D > Sidebar > Mass Export tab")
