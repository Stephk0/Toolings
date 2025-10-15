import bpy
from mathutils import Vector
import bmesh

class MassExporterV3ParentEmptyHandler:
    """
    Handles parent empty positioning issues in mass exporter v3.
    Automatically moves parent empties from subcollections to scene center
    for export, then restores them afterward.
    """
    
    def __init__(self):
        self.backup_data = {}
        self.active_session = False
        
    def find_problematic_parent_empties(self):
        """Find parent empties in subcollections that may cause export issues"""
        problematic_empties = []
        scene = bpy.context.scene
        
        # Recursively get all subcollections (not scene root)
        def collect_subcollections(collection, level=0):
            collections = []
            if level > 0:  # Skip scene collection (level 0)
                collections.append(collection)
            for child in collection.children:
                collections.extend(collect_subcollections(child, level + 1))
            return collections
        
        all_subcollections = collect_subcollections(scene.collection)
        
        for collection in all_subcollections:
            for obj in collection.objects:
                if (obj.type == 'EMPTY' and 
                    len(obj.children) > 0 and 
                    obj.location != Vector((0.0, 0.0, 0.0))):
                    
                    problematic_empties.append({
                        'object': obj,
                        'collection': collection,
                        'original_location': obj.location.copy(),
                        'children_count': len(obj.children)
                    })
        
        return problematic_empties
    
    def start_export_session(self):
        """Start export session - move problematic empties to center"""
        if self.active_session:
            print("Export session already active. Call end_export_session() first.")
            return False
            
        print("=== STARTING MASS EXPORTER V3 EXPORT SESSION ===")
        
        problematic_empties = self.find_problematic_parent_empties()
        
        if not problematic_empties:
            print("No problematic parent empties found - no action needed")
            return True
        
        print(f"Found {len(problematic_empties)} parent empties to relocate:")
        
        for empty_data in problematic_empties:
            obj = empty_data['object']
            collection = empty_data['collection']
            original_loc = empty_data['original_location']
            children_count = empty_data['children_count']
            
            # Store backup data
            self.backup_data[obj.name] = {
                'object': obj,
                'original_location': original_loc,
                'collection': collection
            }
            
            # Move to center
            obj.location = Vector((0.0, 0.0, 0.0))
            
            print(f"  • '{obj.name}' from collection '{collection.name}'")
            print(f"    Original: {original_loc} → Center: (0,0,0)")
            print(f"    Has {children_count} children")
        
        self.active_session = True
        print(f"\nRelocated {len(problematic_empties)} empties to scene center")
        print("*** READY FOR EXPORT ***")
        return True
    
    def end_export_session(self):
        """End export session - restore empties to original positions"""
        if not self.active_session:
            print("No active export session to end")
            return False
            
        print("\n=== ENDING MASS EXPORTER V3 EXPORT SESSION ===")
        
        if not self.backup_data:
            print("No empties to restore")
            self.active_session = False
            return True
        
        print(f"Restoring {len(self.backup_data)} empties to original positions:")
        
        restored_count = 0
        for obj_name, data in self.backup_data.items():
            obj = data['object']
            original_location = data['original_location']
            
            # Check if object still exists
            if obj_name in bpy.data.objects:
                obj.location = original_location
                print(f"  • '{obj_name}' restored to {original_location}")
                restored_count += 1
            else:
                print(f"  ! '{obj_name}' no longer exists - skipping")
        
        # Clear backup data
        self.backup_data.clear()
        self.active_session = False
        
        print(f"\nRestored {restored_count} empties to original positions")
        print("*** EXPORT SESSION COMPLETE ***")
        return True
    
    def get_session_status(self):
        """Get current session status"""
        if self.active_session:
            print(f"Export session ACTIVE - {len(self.backup_data)} empties moved to center")
            for obj_name, data in self.backup_data.items():
                current_loc = data['object'].location
                original_loc = data['original_location']
                print(f"  • '{obj_name}': {original_loc} → {current_loc}")
        else:
            print("No active export session")
        return self.active_session
    
    def force_reset(self):
        """Force reset if something goes wrong"""
        if self.backup_data:
            print("Force restoring empties...")
            self.end_export_session()
        else:
            self.active_session = False
            print("Session reset")

# Global handler instance
mass_exporter_handler = MassExporterV3ParentEmptyHandler()

# Convenient wrapper functions for easy use
def start_mass_export():
    """Start mass export session (moves parent empties to center)"""
    return mass_exporter_handler.start_export_session()

def end_mass_export():
    """End mass export session (restores parent empties)"""
    return mass_exporter_handler.end_export_session()

def check_export_status():
    """Check current export session status"""
    return mass_exporter_handler.get_session_status()

def reset_mass_export():
    """Force reset export session"""
    mass_exporter_handler.force_reset()

# Operator classes for Blender UI integration
class MASS_EXPORT_OT_start_session(bpy.types.Operator):
    bl_idname = "mass_export.start_session"
    bl_label = "Start Export Session"
    bl_description = "Move parent empties to scene center for export"
    
    def execute(self, context):
        success = start_mass_export()
        if success:
            self.report({'INFO'}, "Export session started")
        else:
            self.report({'ERROR'}, "Failed to start export session")
        return {'FINISHED'}

class MASS_EXPORT_OT_end_session(bpy.types.Operator):
    bl_idname = "mass_export.end_session"
    bl_label = "End Export Session"
    bl_description = "Restore parent empties to original positions"
    
    def execute(self, context):
        success = end_mass_export()
        if success:
            self.report({'INFO'}, "Export session ended")
        else:
            self.report({'ERROR'}, "No active session to end")
        return {'FINISHED'}

class MASS_EXPORT_OT_check_status(bpy.types.Operator):
    bl_idname = "mass_export.check_status"
    bl_label = "Check Status"
    bl_description = "Check current export session status"
    
    def execute(self, context):
        check_export_status()
        return {'FINISHED'}

class MASS_EXPORT_PT_panel(bpy.types.Panel):
    bl_label = "Mass Exporter v3 Fix"
    bl_idname = "MASS_EXPORT_PT_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Tool"
    
    def draw(self, context):
        layout = self.layout
        
        layout.operator("mass_export.start_session", icon='EXPORT')
        layout.operator("mass_export.end_session", icon='IMPORT')
        layout.separator()
        layout.operator("mass_export.check_status", icon='INFO')

def register():
    bpy.utils.register_class(MASS_EXPORT_OT_start_session)
    bpy.utils.register_class(MASS_EXPORT_OT_end_session)
    bpy.utils.register_class(MASS_EXPORT_OT_check_status)
    bpy.utils.register_class(MASS_EXPORT_PT_panel)

def unregister():
    bpy.utils.unregister_class(MASS_EXPORT_PT_panel)
    bpy.utils.unregister_class(MASS_EXPORT_OT_check_status)
    bpy.utils.unregister_class(MASS_EXPORT_OT_end_session)
    bpy.utils.unregister_class(MASS_EXPORT_OT_start_session)

if __name__ == "__main__":
    # For direct script execution
    print("Mass Exporter v3 Parent Empty Handler Loaded")
    print("\nAvailable functions:")
    print("  start_mass_export() - Begin export session")
    print("  end_mass_export() - End export session") 
    print("  check_export_status() - Check current status")
    print("  reset_mass_export() - Force reset")
    print("\nTo use as addon: save as .py file and install in Blender")
    
    # Register for UI (comment out if not wanted)
    try:
        register()
        print("UI panels registered successfully")
    except:
        print("Could not register UI panels (may already be registered)")
