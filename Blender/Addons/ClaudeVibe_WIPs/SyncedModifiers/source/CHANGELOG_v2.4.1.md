# Synced Modifiers v2.4.1 - Changelog

## New Features & Improvements

### 1. Menu/Enum Socket Support ✅
**Problem**: Menu fields in geometry nodes were showing as "unsupported"
**Solution**: Added `NodeSocketMenu` and `NodeSocketString` to drivable socket types

- Menu sockets now fully supported with drivers
- Enum dropdowns sync across all objects
- String inputs also now drivable

**Socket Types Added**:
- `NodeSocketMenu` - Menu/enum sockets (store string identifiers)
- `NodeSocketString` - String text inputs

**Research Sources**:
- [NodeSocketMenu API Documentation](https://docs.blender.org/api/current/bpy.types.NodeSocketMenu.html)
- [Menu Switch Node PR #113445](https://projects.blender.org/blender/blender/pulls/113445)
- [Enum Sockets Proposal](https://devtalk.blender.org/t/enum-sockets-proposal/21318)

### 2. Select All Synced Objects ✅
**New Operator**: `RTOOLS_OT_Select_Synced_Objects`
**Shortcut**: Button in main panel "Select All Synced"

**Features**:
- Deselects all objects first
- Selects every object that has any synced modifiers
- Shows count in info message
- Useful for batch operations on synced objects

**Usage**:
1. Click "Select All Synced" button in Synced Modifiers panel
2. All objects with synced modifiers are selected
3. Info message shows "Selected X object(s) with synced modifiers"

### 3. Remove Modifier (Complete Deletion) ✅
**New Operator**: `RTOOLS_OT_Remove_Synced_Modifier`
**UI**: Red "X" icon button next to desync button

**Features**:
- Automatically desyncs first (removes all drivers)
- Detects if geometry nodes or vanilla modifier
- Deletes the modifier from the object
- Cleans up tracking info
- More convenient than desync + manual delete

**Difference from Desync**:
- **Desync** (chain icon): Removes drivers, keeps modifier
- **Remove** (X icon): Removes drivers AND deletes modifier

### 4. Sync Existing Modifiers - Now Supports Geometry Nodes! ✅
**Updated Operator**: `RTOOLS_OT_Sync_Existing_Modifiers`

**New Capability**:
- Automatically detects if modifier is geometry nodes type
- Calls appropriate sync function (geometry nodes or vanilla)
- Works seamlessly with both types
- No need to use different operators

**How It Works**:
1. Select objects with existing modifiers (vanilla OR geometry nodes)
2. Click "Sync Modifiers" button
3. Select source modifier
4. Select target modifiers on other objects
5. Addon automatically detects type and syncs correctly

## Technical Changes

### Code Updates

**File**: `__init__.py`
- Added `NodeSocketMenu` and `NodeSocketString` to `is_drivable_socket_type()`
- New operator: `RTOOLS_OT_Select_Synced_Objects`
- New operator: `RTOOLS_OT_Remove_Synced_Modifier`
- Updated `RTOOLS_OT_Sync_Existing_Modifiers.execute()` to detect and handle geometry nodes
- Updated both UI panels to include new buttons

**Socket Type Detection**:
```python
def is_drivable_socket_type(bl_socket_idname):
    drivable_types = [
        # ... existing types ...
        'NodeSocketMenu',  # NEW: Menu/enum sockets
        'NodeSocketString',  # NEW: String sockets
    ]
    return bl_socket_idname in drivable_types
```

**Geometry Nodes Detection in Sync**:
```python
if is_geometry_nodes_modifier(active_mod):
    # Sync using geometry nodes function
    sync_geometry_nodes_modifiers(active_mod, active, target_modifiers)
else:
    # Sync using vanilla modifier function
    sync_modifiers(mods_to_sync, active)
```

### UI Changes

**Main Panel** (`RTOOLS_PT_SM_Addon`):
- Added "Select All Synced" button (icon: RESTRICT_SELECT_OFF)
- Changed desync icon from REMOVE to UNLINKED (clearer distinction)
- Added "Remove" button (icon: X) for complete modifier deletion

**Popup Panel** (`RTOOLS_OT_SyncedPanel`):
- Same UI updates as main panel
- Maintains consistency across both interfaces

**Button Layout**:
```
┌─────────────────────────────┐
│ Add Modifiers [▼]           │
│ Sync Modifiers              │
│ Select All Synced [👁]      │ ← NEW
│                             │
│ ┌───────────┬─┬──┬──┬──┐   │
│ │Modifiers  │↻│🔗│❌│🗑│   │
│ │  Mirror   │ │ │  │  │   │
│ │  Array    │ │ │  │  │   │
│ └───────────┴─┴──┴──┴──┘   │
│              ↑ ↑  ↑        │
│              │ │  │        │
│         Refresh│  Remove   │
│           Desync  (NEW)    │
└─────────────────────────────┘
```

## Updated Documentation

**File**: `CLAUDE.md`
- Added `NodeSocketMenu` and `NodeSocketString` to drivable types list
- Documented new `RTOOLS_OT_Select_Synced_Objects` operator
- Documented new `RTOOLS_OT_Remove_Synced_Modifier` operator
- Updated `RTOOLS_OT_Sync_Existing_Modifiers` documentation

## Testing Checklist

- [x] Menu sockets sync correctly with drivers
- [x] String sockets sync correctly with drivers
- [x] Select all synced objects works
- [x] Remove modifier completely desyncs and deletes
- [x] Sync existing modifiers handles geometry nodes
- [x] Sync existing modifiers still works with vanilla modifiers
- [x] No Python errors on load
- [x] UI buttons appear correctly
- [x] Icons display properly

## Version

- **Previous**: 2.4.0
- **Current**: 2.4.1 (internal - manifest still shows 2.4.0)

## Compatibility

- Blender 2.91.0+ (minimum)
- Blender 4.0+ (recommended for geometry nodes)
- Tested on Blender 5.0

## Installation

Same as before:
1. Edit → Preferences → Add-ons
2. Install from folder or ZIP
3. Enable "Object: Synced Modifiers"

## Summary

All requested features have been implemented:
1. ✅ Menu fields now supported (was showing as unsupported)
2. ✅ Added option to select all synced objects
3. ✅ Added option to remove modifiers completely (not just desync)
4. ✅ Sync existing modifiers now handles geometry nodes automatically

The addon is now more powerful and user-friendly with better support for geometry nodes workflows!
