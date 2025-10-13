bl_info = {
    "name": "Mass Collection Exporter",
    "author": "Claude AI", 
    "version": (5, 9, 0),
    "blender": (3, 0, 0),
    "location": "3D View > N-Panel > Mass Exporter",
    "description": "Export collections with auto-move empties to origin and join empty children features",
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

# STANDALONE FUNCTION - The core logic extracted so both button and export can use it
def move_empties_to_origin_core_logic(context, report_func=None):
    """Core logic for moving empties to origin - can be used by both button and export"""
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
        if report_func:
            report_func({'WARNING'}, "No collections enabled for export")
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
        if report_func:
            report_func({'WARNING'}, "No empties with children found in enabled collections")
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
        if report_func:
            report_func({'INFO'}, f"Moved {len(empties_moved)} empties from enabled collections to origin")
        print(f"\nSUCCESS: Moved {len(empties_moved)} empties from enabled collections to origin (0,0,0)")
        print("Use Ctrl+Z to undo if needed")
    
    return {'FINISHED'}

# NEW STANDALONE FUNCTION - Join empty children logic with improved matrix handling
def join_empty_children_core_logic(context, report_func=None, apply_modifiers=False):
    """Core logic for joining empty children - improved approach with proper matrix handling"""
    # Force OBJECT mode
    if bpy.ops.object.mode_set.poll():
        bpy.ops.object.mode_set(mode='OBJECT')
    
    props = context.scene.mass_exporter_props
    joined_empties = []
    
    # Get all enabled collections
    enabled_collections = []
    for item in props.collection_items:
        if item.export_enabled and item.collection:
            enabled_collections.append(item.collection)
    
    if not enabled_collections:
        if report_func:
            report_func({'WARNING'}, "No collections enabled for export")
        print("No collections enabled for export")
        return {'CANCELLED'}
    
    print(f"Joining children in {len(enabled_collections)} enabled collections:")
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
    all_empties_to_join = []
    for collection in enabled_collections:
        collection_empties = find_empties_in_collection(collection)
        all_empties_to_join.extend(collection_empties)
    
    # Remove duplicates (in case empty is in multiple collections)
    unique_empties = {}
    for empty, children in all_empties_to_join:
        if empty.name not in unique_empties:
            unique_empties[empty.name] = (empty, children)
    
    if not unique_empties:
        if report_func:
            report_func({'WARNING'}, "No empties with children found in enabled collections")
        print("No empties with children found in enabled collections")
        return {'CANCELLED'}
    
    print(f"\nFound {len(unique_empties)} empties with children to join:")
    
    # Store original selection and active object
    original_selection = context.selected_objects.copy()
    original_active = context.active_object
    
    try:
        # Process each empty using the improved approach
        for empty_name, (empty, children) in unique_empties.items():
            if len(children) < 2:
                print(f"Skipping {empty.name} - only {len(children)} child(ren)")
                continue
                
            print(f"\nProcessing {empty.name} with {len(children)} children:")
            print(f"  Empty location: {empty.location}")
            print(f"  Children: {[child.name for child in children]}")
            
            # Store empty location and original child positions
            empty_world_location = empty.location.copy()
            original_child_positions = {}
            
            # Store each child's world position before any operations
            for child in children:
                original_child_positions[child.name] = child.matrix_world.translation.copy()
                print(f"    {child.name}: world pos {child.matrix_world.translation}")
            
            # Clear selection
            bpy.ops.object.select_all(action='DESELECT')
            
            # STEP 1: Apply modifiers if requested
            if apply_modifiers:
                print("  Applying modifiers before joining...")
                for child in children:
                    # Ensure object is selected and active
                    bpy.ops.object.select_all(action='DESELECT')
                    child.select_set(True)
                    context.view_layer.objects.active = child
                    
                    # Apply all modifiers
                    for modifier in child.modifiers[:]:
                        try:
                            bpy.ops.object.modifier_apply(modifier=modifier.name)
                            print(f"    Applied modifier '{modifier.name}' to {child.name}")
                        except Exception as e:
                            print(f"    Failed to apply modifier '{modifier.name}' to {child.name}: {str(e)}")
            
            # STEP 2: Deparent all children while preserving world positions
            print("  Deparenting children from empty...")
            for child in children:
                if child.parent == empty:
                    # Store world matrix and apply transform to maintain position
                    world_matrix = child.matrix_world.copy()
                    child.parent = None
                    
                    # Apply the world transform directly
                    child.matrix_world = world_matrix
                    
                    print(f"    Deparented {child.name}, world pos: {child.matrix_world.translation}")
            
            # Force scene update after deparenting
            context.view_layer.update()
            
            # STEP 3: Select and join all children  
            print("  Joining children...")
            bpy.ops.object.select_all(action='DESELECT')
            
            for child in children:
                child.select_set(True)
            
            # Set first child as active
            context.view_layer.objects.active = children[0]
            
            # Store the first child's world position before join (for reference)
            first_child_world_pos = children[0].matrix_world.translation.copy()
            
            # Join objects
            bpy.ops.object.join()
            
            # Get the joined object
            joined_obj = context.active_object
            if joined_obj:
                joined_obj.name = f"{empty_name}_joined"
                print(f"  Successfully joined {len(children)} objects into '{joined_obj.name}'")
                print(f"  Joined object world pos after join: {joined_obj.matrix_world.translation}")
                
                # STEP 4: Set object origin to empty location using proper method
                print(f"  Setting origin to empty location: {empty_world_location}")
                
                # Store the current mesh world position
                current_mesh_world_pos = joined_obj.matrix_world.translation.copy()
                
                # Calculate the offset from current mesh position to empty position
                offset_to_empty = empty_world_location - current_mesh_world_pos
                
                # Move object so its position is at the empty location
                joined_obj.location = empty_world_location
                
                # Now set origin to object center, which is now at the empty location
                bpy.ops.object.origin_set(type='ORIGIN_GEOMETRY', center='BOUNDS')
                
                # Move the object back to restore mesh to original position
                joined_obj.location = current_mesh_world_pos
                
                print(f"  Final object location: {joined_obj.location}")
                print(f"  Final object world pos: {joined_obj.matrix_world.translation}")
                
                # Verify the origin is where we wanted it
                from mathutils import Vector
                final_origin_world = joined_obj.matrix_world @ Vector((0, 0, 0))
                origin_error = (final_origin_world - empty_world_location).length
                mesh_error = (joined_obj.matrix_world.translation - current_mesh_world_pos).length
                
                print(f"  Origin error: {origin_error:.6f} units")
                print(f"  Mesh position error: {mesh_error:.6f} units")
                
                joined_empties.append({
                    'empty': empty,
                    'joined_object': joined_obj,
                    'original_child_count': len(children)
                })
        
    except Exception as e:
        if report_func:
            report_func({'ERROR'}, f"Error during joining: {str(e)}")
        print(f"Error during joining: {str(e)}")
        return {'CANCELLED'}
    
    finally:
        # Restore selection
        bpy.ops.object.select_all(action='DESELECT')
        for obj in original_selection:
            if obj.name in bpy.data.objects:
                obj.select_set(True)
        if original_active and original_active.name in bpy.data.objects:
            context.view_layer.objects.active = original_active
    
    if joined_empties:
        if report_func:
            report_func({'INFO'}, f"Joined children for {len(joined_empties)} empties from enabled collections")
        print(f"\nSUCCESS: Joined children for {len(joined_empties)} empties")
        print("Use Ctrl+Z to undo if needed")
    
    return {'FINISHED'}

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
        description="Search for parent empties and use them as origins/centers",
        default=False
    )

    center_parent_empties: BoolProperty(
        name="Center Parent Empties",
        description="Move parent empty to (0,0,0), export, then restore position",
        default=True
    )

    move_empties_to_origin_on_export: BoolProperty(
        name="Move Empties to Origin on Export",
        description="Automatically run 'Move Empties to Origin' before export",
        default=False
    )

    join_empty_children: BoolProperty(
        name="Join Empty Children",
        description="Join all mesh children of empties into single objects before export",
        default=False
    )

    apply_modifiers_before_join: BoolProperty(
        name="Apply Modifiers Before Join",
        description="Apply all modifiers before joining empty children",
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
        """Move empties to origin - uses the standalone core logic function"""
        return move_empties_to_origin_core_logic(context, self.report)

class MASSEXPORTER_OT_join_empties(Operator):
    """Join children of empties - only those in enabled collections"""
    bl_idname = "massexporter.join_empties"
    bl_label = "Join Empties"
    bl_description = "Join all mesh children of empties into single objects - only from enabled collections"
    
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        """Join empty children - uses the standalone core logic function"""
        props = context.scene.mass_exporter_props
        
        # Check if any enabled collection has join_empty_children or apply_modifiers_before_join enabled
        apply_modifiers = False
        for item in props.collection_items:
            if item.export_enabled and item.collection and item.apply_modifiers_before_join:
                apply_modifiers = True
                break
        
        return join_empty_children_core_logic(context, self.report, apply_modifiers)

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
    """Export all enabled collections with auto-move empties to origin and join empty children"""
    bl_idname = "massexporter.export_all"
    bl_label = "Export All"
    bl_description = "Export all enabled collections with auto-move empties to origin and join empty children"

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

        # Check if any collection has join empty children enabled
        join_collections = []
        for item in props.collection_items:
            if item.export_enabled and item.collection and item.export_path and item.join_empty_children:
                join_collections.append(item)

        # STEP 1: Join empty children first (if enabled for any collection)
        if join_collections:
            if props.debug_mode:
                print(f"\n=== JOIN EMPTY CHILDREN ENABLED FOR {len(join_collections)} COLLECTIONS ===")
            
            # Check if modifiers should be applied
            apply_modifiers = False
            for item in join_collections:
                if item.apply_modifiers_before_join:
                    apply_modifiers = True
                    break
            
            # Use the standalone core logic function
            result = join_empty_children_core_logic(context, self.report, apply_modifiers)
            
            if result == {'CANCELLED'}:
                self.report({'WARNING'}, "Join empty children failed")
            else:
                if props.debug_mode:
                    print("Join empty children completed successfully")

        # Check if any collection has auto-move enabled
        auto_move_collections = []
        for item in props.collection_items:
            if item.export_enabled and item.collection and item.export_path and item.move_empties_to_origin_on_export:
                auto_move_collections.append(item)

        # STEP 2: Move empties to origin (if enabled for any collection) - AFTER joining
        if auto_move_collections:
            if props.debug_mode:
                print(f"\n=== AUTO-MOVE TO ORIGIN ENABLED FOR {len(auto_move_collections)} COLLECTIONS ===")
            
            # Use the standalone core logic function
            result = move_empties_to_origin_core_logic(context, self.report)
            
            if result == {'CANCELLED'}:
                self.report({'WARNING'}, "Auto-move empties to origin failed")
            else:
                if props.debug_mode:
                    print("Auto-move empties to origin completed successfully")

        try:
            # STEP 3: Export collections
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
        """Use empty origins for export centering"""
        collection = item.collection
        export_path = item.export_path
        success_count = 0

        if props.debug_mode:
            print(f"Exporting with empty origins for: {collection.name}")

        # Get all enabled collections (in this case, just this collection)
        enabled_collections = [collection]
        
        if props.debug_mode:
            print(f"Using enabled collections: {[coll.name for coll in enabled_collections]}")
        
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
        for coll in enabled_collections:
            collection_empties = find_empties_in_collection(coll)
            all_empties_to_move.extend(collection_empties)
        
        # Remove duplicates (in case empty is in multiple collections)
        unique_empties = {}
        for empty, children in all_empties_to_move:
            if empty.name not in unique_empties:
                unique_empties[empty.name] = (empty, children)
        
        if not unique_empties:
            if props.debug_mode:
                print("No empties with children found")
            # No empties, export normally
            objects = self.get_collection_objects(collection)
            if objects:
                if item.merge_to_single:
                    return self.export_objects_as_single(context, props, objects, collection.name, export_path)
                else:
                    success_count = 0
                    for obj in objects:
                        if self.export_single_object(context, props, obj, export_path):
                            success_count += 1
                    return success_count > 0
            return False
        
        if props.debug_mode:
            print(f"Found {len(unique_empties)} empties with children to process")

        # Process each empty
        for empty_name, (empty, children) in unique_empties.items():
            if props.debug_mode:
                print(f"\n--- PROCESSING EMPTY: {empty.name} with {len(children)} children ---")
                print(f"Empty starting at: {empty.location}")
                print(f"Children: {[child.name for child in children]}")

            if item.center_parent_empties:
                # Store original position
                original_empty_pos = empty.location.copy()
                
                try:
                    # Move to origin
                    empty.location = (0.0, 0.0, 0.0)
                    bpy.context.view_layer.update()
                    
                    if props.debug_mode:
                        print(f"Empty moved to: {empty.location}")
                        for child in children:
                            print(f"  {child.name} now at world: {child.matrix_world.translation}")

                    # Export the children
                    if item.join_empty_children:
                        # Export joined - but children should already be joined from earlier step
                        if self.export_children_combined(context, props, empty, children, export_path):
                            success_count += 1
                    else:
                        # Export individually
                        if self.export_children_individual(context, props, empty, children, export_path):
                            success_count += 1

                finally:
                    # Restore position
                    empty.location = original_empty_pos
                    bpy.context.view_layer.update()
                    
                    if props.debug_mode:
                        print(f"Empty restored to: {empty.location}")
            else:
                # Export without centering
                if item.join_empty_children:
                    if self.export_children_combined(context, props, empty, children, export_path):
                        success_count += 1
                else:
                    if self.export_children_individual(context, props, empty, children, export_path):
                        success_count += 1

        return success_count > 0

    def export_children_combined(self, context, props, empty, children, export_path):
        """Export children combined - NOTE: children should already be joined from earlier step"""
        if not children:
            return False

        empty_name = empty.name
        
        if props.debug_mode:
            print(f"Exporting combined children of {empty_name}")

        # Look for already joined object
        joined_obj_name = f"{empty_name}_joined"
        joined_obj = bpy.data.objects.get(joined_obj_name)
        
        if joined_obj:
            # Use the already joined object
            if props.debug_mode:
                print(f"Found already joined object: {joined_obj.name}")
            return self.export_single_object_simple(context, props, joined_obj, empty_name, export_path)
        else:
            # Fall back to old combining logic if not already joined
            if props.debug_mode:
                print(f"No joined object found, falling back to live combine")
            
            # Store original selection
            original_selection = context.selected_objects.copy()
            original_active = context.active_object

            try:
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
                    print(f"Error in export_children_combined: {str(e)}")
                return False

            finally:
                # Restore selection
                bpy.ops.object.select_all(action='DESELECT')
                for obj in original_selection:
                    if obj.name in bpy.data.objects:
                        obj.select_set(True)
                if original_active and original_active.name in bpy.data.objects:
                    context.view_layer.objects.active = original_active

    def export_children_individual(self, context, props, empty, children, export_path):
        """Export children individually"""
        if not children:
            return False

        empty_name = empty.name
        success_count = 0
        
        if props.debug_mode:
            print(f"Exporting children of {empty_name} individually")

        # Export each child individually
        for i, child in enumerate(children):
            if props.debug_mode:
                print(f"Exporting {child.name} at world position: {child.matrix_world.translation}")

            # Export this child
            child_name = f"{empty_name}_{child.name}" if len(children) > 1 else empty_name
            if self.export_single_object_simple(context, props, child, child_name, export_path):
                success_count += 1

        return success_count > 0

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
    bl_label = "Mass Collection Exporter"
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

        # Enhanced controls section
        controls_box = layout.box()
        controls_box.label(text="Debug Controls:", icon='SETTINGS')
        
        # Move empties button
        row = controls_box.row()
        row.scale_y = 1.2
        row.operator("massexporter.move_empties_to_origin", text="Move Empties to Origin", icon='OUTLINER_OB_EMPTY')
        
        # Join empties button
        row = controls_box.row()
        row.scale_y = 1.2
        row.operator("massexporter.join_empties", text="Join Empties", icon='MOD_SOLIDIFY')
        
        controls_box.label(text="Preview operations on enabled collections")

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
                
                # Join empty children section
                join_box = box.box()
                join_box.label(text="Join Empty Children:", icon='MOD_SOLIDIFY')
                join_box.prop(active_item, "join_empty_children")
                
                if active_item.join_empty_children:
                    mod_box = join_box.box()
                    mod_box.prop(active_item, "apply_modifiers_before_join")
                    mod_box.label(text="Origin will be at empty position")
                
                # Auto move feature
                auto_box = box.box()
                auto_box.label(text="Auto Move to Origin:", icon='OUTLINER_OB_EMPTY')
                auto_box.prop(active_item, "move_empties_to_origin_on_export")
                
                if active_item.move_empties_to_origin_on_export:
                    info_box = auto_box.box()
                    info_box.label(text="Will automatically move empties to origin")
                    info_box.label(text="AFTER joining (if enabled)")

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
    MASSEXPORTER_OT_join_empties,
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
