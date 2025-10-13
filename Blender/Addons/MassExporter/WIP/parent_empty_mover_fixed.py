import bpy
from mathutils import Vector

class ParentEmptyMoverFixed:
    def __init__(self):
        self.moved_empties = {}  # Store original data
    
    def move_parent_empties_with_children_to_center(self):
        """Move parent empties and their children to scene center"""
        print("=== MOVING PARENT EMPTIES AND CHILDREN TO CENTER ===")
        
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
                    # Store original data
                    original_empty_pos = obj.location.copy()
                    original_children_data = []
                    
                    print(f"Processing parent empty '{obj.name}' at {obj.location}")
                    
                    # Store children's world positions
                    for child in obj.children:
                        world_pos = child.matrix_world.translation.copy()
                        original_children_data.append({
                            'object': child,
                            'world_position': world_pos,
                            'local_position': child.location.copy()
                        })
                        print(f"  Child '{child.name}': local {child.location}, world {world_pos}")
                    
                    # Calculate offset needed
                    offset = Vector((0.0, 0.0, 0.0)) - original_empty_pos
                    
                    # Move parent to center
                    obj.location = Vector((0.0, 0.0, 0.0))
                    
                    # Move all children by the same offset
                    for child_data in original_children_data:
                        child_obj = child_data['object']
                        old_world_pos = child_data['world_position']
                        new_world_pos = old_world_pos + offset
                        
                        # Set child's new location
                        child_obj.location = new_world_pos
                        print(f"  Moved child '{child_obj.name}' from {old_world_pos} to {new_world_pos}")
                    
                    # Store all data for restoration
                    self.moved_empties[obj.name] = {
                        'empty_object': obj,
                        'original_empty_position': original_empty_pos,
                        'children_data': original_children_data
                    }
                    
                    moved_count += 1
                    print(f"✓ Moved '{obj.name}' and {len(obj.children)} children to center\n")
        
        # Update scene
        bpy.context.view_layer.update()
        
        print(f"Moved {moved_count} parent empties and their children to scene center")
        return moved_count > 0
    
    def restore_parent_empties_and_children(self):
        """Restore parent empties and children to original positions"""
        print("=== RESTORING PARENT EMPTIES AND CHILDREN ===")
        
        if not self.moved_empties:
            print("No empties to restore")
            return
        
        restored_count = 0
        for empty_name, data in self.moved_empties.items():
            empty_obj = data['empty_object']
            original_empty_pos = data['original_empty_position']
            children_data = data['children_data']
            
            if empty_obj.name in bpy.data.objects:
                print(f"Restoring '{empty_name}' from {empty_obj.location} to {original_empty_pos}")
                
                # Restore parent position
                empty_obj.location = original_empty_pos
                
                # Restore children positions
                for child_data in children_data:
                    child_obj = child_data['object']
                    original_local_pos = child_data['local_position']
                    
                    if child_obj.name in bpy.data.objects:
                        child_obj.location = original_local_pos
                        print(f"  Restored child '{child_obj.name}' to {original_local_pos}")
                    else:
                        print(f"  Warning: Child '{child_obj.name}' no longer exists")
                
                restored_count += 1
            else:
                print(f"Warning: '{empty_name}' no longer exists")
        
        # Update scene
        bpy.context.view_layer.update()
        
        print(f"Restored {restored_count} parent empties and their children")
        self.moved_empties.clear()
    
    def show_current_positions(self):
        """Debug function to show current positions"""
        print("=== CURRENT POSITIONS ===")
        for obj in bpy.context.scene.objects:
            if obj.type == 'EMPTY' and len(obj.children) > 0:
                print(f"Empty '{obj.name}': {obj.location}")
                for child in obj.children:
                    print(f"  Child '{child.name}': {child.location}")

# Global instance
fixed_empty_mover = ParentEmptyMoverFixed()

def move_empties_and_children_to_center():
    """Move parent empties and their children to center"""
    return fixed_empty_mover.move_parent_empties_with_children_to_center()

def restore_empties_and_children():
    """Restore parent empties and children to original positions"""
    fixed_empty_mover.restore_parent_empties_and_children()

def show_positions():
    """Show current positions for debugging"""
    fixed_empty_mover.show_current_positions()

def complete_export_workflow():
    """Complete export workflow with proper parent/children handling"""
    print("=== COMPLETE EXPORT WORKFLOW WITH CHILDREN ===")
    
    # Step 1: Move everything to center
    moved = move_empties_and_children_to_center()
    
    if not moved:
        print("No parent empties found in subcollections - export normally")
        return
    
    print("\n=== READY FOR EXPORT ===")
    show_positions()
    
    print("\n--- PERFORM YOUR EXPORT NOW ---")
    print("All parent empties and their children are properly positioned at center")
    
    # Here you would do your actual export
    input("Press Enter after export is complete...")
    
    # Step 2: Restore everything
    restore_empties_and_children()
    
    print("\n=== FINAL POSITIONS ===")
    show_positions()
    print("\n✅ Export workflow complete!")

if __name__ == "__main__":
    print("Fixed Parent Empty Mover Loaded")
    print("\nFunctions:")
    print("  move_empties_and_children_to_center() - Move everything to center")
    print("  restore_empties_and_children() - Restore original positions")
    print("  show_positions() - Debug current positions")
    print("  complete_export_workflow() - Full workflow")
