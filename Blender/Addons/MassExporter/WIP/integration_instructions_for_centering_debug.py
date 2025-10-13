"""
Integration instructions for adding the "Test Centering Only" debug button
to your mass_exporter_fixed_v8_proper_centering.py script

Add this new operator class after your existing MASSEXPORTER_OT_test_empty_centering class
(around line 850 in your script):
"""

# ============================================
# NEW OPERATOR CLASS TO ADD
# ============================================

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
        
        # Try to get center_parent_empties setting from active collection
        center_parent_empties = True
        if props.collection_items and len(props.collection_items) > 0:
            active = props.collection_items[props.active_collection_index]
            center_parent_empties = bool(getattr(active, "center_parent_empties", True))
        
        if not center_parent_empties:
            self.report({'INFO'}, "Center Parent Empties is disabled in active collection settings")
            return {'CANCELLED'}
        
        # Find all empties with children in the scene
        empties_to_test = []
        test_count = 0
        
        for obj in bpy.context.scene.objects:
            if obj.type == 'EMPTY':
                # Find mesh children
                mesh_children = [child for child in obj.children if child.type == 'MESH']
                if mesh_children:
                    empties_to_test.append({
                        'empty_name': obj.name,
                        'children_names': [c.name for c in mesh_children]
                    })
        
        if not empties_to_test:
            self.report({'WARNING'}, "No parent empties with mesh children found")
            return {'CANCELLED'}
        
        self.report({'INFO'}, f"Testing centering for {len(empties_to_test)} empties")
        
        # Test centering for each empty
        for test_data in empties_to_test:
            if self.test_single_empty_centering(test_data, props.debug_mode):
                test_count += 1
        
        self.report({'INFO'}, f"Centering test complete for {test_count}/{len(empties_to_test)} empties")
        return {'FINISHED'}
    
    def test_single_empty_centering(self, test_data, debug_mode):
        """Test centering and restoration for a single empty"""
        empty_name = test_data['empty_name']
        children_names = test_data['children_names']
        
        # Get fresh references
        if empty_name not in bpy.data.objects:
            return False
        
        empty = bpy.data.objects[empty_name]
        children = [bpy.data.objects[name] for name in children_names if name in bpy.data.objects]
        
        if not children:
            return False
        
        print(f"\n{'='*60}")
        print(f"TESTING CENTERING: {empty.name}")
        print(f"{'='*60}")
        print(f"Original world position: {empty.matrix_world.translation}")
        if empty.parent:
            print(f"Has parent: {empty.parent.name}")
        print(f"Children count: {len(children)}")
        
        # Record children's original world positions
        children_original_positions = []
        print("\nChildren initial positions:")
        for child in children:
            pos = child.matrix_world.translation.copy()
            children_original_positions.append((child.name, pos))
            print(f"  {child.name}: {pos}")
        
        # Store original position
        original_world_pos = empty.matrix_world.translation.copy()
        
        try:
            # Move to center (using the fixed approach)
            print("\n--- Phase 1: Moving to world center ---")
            moved_pos = move_empty_to_world_center(empty, debug_mode)
            
            # Verify centering
            current_pos = empty.matrix_world.translation
            distance = current_pos.length
            
            if distance > 0.001:
                print(f"❌ ERROR: Failed to reach origin! Distance: {distance:.6f}")
                centering_success = False
            else:
                print(f"✓ SUCCESS: Empty at origin (distance: {distance:.6f})")
                centering_success = True
            
            # Show where children ended up
            print("\nChildren after centering:")
            for child in children:
                pos = child.matrix_world.translation
                print(f"  {child.name}: {pos}")
            
            # Hold at center briefly for visual verification
            bpy.context.view_layer.update()
            
            # Restore to original position
            print("\n--- Phase 2: Restoring to original position ---")
            restore_empty_to_original_position(empty, moved_pos, debug_mode)
            
            # Verify restoration
            final_pos = empty.matrix_world.translation
            restore_error = (final_pos - original_world_pos).length
            
            if restore_error > 0.001:
                print(f"❌ ERROR: Not fully restored! Error: {restore_error:.6f}")
                restore_success = False
            else:
                print(f"✓ SUCCESS: Empty restored (error: {restore_error:.6f})")
                restore_success = True
            
            # Check children restoration
            print("\nChildren after restoration:")
            all_children_restored = True
            for child_name, original_pos in children_original_positions:
                child_obj = bpy.data.objects.get(child_name)
                if child_obj:
                    current_pos = child_obj.matrix_world.translation
                    error = (current_pos - original_pos).length
                    if error > 0.001:
                        print(f"  {child_name}: ❌ ERROR {error:.6f}")
                        all_children_restored = False
                    else:
                        print(f"  {child_name}: ✓ OK")
            
            # Summary
            print(f"\n{'='*60}")
            if centering_success and restore_success and all_children_restored:
                print(f"✓ ALL TESTS PASSED: {empty.name}")
            else:
                print(f"⚠ SOME TESTS FAILED: {empty.name}")
                if not centering_success:
                    print("  - Centering failed")
                if not restore_success:
                    print("  - Restoration failed")
                if not all_children_restored:
                    print("  - Some children not restored")
            print(f"{'='*60}\n")
            
            return centering_success and restore_success
            
        except Exception as e:
            print(f"❌ ERROR during test: {str(e)}")
            # Try to restore on error
            try:
                empty = bpy.data.objects.get(empty_name)
                if empty:
                    restore_empty_to_original_position(empty, original_world_pos, debug_mode)
            except:
                pass
            return False


# ============================================
# MODIFY YOUR EXISTING PANEL
# ============================================

"""
In your MASSEXPORTER_PT_main_panel class (around line 1890), 
modify the draw method to add the new button:
"""

class MASSEXPORTER_PT_main_panel(Panel):
    """Main Mass Exporter Panel"""
    bl_label = "Mass Exporter Fixed v8 - Proper Centering"
    bl_idname = "MASSEXPORTER_PT_main_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Mass Exporter"

    def draw(self, context):
        layout = self.layout
        props = context.scene.mass_exporter_props

        # Export button
        layout.operator("massexporter.export_all", text="Export All Collections", icon='EXPORT')

        # Test buttons in a row
        col = layout.column(align=True)
        col.label(text="Debug Tools:")
        row = col.row(align=True)
        row.operator("massexporter.test_empty_centering", text="Test Full Operations", icon='EMPTY_ARROWS')
        row.operator("massexporter.test_centering_only", text="Test Centering Only", icon='PIVOT_CURSOR')

        layout.separator()

        # Debug mode
        layout.prop(props, "debug_mode")


# ============================================
# UPDATE YOUR CLASSES LIST
# ============================================

"""
In your classes list (around line 2030), add the new operator:
"""

classes = [
    CollectionExportItem,
    MassExporterProperties,
    MASSEXPORTER_UL_collections,
    MASSEXPORTER_OT_add_collection,
    MASSEXPORTER_OT_remove_collection,
    MASSEXPORTER_OT_select_folder,
    MASSEXPORTER_OT_refresh_collections,
    MASSEXPORTER_OT_test_empty_centering,
    MASSEXPORTER_OT_test_centering_only,  # ADD THIS LINE
    MASSEXPORTER_OT_export_all,
    MASSEXPORTER_PT_main_panel,
    MASSEXPORTER_PT_collections,
    MASSEXPORTER_PT_transform,
    MASSEXPORTER_PT_materials,
    MASSEXPORTER_PT_export,
]
