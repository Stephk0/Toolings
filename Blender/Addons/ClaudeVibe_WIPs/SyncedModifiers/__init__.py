bl_info = {
    "name": "Synced Modifiers",
    "author": "Amandeep, Stephko",
    "description": "Add modifiers to multiple objects and sync them using Drivers (now with Geometry Nodes support!)",
    "blender": (2, 91, 0),
    "version": (2, 5, 0),
    "location": "N-Panel > Item > Synced Modifiers",
    "warning": "",
    "category": "Object",
}

# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTIBILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.
##Made by Amandeep
import bpy
import os
import inspect
import re as regex
import uuid
import hashlib
from .properties_data_modifiers import *

# ============================================================================
# Sync ID and Source Modifier Helpers
# ============================================================================

SOURCE_SUFFIX_PATTERN = regex.compile(r'\s*\(Source(?::([a-zA-Z0-9]+))?\)$')

def generate_sync_id():
    """Generate a short unique sync ID for identifying linked modifiers"""
    return hashlib.md5(uuid.uuid4().bytes).hexdigest()[:6]

def get_source_suffix(sync_id=None):
    """Get the source suffix string"""
    if sync_id:
        return f" (Source:{sync_id})"
    return " (Source)"

def parse_source_suffix(modifier_name):
    """Parse the source suffix from modifier name. Returns (base_name, sync_id) or (name, None) if not source"""
    match = SOURCE_SUFFIX_PATTERN.search(modifier_name)
    if match:
        base_name = modifier_name[:match.start()]
        sync_id = match.group(1)  # May be None for old "(Source)" format
        return base_name, sync_id
    return modifier_name, None

def is_source_modifier(modifier_name):
    """Check if modifier name indicates it's a source modifier"""
    return SOURCE_SUFFIX_PATTERN.search(modifier_name) is not None

def get_source_object_and_modifier(obj, modifier):
    """
    Find the source object and modifier for a synced modifier.
    Returns (source_object, source_modifier, sync_id) or (None, None, None) if not synced.
    """
    if not obj.animation_data or not obj.animation_data.drivers:
        # Check if this IS the source
        if is_source_modifier(modifier.name):
            _, sync_id = parse_source_suffix(modifier.name)
            return obj, modifier, sync_id
        return None, None, None

    # Look for drivers on this modifier
    for driver in obj.animation_data.drivers:
        if f'modifiers["{modifier.name}"]' in driver.data_path:
            # Found a driver - get the source
            try:
                var = driver.driver.variables[0]
                source_obj = var.targets[0].id
                source_path = var.targets[0].data_path
                # Extract modifier name from path like 'modifiers["ModName"]["Input_2"]'
                mod_match = regex.search(r'modifiers\["([^"]+)"\]', source_path)
                if mod_match and source_obj:
                    source_mod_name = mod_match.group(1)
                    if source_mod_name in [m.name for m in source_obj.modifiers]:
                        source_mod = source_obj.modifiers[source_mod_name]
                        _, sync_id = parse_source_suffix(source_mod_name)
                        return source_obj, source_mod, sync_id
            except (IndexError, AttributeError):
                pass
            break

    return None, None, None

def find_synced_modifiers_by_sync_id(sync_id, node_group=None):
    """Find all modifiers that share a sync ID"""
    results = []
    if not sync_id:
        return results

    for obj in bpy.data.objects:
        for mod in obj.modifiers:
            # Check if this is the source with matching sync ID
            _, mod_sync_id = parse_source_suffix(mod.name)
            if mod_sync_id == sync_id:
                results.append((obj, mod, True))  # True = is source
                continue

            # Check if it's driven by a source with this sync ID
            if obj.animation_data and obj.animation_data.drivers:
                for driver in obj.animation_data.drivers:
                    if f'modifiers["{mod.name}"]' in driver.data_path:
                        try:
                            var = driver.driver.variables[0]
                            source_path = var.targets[0].data_path
                            if f"(Source:{sync_id})" in source_path:
                                results.append((obj, mod, False))  # False = is target
                                break
                        except (IndexError, AttributeError):
                            pass

    return results

def force_modifier_update(obj, modifier):
    """Force viewport update for a modifier by toggling its display"""
    if modifier and modifier.name in [m.name for m in obj.modifiers]:
        original_show = modifier.show_viewport
        modifier.show_viewport = not original_show
        modifier.show_viewport = original_show

def force_object_update(obj):
    """Force an object update using depsgraph"""
    obj.update_tag()
    if bpy.context.view_layer:
        bpy.context.view_layer.update()
def get_collection(name):
    if name not in bpy.data.collections:
        bpy.data.collections.new(name)
        col = bpy.data.collections[name]
        bpy.context.scene.collection.children.link(col)
        return col
    return bpy.data.collections[name]
def link_to_collection(obj, col):
    
        if isinstance(col, str):
            if col in bpy.data.collections:
                bpy.data.collections[col].objects.link(obj)
        else:
            if col.name in bpy.data.collections:
                col.objects.link(obj)
def move_to_collection(obj, col):
    if col not in bpy.data.collections:
        bpy.data.collections.new(col)
        col = bpy.data.collections[col]
        bpy.context.scene.collection.children.link(col)
    else:
        col=bpy.data.collections[col]

    cols = obj.users_collection
    for c in cols:
        c.objects.unlink(obj)
    link_to_collection(obj, col)
def deselect_all():
    if bpy.context.mode=='OBJECT':
        bpy.ops.object.select_all( action='DESELECT')
    elif 'EDIT' in bpy.context.mode:
        bpy.ops.mesh.select_all( action='DESELECT')
def delete_object_with_data(obj):
    if obj and obj.name in bpy.data.objects:
        data=obj.data
        isMesh=obj.type=='MESH'
        bpy.data.objects.remove(obj, do_unlink=True)
        if isMesh:
            bpy.data.meshes.remove(data)
def delete_collection(col, delete_objects = False):
    colref = None
    if isinstance(col, str):
            colref = get_collection(col)
    else:
        colref = col

    if delete_objects:
        deselect_all()
        if len(colref.objects) > 0:
            for co in colref.objects:
                delete_object_with_data(co)
                #co.select_set(True)
            #delete_selected_objects()
    else:
        deselect_all()
        if len(colref.objects) > 0:
            for co in colref.objects:
                bpy.context.scene.collection.objects.link(co)

    bpy.data.collections.remove(colref)
def recurLayerCollection(layerColl, collName):
    found = None
    if (layerColl.name == collName):
        return layerColl
    for layer in layerColl.children:
        found = recurLayerCollection(layer, collName)
        if found:
            return found
def select(obj,active=True):
    try:
        if obj:
            obj.select_set(True)
            if active:
                bpy.context.view_layer.objects.active = obj
    except:
        pass
def preferences():
    return bpy.context.preferences.addons[__package__].preferences

# ============================================================================
# Geometry Nodes Support Functions
# ============================================================================

def is_geometry_nodes_modifier(mod):
    """Check if modifier is a Geometry Nodes modifier"""
    return mod.type == 'NODES' and mod.node_group is not None

def get_geonode_input_sockets(node_group):
    """
    Get all input sockets from a geometry node group.
    Returns list of dicts with: identifier, name, socket_type, bl_socket_idname
    """
    if node_group is None:
        return []

    sockets = []
    try:
        for item in node_group.interface.items_tree:
            if hasattr(item, 'identifier') and hasattr(item, 'in_out'):
                if item.in_out == 'INPUT':
                    sockets.append({
                        'identifier': item.identifier,
                        'name': item.name,
                        'socket_type': item.socket_type if hasattr(item, 'socket_type') else 'VALUE',
                        'bl_socket_idname': item.bl_socket_idname
                    })
    except AttributeError:
        # Blender version might not support interface.items_tree
        pass

    return sockets

def is_drivable_socket_type(bl_socket_idname):
    """Check if a socket type can be driven"""
    drivable_types = [
        'NodeSocketFloat',
        'NodeSocketInt',
        'NodeSocketBool',
        'NodeSocketVector',
        'NodeSocketColor',
        'NodeSocketRotation',
        'NodeSocketFloatFactor',
        'NodeSocketFloatAngle',
        'NodeSocketFloatDistance',
        'NodeSocketFloatTime',
        'NodeSocketIntFactor',
        'NodeSocketIntUnsigned',
        'NodeSocketVectorTranslation',
        'NodeSocketVectorDirection',
        'NodeSocketVectorVelocity',
        'NodeSocketVectorAcceleration',
        'NodeSocketMenu',  # Menu/enum sockets (store string identifiers)
        'NodeSocketString',  # String sockets
    ]
    return bl_socket_idname in drivable_types

def is_reference_socket_type(bl_socket_idname):
    """Check if socket type is a data-block reference"""
    reference_types = [
        'NodeSocketObject',
        'NodeSocketCollection',
        'NodeSocketMaterial',
        'NodeSocketImage',
        'NodeSocketTexture',
    ]
    return bl_socket_idname in reference_types

def get_socket_component_count(bl_socket_idname):
    """Get number of components for vector-like types"""
    if bl_socket_idname in ['NodeSocketVector', 'NodeSocketColor',
                            'NodeSocketVectorTranslation', 'NodeSocketVectorDirection',
                            'NodeSocketVectorVelocity', 'NodeSocketVectorAcceleration']:
        return 3
    elif bl_socket_idname == 'NodeSocketRotation':
        return 3  # Euler rotation
    return 0  # Scalar type

def add_geonode_driver(target_modifier, source_modifier, source_object, socket_info):
    """
    Add driver to a geometry node modifier input.

    Args:
        target_modifier: NodesModifier to add driver to
        source_modifier: NodesModifier to drive from
        source_object: Object containing source modifier
        socket_info: Dict with identifier, bl_socket_idname, etc.
    """
    identifier = socket_info['identifier']
    bl_socket_idname = socket_info['bl_socket_idname']

    # Check if this socket type should be skipped
    if not is_drivable_socket_type(bl_socket_idname):
        return

    # Get component count
    component_count = get_socket_component_count(bl_socket_idname)

    try:
        if component_count > 0:
            # Vector-like type - drive each component
            for i in range(component_count):
                driver = target_modifier.driver_add(f'["{identifier}"]', i)
                var = driver.driver.variables.new()
                var.name = f"{identifier.replace('-', '_')}_{i}"
                var.targets[0].id_type = 'OBJECT'
                var.targets[0].id = source_object
                var.targets[0].data_path = f'modifiers["{source_modifier.name}"]["{identifier}"][{i}]'
                driver.driver.expression = var.name
                # Force update
                driver.driver.expression += " "
                driver.driver.expression = driver.driver.expression[:-1]
        else:
            # Scalar type - single driver
            driver = target_modifier.driver_add(f'["{identifier}"]')
            var = driver.driver.variables.new()
            var.name = identifier.replace('-', '_').replace(' ', '_')  # Clean name for expression
            var.targets[0].id_type = 'OBJECT'
            var.targets[0].id = source_object
            var.targets[0].data_path = f'modifiers["{source_modifier.name}"]["{identifier}"]'
            driver.driver.expression = var.name
            # Force update trick
            driver.driver.expression += " "
            driver.driver.expression = driver.driver.expression[:-1]
    except Exception as e:
        print(f"Failed to add driver for {identifier}: {e}")

def sync_geometry_nodes_modifiers(source_modifier, source_object, target_modifiers, sync_id=None):
    """
    Sync geometry nodes modifiers using drivers.

    Args:
        source_modifier: NodesModifier on source object
        source_object: Source object
        target_modifiers: List of (object, modifier) tuples to sync to
        sync_id: Optional sync ID to use. If None, will generate one or use existing.
    """
    # Get all input sockets from the node group
    sockets = get_geonode_input_sockets(source_modifier.node_group)

    # Generate or retrieve sync ID
    if sync_id is None:
        # Check if source modifier already has a sync ID
        _, existing_sync_id = parse_source_suffix(source_modifier.name)
        if existing_sync_id:
            sync_id = existing_sync_id
        else:
            sync_id = generate_sync_id()

    # Add (Source:ID) suffix to source modifier if not already present
    if not is_source_modifier(source_modifier.name):
        base_name = source_modifier.name
        # Remove old-style "(Source)" suffix if present
        if base_name.endswith(" (Source)"):
            base_name = base_name[:-9]
        new_name = base_name + get_source_suffix(sync_id)
        source_modifier.name = new_name
        # Update tracking on source object
        for info in source_object.SyncedModifierInfo:
            if info.name == base_name or info.name == base_name + " (Source)":
                info.name = new_name
                break
    elif "(Source)" in source_modifier.name and f"(Source:{sync_id})" not in source_modifier.name:
        # Upgrade old-style "(Source)" to new "(Source:ID)" format
        base_name, _ = parse_source_suffix(source_modifier.name)
        old_name = source_modifier.name
        new_name = base_name + get_source_suffix(sync_id)
        source_modifier.name = new_name
        # Update tracking
        for info in source_object.SyncedModifierInfo:
            if info.name == old_name:
                info.name = new_name
                break

    for target_obj, target_mod in target_modifiers:
        # Verify same node group
        if target_mod.node_group != source_modifier.node_group:
            print(f"Warning: {target_obj.name} has different node group, skipping")
            continue

        # Remove existing drivers on this modifier
        desync_geonode_modifier(target_obj, target_mod)

        # Add drivers for each drivable socket
        for socket_info in sockets:
            add_geonode_driver(target_mod, source_modifier, source_object, socket_info)

        # Track in SyncedModifierInfo
        if target_mod.name not in [info.name for info in target_obj.SyncedModifierInfo]:
            info = target_obj.SyncedModifierInfo.add()
            info.name = target_mod.name
            info.object = source_object
            info.is_synced = True
            target_obj.SyncedModifierIndex = len(target_obj.SyncedModifierInfo) - 1
        else:
            # Update existing tracking entry
            for info in target_obj.SyncedModifierInfo:
                if info.name == target_mod.name:
                    info.is_synced = True
                    info.object = source_object
                    break

    return sync_id

def desync_geonode_modifier(obj, modifier):
    """Remove all drivers from a geometry nodes modifier"""
    if not obj.animation_data:
        return

    drivers_to_remove = []
    for driver in obj.animation_data.drivers:
        # Check if driver is for this modifier
        if f'modifiers["{modifier.name}"]' in driver.data_path:
            drivers_to_remove.append(driver)

    for driver in drivers_to_remove:
        obj.animation_data.drivers.remove(driver)

    # Remove from tracking
    if modifier.name in [info.name for info in obj.SyncedModifierInfo]:
        idx = obj.SyncedModifierInfo.find(modifier.name)
        obj.SyncedModifierInfo.remove(idx)
        if obj.SyncedModifierIndex >= len(obj.SyncedModifierInfo):
            obj.SyncedModifierIndex = len(obj.SyncedModifierInfo) - 1

# ============================================================================
# End Geometry Nodes Support Functions
# ============================================================================

def sync_modifiers(modifiers,active):
    mod=modifiers[len(modifiers)-1][1]
    if mod.name not in active.SyncedModifierInfo:
        t=active.SyncedModifierInfo.add()
        t.name=mod.name
        t.object=active
        active.SyncedModifierIndex=len(active.SyncedModifierInfo)-1
    for obj,o_mod in modifiers[:-1]:
        if o_mod:
                        desyncmodifiers(obj,o_mod)
                        props=[ key for key, value in inspect.getmembers(o_mod) if key not in requiresObject and key not in {'name','is_active','vertex_group','filepath','driver','end_cap','start_cap','collection','armature','rim_vertex_group','shell_vertex_group','grid_name','execution_time',
                                "execution_time","is_cached",
                                "is_bound",
                                "is_bind",
                                "vertex_indices",
                                "vertex_indices_set",
                                "matrix_inverse",
                                "falloff_curve",
                                "vertex_velocities",
                                "read_velocity",
                                "has_velocity",
                                "map_curve",
                                "projectors",
                                "__doc__",
                                "__module__",
                                "__slotnames__",
                                "__slots__",
                                "bl_rna",
                                "rna_type",
                                "debug_options",
                                "type",
                                "object",
                                "delimit",
                                "custom_profile",
                                "face_count",
                                "is_external","cache_file","object_path","mask_tex_map_bone","mask_tex_map_object","mask_tex_uv_layer","mask_texture","mask_vertex_group","vertex_group_a","vertex_group_b","use_bone_envelopes","use_vertex_groups",
                                "total_levels",'texture','texture_coords_bone','texture_coords_object','uv_layer','auxiliary_target','origin','bone_from','bone_to','object_from','object_to','start_position_object',
                                "subtarget",'is_override_data','use_pin_to_last'
                            }]
                            
                        props=do_props(props,o_mod.type)
                        #print(props)
                        add_driver(props,o_mod,mod,active)
                        t=obj.SyncedModifierInfo.add()
                        t.name=o_mod.name
                        t.object=active
                        obj.SyncedModifierIndex=len(obj.SyncedModifierInfo)-1
mod_object_field={
    'MIRROR':'mirror_object',
    'ARRAY':'offset_object',
    'CURVE':'object',
    'BOOLEAN':'object',
    'SCREW':'object',
    'CAST':'object',
    'HOOK':'object',
    'LATTICE':'object',
    'SHRINKWRAP':'target',
    'SIMPLE_DEFORM':'origin',
    'SURFACE_DEFORM':'origin',
    'DATA_TRANSFER':'object',
    'NORMAL_EDIT':'target',
    'VERTEX_WEIGHT_PROXIMITY':'target',
    

}
icons={'MULTIRES': 'MOD_MULTIRES',
'ARRAY': 'MOD_ARRAY',
'BEVEL': 'MOD_BEVEL',
'BOOLEAN': 'MOD_BOOLEAN',
'BUILD': 'MOD_BUILD',
'DECIMATE': 'MOD_DECIM',
'EDGE_SPLIT': 'MOD_EDGESPLIT',
'NODES': 'MOD_NODES',
'MASK': 'MOD_MASK',
'MIRROR': 'MOD_MIRROR',
'REMESH': 'MOD_REMESH',
'SCREW': 'MOD_SCREW',
'SKIN': 'MOD_SKIN',
'SOLIDIFY': 'MOD_SOLIDIFY',
'SUBSURF': 'MOD_SUBSURF',
'TRIANGULATE': 'MOD_TRIANGULATE',
'VOLUME_TO_MESH': 'VOLUME_DATA',
'WELD': 'AUTOMERGE_ON',
'WIREFRAME': 'MOD_WIREFRAME',
'ARMATURE': 'MOD_ARMATURE',
'CAST': 'MOD_CAST',
'CURVE': 'MOD_CURVE',
'DISPLACE': 'MOD_DISPLACE',
'HOOK': 'HOOK',
'LAPLACIANDEFORM': 'MOD_MESHDEFORM',
'LATTICE': 'MOD_LATTICE',
'MESH_DEFORM': 'MOD_MESHDEFORM',
'SHRINKWRAP': 'MOD_SHRINKWRAP',
'SIMPLE_DEFORM': 'MOD_SIMPLEDEFORM',
'SMOOTH': 'MOD_SMOOTH',
'CORRECTIVE_SMOOTH': 'MOD_SMOOTH',
'LAPLACIANSMOOTH': 'MOD_SMOOTH',
'SURFACE_DEFORM': 'MOD_MESHDEFORM',
'WARP': 'MOD_WARP',
'WAVE': 'MOD_WAVE',
'DATA_TRANSFER': 'MOD_DATA_TRANSFER',
'MESH_CACHE': 'MOD_MESHDEFORM',
'MESH_SEQUENCE_CACHE': 'MOD_MESHDEFORM',
'NORMAL_EDIT': 'MOD_NORMALEDIT',
'WEIGHTED_NORMAL': 'MOD_NORMALEDIT',
'UV_PROJECT': 'MOD_UVPROJECT',
'UV_WARP': 'MOD_UVPROJECT',
'VERTEX_WEIGHT_EDIT': 'MOD_VERTEX_WEIGHT',
'VERTEX_WEIGHT_MIX': 'MOD_VERTEX_WEIGHT',
'VERTEX_WEIGHT_PROXIMITY': 'MOD_VERTEX_WEIGHT',
'OCEAN':'MOD_OCEAN',
'EXPLODE': 'MOD_EXPLODE'}
requiresObject = ["curve", "object", "offset_object", "mirror_object", "target"]
array_props={'MIRROR_use_axis':3,'MIRROR_use_bisect_axis':3,'MIRROR_use_bisect_flip_axis':3,'ARRAY_constant_offset_displace':3,'ARRAY_relative_offset_displace':3,'SIMPLE_DEFORM_limits':2,'NORMAL_EDIT_offset':3,'UV_WARP_center':2,'UV_WARP_offset':2,'UV_WARP_scale':2,'HOOK_center':2}
def do_props(props,mod_type):
    props_present=[prop for prop in [a.replace(mod_type+"_","") for a in array_props.keys()] if prop in props]
    array=props
    for p in props_present:
        pos = array.index(p)
        array=props[:pos]
        rem_array=props[pos+1:]
        for i in range(0,array_props[mod_type+"_"+p]):
            array.append(f'{p}[{i}]')  
        array = array + rem_array
        props=array
    return array
def Diff(li1, li2):
    return (list(list(set(li1)-set(li2)) + list(set(li2)-set(li1))))
def add_driver(target_properties,target_modifier,source_modifier,source_object):
    #print(target_modifier.name)
    for target_property in target_properties:
        #print(target_property)
        if "[" in target_property:
            index=regex.search(r"\[(.*)\]",target_property)
            if index:
                index=index[1]
                tp=target_property[:target_property.rindex("[")]
                driver=target_modifier.driver_add(tp,eval(index))
        else:
            tp=target_property
            driver=target_modifier.driver_add(target_property)
        var = driver.driver.variables.new()
        var.name = tp
        var.targets[0].data_path = f'modifiers["{source_modifier.name}"].{target_property}'
        var.targets[0].id_type='OBJECT'
        var.targets[0].id = source_object
        driver.driver.expression = f"{tp}"
        driver.driver.expression += " "
        driver.driver.expression = driver.driver.expression[:-1]
modify_mods= ['DATA_TRANSFER', 'MESH_CACHE', 'MESH_SEQUENCE_CACHE', 'NORMAL_EDIT', 'WEIGHTED_NORMAL', 'UV_PROJECT', 'UV_WARP', 'VERTEX_WEIGHT_EDIT', 'VERTEX_WEIGHT_MIX', 'VERTEX_WEIGHT_PROXIMITY']
generate_mods=['ARRAY', 'BEVEL', 'BOOLEAN', 'BUILD', 'DECIMATE', 'EDGE_SPLIT', 'MASK', 'MIRROR', 'REMESH', 'SCREW', 'SKIN', 'SOLIDIFY', 'SUBSURF', 'TRIANGULATE', 'VOLUME_TO_MESH', 'WELD', 'WIREFRAME']
deform_mods=['ARMATURE', 'CAST', 'CURVE', 'DISPLACE', 'HOOK', 'LAPLACIANDEFORM', 'LATTICE', 'MESH_DEFORM', 'SHRINKWRAP', 'SIMPLE_DEFORM', 'SMOOTH', 'CORRECTIVE_SMOOTH', 'LAPLACIANSMOOTH', 'SURFACE_DEFORM', 'WARP', 'WAVE',]
physics_mods=[ 'CLOTH', 'COLLISION', 'DYNAMIC_PAINT', 'EXPLODE', 'FLUID', 'OCEAN', 'PARTICLE_INSTANCE', 'PARTICLE_SYSTEM', 'SOFT_BODY', 'SURFACE']
class RTOOLS_UL_Synced_Mods_List(bpy.types.UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname):
        rs = item
        if rs and rs.name in [m.name for m in data.modifiers]:
            row = layout.row()

            # Show different icon based on sync status
            if rs.is_synced:
                # Synced - show with checkmark icon
                row.label(text=rs.name, icon='CHECKBOX_HLT')
            else:
                # Not synced - show greyed out with empty checkbox
                row.label(text=rs.name, icon='CHECKBOX_DEHLT')
                row.enabled = False  # Grey out the text
class RTOOLS_OT_SyncedPanel(bpy.types.Operator):
    bl_idname = "rtools.synced_modifiers_panel"
    bl_label = "Synced Modifiers Panel"
    bl_description = "Synced Modifiers Panel"
    bl_options = {'REGISTER', 'UNDO'}

    def draw(self, context):
        layout = self.layout
        layout.menu("RTOOLS_MT_Synced_Mods_Add_Menu", icon="MODIFIER")
        layout.operator("rtools.syncexistingmodifiers")

        # Row with scan and select all buttons (compact)
        row = layout.row(align=True)
        row.operator("rtools.scan_syncable_modifiers", text="Scan", icon="VIEWZOOM")
        row.operator("rtools.select_synced_objects", text="Select All", icon="RESTRICT_SELECT_OFF")

        ob = context.active_object

        if ob:
            # Modifier list with sidebar buttons - use split for better proportions
            row = layout.row()
            # Give more space to the list (85%) and less to buttons (15%)
            split = row.split(factor=0.85)

            # List column - wider
            list_col = split.column()
            list_col.template_list("RTOOLS_UL_Synced_Mods_List", "", ob, "SyncedModifierInfo",
                                  ob, "SyncedModifierIndex", item_dyntip_propname='name',
                                  sort_reverse=False, rows=4)

            # Sidebar buttons - narrower, icon-only
            btn_col = split.column(align=True)
            btn_col.scale_x = 0.8
            btn_col.operator("rtools.refreshsyncedmodifiers", text="", icon="FILE_REFRESH")
            btn_col.operator("rtools.desyncmodifiers", text="", icon="UNLINKED")
            btn_col.operator("rtools.remove_synced_modifier", text="", icon="X")
            btn_col.separator()
            btn_col.operator("rtools.resync_modifier", text="", icon="UV_SYNC_SELECT")
            btn_col.operator("rtools.select_source_object", text="", icon="OBJECT_DATA")
            btn_col.separator()
            btn_col.operator("rtools.clearunuseddrivers", text="", icon="TRASH")

            # Sync buttons row
            row = layout.row(align=True)
            row.operator("rtools.sync_selected_modifier", text="Sync Selected", icon="LINKED")
            row.operator("rtools.sync_all_modifiers", text="Sync All", icon="LINKED")

            # Sync from source button (for syncing via already-synced objects)
            if len(context.selected_objects) > 1:
                layout.operator("rtools.sync_from_source", text="Sync From Original Source", icon="TRACKING_FORWARDS")

            if ob.SyncedModifierIndex>=0 and ob.SyncedModifierIndex<len(ob.SyncedModifierInfo) and ob.SyncedModifierInfo[ob.SyncedModifierIndex].name in [mod.name for mod in ob.modifiers]:
                m=ob.modifiers[ob.SyncedModifierInfo[ob.SyncedModifierIndex].name]
                m2=m.name
                ob2=ob
                if ob.animation_data and ob.animation_data.drivers:
                    for driver in ob.animation_data.drivers:
                        
                        if f'modifiers["{m.name}"]' in  driver.data_path:
                            #print(f'modifiers["{m.name}"]',driver.data_path)
                            path=driver.driver.variables[0].targets[0].data_path
                            ob2=driver.driver.variables[0].targets[0].id
                            m2=path[path.index("[")+2:path.index("]")-1]
                            #print(m2,ob2)
                            break
                
                if ob2 and m2 in [t.name for t in ob2.modifiers]:
                    layout.separator(factor=0)
                    box=layout.box()
                    row=box.row(align=True)
                    row=row.split(factor=0.6)
                    row.label(text=m.name)
                    row.prop(ob2.modifiers[m2],'show_viewport',text="",icon="RESTRICT_VIEW_ON")
                    row.prop(ob2.modifiers[m2],'show_render',text="",icon="RESTRICT_RENDER_ON")
                    eval(f'{m.type}(self,box,ob2,ob2.modifiers["{m2}"])')
    def invoke(self, context,event):
        return context.window_manager.invoke_popup(self)
    def execute(self, context):
        return {'FINISHED'}
class RTOOLS_PT_SM_Addon(bpy.types.Panel):
    bl_label = "Synced Modifiers"
    bl_idname = "OBJECT_PT_SYNCED_MODS"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Item"

    def draw(self, context):
        layout = self.layout
        layout.menu("RTOOLS_MT_Synced_Mods_Add_Menu", icon="MODIFIER")
        layout.operator("rtools.syncexistingmodifiers")

        # Row with scan and select all buttons (compact)
        row = layout.row(align=True)
        row.operator("rtools.scan_syncable_modifiers", text="Scan", icon="VIEWZOOM")
        row.operator("rtools.select_synced_objects", text="Select All", icon="RESTRICT_SELECT_OFF")

        ob = context.active_object

        if ob:
            # Modifier list with sidebar buttons - use split for better proportions
            row = layout.row()
            # Give more space to the list (85%) and less to buttons (15%)
            split = row.split(factor=0.85)

            # List column - wider
            list_col = split.column()
            list_col.template_list("RTOOLS_UL_Synced_Mods_List", "", ob, "SyncedModifierInfo",
                                  ob, "SyncedModifierIndex", item_dyntip_propname='name',
                                  sort_reverse=False, rows=4)

            # Sidebar buttons - narrower, icon-only
            btn_col = split.column(align=True)
            btn_col.scale_x = 0.8
            btn_col.operator("rtools.refreshsyncedmodifiers", text="", icon="FILE_REFRESH")
            btn_col.operator("rtools.desyncmodifiers", text="", icon="UNLINKED")
            btn_col.operator("rtools.remove_synced_modifier", text="", icon="X")
            btn_col.separator()
            btn_col.operator("rtools.resync_modifier", text="", icon="UV_SYNC_SELECT")
            btn_col.operator("rtools.select_source_object", text="", icon="OBJECT_DATA")
            btn_col.separator()
            btn_col.operator("rtools.clearunuseddrivers", text="", icon="TRASH")

            # Sync buttons row
            row = layout.row(align=True)
            row.operator("rtools.sync_selected_modifier", text="Sync Selected", icon="LINKED")
            row.operator("rtools.sync_all_modifiers", text="Sync All", icon="LINKED")

            # Sync from source button (for syncing via already-synced objects)
            if len(context.selected_objects) > 1:
                layout.operator("rtools.sync_from_source", text="Sync From Original Source", icon="TRACKING_FORWARDS")
            
            if ob.SyncedModifierIndex>=0 and ob.SyncedModifierIndex<len(ob.SyncedModifierInfo) and ob.SyncedModifierInfo[ob.SyncedModifierIndex].name in [mod.name for mod in ob.modifiers]:
                m=ob.modifiers[ob.SyncedModifierInfo[ob.SyncedModifierIndex].name]
                m2=m.name
                ob2=ob
                if ob.animation_data and ob.animation_data.drivers:
                    for driver in ob.animation_data.drivers:
                        
                        if f'modifiers["{m.name}"]' in  driver.data_path:
                            #print(f'modifiers["{m.name}"]',driver.data_path)
                            path=driver.driver.variables[0].targets[0].data_path
                            ob2=driver.driver.variables[0].targets[0].id
                            m2=path[path.index("[")+2:path.index("]")-1]
                            #print(m2,ob2)
                            break
                
                if ob2 and m2 in [t.name for t in ob2.modifiers]:
                    layout.separator(factor=0)
                    box=layout.box()
                    row=box.row(align=True)
                    row=row.split(factor=0.6)
                    row.label(text=m.name)
                    row.prop(ob2.modifiers[m2],'show_viewport',text="",icon="RESTRICT_VIEW_ON")
                    row.prop(ob2.modifiers[m2],'show_render',text="",icon="RESTRICT_RENDER_ON")
                    eval(f'{m.type}(self,box,ob2,ob2.modifiers["{m2}"])')
class RTOOLS_MT_Synced_Mods_Modify_Menu(bpy.types.Menu):
    bl_label = "Modify Modifiers"

    def draw(self, context):
        layout = self.layout
        layout.operator_context = "INVOKE_DEFAULT"        
        for a in modify_mods:
            layout.operator("rtools.addsyncedmodifiers",text=a.replace("_", " ").capitalize(),icon=icons[a]).type=a
class RTOOLS_MT_Synced_Mods_Generate_Menu(bpy.types.Menu):
    bl_label = "Generate Modifiers"

    def draw(self, context):
        layout = self.layout
        layout.operator_context = "INVOKE_DEFAULT"        
        for a in generate_mods:
            layout.operator("rtools.addsyncedmodifiers",text=a.replace("_", " ").capitalize(),icon=icons[a]).type=a
class RTOOLS_MT_Synced_Mods_Deform_Menu(bpy.types.Menu):
    bl_label = "Deform Modifiers"

    def draw(self, context):
        layout = self.layout
        layout.operator_context = "INVOKE_DEFAULT"        
        for a in deform_mods:
            layout.operator("rtools.addsyncedmodifiers",text=a.replace("_", " ").capitalize(),icon=icons[a]).type=a
class RTOOLS_MT_Synced_Mods_Add_Menu(bpy.types.Menu):
    bl_label = "Add Modifiers"

    def draw(self, context):
        layout = self.layout
        layout.operator_context = "INVOKE_DEFAULT"
        layout.menu("RTOOLS_MT_Synced_Mods_Modify_Menu", icon="MESH_DATA")
        layout.menu("RTOOLS_MT_Synced_Mods_Generate_Menu", icon="MOD_TRIANGULATE")
        layout.menu("RTOOLS_MT_Synced_Mods_Deform_Menu",icon="MOD_MESHDEFORM")
        layout.separator()
        layout.menu("RTOOLS_MT_Synced_Mods_GeoNodes_Menu", icon="GEOMETRY_NODES")
def desyncmodifiers(ob,m):
    if m.name in [mod.name for mod in ob.modifiers]:
            # Check if it's a geometry nodes modifier
            if is_geometry_nodes_modifier(m):
                desync_geonode_modifier(ob, m)
            else:
                # Vanilla modifier desync
                if ob.animation_data and ob.animation_data.drivers:
                        for driver in ob.animation_data.drivers:

                            if f'modifiers["{m.name}"]' in  driver.data_path:
                                ob.animation_data.drivers.remove(driver)
                                ob.SyncedModifierInfo.remove(ob.SyncedModifierInfo.find(m.name))
                                if ob.SyncedModifierIndex>=len(ob.SyncedModifierInfo):
                                    ob.SyncedModifierIndex=len(ob.SyncedModifierInfo)-1
class RTOOLS_OT_Desync_Modifiers(bpy.types.Operator):
    bl_idname = "rtools.desyncmodifiers"
    bl_label = "Desync Modifiers"
    bl_description = "Remove Drivers from this modifier"
    bl_options = {"REGISTER","UNDO"}
    @classmethod
    def poll(cls, context):
        return context.active_object
    def execute(self,context):
        #for a in modify_mods+deform_mods+generate_mods:
        #    bpy.ops.rtools.addsyncedmodifiers('INVOKE_DEFAULT',type=a)
        ob=context.active_object
        if ob.SyncedModifierInfo and ob.SyncedModifierIndex>=0 and ob.SyncedModifierInfo[ob.SyncedModifierIndex].name in [mod.name for mod in ob.modifiers]:
            m=ob.modifiers[ob.SyncedModifierInfo[ob.SyncedModifierIndex].name]
            if ob.animation_data and ob.animation_data.drivers:
                    for driver in ob.animation_data.drivers:
                        
                        if f'modifiers["{m.name}"]' in  driver.data_path:
                            ob.animation_data.drivers.remove(driver)
                            ob.SyncedModifierInfo.remove(ob.SyncedModifierInfo.find(m.name))
                            if ob.SyncedModifierIndex>=len(ob.SyncedModifierInfo):
                                ob.SyncedModifierIndex=len(ob.SyncedModifierInfo)-1
        return {'FINISHED'}
class RTOOLS_OT_Refresh_Synced_Modifiers(bpy.types.Operator):
    bl_idname = "rtools.refreshsyncedmodifiers"
    bl_label = "Refresh Synced Modifiers"
    bl_description = "Refresh the synced modifiers list after manually deleting a modifier"
    bl_options = {"REGISTER","UNDO"}
    @classmethod
    def poll(cls, context):
        return context.active_object
    def execute(self,context):
        active=context.active_object
        for active in context.scene.objects:
            synced_mods=[a.name for a in active.SyncedModifierInfo]
            active.SyncedModifierInfo.clear()
            for a in synced_mods:
                if a in [mod.name for mod in active.modifiers]:
                    t=active.SyncedModifierInfo.add()
                    t.name=a
                    t.object=active
            if len(active.SyncedModifierInfo)>0:
                active.SyncedModifierIndex=0
        return {'FINISHED'}
class RTOOLS_OT_Clear_Unused_Drivers(bpy.types.Operator):
    bl_idname = "rtools.clearunuseddrivers"
    bl_label = "Clear Unused Drivers"
    bl_description = "Remove all unused modifier drivers"
    bl_options = {"REGISTER","UNDO"}
    @classmethod
    def poll(cls, context):
        return context.active_object
    def execute(self,context):
        ob=context.active_object
        bpy.ops.rtools.refreshsyncedmodifiers('INVOKE_DEFAULT')
        if ob and ob.animation_data:
            for driver in ob.animation_data.drivers:
                if f'modifiers[' in  driver.data_path:
                    path=driver.data_path
                    m2=path[path.index("[")+2:path.index("]")-1]
                    if m2 not in [mod.name for mod in ob.modifiers]:
                        ob.animation_data.drivers.remove(driver)
        return {'FINISHED'}

class RTOOLS_OT_Select_Synced_Objects(bpy.types.Operator):
    bl_idname = "rtools.select_synced_objects"
    bl_label = "Select All Synced Objects"
    bl_description = "Select all objects that have synced modifiers"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        return context.active_object

    def execute(self, context):
        # Deselect all first
        deselect_all()

        # Select all objects with synced modifiers
        selected_count = 0
        for obj in context.scene.objects:
            if len(obj.SyncedModifierInfo) > 0:
                try:
                    obj.select_set(True)
                    selected_count += 1
                except:
                    pass

        self.report({'INFO'}, f"Selected {selected_count} object(s) with synced modifiers")
        return {'FINISHED'}

class RTOOLS_OT_Remove_Synced_Modifier(bpy.types.Operator):
    bl_idname = "rtools.remove_synced_modifier"
    bl_label = "Remove Synced Modifier"
    bl_description = "Remove the modifier completely from source AND all synced target objects"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        return context.active_object

    def execute(self, context):
        ob = context.active_object
        if ob.SyncedModifierInfo and ob.SyncedModifierIndex >= 0 and ob.SyncedModifierIndex < len(ob.SyncedModifierInfo):
            mod_name = ob.SyncedModifierInfo[ob.SyncedModifierIndex].name

            if mod_name in [mod.name for mod in ob.modifiers]:
                m = ob.modifiers[mod_name]
                is_geonode = is_geometry_nodes_modifier(m)

                # Find the source object (if this is a target)
                source_obj = ob.SyncedModifierInfo[ob.SyncedModifierIndex].object
                if source_obj is None:
                    source_obj = ob  # This IS the source

                # Collect all objects that have this synced modifier
                objects_to_clean = []

                # Find all objects in scene with this synced modifier
                for scene_obj in context.scene.objects:
                    if mod_name in [mod.name for mod in scene_obj.modifiers]:
                        # Check if it's tracked as synced
                        if mod_name in [info.name for info in scene_obj.SyncedModifierInfo]:
                            objects_to_clean.append(scene_obj)

                # Remove from all objects
                removed_count = 0
                for target_obj in objects_to_clean:
                    if mod_name in [mod.name for mod in target_obj.modifiers]:
                        target_mod = target_obj.modifiers[mod_name]

                        # Desync first (removes drivers and tracking)
                        if is_geonode:
                            desync_geonode_modifier(target_obj, target_mod)
                        else:
                            desyncmodifiers(target_obj, target_mod)

                        # Now remove the modifier itself
                        target_obj.modifiers.remove(target_mod)
                        removed_count += 1

                self.report({'INFO'}, f"Removed modifier '{mod_name}' from {removed_count} object(s)")
            else:
                self.report({'WARNING'}, f"Modifier '{mod_name}' not found")
                # Clean up the tracking entry anyway
                ob.SyncedModifierInfo.remove(ob.SyncedModifierIndex)
                if ob.SyncedModifierIndex >= len(ob.SyncedModifierInfo):
                    ob.SyncedModifierIndex = len(ob.SyncedModifierInfo) - 1

        return {'FINISHED'}

class RTOOLS_OT_Add_Modifiers(bpy.types.Operator):
    bl_idname = "rtools.addsyncedmodifiers"
    bl_label = "Sync Modifiers"
    bl_description = "Add this modifier to the selected objects"
    bl_options = {"REGISTER","UNDO"}
    type:bpy.props.StringProperty(default="None",options={'HIDDEN'})
    @classmethod
    def poll(cls, context):
        return context.active_object
    def execute(self,context):
        #print(self.type)
        active=context.active_object
        selected=context.selected_objects
        bpy.ops.rtools.refreshsyncedmodifiers('INVOKE_DEFAULT')
        if self.type!='None':
            name=self.type.replace("_"," ").capitalize()
            ogname=name
            if active.animation_data and active.animation_data.drivers:
                for driver in active.animation_data.drivers:
                    i=1
                    while( f'modifiers["{name}"]' in  driver.data_path):
                        name=ogname+f"_{i}"
                        i=i+1

            # Generate sync ID if we have multiple objects
            sync_id = generate_sync_id() if len(context.selected_objects) > 1 else None
            source_suffix = get_source_suffix(sync_id) if sync_id else ""

            mod=active.modifiers.new(type=self.type,name=name + source_suffix)
            if mod:
                t=active.SyncedModifierInfo.add()
                
                t.name=mod.name
                t.object=active
                active.SyncedModifierIndex=len(active.SyncedModifierInfo)-1
                for o in [a for a in selected if a!=active]:
                    o_mod=o.modifiers.new(type=self.type,name=name)
                    if o_mod:
                        props=[ key for key, value in inspect.getmembers(o_mod) if key not in requiresObject and key not in {'name','is_active','vertex_group','filepath','driver','end_cap','start_cap','collection','armature','rim_vertex_group','shell_vertex_group','grid_name','execution_time',
                                "execution_time","is_cached",
                                "is_bound",
                                "is_bind",
                                "vertex_indices",
                                "vertex_indices_set",
                                "matrix_inverse",
                                "falloff_curve",
                                "vertex_velocities",
                                "read_velocity",
                                "has_velocity",
                                "map_curve",
                                "projectors",
                                "__doc__",
                                "__module__",
                                "__slotnames__",
                                "__slots__",
                                "bl_rna",
                                "rna_type",
                                "debug_options",
                                "type",
                                "object",
                                "delimit",
                                "custom_profile",
                                "face_count",
                                "is_external","cache_file","object_path","mask_tex_map_bone","mask_tex_map_object","mask_tex_uv_layer","mask_texture","mask_vertex_group","vertex_group_a","vertex_group_b","use_bone_envelopes","use_vertex_groups",
                                "total_levels",'texture','texture_coords_bone','texture_coords_object','uv_layer','auxiliary_target','origin','bone_from','bone_to','object_from','object_to','start_position_object',
                                "subtarget",'is_override_data','use_pin_to_last'
                            }]
                            
                        props=do_props(props,o_mod.type)
                        #print(props)
                        add_driver(props,o_mod,mod,active)
                        t=o.SyncedModifierInfo.add()
                        t.name=o_mod.name
                        t.object=active
                        o.SyncedModifierIndex=len(o.SyncedModifierInfo)-1
            else:
                self.report({'WARNING'},"Object doesn't support this modifier!")
        return {'FINISHED'}
def active_object_modifiers(self, context):
    obj=context.active_object
    # Include both vanilla modifiers and geometry nodes (NODES type)
    mods=[(a.name,a.name,a.name) for a in obj.modifiers if a.type in modify_mods+deform_mods+generate_mods or a.type == 'NODES']
    return mods if mods else [("None","None","None"),]

def selected_object_modifiers(self, context):
    if len(context.selected_objects)>1:
        obj=Diff(context.selected_objects,[context.active_object,])[0]
        if self.mod_1 and self.mod_1!="None":
            source_mod = context.active_object.modifiers[self.mod_1]
            # For geometry nodes, match by node_group; for vanilla, match by type
            if source_mod.type == 'NODES' and source_mod.node_group:
                return [(a.name,a.name,a.name) for a in obj.modifiers if a.type == 'NODES' and a.node_group == source_mod.node_group]
            else:
                return [(a.name,a.name,a.name) for a in obj.modifiers if a.type in modify_mods+deform_mods+generate_mods and a.type == source_mod.type]
    return [("None","None","None"),]
def _get_matching_modifiers_for_object(self, context, obj_index):
    """Helper to get matching modifiers for a target object"""
    if self.mod_1 and self.mod_1 != "None":
        source_mod = context.active_object.modifiers[self.mod_1]
        obj = Diff(context.selected_objects, [context.active_object,])[obj_index]

        # For geometry nodes, match by node_group; for vanilla, match by type
        if source_mod.type == 'NODES' and source_mod.node_group:
            return [(a.name,a.name,a.name) for a in obj.modifiers if a.type == 'NODES' and a.node_group == source_mod.node_group]
        else:
            return [(a.name,a.name,a.name) for a in obj.modifiers if a.type in modify_mods+deform_mods+generate_mods and a.type == source_mod.type]
    return [("None","None","None"),]

def selected_object_modifiers_1(self, context):
    if len(context.selected_objects) > 2:
        return _get_matching_modifiers_for_object(self, context, 1)
    return [("None","None","None"),]

def selected_object_modifiers_2(self, context):
    if len(context.selected_objects) > 3:
        return _get_matching_modifiers_for_object(self, context, 2)
    return [("None","None","None"),]

def selected_object_modifiers_3(self, context):
    if len(context.selected_objects) > 4:
        return _get_matching_modifiers_for_object(self, context, 3)
    return [("None","None","None"),]

def selected_object_modifiers_4(self, context):
    if len(context.selected_objects) > 5:
        return _get_matching_modifiers_for_object(self, context, 4)
    return [("None","None","None"),]

def selected_object_modifiers_5(self, context):
    if len(context.selected_objects) > 6:
        return _get_matching_modifiers_for_object(self, context, 5)
    return [("None","None","None"),]

def selected_object_modifiers_6(self, context):
    if len(context.selected_objects) > 7:
        return _get_matching_modifiers_for_object(self, context, 6)
    return [("None","None","None"),]

def selected_object_modifiers_7(self, context):
    if len(context.selected_objects) > 8:
        return _get_matching_modifiers_for_object(self, context, 7)
    return [("None","None","None"),]

def selected_object_modifiers_8(self, context):
    if len(context.selected_objects) > 9:
        return _get_matching_modifiers_for_object(self, context, 8)
    return [("None","None","None"),]

def selected_object_modifiers_9(self, context):
    if len(context.selected_objects) > 10:
        return _get_matching_modifiers_for_object(self, context, 9)
    return [("None","None","None"),]
class RTOOLS_OT_Sync_Existing_Modifiers(bpy.types.Operator):
    bl_idname = "rtools.syncexistingmodifiers"
    bl_label = "Sync Modifiers"
    bl_description = ""
    bl_options = {"REGISTER","UNDO"}
    mod_1:bpy.props.EnumProperty(items=active_object_modifiers,name="Source Modifier")
    add_new:bpy.props.BoolProperty(default=False,name="Add New Modifier",options={'SKIP_SAVE'})
    mod_2:bpy.props.EnumProperty(items=selected_object_modifiers,name="Target Modifier (Object 1)")
    mod_3:bpy.props.EnumProperty(items=selected_object_modifiers_1,name="Target Modifier (Object 2)")
    mod_4:bpy.props.EnumProperty(items=selected_object_modifiers_2,name="Target Modifier (Object 3)")
    mod_5:bpy.props.EnumProperty(items=selected_object_modifiers_3,name="Target Modifier (Object 4)")
    mod_6:bpy.props.EnumProperty(items=selected_object_modifiers_4,name="Target Modifier (Object 5)")
    mod_7:bpy.props.EnumProperty(items=selected_object_modifiers_5,name="Target Modifier (Object 6)")
    mod_8:bpy.props.EnumProperty(items=selected_object_modifiers_6,name="Target Modifier (Object 7)")
    mod_9:bpy.props.EnumProperty(items=selected_object_modifiers_7,name="Target Modifier (Object 8)")
    mod_10:bpy.props.EnumProperty(items=selected_object_modifiers_8,name="Target Modifier (Object 9)")
    mod_11:bpy.props.EnumProperty(items=selected_object_modifiers_9,name="Target Modifier (Object 10)")
    object_1_name:bpy.props.StringProperty(default="Object 1")
    object_2_name:bpy.props.StringProperty(default="Object 2")
    object_3_name:bpy.props.StringProperty(default="Object 3")
    object_4_name:bpy.props.StringProperty(default="Object 4")
    object_5_name:bpy.props.StringProperty(default="Object 5")
    object_6_name:bpy.props.StringProperty(default="Object 6")
    object_7_name:bpy.props.StringProperty(default="Object 7")
    object_8_name:bpy.props.StringProperty(default="Object 8")
    object_9_name:bpy.props.StringProperty(default="Object 9")
    object_10_name:bpy.props.StringProperty(default="Object 10")
    
    
    @classmethod
    def poll(cls, context):
        return context.active_object and len(context.selected_objects)>1
    def draw(self, context):
        layout = self.layout
        layout.prop(self,"mod_1")
        #if len(context.selected_objects)==2:
        layout.prop(self,"add_new")
        if not self.add_new:
            layout.prop(self,"mod_2",text=self.object_1_name)
            if len(context.selected_objects)>2:
                layout.prop(self,"mod_3",text=self.object_2_name)
            if len(context.selected_objects)>3:
                layout.prop(self,"mod_4",text=self.object_3_name)
            if len(context.selected_objects)>4:
                layout.prop(self,"mod_5",text=self.object_4_name)
            if len(context.selected_objects)>5:
                layout.prop(self,"mod_6",text=self.object_5_name)
            if len(context.selected_objects)>6:
                layout.prop(self,"mod_7",text=self.object_6_name)
            if len(context.selected_objects)>7:
                layout.prop(self,"mod_8",text=self.object_7_name)
            if len(context.selected_objects)>8:
                layout.prop(self,"mod_9",text=self.object_8_name)
            if len(context.selected_objects)>9:
                layout.prop(self,"mod_10",text=self.object_9_name)
            if len(context.selected_objects)>10:
                layout.prop(self,"mod_11",text=self.object_10_name)
    def execute(self,context):
        #print(self.type)
        if self.mod_1 and self.mod_1!="None":
            active=context.active_object
            selected=Diff(context.selected_objects,[active,])[0]
            mod_new=None
            active_mod=active.modifiers[self.mod_1]
            mods_to_sync=[]
            if self.add_new:
                for obj in Diff(context.selected_objects,[active,]):
                    mod_new=obj.modifiers.new(type=active.modifiers[self.mod_1].type,name=self.mod_1)
                    mods_to_sync.append((obj,mod_new))
            else:
                if self.mod_2 and self.mod_2!="None" and  self.mod_2 in [a.name for a in selected.modifiers]:
                    mod_new=selected.modifiers[self.mod_2]
                    mods_to_sync.append((selected,mod_new))
                if self.mod_3 and self.mod_3!="None" and  self.mod_3 in [a.name for a in Diff(context.selected_objects,[active,])[1].modifiers]:
                    mod_new=Diff(context.selected_objects,[active,])[1].modifiers[self.mod_3]
                    mods_to_sync.append((Diff(context.selected_objects,[active,])[1],mod_new))
                if self.mod_4 and self.mod_4!="None" and  self.mod_4 in [a.name for a in Diff(context.selected_objects,[active,])[2].modifiers]:
                    mod_new=Diff(context.selected_objects,[active,])[2].modifiers[self.mod_4]
                    mods_to_sync.append((Diff(context.selected_objects,[active,])[2],mod_new))
                if self.mod_5 and self.mod_5!="None" and  self.mod_5 in [a.name for a in Diff(context.selected_objects,[active,])[3].modifiers]:
                    mod_new=Diff(context.selected_objects,[active,])[3].modifiers[self.mod_5]
                    mods_to_sync.append((Diff(context.selected_objects,[active,])[3],mod_new))
                if self.mod_6 and self.mod_6!="None" and  self.mod_6 in [a.name for a in Diff(context.selected_objects,[active,])[4].modifiers]:
                    mod_new=Diff(context.selected_objects,[active,])[4].modifiers[self.mod_6]
                    mods_to_sync.append((Diff(context.selected_objects,[active,])[4],mod_new))
                if self.mod_7 and self.mod_7!="None" and  self.mod_7 in [a.name for a in Diff(context.selected_objects,[active,])[5].modifiers]:
                    mod_new=Diff(context.selected_objects,[active,])[5].modifiers[self.mod_7]
                    mods_to_sync.append((Diff(context.selected_objects,[active,])[5],mod_new))
                if self.mod_8 and self.mod_8!="None" and  self.mod_8 in [a.name for a in Diff(context.selected_objects,[active,])[6].modifiers]:
                    mod_new=Diff(context.selected_objects,[active,])[6].modifiers[self.mod_8]
                    mods_to_sync.append((Diff(context.selected_objects,[active,])[6],mod_new))
                if self.mod_9 and self.mod_9!="None" and self.mod_2!="None" and  self.mod_9 in [a.name for a in Diff(context.selected_objects,[active,])[7].modifiers]:
                    mod_new=Diff(context.selected_objects,[active,])[7].modifiers[self.mod_9]
                    mods_to_sync.append((Diff(context.selected_objects,[active,])[7],mod_new))
                if self.mod_10 and self.mod_10!="None" and  self.mod_10 in [a.name for a in Diff(context.selected_objects,[active,])[8].modifiers]:
                    mod_new=Diff(context.selected_objects,[active,])[8].modifiers[self.mod_10]
                    mods_to_sync.append((Diff(context.selected_objects,[active,])[8],mod_new))
                if self.mod_11 and self.mod_11!="None" and  self.mod_11 in [a.name for a in Diff(context.selected_objects,[active,])[9].modifiers]:
                    mod_new=Diff(context.selected_objects,[active,])[9].modifiers[self.mod_11]
                    mods_to_sync.append((Diff(context.selected_objects,[active,])[9],mod_new))
            if active.animation_data and active.animation_data.drivers:
                        for driver in active.animation_data.drivers:
                            
                            if f'modifiers["{active_mod.name}"]' in  driver.data_path:
                                #print(f'modifiers["{m.name}"]',driver.data_path)
                                path=driver.driver.variables[0].targets[0].data_path
                                if "modifiers" in  path:
                                    ob2=driver.driver.variables[0].targets[0].id
                                    m2=path[path.index("[")+2:path.index("]")-1]
                                    #print(m2,ob2)
                                    if m2 in [a.name for a in ob2.modifiers]:
                                        active=ob2
                                        active_mod=ob2.modifiers[m2]
                                    break
            mods_to_sync.append((active,active.modifiers[self.mod_1]))
            if self.mod_1 and mod_new:
                # Check if it's a geometry nodes modifier
                if is_geometry_nodes_modifier(active_mod):
                    # Sync using geometry nodes function
                    target_modifiers = mods_to_sync[:-1]  # Exclude the source (last item)
                    sync_geometry_nodes_modifiers(active_mod, active, target_modifiers)
                else:
                    # Sync using vanilla modifier function
                    sync_modifiers(mods_to_sync,active)
        else:
            self.report({'WARNING'},"No Source Modifier")
        return {'FINISHED'}
    def invoke(self, context,event):
        if len(context.selected_objects)>2:
            self.add_new=True
        if  len(context.selected_objects)>1:
            self.object_1_name=Diff(context.selected_objects,[context.active_object,])[0].name
        if  len(context.selected_objects)>2:
            self.object_2_name=Diff(context.selected_objects,[context.active_object,])[1].name
        if  len(context.selected_objects)>3:
            self.object_3_name=Diff(context.selected_objects,[context.active_object,])[2].name
        if  len(context.selected_objects)>4:
            self.object_4_name=Diff(context.selected_objects,[context.active_object,])[3].name
        if  len(context.selected_objects)>5:
            self.object_5_name=Diff(context.selected_objects,[context.active_object,])[4].name
        if  len(context.selected_objects)>6:
            self.object_6_name=Diff(context.selected_objects,[context.active_object,])[5].name
        if  len(context.selected_objects)>7:
            self.object_7_name=Diff(context.selected_objects,[context.active_object,])[6].name
        if  len(context.selected_objects)>8:
            self.object_8_name=Diff(context.selected_objects,[context.active_object,])[7].name
        if  len(context.selected_objects)>9:
            self.object_9_name=Diff(context.selected_objects,[context.active_object,])[8].name
        if  len(context.selected_objects)>10:
            self.object_10_name=Diff(context.selected_objects,[context.active_object,])[9].name
        return self.execute(context)
class RTOOLS_OT_Sync_Modifier_Object(bpy.types.Operator):
    bl_idname = "rtools.sync_object"
    bl_label = "Sync"
    bl_description = "Sync Object Fields"
    bl_options = {"REGISTER","UNDO"}
    mod: bpy.props.StringProperty(options={'SKIP_SAVE'})
    object:bpy.props.StringProperty(options={'SKIP_SAVE'})
    @classmethod
    def poll(cls, context):
        return context.active_object
    def execute(self,context):
        og_mod=bpy.data.objects[self.object].modifiers[self.mod]
        mod_type=bpy.data.objects[self.object].modifiers[self.mod].type
        for obj in bpy.data.objects:
            for mod in obj.modifiers:
                if mod.type==mod_type and mod.name in obj.SyncedModifierInfo:
                    setattr(mod,mod_object_field[mod.type],getattr(og_mod,mod_object_field[mod.type]))

        return {'FINISHED'}

class RTOOLS_OT_Add_Synced_GeoNodes(bpy.types.Operator):
    bl_idname = "rtools.add_synced_geonodes"
    bl_label = "Add Synced Geometry Nodes"
    bl_description = "Add a Geometry Nodes modifier with the same node group to selected objects"
    bl_options = {"REGISTER", "UNDO"}

    node_group_name: bpy.props.StringProperty(
        name="Node Group",
        description="Name of the geometry node group to use"
    )

    @classmethod
    def poll(cls, context):
        return context.active_object is not None

    def get_node_group(self):
        """Get node group by name"""
        if not self.node_group_name:
            return None
        return bpy.data.node_groups.get(self.node_group_name)

    def execute(self, context):
        node_group = self.get_node_group()
        if not node_group:
            self.report({'WARNING'}, "No node group selected or not found")
            return {'CANCELLED'}

        active = context.active_object
        selected = [obj for obj in context.selected_objects if obj != active]

        # Generate sync ID upfront if we have targets
        sync_id = generate_sync_id() if selected else None

        # Create modifier on active object with sync ID in name
        if selected and sync_id:
            mod_name = node_group.name + get_source_suffix(sync_id)
        else:
            mod_name = node_group.name
        source_mod = active.modifiers.new(name=mod_name, type='NODES')
        source_mod.node_group = node_group

        # Track on source
        info = active.SyncedModifierInfo.add()
        info.name = source_mod.name
        info.object = active
        info.is_synced = True if selected else False
        active.SyncedModifierIndex = len(active.SyncedModifierInfo) - 1

        # Create and sync on selected objects
        if selected:
            target_modifiers = []
            for obj in selected:
                target_mod = obj.modifiers.new(name=node_group.name, type='NODES')
                target_mod.node_group = node_group
                target_modifiers.append((obj, target_mod))

            # Sync them with the sync ID
            sync_geometry_nodes_modifiers(source_mod, active, target_modifiers, sync_id)

        self.report({'INFO'}, f"Added synced Geometry Nodes modifier with '{node_group.name}'")
        return {'FINISHED'}

class RTOOLS_OT_Sync_GeoNode_Input(bpy.types.Operator):
    bl_idname = "rtools.sync_geonode_input"
    bl_label = "Sync Geometry Node Input"
    bl_description = "Sync Object/Collection/Material inputs across all synced modifiers"
    bl_options = {"REGISTER", "UNDO"}

    mod: bpy.props.StringProperty(options={'SKIP_SAVE'})
    object: bpy.props.StringProperty(options={'SKIP_SAVE'})
    identifier: bpy.props.StringProperty(options={'SKIP_SAVE'})
    socket_type: bpy.props.StringProperty(options={'SKIP_SAVE'})

    @classmethod
    def poll(cls, context):
        return context.active_object

    def execute(self, context):
        source_obj = bpy.data.objects.get(self.object)
        if not source_obj:
            self.report({'WARNING'}, f"Source object '{self.object}' not found")
            return {'CANCELLED'}

        source_mod = source_obj.modifiers.get(self.mod)
        if not source_mod or source_mod.type != 'NODES':
            self.report({'WARNING'}, f"Source modifier '{self.mod}' not found or not a Geometry Nodes modifier")
            return {'CANCELLED'}

        # Get the value from source
        try:
            source_value = source_mod[self.identifier]
        except KeyError:
            self.report({'WARNING'}, f"Input '{self.identifier}' not found in source modifier")
            return {'CANCELLED'}

        # Apply to all objects with same geometry nodes modifier
        synced_count = 0
        synced_objects = []
        for obj in bpy.data.objects:
            for mod in obj.modifiers:
                if mod.type == 'NODES' and mod.node_group == source_mod.node_group:
                    if mod.name in [info.name for info in obj.SyncedModifierInfo]:
                        # This is a synced modifier
                        try:
                            mod[self.identifier] = source_value
                            synced_count += 1
                            synced_objects.append((obj, mod))
                        except:
                            pass  # Input might not exist on this version

        # Force viewport update for all synced modifiers
        # This is needed because object/collection/material fields don't auto-update viewport
        for obj, mod in synced_objects:
            force_modifier_update(obj, mod)

        # Also trigger a general depsgraph update
        if synced_objects:
            context.view_layer.update()

        self.report({'INFO'}, f"Synced '{self.identifier}' to {synced_count} modifier(s)")
        return {'FINISHED'}

class RTOOLS_OT_Scan_Syncable_Modifiers(bpy.types.Operator):
    bl_idname = "rtools.scan_syncable_modifiers"
    bl_label = "Scan for Syncable"
    bl_description = "Scan for all modifiers that can be synced"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        return context.active_object

    def execute(self, context):
        ob = context.active_object

        # Clear the existing list
        ob.SyncedModifierInfo.clear()

        # Scan all modifiers on the active object
        for mod in ob.modifiers:
            # Check if this modifier has drivers (is synced)
            is_currently_synced = False
            if ob.animation_data and ob.animation_data.drivers:
                for driver in ob.animation_data.drivers:
                    if f'modifiers["{mod.name}"]' in driver.data_path:
                        is_currently_synced = True
                        break

            # Add to list
            info = ob.SyncedModifierInfo.add()
            info.name = mod.name
            info.object = ob if not is_currently_synced else ob  # Will be updated during sync
            info.is_synced = is_currently_synced

        if len(ob.SyncedModifierInfo) > 0:
            ob.SyncedModifierIndex = 0

        synced_count = len([m for m in ob.SyncedModifierInfo if m.is_synced])
        total_count = len(ob.SyncedModifierInfo)
        self.report({'INFO'}, f"Found {total_count} modifier(s), {synced_count} already synced")
        return {'FINISHED'}

class RTOOLS_OT_Sync_Selected_Modifier(bpy.types.Operator):
    bl_idname = "rtools.sync_selected_modifier"
    bl_label = "Sync Selected"
    bl_description = "Sync the selected modifier to all selected objects"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        return (context.active_object and
                len(context.selected_objects) > 1 and
                context.active_object.SyncedModifierInfo and
                context.active_object.SyncedModifierIndex >= 0)

    def execute(self, context):
        ob = context.active_object
        if ob.SyncedModifierIndex >= len(ob.SyncedModifierInfo):
            self.report({'WARNING'}, "No modifier selected")
            return {'CANCELLED'}

        mod_info = ob.SyncedModifierInfo[ob.SyncedModifierIndex]
        mod_name = mod_info.name

        if mod_name not in [m.name for m in ob.modifiers]:
            self.report({'WARNING'}, f"Modifier '{mod_name}' not found on active object")
            return {'CANCELLED'}

        source_mod = ob.modifiers[mod_name]
        selected = [obj for obj in context.selected_objects if obj != ob]

        if not selected:
            self.report({'WARNING'}, "No other objects selected")
            return {'CANCELLED'}

        # Create or sync modifiers on selected objects
        target_modifiers = []
        for target_obj in selected:
            # Check if target already has this modifier
            if mod_name in [m.name for m in target_obj.modifiers]:
                target_mod = target_obj.modifiers[mod_name]
            else:
                # Create new modifier
                target_mod = target_obj.modifiers.new(name=mod_name, type=source_mod.type)
                if source_mod.type == 'NODES' and source_mod.node_group:
                    target_mod.node_group = source_mod.node_group

            target_modifiers.append((target_obj, target_mod))

        # Sync using appropriate function
        if is_geometry_nodes_modifier(source_mod):
            sync_geometry_nodes_modifiers(source_mod, ob, target_modifiers)
        else:
            # For vanilla modifiers, use existing sync
            all_mods = target_modifiers + [(ob, source_mod)]
            sync_modifiers(all_mods, ob)

        # Mark as synced
        mod_info.is_synced = True

        self.report({'INFO'}, f"Synced '{mod_name}' to {len(target_modifiers)} object(s)")
        return {'FINISHED'}

class RTOOLS_OT_Sync_All_Modifiers(bpy.types.Operator):
    bl_idname = "rtools.sync_all_modifiers"
    bl_label = "Sync All"
    bl_description = "Sync all non-synced modifiers to all selected objects"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        return context.active_object and len(context.selected_objects) > 1

    def execute(self, context):
        ob = context.active_object
        selected = [obj for obj in context.selected_objects if obj != ob]

        if not selected:
            self.report({'WARNING'}, "No other objects selected")
            return {'CANCELLED'}

        synced_count = 0
        for mod_info in ob.SyncedModifierInfo:
            if not mod_info.is_synced:  # Only sync non-synced modifiers
                mod_name = mod_info.name

                if mod_name not in [m.name for m in ob.modifiers]:
                    continue

                source_mod = ob.modifiers[mod_name]
                target_modifiers = []

                for target_obj in selected:
                    # Check if target already has this modifier
                    if mod_name in [m.name for m in target_obj.modifiers]:
                        target_mod = target_obj.modifiers[mod_name]
                    else:
                        # Create new modifier
                        target_mod = target_obj.modifiers.new(name=mod_name, type=source_mod.type)
                        if source_mod.type == 'NODES' and source_mod.node_group:
                            target_mod.node_group = source_mod.node_group

                    target_modifiers.append((target_obj, target_mod))

                # Sync using appropriate function
                if is_geometry_nodes_modifier(source_mod):
                    sync_geometry_nodes_modifiers(source_mod, ob, target_modifiers)
                else:
                    all_mods = target_modifiers + [(ob, source_mod)]
                    sync_modifiers(all_mods, ob)

                # Mark as synced
                mod_info.is_synced = True
                synced_count += 1

        self.report({'INFO'}, f"Synced {synced_count} modifier(s) to {len(selected)} object(s)")
        return {'FINISHED'}


class RTOOLS_OT_Select_Source_Object(bpy.types.Operator):
    bl_idname = "rtools.select_source_object"
    bl_label = "Select Source Object"
    bl_description = "Select the source object that drives this synced modifier"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        ob = context.active_object
        if not ob:
            return False
        if not ob.SyncedModifierInfo or ob.SyncedModifierIndex < 0:
            return False
        if ob.SyncedModifierIndex >= len(ob.SyncedModifierInfo):
            return False
        return True

    def execute(self, context):
        ob = context.active_object
        mod_info = ob.SyncedModifierInfo[ob.SyncedModifierIndex]
        mod_name = mod_info.name

        if mod_name not in [m.name for m in ob.modifiers]:
            self.report({'WARNING'}, f"Modifier '{mod_name}' not found")
            return {'CANCELLED'}

        modifier = ob.modifiers[mod_name]

        # Find the source object and modifier
        source_obj, source_mod, sync_id = get_source_object_and_modifier(ob, modifier)

        if source_obj is None:
            # This might be the source itself
            if is_source_modifier(modifier.name):
                self.report({'INFO'}, "This object IS the source")
                return {'FINISHED'}
            else:
                self.report({'WARNING'}, "Could not find source object for this modifier")
                return {'CANCELLED'}

        if source_obj == ob:
            self.report({'INFO'}, "This object IS the source")
            return {'FINISHED'}

        # Deselect all and select the source object
        deselect_all()
        source_obj.select_set(True)
        context.view_layer.objects.active = source_obj

        self.report({'INFO'}, f"Selected source object: {source_obj.name}")
        return {'FINISHED'}


class RTOOLS_OT_Resync_Modifier(bpy.types.Operator):
    bl_idname = "rtools.resync_modifier"
    bl_label = "Resync Modifier"
    bl_description = "Re-sync modifier to add missing drivers for new inputs and update source naming"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        ob = context.active_object
        if not ob:
            return False
        if not ob.SyncedModifierInfo or ob.SyncedModifierIndex < 0:
            return False
        if ob.SyncedModifierIndex >= len(ob.SyncedModifierInfo):
            return False
        return True

    def execute(self, context):
        ob = context.active_object
        mod_info = ob.SyncedModifierInfo[ob.SyncedModifierIndex]
        mod_name = mod_info.name

        if mod_name not in [m.name for m in ob.modifiers]:
            self.report({'WARNING'}, f"Modifier '{mod_name}' not found")
            return {'CANCELLED'}

        modifier = ob.modifiers[mod_name]

        # Find the source object and modifier
        source_obj, source_mod, sync_id = get_source_object_and_modifier(ob, modifier)

        if source_obj is None:
            self.report({'WARNING'}, "Could not find source for this modifier. It may not be synced.")
            return {'CANCELLED'}

        # If this is the source, we need to find all targets and resync them
        if source_obj == ob and is_source_modifier(modifier.name):
            source_mod = modifier
            sync_id = parse_source_suffix(modifier.name)[1]

            # Ensure the source has the proper (Source:ID) naming
            if sync_id is None:
                sync_id = generate_sync_id()
                base_name, _ = parse_source_suffix(modifier.name)
                new_name = base_name + get_source_suffix(sync_id)
                old_name = modifier.name
                modifier.name = new_name
                # Update tracking
                for info in ob.SyncedModifierInfo:
                    if info.name == old_name:
                        info.name = new_name
                        break
                mod_name = new_name

        # Handle geometry nodes modifiers
        if is_geometry_nodes_modifier(source_mod):
            # Find all objects with synced modifiers using this source
            target_modifiers = []

            for scene_obj in bpy.data.objects:
                if scene_obj == source_obj:
                    continue

                for mod in scene_obj.modifiers:
                    if mod.type != 'NODES' or mod.node_group != source_mod.node_group:
                        continue

                    # Check if this modifier is driven by our source
                    obj_source, obj_source_mod, obj_sync_id = get_source_object_and_modifier(scene_obj, mod)

                    if obj_source == source_obj and obj_source_mod == source_mod:
                        target_modifiers.append((scene_obj, mod))

            # Resync all targets
            if target_modifiers:
                sync_geometry_nodes_modifiers(source_mod, source_obj, target_modifiers, sync_id)
                self.report({'INFO'}, f"Resynced {len(target_modifiers)} modifier(s) with source '{source_mod.name}'")
            else:
                # Just update the source naming
                if not is_source_modifier(source_mod.name):
                    if sync_id is None:
                        sync_id = generate_sync_id()
                    new_name = source_mod.name + get_source_suffix(sync_id)
                    old_name = source_mod.name
                    source_mod.name = new_name
                    for info in source_obj.SyncedModifierInfo:
                        if info.name == old_name:
                            info.name = new_name
                            break
                self.report({'INFO'}, "Updated source modifier naming")

            return {'FINISHED'}

        else:
            # For vanilla modifiers, just report - we don't have the same resync capability
            self.report({'INFO'}, "Resync for vanilla modifiers not yet implemented. Use desync and re-sync instead.")
            return {'FINISHED'}


class RTOOLS_OT_Sync_From_Source(bpy.types.Operator):
    bl_idname = "rtools.sync_from_source"
    bl_label = "Sync from Original Source"
    bl_description = "When syncing from an already-synced object, find and use the original source"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        # Need at least 2 selected objects
        if len(context.selected_objects) < 2:
            return False
        if not context.active_object:
            return False
        return True

    def execute(self, context):
        active = context.active_object
        selected = [obj for obj in context.selected_objects if obj != active]

        if not selected:
            self.report({'WARNING'}, "No target objects selected")
            return {'CANCELLED'}

        # Get the selected modifier from the active object
        if not active.SyncedModifierInfo or active.SyncedModifierIndex < 0:
            self.report({'WARNING'}, "No modifier selected in the synced list")
            return {'CANCELLED'}

        mod_info = active.SyncedModifierInfo[active.SyncedModifierIndex]
        mod_name = mod_info.name

        if mod_name not in [m.name for m in active.modifiers]:
            self.report({'WARNING'}, f"Modifier '{mod_name}' not found")
            return {'CANCELLED'}

        modifier = active.modifiers[mod_name]

        # Check if the active object's modifier is driven by another source
        source_obj, source_mod, sync_id = get_source_object_and_modifier(active, modifier)

        if source_obj is None:
            # Active object is the source, use it directly
            source_obj = active
            source_mod = modifier
            _, sync_id = parse_source_suffix(modifier.name)

        # If we found a different source, use that instead
        if source_obj != active:
            self.report({'INFO'}, f"Using original source: {source_obj.name}")

        # Handle geometry nodes
        if is_geometry_nodes_modifier(source_mod):
            target_modifiers = []
            for obj in selected:
                # Check if target already has a matching modifier
                matching_mod = None
                for mod in obj.modifiers:
                    if mod.type == 'NODES' and mod.node_group == source_mod.node_group:
                        matching_mod = mod
                        break

                if matching_mod is None:
                    # Create new modifier
                    matching_mod = obj.modifiers.new(name=source_mod.node_group.name, type='NODES')
                    matching_mod.node_group = source_mod.node_group

                target_modifiers.append((obj, matching_mod))

            # Sync with original source
            sync_geometry_nodes_modifiers(source_mod, source_obj, target_modifiers, sync_id)

            self.report({'INFO'}, f"Synced {len(target_modifiers)} object(s) with source '{source_obj.name}'")
        else:
            self.report({'WARNING'}, "This operation currently only supports Geometry Nodes modifiers")
            return {'CANCELLED'}

        return {'FINISHED'}

def drawIntoAddMenu(self, context):
    layout= self.layout
    layout.menu("RTOOLS_MT_Synced_Mods_Add_Menu")

class RTOOLS_MT_Synced_Mods_GeoNodes_Menu(bpy.types.Menu):
    bl_label = "Geometry Nodes"

    def draw(self, context):
        layout = self.layout
        layout.operator_context = "INVOKE_DEFAULT"

        # List all geometry node groups (local and linked)
        try:
            # Try different ways to identify GeometryNodeTree for different Blender versions
            node_groups = []
            for ng in bpy.data.node_groups:
                # Check if it's a GeometryNodeTree
                if hasattr(ng, 'bl_idname') and ng.bl_idname == 'GeometryNodeTree':
                    node_groups.append(ng)
                elif ng.__class__.__name__ == 'GeometryNodeTree':
                    node_groups.append(ng)
        except:
            node_groups = []

        if not node_groups:
            layout.label(text="No Geometry Node Groups", icon='INFO')
        else:
            for ng in node_groups:
                op = layout.operator("rtools.add_synced_geonodes",
                                   text=ng.name,
                                   icon='LINKED' if ng.library else 'NODETREE')
                op.node_group_name = ng.name

class ModifierInfo(bpy.types.PropertyGroup):
    name: bpy.props.StringProperty()
    object: bpy.props.PointerProperty(type=bpy.types.Object)
    is_synced: bpy.props.BoolProperty(default=False, description="Whether this modifier is currently synced")
classes = (
    RTOOLS_OT_Add_Modifiers,
    RTOOLS_PT_SM_Addon,
    RTOOLS_MT_Synced_Mods_Add_Menu,
    RTOOLS_MT_Synced_Mods_Deform_Menu,
    RTOOLS_MT_Synced_Mods_Generate_Menu,
    RTOOLS_MT_Synced_Mods_Modify_Menu,
    RTOOLS_MT_Synced_Mods_GeoNodes_Menu,
    ModifierInfo,
    RTOOLS_UL_Synced_Mods_List,
    RTOOLS_OT_Refresh_Synced_Modifiers,
    RTOOLS_OT_Desync_Modifiers,
    RTOOLS_OT_SyncedPanel,
    RTOOLS_OT_Clear_Unused_Drivers,
    RTOOLS_OT_Select_Synced_Objects,
    RTOOLS_OT_Remove_Synced_Modifier,
    RTOOLS_OT_Sync_Modifier_Object,
    RTOOLS_OT_Sync_Existing_Modifiers,
    RTOOLS_OT_Add_Synced_GeoNodes,
    RTOOLS_OT_Sync_GeoNode_Input,
    RTOOLS_OT_Scan_Syncable_Modifiers,
    RTOOLS_OT_Sync_Selected_Modifier,
    RTOOLS_OT_Sync_All_Modifiers,
    RTOOLS_OT_Select_Source_Object,
    RTOOLS_OT_Resync_Modifier,
    RTOOLS_OT_Sync_From_Source,
)

icon_collection={}
addon_keymaps = []

def register():
    from bpy.utils import register_class

    # Register all classes
    for cls in classes:
        try:
            register_class(cls)
        except Exception as e:
            print(f"Failed to register {cls}: {e}")

    # Register keymaps
    try:
        wm = bpy.context.window_manager
        kc = wm.keyconfigs.addon
        kmaps = [
            ("rtools.synced_modifiers_panel","J","ALT"),
        ]

        km = kc.keymaps.new(name="3D View", space_type="VIEW_3D")
        if kc:
            for (op, k, sp) in kmaps:
                kmi = km.keymap_items.new(
                    op,
                    type=k,
                    value="PRESS",
                    alt="alt" in sp.lower(),
                    shift="shift" in sp.lower(),
                    ctrl="ctrl" in sp.lower(),
                )
                addon_keymaps.append((km, kmi))
    except Exception as e:
        print(f"Failed to register keymaps: {e}")

    # Register menu and properties
    try:
        bpy.types.VIEW3D_MT_add.append(drawIntoAddMenu)
    except Exception as e:
        print(f"Failed to register menu: {e}")

    try:
        bpy.types.Object.SyncedModifierInfo = bpy.props.CollectionProperty(type=ModifierInfo)
        bpy.types.Object.SyncedModifierIndex = bpy.props.IntProperty(name="Modifier")
    except Exception as e:
        print(f"Failed to register properties: {e}")

def unregister():
    from bpy.utils import unregister_class

    # Unregister classes
    for cls in reversed(classes):
        try:
            unregister_class(cls)
        except Exception as e:
            print(f"Failed to unregister {cls}: {e}")

    # Unregister keymaps
    try:
        for (km, kmi) in addon_keymaps:
            km.keymap_items.remove(kmi)
        addon_keymaps.clear()
    except Exception as e:
        print(f"Failed to unregister keymaps: {e}")

    # Unregister menu
    try:
        bpy.types.VIEW3D_MT_add.remove(drawIntoAddMenu)
    except Exception as e:
        print(f"Failed to unregister menu: {e}")

if __name__ == "__main__":
    register()

