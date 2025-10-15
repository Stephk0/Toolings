bl_info = {
    "name": "Mass Collection Exporter Fixed v6 - Export Functions Fixed",
    "author": "Claude AI",
    "version": (4, 4, 0),
    "blender": (3, 0, 0),
    "location": "3D View > N-Panel > Mass Exporter",
    "description": "Export collections with PROPERLY SYNCED test and export world-space centering",
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
        description="Move parent empties to WORLD center (0,0,0) before export - works with parented empties",
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

    # Transform Options
    export_at_origin: BoolProperty(
        name="Export at Origin",
        description="Move objects to origin before export",
        default=False
    )

    apply_transforms: BoolProperty(
        name="Apply Transforms",
        description="Apply object transforms before export",
        default=False
    )

    axis_forward: EnumProperty(
        name="Forward Axis",
        description="Forward axis for export",
        items=[
            ('X', 'X Forward', ''),
            ('Y', 'Y Forward', ''),
            ('Z', 'Z Forward', ''),
            ('-X', '-X Forward', ''),
            ('-Y', '-Y Forward', ''),
            ('-Z', '-Z Forward', ''),
        ],
        default='Y'
    )

    axis_up: EnumProperty(
        name="Up Axis",
        description="Up axis for export",
        items=[
            ('X', 'X Up', ''),
            ('Y', 'Y Up', ''),
            ('Z', 'Z Up', ''),
            ('-X', '-X Up', ''),
            ('-Y', '-Y Up', ''),
            ('-Z', '-Z Up', ''),
        ],
        default='Z'
    )

    # Material Options
    override_materials: BoolProperty(
        name="Override Materials",
        description="Override materials on export",
        default=False
    )

    override_material: PointerProperty(
        name="Override Material",
        type=bpy.types.Material,
        description="Material to use for override"
    )

    assign_if_no_material: BoolProperty(
        name="Assign Override Material if No Material",
        description="Assign override material to objects with no material",
        default=False
    )

    add_m_prefix: BoolProperty(
        name="Add M_ Prefix if Missing",
        description="Add M_ prefix to material names if missing",
        default=False
    )

    # File Export Options
    export_format: EnumProperty(
        name="Export Format",
        description="File format for export",
        items=[
            ('FBX', 'FBX', 'Export as FBX'),
            ('OBJ', 'OBJ', 'Export as OBJ'),
            ('DAE', 'Collada (DAE)', 'Export as Collada'),
            ('GLTF', 'glTF 2.0', 'Export as glTF 2.0'),
        ],
        default='FBX'
    )

    use_custom_fbx_ascii: BoolProperty(
        name="Custom FBX ASCII Exporter (Experimental)",
        description="Use custom ASCII FBX exporter (experimental feature)",
        default=False
    )

    debug_mode: BoolProperty(
        name="Debug Mode",
        description="Print debug information during export",
        default=False
    )

# UI Lists
class MASSEXPORTER_UL_collections(UIList):
    """UI List for collection items"""

    def draw_item(self, context, layout, data, item, icon, active_data, active_propname):
        if self.layout_type in {'DEFAULT', 'COMPACT'}:
            # Visibility toggle
            layout.prop(item, "visibility_synced", text="", icon='HIDE_OFF' if item.visibility_synced else 'HIDE_ON')

            # Export checkbox
            layout.prop(item, "export_enabled", text="")

            # Merge checkbox
            layout.prop(item, "merge_to_single", text="", icon='SNAP_FACE_CENTER')

            # Collection selector
            layout.prop(item, "collection", text="")

            # Export path
            row = layout.row()
            row.prop(item, "export_path", text="")
            row.operator("massexporter.select_folder", text="", icon='FOLDER_REDIRECT').index = data.collection_items.find(item.name)

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

class MASSEXPORTER_OT_select_folder(Operator, ExportHelper):
    """Select folder for export path"""
    bl_idname = "massexporter.select_folder"
    bl_label = "Select Export Folder"
    bl_description = "Select folder for export path"

    filename_ext = ""
    use_filter_folder = True

    index: IntProperty()

    def execute(self, context):
        props = context.scene.mass_exporter_props
        if self.index < len(props.collection_items):
            # Get directory path from filepath
            directory = os.path.dirname(self.filepath)
            props.collection_items[self.index].export_path = directory
        return {'FINISHED'}

class MASSEXPORTER_OT_refresh_collections(Operator):
    """Refresh collections list"""
    bl_idname = "massexporter.refresh_collections"
    bl_label = "Refresh Collections"
    bl_description = "Refresh the collections list from scene"

    def execute(self, context):
        props = context.scene.mass_exporter_props

        # Update visibility sync for existing items
        for item in props.collection_items:
            if item.collection:
                item.visibility_synced = not item.collection.hide_viewport

        self.report({'INFO'}, "Collections refreshed")
        return {'FINISHED'}

# SHARED FUNCTION: World space empty centering (used by both test and export)
def center_empty_to_world_origin(empty, debug_mode=False):
    """
    Center an empty to world origin using world space transforms.
    Returns the original world matrix for restoration.
    This is the MASTER function that both test and export use.
    """
    if debug_mode:
        print(f"  Centering {empty.name} from world {empty.matrix_world.translation} to world (0,0,0)")
    
    # Store original world matrix
    empty_world_matrix = empty.matrix_world.copy()
    
    # Set world translation to origin
    empty.matrix_world.translation = mathutils.Vector((0.0, 0.0, 0.0))
    bpy.context.view_layer.update()
    
    if debug_mode:
        print(f"  {empty.name} now at world: {empty.matrix_world.translation}")
    
    return empty_world_matrix

def restore_empty_world_matrix(empty, original_matrix, debug_mode=False):
    """
    Restore an empty's world matrix.
    This is the MASTER function that both test and export use.
    """
    if debug_mode:
        print(f"  Restoring {empty.name} to original world matrix")
    
    empty.matrix_world = original_matrix
    bpy.context.view_layer.update()
    
    if debug_mode:
        print(f"  {empty.name} restored to world: {empty.matrix_world.translation}")

class MASSEXPORTER_OT_test_empty_centering(Operator):
    """Test parent empty centering and combining functionality"""
    bl_idname = "massexporter.test_empty_centering"
    bl_label = "Test Empty Centering & Combining"
    bl_description = "Test the parent empty centering and mesh combining functionality without exporting"

    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        # Force OBJECT mode to avoid operator context errors
        if bpy.ops.object.mode_set.poll():
            bpy.ops.object.mode_set(mode='OBJECT')
            
        # Read active item's parent-empty options so the test mirrors export behavior
        props = context.scene.mass_exporter_props
        center_parent_empties = True
        combine_empty_children = False
        
        # Try to read from the active collection item if available
        try:
            if props.collection_items and len(props.collection_items) > 0:
                active = props.collection_items[props.active_collection_index]
                center_parent_empties = bool(getattr(active, "center_parent_empties", True))
                combine_empty_children = bool(getattr(active, "combine_empty_children", False))
        except Exception:
            pass

        # Find empties with children in the scene - store names instead of references
        empties_data = self.find_all_empties_with_children()

        if not empties_data:
            self.report({'WARNING'}, "No parent empties with mesh children found in scene")
            return {'CANCELLED'}

        # Test both centering and combining for each empty
        test_count = 0
        for empty_name, children_names in empties_data.items():
            if self.test_empty_operations(
                empty_name,
                children_names,
                center_parent_empties=center_parent_empties,
                combine_empty_children=combine_empty_children
            ):
                test_count += 1

        self.report({'INFO'}, f"Tested operations for {test_count} empties")
        return {'FINISHED'}

    def find_all_empties_with_children(self):
        """Find all empty objects with mesh children - return names instead of object references"""
        empties_data = {}

        for obj in bpy.context.scene.objects:
            if obj.type == 'EMPTY':
                # Find mesh children of this empty
                children_names = [child.name for child in obj.children if child.type == 'MESH']
                if children_names:
                    empties_data[obj.name] = children_names

        return empties_data

    def test_empty_operations(self, empty_name, children_names, *, center_parent_empties=True, combine_empty_children=False):
        """Test centering and combining operations - USES SHARED FUNCTIONS"""
        # Get fresh object references at the start
        if empty_name not in bpy.data.objects:
            print(f"Empty {empty_name} not found")
            return False

        empty = bpy.data.objects[empty_name]
        children = [bpy.data.objects[name] for name in children_names if name in bpy.data.objects]

        if not children:
            print(f"No valid children found for {empty_name}")
            return False

        print(f"\n=== TESTING OPERATIONS FOR: {empty_name} ===")
        print(f"Original empty local: {empty.location}, world: {empty.matrix_world.translation}")
        print(f"Children: {children_names}")

        # Store children world positions before centering
        children_original_world_positions = []
        for child in children:
            world_pos = child.matrix_world.translation.copy()
            children_original_world_positions.append({
                'name': child.name,
                'world_position': world_pos
            })
            print(f"  {child.name} original world position: {world_pos}")

        # Store original matrix for restoration
        empty_world_matrix = None

        try:
            # Test 1: Center empty using SHARED FUNCTION
            print("\n--- Testing Empty Centering (SHARED FUNCTION) ---")
            if center_parent_empties:
                print("Children will automatically follow due to parent-child relationship")
                
                # Use the shared centering function
                empty_world_matrix = center_empty_to_world_origin(empty, debug_mode=True)
                
                # Show where children ended up (they moved automatically)
                for child in children:
                    new_world_pos = child.matrix_world.translation
                    print(f"  {child.name} new world position: {new_world_pos}")
            else:
                print("Centering disabled by options; skipping move.")

            # Test 2: Combine children (if more than one)
            if combine_empty_children and len(children) > 1:
                print("\n--- Testing Mesh Combining ---")

                # Clear selection
                bpy.ops.object.select_all(action='DESELECT')

                # Select all children
                for child in children:
                    child.select_set(True)

                if children:
                    bpy.context.view_layer.objects.active = children[0]
                    print(f"Active object set to: {children[0].name}")

                # Count objects before join
                objects_before = len([obj for obj in bpy.context.scene.objects if obj.type == 'MESH'])
                print(f"Mesh objects before join: {objects_before}")

                # Perform join
                bpy.ops.object.join()
                print("Join operation completed!")

                objects_after = len([obj for obj in bpy.context.scene.objects if obj.type == 'MESH'])
                print(f"Mesh objects after join: {objects_after}")

                combined_obj_name = bpy.context.active_object.name if bpy.context.active_object else "Unknown"
                print(f"Combined object: {combined_obj_name}")

                # Restore using undo
                print("\n--- Restoring Original State ---")
                bpy.ops.ed.undo()
            else:
                if not combine_empty_children:
                    print("\nCombine test disabled by options; skipping")
                else:
                    print("\nOnly one child - skipping combine test")

            # Get fresh object references after any undo operations
            empty = bpy.data.objects.get(empty_name)
            if empty and empty_world_matrix:
                # Restore using SHARED FUNCTION
                restore_empty_world_matrix(empty, empty_world_matrix, debug_mode=True)
                
                # Verify children are back to original world positions
                for i, child_data in enumerate(children_original_world_positions):
                    child_obj = bpy.data.objects.get(child_data['name'])
                    if child_obj:
                        current_world_pos = child_obj.matrix_world.translation
                        print(f"  {child_obj.name} restored world position: {current_world_pos}")

            print("=== TEST COMPLETE ===\n")
            return True

        except Exception as e:
            print(f"Error during test: {str(e)}")
            # Try to restore state even on error
            try:
                if empty_world_matrix:
                    empty = bpy.data.objects.get(empty_name)
                    if empty:
                        restore_empty_world_matrix(empty, empty_world_matrix, debug_mode=True)
                bpy.ops.ed.undo()
            except:
                pass
            return False

class MASSEXPORTER_OT_export_all(Operator):
    """Export all enabled collections"""
    bl_idname = "massexporter.export_all"
    bl_label = "Export All"
    bl_description = "Export all enabled collections with current settings"

    def execute(self, context):
        # Force OBJECT mode to avoid operator context errors
        if bpy.ops.object.mode_set.poll():
            bpy.ops.object.mode_set(mode='OBJECT')
            
        props = context.scene.mass_exporter_props
        exported_count = 0

        # Store original selection and active object
        original_selection = context.selected_objects.copy()
        original_active = context.active_object

        try:
            for item in props.collection_items:
                if item.export_enabled and item.collection and item.export_path:
                    if self.export_collection(context, props, item):
                        exported_count += 1
        except Exception as e:
            self.report({'ERROR'}, f"Export failed: {str(e)}")
            return {'CANCELLED'}
        finally:
            # Restore original selection
            bpy.ops.object.select_all(action='DESELECT')
            for obj in original_selection:
                if obj.name in bpy.data.objects:  # Check if object still exists
                    obj.select_set(True)
            if original_active and original_active.name in bpy.data.objects:
                context.view_layer.objects.active = original_active

        self.report({'INFO'}, f"Exported {exported_count} collections")
        return {'FINISHED'}

    def export_collection(self, context, props, item):
        """Export a single collection"""
        collection = item.collection
        export_path = item.export_path

        if props.debug_mode:
            print(f"\n=== EXPORTING COLLECTION: {collection.name} ===")

        if not os.path.exists(export_path):
            try:
                os.makedirs(export_path)
            except:
                self.report({'ERROR'}, f"Cannot create directory: {export_path}")
                return False

        # Handle different export modes
        if item.export_subcollections_as_single:
            return self.export_subcollections_as_single(context, props, item)
        elif item.use_empty_origins:
            return self.export_with_empty_origins(context, props, item)
        else:
            # Original export logic
            objects = self.get_collection_objects(collection)

            if not objects:
                self.report({'WARNING'}, f"No objects found in collection: {collection.name}")
                return False

            if item.merge_to_single:
                return self.export_objects_as_single(context, props, objects, collection.name, export_path)
            else:
                success_count = 0
                for obj in objects:
                    if self.export_single_object(context, props, obj, export_path):
                        success_count += 1
                return success_count > 0

    def export_subcollections_as_single(self, context, props, item):
        """Export each sub-collection as a single merged object"""
        collection = item.collection
        export_path = item.export_path
        success_count = 0

        if props.debug_mode:
            print(f"Exporting sub-collections as single files for: {collection.name}")

        # Export main collection objects (if any) as one file
        main_objects = [obj for obj in collection.objects if obj.type == 'MESH']
        if main_objects:
            if self.export_objects_as_single(context, props, main_objects, f"{collection.name}_main", export_path):
                success_count += 1

        # Export each sub-collection as individual merged files
        for sub_collection in collection.children:
            sub_objects = self.get_collection_objects(sub_collection)
            if sub_objects:
                if self.export_objects_as_single(context, props, sub_objects, sub_collection.name, export_path):
                    success_count += 1

        return success_count > 0

    def export_with_empty_origins(self, context, props, item):
        """Export using empty objects as origins and group centers"""
        collection = item.collection
        export_path = item.export_path
        success_count = 0

        if props.debug_mode:
            print(f"Exporting with empty origins for: {collection.name}")

        # Find all empties in collection and sub-collections
        empties_with_children = self.find_empties_with_children(collection)

        if empties_with_children:
            if props.debug_mode:
                print(f"Found {len(empties_with_children)} empties with children")

            # Export each empty group
            for empty, children in empties_with_children.items():
                if props.debug_mode:
                    print(f"Processing empty: {empty.name} with {len(children)} children")

                if item.combine_empty_children:
                    # Combine children into single mesh before export
                    if self.export_combined_empty_children(context, props, children, empty, export_path, item):
                        success_count += 1
                else:
                    # Export each child individually but with empty as origin
                    for child in children:
                        if self.export_objects_with_empty_origin(context, props, [child], empty, child.name, export_path, item):
                            success_count += 1

        # Export objects without empty parents (if any)
        orphaned_objects = self.get_orphaned_objects(collection, empties_with_children)
        if orphaned_objects:
            if props.debug_mode:
                print(f"Found {len(orphaned_objects)} orphaned objects")

            if item.merge_to_single:
                if self.export_objects_as_single(context, props, orphaned_objects, f"{collection.name}_orphaned", export_path):
                    success_count += 1
            else:
                for obj in orphaned_objects:
                    if self.export_single_object(context, props, obj, export_path):
                        success_count += 1

        return success_count > 0

    def export_combined_empty_children(self, context, props, children, empty, export_path, item):
        """Combine children into single mesh and export - USES SHARED FUNCTIONS"""
        if not children:
            return False

        # Store names instead of references
        empty_name = empty.name
        children_names = [child.name for child in children]

        if props.debug_mode:
            print(f"\n--- EXPORT: Combining and exporting children of {empty_name} ---")
            print(f"Children to combine: {children_names}")

        # Store original selection
        original_selection = context.selected_objects.copy()
        original_active = context.active_object

        # Store original matrix for restoration
        empty_world_matrix = None

        try:
            # Step 1: Center empty if enabled - USES SHARED FUNCTION
            if item.center_parent_empties:
                if props.debug_mode:
                    print("Children will automatically follow the parent")

                # Use the SAME shared centering function as the test
                empty_world_matrix = center_empty_to_world_origin(empty, debug_mode=props.debug_mode)

                if props.debug_mode:
                    for child in children:
                        print(f"  {child.name} world position: {child.matrix_world.translation}")

            # Step 2: Combine children into single mesh
            if len(children) > 1:
                if props.debug_mode:
                    print(f"Combining {len(children)} children into single mesh...")

                # Clear selection
                bpy.ops.object.select_all(action='DESELECT')

                # Select all children
                for child in children:
                    child.select_set(True)

                # Set active object
                context.view_layer.objects.active = children[0]

                # Join the objects
                bpy.ops.object.join()

                # Get the combined object
                combined_obj = context.active_object
                combined_obj.name = f"{empty_name}_combined"

                if props.debug_mode:
                    print(f"Combined into: {combined_obj.name}")

                # Export the combined object
                result = self.export_single_object_direct(context, props, combined_obj, f"{empty_name}_combined", export_path)

            else:
                # Only one child, just export it with the empty's name
                child = children[0]
                if props.debug_mode:
                    print(f"Single child, exporting as: {empty_name}")

                result = self.export_single_object_direct(context, props, child, empty_name, export_path)

            return result

        except Exception as e:
            if props.debug_mode:
                print(f"Error during combine and export: {str(e)}")
            return False

        finally:
            # Restore original state
            if props.debug_mode:
                print("Restoring original state...")

            # Undo the join operation to restore individual objects
            if len(children) > 1:
                bpy.ops.ed.undo()

            # Get fresh object references after undo
            empty = bpy.data.objects.get(empty_name)
            if empty and empty_world_matrix:
                # Restore using SHARED FUNCTION
                restore_empty_world_matrix(empty, empty_world_matrix, debug_mode=props.debug_mode)

            # Restore original selection
            bpy.ops.object.select_all(action='DESELECT')
            for obj in original_selection:
                if obj.name in bpy.data.objects:
                    obj.select_set(True)
            if original_active and original_active.name in bpy.data.objects:
                context.view_layer.objects.active = original_active

            if props.debug_mode:
                print("--- Export combine complete ---\n")

    def export_objects_with_empty_origin(self, context, props, objects, empty, name, export_path, item):
        """Export objects using empty's location as origin - USES SHARED FUNCTIONS"""
        if not objects:
            return False

        # Store names instead of references
        empty_name = empty.name
        object_names = [obj.name for obj in objects]

        if props.debug_mode:
            print(f"\n--- EXPORT: Exporting with empty origin: {empty_name} ---")
            print(f"Objects: {object_names}")
            print(f"Empty original world location: {empty.matrix_world.translation}")

        # Clear selection
        bpy.ops.object.select_all(action='DESELECT')

        # Select all objects
        for obj in objects:
            obj.select_set(True)

        if objects:
            context.view_layer.objects.active = objects[0]

        # Store original matrix for restoration
        empty_world_matrix = None

        try:
            # Center parent empty if option is enabled - USES SHARED FUNCTION
            if item.center_parent_empties:
                if props.debug_mode:
                    print("Children will automatically follow the parent")

                # Use the SAME shared centering function as the test
                empty_world_matrix = center_empty_to_world_origin(empty, debug_mode=props.debug_mode)

                if props.debug_mode:
                    for obj in objects:
                        print(f"  {obj.name} world position: {obj.matrix_world.translation}")

            # Apply additional transform options
            if props.apply_transforms:
                if props.debug_mode:
                    print("Applying transforms...")
                bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)

            # Apply material overrides if needed
            if props.override_materials and props.override_material:
                self.apply_material_overrides(objects, props)

            # Set export filename
            filename = f"{name}.{props.export_format.lower()}"
            filepath = os.path.join(export_path, filename)

            if props.debug_mode:
                print(f"Exporting to: {filepath}")

            # Export based on format
            result = self.perform_export(props, filepath)

            if props.debug_mode:
                print(f"Export result: {result}")

        except Exception as e:
            if props.debug_mode:
                print(f"Error during export: {str(e)}")
            result = False

        finally:
            # Always restore original transforms
            if props.debug_mode:
                print("Restoring original transforms...")

            # Get fresh reference to empty
            empty = bpy.data.objects.get(empty_name)
            if empty and empty_world_matrix:
                # Restore using SHARED FUNCTION
                restore_empty_world_matrix(empty, empty_world_matrix, debug_mode=props.debug_mode)

            if props.debug_mode:
                print("--- Export with empty origin complete ---\n")

        return result

    def export_single_object_direct(self, context, props, obj, name, export_path):
        """Export a single object directly without additional transformations"""
        # Clear selection and select only this object
        bpy.ops.object.select_all(action='DESELECT')
        obj.select_set(True)
        context.view_layer.objects.active = obj

        # Apply transform options if needed
        if props.apply_transforms:
            bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)

        # Apply material overrides if needed
        if props.override_materials and props.override_material:
            self.apply_material_overrides([obj], props)

        # Set export filename
        filename = f"{name}.{props.export_format.lower()}"
        filepath = os.path.join(export_path, filename)

        # Export based on format
        return self.perform_export(props, filepath)

    def find_empties_with_children(self, collection):
        """Find all empty objects with mesh children in collection and sub-collections"""
        empties_with_children = {}

        def search_collection(coll):
            for obj in coll.objects:
                if obj.type == 'EMPTY':
                    # Find mesh children of this empty
                    children = [child for child in obj.children if child.type == 'MESH']
                    if children:
                        empties_with_children[obj] = children

            # Search sub-collections
            for sub_coll in coll.children:
                search_collection(sub_coll)

        search_collection(collection)
        return empties_with_children

    def get_orphaned_objects(self, collection, empties_with_children):
        """Get objects that are not children of any empty"""
        all_objects = self.get_collection_objects(collection)
        children_of_empties = set()

        # Collect all objects that are children of empties
        for children_list in empties_with_children.values():
            children_of_empties.update(children_list)

        # Return objects not in any empty's children
        return [obj for obj in all_objects if obj not in children_of_empties]

    def get_collection_objects(self, collection):
        """Get all objects from collection and sub-collections"""
        objects = []

        # Add objects directly in collection
        for obj in collection.objects:
            if obj.type == 'MESH':
                objects.append(obj)

        # Add objects from sub-collections
        for child_collection in collection.children:
            objects.extend(self.get_collection_objects(child_collection))

        return objects

    def export_objects_as_single(self, context, props, objects, collection_name, export_path):
        """Export multiple objects as single file"""
        # Clear selection
        bpy.ops.object.select_all(action='DESELECT')

        # Select all objects
        for obj in objects:
            obj.select_set(True)

        if objects:
            context.view_layer.objects.active = objects[0]

        # Store original transforms
        original_transforms = []
        for obj in objects:
            original_transforms.append({
                'name': obj.name,
                'location': obj.location.copy(),
                'rotation': obj.rotation_euler.copy(),
                'scale': obj.scale.copy()
            })

        try:
            # Apply transform options
            if props.export_at_origin:
                for obj in objects:
                    obj.location = (0, 0, 0)

            if props.apply_transforms:
                bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)

            # Apply material overrides if needed
            if props.override_materials and props.override_material:
                self.apply_material_overrides(objects, props)

            # Set export filename
            filename = f"{collection_name}.{props.export_format.lower()}"
            filepath = os.path.join(export_path, filename)

            # Export based on format
            result = self.perform_export(props, filepath)

        finally:
            # Restore original transforms if we moved to origin and didn't apply transforms
            if props.export_at_origin and not props.apply_transforms:
                for orig_transform in original_transforms:
                    obj = bpy.data.objects.get(orig_transform['name'])
                    if obj:
                        obj.location = orig_transform['location']
                        obj.rotation_euler = orig_transform['rotation']
                        obj.scale = orig_transform['scale']

        return result

    def export_single_object(self, context, props, obj, export_path):
        """Export single object"""
        # Clear selection and select only this object
        bpy.ops.object.select_all(action='DESELECT')
        obj.select_set(True)
        context.view_layer.objects.active = obj

        # Store original transform
        original_location = obj.location.copy()
        original_rotation = obj.rotation_euler.copy()
        original_scale = obj.scale.copy()

        try:
            # Apply transform options
            if props.export_at_origin:
                obj.location = (0, 0, 0)

            if props.apply_transforms:
                bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)

            # Apply material overrides if needed
            if props.override_materials and props.override_material:
                self.apply_material_overrides([obj], props)

            # Set export filename
            filename = f"{obj.name}.{props.export_format.lower()}"
            filepath = os.path.join(export_path, filename)

            # Export based on format
            result = self.perform_export(props, filepath)

        finally:
            # Restore original transform if we moved to origin and didn't apply transforms
            if props.export_at_origin and not props.apply_transforms:
                obj.location = original_location
                obj.rotation_euler = original_rotation
                obj.scale = original_scale

        return result

    def apply_material_overrides(self, objects, props):
        """Apply material overrides to objects"""
        for obj in objects:
            if obj.type == 'MESH':
                # Clear existing materials if override is enabled
                if props.override_materials:
                    obj.data.materials.clear()

                # Add override material or assign to objects without materials
                if props.override_material:
                    if len(obj.data.materials) == 0 or props.override_materials:
                        obj.data.materials.append(props.override_material)
                    elif props.assign_if_no_material and len(obj.data.materials) == 0:
                        obj.data.materials.append(props.override_material)

        # Handle M_ prefix
        if props.add_m_prefix:
            for mat in bpy.data.materials:
                if not mat.name.startswith("M_"):
                    mat.name = "M_" + mat.name

    def perform_export(self, props, filepath):
        """Perform the actual export based on format"""
        try:
            if props.export_format == 'FBX':
                if props.use_custom_fbx_ascii:
                    # Custom ASCII FBX export (experimental)
                    bpy.ops.export_scene.fbx(
                        filepath=filepath,
                        use_selection=True,
                        axis_forward=props.axis_forward,
                        axis_up=props.axis_up,
                        global_scale=1.0,
                        apply_unit_scale=True,
                        use_space_transform=True,
                        bake_space_transform=False,
                        use_mesh_modifiers=True,
                        use_mesh_modifiers_render=True,
                        mesh_smooth_type='OFF',
                        use_subsurf=False,
                        use_mesh_edges=False,
                        use_tspace=False,
                        use_custom_props=False,
                        add_leaf_bones=True,
                        primary_bone_axis='Y',
                        secondary_bone_axis='X',
                        use_armature_deform_only=False,
                        armature_nodetype='NULL',
                        bake_anim=True,
                        bake_anim_use_all_bones=True,
                        bake_anim_use_nla_strips=True,
                        bake_anim_use_all_actions=True,
                        bake_anim_force_startend_keying=True,
                        bake_anim_step=1.0,
                        bake_anim_simplify_factor=1.0,
                        path_mode='AUTO',
                        embed_textures=False,
                        batch_mode='OFF',
                        use_batch_own_dir=True,
                        use_metadata=True
                    )
                else:
                    bpy.ops.export_scene.fbx(
                        filepath=filepath,
                        use_selection=True,
                        axis_forward=props.axis_forward,
                        axis_up=props.axis_up
                    )

            elif props.export_format == 'OBJ':
                bpy.ops.wm.obj_export(
                    filepath=filepath,
                    export_selected_objects=True,
                    forward_axis=props.axis_forward,
                    up_axis=props.axis_up,
                    export_materials=True,
                    apply_modifiers=True
                )

            elif props.export_format == 'DAE':
                bpy.ops.wm.collada_export(
                    filepath=filepath,
                    selected=True,
                    apply_modifiers=True
                )

            elif props.export_format == 'GLTF':
                bpy.ops.export_scene.gltf(
                    filepath=filepath,
                    use_selection=True
                )

            return True

        except Exception as e:
            print(f"Export error: {str(e)}")
            return False

# Panels
class MASSEXPORTER_PT_main_panel(Panel):
    """Main Mass Exporter Panel"""
    bl_label = "Mass Exporter Fixed v6 - Synced Functions"
    bl_idname = "MASSEXPORTER_PT_main_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Mass Exporter"

    def draw(self, context):
        layout = self.layout
        props = context.scene.mass_exporter_props

        # Export button
        layout.operator("massexporter.export_all", text="Export All Collections", icon='EXPORT')

        # Test button
        layout.operator("massexporter.test_empty_centering", text="Test Empty Operations", icon='EMPTY_ARROWS')

        layout.separator()

        # Debug mode
        layout.prop(props, "debug_mode")

class MASSEXPORTER_PT_collections(Panel):
    """Collection Options Panel"""
    bl_label = "Collection Options"
    bl_idname = "MASSEXPORTER_PT_collections"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Mass Exporter"
    bl_parent_id = "MASSEXPORTER_PT_main_panel"

    def draw(self, context):
        layout = self.layout
        props = context.scene.mass_exporter_props

        # Collection list
        row = layout.row()
        row.template_list(
            "MASSEXPORTER_UL_collections", "",
            props, "collection_items",
            props, "active_collection_index"
        )

        # Add/Remove buttons
        col = row.column(align=True)
        col.operator("massexporter.add_collection", icon='ADD', text="")
        col.operator("massexporter.remove_collection", icon='REMOVE', text="")
        col.separator()
        col.operator("massexporter.refresh_collections", icon='FILE_REFRESH', text="")

        # Enhanced options for active collection
        if props.collection_items and len(props.collection_items) > props.active_collection_index:
            active_item = props.collection_items[props.active_collection_index]

            layout.separator()
            layout.label(text="Enhanced Export Options:")

            layout.prop(active_item, "export_subcollections_as_single")
            layout.prop(active_item, "use_empty_origins")

            if active_item.use_empty_origins:
                box = layout.box()
                box.label(text="Parent Empty Options:", icon='EMPTY_ARROWS')
                box.prop(active_item, "center_parent_empties")
                box.prop(active_item, "combine_empty_children")
                
                # Add note about shared functions
                note_box = box.box()
                note_box.label(text="✓ Test and Export use same functions", icon='INFO')
                note_box.label(text="✓ World space positioning guaranteed")

class MASSEXPORTER_PT_transform(Panel):
    """Transform Options Panel"""
    bl_label = "Transform Options"
    bl_idname = "MASSEXPORTER_PT_transform"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Mass Exporter"
    bl_parent_id = "MASSEXPORTER_PT_main_panel"

    def draw(self, context):
        layout = self.layout
        props = context.scene.mass_exporter_props

        layout.prop(props, "export_at_origin")
        layout.prop(props, "apply_transforms")

        layout.separator()
        layout.label(text="Transform Axis Settings:")

        row = layout.row()
        row.prop(props, "axis_forward", text="Forward")
        row.prop(props, "axis_up", text="Up")

class MASSEXPORTER_PT_materials(Panel):
    """Material Options Panel"""
    bl_label = "Material Options"
    bl_idname = "MASSEXPORTER_PT_materials"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Mass Exporter"
    bl_parent_id = "MASSEXPORTER_PT_main_panel"

    def draw(self, context):
        layout = self.layout
        props = context.scene.mass_exporter_props

        layout.prop(props, "override_materials")

        row = layout.row()
        row.enabled = props.override_materials
        row.prop(props, "override_material")

        layout.prop(props, "assign_if_no_material")
        layout.prop(props, "add_m_prefix")

class MASSEXPORTER_PT_export(Panel):
    """File Export Options Panel"""
    bl_label = "File Export Options"
    bl_idname = "MASSEXPORTER_PT_export"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Mass Exporter"
    bl_parent_id = "MASSEXPORTER_PT_main_panel"

    def draw(self, context):
        layout = self.layout
        props = context.scene.mass_exporter_props

        layout.prop(props, "export_format")

        # Show custom FBX option only when FBX is selected
        if props.export_format == 'FBX':
            layout.prop(props, "use_custom_fbx_ascii")

# Registration
classes = [
    CollectionExportItem,
    MassExporterProperties,
    MASSEXPORTER_UL_collections,
    MASSEXPORTER_OT_add_collection,
    MASSEXPORTER_OT_remove_collection,
    MASSEXPORTER_OT_select_folder,
    MASSEXPORTER_OT_refresh_collections,
    MASSEXPORTER_OT_test_empty_centering,
    MASSEXPORTER_OT_export_all,
    MASSEXPORTER_PT_main_panel,
    MASSEXPORTER_PT_collections,
    MASSEXPORTER_PT_transform,
    MASSEXPORTER_PT_materials,
    MASSEXPORTER_PT_export,
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
