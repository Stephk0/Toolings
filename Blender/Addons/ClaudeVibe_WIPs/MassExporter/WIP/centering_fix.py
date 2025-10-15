import bpy
import mathutils

def move_empty_to_world_center_fixed(empty, debug_mode=False):
    """
    Move an empty to world center (0,0,0) - FIXED VERSION.
    Properly handles empties with parent transforms.
    Returns the original world position for restoration.
    """
    # Get current world position
    original_world_pos = empty.matrix_world.translation.copy()
    
    if debug_mode:
        print(f"  Moving {empty.name} from world {original_world_pos} to world (0,0,0)")
        if empty.parent:
            print(f"  {empty.name} has parent: {empty.parent.name}")
    
    # Method depends on whether empty has a parent
    if empty.parent:
        # Empty has a parent - need to account for parent's transform
        # Convert world target (0,0,0) to parent's local space
        parent_matrix_inv = empty.parent.matrix_world.inverted()
        target_in_parent_space = parent_matrix_inv @ mathutils.Vector((0, 0, 0))
        
        # Set location in parent space
        empty.location = target_in_parent_space
    else:
        # No parent - simple case
        empty.location = mathutils.Vector((0, 0, 0))
    
    # Update scene
    bpy.context.view_layer.update()
    
    if debug_mode:
        new_world_pos = empty.matrix_world.translation
        print(f"  {empty.name} now at world: {new_world_pos}")
        # Check if we actually reached (0,0,0)
        distance = new_world_pos.length
        if distance > 0.001:
            print(f"  WARNING: Not exactly at origin! Distance: {distance}")
    
    return original_world_pos

def restore_empty_to_original_position_fixed(empty, original_world_pos, debug_mode=False):
    """
    Restore an empty to its original world position - FIXED VERSION.
    Properly handles empties with parent transforms.
    """
    if debug_mode:
        print(f"  Restoring {empty.name} to original world position {original_world_pos}")
    
    # Method depends on whether empty has a parent
    if empty.parent:
        # Empty has a parent - convert world position to parent's local space
        parent_matrix_inv = empty.parent.matrix_world.inverted()
        target_in_parent_space = parent_matrix_inv @ original_world_pos
        
        # Set location in parent space
        empty.location = target_in_parent_space
    else:
        # No parent - simple case
        empty.location = original_world_pos
    
    # Update scene
    bpy.context.view_layer.update()
    
    if debug_mode:
        restored_world_pos = empty.matrix_world.translation
        print(f"  {empty.name} restored to world: {restored_world_pos}")
        # Check restoration accuracy
        distance = (restored_world_pos - original_world_pos).length
        if distance > 0.001:
            print(f"  WARNING: Not exactly restored! Distance error: {distance}")

# Alternative approach using matrix decomposition
def move_empty_to_world_center_matrix(empty, debug_mode=False):
    """
    Alternative method using matrix decomposition.
    This approach preserves rotation and scale while moving to origin.
    """
    # Store original world matrix
    original_matrix = empty.matrix_world.copy()
    original_world_pos = original_matrix.translation.copy()
    
    if debug_mode:
        print(f"  Moving {empty.name} from world {original_world_pos} to world (0,0,0)")
    
    # Decompose the world matrix
    loc, rot, scale = original_matrix.decompose()
    
    # Create new matrix with position at origin
    new_matrix = mathutils.Matrix.Translation((0, 0, 0)) @ rot.to_matrix().to_4x4()
    
    # Apply scale
    for i in range(3):
        new_matrix[i][i] *= scale[i]
    
    # Set the new world matrix
    empty.matrix_world = new_matrix
    
    # Update scene
    bpy.context.view_layer.update()
    
    if debug_mode:
        new_world_pos = empty.matrix_world.translation
        print(f"  {empty.name} now at world: {new_world_pos}")
    
    return original_world_pos

# Test function to verify centering works
def test_centering_methods():
    """Test all centering methods to see which works best"""
    
    # Find or create test empty with child
    empty = None
    for obj in bpy.context.scene.objects:
        if obj.type == 'EMPTY' and len([c for c in obj.children if c.type == 'MESH']) > 0:
            empty = obj
            break
    
    if not empty:
        # Create test empty and child
        bpy.ops.object.empty_add(type='PLAIN_AXES', location=(5, 3, 2))
        empty = bpy.context.active_object
        empty.name = "Test_Empty"
        
        bpy.ops.mesh.primitive_cube_add(location=(6, 4, 3))
        cube = bpy.context.active_object
        cube.name = "Test_Cube"
        cube.parent = empty
    
    print("\n=== TESTING CENTERING METHODS ===")
    print(f"Test empty: {empty.name}")
    print(f"Has parent: {empty.parent is not None}")
    
    # Store original position
    original_pos = empty.matrix_world.translation.copy()
    print(f"Original world position: {original_pos}")
    
    # Test fixed method
    print("\n--- Testing Fixed Method ---")
    restored_pos = move_empty_to_world_center_fixed(empty, debug_mode=True)
    
    # Check if at origin
    current_pos = empty.matrix_world.translation
    distance = current_pos.length
    print(f"Distance from origin: {distance}")
    
    if distance < 0.001:
        print("✓ Successfully moved to origin!")
    else:
        print("✗ Failed to reach origin exactly")
    
    # Restore
    restore_empty_to_original_position_fixed(empty, restored_pos, debug_mode=True)
    
    # Check restoration
    final_pos = empty.matrix_world.translation
    restore_distance = (final_pos - original_pos).length
    print(f"Restoration error: {restore_distance}")
    
    if restore_distance < 0.001:
        print("✓ Successfully restored!")
    else:
        print("✗ Restoration not exact")
    
    print("\n=== TEST COMPLETE ===")

# Run the test
test_centering_methods()
