bl_info = {
    "name": "Mass Collection Exporter - SIMPLE CENTERING",
    "author": "Claude AI", 
    "version": (5, 4, 0),
    "blender": (3, 0, 0),
    "location": "3D View > N-Panel > Mass Exporter",
    "description": "Export collections with SIMPLE working empty centering - move to origin, export, restore",
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
        description="Search for parent empties and use them as origins/centers. Will center empties for export",
        default=False
    )

    center_parent_empties: BoolProperty(
        name="Center Parent Empties",
        description="SIMPLE: Move parent empty to (0,0,0), export, then restore position",
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
class MASSEXPORTER_OT_move_empties_to_origin(Operator):
    """Move empties with children to origin - only those in enabled collections"""
    bl_idname = "massexporter.move_empties_to_origin"
    bl_label = "Move Empties to Origin"
    bl_description = "Move empties with mesh children to origin (0,0,0) - only from enabled collections"
    
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        """Move empties to origin - only those in enabled collections"""
        # Force OBJECT mode
        if bpy.ops.object.mode_set.poll():
            bpy.ops.object.mode_set(mode='OBJECT')
        
        props = context.scene.mass_exporter_props
        empties_moved = []
        
        # Get all enabled collections
        enabled_collections = []
        for item in props.collection_items:
            if item.export_enabled and item.collection:
                enabled_collections.append(item.collection)
        
        if not enabled_collections:
            self.report({'WARNING'}, "No collections enabled for export")
            print("No collections enabled for export")
            return {'CANCELLED'}
        
        print(f"Checking empties in {len(enabled_collections)} enabled collections:")
        for coll in enabled_collections:
            print(f"  - {coll.name}")
        
        # Find empties with children in enabled collections
        def find_empties_in_collection(collection):
            """Recursively find empties with children in collection and sub-collections"""
            empties_found = []
            
            # Check objects directly in collection
            for obj in collection.objects:
                if obj.type == 'EMPTY':
                    children = [child for child in obj.children if child.type == 'MESH']
                    if children:
                        empties_found.append((obj, children))
            
            # Check sub-collections
            for sub_coll in collection.children:
                empties_found.extend(find_empties_in_collection(sub_coll))
            
            return empties_found
        
        # Collect all empties from enabled collections
        all_empties_to_move = []
        for collection in enabled_collections:
            collection_empties = find_empties_in_collection(collection)
            all_empties_to_move.extend(collection_empties)
        
        # Remove duplicates (in case empty is in multiple collections)
        unique_empties = {}
        for empty, children in all_empties_to_move:
            if empty.name not in unique_empties:
                unique_empties[empty.name] = (empty, children)
        
        if not unique_empties:
            self.report({'WARNING'}, "No empties with children found in enabled collections")
            print("No empties with children found in enabled collections")
            return {'CANCELLED'}
        
        print(f"\nFound {len(unique_empties)} empties to move:")
        
        # Move each empty to origin
        for empty_name, (empty, children) in unique_empties.items():
            print(f"Moving {empty.name} from {empty.location} to origin")
            print(f"  Children: {[child.name for child in children]}")
            print(f"  In collections: {[coll.name for coll in bpy.data.collections if empty.name in coll.objects]}")
            
            # Store original location (for undo)
            original_location = empty.location.copy()
            
            # Move to origin
            empty.location = (0.0, 0.0, 0.0)
            
            # Update scene
            bpy.context.view_layer.update()
            
            empties_moved.append({
                'object': empty,
                'original_location': original_location
            })
            
            print(f"  {empty.name} moved to {empty.location}")
            
            # Show where children ended up
            for child in children:
                world_pos = child.matrix_world.translation
                print(f"    {child.name} now at: {world_pos}")
        
        if empties_moved:
            self.report({'INFO'}, f"Moved {len(empties_moved)} empties from enabled collections to origin")
            print(f"\nSUCCESS: Moved {len(empties_moved)} empties from enabled collections to origin (0,0,0)")
            print("Use Ctrl+Z to undo if needed")
        
        return {'FINISHED'}

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
        
        # Store original empty positions BEFORE any export operations
        original_empty_positions = {}
        if props.debug_mode:
            print("\n=== EXPORT STARTED - STORING ORIGINAL POSITIONS ===")
        
        for obj in bpy.context.scene.objects:
            if obj.type == 'EMPTY':
                children = [child for child in obj.children if child.type == 'MESH']
                if children:
                    original_empty_positions[obj.name] = obj.location.copy()
                    if props.debug_mode:
                        print(f"Stored original position for {obj.name}: {obj.location}")

        try:
            for item in props.collection_items:
                if item.export_enabled and item.collection and item.export_path:
                    if self.export_collection(context, props, item):
                        exported_count += 1
        except Exception as e:
            self.report({'ERROR'}, f"Export failed: {str(e)}")
            return {'CANCELLED'}
        finally:
            # Restore ALL empty positions at the very end
            if props.debug_mode:
                print("\n=== EXPORT FINISHED - RESTORING ALL POSITIONS ===")
            
            for empty_name, original_location in original_empty_positions.items():
                if empty_name in bpy.data.objects:
                    empty = bpy.data.objects[empty_name]
                    if props.debug_mode:
                        print(f"Restoring {empty_name} from {empty.location} to {original_location}")
                    empty.location = original_location
            
            # Update scene after all restorations
            bpy.context.view_layer.update()
            
            # Restore original selection
            bpy.ops.object.select_all(action='DESELECT')
            for obj in original_selection:
                if obj.name in bpy.data.objects:  # Check if object still exists
                    obj.select_set(True)
            if original_active and original_active.name in bpy.data.objects:
                context.view_layer.objects.active = original_active
            
            if props.debug_mode:
                print("=== ALL POSITIONS RESTORED ===")

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
            return self.export_with_empty_origins_simple(context, props, item)
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

    def export_with_empty_origins_simple(self, context, props, item):
        """SIMPLE: Export using empty objects as origins - move to origin, export, restore"""
        collection = item.collection
        export_path = item.export_path
        success_count = 0

        if props.debug_mode:
            print(f"SIMPLE: Exporting with empty origins for: {collection.name}")

        # Find all empties in collection and sub-collections
        empties_with_children = self.find_empties_with_children(collection)

        if empties_with_children:
            if props.debug_mode:
                print(f"Found {len(empties_with_children)} empties with children")

            # Export each empty group with SIMPLE centering
            for empty, children in empties_with_children.items():
                if props.debug_mode:
                    print(f"\n--- EXPORTING GROUP: {empty.name} with {len(children)} children ---")

                if item.center_parent_empties:
                    # SIMPLE METHOD: Move empty to origin, export, restore
                    if item.combine_empty_children:
                        if self.export_empty_group_combined_simple(context, props, empty, children, export_path):
                            success_count += 1
                    else:
                        if self.export_empty_group_individual_simple(context, props, empty, children, export_path):
                            success_count += 1
                else:
                    # Export without centering
                    if item.combine_empty_children:
                        if self.export_combined_empty_children_original(context, props, children, empty, export_path):
                            success_count += 1
                    else:
                        for child in children:
                            if self.export_single_object(context, props, child, export_path):
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

    def export_empty_group_combined_simple(self, context, props, empty, children, export_path):
        """SIMPLE: Move empty to origin, combine and export children, restore empty position"""
        if not children:
            return False

        empty_name = empty.name
        
        if props.debug_mode:
            print(f"SIMPLE: Combining group {empty_name}")
            print(f"Empty starting at: {empty.location}")
            print(f"Children: {[child.name for child in children]}")

        # Store original empty position
        original_empty_pos = empty.location.copy()

        # Store original selection
        original_selection = context.selected_objects.copy()
        original_active = context.active_object

        try:
            # STEP 1: Move empty to origin (0,0,0) - SIMPLE!
            empty.location = (0.0, 0.0, 0.0)
            bpy.context.view_layer.update()
            
            if props.debug_mode:
                print(f"Empty moved to: {empty.location}")
                for child in children:
                    print(f"  {child.name} now at world: {child.matrix_world.translation}")

            # STEP 2: Combine and export
            if len(children) > 1:
                # Clear selection and select all children
                bpy.ops.object.select_all(action='DESELECT')
                for child in children:
                    child.select_set(True)
                context.view_layer.objects.active = children[0]

                # Join objects
                bpy.ops.object.join()
                combined_obj = context.active_object
                combined_obj.name = f"{empty_name}_combined"

                if props.debug_mode:
                    print(f"Combined object world position: {combined_obj.matrix_world.translation}")

                # Export the combined object
                result = self.export_single_object_simple(context, props, combined_obj, f"{empty_name}_combined", export_path)

                # Undo join to restore individual objects
                bpy.ops.ed.undo()
            else:
                # Single child - just export it
                child = children[0]
                result = self.export_single_object_simple(context, props, child, empty_name, export_path)

            return result

        except Exception as e:
            if props.debug_mode:
                print(f"Error in export_empty_group_combined_simple: {str(e)}")
            return False

        finally:
            # STEP 3: Restore empty position - SIMPLE!
            empty.location = original_empty_pos
            bpy.context.view_layer.update()
            
            if props.debug_mode:
                print(f"Empty restored to: {empty.location}")

            # Restore selection
            bpy.ops.object.select_all(action='DESELECT')
            for obj in original_selection:
                if obj.name in bpy.data.objects:
                    obj.select_set(True)
            if original_active and original_active.name in bpy.data.objects:
                context.view_layer.objects.active = original_active

    def export_empty_group_individual_simple(self, context, props, empty, children, export_path):
        """SIMPLE: Move empty to origin, export children individually, restore empty position"""
        if not children:
            return False

        empty_name = empty.name
        success_count = 0
        
        if props.debug_mode:
            print(f"SIMPLE: Exporting group {empty_name} individually")

        # Store original empty position
        original_empty_pos = empty.location.copy()

        try:
            # STEP 1: Move empty to origin (0,0,0) - SIMPLE!
            empty.location = (0.0, 0.0, 0.0)
            bpy.context.view_layer.update()
            
            if props.debug_mode:
                print(f"Empty moved to: {empty.location}")

            # STEP 2: Export each child individually
            for i, child in enumerate(children):
                if props.debug_mode:
                    print(f"Exporting {child.name} at world position: {child.matrix_world.translation}")

                # Export this child
                child_name = f"{empty_name}_{child.name}" if len(children) > 1 else empty_name
                if self.export_single_object_simple(context, props, child, child_name, export_path):
                    success_count += 1

            return success_count > 0

        except Exception as e:
            if props.debug_mode:
                print(f"Error in export_empty_group_individual_simple: {str(e)}")
            return False

        finally:
            # STEP 3: Restore empty position - SIMPLE!
            empty.location = original_empty_pos
            bpy.context.view_layer.update()
            
            if props.debug_mode:
                print(f"Empty restored to: {empty.location}")

    def export_single_object_simple(self, context, props, obj, name, export_path):
        """Simple export of a single object without additional transform modifications"""
        if props.debug_mode:
            print(f"Simple export: {obj.name} as {name}")
            print(f"  Object world position: {obj.matrix_world.translation}")

        # Store original selection
        original_selection = context.selected_objects.copy()
        original_active = context.active_object

        try:
            # Clear selection and select only this object
            bpy.ops.object.select_all(action='DESELECT')
            obj.select_set(True)
            context.view_layer.objects.active = obj

            # Apply material overrides if needed
            if props.override_materials and props.override_material:
                self.apply_material_overrides([obj], props)

            # Set export filename
            filename = f"{name}.{props.export_format.lower()}"
            filepath = os.path.join(export_path, filename)

            if props.debug_mode:
                print(f"Exporting to: {filepath}")

            # Export based on format
            result = self.perform_export(props, filepath)

            if props.debug_mode:
                print(f"Export result: {result}")

            return result

        finally:
            # Restore selection
            bpy.ops.object.select_all(action='DESELECT')
            for original_obj in original_selection:
                if original_obj.name in bpy.data.objects:
                    original_obj.select_set(True)
            if original_active and original_active.name in bpy.data.objects:
                context.view_layer.objects.active = original_active

    def export_combined_empty_children_original(self, context, props, children, empty, export_path):
        """Original method for combining children without centering"""
        if not children:
            return False

        empty_name = empty.name
        
        # Store original selection
        original_selection = context.selected_objects.copy()
        original_active = context.active_object

        try:
            if len(children) > 1:
                # Clear selection
                bpy.ops.object.select_all(action='DESELECT')

                # Select all children
                for child in children:
                    child.select_set(True)

                # Set active object
                context.view_layer.objects.active = children[0]

                # Join the objects
                bpy.ops.object.join()
                combined_obj = context.active_object
                combined_obj.name = f"{empty_name}_combined"

                # Export the combined object
                result = self.export_single_object_simple(context, props, combined_obj, f"{empty_name}_combined", export_path)

                # Undo the join operation
                bpy.ops.ed.undo()
            else:
                # Only one child
                child = children[0]
                result = self.export_single_object_simple(context, props, child, empty_name, export_path)

            return result

        except Exception as e:
            if props.debug_mode:
                print(f"Error in export_combined_empty_children_original: {str(e)}")
            return False

        finally:
            # Restore original selection
            bpy.ops.object.select_all(action='DESELECT')
            for obj in original_selection:
                if obj.name in bpy.data.objects:
                    obj.select_set(True)
            if original_active and original_active.name in bpy.data.objects:
                context.view_layer.objects.active = original_active

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
    bl_label = "Mass Exporter - SIMPLE CENTERING"
    bl_idname = "MASSEXPORTER_PT_main_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Mass Exporter"

    def draw(self, context):
        layout = self.layout
        props = context.scene.mass_exporter_props

        # Export button
        layout.operator("massexporter.export_all", text="Export All Collections", icon='EXPORT')

        layout.separator()

        # Main centering controls section
        centering_box = layout.box()
        centering_box.label(text="Empty Centering Controls:", icon='EMPTY_ARROWS')
        
        # WORKING button - highlighted and prominent
        row = centering_box.row()
        row.scale_y = 2.0
        row.operator("massexporter.move_empties_to_origin", text="MOVE EMPTIES TO ORIGIN", icon='OUTLINER_OB_EMPTY')
        
        # Info text
        centering_box.label(text="→ Moves empties from ENABLED collections to (0,0,0)", icon='INFO')
        centering_box.label(text="Only affects empties in collections with checkmark", icon='CHECKMARK')
        
        # Status info
        status_box = layout.box()
        status_box.label(text="SIMPLE: Move to origin → Export → Restore", icon='CHECKMARK')
        status_box.label(text="No complex calculations, just simple positioning!", icon='PIVOT_INDIVIDUAL')

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
                
                # Add note about SIMPLE centering
                note_box = box.box()
                note_box.label(text="SIMPLE: Move to (0,0,0) → Export → Restore", icon='CHECKMARK')
                note_box.label(text="No complex calculations needed!", icon='PIVOT_INDIVIDUAL')

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
    MASSEXPORTER_OT_move_empties_to_origin,
    MASSEXPORTER_OT_add_collection,
    MASSEXPORTER_OT_remove_collection,
    MASSEXPORTER_OT_select_folder,
    MASSEXPORTER_OT_refresh_collections,
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
