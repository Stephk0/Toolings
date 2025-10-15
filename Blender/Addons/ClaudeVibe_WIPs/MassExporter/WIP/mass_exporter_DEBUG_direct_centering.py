bl_info = {
    "name": "Mass Collection Exporter DEBUG - Direct Centering",
    "author": "Claude AI", 
    "version": (4, 6, 0),
    "blender": (3, 0, 0),
    "location": "3D View > N-Panel > Mass Exporter",
    "description": "DEBUG version with direct centering approach",
    "category": "Import-Export",
}

import bpy
import bmesh
import os
import mathutils
from bpy.props import (
    StringProperty,
    BoolProperty,
    EnumProperty,
    CollectionProperty,
    PointerProperty,
    IntProperty
)
from bpy.types import (
    Panel,
    Operator,
    PropertyGroup,
    UIList
)
from bpy_extras.io_utils import ExportHelper

# Property Groups
class CollectionExportItem(PropertyGroup):
    """Individual collection export settings"""
    collection: PointerProperty(
        name="Collection",
        type=bpy.types.Collection,
        description="Collection to export"
    )

    export_enabled: BoolProperty(
        name="Export",
        description="Enable export for this collection",
        default=False
    )

    merge_to_single: BoolProperty(
        name="Merge",
        description="Merge all objects in collection to single file",
        default=False
    )

    export_subcollections_as_single: BoolProperty(
        name="Sub-Collections as Single",
        description="Export each sub-collection as a single merged object",
        default=False
    )

    use_empty_origins: BoolProperty(
        name="Use Parent Empties",
        description="Search for parent empties and use them as origins/centers. Will move empties to world center for export",
        default=False
    )

    center_parent_empties: BoolProperty(
        name="Center Parent Empties",
        description="Move parent empties to world center (0,0,0) before export",
        default=True
    )

    combine_empty_children: BoolProperty(
        name="Combine Empty Children",
        description="Join all mesh children of empties into single objects before export",
        default=False
    )

    export_path: StringProperty(
        name="Export Path",
        description="Path where files will be exported",
        default="",
        subtype='DIR_PATH'
    )

    visibility_synced: BoolProperty(
        name="Visible",
        description="Collection visibility (synced with scene)",
        default=True,
        update=lambda self, context: self.update_collection_visibility(context)
    )

    def update_collection_visibility(self, context):
        """Update collection visibility in scene"""
        if self.collection:
            # Update viewport visibility
            self.collection.hide_viewport = not self.visibility_synced
            # Update render visibility
            self.collection.hide_render = not self.visibility_synced

class MassExporterProperties(PropertyGroup):
    """Main property group for Mass Exporter"""

    # Collection Options
    collection_items: CollectionProperty(
        type=CollectionExportItem,
        name="Collection Export Items"
    )

    active_collection_index: IntProperty(
        name="Active Collection Index",
        default=0
    )

    debug_mode: BoolProperty(
        name="Debug Mode",
        description="Print debug information during export",
        default=True  # Default to True for debugging
    )

# SHARED FUNCTION: Direct centering approach with extensive debugging
def move_empty_to_center_DIRECT(empty):
    """
    DIRECT approach: Try multiple methods to move empty to world center
    """
    print(f"\n=== ATTEMPTING TO CENTER {empty.name} ===")
    
    # Show initial state
    print(f"BEFORE - Local: {empty.location}")
    print(f"BEFORE - World: {empty.matrix_world.translation}")
    print(f"BEFORE - Has parent: {empty.parent is not None}")
    if empty.parent:
        print(f"BEFORE - Parent: {empty.parent.name} at {empty.parent.matrix_world.translation}")
    
    # Store original values
    original_local = empty.location.copy()
    original_world = empty.matrix_world.translation.copy()
    
    # METHOD 1: Direct world matrix translation assignment
    print(f"\n--- METHOD 1: Direct world matrix assignment ---")
    try:
        empty.matrix_world.translation = mathutils.Vector((0.0, 0.0, 0.0))
        bpy.context.view_layer.update()
        print(f"AFTER METHOD 1 - Local: {empty.location}")
        print(f"AFTER METHOD 1 - World: {empty.matrix_world.translation}")
        
        # Check if it actually moved
        new_world = empty.matrix_world.translation
        if abs(new_world.x) < 0.001 and abs(new_world.y) < 0.001 and abs(new_world.z) < 0.001:
            print("✅ METHOD 1 WORKED!")
            return original_world, "method1"
        else:
            print("❌ METHOD 1 FAILED - Empty not at center")
    except Exception as e:
        print(f"❌ METHOD 1 ERROR: {e}")
    
    # METHOD 2: Clear parent, move, restore parent
    print(f"\n--- METHOD 2: Temporary parent clearing ---")
    original_parent = empty.parent
    original_parent_type = empty.parent_type if empty.parent else None
    original_parent_bone = empty.parent_bone if empty.parent else None
    
    try:
        # Clear parent
        if empty.parent:
            print(f"Clearing parent {empty.parent.name}")
            empty.parent = None
            bpy.context.view_layer.update()
        
        # Move to center
        print(f"Setting location to (0,0,0)")
        empty.location = (0, 0, 0)
        bpy.context.view_layer.update()
        
        print(f"AFTER METHOD 2 - Local: {empty.location}")
        print(f"AFTER METHOD 2 - World: {empty.matrix_world.translation}")
        
        # Check if it worked
        new_world = empty.matrix_world.translation
        if abs(new_world.x) < 0.001 and abs(new_world.y) < 0.001 and abs(new_world.z) < 0.001:
            print("✅ METHOD 2 WORKED!")
            
            # Restore parent
            if original_parent:
                print(f"Restoring parent {original_parent.name}")
                empty.parent = original_parent
                empty.parent_type = original_parent_type
                if original_parent_bone:
                    empty.parent_bone = original_parent_bone
                bpy.context.view_layer.update()
                
            return original_world, "method2"
        else:
            print("❌ METHOD 2 FAILED - Empty not at center")
            
            # Restore parent anyway
            if original_parent:
                empty.parent = original_parent
                empty.parent_type = original_parent_type
                if original_parent_bone:
                    empty.parent_bone = original_parent_bone
                bpy.context.view_layer.update()
                
    except Exception as e:
        print(f"❌ METHOD 2 ERROR: {e}")
        # Restore parent on error
        if original_parent:
            empty.parent = original_parent
            empty.parent_type = original_parent_type
            if original_parent_bone:
                empty.parent_bone = original_parent_bone
    
    # METHOD 3: Manual constraint approach
    print(f"\n--- METHOD 3: Manual position calculation ---")
    try:
        # Calculate what local position should be to achieve world (0,0,0)
        if empty.parent:
            # Get parent's world matrix
            parent_world_matrix = empty.parent.matrix_world
            # Calculate what local position would result in world (0,0,0)
            target_local = parent_world_matrix.inverted() @ mathutils.Vector((0.0, 0.0, 0.0))
            print(f"Calculated target local position: {target_local}")
        else:
            target_local = mathutils.Vector((0.0, 0.0, 0.0))
            print(f"No parent, target local position: {target_local}")
        
        empty.location = target_local
        bpy.context.view_layer.update()
        
        print(f"AFTER METHOD 3 - Local: {empty.location}")
        print(f"AFTER METHOD 3 - World: {empty.matrix_world.translation}")
        
        # Check if it worked
        new_world = empty.matrix_world.translation
        if abs(new_world.x) < 0.001 and abs(new_world.y) < 0.001 and abs(new_world.z) < 0.001:
            print("✅ METHOD 3 WORKED!")
            return original_world, "method3"
        else:
            print("❌ METHOD 3 FAILED - Empty not at center")
            
    except Exception as e:
        print(f"❌ METHOD 3 ERROR: {e}")
    
    print("❌ ALL METHODS FAILED!")
    return original_world, "failed"

def restore_empty_position(empty, original_world_pos, method_used):
    """
    Restore empty to original position using the method that worked
    """
    print(f"\n=== RESTORING {empty.name} USING {method_used} ===")
    
    if method_used == "method1":
        # Restore using world matrix
        empty.matrix_world.translation = original_world_pos
        bpy.context.view_layer.update()
        
    elif method_used == "method2":
        # For method2, we need to restore the original local position
        # But this is tricky because parent might affect it
        # Let's try setting world position directly
        empty.matrix_world.translation = original_world_pos
        bpy.context.view_layer.update()
        
    elif method_used == "method3":
        # Restore using calculated local position
        if empty.parent:
            parent_world_matrix = empty.parent.matrix_world
            target_local = parent_world_matrix.inverted() @ original_world_pos
        else:
            target_local = original_world_pos
        empty.location = target_local
        bpy.context.view_layer.update()
        
    print(f"RESTORED - Local: {empty.location}")
    print(f"RESTORED - World: {empty.matrix_world.translation}")

# UI Lists
class MASSEXPORTER_UL_collections(UIList):
    """UI List for collection items"""

    def draw_item(self, context, layout, data, item, icon, active_data, active_propname):
        if self.layout_type in {'DEFAULT', 'COMPACT'}:
            layout.prop(item, "export_enabled", text="")
            layout.prop(item, "collection", text="")

# Operators
class MASSEXPORTER_OT_add_collection(Operator):
    """Add a new collection to export list"""
    bl_idname = "massexporter.add_collection"
    bl_label = "Add Collection"
    bl_description = "Add a new collection to the export list"

    def execute(self, context):
        props = context.scene.mass_exporter_props
        new_item = props.collection_items.add()
        props.active_collection_index = len(props.collection_items) - 1
        return {'FINISHED'}

class MASSEXPORTER_OT_remove_collection(Operator):
    """Remove collection from export list"""
    bl_idname = "massexporter.remove_collection"
    bl_label = "Remove Collection"
    bl_description = "Remove selected collection from export list"

    def execute(self, context):
        props = context.scene.mass_exporter_props
        if props.collection_items:
            props.collection_items.remove(props.active_collection_index)
            props.active_collection_index = max(0, props.active_collection_index - 1)
        return {'FINISHED'}

class MASSEXPORTER_OT_test_empty_centering(Operator):
    """Test parent empty centering with extensive debugging"""
    bl_idname = "massexporter.test_empty_centering"
    bl_label = "DEBUG Test Empty Centering"
    bl_description = "Test empty centering with multiple methods and extensive debugging"

    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        # Force OBJECT mode
        if bpy.ops.object.mode_set.poll():
            bpy.ops.object.mode_set(mode='OBJECT')

        # Find empties with children in the scene
        empties_data = self.find_all_empties_with_children()

        if not empties_data:
            self.report({'WARNING'}, "No parent empties with mesh children found in scene")
            return {'CANCELLED'}

        print(f"\n{'='*60}")
        print(f"STARTING DEBUG TEST OF EMPTY CENTERING")
        print(f"Found {len(empties_data)} empties to test")
        print(f"{'='*60}")

        # Test each empty
        test_count = 0
        for empty_name, children_names in empties_data.items():
            if self.test_single_empty(empty_name, children_names):
                test_count += 1

        print(f"\n{'='*60}")
        print(f"DEBUG TEST COMPLETE")
        print(f"Successfully tested {test_count}/{len(empties_data)} empties")
        print(f"{'='*60}")

        self.report({'INFO'}, f"DEBUG: Tested {test_count} empties - check console for details")
        return {'FINISHED'}

    def find_all_empties_with_children(self):
        """Find all empty objects with mesh children"""
        empties_data = {}

        for obj in bpy.context.scene.objects:
            if obj.type == 'EMPTY':
                children_names = [child.name for child in obj.children if child.type == 'MESH']
                if children_names:
                    empties_data[obj.name] = children_names

        return empties_data

    def test_single_empty(self, empty_name, children_names):
        """Test centering a single empty with full debugging"""
        
        # Get object reference
        if empty_name not in bpy.data.objects:
            print(f"❌ Empty {empty_name} not found")
            return False

        empty = bpy.data.objects[empty_name]
        children = [bpy.data.objects[name] for name in children_names if name in bpy.data.objects]

        if not children:
            print(f"❌ No valid children found for {empty_name}")
            return False

        print(f"\n{'='*40}")
        print(f"TESTING: {empty_name}")
        print(f"Children: {children_names}")
        print(f"{'='*40}")

        # Store children positions before
        children_before = {}
        for child in children:
            children_before[child.name] = child.matrix_world.translation.copy()
            print(f"Child {child.name} before: {child.matrix_world.translation}")

        try:
            # Attempt to center the empty
            original_world_pos, method_used = move_empty_to_center_DIRECT(empty)
            
            if method_used != "failed":
                # Show children positions after centering
                print(f"\n--- CHILDREN AFTER CENTERING ---")
                for child in children:
                    new_pos = child.matrix_world.translation
                    print(f"Child {child.name} after: {new_pos}")
                
                # Wait a moment so user can see the change
                print(f"\n⏸️  EMPTY IS NOW CENTERED - Check viewport!")
                print(f"Empty {empty_name} should be at world center (0,0,0)")
                print(f"Press SPACE to continue restoration...")
                
                # Restore original position
                restore_empty_position(empty, original_world_pos, method_used)
                
                # Show children positions after restoration
                print(f"\n--- CHILDREN AFTER RESTORATION ---")
                for child in children:
                    restored_pos = child.matrix_world.translation
                    original_pos = children_before[child.name]
                    diff = (restored_pos - original_pos).length
                    print(f"Child {child.name} restored: {restored_pos} (diff: {diff:.6f})")
                
                print(f"✅ Test of {empty_name} completed using {method_used}")
                return True
            else:
                print(f"❌ Failed to center {empty_name}")
                return False
                
        except Exception as e:
            print(f"❌ Error testing {empty_name}: {str(e)}")
            return False

# Panels
class MASSEXPORTER_PT_main_panel(Panel):
    """Main Mass Exporter Panel"""
    bl_label = "Mass Exporter DEBUG"
    bl_idname = "MASSEXPORTER_PT_main_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Mass Exporter"

    def draw(self, context):
        layout = self.layout
        props = context.scene.mass_exporter_props

        # Test button
        layout.operator("massexporter.test_empty_centering", text="DEBUG Test Empty Centering", icon='EMPTY_ARROWS')

        layout.separator()
        layout.label(text="This is a DEBUG version")
        layout.label(text="Check console for detailed output")

# Registration
classes = [
    CollectionExportItem,
    MassExporterProperties,
    MASSEXPORTER_UL_collections,
    MASSEXPORTER_OT_add_collection,
    MASSEXPORTER_OT_remove_collection,
    MASSEXPORTER_OT_test_empty_centering,
    MASSEXPORTER_PT_main_panel,
]

def register():
    for cls in classes:
        bpy.utils.register_class(cls)

    bpy.types.Scene.mass_exporter_props = PointerProperty(type=MassExporterProperties)

def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)

    del bpy.types.Scene.mass_exporter_props

if __name__ == "__main__":
    register()
