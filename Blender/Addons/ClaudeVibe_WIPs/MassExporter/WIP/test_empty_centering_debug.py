import bpy
import mathutils

def test_empty_centering():
    """Test script to debug empty centering issues"""
    
    # Find an empty with children
    empty = None
    for obj in bpy.context.scene.objects:
        if obj.type == 'EMPTY' and len([c for c in obj.children if c.type == 'MESH']) > 0:
            empty = obj
            break
    
    if not empty:
        print("No empty with mesh children found!")
        return
    
    print(f"\n=== Testing Empty: {empty.name} ===")
    print(f"Empty local location: {empty.location}")
    print(f"Empty world location: {empty.matrix_world.translation}")
    
    # Get children
    children = [c for c in empty.children if c.type == 'MESH']
    print(f"Children: {[c.name for c in children]}")
    
    # Store original positions
    original_empty_world = empty.matrix_world.translation.copy()
    original_empty_local = empty.location.copy()
    
    children_original = []
    for child in children:
        children_original.append({
            'name': child.name,
            'world': child.matrix_world.translation.copy(),
            'local': child.location.copy()
        })
    
    print("\n--- Method 1: Direct World Translation ---")
    # Calculate the offset needed to move to world center
    world_offset = mathutils.Vector((0.0, 0.0, 0.0)) - empty.matrix_world.translation
    print(f"World offset needed: {world_offset}")
    
    # Apply to local position
    empty.location = empty.location + world_offset
    bpy.context.view_layer.update()
    
    print(f"New empty world location: {empty.matrix_world.translation}")
    for child in children:
        print(f"  {child.name} world: {child.matrix_world.translation}")
    
    # Restore
    empty.location = original_empty_local
    bpy.context.view_layer.update()
    
    print("\n--- Method 2: Matrix World Manipulation ---")
    # Create a translation matrix
    translation_matrix = mathutils.Matrix.Translation(-original_empty_world)
    
    # Apply to empty's matrix_world
    empty.matrix_world = translation_matrix @ empty.matrix_world
    bpy.context.view_layer.update()
    
    print(f"New empty world location: {empty.matrix_world.translation}")
    for child in children:
        print(f"  {child.name} world: {child.matrix_world.translation}")
    
    # Restore
    empty.location = original_empty_local
    bpy.context.view_layer.update()
    
    print("\n--- Method 3: Parent-Aware Translation ---")
    # If empty has parent, we need to account for parent transform
    if empty.parent:
        print(f"Empty has parent: {empty.parent.name}")
        # Convert world target to parent space
        parent_inv = empty.parent.matrix_world.inverted()
        target_in_parent = parent_inv @ mathutils.Vector((0, 0, 0))
        empty.location = target_in_parent
    else:
        # No parent, simple case
        empty.location = mathutils.Vector((0, 0, 0))
    
    bpy.context.view_layer.update()
    
    print(f"New empty world location: {empty.matrix_world.translation}")
    for child in children:
        print(f"  {child.name} world: {child.matrix_world.translation}")
    
    # Restore
    empty.location = original_empty_local
    bpy.context.view_layer.update()
    
    print("\n=== Test Complete ===")

# Run the test
test_empty_centering()
