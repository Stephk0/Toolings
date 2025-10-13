import bpy
import bmesh
from mathutils import Vector

class MassExporterParentEmptyFix:
    def __init__(self):
        self.original_positions = {}
        self.original_collections = {}
        self.moved_empties = []
        
    def find_parent_empties_in_subcollections(self):
        """Find parent empties that are in subcollections (not in scene root)"""
        parent_empties = []
        scene = bpy.context.scene
        
        # Get all collections except the scene collection
        def get_all_collections(collection, level=0):
            collections = []
            if level > 0:  # Skip scene collection (level 0)
                collections.append(collection)
            for child in collection.children:
                collections.extend(get_all_collections(child, level + 1))
            return collections
        
        all_subcollections = get_all_collections(scene.collection)
        
        # Check each subcollection for parent empties
        for collection in all_subcollections:
            for obj in collection.objects:
                if obj.type == 'EMPTY' and len(obj.children) > 0:
                    # This is a parent empty in a subcollection
                    parent_empties.append(obj)
                    print(f"Found parent empty '{obj.name}' in collection '{collection.name}' with {len(obj.children)} children")
        
        return parent_empties
    
    def store_original_state(self, empty_obj):
        """Store the original position and collection of an empty"""
        self.original_positions[empty_obj.name] = empty_obj.location.copy()
        
        # Find which collection this object belongs to
        for collection in bpy.data.collections:
            if empty_obj.name in collection.objects:
                self.original_collections[empty_obj.name] = collection
                break
    
    def move_empty_to_center(self, empty_obj):
        """Move empty to scene center and store original state"""
        print(f"Moving empty '{empty_obj.name}' from {empty_obj.location} to scene center")
        
        # Store original state
        self.store_original_state(empty_obj)
        
        # Move to center
        empty_obj.location = Vector((0.0, 0.0, 0.0))
        
        # Add to moved list
        if empty_obj not in self.moved_empties:
            self.moved_empties.append(empty_obj)
    
    def restore_empty_position(self, empty_obj):
        """Restore empty to its original position"""
        if empty_obj.name in self.original_positions:
            original_pos = self.original_positions[empty_obj.name]
            print(f"Restoring empty '{empty_obj.name}' to original position {original_pos}")
            empty_obj.location = original_pos
            
            # Remove from moved list
            if empty_obj in self.moved_empties:
                self.moved_empties.remove(empty_obj)
    
    def prepare_for_export(self):
        """Move all parent empties in subcollections to scene center"""
        print("=== PREPARING PARENT EMPTIES FOR EXPORT ===")
        
        parent_empties = self.find_parent_empties_in_subcollections()
        
        if not parent_empties:
            print("No parent empties found in subcollections")
            return
        
        for empty in parent_empties:
            self.move_empty_to_center(empty)
        
        print(f"Moved {len(parent_empties)} parent empties to scene center")
        return parent_empties
    
    def restore_after_export(self):
        """Restore all moved empties to their original positions"""
        print("=== RESTORING PARENT EMPTIES AFTER EXPORT ===")
        
        if not self.moved_empties:
            print("No empties to restore")
            return
        
        # Make a copy of the list since we'll be modifying it
        empties_to_restore = self.moved_empties.copy()
        
        for empty in empties_to_restore:
            self.restore_empty_position(empty)
        
        print(f"Restored {len(empties_to_restore)} parent empties to original positions")
    
    def get_export_status(self):
        """Get current status of moved empties"""
        if not self.moved_empties:
            print("No empties currently moved for export")
            return
        
        print(f"Currently {len(self.moved_empties)} empties moved for export:")
        for empty in self.moved_empties:
            original_pos = self.original_positions.get(empty.name, "Unknown")
            print(f"  - '{empty.name}': Original pos {original_pos}, Current pos {empty.location}")


# Global instance for easy access
mass_exporter_fix = MassExporterParentEmptyFix()

def prepare_empties_for_export():
    """Convenience function to prepare empties for export"""
    return mass_exporter_fix.prepare_for_export()

def restore_empties_after_export():
    """Convenience function to restore empties after export"""
    mass_exporter_fix.restore_after_export()

def get_empty_export_status():
    """Convenience function to check status"""
    mass_exporter_fix.get_export_status()

# Example usage:
if __name__ == "__main__":
    print("Mass Exporter v3 Parent Empty Fix Script Loaded")
    print("Available functions:")
    print("  - prepare_empties_for_export(): Move parent empties to center")
    print("  - restore_empties_after_export(): Restore empties to original positions")
    print("  - get_empty_export_status(): Check current status")
    
    # Uncomment to test
    # prepare_empties_for_export()
    # get_empty_export_status()
    # restore_empties_after_export()
