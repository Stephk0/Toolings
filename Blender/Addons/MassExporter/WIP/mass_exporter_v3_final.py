"""
Mass Exporter v3 Parent Empty Fix - FINAL VERSION
Simple solution: Move parent empties and their children to scene center for export, then restore.
"""

import bpy
from mathutils import Vector

# Global storage for moved empties
moved_empties_data = {}

def prepare_for_export():
    """Move all parent empties in subcollections to scene center with their children"""
    global moved_empties_data
    moved_empties_data.clear()
    
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
                # Store original positions
                original_empty_pos = obj.location.copy()
                children_original_pos = []
                
                print(f"Moving '{obj.name}' and {len(obj.children)} children to center")
                
                # Store children positions and calculate offset
                for child in obj.children:
                    children_original_pos.append({
                        'object': child,
                        'original_local_pos': child.location.copy()
                    })
                
                # Calculate offset to move to center
                offset = Vector((0.0, 0.0, 0.0)) - original_empty_pos
                
                # Move parent to center
                obj.location = Vector((0.0, 0.0, 0.0))
                
                # Move children by same offset
                for child_data in children_original_pos:
                    child = child_data['object']
                    # Move child by the same offset the parent moved
                    child.location = child.location + offset
                
                # Store for restoration
                moved_empties_data[obj.name] = {
                    'empty': obj,
                    'original_empty_pos': original_empty_pos,
                    'children_data': children_original_pos
                }
                
                moved_count += 1
    
    bpy.context.view_layer.update()
    print(f"✓ Moved {moved_count} parent empties to center - READY FOR EXPORT")
    return moved_count > 0

def restore_after_export():
    """Restore all parent empties and children to original positions"""
    global moved_empties_data
    
    print("=== RESTORING AFTER EXPORT ===")
    
    if not moved_empties_data:
        print("Nothing to restore")
        return
    
    for empty_name, data in moved_empties_data.items():
        empty = data['empty']
        original_pos = data['original_empty_pos']
        children_data = data['children_data']
        
        print(f"Restoring '{empty_name}' and children to original positions")
        
        # Restore parent
        empty.location = original_pos
        
        # Restore children
        for child_data in children_data:
            child = child_data['object']
            original_local_pos = child_data['original_local_pos']
            child.location = original_local_pos
    
    bpy.context.view_layer.update()
    moved_empties_data.clear()
    print("✓ All objects restored to original positions")

def export_workflow():
    """Complete export workflow - use this for automatic handling"""
    print("=== MASS EXPORTER V3 WORKFLOW ===")
    
    # Prepare for export
    if not prepare_for_export():
        print("No parent empties found - export normally")
        return
    
    print("\n🎯 EXPORT NOW - Everything is positioned at scene center")
    print("   Parent empties and their children are ready for export")
    
    # Your export code goes here:
    """
    Example export operations:
    
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.export_scene.fbx(filepath="your_path.fbx")
    
    or 
    
    bpy.ops.export_scene.obj(filepath="your_path.obj")
    """
    
    input("\nPress Enter after your export is complete...")
    
    # Restore positions
    restore_after_export()
    print("\n✅ Export workflow complete!")

# For manual control
def move_to_center():
    """Just move empties to center (manual control)"""
    prepare_for_export()
    
def restore_positions():
    """Just restore positions (manual control)"""
    restore_after_export()

if __name__ == "__main__":
    print("Mass Exporter v3 Fix - FINAL VERSION")
    print("\n🔥 SIMPLE USAGE:")
    print("   prepare_for_export()  - Move everything to center")
    print("   restore_after_export()  - Restore original positions")  
    print("\n🚀 AUTOMATIC:")
    print("   export_workflow()  - Complete automated workflow")
    print("\n⚡ QUICK:")
    print("   move_to_center()  - Quick move")
    print("   restore_positions()  - Quick restore")
    
    print("\n" + "="*50)
    print("READY TO USE! 🎯")
