# Geometry Nodes Support Implementation Plan

## Research Summary

Based on comprehensive research of Blender's Python API and community resources, here's what we've learned about Geometry Nodes:

### Key API Patterns

1. **NodesModifier Access**
   - Geometry Nodes use `bpy.types.NodesModifier` (type='NODES')
   - Has `node_group` property pointing to a GeometryNodeTree
   - Inputs are dynamic IDProperties accessed via bracket notation: `modifier["Input_2"]`

2. **Enumerating Inputs** (Blender 4.0+)
   ```python
   modifier = obj.modifiers["GeometryNodes"]
   node_group = modifier.node_group

   for item in node_group.interface.items_tree:
       if hasattr(item, 'identifier') and item.in_out == 'INPUT':
           identifier = item.identifier  # e.g., "Input_2", "Socket_4"
           socket_type = item.bl_socket_idname  # e.g., "NodeSocketFloat", "NodeSocketObject"
           name = item.name  # User-visible name
   ```

3. **Adding Drivers to Inputs**
   ```python
   # For simple types (Float, Int, Boolean, Color, Vector)
   driver = modifier.driver_add('["Input_2"]')

   # For Vector types with components
   driver = modifier.driver_add('["Input_2"]', 0)  # X component

   # Set up driver variable
   var = driver.driver.variables.new()
   var.targets[0].id = source_object
   var.targets[0].data_path = f'modifiers["{source_mod.name}"]["Input_2"]'
   ```

4. **Socket Type Categories**

   **Drivable Types** (can use standard driver approach):
   - NodeSocketFloat
   - NodeSocketInt
   - NodeSocketBool
   - NodeSocketVector
   - NodeSocketColor
   - NodeSocketRotation
   - NodeSocketString (read-only, but can try)

   **Reference Types** (need sync button like vanilla modifiers):
   - NodeSocketObject
   - NodeSocketCollection
   - NodeSocketMaterial
   - NodeSocketImage
   - NodeSocketTexture

5. **Library-Linked Node Groups**
   - Check with `node_group.library is not None`
   - Linked node groups are read-only
   - BUT modifier inputs can still be set and driven
   - No special handling needed - works the same way

## Implementation Strategy

### Phase 1: Core Geometry Nodes Detection

**File: `__init__.py`**

Add functions to detect and work with geometry nodes modifiers:

```python
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
    for item in node_group.interface.items_tree:
        if hasattr(item, 'identifier') and hasattr(item, 'in_out'):
            if item.in_out == 'INPUT':
                sockets.append({
                    'identifier': item.identifier,
                    'name': item.name,
                    'socket_type': item.socket_type,  # 'GEOMETRY', 'VALUE', 'VECTOR', etc.
                    'bl_socket_idname': item.bl_socket_idname  # Full type name
                })
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
```

### Phase 2: Driver Creation for Geometry Nodes

**File: `__init__.py`**

Create specialized function for adding drivers to geometry node inputs:

```python
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

    if component_count > 0:
        # Vector-like type - drive each component
        for i in range(component_count):
            driver = target_modifier.driver_add(f'["{identifier}"]', i)
            var = driver.driver.variables.new()
            var.name = f"{identifier}_{i}"
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
        var.name = identifier.replace('-', '_')  # Clean name for expression
        var.targets[0].id_type = 'OBJECT'
        var.targets[0].id = source_object
        var.targets[0].data_path = f'modifiers["{source_modifier.name}"]["{identifier}"]'
        driver.driver.expression = var.name
        # Force update trick
        driver.driver.expression += " "
        driver.driver.expression = driver.driver.expression[:-1]

def sync_geometry_nodes_modifiers(source_modifier, source_object, target_modifiers):
    """
    Sync geometry nodes modifiers using drivers.

    Args:
        source_modifier: NodesModifier on source object
        source_object: Source object
        target_modifiers: List of (object, modifier) tuples to sync to
    """
    # Get all input sockets from the node group
    sockets = get_geonode_input_sockets(source_modifier.node_group)

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
            target_obj.SyncedModifierIndex = len(target_obj.SyncedModifierInfo) - 1

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
```

### Phase 3: Operator Updates

**File: `__init__.py`**

Update existing operators to support geometry nodes:

#### RTOOLS_OT_Add_Modifiers
- Detect if adding a 'NODES' type modifier
- After creation, show dialog to select node group
- Sync to selected objects

#### New: RTOOLS_OT_Add_Synced_GeoNodes

```python
class RTOOLS_OT_Add_Synced_GeoNodes(bpy.types.Operator):
    bl_idname = "rtools.add_synced_geonodes"
    bl_label = "Add Synced Geometry Nodes"
    bl_description = "Add a Geometry Nodes modifier with the same node group to selected objects"
    bl_options = {"REGISTER", "UNDO"}

    node_group: bpy.props.PointerProperty(
        type=bpy.types.GeometryNodeTree,
        name="Node Group"
    )

    @classmethod
    def poll(cls, context):
        return context.active_object and len(bpy.data.node_groups) > 0

    def draw(self, context):
        layout = self.layout
        layout.prop(self, "node_group")

    def execute(self, context):
        if not self.node_group:
            self.report({'WARNING'}, "No node group selected")
            return {'CANCELLED'}

        active = context.active_object
        selected = [obj for obj in context.selected_objects if obj != active]

        # Create modifier on active object
        source_mod = active.modifiers.new(
            name=self.node_group.name + "(Source)" if selected else self.node_group.name,
            type='NODES'
        )
        source_mod.node_group = self.node_group

        # Track on source
        info = active.SyncedModifierInfo.add()
        info.name = source_mod.name
        info.object = active
        active.SyncedModifierIndex = len(active.SyncedModifierInfo) - 1

        # Create and sync on selected objects
        if selected:
            target_modifiers = []
            for obj in selected:
                target_mod = obj.modifiers.new(
                    name=self.node_group.name,
                    type='NODES'
                )
                target_mod.node_group = self.node_group
                target_modifiers.append((obj, target_mod))

            # Sync them
            sync_geometry_nodes_modifiers(source_mod, active, target_modifiers)

        return {'FINISHED'}

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)
```

#### Update: RTOOLS_OT_Sync_Existing_Modifiers
- Add support for detecting NODES type modifiers
- When syncing, check if both are NODES type
- Use geometry nodes sync function instead of vanilla sync

### Phase 4: UI Updates

**File: `properties_data_modifiers.py`**

Add UI drawing function for Geometry Nodes:

```python
def NODES(self, layout, ob, md):
    """Draw UI for Geometry Nodes modifier"""
    if md.node_group is None:
        layout.label(text="No node group assigned", icon='ERROR')
        return

    # Show node group name (with library indicator if linked)
    box = layout.box()
    row = box.row()
    if md.node_group.library:
        row.label(text=f"Node Group: {md.node_group.name} (Linked)", icon='LINKED')
    else:
        row.label(text=f"Node Group: {md.node_group.name}", icon='NODETREE')

    # Get all input sockets
    sockets = get_geonode_input_sockets(md.node_group)

    if not sockets:
        layout.label(text="No inputs", icon='INFO')
        return

    # Draw each input
    for socket_info in sockets:
        identifier = socket_info['identifier']
        name = socket_info['name']
        bl_socket_idname = socket_info['bl_socket_idname']

        # Check if this input has a driver
        has_driver = False
        if ob.animation_data and ob.animation_data.drivers:
            for driver in ob.animation_data.drivers:
                if f'modifiers["{md.name}"]["{identifier}"]' in driver.data_path:
                    has_driver = True
                    break

        # Draw based on socket type
        if is_reference_socket_type(bl_socket_idname):
            # Object/Collection/Material - show with sync button
            row = layout.row().split(factor=0.7)
            row.prop(md, f'["{identifier}"]', text=name)

            # Add sync button for reference types
            op = row.operator("rtools.sync_geonode_input", text="Sync")
            op.mod = md.name
            op.object = ob.name
            op.identifier = identifier
            op.socket_type = bl_socket_idname

        elif is_drivable_socket_type(bl_socket_idname):
            # Regular drivable input
            row = layout.row()
            row.prop(md, f'["{identifier}"]', text=name)

            # Show driver indicator
            if has_driver:
                row.label(text="", icon='DRIVER')
        else:
            # Unknown or unsupported type - show read-only
            row = layout.row()
            row.enabled = False
            row.label(text=f"{name}: (Unsupported type)")
```

**File: `__init__.py`**

Add operator for syncing reference-type inputs:

```python
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
            return {'CANCELLED'}

        source_mod = source_obj.modifiers.get(self.mod)
        if not source_mod or source_mod.type != 'NODES':
            return {'CANCELLED'}

        # Get the value from source
        source_value = source_mod[self.identifier]

        # Apply to all objects with same geometry nodes modifier
        for obj in bpy.data.objects:
            for mod in obj.modifiers:
                if mod.type == 'NODES' and mod.node_group == source_mod.node_group:
                    if mod.name in [info.name for info in obj.SyncedModifierInfo]:
                        # This is a synced modifier
                        try:
                            mod[self.identifier] = source_value
                        except:
                            pass  # Input might not exist on this version

        return {'FINISHED'}
```

### Phase 5: Menu Integration

**File: `__init__.py`**

Add Geometry Nodes to the modifier menu:

```python
# Add to existing menu system
class RTOOLS_MT_Synced_Mods_GeoNodes_Menu(bpy.types.Menu):
    bl_label = "Geometry Nodes"

    def draw(self, context):
        layout = self.layout
        layout.operator_context = "INVOKE_DEFAULT"

        # List all geometry node groups (local and linked)
        node_groups = [ng for ng in bpy.data.node_groups if isinstance(ng, bpy.types.GeometryNodeTree)]

        if not node_groups:
            layout.label(text="No Geometry Node Groups", icon='INFO')
        else:
            for ng in node_groups:
                op = layout.operator("rtools.add_synced_geonodes",
                                   text=ng.name,
                                   icon='LINKED' if ng.library else 'NODETREE')
                op.node_group = ng

# Update main menu to include geometry nodes
class RTOOLS_MT_Synced_Mods_Add_Menu(bpy.types.Menu):
    bl_label = "Add Modifiers"

    def draw(self, context):
        layout = self.layout
        layout.operator_context = "INVOKE_DEFAULT"
        layout.menu("RTOOLS_MT_Synced_Mods_Modify_Menu", icon="MESH_DATA")
        layout.menu("RTOOLS_MT_Synced_Mods_Generate_Menu", icon="MOD_TRIANGULATE")
        layout.menu("RTOOLS_MT_Synced_Mods_Deform_Menu", icon="MOD_MESHDEFORM")
        layout.separator()
        layout.menu("RTOOLS_MT_Synced_Mods_GeoNodes_Menu", icon="GEOMETRY_NODES")  # NEW
```

### Phase 6: Edge Cases & Error Handling

1. **Missing Node Group**
   - Check `modifier.node_group is not None` before operations
   - Show warning in UI if node group is None

2. **Node Group Changed**
   - Inputs might have different identifiers after node group update
   - Add "Refresh" operator to rebuild drivers with new identifiers
   - Remove orphaned drivers automatically

3. **Library-Linked Node Groups**
   - No special handling needed
   - Works transparently
   - Show visual indicator in UI (LINKED icon)

4. **Incompatible Socket Types**
   - Skip unsupported types during sync
   - Show as disabled in UI
   - Log warnings for debugging

5. **Driver Update Issues**
   - Use the "expression += space then remove space" trick to force updates
   - Call `bpy.context.view_layer.update()` after creating drivers

### Phase 7: Testing Checklist

- [ ] Local geometry node groups sync correctly
- [ ] Library-linked geometry node groups sync correctly
- [ ] Float inputs drive properly
- [ ] Vector inputs drive all 3 components
- [ ] Boolean inputs toggle correctly
- [ ] Object reference inputs sync with button
- [ ] Collection reference inputs sync with button
- [ ] Material reference inputs sync with button
- [ ] Multiple geometry nodes modifiers on same object
- [ ] Desyncing removes all drivers
- [ ] Refresh handles changed node groups
- [ ] UI shows driver indicators
- [ ] Works with Blender 2.91+ (minimum version)
- [ ] Addon installs via addon menu
- [ ] No errors in console during normal operation

## File Structure Changes

```
SyncedModifiers/
├── __init__.py                    # MODIFIED - add GeoNodes functions and operators
├── properties_data_modifiers.py   # MODIFIED - add NODES() function
├── blender_manifest.toml          # MODIFIED - bump version to 2.4.0
└── CLAUDE.md                      # MODIFIED - document GeoNodes additions
```

## Version Updates

**blender_manifest.toml:**
```toml
version = "2.4.0"
tagline = "Add modifiers to multiple objects and sync them using Drivers (now with Geometry Nodes support!)"
```

**__init__.py:**
```python
"version": (2, 4, 0),
```

## Sources & References

- [NodesModifier API Documentation](https://docs.blender.org/api/current/bpy.types.NodesModifier.html)
- [NodeTreeInterface API](https://docs.blender.org/api/current/bpy.types.NodeTreeInterface.html)
- [API Access for Geometry Node Modifier Inputs](https://blenderartists.org/t/api-access-for-geometry-node-modifier-input-output-attributes/1383622)
- [Creating Inputs/Outputs for Node Groups in Blender 4.0](https://b3d.interplanety.org/en/creating-inputs-and-outputs-for-node-groups-in-blender-4-0-using-the-python-api/)
- [Library Overrides Documentation](https://developer.blender.org/docs/features/core/overrides/library/)
- [Geometry Nodes Modifier Manual](https://docs.blender.org/manual/en/4.3/modeling/modifiers/generate/geometry_nodes.html)
- [Using Drivers with Nodes](https://b3d.interplanety.org/en/using-drivers-with-nodes/)

## Implementation Priority

1. **HIGH**: Core detection and enumeration functions
2. **HIGH**: Driver creation for basic types (Float, Int, Bool)
3. **HIGH**: Vector type support (Vector, Color)
4. **MEDIUM**: Reference type sync buttons (Object, Collection, Material)
5. **MEDIUM**: UI integration
6. **MEDIUM**: Menu system updates
7. **LOW**: Edge case handling and polish
8. **LOW**: Documentation updates
