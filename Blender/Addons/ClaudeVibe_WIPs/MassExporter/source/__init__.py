# Single source of truth for the addon version. bl_info + blender_manifest.toml
# both derive from this; the panel title does NOT show the version. Bump here
# and in blender_manifest.toml only.
VERSION = (13, 6, 3)

bl_info = {
    "name": "Mass Collection Exporter",
    "author": "Claude AI, Stephko",
    "version": VERSION,
    "blender": (4, 2, 0),
    "location": "3D View > N-Panel > Mass Exporter",
    "description": "Batch export collections with modifier apply, rig export, armature options, state-proof visibility isolation (local view / hidden / excluded), suffix grouping, and whole-collection-as-one-file export",
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
def join_empty_children_core_logic(context, report_func=None, apply_modifiers=False, apply_only_visible=False, keep_joined_copy=True):
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
                batch_deselect_all(context)
                
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
                        batch_deselect_all(context)
                        dup.select_set(True)
                        context.view_layer.objects.active = dup

                        # Remove disabled modifiers first if apply_only_visible is enabled
                        if apply_only_visible:
                            print(f"    Checking for disabled modifiers on {dup.name}...")
                            modifiers_to_remove = []
                            for modifier in dup.modifiers:
                                if not modifier.show_viewport:
                                    modifiers_to_remove.append(modifier.name)
                                    print(f"      Marking disabled modifier '{modifier.name}' for removal")

                            # Remove disabled modifiers
                            for mod_name in modifiers_to_remove:
                                dup.modifiers.remove(dup.modifiers[mod_name])
                                print(f"      Removed disabled modifier '{mod_name}' from {dup.name}")

                        # Apply remaining modifiers
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
                    batch_deselect_all(context)
                    
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
        batch_deselect_all(context)
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

class SuffixItem(PropertyGroup):
    """Individual suffix definition for grouping exports"""
    suffix: StringProperty(
        name="Suffix",
        description="Suffix to look for (e.g., _COL, _LOD0, _UCX)",
        default="_COL"
    )

    enabled: BoolProperty(
        name="Enabled",
        description="Enable this suffix for grouping",
        default=True
    )

    description: StringProperty(
        name="Description",
        description="Description of what this suffix represents",
        default="Collision"
    )


# ============================================================================
# Suffix Grouping Helper Functions
# ============================================================================

_SUFFIX_SEPARATORS = ("_", "-", ".", " ")


def get_base_name_without_suffix(name, suffix_items):
    """
    Get the base name by removing any matching suffix.
    Returns (base_name, matched_suffix) or (name, None) if no suffix matched.

    Trailing separator characters (_ - . space) are stripped from the
    resulting base so that suffixes typed without a leading separator
    (e.g. "cape") group correctly with the unsuffixed sibling
    (e.g. "char_001" and "char_001_cape" both reduce to "char_001").
    """
    name_lower = name.lower()
    # Match the longest enabled suffix first so "cape" doesn't out-match
    # "_cape" when both are defined.
    enabled = sorted(
        (item for item in suffix_items if item.enabled),
        key=lambda i: len(i.suffix),
        reverse=True,
    )
    for item in enabled:
        suffix_lower = item.suffix.lower()
        if not suffix_lower:
            continue
        if name_lower.endswith(suffix_lower):
            base = name[: -len(item.suffix)]
            # Strip a single trailing separator so "char_001_" -> "char_001"
            if base and base[-1] in _SUFFIX_SEPARATORS:
                base = base[:-1]
            return base, item.suffix
    return name, None


def find_suffix_groups(objects, suffix_items, debug=False):
    """
    Group objects by their base name (without suffix).
    Returns a dict: {base_name: [(obj, suffix_or_None), ...]}

    Objects without any suffix are grouped under their own name.
    Objects with suffixes are grouped with their base name counterparts.
    """
    groups = {}

    for obj in objects:
        base_name, suffix = get_base_name_without_suffix(obj.name, suffix_items)

        if base_name not in groups:
            groups[base_name] = []

        groups[base_name].append((obj, suffix))

        if debug:
            if suffix:
                print(f"  Object '{obj.name}' -> base '{base_name}' (suffix: {suffix})")
            else:
                print(f"  Object '{obj.name}' -> base '{base_name}' (no suffix)")

    return groups


def find_suffix_groups_in_collection(collection, suffix_items, include_subcollections=True, debug=False):
    """
    Find all objects in a collection and group them by base name.
    Works with parent empties and sub-collections.

    Returns dict: {base_name: {'objects': [(obj, suffix)], 'empties': [empty], 'subcollections': [coll]}}
    """
    groups = {}

    def add_to_group(base_name, obj, suffix, source_type='object', source=None):
        if base_name not in groups:
            groups[base_name] = {'objects': [], 'empties': [], 'subcollections': []}

        if source_type == 'object':
            groups[base_name]['objects'].append((obj, suffix))
        elif source_type == 'empty':
            if source and source not in groups[base_name]['empties']:
                groups[base_name]['empties'].append(source)
        elif source_type == 'subcollection':
            if source and source not in groups[base_name]['subcollections']:
                groups[base_name]['subcollections'].append(source)

    def process_collection(coll, depth=0):
        indent = "  " * depth
        if debug:
            print(f"{indent}Processing collection: {coll.name}")

        # Process objects directly in collection
        for obj in coll.objects:
            if obj.type == 'MESH':
                base_name, suffix = get_base_name_without_suffix(obj.name, suffix_items)
                add_to_group(base_name, obj, suffix, 'object')
                if debug:
                    print(f"{indent}  Mesh '{obj.name}' -> '{base_name}'")

            elif obj.type == 'EMPTY':
                # Check the empty's name for suffix matching
                empty_base, empty_suffix = get_base_name_without_suffix(obj.name, suffix_items)

                # Get all mesh children
                children = [child for child in obj.children if child.type == 'MESH']
                if children:
                    # Add children under the empty's base name
                    for child in children:
                        add_to_group(empty_base, child, empty_suffix, 'empty', obj)
                    if debug:
                        print(f"{indent}  Empty '{obj.name}' ({len(children)} children) -> '{empty_base}'")

        # Process sub-collections
        if include_subcollections:
            for sub_coll in coll.children:
                sub_base, sub_suffix = get_base_name_without_suffix(sub_coll.name, suffix_items)

                # Get all mesh objects in sub-collection
                sub_objects = []
                for obj in sub_coll.all_objects:
                    if obj.type == 'MESH':
                        sub_objects.append(obj)

                if sub_objects:
                    for obj in sub_objects:
                        add_to_group(sub_base, obj, sub_suffix, 'subcollection', sub_coll)
                    if debug:
                        print(f"{indent}  Sub-collection '{sub_coll.name}' ({len(sub_objects)} meshes) -> '{sub_base}'")

    process_collection(collection)

    return groups


# ============================================================================
# Performance Helpers (from v12.6.0)
# ============================================================================

def batch_deselect_all(context):
    """Deselect all by iterating only currently selected objects — much faster
    than batch_deselect_all(context) which walks all scene objects."""
    for obj in context.selected_objects:
        obj.select_set(False)


def batch_select_objects(objects, context, deselect_first=True):
    """Efficiently select a list of objects."""
    if deselect_first:
        batch_deselect_all(context)
    for obj in objects:
        obj.select_set(True)
    if objects:
        context.view_layer.objects.active = objects[0]


def build_collection_depth_map():
    """Build a collection -> depth map for fast O(n) lookups.
    Depth is distance from the scene root collection (root = 0)."""
    depth_map = {}

    def traverse(collection, depth):
        depth_map[collection] = depth
        for child in collection.children:
            traverse(child, depth + 1)

    for scene in bpy.data.scenes:
        traverse(scene.collection, 0)

    for coll in bpy.data.collections:
        if coll not in depth_map:
            depth_map[coll] = 0

    return depth_map


def find_immediate_collection(obj, depth_map=None):
    """Return the deepest (most immediate) collection directly containing obj.
    Pass a pre-built depth_map when calling in a loop for best performance."""
    containing = [c for c in bpy.data.collections if obj.name in c.objects]
    if not containing:
        return None
    if len(containing) == 1:
        return containing[0]
    if depth_map is None:
        depth_map = build_collection_depth_map()
    return max(containing, key=lambda c: depth_map.get(c, 0))


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
        name="Center Each Empty",
        description="Temporarily center each empty at origin during its export",
        default=True
    )

    move_empties_to_origin_on_export: BoolProperty(
        name="Move All Empties to Origin",
        description="Move all empties to world origin before export begins",
        default=False
    )

    join_empty_children: BoolProperty(
        name="Join Empty Children",
        description="Combine all mesh children into a single object per export",
        default=False
    )

    apply_modifiers_before_join: BoolProperty(
        name="Apply Modifiers",
        description="Apply modifiers before joining meshes",
        default=False
    )

    apply_only_visible: BoolProperty(
        name="Only Visible Modifiers",
        description="Skip modifiers disabled in viewport",
        default=False
    )

    move_to_center: BoolProperty(
        name="Move to Center",
        description="Temporarily move objects to world origin (0,0,0) during export",
        default=True
    )

    use_suffix_grouping: BoolProperty(
        name="Group by Suffix",
        description="Group objects with matching names but different suffixes (e.g., sm_cube and sm_cube_COL) into single exports",
        default=False
    )

    export_as_single_fbx: BoolProperty(
        name="Whole Collection as One File",
        description=(
            "Export the entire collection (including all subcollections, meshes, "
            "armatures and empties) into a single file, preserving hierarchy. "
            "Armature modifiers stay bound because rigs are included in the same export. "
            "Takes priority over other export modes"
        ),
        default=False
    )

    single_fbx_custom_name: StringProperty(
        name="Custom Filename",
        description=(
            "Filename to use when 'Whole Collection as One File' is enabled "
            "(without extension). Leave empty to use the collection's name"
        ),
        default=""
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
        """Update collection visibility in scene (legacy path).
        The UIList now uses the toggle operator, but this callback is kept for
        backwards-compat in case external scripts flip ``visibility_synced``.
        """
        coll = self.collection
        if coll is None:
            return
        if hasattr(coll, 'hide_viewport'):
            coll.hide_viewport = not self.visibility_synced
        if hasattr(coll, 'hide_render'):
            coll.hide_render = not self.visibility_synced

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

    # Suffix Grouping Options
    suffix_items: CollectionProperty(
        type=SuffixItem,
        name="Export Suffixes"
    )

    active_suffix_index: IntProperty(
        name="Active Suffix Index",
        default=0
    )

    # Transform Options
    # Note: "Export at Origin" is gone — centering is now per-collection via
    # `move_to_center` on each CollectionItem. See _center_root_objects_temporarily.

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

    apply_modifiers: BoolProperty(
        name="Apply Modifiers",
        description="Apply all object modifiers before export",
        default=True
    )

    skip_armature_modifier: BoolProperty(
        name="Skip Armature Modifier",
        description="When applying modifiers, skip armature deform modifiers (exports mesh without armature deformation)",
        default=False
    )

    export_rig_with_mesh: BoolProperty(
        name="Export Rig with Mesh",
        description="Include the armature object from Armature modifiers in the export, even if it is not part of the export collection",
        default=False
    )

    # FBX Armature Options
    primary_bone_axis: EnumProperty(
        name="Primary Bone Axis",
        items=[
            ('X', 'X Axis', ''),
            ('Y', 'Y Axis', ''),
            ('Z', 'Z Axis', ''),
            ('-X', '-X Axis', ''),
            ('-Y', '-Y Axis', ''),
            ('-Z', '-Z Axis', ''),
        ],
        default='Y'
    )

    secondary_bone_axis: EnumProperty(
        name="Secondary Bone Axis",
        items=[
            ('X', 'X Axis', ''),
            ('Y', 'Y Axis', ''),
            ('Z', 'Z Axis', ''),
            ('-X', '-X Axis', ''),
            ('-Y', '-Y Axis', ''),
            ('-Z', '-Z Axis', ''),
        ],
        default='X'
    )

    armature_nodetype: EnumProperty(
        name="Armature FBX Node",
        items=[
            ('NULL', 'Null', 'Export armature as a null/locator node'),
            ('ROOT', 'Root', 'Export armature as a root node'),
            ('LIMBNODE', 'LimbNode', 'Export armature as a limb node'),
        ],
        default='NULL'
    )

    use_armature_deform_only: BoolProperty(
        name="Only Deform Bones",
        description="Only export bones used for mesh deformation",
        default=True
    )

    add_leaf_bones: BoolProperty(
        name="Add Leaf Bones",
        description="Append a final bone to the end of each chain to specify the tip of the last bone",
        default=False
    )

    export_hidden_collections: BoolProperty(
        name="Export Hidden Collections",
        description=(
            "Temporarily unhide collections/objects that are hidden "
            "(collection hide_viewport, layer collection exclude / hide, "
            "object eye icon, selection lock, local view) so they can be "
            "exported. Original visibility state is restored afterward. "
            "When disabled, hidden collections are skipped with a warning"
        ),
        default=True
    )

# Blender has two separate "hide" flags:
#   - Collection.hide_viewport: the monitor icon in the outliner (disable in
#     viewports globally, across all view layers)
#   - LayerCollection.hide_viewport: the EYE icon in the outliner (per view
#     layer, temporary)
# Users almost always toggle the EYE in the outliner, so the UIList eye has to
# read/write LayerCollection.hide_viewport to stay in sync.
def _find_layer_collection(root_lc, target_coll):
    """Return the LayerCollection wrapping target_coll in the active view
    layer, or None if the collection is not present in this view layer."""
    if root_lc is None or target_coll is None:
        return None
    stack = [root_lc]
    while stack:
        lc = stack.pop()
        if lc.collection == target_coll:
            return lc
        stack.extend(lc.children)
    return None


def _collection_effective_hidden(coll):
    """Return the best-effort 'is the eye icon off?' for coll.

    Uses LayerCollection.hide_viewport when the collection is in the active
    view layer; falls back to Collection.hide_viewport otherwise.
    """
    if coll is None:
        return False
    try:
        root_lc = bpy.context.view_layer.layer_collection
    except AttributeError:
        root_lc = None
    lc = _find_layer_collection(root_lc, coll)
    if lc is not None:
        return bool(lc.hide_viewport)
    return bool(getattr(coll, 'hide_viewport', False))


# UI Lists
class MASSEXPORTER_UL_collections(UIList):
    """UI List for collection items"""

    def draw_item(self, context, layout, data, item, icon, active_data,
                  active_propname, index=0, flt_flag=0):
        if self.layout_type in {'DEFAULT', 'COMPACT'}:
            coll = item.collection

            # Eye icon mirrors the outliner eye: LayerCollection.hide_viewport
            # in the active view layer. Falls back to Collection.hide_viewport
            # if the collection is not in this view layer.
            is_hidden = _collection_effective_hidden(coll)
            eye_icon = 'HIDE_ON' if is_hidden else 'HIDE_OFF'
            vis_row = layout.row()
            vis_row.enabled = coll is not None
            op = vis_row.operator("massexporter.toggle_collection_visibility",
                                  text="", icon=eye_icon, emboss=False)
            op.index = index

            # Export checkbox
            layout.prop(item, "export_enabled", text="")

            # Merge checkbox
            layout.prop(item, "merge_to_single", text="", icon='SNAP_FACE_CENTER')

            # Collection selector
            layout.prop(item, "collection", text="")

            # Export path
            row = layout.row()
            row.prop(item, "export_path", text="")
            row.operator("massexporter.select_folder", text="", icon='FOLDER_REDIRECT').index = index

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
        apply_only_visible = False
        for item in props.collection_items:
            if item.export_enabled and item.collection and item.apply_modifiers_before_join:
                apply_modifiers = True
                if item.apply_only_visible:
                    apply_only_visible = True
                break

        # KEEP the joined copies for debug button (keep_joined_copy=True)
        return join_empty_children_core_logic(context, self.report, apply_modifiers, apply_only_visible, keep_joined_copy=True)

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


class MASSEXPORTER_OT_toggle_collection_visibility(Operator):
    """Toggle viewport (and render) visibility of the collection assigned to this row"""
    bl_idname = "massexporter.toggle_collection_visibility"
    bl_label = "Toggle Collection Visibility"
    bl_description = "Toggle visibility of the assigned collection (viewport + render)"

    index: IntProperty()

    def execute(self, context):
        props = context.scene.mass_exporter_props
        if not (0 <= self.index < len(props.collection_items)):
            return {'CANCELLED'}
        coll = props.collection_items[self.index].collection
        if coll is None:
            self.report({'WARNING'}, "No collection assigned to this row")
            return {'CANCELLED'}
        if not hasattr(coll, 'hide_viewport'):
            self.report({'WARNING'},
                        f"'{getattr(coll, 'name', '<unknown>')}' is not a Collection (type={type(coll).__name__})")
            return {'CANCELLED'}
        # Toggle the same flag the outliner eye uses so the UIs stay in sync.
        # LayerCollection.hide_viewport is per-view-layer (the eye). We only
        # fall back to Collection.hide_viewport when the collection isn't in
        # the active view layer at all.
        lc = _find_layer_collection(context.view_layer.layer_collection, coll)
        if lc is not None:
            lc.hide_viewport = not lc.hide_viewport
        else:
            coll.hide_viewport = not coll.hide_viewport
            if hasattr(coll, 'hide_render'):
                coll.hide_render = coll.hide_viewport
        return {'FINISHED'}


# ============================================================================
# Suffix Management Operators
# ============================================================================

class MASSEXPORTER_OT_add_suffix(Operator):
    """Add a new suffix to the grouping list"""
    bl_idname = "massexporter.add_suffix"
    bl_label = "Add Suffix"
    bl_description = "Add a new suffix for grouping exports (e.g., _COL for collision)"

    suffix: StringProperty(
        name="Suffix",
        default="_COL"
    )

    description: StringProperty(
        name="Description",
        default="Collision"
    )

    def execute(self, context):
        props = context.scene.mass_exporter_props
        item = props.suffix_items.add()
        item.suffix = self.suffix
        item.description = self.description
        item.enabled = True
        props.active_suffix_index = len(props.suffix_items) - 1
        return {'FINISHED'}

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)

    def draw(self, context):
        layout = self.layout
        layout.prop(self, "suffix")
        layout.prop(self, "description")


class MASSEXPORTER_OT_remove_suffix(Operator):
    """Remove suffix from grouping list"""
    bl_idname = "massexporter.remove_suffix"
    bl_label = "Remove Suffix"
    bl_description = "Remove selected suffix from grouping list"

    def execute(self, context):
        props = context.scene.mass_exporter_props
        if props.suffix_items:
            props.suffix_items.remove(props.active_suffix_index)
            props.active_suffix_index = max(0, props.active_suffix_index - 1)
        return {'FINISHED'}


class MASSEXPORTER_OT_add_default_suffixes(Operator):
    """Add common default suffixes"""
    bl_idname = "massexporter.add_default_suffixes"
    bl_label = "Add Default Suffixes"
    bl_description = "Add common suffixes like _COL (collision), _LOD0, _UCX (Unreal collision)"

    def execute(self, context):
        props = context.scene.mass_exporter_props

        # Common game development suffixes
        defaults = [
            ("_COL", "Collision"),
            ("_col", "Collision (lowercase)"),
            ("_UCX", "Unreal Convex Collision"),
            ("_LOD0", "LOD Level 0"),
            ("_LOD1", "LOD Level 1"),
            ("_LOD2", "LOD Level 2"),
            ("_LOD3", "LOD Level 3"),
        ]

        added_count = 0
        existing_suffixes = [item.suffix.lower() for item in props.suffix_items]

        for suffix, desc in defaults:
            if suffix.lower() not in existing_suffixes:
                item = props.suffix_items.add()
                item.suffix = suffix
                item.description = desc
                item.enabled = True
                added_count += 1

        if added_count > 0:
            props.active_suffix_index = len(props.suffix_items) - 1
            self.report({'INFO'}, f"Added {added_count} default suffix(es)")
        else:
            self.report({'INFO'}, "All default suffixes already exist")

        return {'FINISHED'}


class MASSEXPORTER_UL_suffixes(UIList):
    """UIList for suffix items"""
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname):
        if self.layout_type in {'DEFAULT', 'COMPACT'}:
            row = layout.row(align=True)
            row.prop(item, "enabled", text="")
            row.prop(item, "suffix", text="", emboss=False)
            row.label(text=f"({item.description})")
        elif self.layout_type == 'GRID':
            layout.alignment = 'CENTER'
            layout.prop(item, "enabled", text="")

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

        # Sync the legacy visibility_synced flag with the live collection
        # state. The UIList eye icon reads collection.hide_viewport directly
        # now, so this is only relevant for any external code still inspecting
        # visibility_synced.
        for item in props.collection_items:
            coll = item.collection
            if coll is not None and hasattr(coll, 'hide_viewport'):
                item.visibility_synced = not coll.hide_viewport

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
        exported_collection_names = []  # NEW: Track exported collection names

        # --- Sanity check: clean up any orphaned temp-export objects from a
        # previous interrupted run. The modifier-apply path renames originals
        # to `__mexport_<name>` while a duplicate takes the clean name; if a
        # prior export crashed mid-flight those stale names can cause name
        # collisions / duplicate-op failures on the next run.
        stale = [o for o in bpy.data.objects if o.name.startswith("__mexport_")]
        if stale:
            self.report({'WARNING'},
                        f"Recovered {len(stale)} leftover temp objects from a prior export — restoring names")
            for o in stale:
                clean = o.name[len("__mexport_"):]
                # Only restore if the clean name is free; otherwise leave alone
                # so the user can inspect.
                if clean not in bpy.data.objects:
                    o.name = clean

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

        # Export only collections whose checkbox is enabled, regardless of
        # which row is active/selected in the UIList. A per-item try/except
        # ensures one bad collection does not abort the rest of the batch.
        failed = []
        try:
            for item in props.collection_items:
                if not (item.export_enabled and item.collection and item.export_path):
                    continue
                coll = item.collection
                coll_name = getattr(coll, 'name', '<unknown>')
                # Validate the pointer is actually a Collection — it must
                # expose `all_objects`. If not, the row is pointing at an
                # Object/ID by mistake (possible after old data migrations);
                # skip and warn instead of crashing/hanging in the export
                # path.
                if not hasattr(coll, 'all_objects'):
                    self.report({'WARNING'},
                                f"Row '{coll_name}' is not a Collection "
                                f"(type={type(coll).__name__}) — skipping")
                    continue
                if props.debug_mode:
                    print(f"\n--- Exporting '{coll_name}' ---")
                try:
                    if self.export_collection(context, props, item):
                        exported_count += 1
                        exported_collection_names.append(coll_name)
                except Exception as e:
                    failed.append((coll_name, str(e)))
                    if props.debug_mode:
                        import traceback
                        traceback.print_exc()
        finally:
            # Surface per-item failures to the user.
            for coll_name, err in failed:
                self.report({'ERROR'}, f"Export failed for '{coll_name}': {err}")

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
            batch_deselect_all(context)
            for obj in original_selection:
                if obj.name in bpy.data.objects:  # Check if object still exists
                    obj.select_set(True)
            if original_active and original_active.name in bpy.data.objects:
                context.view_layer.objects.active = original_active

            if props.debug_mode:
                print("=== ALL POSITIONS RESTORED ===")

        # NEW: Report exported collection names
        if exported_count > 0:
            names_str = ", ".join(exported_collection_names[:3])  # Show first 3
            if len(exported_collection_names) > 3:
                names_str += f", ... ({len(exported_collection_names)} total)"
            self.report({'INFO'}, f"Exported {exported_count} collections: {names_str}")
        else:
            self.report({'WARNING'}, "No collections were exported")
            
        return {'FINISHED'}

    @staticmethod
    def _get_layer_collection_path(root_lc, target_coll):
        """Return all LayerCollections from root down to the one wrapping target_coll.

        Uses explicit visited-set + iterative BFS to guard against any malformed
        layer-collection graph that could otherwise send the previous recursive
        implementation into an infinite loop / stack blow-up. A proper Blender
        scene has a pure tree, but library-linked / override scenes have been
        observed to briefly expose cycles while state is in transition.

        CRITICAL: the visited set is keyed on the wrapped Collection's name, NOT
        `id(lc)`. Blender re-creates the `LayerCollection` Python wrapper on every
        `.children` access, so each wrapper is a throwaway object; once it is
        garbage-collected Python freely RECYCLES its `id()` for the next wrapper.
        Keying `visited` on `id(lc)` therefore produces false "already visited"
        hits that abort the search before it reaches the target — returning [],
        which silently disables the entire unhide pipeline (the bug that left
        eye-hidden parent collections un-revealed during export). Collection names
        are unique per blend file and stable across wrapper churn, so they are a
        safe identity key.
        """
        if root_lc is None or target_coll is None:
            return []
        visited = set()
        # Each queue entry is (layer_coll, path_so_far_without_self)
        queue = [(root_lc, [])]
        while queue:
            lc, path = queue.pop(0)
            key = lc.collection.name if lc.collection is not None else id(lc)
            if key in visited:
                continue
            visited.add(key)
            if lc.collection == target_coll:
                return path + [lc]
            for child in lc.children:
                queue.append((child, path + [lc]))
        return []

    @staticmethod
    def _collection_is_hidden(collection):
        """Return True if the collection is hidden through any viewport-level
        mechanism: data-level `hide_viewport`, or any layer collection on the
        path having `exclude` or `hide_viewport` set."""
        if getattr(collection, 'hide_viewport', False):
            return True
        root_lc = bpy.context.view_layer.layer_collection
        path = MASSEXPORTER_OT_export_all._get_layer_collection_path(root_lc, collection)
        for lc in path:
            if lc.exclude or lc.hide_viewport:
                return True
        return False

    @staticmethod
    def _unhide_collection_for_export(collection):
        """Force collection into a fully-exportable state, deterministically.

        Strategy: clear every Blender hide flag that can block select_set and
        make the object invisible to the exporter — on every Collection and
        LayerCollection touched by the export, and on every object in scope.
        Restore is symmetric: the backup is a flat list of (obj/coll/lc,
        original-value-tuple) entries that _restore_collection_for_export
        replays in reverse order. That property guarantees two consecutive
        exports yield the same scene state.

        Scope of what gets unhidden, all in a single pass:

          Collections (data-block — the monitor icon):
            - Every Collection on the path from scene root to target
            - Target itself
            - Every descendant Collection of target (recursively)
            Flags cleared: hide_viewport, hide_render

          LayerCollections (the outliner eye + the exclude checkbox):
            - Same tree: root-to-target + all descendants
            Flags cleared: exclude, hide_viewport

          Objects (collection.all_objects of target — flat recursive list):
            Flags cleared: hide_viewport, hide_get (eye), hide_select
            Added to local view in every 3D-viewport space that currently
            has local view active, so select_set is not silently rejected

        After the Collection and LayerCollection flips we flush the view
        layer once; object flips follow; we flush again so hide_get reflects
        the flips before the caller's select_set fires.
        """
        backup = {
            'target_collection': collection,
            'coll_flags': [],     # [(coll, hide_viewport, hide_render), ...]
            'layer_coll': [],     # [(lc, exclude, hide_viewport, is_master), ...]
            'objects': [],        # [(obj, hide_viewport, hide_get), ...]
            'hide_select': [],    # [(obj, prev_hide_select), ...]
            'local_view': [],     # [(obj, space), ...]
        }

        root_lc = bpy.context.view_layer.layer_collection
        path = MASSEXPORTER_OT_export_all._get_layer_collection_path(root_lc, collection)

        # Every LayerCollection we will touch: path (root→target) + every
        # descendant of target. Drives both LayerCollection-flag clearing and
        # Collection-flag clearing (one Collection per LayerCollection).
        lc_all = list(path)
        if path:
            stack = list(path[-1].children)
            while stack:
                lc = stack.pop()
                lc_all.append(lc)
                stack.extend(lc.children)

        # 1) Clear LayerCollection flags (per-view-layer: exclude + eye).
        #    NEVER write `exclude` on the master (scene-root) LayerCollection:
        #    on Blender 5.0, assigning `master.exclude` — even to its current
        #    value — cascades a reset of EVERY descendant LayerCollection's
        #    `exclude` flag across the whole view layer. That silently wipes the
        #    original exclude state (including unrelated excluded collections)
        #    *before* we record it, so the backup captures the wrong values and
        #    restore can never put them back. The master is always effectively
        #    included anyway, so skipping its `exclude` loses nothing; we still
        #    clear its eye (hide_viewport). `is_master` is stored so the
        #    symmetric restore can skip it without needing the root reference.
        for lc in lc_all:
            is_master = (lc == root_lc)
            backup['layer_coll'].append((lc, lc.exclude, lc.hide_viewport, is_master))
            if not is_master:
                lc.exclude = False
            lc.hide_viewport = False

        # 2) Clear Collection-level flags (global: monitor icon + camera)
        #    Iterate the Collections behind each LayerCollection, de-duped.
        #    De-dupe on the Collection NAME, not id(coll): `lc.collection`
        #    returns a fresh wrapper each access and Python recycles freed
        #    wrappers' id()s, so id()-keyed dedup yields false collisions that
        #    would skip clearing a still-hidden collection (same class of bug
        #    as the old id(lc) path-walk — see _get_layer_collection_path).
        seen_colls = set()
        for lc in lc_all:
            coll = lc.collection
            if coll is None:
                continue
            key = coll.name
            if key in seen_colls:
                continue
            seen_colls.add(key)
            hv = getattr(coll, 'hide_viewport', False)
            hr = getattr(coll, 'hide_render', False)
            backup['coll_flags'].append((coll, hv, hr))
            if hasattr(coll, 'hide_viewport'):
                coll.hide_viewport = False
            if hasattr(coll, 'hide_render'):
                coll.hide_render = False

        # CRITICAL: flush the view layer now, BEFORE touching per-object state.
        # Clearing `lc.exclude` re-adds the collection's objects to the view
        # layer — but until the depsgraph refreshes, calling `obj.hide_set()`
        # or `obj.select_set()` raises "object is not in view layer" and the
        # exporter silently writes nothing.
        bpy.context.view_layer.update()

        # 3) Object-level flags + local view membership.
        #    Every 3D viewport (across every window) currently in local view.
        local_view_spaces = []
        wm = getattr(bpy.context, 'window_manager', None)
        if wm is not None:
            for window in wm.windows:
                for area in window.screen.areas:
                    if area.type != 'VIEW_3D':
                        continue
                    for space in area.spaces:
                        if space.type == 'VIEW_3D' and getattr(space, 'local_view', None):
                            local_view_spaces.append(space)

        # Materialize into a plain Python list BEFORE the loop. Iterating a
        # live `bpy_prop_collection` while the body calls `hide_set` /
        # `local_view_set` mutates the depsgraph mid-walk — on Blender 5.0
        # this has been observed to invalidate the underlying iterator and
        # segfault. A frozen list of object refs sidesteps that entirely.
        try:
            all_objects = list(getattr(collection, 'all_objects', ()) or ())
        except (ReferenceError, AttributeError, TypeError):
            all_objects = []
        skipped = []
        for obj in all_objects:
            # Skip stale / freed references defensively — `obj` from a
            # cached list can outlive the underlying ID datablock.
            try:
                _ = obj.name
            except (ReferenceError, AttributeError):
                continue
            try:
                backup['objects'].append((obj, obj.hide_viewport, obj.hide_get()))
                obj.hide_viewport = False
                obj.hide_set(False)
            except (AttributeError, RuntimeError, ReferenceError) as exc:
                # After the exhaustive layer flush above this should never
                # fire; keep it as a visible regression signal.
                skipped.append((getattr(obj, 'name', '<?>'), str(exc)))
                continue
            try:
                if obj.hide_select:
                    backup['hide_select'].append((obj, True))
                    obj.hide_select = False
            except (AttributeError, ReferenceError):
                pass
            for space in local_view_spaces:
                try:
                    was_in_lv = obj.local_view_get(space)
                except (AttributeError, RuntimeError, TypeError, ReferenceError):
                    continue
                if not was_in_lv:
                    try:
                        obj.local_view_set(space, True)
                        backup['local_view'].append((obj, space))
                    except (AttributeError, RuntimeError, TypeError, ReferenceError):
                        continue

        if skipped:
            print(f"[MassExporter] _unhide_collection_for_export: skipped "
                  f"{len(skipped)} objects not in view layer "
                  f"(first: {skipped[0]}) — this is a bug, please report")

        # Flush so hide_get() reflects the flips before the caller selects.
        bpy.context.view_layer.update()

        return backup

    @staticmethod
    def _restore_collection_for_export(backup):
        """Symmetric restore. Replays the backup in reverse order so two
        consecutive exports leave the scene in identical state."""
        # Objects first (they depend on their collections existing in view
        # layer — which, after restore, may no longer be true).
        for obj, space in backup.get('local_view', ()):
            if obj.name in bpy.data.objects:
                try:
                    obj.local_view_set(space, False)
                except (AttributeError, RuntimeError, TypeError):
                    pass
        for obj, prev in backup.get('hide_select', ()):
            if obj.name in bpy.data.objects:
                try:
                    obj.hide_select = prev
                except AttributeError:
                    pass
        for obj, hide_viewport, hide_eye in backup.get('objects', ()):
            if obj.name in bpy.data.objects:
                try:
                    obj.hide_viewport = hide_viewport
                    obj.hide_set(hide_eye)
                except (AttributeError, RuntimeError):
                    pass

        # Collection-level flags (monitor + camera icons)
        for coll, hv, hr in backup.get('coll_flags', ()):
            if hasattr(coll, 'hide_viewport'):
                try:
                    coll.hide_viewport = hv
                except (AttributeError, ReferenceError):
                    pass
            if hasattr(coll, 'hide_render'):
                try:
                    coll.hide_render = hr
                except (AttributeError, ReferenceError):
                    pass

        # LayerCollection flags (eye + exclude) — last, so the view layer's
        # final state is the originally-saved one. Restore DEEPEST-FIRST
        # (reverse of capture order): `exclude` is hierarchical, so writing an
        # ancestor's `exclude` before its descendants' would force-include the
        # descendants and corrupt their flags. Skip the master's `exclude` for
        # the same reason it is skipped on the way in (see _unhide_*).
        for lc, was_excluded, was_hidden, is_master in reversed(backup.get('layer_coll', ())):
            try:
                if not is_master:
                    lc.exclude = was_excluded
                lc.hide_viewport = was_hidden
            except (AttributeError, ReferenceError):
                pass

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

        # Visibility isolation: forces collection / layer collection / object
        # / local-view state into an exportable shape for the duration of the
        # export, then restores it in `finally`. Local-view isolation is
        # always applied (it is the only way the exporter works at all while
        # the user is in local view); hidden-collection isolation is gated on
        # the user-facing `export_hidden_collections` toggle so skipping
        # hidden rows stays an option.
        is_hidden = MASSEXPORTER_OT_export_all._collection_is_hidden(collection)
        if is_hidden and not props.export_hidden_collections:
            self.report(
                {'WARNING'},
                f"Skipping '{collection.name}' — it is hidden and "
                "'Export Hidden Collections' is off"
            )
            return False
        if is_hidden and props.debug_mode:
            print(f"[MassExporter] Unhiding hidden collection '{collection.name}' for export "
                  f"(armature rules still apply via export_rig_with_mesh)")
        visibility_backup = MASSEXPORTER_OT_export_all._unhide_collection_for_export(collection)

        try:
            # Handle different export modes
            # Whole-collection-as-one-file takes highest priority — it bundles
            # every object (meshes + armatures + empties + ...) into a single
            # FBX with hierarchy intact, so it should short-circuit the other
            # per-collection modes.
            if item.export_as_single_fbx:
                return MASSEXPORTER_OT_export_all.export_collection_as_single_fbx(self, context, props, item)
            # Suffix grouping takes priority if enabled
            if item.use_suffix_grouping and len(props.suffix_items) > 0:
                return MASSEXPORTER_OT_export_all.export_with_suffix_grouping(self, context, props, item)
            elif item.export_subcollections_as_single:
                return MASSEXPORTER_OT_export_all.export_subcollections_as_single(self, context, props, item)
            elif item.use_empty_origins:
                return MASSEXPORTER_OT_export_all.export_with_empty_origins(self, context, props, item)
            else:
                objects = MASSEXPORTER_OT_export_all.get_collection_objects(self, collection)

                if not objects:
                    self.report({'WARNING'}, f"No objects found in collection: {collection.name}")
                    return False

                if item.merge_to_single:
                    return MASSEXPORTER_OT_export_all.export_objects_as_single(self, context, props, objects, collection.name, export_path, item=item)
                else:
                    success_count = 0
                    for obj in objects:
                        if MASSEXPORTER_OT_export_all.export_single_object(self, context, props, obj, export_path, item=item):
                            success_count += 1
                    return success_count > 0
        finally:
            if visibility_backup:
                MASSEXPORTER_OT_export_all._restore_collection_for_export(visibility_backup)

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
            if MASSEXPORTER_OT_export_all.export_objects_as_single(self, context, props, main_objects, f"{collection.name}_main", export_path, item=item):
                success_count += 1

        # Export each sub-collection as individual merged files
        for sub_collection in collection.children:
            # FIXED: Use new join logic if join_empty_children is enabled
            if item.use_empty_origins and item.join_empty_children:
                # Join all empties in this sub-collection and export as one
                if MASSEXPORTER_OT_export_all.export_collection_with_all_empties_joined(self, context, props, item, sub_collection, export_path):
                    success_count += 1
            else:
                sub_objects = MASSEXPORTER_OT_export_all.get_collection_objects(self, sub_collection)
                if sub_objects:
                    if MASSEXPORTER_OT_export_all.export_objects_as_single(self, context, props, sub_objects, sub_collection.name, export_path, item=item):
                        success_count += 1

        return success_count > 0

    # Object types that survive a round-trip through the FBX exporter. Anything
    # else (e.g. metaballs, volumes, grease pencil) is dropped silently and only
    # bloats the selection, so we filter at the source.
    _SINGLE_FBX_TYPES = frozenset({
        'MESH', 'ARMATURE', 'EMPTY', 'CURVE', 'SURFACE',
        'META', 'FONT', 'CAMERA', 'LIGHT', 'LATTICE',
    })

    @staticmethod
    def _collect_collection_objects_for_single_fbx(collection):
        """Return every exportable object from `collection` and its descendants.

        Uses `collection.all_objects` so subcollections are included with no
        manual recursion. Order is deterministic for stable debug output.
        """
        return [
            obj for obj in collection.all_objects
            if obj.type in MASSEXPORTER_OT_export_all._SINGLE_FBX_TYPES
        ]

    @staticmethod
    def _center_root_objects_temporarily(objects):
        """Park every export-set root at world (0,0,0) for the export.

        A "root" is an object whose parent is None or whose parent is outside
        the export set. Children inherit their parent's transform, so moving
        only the roots is sufficient — moving a child too would re-apply the
        offset through its parent.

        For a root with no parent, `obj.location` is the world position, so
        zeroing it parks the object at the origin. For a root that has an
        external parent, the local `obj.location` that produces world (0,0,0)
        is `parent.matrix_world.inverted().translation` (parent_world @ that
        local point lands on the world origin).

        Per-object-to-origin (not centroid): multiple roots stack on top of
        each other at origin. Relative positions are intentionally dropped —
        this is the semantic the user requested for grouped exports.

        Returns a backup that `_restore_root_object_locations` will consume.
        """
        if not objects:
            return None
        obj_set = set(objects)
        roots = [
            o for o in objects
            if o.parent is None or o.parent not in obj_set
        ]
        if not roots:
            return None
        backup = [(o, o.location.copy()) for o in roots]
        for o in roots:
            if o.parent is None:
                o.location = mathutils.Vector((0.0, 0.0, 0.0))
            else:
                # Local location whose world projection is (0,0,0).
                o.location = o.parent.matrix_world.inverted().translation
        bpy.context.view_layer.update()
        return backup

    @staticmethod
    def _restore_root_object_locations(backup):
        if not backup:
            return
        for obj, original in backup:
            if obj.name in bpy.data.objects:
                obj.location = original
        bpy.context.view_layer.update()

    def export_collection_as_single_fbx(self, context, props, item):
        """Export the whole collection (meshes + armatures + empties + ...)
        as a single file, preserving hierarchy.

        Mesh armature modifiers stay valid because every referenced rig in
        the collection ships in the same file. External rigs are still
        picked up via `perform_export`'s `_select_associated_rigs` path when
        `export_rig_with_mesh` is enabled globally.
        """
        collection = item.collection
        export_path = item.export_path

        if props.debug_mode:
            print(f"\n=== SINGLE-FBX EXPORT: {collection.name} ===")

        objects = MASSEXPORTER_OT_export_all._collect_collection_objects_for_single_fbx(collection)
        if not objects:
            self.report({'WARNING'}, f"No exportable objects in: {collection.name}")
            return False

        if props.debug_mode:
            print(f"  {len(objects)} objects:")
            for o in objects:
                print(f"    [{o.type}] {o.name}")

        # Resolve filename: custom override (trimmed) falls back to collection name.
        custom = (item.single_fbx_custom_name or "").strip()
        out_name = custom if custom else collection.name

        batch_select_objects(objects, context)

        # Per-collection "Move to Center" — translate root-level objects so
        # their centroid lands at the origin for the export, then restore.
        location_backup = None
        if item.move_to_center:
            location_backup = MASSEXPORTER_OT_export_all._center_root_objects_temporarily(objects)

        try:
            if props.override_materials and props.override_material:
                MASSEXPORTER_OT_export_all.apply_material_overrides(self, objects, props)

            filename = f"{out_name}.{props.export_format.lower()}"
            filepath = os.path.join(export_path, filename)

            if props.debug_mode:
                print(f"  Exporting to: {filepath}")

            return MASSEXPORTER_OT_export_all.perform_export(self, props, filepath)
        finally:
            MASSEXPORTER_OT_export_all._restore_root_object_locations(location_backup)

    def export_with_suffix_grouping(self, context, props, item):
        """
        Export with suffix grouping enabled.
        Groups objects/empties/subcollections by base name and exports them together.
        Example: sm_cube_4x4 and sm_cube_4x4_COL are exported as single file 'sm_cube_4x4.fbx'
        """
        collection = item.collection
        export_path = item.export_path
        success_count = 0

        if props.debug_mode:
            print(f"\n=== SUFFIX GROUPING EXPORT: {collection.name} ===")
            print(f"Enabled suffixes: {[s.suffix for s in props.suffix_items if s.enabled]}")

        # Find all groups based on suffix matching
        groups = find_suffix_groups_in_collection(
            collection,
            props.suffix_items,
            include_subcollections=True,
            debug=props.debug_mode
        )

        if not groups:
            self.report({'WARNING'}, f"No objects found in collection: {collection.name}")
            return False

        if props.debug_mode:
            print(f"\nFound {len(groups)} export group(s):")
            for base_name, group_data in groups.items():
                obj_count = len(group_data['objects'])
                empty_count = len(group_data['empties'])
                coll_count = len(group_data['subcollections'])
                print(f"  '{base_name}': {obj_count} objects, {empty_count} empties, {coll_count} subcollections")

        # Export each group
        for base_name, group_data in groups.items():
            # Collect all mesh objects from this group
            all_meshes = []

            # Add direct objects
            for obj, suffix in group_data['objects']:
                if obj.type == 'MESH':
                    all_meshes.append(obj)

            # Add children from empties
            for empty in group_data['empties']:
                for child in empty.children:
                    if child.type == 'MESH' and child not in all_meshes:
                        all_meshes.append(child)

            # Add objects from subcollections
            for subcoll in group_data['subcollections']:
                for obj in subcoll.all_objects:
                    if obj.type == 'MESH' and obj not in all_meshes:
                        all_meshes.append(obj)

            if not all_meshes:
                if props.debug_mode:
                    print(f"  Skipping '{base_name}' - no mesh objects found")
                continue

            if props.debug_mode:
                print(f"\n  Exporting group '{base_name}' with {len(all_meshes)} mesh(es):")
                for mesh in all_meshes:
                    print(f"    - {mesh.name}")

            # Export this group as a single file
            if MASSEXPORTER_OT_export_all.export_objects_as_single(
                self, context, props, all_meshes, base_name, export_path, item=item
            ):
                success_count += 1
                if props.debug_mode:
                    print(f"  ✓ Successfully exported '{base_name}'")
            else:
                if props.debug_mode:
                    print(f"  ✗ Failed to export '{base_name}'")

        if props.debug_mode:
            print(f"\n=== SUFFIX GROUPING COMPLETE: {success_count}/{len(groups)} groups exported ===")

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
            return MASSEXPORTER_OT_export_all.export_collection_with_all_empties_joined(self, context, props, item, collection, export_path)

        # Original behavior: export each empty separately (without join)
        return MASSEXPORTER_OT_export_all.export_with_empty_origins_individual(self, context, props, item)

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
            objects = MASSEXPORTER_OT_export_all.get_collection_objects(self, collection)
            if objects:
                if item.merge_to_single:
                    return MASSEXPORTER_OT_export_all.export_objects_as_single(self, context, props, objects, collection.name, export_path, item=item)
                else:
                    success_count = 0
                    for obj in objects:
                        if MASSEXPORTER_OT_export_all.export_single_object(self, context, props, obj, export_path, item=item):
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
                    if MASSEXPORTER_OT_export_all.export_children_individual(self, context, props, empty, children, export_path):
                        success_count += 1

                finally:
                    empty.location = original_empty_pos
                    bpy.context.view_layer.update()
            else:
                if MASSEXPORTER_OT_export_all.export_children_individual(self, context, props, empty, children, export_path):
                    success_count += 1

        return success_count > 0

    def export_collection_with_all_empties_joined(self, context, props, item, collection, export_path):
        """
        ========== FIXED v12: Export meshes even when no empties present ==========
        Collects ALL children from ALL empties in the collection, joins them together,
        and exports as ONE file named after the collection.
        FALLBACK: If no empties found, exports meshes in collection normally.
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
        
        # FIXED v12: If no empties found, fallback to normal export of meshes in collection
        if not all_empties:
            if props.debug_mode:
                print("âš  No empties with children found in collection")
                print("âž¡ Falling back to normal export of meshes in collection")
            
            # Get all mesh objects from the collection
            objects = MASSEXPORTER_OT_export_all.get_collection_objects(self, collection)

            if not objects:
                if props.debug_mode:
                    print("âš  No mesh objects found in collection either")
                return False

            if props.debug_mode:
                print(f"✓ Found {len(objects)} mesh objects to export")

            # Export based on merge setting
            if item.merge_to_single:
                return MASSEXPORTER_OT_export_all.export_objects_as_single(self, context, props, objects, collection.name, export_path, item=item)
            else:
                success_count = 0
                for obj in objects:
                    if MASSEXPORTER_OT_export_all.export_single_object(self, context, props, obj, export_path, item=item):
                        success_count += 1
                return success_count > 0
        
        # Continue with normal empty-based export if empties were found
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
            batch_deselect_all(context)
            
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

                    batch_deselect_all(context)
                    dup.select_set(True)
                    context.view_layer.objects.active = dup

                    # Remove disabled modifiers first if apply_only_visible is enabled
                    if item.apply_only_visible:
                        if props.debug_mode:
                            print(f"  Checking for disabled modifiers on {dup.name}...")
                        modifiers_to_remove = []
                        for modifier in dup.modifiers:
                            if not modifier.show_viewport:
                                modifiers_to_remove.append(modifier.name)
                                if props.debug_mode:
                                    print(f"    Marking disabled modifier '{modifier.name}' for removal")

                        # Remove disabled modifiers
                        for mod_name in modifiers_to_remove:
                            dup.modifiers.remove(dup.modifiers[mod_name])
                            if props.debug_mode:
                                print(f"    Removed disabled modifier '{mod_name}' from {dup.name}")

                    # Apply remaining modifiers
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
                
                batch_deselect_all(context)
                
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
            batch_deselect_all(context)
            joined_obj.select_set(True)
            context.view_layer.objects.active = joined_obj
            
            bpy.ops.object.origin_set(type='ORIGIN_CURSOR')
            context.scene.cursor.location = original_cursor
            
            if props.debug_mode:
                print(f"Final joined object location: {joined_obj.location}")
            
            # STEP 7: Export ONLY this ONE joined object
            if props.debug_mode:
                print(f"Exporting joined object as '{collection.name}.fbx'...")

            result = MASSEXPORTER_OT_export_all.export_single_object_simple(self, context, props, joined_obj, collection.name, export_path)

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
            batch_deselect_all(context)
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
            if MASSEXPORTER_OT_export_all.export_single_object_simple(self, context, props, child, child_name, export_path):
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
            batch_select_objects([obj], context)

            # Apply material overrides if needed
            if props.override_materials and props.override_material:
                MASSEXPORTER_OT_export_all.apply_material_overrides(self, [obj], props)

            # Set export filename
            filename = f"{name}.{props.export_format.lower()}"
            filepath = os.path.join(export_path, filename)

            if props.debug_mode:
                print(f"Exporting to: {filepath}")

            # Export based on format
            result = MASSEXPORTER_OT_export_all.perform_export(self, props, filepath)

            if props.debug_mode:
                print(f"Export result: {result}")

            return result

        finally:
            # Restore selection
            batch_deselect_all(context)
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

    def export_objects_as_single(self, context, props, objects, collection_name, export_path, item=None):
        """Export multiple objects as single file.

        Source data must never be altered. Centering (item.move_to_center)
        parks each export-set root at world (0,0,0) and is restored in finally.
        apply_transforms runs on temporary duplicates because transform_apply
        is destructive to mesh vertices. Centering happens BEFORE the duplicate
        so transform_apply bakes the centered position into the exported mesh.
        """
        batch_select_objects(objects, context)

        # Snapshot loc/rot/scale up front so we can restore unconditionally
        # in finally, no matter which option mutated what.
        original_transforms = [
            {
                'name': obj.name,
                'location': obj.location.copy(),
                'rotation': obj.rotation_euler.copy(),
                'scale': obj.scale.copy(),
            }
            for obj in objects
        ]

        # Center BEFORE duplicating so transform_apply bakes the centered
        # world position into the exported mesh (otherwise the duplicate would
        # bake the source's pre-centered position).
        location_backup = None
        if item is not None and item.move_to_center:
            location_backup = MASSEXPORTER_OT_export_all._center_root_objects_temporarily(objects)

        # apply_transforms is destructive (rewrites vertex coords). Push it to
        # temporary mesh duplicates so the source mesh data stays clean.
        xform_copies = []
        xform_originals = []
        xform_original_names = []
        if props.apply_transforms:
            xform_copies, xform_originals, xform_original_names = \
                MASSEXPORTER_OT_export_all._apply_transforms_via_duplicates(context, objects)

        result = False
        try:
            # Apply material overrides to whatever will actually be exported.
            if props.override_materials and props.override_material:
                target_objs = xform_copies if xform_copies else objects
                MASSEXPORTER_OT_export_all.apply_material_overrides(self, target_objs, props)

            filename = f"{collection_name}.{props.export_format.lower()}"
            filepath = os.path.join(export_path, filename)

            result = MASSEXPORTER_OT_export_all.perform_export(self, props, filepath)

        finally:
            # Delete duplicates first so original names are free to be restored.
            if xform_copies:
                MASSEXPORTER_OT_export_all._cleanup_modifier_copies(
                    context, xform_copies, xform_originals, xform_original_names
                )

            # Restore the centering shift (only roots were touched).
            if location_backup is not None:
                MASSEXPORTER_OT_export_all._restore_root_object_locations(location_backup)

            # Always restore the captured loc/rot/scale on source objects.
            # Defense in depth — _restore_root_object_locations only restores
            # location on roots, but this catches any path that touched rot/scale
            # too. Source data must end the export exactly as it started.
            for orig_transform in original_transforms:
                obj = bpy.data.objects.get(orig_transform['name'])
                if obj:
                    obj.location = orig_transform['location']
                    obj.rotation_euler = orig_transform['rotation']
                    obj.scale = orig_transform['scale']

        return result

    def export_single_object(self, context, props, obj, export_path, item=None):
        """Export single object.

        Source data must never be altered. Centering (item.move_to_center)
        parks the object's root at world (0,0,0) and is restored in finally.
        apply_transforms runs on a temporary duplicate because transform_apply
        is destructive to mesh vertices. Centering happens BEFORE the duplicate
        so transform_apply bakes the centered position into the exported mesh.
        """
        batch_select_objects([obj], context)

        original_name = obj.name
        original_location = obj.location.copy()
        original_rotation = obj.rotation_euler.copy()
        original_scale = obj.scale.copy()

        # Center BEFORE duplicating so transform_apply on the duplicate bakes
        # the world (0,0,0) position, not the source's original position.
        location_backup = None
        if item is not None and item.move_to_center:
            location_backup = MASSEXPORTER_OT_export_all._center_root_objects_temporarily([obj])

        # Push destructive apply_transforms onto a temporary duplicate.
        xform_copies = []
        xform_originals = []
        xform_original_names = []
        if props.apply_transforms:
            xform_copies, xform_originals, xform_original_names = \
                MASSEXPORTER_OT_export_all._apply_transforms_via_duplicates(context, [obj])

        result = False
        try:
            if props.override_materials and props.override_material:
                target_obj = xform_copies[0] if xform_copies else obj
                MASSEXPORTER_OT_export_all.apply_material_overrides(self, [target_obj], props)

            # Use the original name for the file even when exporting from a copy.
            filename = f"{original_name}.{props.export_format.lower()}"
            filepath = os.path.join(export_path, filename)

            result = MASSEXPORTER_OT_export_all.perform_export(self, props, filepath)

        finally:
            if xform_copies:
                MASSEXPORTER_OT_export_all._cleanup_modifier_copies(
                    context, xform_copies, xform_originals, xform_original_names
                )

            # Restore the centering shift.
            if location_backup is not None:
                MASSEXPORTER_OT_export_all._restore_root_object_locations(location_backup)

            # Always restore the captured loc/rot/scale on the source object.
            restored = bpy.data.objects.get(original_name)
            if restored:
                restored.location = original_location
                restored.rotation_euler = original_rotation
                restored.scale = original_scale

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

    @staticmethod
    def _apply_modifiers_to_selection(context, objects, skip_armature=False):
        """Apply modifiers non-destructively on temporary copies of mesh objects.
        Swaps the selection so copies replace originals.
        Returns (copies, originals, original_names) for cleanup after export.

        Armature modifiers whose rig is already in the export selection are
        always preserved — baking them would strip the skin binding from the
        FBX even though the rig ships in the same file. `skip_armature` is
        kept as a manual override that suppresses ALL armature modifiers
        regardless of whether the rig is in the selection.
        """
        copies = []
        originals_swapped = []
        original_names = []

        rigs_in_selection = {o for o in objects if o.type == 'ARMATURE'}

        def _should_skip(mod):
            if mod.type != 'ARMATURE':
                return False
            if skip_armature:
                return True
            return mod.object in rigs_in_selection

        for obj in objects:
            if obj.type != 'MESH':
                continue  # armatures/empties: leave in selection as-is

            mods_to_apply = [m for m in obj.modifiers if not _should_skip(m)]
            if not mods_to_apply:
                continue  # nothing to do for this object

            try:
                original_name = obj.name
                # Free the name so the copy can take it cleanly (no .001 suffix)
                obj.name = f"__mexport_{original_name}"

                batch_select_objects([obj], context)
                bpy.ops.object.duplicate(linked=False)
                copy = context.active_object
                copy.name = original_name  # copy now has the clean original name

                for mod in list(copy.modifiers):
                    if _should_skip(mod):
                        continue
                    try:
                        bpy.ops.object.modifier_apply(modifier=mod.name)
                    except Exception as e:
                        print(f"[MassExporter] Could not apply modifier '{mod.name}' on '{obj.name}': {e}")
                        copy.modifiers.remove(mod)

                copies.append(copy)
                originals_swapped.append(obj)
                original_names.append(original_name)
            except Exception as e:
                print(f"[MassExporter] Could not duplicate '{obj.name}' for modifier apply: {e}")
                # Undo temp rename if duplication failed
                if obj.name.startswith("__mexport_"):
                    obj.name = obj.name[len("__mexport_"):]

        # Swap selection: deselect originals that have copies, select copies
        for obj in originals_swapped:
            obj.select_set(False)
        for copy in copies:
            copy.select_set(True)
        # Keep non-mesh / no-modifier / armature objects selected
        for obj in objects:
            if obj not in originals_swapped:
                obj.select_set(True)

        if copies:
            context.view_layer.objects.active = copies[0]
        elif objects:
            still_selected = [o for o in objects if o not in originals_swapped]
            if still_selected:
                context.view_layer.objects.active = still_selected[0]

        return copies, originals_swapped, original_names

    @staticmethod
    def _cleanup_modifier_copies(context, copies, originals, original_names):
        """Delete temporary modifier copies and restore original names and selection."""
        # Delete copies first — originals currently hold temp names, copies hold real names.
        # Deleting copies frees the real names so originals can be renamed back without conflict.
        batch_deselect_all(context)
        for copy in copies:
            if copy.name in bpy.data.objects:
                copy.select_set(True)
        if copies:
            bpy.ops.object.delete()
        # Restore original names now that copies (which held them) are gone
        for obj, orig_name in zip(originals, original_names):
            if obj.name in bpy.data.objects:
                obj.name = orig_name
        # Restore selection
        for obj in originals:
            if obj.name in bpy.data.objects:
                obj.select_set(True)
        if originals and originals[0].name in bpy.data.objects:
            context.view_layer.objects.active = originals[0]

    @staticmethod
    def _apply_transforms_via_duplicates(context, objects):
        """Bake location/rotation/scale into mesh data on temporary copies.

        transform_apply rewrites vertex coordinates in place, so it must never
        run on source meshes. Mirrors _apply_modifiers_to_selection: duplicate
        each mesh, hand the original's name to the copy, bake the transform
        into the copy's mesh data, swap selection to copies. Non-mesh objects
        are left untouched (their transforms are restored unconditionally by
        the caller's finally block).

        Returns (copies, originals, original_names) for cleanup via
        _cleanup_modifier_copies — the cleanup pattern is identical.
        """
        copies = []
        originals_swapped = []
        original_names = []

        for obj in objects:
            if obj.type != 'MESH':
                continue

            try:
                original_name = obj.name
                obj.name = f"__mexport_xform_{original_name}"

                batch_select_objects([obj], context)
                bpy.ops.object.duplicate(linked=False)
                copy = context.active_object
                copy.name = original_name

                # duplicate(linked=False) already unlinks mesh data, but be defensive:
                # if anything else is still sharing it, fork before baking vertices.
                if copy.data and copy.data.users > 1:
                    copy.data = copy.data.copy()

                batch_select_objects([copy], context)
                bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)

                copies.append(copy)
                originals_swapped.append(obj)
                original_names.append(original_name)
            except Exception as e:
                print(f"[MassExporter] Could not duplicate '{obj.name}' for transform apply: {e}")
                if obj.name.startswith("__mexport_xform_"):
                    obj.name = obj.name[len("__mexport_xform_"):]

        # Swap selection: deselect originals that have copies, select copies + passthroughs
        for obj in originals_swapped:
            obj.select_set(False)
        for copy in copies:
            copy.select_set(True)
        for obj in objects:
            if obj not in originals_swapped:
                obj.select_set(True)

        if copies:
            context.view_layer.objects.active = copies[0]
        elif objects:
            still_selected = [o for o in objects if o not in originals_swapped]
            if still_selected:
                context.view_layer.objects.active = still_selected[0]

        return copies, originals_swapped, original_names

    @staticmethod
    def _select_associated_rigs(objects):
        """Select armature objects referenced by Armature modifiers.

        Temporarily links each rig to the scene root collection so
        collection-level hiding cannot block the exporter, clears every
        visibility/selection block on it (object hide flags, hide_select,
        local-view membership in every active 3D viewport), and selects it.
        Returns a backup list for full restoration by _deselect_rigs.

        Mirrors the local-view handling in _unhide_collection_for_export: a
        rig outside the active local view reports hide_get()==True and
        select_set(True) is a silent no-op, which is why armature export
        previously did nothing while in local view.
        """
        backup = []
        seen = set()
        root_coll = bpy.context.scene.collection

        local_view_spaces = []
        wm = getattr(bpy.context, 'window_manager', None)
        if wm is not None:
            for window in wm.windows:
                for area in window.screen.areas:
                    if area.type != 'VIEW_3D':
                        continue
                    for space in area.spaces:
                        if space.type == 'VIEW_3D' and getattr(space, 'local_view', None):
                            local_view_spaces.append(space)

        for obj in objects:
            if obj.type != 'MESH':
                continue
            for mod in obj.modifiers:
                if mod.type != 'ARMATURE' or not mod.object or mod.object.name not in bpy.data.objects:
                    continue
                rig = mod.object
                if rig.name in seen:
                    continue
                seen.add(rig.name)
                entry = {
                    'rig': rig,
                    'was_selected': rig.select_get(),
                    'hide_viewport': rig.hide_viewport,
                    'hide_eye': rig.hide_get(),
                    'in_root': rig.name in root_coll.objects,
                    'hide_select': getattr(rig, 'hide_select', False),
                    'local_view': [],
                }
                # Link to root collection so collection-level visibility cannot hide it
                if not entry['in_root']:
                    root_coll.objects.link(rig)
                # Clear object-level hide flags
                rig.hide_viewport = False
                rig.hide_set(False)
                # Clear selection lock
                try:
                    if rig.hide_select:
                        rig.hide_select = False
                except AttributeError:
                    pass
                # Inject into every active local view so it is selectable
                for space in local_view_spaces:
                    try:
                        was_in_lv = rig.local_view_get(space)
                    except (AttributeError, RuntimeError, TypeError):
                        continue
                    if not was_in_lv:
                        try:
                            rig.local_view_set(space, True)
                            entry['local_view'].append(space)
                        except (AttributeError, RuntimeError, TypeError):
                            continue
                # Flush before select_set so hide_get reflects the flips
                bpy.context.view_layer.update()
                if not entry['was_selected']:
                    rig.select_set(True)
                backup.append(entry)
        return backup

    @staticmethod
    def _deselect_rigs(backup):
        """Restore rig visibility, selection, local-view membership, and collection
        membership from a backup produced by _select_associated_rigs."""
        root_coll = bpy.context.scene.collection
        for entry in backup:
            rig = entry['rig']
            if rig.name not in bpy.data.objects:
                continue
            if not entry['was_selected']:
                try:
                    rig.select_set(False)
                except RuntimeError:
                    pass
            try:
                rig.hide_viewport = entry['hide_viewport']
                rig.hide_set(entry['hide_eye'])
            except (AttributeError, RuntimeError):
                pass
            try:
                rig.hide_select = entry.get('hide_select', False)
            except AttributeError:
                pass
            for space in entry.get('local_view', ()):
                try:
                    rig.local_view_set(space, False)
                except (AttributeError, RuntimeError, TypeError):
                    continue
            if not entry['in_root'] and rig.name in root_coll.objects:
                root_coll.objects.unlink(rig)

    def perform_export(self, props, filepath):
        """Perform the actual export based on format.
        Modifiers are applied via temporary copies so all formats and modifier
        types are handled reliably, independent of exporter flags."""
        initial_selected = [obj for obj in bpy.context.selected_objects]

        # Add rigs FIRST so they are included in the selection passed to modifier apply
        added_rigs = []
        if props.export_rig_with_mesh:
            added_rigs = MASSEXPORTER_OT_export_all._select_associated_rigs(initial_selected)

        # Snapshot full selection now (includes any added rigs)
        selected = [obj for obj in bpy.context.selected_objects]

        # Apply modifiers via temporary copies so the result is guaranteed.
        # Armature objects in the selection are non-mesh and pass through untouched.
        modifier_copies = []
        modifier_originals = []
        modifier_original_names = []
        if props.apply_modifiers:
            modifier_copies, modifier_originals, modifier_original_names = \
                MASSEXPORTER_OT_export_all._apply_modifiers_to_selection(
                    bpy.context, selected, skip_armature=props.skip_armature_modifier
                )

        try:
            if props.export_format == 'FBX':
                bpy.ops.export_scene.fbx(
                    filepath=filepath,
                    use_selection=True,
                    axis_forward=props.axis_forward,
                    axis_up=props.axis_up,
                    apply_scale_options=props.apply_scaling,
                    bake_space_transform=props.bake_space_transform,
                    use_mesh_modifiers=False,
                    primary_bone_axis=props.primary_bone_axis,
                    secondary_bone_axis=props.secondary_bone_axis,
                    armature_nodetype=props.armature_nodetype,
                    use_armature_deform_only=props.use_armature_deform_only,
                    add_leaf_bones=props.add_leaf_bones
                )

            elif props.export_format == 'OBJ':
                bpy.ops.wm.obj_export(
                    filepath=filepath,
                    export_selected_objects=True,
                    forward_axis=props.axis_forward,
                    up_axis=props.axis_up,
                    export_materials=True,
                    apply_modifiers=False
                )

            elif props.export_format == 'DAE':
                bpy.ops.wm.collada_export(
                    filepath=filepath,
                    selected=True,
                    apply_modifiers=False
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

        finally:
            if modifier_copies:
                MASSEXPORTER_OT_export_all._cleanup_modifier_copies(
                    bpy.context, modifier_copies, modifier_originals, modifier_original_names
                )
            if added_rigs:
                MASSEXPORTER_OT_export_all._deselect_rigs(added_rigs)

class MASSEXPORTER_OT_export_selected_collection(Operator):
    """Export collection of currently selected object as a whole"""
    bl_idname = "massexporter.export_selected_collection"
    bl_label = "Export Collection of Selected"
    bl_description = "Export the immediate collection containing the selected object as a whole, using configured export settings (ignores 'Sub-Collections as Single' mode)"

    def find_immediate_collection(self, obj):
        """Find the immediate (lowest-level) collection containing the object"""
        # Start with all collections that contain this object
        containing_collections = []
        for collection in bpy.data.collections:
            if obj.name in collection.objects:
                containing_collections.append(collection)

        if not containing_collections:
            return None

        # If only one collection, return it
        if len(containing_collections) == 1:
            return containing_collections[0]

        # Find the most specific (deepest) collection by checking which collections
        # are children of other collections in the list
        # A collection is "immediate" if it's not a parent of any other collection in the list
        immediate_collection = None
        for coll in containing_collections:
            is_parent = False
            for other_coll in containing_collections:
                if coll != other_coll and self.is_parent_of(coll, other_coll):
                    is_parent = True
                    break

            # If this collection is not a parent of any other, it's more immediate
            if not is_parent:
                immediate_collection = coll
                break

        return immediate_collection if immediate_collection else containing_collections[0]

    def is_parent_of(self, parent_coll, child_coll):
        """Check if parent_coll is a parent (or ancestor) of child_coll"""
        # Check direct children by comparing collection objects
        for child in parent_coll.children:
            if child == child_coll:
                return True

        # Check recursively through all descendants
        for child in parent_coll.children:
            if self.is_parent_of(child, child_coll):
                return True

        return False

    def execute(self, context):
        # Force OBJECT mode
        if bpy.ops.object.mode_set.poll():
            bpy.ops.object.mode_set(mode='OBJECT')

        # Get active object
        active_obj = context.active_object
        if not active_obj:
            self.report({'WARNING'}, "No object selected")
            return {'CANCELLED'}

        # Find the immediate collection containing this object
        target_collection = self.find_immediate_collection(active_obj)

        if not target_collection:
            self.report({'WARNING'}, f"Object '{active_obj.name}' is not in any collection")
            return {'CANCELLED'}

        # Find or create export item for this collection
        props = context.scene.mass_exporter_props
        export_item = None
        for item in props.collection_items:
            if item.collection == target_collection:
                export_item = item
                break

        # If not in export list, we need an export path from somewhere
        if not export_item:
            # Try to find a parent collection in the export list and use its settings
            parent_export_item = self.find_parent_export_item(target_collection, props)

            if not parent_export_item:
                self.report({'WARNING'}, f"Collection '{target_collection.name}' is not in export list and no parent collection found")
                return {'CANCELLED'}

            if not parent_export_item.export_path:
                self.report({'WARNING'}, f"No export path set for collection hierarchy")
                return {'CANCELLED'}

            # Create temporary export item with parent's settings
            export_item = props.collection_items.add()
            export_item.collection = target_collection
            export_item.export_enabled = True
            export_item.export_path = parent_export_item.export_path
            export_item.merge_to_single = parent_export_item.merge_to_single
            export_item.export_subcollections_as_single = parent_export_item.export_subcollections_as_single
            export_item.use_empty_origins = parent_export_item.use_empty_origins
            export_item.center_parent_empties = parent_export_item.center_parent_empties
            export_item.move_empties_to_origin_on_export = parent_export_item.move_empties_to_origin_on_export
            export_item.join_empty_children = parent_export_item.join_empty_children
            export_item.apply_modifiers_before_join = parent_export_item.apply_modifiers_before_join
            export_item.apply_only_visible = parent_export_item.apply_only_visible

            temp_created = True
        else:
            if not export_item.export_path:
                self.report({'WARNING'}, f"No export path set for collection '{target_collection.name}'")
                return {'CANCELLED'}
            temp_created = False

        # Store original selection
        original_selection = context.selected_objects.copy()
        original_active = context.active_object

        try:
            # Export this collection using the existing export logic
            # Temporarily disable export_subcollections_as_single to export the collection as a whole
            original_export_subcollections = export_item.export_subcollections_as_single
            export_item.export_subcollections_as_single = False

            # Call the method as an unbound method from the class
            if MASSEXPORTER_OT_export_all.export_collection(self, context, props, export_item):
                self.report({'INFO'}, f"Exported collection '{target_collection.name}'")
                result = {'FINISHED'}
            else:
                self.report({'ERROR'}, f"Failed to export collection '{target_collection.name}'")
                result = {'CANCELLED'}

            # Restore original setting if not temp_created
            if not temp_created:
                export_item.export_subcollections_as_single = original_export_subcollections

            return result
        finally:
            # Remove temporary item if created
            if temp_created:
                index = len(props.collection_items) - 1
                props.collection_items.remove(index)

            # Restore selection
            batch_deselect_all(context)
            for obj in original_selection:
                if obj.name in bpy.data.objects:
                    obj.select_set(True)
            if original_active and original_active.name in bpy.data.objects:
                context.view_layer.objects.active = original_active

    def find_parent_export_item(self, collection, props):
        """Find a parent collection in the export list"""
        for item in props.collection_items:
            if item.collection and self.is_parent_of(item.collection, collection):
                return item
        return None

class MASSEXPORTER_OT_export_selected_subcollections(Operator):
    """Export sub-collections of currently selected object's collection"""
    bl_idname = "massexporter.export_selected_subcollections"
    bl_label = "Export Sub-Collections of Selected"
    bl_description = "Export each sub-collection of the collection containing the selected object, using the collection's configured export settings"

    def find_immediate_collection(self, obj):
        """Find the immediate (lowest-level) collection containing the object"""
        # Start with all collections that contain this object
        containing_collections = []
        for collection in bpy.data.collections:
            if obj.name in collection.objects:
                containing_collections.append(collection)

        if not containing_collections:
            return None

        # If only one collection, return it
        if len(containing_collections) == 1:
            return containing_collections[0]

        # Find the most specific (deepest) collection by checking which collections
        # are children of other collections in the list
        # A collection is "immediate" if it's not a parent of any other collection in the list
        immediate_collection = None
        for coll in containing_collections:
            is_parent = False
            for other_coll in containing_collections:
                if coll != other_coll and self.is_parent_of(coll, other_coll):
                    is_parent = True
                    break

            # If this collection is not a parent of any other, it's more immediate
            if not is_parent:
                immediate_collection = coll
                break

        return immediate_collection if immediate_collection else containing_collections[0]

    def is_parent_of(self, parent_coll, child_coll):
        """Check if parent_coll is a parent (or ancestor) of child_coll"""
        # Check direct children by comparing collection objects
        for child in parent_coll.children:
            if child == child_coll:
                return True

        # Check recursively through all descendants
        for child in parent_coll.children:
            if self.is_parent_of(child, child_coll):
                return True

        return False

    def find_parent_export_item(self, collection, props):
        """Find a parent collection in the export list"""
        for item in props.collection_items:
            if item.collection and self.is_parent_of(item.collection, collection):
                return item
        return None

    def execute(self, context):
        # Force OBJECT mode
        if bpy.ops.object.mode_set.poll():
            bpy.ops.object.mode_set(mode='OBJECT')

        # Get active object
        active_obj = context.active_object
        if not active_obj:
            self.report({'WARNING'}, "No object selected")
            return {'CANCELLED'}

        # Find the immediate collection containing this object
        target_collection = self.find_immediate_collection(active_obj)

        if not target_collection:
            self.report({'WARNING'}, f"Object '{active_obj.name}' is not in any collection")
            return {'CANCELLED'}

        # Check if collection has sub-collections
        if not target_collection.children:
            self.report({'WARNING'}, f"Collection '{target_collection.name}' has no sub-collections")
            return {'CANCELLED'}

        # Find or get export settings
        props = context.scene.mass_exporter_props
        export_item = None
        for item in props.collection_items:
            if item.collection == target_collection:
                export_item = item
                break

        # If not in export list, try to find parent collection settings
        if not export_item:
            parent_export_item = self.find_parent_export_item(target_collection, props)

            if not parent_export_item:
                self.report({'WARNING'}, f"Collection '{target_collection.name}' is not in export list and no parent collection found")
                return {'CANCELLED'}

            if not parent_export_item.export_path:
                self.report({'WARNING'}, f"No export path set for collection hierarchy")
                return {'CANCELLED'}

            # Use parent's settings as reference
            reference_item = parent_export_item
        else:
            if not export_item.export_path:
                self.report({'WARNING'}, f"No export path set for collection '{target_collection.name}'")
                return {'CANCELLED'}
            reference_item = export_item

        # Store original selection
        original_selection = context.selected_objects.copy()
        original_active = context.active_object

        try:
            # Export each sub-collection
            exported_count = 0
            temp_items_created = []

            for sub_collection in target_collection.children:
                # Create a temporary export item for this sub-collection
                temp_item = props.collection_items.add()
                temp_item.collection = sub_collection
                temp_item.export_enabled = True
                temp_item.export_path = reference_item.export_path
                temp_item.merge_to_single = reference_item.merge_to_single
                temp_item.export_subcollections_as_single = reference_item.export_subcollections_as_single
                temp_item.use_empty_origins = reference_item.use_empty_origins
                temp_item.center_parent_empties = reference_item.center_parent_empties
                temp_item.move_empties_to_origin_on_export = reference_item.move_empties_to_origin_on_export
                temp_item.join_empty_children = reference_item.join_empty_children
                temp_item.apply_modifiers_before_join = reference_item.apply_modifiers_before_join
                temp_item.apply_only_visible = reference_item.apply_only_visible

                temp_items_created.append(len(props.collection_items) - 1)

                # Call the method as an unbound method from the class
                if MASSEXPORTER_OT_export_all.export_collection(self, context, props, temp_item):
                    exported_count += 1

            # Remove temporary items in reverse order
            for index in reversed(temp_items_created):
                props.collection_items.remove(index)

            if exported_count > 0:
                self.report({'INFO'}, f"Exported {exported_count} sub-collections from '{target_collection.name}'")
                return {'FINISHED'}
            else:
                self.report({'ERROR'}, "No sub-collections were exported")
                return {'CANCELLED'}
        finally:
            # Restore selection
            batch_deselect_all(context)
            for obj in original_selection:
                if obj.name in bpy.data.objects:
                    obj.select_set(True)
            if original_active and original_active.name in bpy.data.objects:
                context.view_layer.objects.active = original_active

# Panels
class MASSEXPORTER_OT_export_selected_objects(Operator):
    """Export collections of selected objects using their configured export settings"""
    bl_idname = "massexporter.export_selected_objects"
    bl_label = "Export Selected Object(s)"
    bl_description = "Export the collections containing selected objects, using each collection's configured export settings (merge, sub-collections, etc.)"

    def find_immediate_collection(self, obj):
        """Find the immediate (lowest-level) collection containing the object"""
        # Start with all collections that contain this object
        containing_collections = []
        for collection in bpy.data.collections:
            if obj.name in collection.objects:
                containing_collections.append(collection)

        if not containing_collections:
            return None

        # If only one collection, return it
        if len(containing_collections) == 1:
            return containing_collections[0]

        # Find the most specific (deepest) collection
        immediate_collection = None
        for coll in containing_collections:
            is_parent = False
            for other_coll in containing_collections:
                if coll != other_coll and self.is_parent_of(coll, other_coll):
                    is_parent = True
                    break

            if not is_parent:
                immediate_collection = coll
                break

        return immediate_collection if immediate_collection else containing_collections[0]

    def is_parent_of(self, parent_coll, child_coll):
        """Check if parent_coll is a parent (or ancestor) of child_coll"""
        for child in parent_coll.children:
            if child == child_coll:
                return True

        for child in parent_coll.children:
            if self.is_parent_of(child, child_coll):
                return True

        return False

    def find_parent_export_item(self, collection, props):
        """Find a parent collection in the export list"""
        for item in props.collection_items:
            if item.collection and self.is_parent_of(item.collection, collection):
                return item
        return None


    def find_parent_collection(self, collection):
        """Find the direct parent collection of the given collection"""
        for coll in bpy.data.collections:
            if collection.name in coll.children:
                return coll
        return None

    def execute(self, context):
        """Export ONLY the selected objects, not entire collections.

        Wrapped in a single try/finally so every exit path (early warning
        returns, exceptions mid-export, successful completion) restores the
        original selection and active object. Previously, early returns
        skipped cleanup, which could leave the scene in a partially-modified
        state that made subsequent `Export All` calls hang.
        """
        # Snapshot state BEFORE touching the scene so cleanup can always run.
        original_selection = context.selected_objects.copy()
        original_active = context.active_object

        # Force OBJECT mode
        if bpy.ops.object.mode_set.poll():
            bpy.ops.object.mode_set(mode='OBJECT')

        props = context.scene.mass_exporter_props
        exported_count = 0
        cancelled = False

        try:
            # Get selected mesh objects
            selected_objects = [obj for obj in context.selected_objects if obj.type == 'MESH']
            if not selected_objects:
                self.report({'WARNING'}, "No mesh objects selected")
                cancelled = True
                return {'CANCELLED'}

            # Group selected objects by their immediate collection
            collection_groups = {}
            for obj in selected_objects:
                coll = self.find_immediate_collection(obj)
                if coll:
                    collection_groups.setdefault(coll, []).append(obj)

            if not collection_groups:
                self.report({'WARNING'}, "Selected objects are not in any collections")
                cancelled = True
                return {'CANCELLED'}

            # Export each collection group
            for collection, objects in collection_groups.items():
                # Find export item for this collection or its parent
                export_item = None
                for item in props.collection_items:
                    if item.collection == collection:
                        export_item = item
                        break

                # If not found, check parent collections
                if not export_item:
                    parent_export_item = self.find_parent_export_item(collection, props)
                    if not parent_export_item:
                        self.report({'WARNING'}, f"Collection '{collection.name}' not in export list - skipping")
                        continue
                    export_item = parent_export_item

                if not export_item.export_path:
                    self.report({'WARNING'}, f"No export path for collection '{collection.name}' - skipping")
                    continue

                # Respect the same hidden-collection gating the main Export All
                # path uses, so behavior is consistent across entry points.
                is_hidden = MASSEXPORTER_OT_export_all._collection_is_hidden(collection)
                if is_hidden and not props.export_hidden_collections:
                    self.report({'WARNING'},
                                f"Skipping '{collection.name}' — it is hidden and "
                                "'Export Hidden Collections' is off")
                    continue

                # Drive every path through the unhide pipeline so a hidden
                # parent, a sibling-excluded layer collection, or local view
                # cannot silently produce an empty export. Restore is
                # guaranteed in finally, which in turn means two consecutive
                # exports leave the scene in identical state.
                visibility_backup = MASSEXPORTER_OT_export_all._unhide_collection_for_export(collection)
                try:
                    # Check if this is a subcollection and should be exported as a whole
                    parent_coll = self.find_parent_collection(collection)
                    parent_item = None
                    if parent_coll:
                        for item in props.collection_items:
                            if item.collection == parent_coll:
                                parent_item = item
                                break

                    # If parent has "export subcollections as single" enabled, export entire subcollection
                    if parent_item and parent_item.export_subcollections_as_single:
                        if props.debug_mode:
                            print(f"Exporting entire subcollection '{collection.name}' (parent has subcollections-as-single enabled)")
                        sub_objects = MASSEXPORTER_OT_export_all.get_collection_objects(self, collection)
                        if MASSEXPORTER_OT_export_all.export_objects_as_single(
                                self, context, props, sub_objects, collection.name, export_item.export_path, item=export_item):
                            exported_count += 1
                    else:
                        if props.debug_mode:
                            print(f"Exporting {len(objects)} selected objects from '{collection.name}'")
                        if len(objects) == 1:
                            if MASSEXPORTER_OT_export_all.export_single_object(
                                    self, context, props, objects[0], export_item.export_path, item=export_item):
                                exported_count += 1
                        else:
                            group_name = f"{collection.name}_selected"
                            if MASSEXPORTER_OT_export_all.export_objects_as_single(
                                    self, context, props, objects, group_name, export_item.export_path, item=export_item):
                                exported_count += 1
                finally:
                    MASSEXPORTER_OT_export_all._restore_collection_for_export(visibility_backup)

            if exported_count > 0:
                self.report({'INFO'}, f"Exported {exported_count} object(s)")
                return {'FINISHED'}
            self.report({'ERROR'}, "No objects were exported")
            cancelled = True
            return {'CANCELLED'}

        finally:
            # Always restore selection + active, even on early warning returns.
            # This prevents leaked `__mexport_*` renames from partial runs from
            # breaking the next export.
            batch_deselect_all(context)
            for obj in original_selection:
                if obj.name in bpy.data.objects:
                    obj.select_set(True)
            if original_active and original_active.name in bpy.data.objects:
                context.view_layer.objects.active = original_active
            # Double-check: if anything left a `__mexport_*` rename behind,
            # undo it now so the next export starts clean.
            for o in bpy.data.objects:
                if o.name.startswith("__mexport_"):
                    clean = o.name[len("__mexport_"):]
                    if clean not in bpy.data.objects:
                        o.name = clean


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
        layout.prop(props, "export_hidden_collections")

        layout.separator()

        # Quick export from selection — foldable so people can collapse it
        # once they've muscle-memoried the buttons.
        header, body = layout.panel("massexporter_main_quick_export", default_closed=False)
        header.label(text="Quick Export from Selection", icon='RESTRICT_SELECT_OFF')
        if body is not None:
            row = body.row()
            row.scale_y = 1.2
            row.operator("massexporter.export_selected_objects", icon='OBJECT_DATA')
            row = body.row()
            row.scale_y = 1.2
            row.operator("massexporter.export_selected_collection", icon='OUTLINER_COLLECTION')
            row = body.row()
            row.scale_y = 1.2
            row.operator("massexporter.export_selected_subcollections", icon='OUTLINER_OB_GROUP_INSTANCE')

        layout.separator()

        # Debug mode
        layout.prop(props, "debug_mode")

class MASSEXPORTER_PT_debug(Panel):
    """Debug Controls Panel"""
    bl_label = "Debug Controls"
    bl_idname = "MASSEXPORTER_PT_debug"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Mass Exporter"
    bl_parent_id = "MASSEXPORTER_PT_main_panel"
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        layout = self.layout

        # Move empties button
        row = layout.row()
        row.scale_y = 1.2
        row.operator("massexporter.move_empties_to_origin", text="Move Empties to Origin", icon='OUTLINER_OB_EMPTY')

        # Join empties button
        row = layout.row()
        row.scale_y = 1.2
        row.operator("massexporter.join_empties", text="Join Empties (Preview)", icon='MOD_SOLIDIFY')

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

            # Whole-collection-as-one-file — when on, this overrides the other
            # per-collection modes (suffix grouping / subcollection split /
            # empty origins). UI greys those out so the precedence is visible.
            single_box = layout.box()
            single_box.prop(active_item, "export_as_single_fbx")
            if active_item.export_as_single_fbx:
                sub = single_box.column(align=True)
                sub.prop(active_item, "single_fbx_custom_name", text="Filename")
                if not (active_item.single_fbx_custom_name or "").strip():
                    info = single_box.row()
                    info.label(text=f"Falls back to: {active_item.collection.name if active_item.collection else '<collection name>'}", icon='INFO')
                single_box.label(text="Includes meshes, armatures, empties, curves, etc.", icon='ARMATURE_DATA')

            sub_modes = layout.column()
            sub_modes.enabled = not active_item.export_as_single_fbx
            # Order mirrors export precedence: suffix grouping > subcollections > empty origins.
            sub_modes.prop(active_item, "use_suffix_grouping")
            sub_modes.prop(active_item, "export_subcollections_as_single")
            sub_modes.prop(active_item, "use_empty_origins")

            if active_item.use_empty_origins:
                header, body = sub_modes.panel("massexporter_collections_empty_options", default_closed=False)
                header.label(text="Empty Options", icon='EMPTY_ARROWS')
                if body is not None:
                    body.prop(active_item, "center_parent_empties")
                    body.prop(active_item, "move_empties_to_origin_on_export")

                header, body = sub_modes.panel("massexporter_collections_join_options", default_closed=True)
                header.label(text="Join Options", icon='MOD_SOLIDIFY')
                if body is not None:
                    body.prop(active_item, "join_empty_children")
                    if active_item.join_empty_children:
                        body.prop(active_item, "apply_modifiers_before_join")
                        if active_item.apply_modifiers_before_join:
                            body.prop(active_item, "apply_only_visible")

            # Per-collection move-to-center applies to whole-collection-as-one-file
            # too, so it lives outside the sub_modes gating.
            layout.separator()
            layout.prop(active_item, "move_to_center")

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

        layout.prop(props, "apply_transforms")
        layout.label(text="(centering is per-collection via 'Move to Center')", icon='INFO')

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
            header, body = layout.panel("massexporter_export_fbx_options", default_closed=False)
            header.label(text="FBX Options", icon='EXPORT')
            if body is not None:
                body.prop(props, "apply_scaling")
                body.prop(props, "bake_space_transform")

                body.separator()
                body.label(text="Axis Orientation:")
                row = body.row()
                row.prop(props, "axis_forward", text="Forward")
                row.prop(props, "axis_up", text="Up")

                body.separator()
                body.label(text="Armature:", icon='ARMATURE_DATA')
                row = body.row()
                row.prop(props, "primary_bone_axis", text="Primary")
                row = body.row()
                row.prop(props, "secondary_bone_axis", text="Secondary")
                body.prop(props, "armature_nodetype")
                body.prop(props, "use_armature_deform_only")
                body.prop(props, "add_leaf_bones")

            header, body = layout.panel("massexporter_export_unity_tips", default_closed=True)
            header.label(text="Unity Import Tips", icon='INFO')
            if body is not None:
                body.label(text="• Apply Scaling: Use 'FBX Units Scale'")
                body.label(text="• Apply Transform: Enable for clean imports")
                body.label(text="• Default: -Z Forward, Y Up for Unity")


class MASSEXPORTER_PT_modifier_rig(Panel):
    """Modifier & Rig Options Panel

    Houses options that affect modifier evaluation and rig/armature handling
    during export — the animation-adjacent settings that used to live at the
    bottom of File Export Options.
    """
    bl_label = "Modifier & Rig Options"
    bl_idname = "MASSEXPORTER_PT_modifier_rig"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Mass Exporter"
    bl_parent_id = "MASSEXPORTER_PT_main_panel"

    def draw(self, context):
        layout = self.layout
        props = context.scene.mass_exporter_props

        header, body = layout.panel("massexporter_modrig_modifiers", default_closed=False)
        header.label(text="Modifiers", icon='MODIFIER')
        if body is not None:
            body.prop(props, "apply_modifiers")

        header, body = layout.panel("massexporter_modrig_armature", default_closed=False)
        header.label(text="Rig / Armature", icon='ARMATURE_DATA')
        if body is not None:
            body.prop(props, "export_rig_with_mesh")
            sub = body.row()
            sub.enabled = props.apply_modifiers
            sub.prop(props, "skip_armature_modifier")


class MASSEXPORTER_PT_suffix_grouping(Panel):
    """Suffix Grouping Panel"""
    bl_label = "Suffix Grouping"
    bl_idname = "MASSEXPORTER_PT_suffix_grouping"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Mass Exporter"
    bl_parent_id = "MASSEXPORTER_PT_main_panel"

    def draw(self, context):
        layout = self.layout
        props = context.scene.mass_exporter_props

        header, body = layout.panel("massexporter_suffix_about", default_closed=True)
        header.label(text="About Suffix Grouping", icon='INFO')
        if body is not None:
            body.label(text="Group objects by base name + suffix")
            body.label(text="Example: cube + cube_COL = cube.fbx")

        # Suffix list with add/remove buttons
        row = layout.row()
        row.template_list("MASSEXPORTER_UL_suffixes", "", props, "suffix_items",
                         props, "active_suffix_index", rows=4)

        col = row.column(align=True)
        col.operator("massexporter.add_suffix", icon='ADD', text="")
        col.operator("massexporter.remove_suffix", icon='REMOVE', text="")

        # Show description for active suffix
        if props.suffix_items and len(props.suffix_items) > props.active_suffix_index:
            active_suffix = props.suffix_items[props.active_suffix_index]
            layout.separator()
            box = layout.box()
            box.label(text=f"Description: {active_suffix.description}", icon='TEXT')

        layout.separator()

        # Add default suffixes button
        layout.operator("massexporter.add_default_suffixes",
                       text="Add Default Suffixes",
                       icon='PRESET')

# Registration
classes = [
    # Property Groups (must be registered first)
    SuffixItem,
    CollectionExportItem,
    MassExporterProperties,

    # UI Lists
    MASSEXPORTER_UL_collections,
    MASSEXPORTER_UL_suffixes,

    # Operators
    MASSEXPORTER_OT_move_empties_to_origin,
    MASSEXPORTER_OT_join_empties,
    MASSEXPORTER_OT_add_collection,
    MASSEXPORTER_OT_remove_collection,
    MASSEXPORTER_OT_toggle_collection_visibility,
    MASSEXPORTER_OT_select_folder,
    MASSEXPORTER_OT_refresh_collections,
    MASSEXPORTER_OT_add_suffix,
    MASSEXPORTER_OT_remove_suffix,
    MASSEXPORTER_OT_add_default_suffixes,
    MASSEXPORTER_OT_export_all,
    MASSEXPORTER_OT_export_selected_collection,
    MASSEXPORTER_OT_export_selected_subcollections,
    MASSEXPORTER_OT_export_selected_objects,

    # Panels — registration order determines the vertical order of
    # sub-panels under the main panel in the N-Panel.
    MASSEXPORTER_PT_main_panel,
    MASSEXPORTER_PT_collections,
    MASSEXPORTER_PT_transform,
    MASSEXPORTER_PT_materials,
    MASSEXPORTER_PT_modifier_rig,
    MASSEXPORTER_PT_export,
    MASSEXPORTER_PT_suffix_grouping,
    MASSEXPORTER_PT_debug,
]

def _draw_viewport_header_export_all(self, context):
    """Small 'Export All' button in the 3D Viewport header.

    Sits at the right end of the header (appended after the stock
    Selectability/Visibility/Gizmo/Overlay toggles). Greyed out when no
    collection is enabled for export so the click surfaces the reason via
    tooltip rather than running a no-op.
    """
    scene = getattr(context, 'scene', None)
    props = getattr(scene, 'mass_exporter_props', None) if scene else None
    if props is None:
        return
    enabled_count = sum(
        1 for item in props.collection_items
        if item.export_enabled and item.collection is not None
    )
    layout = self.layout
    row = layout.row(align=True)
    row.separator()
    sub = row.row(align=True)
    sub.enabled = enabled_count > 0
    sub.operator("massexporter.export_all", text="", icon='EXPORT')


def register():
    for cls in classes:
        bpy.utils.register_class(cls)

    bpy.types.Scene.mass_exporter_props = PointerProperty(type=MassExporterProperties)
    bpy.types.VIEW3D_HT_header.append(_draw_viewport_header_export_all)

def unregister():
    try:
        bpy.types.VIEW3D_HT_header.remove(_draw_viewport_header_export_all)
    except (ValueError, AttributeError):
        pass

    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)

    del bpy.types.Scene.mass_exporter_props

if __name__ == "__main__":
    register()
