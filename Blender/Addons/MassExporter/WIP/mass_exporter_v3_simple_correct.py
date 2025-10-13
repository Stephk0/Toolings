"""
Mass Exporter v3 Parent Empty Fix - SIMPLE & CORRECT VERSION
Just move parent empties to center - children follow automatically via parent-child relationship
"""

import bpy
from mathutils import Vector

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

def export_workflow():
    """Complete export workflow with automatic parent empty handling"""
    print("=== MASS EXPORTER V3 WORKFLOW ===")
    
    # Prepare for export
    if not prepare_for_export():
        print("No parent empties found in subcollections - export normally")
        return
    
    print("\n🎯 EXPORT NOW - Parent empties centered, children followed automatically")
    
    # Your export code goes here:
    """
    Example:
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.export_scene.fbx(filepath="your_path.fbx")
    """
    
    input("\nPress Enter after your export is complete...")
    
    # Restore positions
    restore_after_export()
    print("\n✅ Export workflow complete!")

def show_current_positions():
    """Debug function to show current positions"""
    print("=== CURRENT POSITIONS ===")
    for obj in bpy.context.scene.objects:
        if obj.type == 'EMPTY' and len(obj.children) > 0:
            print(f"Empty '{obj.name}': {obj.location}")
            for child in obj.children:
                print(f"  Child '{child.name}': {child.location}")

# Simple aliases
def move_to_center():
    """Move parent empties to center"""
    prepare_for_export()

def restore_positions():
    """Restore parent empties to original positions"""
    restore_after_export()

if __name__ == "__main__":
    print("Mass Exporter v3 Fix - SIMPLE & CORRECT VERSION")
    print("Parent-child relationships handle movement automatically!")
    print("\n🔥 USAGE:")
    print("   prepare_for_export() - Move parent empties to center")
    print("   restore_after_export() - Restore to original positions")
    print("   export_workflow() - Complete automated workflow")
    print("   show_current_positions() - Debug current positions")
    print("\n" + "="*60)
    print("✨ READY TO USE - Children follow parents automatically! ✨")
