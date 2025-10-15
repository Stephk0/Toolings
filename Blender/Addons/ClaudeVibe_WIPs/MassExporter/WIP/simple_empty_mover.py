import bpy
from mathutils import Vector

class SimpleEmptyMover:
    def __init__(self):
        self.moved_empties = {}  # Store original positions
    
    def move_parent_empties_to_center(self):
        """Move all parent empties in subcollections to scene center"""
        print("=== MOVING PARENT EMPTIES TO CENTER ===")
        
        # Clear previous data
        self.moved_empties.clear()
        
        # Find all collections except the main scene collection
        def get_subcollections(collection, level=0):
            collections = []
            if level > 0:  # Skip scene collection (level 0)
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
                    self.moved_empties[obj.name] = obj.location.copy()
                    
                    print(f"Moving '{obj.name}' from {obj.location} to center")
                    print(f"  Has {len(obj.children)} children that will move with it")
                    
                    # Move to center - children will automatically follow
                    obj.location = Vector((0.0, 0.0, 0.0))
                    moved_count += 1
        
        print(f"Moved {moved_count} parent empties (and their children) to scene center")
        return moved_count > 0
    
    def restore_parent_empties(self):
        """Restore parent empties to original positions"""
        print("=== RESTORING PARENT EMPTIES TO ORIGINAL POSITIONS ===")
        
        if not self.moved_empties:
            print("No empties to restore")
            return
        
        restored_count = 0
        for empty_name, original_pos in self.moved_empties.items():
            if empty_name in bpy.data.objects:
                empty_obj = bpy.data.objects[empty_name]
                print(f"Restoring '{empty_name}' from {empty_obj.location} to {original_pos}")
                
                # Move back - children will automatically follow
                empty_obj.location = original_pos
                restored_count += 1
            else:
                print(f"Warning: '{empty_name}' no longer exists")
        
        print(f"Restored {restored_count} parent empties (and their children)")
        self.moved_empties.clear()

# Global instance
empty_mover = SimpleEmptyMover()

def move_empties_to_center():
    """Simple function to move parent empties to center"""
    return empty_mover.move_parent_empties_to_center()

def restore_empties():
    """Simple function to restore parent empties"""
    empty_mover.restore_parent_empties()

def export_workflow():
    """Complete export workflow"""
    print("=== COMPLETE EXPORT WORKFLOW ===")
    
    # Step 1: Move empties to center
    moved = move_empties_to_center()
    
    if not moved:
        print("No parent empties found in subcollections - export normally")
        return
    
    print("\n--- PERFORM YOUR EXPORT OPERATIONS NOW ---")
    print("Parent empties and their children are now at scene center")
    
    # Here you would do your actual export
    # For example:
    """
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.export_scene.fbx(filepath="your_path.fbx")
    """
    
    input("Press Enter after you complete your export...")
    
    # Step 2: Restore positions
    restore_empties()
    print("\n✅ Export workflow complete!")

if __name__ == "__main__":
    print("Simple Parent Empty Mover Loaded")
    print("\nFunctions:")
    print("  move_empties_to_center() - Move parent empties and children to center")
    print("  restore_empties() - Restore to original positions")  
    print("  export_workflow() - Complete workflow")
