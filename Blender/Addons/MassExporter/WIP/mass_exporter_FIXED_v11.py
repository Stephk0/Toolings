bl_info = {
    "name": "Mass Collection Exporter",
    "author": "Claude AI", 
    "version": (11, 0, 0),  # FIXED VERSION - Robust list checking for new objects
    "blender": (3, 0, 0),
    "location": "3D View > N-Panel > Mass Exporter",
    "description": "Export collections with on-demand join during export - joins ALL empties together",
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

# FIXED: Join ALL empties from ALL enabled collections
def join_empty_children_core_logic(context, report_func=None, apply_modifiers=False, keep_joined_copy=True):
    """Core logic for joining empty children - creates duplicates and joins those instead of originals
    FIXED: Processes ALL empties from ALL enabled collections"""
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
                if children:  # FIXED: Include empties with ANY number of children (even 1)
                    empties_found.append((obj, children, collection))
        
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
    for empty, children, collection in all_empties_to_join:
        if empty.name not in unique_empties:
            unique_empties[empty.name] = (empty, children, collection)
    
    if not unique_empties:
        if report_func:
            report_func({'WARNING'}, "No empties with children found in enabled collections")
        print("No empties with children found in enabled collections")
        return {'CANCELLED'}
    
    print(f"\nFound {len(unique_empties)} empties with children to join:")
    
    # Store original selection and active object
    original_selection = context.selected_objects.copy()
    original_active = context.active_object
    
    # FIXED: Process ALL empties without early returns
    processed_count = 0
    try:
        # Process each empty using the COPY-BASED approach
        for empty_name, (empty, children, parent_collection) in unique_empties.items():
            # FIXED: Process even single children (removed the skip condition)
            print(f"\nProcessing {empty.name} with {len(children)} child(ren):")
            print(f"  Empty location: {empty.location}")
            print(f"  Parent collection: {parent_collection.name}")
            print(f"  Children: {[child.name for child in children]}")
            
            try:
                # Store empty location
                empty_world_location = empty.location.copy()
                
                # Clear selection
                bpy.ops.object.select_all(action='DESELECT')
                
                # STEP 1: Duplicate all children
                print("  Duplicating children...")
                duplicates = []
                for child in children:
                    child.select_set(True)
                
                # FIXED: Check if we have any children before accessing
                if not children:
                    print("  No children to duplicate, skipping...")
                    continue
                    
                context.view_layer.objects.active = children[0]
                
                # Duplicate selected objects
                bpy.ops.object.duplicate(linked=False)
                
                # Get the duplicates
                duplicates = context.selected_objects.copy()
                print(f"  Created {len(duplicates)} duplicates")
                
                # FIXED: Validate duplicates exist
                if not duplicates:
                    print("  No duplicates created, skipping...")
                    continue
                
                # STEP 2: Apply modifiers to duplicates if requested
                if apply_modifiers:
                    print("  Applying modifiers to duplicates...")
                    for dup in duplicates:
                        bpy.ops.object.select_all(action='DESELECT')
                        dup.select_set(True)
                        context.view_layer.objects.active = dup
                        
                        for modifier in dup.modifiers[:]:
                            try:
                                bpy.ops.object.modifier_apply(modifier=modifier.name)
                                print(f"    Applied modifier '{modifier.name}' to {dup.name}")
                            except Exception as e:
                                print(f"    Failed to apply modifier '{modifier.name}' to {dup.name}: {str(e)}")
                
                # STEP 3: Deparent duplicates (they inherit parent from originals)
                print("  Deparenting duplicates...")
                for dup in duplicates:
                    if dup.parent:
                        world_matrix = dup.matrix_world.copy()
                        dup.parent = None
                        dup.matrix_world = world_matrix
                
                context.view_layer.update()
                
                # STEP 4: Join duplicates (if more than one)
                if len(duplicates) > 1:
                    print("  Joining duplicates...")
                    bpy.ops.object.select_all(action='DESELECT')
                    
                    for dup in duplicates:
                        dup.select_set(True)
                    
                    context.view_layer.objects.active = duplicates[0]
                    
                    # Join objects
                    bpy.ops.object.join()
                    joined_obj = context.active_object
                else:
                    # Only one child, no need to join
                    print("  Only one duplicate, no join needed")
                    joined_obj = duplicates[0]
                
                # Get the joined object
                if joined_obj:
                    # Generate a unique name based on collection/empty name
                    base_name = parent_collection.name
                    desired_name = f"{base_name}_joined"
                    
                    # Handle naming conflicts
                    final_name = desired_name
                    counter = 1
                    while final_name in bpy.data.objects:
                        final_name = f"{desired_name}_{counter}"
                        counter += 1
                    
                    joined_obj.name = final_name
                    print(f"  Successfully created '{joined_obj.name}'")
                    print(f"  Joined object world pos: {joined_obj.matrix_world.translation}")
                    
                    # STEP 5: Set object origin to empty location using 3D cursor
                    print(f"  Setting origin to empty location: {empty_world_location}")
                    
                    # Store original cursor location
                    original_cursor_location = context.scene.cursor.location.copy()
                    
                    # Set 3D cursor to empty's world location
                    context.scene.cursor.location = empty_world_location
                    
                    # Set origin to 3D cursor
                    bpy.ops.object.origin_set(type='ORIGIN_CURSOR')
                    
                    # Restore cursor to original location
                    context.scene.cursor.location = original_cursor_location
                    
                    print(f"  Final object location: {joined_obj.location}")
                    print(f"  Final object world pos: {joined_obj.matrix_world.translation}")
                    
                    # Verify the origin
                    from mathutils import Vector
                    final_origin_world = joined_obj.matrix_world @ Vector((0, 0, 0))
                    origin_error = (final_origin_world - empty_world_location).length
                    print(f"  Origin error: {origin_error:.6f} units")
                    
                    # STEP 6: Add to same collection as parent
                    if parent_collection:
                        parent_collection.objects.link(joined_obj)
                        print(f"  Added '{joined_obj.name}' to collection '{parent_collection.name}'")
                    
                    # STEP 7: If not keeping the copy, hide it or mark for deletion
                    if not keep_joined_copy:
                        joined_obj.hide_set(True)
                        joined_obj.hide_viewport = True
                        print(f"  Marked '{joined_obj.name}' for cleanup (hidden)")
                    
                    joined_empties.append({
                        'empty': empty,
                        'joined_object': joined_obj,
                        'original_child_count': len(children),
                        'parent_collection': parent_collection
                    })
                    
                    processed_count += 1
                    print(f"  ✓ Successfully processed empty {processed_count}/{len(unique_empties)}")
            
            except Exception as e:
                print(f"  ✗ Error processing {empty.name}: {str(e)}")
                # Continue to next empty instead of stopping
                continue
        
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
            if keep_joined_copy:
                report_func({'INFO'}, f"Created joined copies for {len(joined_empties)} empties from enabled collections")
            else:
                report_func({'INFO'}, f"Created temporary joined copies for {len(joined_empties)} empties")
        print(f"\n✓ SUCCESS: Processed {processed_count}/{len(unique_empties)} empties")
        if keep_joined_copy:
            print("Joined copies are kept in the scene")
        else:
            print("Joined copies are marked for export cleanup")
    
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
        description="Join all mesh children of ALL empties into ONE object during export (on-demand)",
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
        default='-Z'
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
        default='Y'
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

    # FBX Scale and Transform Options
    apply_scaling: EnumProperty(
        name="Apply Scaling",
        description="How to apply scaling to exported FBX (affects scale in Unity)",
        items=[
            ('FBX_SCALE_NONE', 'None', 'Do not apply any scaling'),
            ('FBX_SCALE_UNITS', 'FBX Units Scale', 'Apply unit scaling (recommended for Unity)'),
            ('FBX_SCALE_CUSTOM', 'FBX Custom Scale', 'Apply custom scale'),
            ('FBX_SCALE_ALL', 'FBX All', 'Apply all scaling'),
        ],
        default='FBX_SCALE_UNITS'
    )

    bake_space_transform: BoolProperty(
        name="Apply Transform",
        description="Bake space transform into object data, avoiding object transforms in Unity",
        default=True
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
    bl_description = "Create joined copies of all mesh children of empties - only from enabled collections"
    
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        """Join empty children - uses the copy-based core logic function and KEEPS the copies"""
        props = context.scene.mass_exporter_props
        
        # Check if any enabled collection has apply_modifiers_before_join enabled
        apply_modifiers = False
        for item in props.collection_items:
            if item.export_enabled and item.collection and item.apply_modifiers_before_join:
                apply_modifiers = True
                break
        
        # KEEP the joined copies for debug button (keep_joined_copy=True)
        return join_empty_children_core_logic(context, self.report, apply_modifiers, keep_joined_copy=True)

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
    """Export all enabled collections - join happens on-demand during export"""
    bl_idname = "massexporter.export_all"
    bl_label = "Export All"
    bl_description = "Export all enabled collections - join happens on-demand during each export"

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

        # Check if any collection has auto-move enabled
        auto_move_collections = []
        for item in props.collection_items:
            if item.export_enabled and item.collection and item.export_path and item.move_empties_to_origin_on_export:
                auto_move_collections.append(item)

        # Move empties to origin (if enabled for any collection)
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
            # Export collections (join happens on-demand)
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
            # FIXED: Use new join logic if join_empty_children is enabled
            if item.use_empty_origins and item.join_empty_children:
                # Join all empties in this sub-collection and export as one
                if self.export_collection_with_all_empties_joined(context, props, item, sub_collection, export_path):
                    success_count += 1
            else:
                sub_objects = self.get_collection_objects(sub_collection)
                if sub_objects:
                    if self.export_objects_as_single(context, props, sub_objects, sub_collection.name, export_path):
                        success_count += 1

        return success_count > 0

    def export_with_empty_origins(self, context, props, item):
        """Use empty origins for export centering
        FIXED: If join_empty_children is enabled, joins ALL empties together into ONE export"""
        collection = item.collection
        export_path = item.export_path

        if props.debug_mode:
            print(f"Exporting with empty origins for: {collection.name}")

        # FIXED: If join is enabled, export the entire collection as ONE joined file
        if item.join_empty_children:
            return self.export_collection_with_all_empties_joined(context, props, item, collection, export_path)
        
        # Original behavior: export each empty separately (without join)
        return self.export_with_empty_origins_individual(context, props, item)

    def export_with_empty_origins_individual(self, context, props, item):
        """Export each empty's children individually (original behavior without join)"""
        collection = item.collection
        export_path = item.export_path
        success_count = 0

        # Find empties with children in this collection
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
        
        # Collect all empties
        all_empties = find_empties_in_collection(collection)
        
        # Remove duplicates
        unique_empties = {}
        for empty, children in all_empties:
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
            print(f"Found {len(unique_empties)} empties to process individually")

        # Process each empty
        for empty_name, (empty, children) in unique_empties.items():
            if props.debug_mode:
                print(f"\n--- PROCESSING EMPTY: {empty.name} ---")

            if item.center_parent_empties:
                original_empty_pos = empty.location.copy()
                
                try:
                    empty.location = (0.0, 0.0, 0.0)
                    bpy.context.view_layer.update()

                    # Export children individually
                    if self.export_children_individual(context, props, empty, children, export_path):
                        success_count += 1

                finally:
                    empty.location = original_empty_pos
                    bpy.context.view_layer.update()
            else:
                if self.export_children_individual(context, props, empty, children, export_path):
                    success_count += 1

        return success_count > 0

    def export_collection_with_all_empties_joined(self, context, props, item, collection, export_path):
        """
        ========== FIXED v11: Robust list checking for new objects ==========
        Collects ALL children from ALL empties in the collection, joins them together,
        and exports as ONE file named after the collection.
        CRITICAL FIXES:
        - Update view layer before accessing collections
        - Check if lists are empty before accessing elements
        - Validate all objects exist in view layer
        - Refresh collection state to get latest meshes
        """
        if props.debug_mode:
            print(f"\n=== JOINING ALL EMPTIES IN COLLECTION: {collection.name} ===")
        
        # FIXED: Update view layer to ensure we see latest objects
        context.view_layer.update()
        
        # Find all empties with children in this collection
        def find_empties_in_collection(coll):
            """Recursively find empties with children - REFRESHES to get latest"""
            empties_found = []
            
            # FIXED: Iterate directly on collection objects (refreshed)
            for obj in coll.objects:
                # FIXED: Validate object exists in view layer
                if obj.name not in context.view_layer.objects:
                    continue
                    
                if obj.type == 'EMPTY':
                    # FIXED: Get fresh children list each time
                    children = [child for child in obj.children 
                               if child.type == 'MESH' and child.name in context.view_layer.objects]
                    if children:
                        empties_found.append((obj, children))
            
            # Check sub-collections
            for sub_coll in coll.children:
                empties_found.extend(find_empties_in_collection(sub_coll))
            
            return empties_found
        
        all_empties = find_empties_in_collection(collection)
        
        # FIXED: Validate we found empties
        if not all_empties:
            if props.debug_mode:
                print("No empties with children found in collection")
            return False
        
        # Collect ALL children from ALL empties
        all_children = []
        empties_list = []
        for empty, children in all_empties:
            empties_list.append(empty)
            all_children.extend(children)
        
        # FIXED: Validate we have children
        if not all_children:
            if props.debug_mode:
                print("No children found in empties")
            return False
        
        if props.debug_mode:
            print(f"Found {len(empties_list)} empties with total {len(all_children)} children:")
            for empty, children in all_empties:
                print(f"  - {empty.name}: {len(children)} children")
        
        # FIXED: Validate we have at least one empty before accessing
        if not empties_list:
            if props.debug_mode:
                print("No empties in list")
            return False
            
        # Use the first empty's location as the origin point
        reference_empty = empties_list[0]
        empty_world_loc = reference_empty.location.copy()
        
        original_selection = context.selected_objects.copy()
        original_active = context.active_object
        joined_obj = None
        
        try:
            # STEP 1: Duplicate ALL children from ALL empties
            if props.debug_mode:
                print(f"Duplicating all {len(all_children)} children...")
            
            # FIXED: Clear selection first
            bpy.ops.object.select_all(action='DESELECT')
            
            # FIXED: Select all children that exist in view layer
            valid_children = []
            for child in all_children:
                if child.name in context.view_layer.objects:
                    child.select_set(True)
                    valid_children.append(child)
            
            # FIXED: Validate we have valid children to duplicate
            if not valid_children:
                if props.debug_mode:
                    print("No valid children to duplicate")
                return False
            
            # FIXED: Set active object with validation
            if len(valid_children) > 0:
                context.view_layer.objects.active = valid_children[0]
            else:
                if props.debug_mode:
                    print("No valid children to set as active")
                return False
            
            # Duplicate selected objects
            bpy.ops.object.duplicate(linked=False)
            
            # Get the duplicates
            duplicates = context.selected_objects.copy()
            
            # FIXED: Validate duplicates were created
            if not duplicates or len(duplicates) == 0:
                if props.debug_mode:
                    print("No duplicates were created")
                return False
                
            if props.debug_mode:
                print(f"Created {len(duplicates)} duplicates")
            
            # STEP 2: Apply modifiers if requested
            if item.apply_modifiers_before_join:
                if props.debug_mode:
                    print("Applying modifiers to duplicates...")
                for dup in duplicates:
                    # FIXED: Validate duplicate exists
                    if dup.name not in bpy.data.objects:
                        continue
                        
                    bpy.ops.object.select_all(action='DESELECT')
                    dup.select_set(True)
                    context.view_layer.objects.active = dup
                    for mod in dup.modifiers[:]:
                        try:
                            bpy.ops.object.modifier_apply(modifier=mod.name)
                        except Exception as e:
                            if props.debug_mode:
                                print(f"  Failed to apply modifier '{mod.name}': {str(e)}")
            
            # STEP 3: Deparent ALL duplicates
            if props.debug_mode:
                print("Deparenting all duplicates...")
            for dup in duplicates:
                # FIXED: Validate duplicate exists before deparenting
                if dup.name not in bpy.data.objects:
                    continue
                    
                if dup.parent:
                    world_matrix = dup.matrix_world.copy()
                    dup.parent = None
                    dup.matrix_world = world_matrix
            
            context.view_layer.update()
            
            # STEP 4: Join ALL duplicates into ONE object
            if len(duplicates) > 1:
                if props.debug_mode:
                    print(f"Joining all {len(duplicates)} duplicates into ONE object...")
                
                bpy.ops.object.select_all(action='DESELECT')
                
                # FIXED: Select only valid duplicates
                valid_duplicates = [d for d in duplicates if d.name in bpy.data.objects]
                if not valid_duplicates:
                    if props.debug_mode:
                        print("No valid duplicates to join")
                    return False
                
                for dup in valid_duplicates:
                    dup.select_set(True)
                
                # FIXED: Validate we have an active object before joining
                if len(valid_duplicates) > 0:
                    context.view_layer.objects.active = valid_duplicates[0]
                else:
                    if props.debug_mode:
                        print("No valid duplicates to set as active for join")
                    return False
                
                bpy.ops.object.join()
                joined_obj = context.active_object
            elif len(duplicates) == 1:
                # FIXED: Validate the single duplicate exists
                if duplicates[0].name in bpy.data.objects:
                    joined_obj = duplicates[0]
                else:
                    if props.debug_mode:
                        print("Single duplicate does not exist")
                    return False
            else:
                if props.debug_mode:
                    print("No duplicates to process")
                return False
            
            # FIXED: Validate joined object exists
            if not joined_obj or joined_obj.name not in bpy.data.objects:
                if props.debug_mode:
                    print("Joined object does not exist")
                return False
            
            # STEP 5: Rename to collection name (EXACTLY)
            joined_obj.name = collection.name
            if props.debug_mode:
                print(f"Renamed joined object to: {joined_obj.name}")
            
            # STEP 6: Set origin to reference empty location
            if props.debug_mode:
                print(f"Setting origin to reference empty location: {empty_world_loc}")
            
            original_cursor = context.scene.cursor.location.copy()
            context.scene.cursor.location = empty_world_loc
            
            # FIXED: Select the joined object before setting origin
            bpy.ops.object.select_all(action='DESELECT')
            joined_obj.select_set(True)
            context.view_layer.objects.active = joined_obj
            
            bpy.ops.object.origin_set(type='ORIGIN_CURSOR')
            context.scene.cursor.location = original_cursor
            
            if props.debug_mode:
                print(f"Final joined object location: {joined_obj.location}")
            
            # STEP 7: Export ONLY this ONE joined object
            if props.debug_mode:
                print(f"Exporting joined object as '{collection.name}.fbx'...")
            
            result = self.export_single_object_simple(context, props, joined_obj, collection.name, export_path)
            
            if props.debug_mode:
                print(f"Export result: {'SUCCESS' if result else 'FAILED'}")
            
            return result
        
        except Exception as e:
            if props.debug_mode:
                print(f"ERROR during join-all export: {str(e)}")
                import traceback
                traceback.print_exc()
            self.report({'ERROR'}, f"Error during join-all export: {str(e)}")
            return False
        
        finally:
            # STEP 8: Delete the temporary joined object
            if joined_obj and joined_obj.name in bpy.data.objects:
                if props.debug_mode:
                    print(f"Deleting temporary joined object: {joined_obj.name}")
                bpy.data.objects.remove(joined_obj, do_unlink=True)
            
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
                        apply_scale_options=props.apply_scaling,
                        use_space_transform=True,
                        bake_space_transform=props.bake_space_transform,
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
                        axis_up=props.axis_up,
                        apply_scale_options=props.apply_scaling,
                        bake_space_transform=props.bake_space_transform
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
    bl_label = "Mass Collection Exporter v11"
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
        row.operator("massexporter.join_empties", text="Join ALL Empties (Create Copies)", icon='MOD_SOLIDIFY')
        
        controls_box.label(text="✓ v11: Robust list checking for new objects")
        controls_box.label(text="✓ Always checks for latest meshes in collection")

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
                    mod_box.label(text="✓ Joins ALL empties into ONE mesh")
                    mod_box.label(text="✓ Handles new objects dynamically")
                
                # Auto move feature
                auto_box = box.box()
                auto_box.label(text="Auto Move to Origin:", icon='OUTLINER_OB_EMPTY')
                auto_box.prop(active_item, "move_empties_to_origin_on_export")
                
                if active_item.move_empties_to_origin_on_export:
                    info_box = auto_box.box()
                    info_box.label(text="Will move empties to origin before export")

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

        # Show FBX-specific options when FBX is selected
        if props.export_format == 'FBX':
            layout.separator()
            fbx_box = layout.box()
            fbx_box.label(text="FBX Options:", icon='EXPORT')
            
            fbx_box.prop(props, "apply_scaling")
            fbx_box.prop(props, "bake_space_transform")
            
            # Add axis settings to FBX options
            fbx_box.separator()
            fbx_box.label(text="Axis Orientation:")
            row = fbx_box.row()
            row.prop(props, "axis_forward", text="Forward")
            row.prop(props, "axis_up", text="Up")
            
            layout.separator()
            layout.prop(props, "use_custom_fbx_ascii")
            
            # Add helpful info
            info_box = layout.box()
            info_box.label(text="Unity Import Tips:", icon='INFO')
            info_box.label(text="• Apply Scaling: Use 'FBX Units Scale'")
            info_box.label(text="• Apply Transform: Enable for clean imports")
            info_box.label(text="• Default: -Z Forward, Y Up for Unity")

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
