# Test Centering Only - Debug Button Addition
# This adds a new operator and button specifically for testing parent empty centering

import bpy
from bpy.types import Operator

class MASSEXPORTER_OT_test_centering_only(Operator):
    """Test only the parent empty centering functionality without combining"""
    bl_idname = "massexporter.test_centering_only"
    bl_label = "Test Centering Only"
    bl_description = "Test only the parent empty centering (move to origin and restore)"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        # Force OBJECT mode
        if bpy.ops.object.mode_set.poll():
            bpy.ops.object.mode_set(mode='OBJECT')
        
        props = context.scene.mass_exporter_props
        
        # Find all empties with children in the scene
        empties_to_test = []
        for obj in bpy.context.scene.objects:
            if obj.type == 'EMPTY':
                # Find mesh children
                mesh_children = [child for child in obj.children if child.type == 'MESH']
                if mesh_children:
                    empties_to_test.append({
                        'empty': obj,
                        'children': mesh_children,
                        'original_world_pos': obj.matrix_world.translation.copy()
                    })
        
        if not empties_to_test:
            self.report({'WARNING'}, "No parent empties with mesh children found")
            return {'CANCELLED'}
        
        self.report({'INFO'}, f"Testing centering for {len(empties_to_test)} empties")
        
        # Test centering for each empty
        for test_data in empties_to_test:
            self.test_single_empty_centering(test_data, props.debug_mode)
        
        self.report({'INFO'}, f"Centering test complete for {len(empties_to_test)} empties")
        return {'FINISHED'}
    
    def test_single_empty_centering(self, test_data, debug_mode):
        """Test centering and restoration for a single empty"""
        empty = test_data['empty']
        children = test_data['children']
        
        print(f"\n=== TESTING CENTERING: {empty.name} ===")
        print(f"Original world position: {empty.matrix_world.translation}")
        if empty.parent:
            print(f"Has parent: {empty.parent.name}")
        print(f"Children count: {len(children)}")
        
        # Record children's original world positions
        children_original_positions = []
        for child in children:
            pos = child.matrix_world.translation.copy()
            children_original_positions.append((child.name, pos))
            print(f"  {child.name} at: {pos}")
        
        # Move to center (using the fixed approach from your script)
        print("\n--- Moving to world center ---")
        original_world_pos = self.move_empty_to_world_center(empty, debug_mode)
        
        # Check if we reached origin
        current_pos = empty.matrix_world.translation
        distance = current_pos.length
        if distance > 0.001:
            print(f"ERROR: Failed to reach origin! Distance: {distance}")
        else:
            print(f"SUCCESS: Empty at origin (distance: {distance})")
        
        # Show where children ended up
        print("\nChildren after centering:")
        for child in children:
            print(f"  {child.name} at: {child.matrix_world.translation}")
        
        # Hold at center for a moment (optional - remove if not needed)
        bpy.context.view_layer.update()
        
        # Restore to original position
        print("\n--- Restoring to original position ---")
        self.restore_empty_to_original_position(empty, original_world_pos, debug_mode)
        
        # Verify restoration
        final_pos = empty.matrix_world.translation
        restore_error = (final_pos - test_data['original_world_pos']).length
        if restore_error > 0.001:
            print(f"ERROR: Not fully restored! Error: {restore_error}")
        else:
            print(f"SUCCESS: Empty restored (error: {restore_error})")
        
        # Check children restoration
        print("\nChildren after restoration:")
        for i, (child_name, original_pos) in enumerate(children_original_positions):
            child_obj = bpy.data.objects.get(child_name)
            if child_obj:
                current_pos = child_obj.matrix_world.translation
                error = (current_pos - original_pos).length
                status = "OK" if error < 0.001 else f"ERROR: {error}"
                print(f"  {child_name}: {status}")
        
        print(f"=== COMPLETE: {empty.name} ===\n")
    
    def move_empty_to_world_center(self, empty, debug_mode=False):
        """Move an empty to world center - copied from your fixed version"""
        import mathutils
        
        # Get current world position
        original_world_pos = empty.matrix_world.translation.copy()
        
        if debug_mode:
            print(f"  Moving {empty.name} from world {original_world_pos} to world (0,0,0)")
            if empty.parent:
                print(f"  {empty.name} has parent: {empty.parent.name}")
        
        # Method depends on whether empty has a parent
        if empty.parent:
            # Empty has a parent - need to account for parent's transform
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
    
    def restore_empty_to_original_position(self, empty, original_world_pos, debug_mode=False):
        """Restore an empty to its original world position - copied from your fixed version"""
        import mathutils
        
        if debug_mode:
            print(f"  Restoring {empty.name} to original world position {original_world_pos}")
            if empty.parent:
                print(f"  {empty.name} has parent: {empty.parent.name}")
        
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


# For reference - this is how to add the button to your existing panel
# Add this to your MASSEXPORTER_PT_main_panel class draw method:
#
# def draw(self, context):
#     layout = self.layout
#     props = context.scene.mass_exporter_props
#
#     # Export button
#     layout.operator("massexporter.export_all", text="Export All Collections", icon='EXPORT')
#
#     # Test buttons row
#     row = layout.row(align=True)
#     row.operator("massexporter.test_empty_centering", text="Test Empty Operations", icon='EMPTY_ARROWS')
#     row.operator("massexporter.test_centering_only", text="Test Centering Only", icon='PIVOT_CURSOR')
#
#     layout.separator()
#
#     # Debug mode
#     layout.prop(props, "debug_mode")


# For registering the new operator, add to your classes list:
# classes = [
#     ...existing classes...
#     MASSEXPORTER_OT_test_centering_only,  # Add this line
#     ...rest of classes...
# ]
