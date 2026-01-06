# Mass Collection Exporter v12.2

A powerful Blender addon for batch exporting collections with advanced parent-child relationship handling, automatic joining, and flexible export options.
Allows specifying a collection for export with subcollections (Main Collection Env_Buildings > SubCollections Building_01, Building_02, Building_03, etc)

## 📋 Table of Contents

- [Features](#features)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [Main Features](#main-features)
- [Usage Guide](#usage-guide)
- [Export Options](#export-options)
- [Workflow Examples](#workflow-examples)
- [Tips & Best Practices](#tips--best-practices)
- [Troubleshooting](#troubleshooting)

---

## ✨ Features

### Core Functionality
- **Batch Collection Export**: Export multiple collections at once with individual settings
- **Quick Export from Selection**: Export selected object(s), collection, or sub-collections with one click (v12.1+)
- **Smart Empty Handling**: Automatically process parent empties and their children
- **On-Demand Joining**: Join mesh children during export without affecting your scene
- **Multiple Export Formats**: FBX, OBJ, Collada (DAE), and glTF 2.0
- **Flexible Export Modes**: Individual objects, merged collections, or sub-collection based

### Advanced Features
- **Auto-Move to Origin**: Automatically center empties at world origin before export
- **Join ALL Empties**: Combine all empties from a collection into a single mesh
- **Apply Modifiers Option**: Apply modifiers before joining/exporting
- **Material Override**: Batch apply materials to exported objects
- **Transform Options**: Control object transforms, axis orientation, and scaling
- **Fallback Export**: Automatically exports regular meshes if no empties are found

### v12 Updates

**v12.2** (Latest)
✅ **Export Selected Object(s)** - NEW quick export button to export collections of selected objects using their configured settings

**v12.1**
✅ **Quick Export from Selection** - Export collection or sub-collections of selected object with one click

**v12.0**
✅ **Export meshes even when no empties present** - Falls back to normal mesh export
✅ **Improved robustness** - Better error handling and validation
✅ **Enhanced debugging** - Comprehensive debug mode for troubleshooting

---

## 📦 Installation

### Method 1: Direct Install (Recommended)

1. Download `mass_exporter_FIXED_v12.py`
2. Open Blender
3. Go to: **Edit → Preferences → Add-ons**
4. Click **Install...** button
5. Navigate to the downloaded file and select it
6. Enable the addon by checking the checkbox next to "Import-Export: Mass Collection Exporter"

### Method 2: Manual Install

1. Download `mass_exporter_FIXED_v12.py`
2. Locate your Blender addons folder:
   - **Windows**: `%APPDATA%\Blender Foundation\Blender\[version]\scripts\addons\`
   - **macOS**: `~/Library/Application Support/Blender/[version]/scripts/addons/`
   - **Linux**: `~/.config/blender/[version]/scripts/addons/`
3. Copy the file to the addons folder
4. Restart Blender
5. Enable the addon in **Edit → Preferences → Add-ons**

### Verification

After installation, you should see a new **"Mass Exporter"** tab in the 3D Viewport's N-Panel (press `N` to toggle).

---

## 🚀 Quick Start

### Basic Workflow

1. **Open the Panel**: Press `N` in 3D Viewport → Select **Mass Exporter** tab
2. **Add Collections**: Click the `+` button to add collections to export
3. **Select Collection**: Choose a collection from the dropdown
4. **Set Export Path**: Click the folder icon to set the export directory
5. **Enable Export**: Check the export checkbox for the collection
6. **Export**: Click **"Export All Collections"**

### Example: Simple Collection Export

```
1. Add collection "MyProps" to the exporter
2. Enable export checkbox ☑
3. Set export path to: C:/Exports/Props/
4. Choose format: FBX
5. Click "Export All Collections"
→ Result: All mesh objects in "MyProps" exported as individual FBX files
```

---

## 🎯 Main Features

### 1. Collection Management

**Add/Remove Collections**
- Click `+` to add new collection slots
- Click `-` to remove selected collection
- Click refresh icon 🔄 to sync visibility

**Per-Collection Settings**
- **Export Enabled**: Toggle export on/off
- **Visibility**: Control viewport visibility
- **Merge to Single**: Combine all objects into one file
- **Export Path**: Individual export directory per collection

### 2. Parent Empty System

When **"Use Parent Empties"** is enabled:

**What it does:**
- Searches for Empty objects with mesh children
- Uses empty's location as the origin point
- Exports children relative to their parent empty

**Options:**
- **Center Parent Empties**: Move empties to (0,0,0) during export
- **Move Empties to Origin on Export**: Auto-run move operation before export
- **Join Empty Children**: Combine all children into single mesh

**Example Structure:**
```
Collection: "Buildings"
  ├─ Empty: "Building_A" (at position X,Y,Z)
  │   ├─ Mesh: "Wall_01"
  │   ├─ Mesh: "Wall_02"
  │   └─ Mesh: "Roof"
  └─ Empty: "Building_B" (at position X2,Y2,Z2)
      ├─ Mesh: "Foundation"
      └─ Mesh: "Structure"
```

**With Join Enabled** → Exports as:
- `Buildings_joined.fbx` (single file, all buildings merged)

**Without Join** → Exports as:
- `Building_A.fbx` (Wall_01, Wall_02, Roof)
- `Building_B.fbx` (Foundation, Structure)

### 3. Join Empty Children

**The Problem:**
You have multiple empties with children, and you want to export everything as ONE mesh.

**The Solution:**
```
1. Enable: "Join Empty Children"
2. Click: "Export All Collections"
→ Creates temporary duplicates
→ Joins ALL empties together
→ Exports as single file
→ Cleans up (originals untouched)
```

**Advanced Options:**
- **Apply Modifiers Before Join**: Bakes all modifiers before joining
- **Keep Joined Copy**: Optionally keep the joined result in your scene

### 4. Debug Tools

Two powerful debug buttons for testing:

**Move Empties to Origin**
- Moves all empties (from enabled collections) to world origin (0,0,0)
- Useful for: Centering models, preparing for export, testing positions
- Undoable with `Ctrl+Z`

**Join ALL Empties (Create Copies)**
- Creates joined copies without affecting originals
- Useful for: Preview, testing, manual work
- Keeps copies in your scene for inspection

---

## ⚙️ Export Options

### Transform Options

**Export at Origin**
- Moves objects to (0,0,0) before export
- Restores original position after export
- Useful for: Centering models, Unity imports

**Apply Transforms**
- Applies location, rotation, scale to object data
- **Warning**: Permanently modifies objects
- Use for: Baking transforms, clean exports

**Axis Orientation**
- **Forward Axis**: -Z (Unity default), Y, X, etc.
- **Up Axis**: Y (Unity default), Z, etc.
- Match your target engine's coordinate system

### Material Options

**Override Materials**
- Replace all materials with a single material
- Useful for: Placeholder exports, testing

**Assign if No Material**
- Only adds material to objects without one
- Preserves existing materials

**Add M_ Prefix**
- Automatically adds "M_" prefix to material names
- Follows common game engine naming conventions

### FBX Specific Options

**Apply Scaling**
- `FBX Units Scale` ← **Recommended for Unity**
- Controls how scale is baked into the FBX
- Affects import scale in game engines

**Apply Transform**
- Bakes space transform into object data
- **Enable for Unity** to avoid transform issues
- Ensures clean imports without extra transform nodes

**Custom FBX ASCII Exporter**
- Experimental ASCII FBX format
- More export options available
- Use standard exporter unless needed

---

## 📖 Usage Guide

### Scenario 1: Export Individual Objects

**Use Case**: Each object needs to be a separate file

**Setup:**
```
1. Add collection to exporter
2. Enable export ☑
3. Set export path
4. Merge to Single: ☐ (unchecked)
5. Export
```

**Result**: `Object1.fbx`, `Object2.fbx`, `Object3.fbx`...

---

### Scenario 2: Export Collection as Single Mesh

**Use Case**: Combine entire collection into one file

**Setup:**
```
1. Add collection to exporter
2. Enable export ☑
3. Merge to Single: ☑ (checked)
4. Export
```

**Result**: `CollectionName.fbx` (all objects joined)

---

### Scenario 3: Export Sub-Collections Individually

**Use Case**: Each sub-collection becomes one file

**Setup:**
```
1. Add parent collection
2. Enable: "Sub-Collections as Single" ☑
3. Export
```

**Structure:**
```
Collection: "Props"
  ├─ Sub-Collection: "Furniture"
  │   ├─ Chair_01
  │   └─ Table_01
  └─ Sub-Collection: "Decorations"
      ├─ Vase_01
      └─ Picture_01
```

**Result**:
- `Furniture.fbx` (Chair + Table merged)
- `Decorations.fbx` (Vase + Picture merged)

---

### Scenario 4: Export Empty Hierarchies

**Use Case**: Export objects organized under parent empties

**Setup:**
```
1. Add collection
2. Enable: "Use Parent Empties" ☑
3. Enable: "Center Parent Empties" ☑
4. Export
```

**What Happens:**
```
For each Empty:
  1. Move empty to (0,0,0)
  2. Export children
  3. Restore empty position
```

**Best For:**
- Modular assets
- Building systems
- Props with pivot points

---

### Scenario 5: Join ALL Empties Together

**Use Case**: Export entire collection as ONE joined mesh

**Setup:**
```
1. Add collection
2. Enable: "Use Parent Empties" ☑
3. Enable: "Join Empty Children" ☑
4. Optional: "Apply Modifiers Before Join" ☑
5. Export
```

**What Happens:**
```
1. Finds ALL empties in collection
2. Duplicates ALL their children
3. Joins duplicates into ONE mesh
4. Exports single file
5. Cleans up (originals safe)
```

**Example:**
```
Input:
  Empty_A → [Mesh1, Mesh2]
  Empty_B → [Mesh3, Mesh4]
  Empty_C → [Mesh5]

Output:
  CollectionName_joined.fbx (single mesh with Mesh1-5)
```

---

### Scenario 6: Quick Export - Selected Object(s) (v12.2)

**Use Case**: Export the collections containing selected objects, using each collection's normal export settings

**Setup:**
```
1. Select one or more objects from different collections
2. In the Mass Exporter panel, go to "Quick Export from Selection"
3. Click "Export Selected Object(s)"
```

**What Happens:**
```
1. Finds all unique collections from selected objects
2. Exports each collection using its configured settings
3. Respects merge_to_single, export_subcollections_as_single, and all other options
4. Uses parent collection settings if collection not in export list
```

**Example 1 - Objects from Same Collection:**
```
Collection: "Furniture" (merge_to_single: ON)
  ├─ Chair
  ├─ Table  ← Selected
  └─ Lamp   ← Selected

Result: Furniture.fbx (entire collection exported as one file)
```

**Example 2 - Objects from Different Collections:**
```
Collection: "Props" (merge_to_single: OFF)
  ├─ Chair   ← Selected
  └─ Table   ← Selected

Collection: "Decorations" (merge_to_single: ON)
  ├─ Vase    ← Selected
  └─ Picture

Result:
  - Chair.fbx (individual object)
  - Table.fbx (individual object)
  - Decorations.fbx (entire collection merged)
```

**Example 3 - Sub-Collections Mode:**
```
Collection: "Buildings" (export_subcollections_as_single: ON)
  ├─ Sub: "House_A"
  │   └─ Wall_01  ← Selected
  └─ Sub: "House_B"
      └─ Door_01  ← Selected

Result:
  - House_A.fbx (entire sub-collection)
  - House_B.fbx (entire sub-collection)
```

**Best For:**
- Batch exporting multiple collections at once
- Exporting based on what you're currently working on
- Quick workflow without navigating collection list
- Respecting pre-configured collection export settings

---

### Scenario 7: Quick Export - Collection of Selected (v12.1)

**Use Case**: Export the entire collection containing the selected object

**Setup:**
```
1. Select any object
2. Click "Export Collection of Selected"
```

**What Happens:**
```
1. Finds the immediate collection containing selected object
2. Exports entire collection using its configured settings
3. Ignores sub-collections mode (exports as whole)
```

**Best For:**
- Quick export of a specific collection
- Testing without navigating collection list

---

### Scenario 8: Quick Export - Sub-Collections of Selected (v12.1)

**Use Case**: Export all sub-collections of the selected object's collection

**Setup:**
```
1. Select object in parent collection
2. Click "Export Sub-Collections of Selected"
```

**What Happens:**
```
1. Finds collection containing selected object
2. Exports each sub-collection individually
3. Uses parent collection's export settings
```

**Example:**
```
Selected object is in: "Props"
  ├─ Sub: "Furniture" → Exports Furniture.fbx
  ├─ Sub: "Decorations" → Exports Decorations.fbx
  └─ Sub: "Lighting" → Exports Lighting.fbx
```

**Best For:**
- Batch exporting related asset groups
- Quick iteration on modular sets

---

## 💡 Tips & Best Practices

### Unity Export Settings

**Recommended Settings:**
```
✓ Use Parent Empties (if organized with empties)
✓ Center Parent Empties
✓ Apply Scaling: FBX Units Scale
✓ Apply Transform: Enabled
  Forward: -Z
  Up: Y
```

**Why?**
- Ensures proper scale in Unity (1 Blender unit = 1 Unity unit)
- Avoids extra transform nodes
- Matches Unity's coordinate system

### Workflow Tips

**1. Use Collections for Organization**
```
Scene Collection
  ├─ Export_Props (enable in exporter)
  ├─ Export_Buildings (enable in exporter)
  └─ Reference (don't export)
```

**2. Name Empties Meaningfully**
- Empty names become file names
- Use: `Building_House_01` not `Empty.001`

**3. Test with Debug Tools First**
- Use "Move Empties to Origin" to test positions
- Use "Join ALL Empties" to preview joined result
- Then use "Export All" for final export

**4. Apply Modifiers Before Join**
- Mirror, Array, Subdivision modifiers
- Bakes everything before joining
- Ensures correct geometry export

**5. Use Debug Mode**
- Enable "Debug Mode" checkbox
- Watch Console window (Window → Toggle System Console)
- See detailed export information

### Common Patterns

**Pattern 1: Modular Building System**
```
Collection: Buildings
  Empty: "Building_A" → [Walls, Floors, Roof]
  Empty: "Building_B" → [Walls, Floors, Roof]

Settings:
  ☑ Use Parent Empties
  ☑ Center Parent Empties
  ☐ Join Empty Children (each building separate)
```

**Pattern 2: Prop Collection**
```
Collection: Props
  Sub-Collection: Furniture
  Sub-Collection: Decorations
  Sub-Collection: Plants

Settings:
  ☑ Sub-Collections as Single
  ☑ Merge to Single (per sub-collection)
```

**Pattern 3: Complete Scene Export**
```
Collection: Level_01
  Empty: Environment → [Terrain, Trees, Rocks]
  Empty: Buildings → [House, Shop, Tower]

Settings:
  ☑ Use Parent Empties
  ☑ Join Empty Children
  ☑ Apply Modifiers Before Join
  → Result: Level_01_joined.fbx (everything merged)
```

---

## 🐛 Troubleshooting

### Issue: Nothing Exports

**Check:**
1. Is collection selected in dropdown? ✓
2. Is "Export" checkbox enabled? ✓
3. Is export path valid? ✓
4. Does collection have mesh objects? ✓

**Solution:**
- Enable Debug Mode
- Check Console for errors
- Try exporting a single object first

---

### Issue: Empties Not Moving/Joining

**Check:**
1. Is "Use Parent Empties" enabled? ✓
2. Do empties have mesh children? ✓
3. Are empties in enabled collections? ✓

**Solution:**
- Test with "Move Empties to Origin" button first
- Check Console for warnings
- Verify empty-child relationships in Outliner

---

### Issue: Wrong Scale in Unity

**Check:**
1. Apply Scaling setting
2. Apply Transform setting

**Solution:**
```
Set:
  Apply Scaling: FBX Units Scale
  Apply Transform: ☑ Enabled
```

---

### Issue: Joined Export Missing Objects

**Check:**
1. Are all objects MESH type?
2. Are all objects visible?
3. Are objects in correct collection?

**Debug:**
```
1. Enable Debug Mode
2. Run "Join ALL Empties" button
3. Inspect the joined copy before export
4. Check Console output
```

---

### Issue: Export Takes Very Long

**Causes:**
- Many objects
- Heavy modifiers
- Large textures

**Solutions:**
```
1. Use "Apply Modifiers Before Join" sparingly
2. Export in smaller batches
3. Simplify geometry before export
4. Disable texture embedding
```

---

### Issue: Transforms Wrong After Export

**Check:**
1. "Export at Origin" setting
2. "Apply Transforms" setting
3. Parent-child relationships

**Solution:**
```
For Unity:
  ☑ Center Parent Empties
  ☑ Apply Transform (bake_space_transform)
  ☐ Apply Transforms (unless needed)
```

---

## 📝 Version History

### v12.0.0 (Current)
- ✅ **Export meshes even when no empties present**
- ✅ Automatic fallback to normal mesh export
- ✅ Improved error handling and validation
- ✅ Enhanced debug output
- ✅ Better object existence checks

### Previous Versions
- v11: Enhanced empty joining logic
- v10: Added modifier application
- v9: Sub-collection export modes
- v8: Parent empty centering
- v7: Initial release

---

## 🔗 Additional Resources

### Related Documentation
- [Blender FBX Export Documentation](https://docs.blender.org/manual/en/latest/addons/import_export/scene_fbx.html)
- [Unity FBX Import Guide](https://docs.unity3d.com/Manual/ImportingModelFiles.html)

### Common Issues
- Collection visibility affects export
- Hidden objects won't export
- Disabled modifiers won't apply

---

## 📄 License

This addon is created by Claude AI and provided as-is for free use in Blender projects.

---

## 🤝 Support

If you encounter issues:
1. Enable **Debug Mode**
2. Check the **Console** (Window → Toggle System Console)
3. Try the **Debug Tools** buttons first
4. Verify your **collection structure**


---

**Happy Exporting! 🚀**
