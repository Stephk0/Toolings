# Mass Collection Exporter v13.9.0

A powerful Blender addon for batch exporting collections with advanced parent-child relationship handling, automatic joining, and flexible export options.
Allows specifying a collection for export with subcollections (Main Collection Env_Buildings > SubCollections Building_01, Building_02, Building_03, etc)

> 📘 **New:** Step-by-step tutorial with screenshots: [TUTORIAL.md](TUTORIAL.md)
>
> **Export flow diagrams:** [EXPORT_FLOW.md](EXPORT_FLOW.md) — mermaid charts of the mode priority order and the shared export tail
>
> **v13.9.0:** a parent empty is one asset — **Use Parent Empties** writes one file per empty (Join makes it one mesh). **Move to Center** is the only centring option and works with Apply Transforms. **Materials** is one choice: Keep / Fill Empty / Overwrite. Relative `//` export paths work, hidden objects no longer stay selected after an export, and Export Hidden Collections off skips hidden sub-collections too. See the [changelog](source/CHANGELOG.md).
>
> **v13.7.0:** new **Only Visible Modifiers** option (Modifier & Rig Options → Modifiers, **on by default**). Exports now bake only the modifiers that are enabled in the viewport, matching what you actually see. ⚠️ This changes export output for objects that carry viewport-disabled modifiers — see [Only Visible Modifiers](#only-visible-modifiers-v1370).
>

## 📋 Table of Contents

- [Features](#-features)
- [Installation](#-installation)
- [Quick Start](#-quick-start)
- [Main Features](#-main-features)
- [Export Options](#️-export-options)
- [Usage Guide](#-usage-guide)
- [Tips & Best Practices](#-tips--best-practices)
- [Troubleshooting](#-troubleshooting)

---

## ✨ Features

### Core Functionality
- **Batch Collection Export**: Export multiple collections at once with individual settings
- **Quick Export from Selection**: Export selected object(s), collection, or sub-collections with one click (v12.1+)
- **Smart Empty Handling**: Automatically process parent empties and their children
- **On-Demand Joining**: Join mesh children during export without affecting your scene
- **Multiple Export Formats**: FBX, OBJ and glTF 2.0 (binary `.glb`)
- **Flexible Export Modes**: Individual objects, merged collections, or sub-collection based

### Advanced Features
- **Move to Center**: Every exported asset lands at the world origin while it stays lined up in your scene
- **Join Empty Children**: Turn each parent empty's meshes into one mesh
- **Apply Modifiers Option**: Apply modifiers before joining/exporting
- **Materials**: Keep, fill empty slots, or overwrite with one material
- **Transform Options**: Control object transforms, axis orientation, and scaling
- **Fallback Export**: Automatically exports regular meshes if no empties are found

## 📦 Installation

### Method 1: Direct Install (Recommended)

1. Download the latest zip from `distribution/` (`MassExporter_v13.9.0.zip`)
2. Open Blender
3. Go to: **Edit → Preferences → Add-ons**
4. Click **Install...** button
5. Navigate to the downloaded file and select it
6. Enable the addon by checking the checkbox next to "Import-Export: Mass Collection Exporter"

### Method 2: Manual Install

1. Download the latest zip from `distribution/` (`MassExporter_v13.9.0.zip`)
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

**Per-Collection Settings**
- **Export Enabled**: Toggle export on/off
- **Visibility**: The eye icon mirrors the outliner eye of the collection
- **Merge to Single**: Combine all objects into one file
- **Export Path**: Individual export directory per collection

### 2. Parent Empty System

When **"Use Parent Empties"** is enabled:

**What it does:**
- A parent empty is one asset: everything under it goes into **one file named after the empty**
- Searches for Empty objects with mesh children (grandchildren included — each mesh belongs to its nearest empty)
- The empty is the asset's origin; with **Move to Center** it sits at (0,0,0) in the file
- Meshes that sit under no empty are still exported: one file each, or merged into `<collection>.fbx` with **Merge** on

**Options:**
- **Join Empty Children**: the empty's meshes become one mesh named after the empty (off: they stay separate elements inside the file)

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

**Without Join** → Exports as:
- `Building_A.fbx` (Wall_01, Wall_02, Roof as separate meshes)
- `Building_B.fbx` (Foundation, Structure)

**With Join Enabled** → Exports as:
- `Building_A.fbx` (one mesh `Building_A`, origin at the empty)
- `Building_B.fbx` (one mesh `Building_B`)

### 3. Join Empty Children

**The Problem:**
Each asset is built from several meshes under an empty, and the engine should get ONE mesh per asset.

**The Solution:**
```
1. Enable: "Use Parent Empties" and "Join Empty Children"
2. Click: "Export All Collections"
→ Creates temporary duplicates
→ Joins each empty's meshes into one mesh named after the empty
→ One file per empty
→ Cleans up (originals untouched)
```

To join a whole sub-collection into one mesh instead, use **Sub-Collections as Single** together with Use Parent Empties + Join.

**Advanced Options:**
- Every child bakes its **own** modifier stack before the join when *Apply Modifiers* (here or the global one) is on; otherwise modifiers are left out
- Viewport-disabled modifiers are skipped when the global *Only Visible Modifiers* is on, or when this collection's *Only Visible Modifiers* is ticked

### 4. Debug Tools

Two powerful debug buttons for testing:

**Move Empties to Origin**
- Moves all empties (from enabled collections) to world origin (0,0,0), parented empties included
- Useful for: Centering models, preparing for export, testing positions
- Undoable with `Ctrl+Z`

**Join ALL Empties (Create Copies)**
- Creates joined copies without affecting originals
- Useful for: Preview, testing, manual work
- Keeps copies in your scene for inspection

---

## ⚙️ Export Options

### Transform Options

**Move to Center** (per collection)
- The one centring option: each exported asset is placed at (0,0,0) in its file
- An asset under a parent empty is moved by its empty, so its parts keep their layout; anything else is moved by its own origin
- Your scene is restored after the export, so assets can stay lined up side by side in Blender
- Works together with Apply Transforms

**Apply Transforms**
- Bakes location, rotation, scale into the exported mesh
- Runs on temporary copies — your objects are not changed
- Works in every mode, including *Whole Collection as One File* (children stay parented)

**Axis Orientation**
- **Forward Axis**: -Z (Unity default), Y, X, etc.
- **Up Axis**: Y (Unity default), Z, etc.
- Match your target engine's coordinate system

### Material Options

All material options only affect the exported file — your scene's materials and their names are restored right after each export.

**Materials** — pick one:
- **Keep**: every object keeps its own materials (default)
- **Fill Empty**: existing materials stay; objects and empty slots without a material get the Override Material. In a joined mesh each part is filled before the join, so a collision mesh never borrows another part's material
- **Overwrite**: every material is replaced by the Override Material — useful for placeholder exports and tests

**Add M_ Prefix**
- Adds the "M_" prefix to the names of the exported objects' materials
- Follows common game engine naming conventions

### Modifier Options

Panel: **Modifier & Rig Options → Modifiers**

**Apply Modifiers**
- Bakes object modifiers into the exported mesh
- Always runs on a temporary copy — your source objects are never modified
- Also works on meshes with shape keys (the shape keys are baked at their current values, as every exporter does once modifiers are applied)

#### Only Visible Modifiers (v13.7.0)

- **Default: ON**
- Only bakes modifiers whose **viewport toggle (monitor icon) is enabled**
- Greyed out unless *Apply Modifiers* is on

**Why this option exists.** Blender's own `Apply Modifier` operator has no notion
of the viewport toggle — it bakes a modifier that is switched *off* in the stack
exactly as if it were on. So "apply all modifiers" silently produced geometry
that never matched the viewport. Measured on a cube with a visible Subsurf and a
disabled 3× Array:

| | Vertices |
|---|---|
| What the viewport shows | 26 |
| Vanilla "apply all modifiers" | **78** ← the disabled Array got baked |
| *Only Visible Modifiers* ON | 26 ✅ |

**The workaround.** Modifiers disabled in the viewport are **deleted from the
temporary export copy before anything is applied**. Deleting rather than skipping
matters: whatever sits *after* a stripped modifier then evaluates on the previous
result, which is exactly the stack the viewport evaluates. The source object's
modifier stack is never touched.

**Exception — armature bindings.** An Armature modifier that is preserved for rig
binding (rig included in the export, and *Skip Armature Modifier* off) is never
stripped, even when its viewport toggle is off. Removing it would silently unbind
the mesh from its rig in the FBX.

**Turn it OFF** to restore the pre-v13.7 behaviour of baking every modifier
regardless of visibility.

> The **Join Empty Children** path follows this setting too. Its per-collection
> **Only Visible Modifiers** checkbox only matters when this global one is off.

---

### FBX Specific Options

**Apply Scaling**
- `FBX Units Scale` ← **Recommended for Unity**
- Controls how scale is baked into the FBX
- Affects import scale in game engines

**Apply Transform**
- Bakes space transform into object data
- **Enable for Unity** static meshes to avoid the -90° rotation
- Blender marks it experimental: it **moves child objects** in any parent hierarchy (an asset under an empty, a mesh parented to a mesh), and breaks rigs and animation. Checked in Unity 6: for hierarchies turn it off, set Forward **Y** / Up **Z** (Blender's default), and tick **Bake Axis Conversion** in Unity's model importer — the hierarchy is correct and objects come in upright. Assets then face the other way round than with Apply Transform on, so check facing before switching an existing project

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
3. Keep: "Move to Center" ☑
4. Export
```

**What Happens:**
```
For each Empty:
  1. Move empty to (0,0,0)
  2. Export everything under it into <empty>.fbx
  3. Restore empty position
```

**Best For:**
- Modular assets
- Building systems
- Props with pivot points

---

### Scenario 5: One Joined Mesh per Empty

**Use Case**: Each asset under an empty becomes ONE mesh

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
For each Empty:
  1. Duplicates its meshes
  2. Joins the duplicates into ONE mesh named after the empty
  3. Exports <empty>.fbx, origin at the empty
  4. Cleans up (originals safe)
```

**Example:**
```
Input:
  Empty_A → [Mesh1, Mesh2]
  Empty_B → [Mesh3, Mesh4]
  Empty_C → [Mesh5]

Output:
  Empty_A.fbx, Empty_B.fbx, Empty_C.fbx (one mesh each)
```

For one joined mesh per sub-collection, also enable **Sub-Collections as Single**.

---

### Scenario 6: Quick Export - Selected Object(s) (v12.2)

**Use Case**: Export only the selected objects, using the settings of the collection they live in

**Setup:**
```
1. Select one or more objects from different collections
2. In the Mass Exporter panel, go to "Quick Export from Selection"
3. Click "Export Selected Object(s)"
```

**What Happens:**
```
1. Groups the selected meshes by the collection they live in
2. Per collection, only the selected meshes are exported:
   - Group by Suffix on (with an enabled suffix) → one file per base name
   - Merge on (2+ selected) → one file `<collection>_selected`
   - otherwise → one file per selected object
3. If the parent collection has Sub-Collections as Single on, the whole sub-collection is exported instead
4. Uses parent collection settings if collection not in export list
```

**Example 1 - Objects from Same Collection:**
```
Collection: "Furniture" (merge_to_single: ON)
  ├─ Chair
  ├─ Table  ← Selected
  └─ Lamp   ← Selected

Result: Furniture_selected.fbx (Table + Lamp merged)
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
  - Vase.fbx (only one object selected)
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
✓ Move to Center
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
  ☑ Move to Center
  ☐ Join Empty Children (each building's parts stay separate)
  → Result: Building_A.fbx, Building_B.fbx
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
  ☑ Sub-Collections as Single
  ☑ Use Parent Empties
  ☑ Join Empty Children
  ☑ Apply Modifiers Before Join
  → Result: one merged mesh per sub-collection
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
1. "Move to Center" setting
2. FBX "Apply Transform" — it misplaces children in a hierarchy
3. Parent-child relationships

**Solution:**
```
For Unity, assets with a hierarchy:
  ☑ Move to Center
  ☐ Apply Transform (bake_space_transform)
  Forward: Y   Up: Z
  → In Unity: Bake Axis Conversion ☑
```

---

## 🔗 Additional Resources

### Related Documentation
- [Blender FBX Export Documentation](https://docs.blender.org/manual/en/latest/addons/import_export/scene_fbx.html)
- [Unity FBX Import Guide](https://docs.unity3d.com/Manual/ImportingModelFiles.html)

### Common Issues
- Hidden collections/objects ARE exported by default since v13.6 ("Export Hidden Collections" toggle) — disable it to skip them, hidden sub-collections and hidden objects of an exported collection included
- Export paths may be relative (`//Exports/`): they resolve next to the saved .blend file
- Disabled modifiers won't apply

---

## 📄 License

Free for personal and commercial use. Provided as-is, no warranty.

---

## 🤝 Support

If you encounter issues:
1. Enable **Debug Mode**
2. Check the **Console** (Window → Toggle System Console)
3. Try the **Debug Tools** buttons first
4. Verify your **collection structure**

---

**Happy Exporting! 🚀**

---

[Changelog](source/CHANGELOG.md)
