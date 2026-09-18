# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

Synced Modifiers is a Blender addon that allows users to add modifiers to multiple objects simultaneously and keep them synchronized using Blender's driver system. The addon creates drivers that link modifier properties from target objects to a source object, ensuring any changes to the source modifier automatically propagate to all synced instances.

## Project Structure

This is a single-directory Blender addon with three core files:

- `__init__.py` - Main addon entry point containing operators, panels, UI, and driver synchronization logic
- `properties_data_modifiers.py` - UI drawing functions for each modifier type's properties panel
- `blender_manifest.toml` - Blender addon manifest (schema version 1.0.0)

## Core Architecture

### Driver-Based Synchronization

The addon uses Blender's driver system to sync modifier properties:

1. **Source Modifier**: Created on the active object, contains the "master" properties
2. **Target Modifiers**: Created on selected objects with drivers pointing to the source
3. **Driver Variables**: Each syncable property gets a driver variable that references the source modifier's property path

The key function `add_driver()` (line 236) creates drivers for each property using the data path pattern: `modifiers["{source_modifier.name}"].{property_name}`

### Modifier Property Filtering

Not all modifier properties can be synced. The addon excludes:

- Object reference fields (curve, object, offset_object, mirror_object, target) - stored in `requiresObject` (line 220) and `mod_object_field` dict (lines 155-172)
- Read-only properties (execution_time, is_cached, vertex_indices, etc.)
- Internal Blender properties (__doc__, bl_rna, rna_type)
- Certain special properties (name, is_active, vertex_group, filepath, driver)

Syncable properties are determined dynamically via `inspect.getmembers()` in the operator execute methods.

### Array Properties

Some modifier properties are arrays/vectors that need special handling. The `array_props` dict (line 221) maps modifier type + property name to array length:

- Example: `'MIRROR_use_axis': 3` means the Mirror modifier's `use_axis` property has 3 elements
- The `do_props()` function (line 222) expands these into indexed properties like `use_axis[0]`, `use_axis[1]`, `use_axis[2]`

### Modifier Categories

Modifiers are organized into four categories (matching Blender's categories):

- `modify_mods` (line 257): Data Transfer, Mesh Cache, Normal Edit, UV Project, Vertex Weight, etc.
- `generate_mods` (line 258): Array, Bevel, Boolean, Mirror, Solidify, Subsurf, etc.
- `deform_mods` (line 259): Armature, Cast, Curve, Hook, Lattice, Shrinkwrap, Wave, etc.
- `physics_mods` (line 260): Cloth, Collision, Fluid, Ocean, Particle System, etc.

Only the first three categories are fully supported for syncing.

## Key Operators

### RTOOLS_OT_Add_Modifiers (`rtools.addsyncedmodifiers`)

Adds a new modifier to the active object and all selected objects, automatically creating drivers.

- Takes a `type` property (modifier type enum like 'ARRAY', 'MIRROR')
- Creates source modifier on active object with "(Source)" suffix if multiple objects selected
- Creates target modifiers on other selected objects
- Calls `add_driver()` to establish property synchronization
- Updates `SyncedModifierInfo` collection property to track synced modifiers

### RTOOLS_OT_Sync_Existing_Modifiers (`rtools.syncexistingmodifiers`)

Syncs existing modifiers between objects without creating new ones.

- Presents dialog with enum properties to select source and target modifiers
- Supports up to 11 objects (1 source + 10 targets) via `mod_1` through `mod_11` properties
- Has `add_new` option to create new modifiers on targets instead of using existing ones
- Validates modifier types match between source and targets
- Follows driver chain if source modifier is itself driven by another object

### RTOOLS_OT_Desync_Modifiers (`rtools.desyncmodifiers`)

Removes drivers from a selected modifier, breaking synchronization.

- Finds all drivers with data paths matching the modifier name pattern
- Removes drivers and updates `SyncedModifierInfo` collection
- Uses `desyncmodifiers()` helper function (line 403)

### RTOOLS_OT_Refresh_Synced_Modifiers (`rtools.refreshsyncedmodifiers`)

Cleans up the synced modifier tracking after manual modifier deletion.

- Iterates all scene objects
- Rebuilds `SyncedModifierInfo` by checking if tracked modifiers still exist
- Should be called after manually deleting modifiers in Blender's modifier panel

### RTOOLS_OT_Clear_Unused_Drivers (`rtools.clearunuseddrivers`)

Removes orphaned drivers that reference deleted modifiers.

- Checks if driver data paths reference modifiers that no longer exist
- Automatically calls refresh before cleanup

### RTOOLS_OT_Sync_Modifier_Object (`rtools.sync_object`)

Syncs object reference fields (like Mirror modifier's mirror_object) across all modifiers of the same type.

- Special operator since object fields can't use drivers
- Triggered from UI buttons in modifier property panels (see `properties_data_modifiers.py`)

## UI Components

### RTOOLS_PT_SM_Addon Panel

Main N-panel located in 3D View sidebar under "Item" category.

- Shows "Add Modifiers" menu for creating new synced modifiers
- Displays `template_list` of synced modifiers on active object
- Shows property panel for selected synced modifier at bottom
- Provides refresh, desync, and cleanup buttons

### RTOOLS_OT_SyncedPanel Operator

Popup version of the main panel, triggered by Alt+J keyboard shortcut.

### Modifier Property Panels

The `properties_data_modifiers.py` file contains drawing functions for each modifier type (ARMATURE, ARRAY, BEVEL, etc.) that are dynamically called via `eval(f'{m.type}(self,box,ob2,ob2.modifiers["{m2}"])')` (lines 315, 369).

## Custom Properties

### Object.SyncedModifierInfo (CollectionProperty)

Tracks which modifiers on an object are synced:

- `name`: Modifier name
- `object`: Pointer to source object (the object whose modifier this one is driven by)

### Object.SyncedModifierIndex (IntProperty)

Active index in the SyncedModifierInfo list, used for UIList selection.

## Development Notes

### Testing Modifier Syncing

When adding support for new modifier types or properties:

1. Check if the property should be excluded (object references, read-only, etc.)
2. For array properties, add entries to `array_props` dict with correct array length
3. Test that drivers are created correctly using Blender's Drivers Editor
4. Verify property changes on source object propagate to targets

### Blender Version Compatibility

- Minimum Blender version: 2.91.0 (specified in both `bl_info` and `blender_manifest.toml`)
- Uses Blender 2.8+ API (bpy.types, bpy.props)
- Driver API is stable across 2.9x-4.x versions

### Icon Mapping

The `icons` dict (lines 173-219) maps modifier type enums to Blender icon identifiers for UI display.

### Helper Functions

- `get_collection()`, `link_to_collection()`, `move_to_collection()` - Collection management utilities
- `delete_object_with_data()`, `delete_collection()` - Cleanup utilities
- `select()`, `deselect_all()` - Object selection helpers
- `sync_modifiers()` (line 108) - Main synchronization function that sets up drivers
- `Diff()` (line 234) - Symmetric difference between lists

## Geometry Nodes Support (v2.4.0+)

The addon now supports syncing Geometry Nodes modifiers using the same driver-based approach as vanilla modifiers.

### Geometry Nodes Architecture

Geometry Nodes modifiers (`type='NODES'`) work differently from vanilla modifiers:

1. **Node Group Reference**: Each modifier has a `node_group` property pointing to a GeometryNodeTree
2. **Dynamic Inputs**: Inputs are exposed as dynamic IDProperties on the modifier, accessed via bracket notation: `modifier["Input_2"]`
3. **Socket Types**: Inputs have different socket types (Float, Vector, Object, Collection, etc.)
4. **Library Support**: Node groups can be linked from external .blend files - works transparently

### Key Functions

#### Detection and Enumeration

**`is_geometry_nodes_modifier(mod)`**
- Returns `True` if modifier is type 'NODES' with a node group assigned

**`get_geonode_input_sockets(node_group)`**
- Iterates `node_group.interface.items_tree` to find all INPUT sockets
- Returns list of dicts with: `identifier`, `name`, `socket_type`, `bl_socket_idname`
- The `identifier` is used to access the input on the modifier (e.g., "Input_2", "Socket_4")

**`is_drivable_socket_type(bl_socket_idname)`**
- Checks if a socket type can be driven (Float, Int, Bool, Vector, Color, Rotation, etc.)
- Returns `True` for types that support driver creation

**`is_reference_socket_type(bl_socket_idname)`**
- Checks if socket is a data-block reference (Object, Collection, Material, Image, Texture)
- These types cannot be driven and need manual sync buttons

**`get_socket_component_count(bl_socket_idname)`**
- Returns 3 for Vector/Color types, 0 for scalars
- Used to determine how many drivers to create (one per component for vectors)

#### Driver Creation

**`add_geonode_driver(target_modifier, source_modifier, source_object, socket_info)`**
- Creates drivers for a single geometry node input
- For vectors, creates one driver per component (X, Y, Z)
- Uses data path pattern: `modifiers["{source_mod.name}"]["{identifier}"]`
- Applies the "expression += space then remove space" trick to force driver updates

**`sync_geometry_nodes_modifiers(source_modifier, source_object, target_modifiers)`**
- Main sync function for geometry nodes
- Verifies all modifiers use the same node group
- Calls `add_geonode_driver()` for each drivable input
- Tracks synced modifiers in `SyncedModifierInfo`

**`desync_geonode_modifier(obj, modifier)`**
- Removes all drivers for a geometry nodes modifier
- Updates `SyncedModifierInfo` tracking

### Operators

#### RTOOLS_OT_Add_Synced_GeoNodes (`rtools.add_synced_geonodes`)

Adds a new Geometry Nodes modifier to active and selected objects with drivers.

- Takes `node_group_name` property (string name of node group)
- Creates source modifier on active object with "(Source)" suffix if multiple objects selected
- Creates target modifiers on other selected objects
- Calls `sync_geometry_nodes_modifiers()` to establish property synchronization

#### RTOOLS_OT_Sync_GeoNode_Input (`rtools.sync_geonode_input`)

Syncs reference-type inputs (Object, Collection, Material) across all synced modifiers.

- Takes `mod`, `object`, `identifier`, and `socket_type` properties
- Copies value from source modifier to all modifiers with the same node group
- Triggered by "Sync" buttons in the UI for reference-type inputs

### UI Components

#### RTOOLS_MT_Synced_Mods_GeoNodes_Menu

Submenu in "Add Modifiers" that lists all available Geometry Node groups.

- Iterates `bpy.data.node_groups` filtering for `bl_idname == 'GeometryNodeTree'`
- Shows LINKED icon for library-linked node groups
- Each entry calls `rtools.add_synced_geonodes` with the node group name

#### NODES() Function (properties_data_modifiers.py)

Draws UI panel for Geometry Nodes modifier inputs.

- Shows node group selector if no node group assigned
- Displays node group name with LINKED indicator if from library
- For each input socket:
  - **Drivable types**: Shows property with DRIVER icon if driven
  - **Reference types**: Shows property + "Sync" button (cannot be driven)
  - **Unsupported types**: Shows as disabled with error icon

### Socket Type Categories

**Drivable Types** (use drivers):
- NodeSocketFloat, NodeSocketInt, NodeSocketBool
- NodeSocketVector, NodeSocketColor, NodeSocketRotation
- NodeSocketFloatFactor, NodeSocketFloatAngle, NodeSocketFloatDistance, NodeSocketFloatTime
- NodeSocketIntFactor, NodeSocketIntUnsigned
- NodeSocketVectorTranslation, NodeSocketVectorDirection, NodeSocketVectorVelocity, NodeSocketVectorAcceleration
- NodeSocketMenu (menu/enum sockets - store string identifiers)
- NodeSocketString (string sockets)

**Reference Types** (use sync buttons):
- NodeSocketObject
- NodeSocketCollection
- NodeSocketMaterial
- NodeSocketImage
- NodeSocketTexture

### Implementation Details

#### Data Path Pattern for Drivers

Geometry node inputs use IDProperty-style data paths:
```python
# For scalar inputs
data_path = f'modifiers["{mod_name}"]["{identifier}"]'

# For vector inputs (component 0)
data_path = f'modifiers["{mod_name}"]["{identifier}"][0]'
```

#### Library-Linked Node Groups

Node groups can be linked from external files:
```python
# Check if linked
if node_group.library is not None:
    # It's linked from external file
    library_path = node_group.library.filepath
```

Linked node groups work identically to local ones - the modifier inputs are still local to the current file and can be driven normally.

#### Blender Version Compatibility

- **Blender 4.0+**: Uses `node_group.interface.items_tree` to enumerate inputs
- **Older versions**: Will gracefully skip if interface API not available (wrapped in try/except)
- Driver system is stable across all supported versions (2.91+)

### Common Workflows

#### Adding Synced Geometry Nodes

1. Select multiple objects (active + targets)
2. Open "Add Modifiers" menu → "Geometry Nodes"
3. Click on a node group name
4. Source modifier created on active object with "(Source)" suffix
5. Target modifiers created on other objects with drivers automatically set up

#### Syncing Reference-Type Inputs

1. Select object with synced Geometry Nodes modifier
2. In N-Panel, find the modifier in the synced list
3. Set Object/Collection/Material input to desired value
4. Click "Sync" button next to the input
5. Value propagates to all synced modifiers with the same node group

#### Desyncing Geometry Nodes

1. Select modifier in synced modifiers list
2. Click the remove icon (trash/X button)
3. All drivers for that modifier are removed
4. Modifier remains but is no longer synced

### Edge Cases Handled

- **Missing Node Group**: Shows error and node group selector
- **Library-Linked Groups**: Works transparently, shows LINKED icon
- **Different Node Groups**: Skips syncing if target has different group
- **Unsupported Socket Types**: Shows as disabled in UI
- **Changed Node Group**: Drivers may reference non-existent inputs (handled gracefully)
- **Vector Components**: Creates separate driver for each X, Y, Z component

## Additional Operators

### RTOOLS_OT_Select_Synced_Objects (`rtools.select_synced_objects`)

Selects all objects in the scene that have synced modifiers.

- Deselects all objects first
- Iterates through scene objects checking for `SyncedModifierInfo`
- Selects any object with at least one synced modifier
- Reports count of selected objects
- Useful for quickly finding all objects involved in syncing

**UI Location**: Main panel button "Select All Synced" with SELECT icon

### RTOOLS_OT_Remove_Synced_Modifier (`rtools.remove_synced_modifier`)

Removes a modifier completely (both desync and delete).

- First desyncs the modifier (removes drivers and tracking)
- Detects if it's a geometry nodes modifier or vanilla modifier
- Calls appropriate desync function
- Then removes the modifier from the object entirely
- Cleans up tracking even if modifier is already gone
- More convenient than desyncing then manually deleting

**UI Location**: Modifier list sidebar with "X" icon (red delete button)

### Updated: RTOOLS_OT_Sync_Existing_Modifiers

Now supports both vanilla and geometry nodes modifiers.

- Automatically detects if source modifier is geometry nodes type
- Calls `sync_geometry_nodes_modifiers()` for NODES type
- Calls `sync_modifiers()` for vanilla modifiers
- Works transparently - user doesn't need to know the type
- Allows syncing existing geometry nodes without creating new ones

## Version 2.5.0 Features (January 2025)

### Sync ID System

Source modifiers now include a unique sync ID in their name for reliable identification:

- **Format**: `ModifierName (Source:abc123)` where `abc123` is a 6-character hash
- **Purpose**: Uniquely identifies which source drives which targets
- **Helper Functions**:
  - `generate_sync_id()`: Creates a new 6-character unique ID
  - `get_source_suffix(sync_id)`: Returns ` (Source:ID)` suffix string
  - `parse_source_suffix(name)`: Extracts (base_name, sync_id) from modifier name
  - `is_source_modifier(name)`: Checks if name has source suffix
  - `get_source_object_and_modifier(obj, mod)`: Traces back to find the source

### Viewport Update Fix

Object/Collection/Material reference fields in geometry nodes cannot use drivers.
After syncing these fields, the viewport now properly updates:

- `force_modifier_update(obj, mod)`: Toggles modifier's `show_viewport` off/on
- `force_object_update(obj)`: Calls `update_tag()` and `view_layer.update()`
- Applied automatically in `RTOOLS_OT_Sync_GeoNode_Input` operator

### New Operators

#### RTOOLS_OT_Select_Source_Object (`rtools.select_source_object`)

Selects the source object that drives a synced modifier.

- Traces back through drivers to find the original source
- If current object IS the source, reports that information
- Deselects all and selects/activates the source object
- **UI**: Icon button (OBJECT_DATA) in sidebar

#### RTOOLS_OT_Resync_Modifier (`rtools.resync_modifier`)

Re-syncs modifiers to add missing drivers for new inputs.

**Use Cases**:
- New fields added to geometry nodes after initial sync
- Upgrade old "(Source)" naming to new "(Source:ID)" format
- Fix broken driver connections

**Behavior**:
- Finds all targets currently driven by the source
- Re-runs `sync_geometry_nodes_modifiers()` to add missing drivers
- Updates source naming if sync ID is missing
- **UI**: Icon button (UV_SYNC_SELECT) in sidebar

#### RTOOLS_OT_Sync_From_Source (`rtools.sync_from_source`)

Syncs new objects using the original source (via an already-synced object).

**Use Case**: User selects an already-synced object and a new object, wants to sync
the new object with the ORIGINAL source, not with the selected synced object.

**Behavior**:
- Detects if selected "source" is actually a target
- Traces back to find the original source object/modifier
- Syncs new targets with the original source
- **UI**: Button appears when 2+ objects selected: "Sync From Original Source"

### UI Improvements

- **Wider List**: Template list now uses 85% of horizontal space
- **Narrower Buttons**: Sidebar buttons use 15% and have `scale_x = 0.8`
- **Compact Top Row**: Scan and Select All buttons share a row
- **New Sidebar Buttons**:
  - Resync (UV_SYNC_SELECT icon)
  - Select Source (OBJECT_DATA icon)
- **Conditional Button**: "Sync From Original Source" only shows when 2+ objects selected

### Updated sync_geometry_nodes_modifiers()

Now accepts optional `sync_id` parameter and handles source naming:

```python
def sync_geometry_nodes_modifiers(source_modifier, source_object, target_modifiers, sync_id=None):
```

**Behavior**:
- Generates sync_id if not provided and source doesn't have one
- Adds `(Source:ID)` suffix to source modifier name
- Upgrades old `(Source)` format to new `(Source:ID)` format
- Returns the sync_id used for further operations

### Helper Functions Added

```python
# Pattern for matching source suffix
SOURCE_SUFFIX_PATTERN = regex.compile(r'\s*\(Source(?::([a-zA-Z0-9]+))?\)$')

# Generate unique 6-character sync ID
def generate_sync_id() -> str

# Get suffix string like " (Source:abc123)"
def get_source_suffix(sync_id: str = None) -> str

# Parse modifier name -> (base_name, sync_id or None)
def parse_source_suffix(modifier_name: str) -> tuple

# Check if modifier name indicates it's a source
def is_source_modifier(modifier_name: str) -> bool

# Find source object/modifier from a synced modifier
def get_source_object_and_modifier(obj, modifier) -> tuple

# Find all modifiers with a given sync ID
def find_synced_modifiers_by_sync_id(sync_id, node_group=None) -> list

# Force viewport refresh for a modifier
def force_modifier_update(obj, modifier) -> None

# Force object update via depsgraph
def force_object_update(obj) -> None
```
