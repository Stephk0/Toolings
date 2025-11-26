# Compositor Render Sets

![Version](https://img.shields.io/badge/version-1.0.0-blue)
![Blender](https://img.shields.io/badge/blender-4.0+-orange)

**Author:** Claude AI + Stephan Viranyi
**Category:** Render
**License:** GPL v2

---

## 🎯 Overview

**Compositor Render Sets** is a powerful Blender addon that enables you to render multiple collection configurations through the compositor automatically. It manages File Output nodes, controls collection visibility, and organizes your render pipeline into discrete "Render Sets."

### The Problem

When creating complex scenes with multiple variations (characters, props, lighting setups), you often need to:
- Render different collection combinations separately
- Output each variation with different file names
- Manually toggle visibility and adjust compositor settings
- Keep track of which collections belong to which render pass

### The Solution

Compositor Render Sets automates this entire workflow:
- ✅ Define **Render Sets** - groups of collections with unique names and output paths
- ✅ Automatically configures a **File Output node** in the compositor
- ✅ Renders each set with **one click** (or render multiple sets in batch)
- ✅ Controls **collection visibility** per set with Show/Hide/Solo tools
- ✅ **Restores** compositor settings after rendering
- ✅ **Logs** all render operations for tracking

---

## 📦 Installation

### Method 1: Install from File
1. Download `compositor_render_sets.py`
2. Open Blender (version 4.0 or later)
3. Go to `Edit` → `Preferences` → `Add-ons`
4. Click `Install...` button
5. Navigate to and select `compositor_render_sets.py`
6. Enable the checkbox next to **"Render: Compositor Render Sets"**

### Method 2: Manual Installation
1. Copy `compositor_render_sets.py` to Blender's addons folder:
   - **Windows:** `%APPDATA%\Blender Foundation\Blender\[version]\scripts\addons\`
   - **macOS:** `~/Library/Application Support/Blender/[version]/scripts/addons/`
   - **Linux:** `~/.config/blender/[version]/scripts/addons/`
2. Restart Blender
3. Enable in Preferences → Add-ons

### Verification

After installation, press `N` in the 3D Viewport to open the sidebar. You should see a new tab: **"Compositor Render Sets"**

---

## 🚀 Quick Start

### Setup Workflow

1. **Setup Compositor:**
   - Switch to Compositing workspace
   - Enable `Use Nodes`
   - Add a **File Output** node
   - Rename it to `RenderSetOutput` (or your custom name)
   - Connect render layers to the File Output node
   - Name the input slots with a prefix like `XXX_Beauty`, `XXX_Mask`, etc.

2. **Create Render Sets:**
   - Open the 3D Viewport sidebar (`N` key)
   - Go to **Compositor Render Sets** tab
   - Click **Add Set**
   - Name your render set (e.g., "Character_Front")
   - Set the output path
   - Add collections to the set

3. **Render:**
   - Click **Render Current Set**
   - The addon will automatically:
     - Show only the collections in the set
     - Configure the File Output node
     - Render the scene
     - Restore settings

---

## 📖 Features Guide

### 1. Render Set Setup

#### Creating Render Sets

**Render Sets** are groups of collections with:
- **Name:** Used in file naming (replaces prefix in File Output slots)
- **Output Path:** Directory where renders are saved
- **Collections:** List of collections to show/hide for this set
- **Enabled Toggle:** Include/exclude from batch renders

**Workflow:**
1. Click `Add Set` button
2. Click the tab with the set name to make it active
3. Configure the set:
   - Change the name
   - Browse to output directory
   - Add collections via `Add Collection` button

#### Managing Collections in Sets

- **Add Collection:** Opens a dialog to pick from scene collections
- **Remove Collection:** Click the `X` icon next to a collection in the list
- Collections can be in multiple render sets

---

### 2. Visibility Controls

#### Show/Hide Set

Toggles the viewport visibility of all collections in the current set.

**Use Cases:**
- Quickly preview what will be rendered
- Toggle between different set configurations
- Work on specific parts of the scene

**Behavior:**
- First press: Hides all collections in the set
- Second press: Shows all collections in the set
- Does not affect collections outside the set

#### Solo Set

Shows **only** the collections in the current set, hides everything else.

**Use Cases:**
- Isolate a render set for focused work
- Preview exactly what will render
- Compare different sets visually

**Behavior:**
- First press: Hides all collections except those in the current set
- Second press: Restores previous visibility states
- Caches original visibility to allow toggling

---

### 3. Rendering

#### Render Current Set

Renders the currently active render set (the selected tab).

**Steps:**
1. Select a render set by clicking its tab
2. Click `Render Current Set`
3. The addon will:
   - Set collection visibility for this set
   - Configure the File Output node
   - Trigger a render
   - Restore settings

#### Render Selected Sets

Renders all sets that have **Enabled for Render** checked.

**Use Cases:**
- Batch render multiple variations
- Render only specific sets while skipping others
- Queue multiple renders with one click

**Workflow:**
1. Check the `Enabled for Render` toggle on each set you want to render
2. Click `Render Selected Sets`
3. Each enabled set renders in sequence

#### Render All Sets

Renders **all** render sets regardless of the enabled toggle.

**Use Cases:**
- Full batch render of all variations
- Comprehensive export of all sets

---

### 4. Settings

#### Output Node Name

**Default:** `RenderSetOutput`

The name of the **File Output** node in the compositor that the addon will manipulate.

**Setup:**
1. In the Compositor, add a File Output node
2. Rename it to match this setting
3. The addon will find and configure this node during renders

#### Name Prefix

**Default:** `XXX`

The prefix used in File Output node input slot names for automatic renaming.

**How It Works:**
- File Output slots starting with this prefix will be renamed during render
- The prefix is replaced with the **Render Set Name**
- Everything after the prefix is preserved

**Example:**
- Prefix: `XXX`
- File Output slot name: `XXX_Beauty`
- Render Set name: `Character_A`
- Resulting output file: `Character_A_Beauty`

**Another Example:**
- Prefix: `XXX`
- Slots: `XXX_Beauty`, `XXX_Mask`, `XXX_Normal`
- Render Set: `Prop_Chair`
- Outputs: `Prop_Chair_Beauty`, `Prop_Chair_Mask`, `Prop_Chair_Normal`

#### Sync Renderer to Viewport Visibility

**Default:** Enabled

When enabled, the addon syncs `hide_render` to match `hide_viewport` for all collections before rendering.

**Effect:**
- What you see in the viewport is what renders
- Collections hidden in viewport won't render (even if `hide_render` is off)
- Collections shown in viewport will render (even if `hide_render` is on)

**When Disabled:**
- The addon only controls viewport visibility
- Render visibility is not modified
- Use this if you have custom render visibility setups

#### Enable Log

**Default:** Enabled

Controls whether render operations are logged in the Log section.

**Logged Information:**
- Timestamp of each operation
- Render Set name
- Output path used
- List of output file names generated
- Success/error messages

---

### 5. Log

The log section displays recent render operations with timestamps.

**Information Shown:**
- When each render started
- Which render set was processed
- Output directory path
- List of output file names
- Any errors or warnings

**Controls:**
- `Clear` button (X icon) - Clears all log entries

**Example Log Entries:**
```
[2025-01-17 14:32:15] Added new render set: RenderSet_1
[2025-01-17 14:33:42] Added collection 'Characters' to 'RenderSet_1'
[2025-01-17 14:35:10] Starting render for set: Character_Front
[2025-01-17 14:35:12] Rendered 'Character_Front' to '//exports/characters/'. Outputs: Character_Front_Beauty, Character_Front_Mask
[2025-01-17 14:35:12] File Output node restored to original state
```

---

## 🎓 Detailed Workflow Example

### Scenario: Character Render Variations

You have a character model and want to render it from multiple angles with different lighting setups.

#### Setup

1. **Collections:**
   - `Character_Mesh`
   - `Lights_Front`
   - `Lights_Side`
   - `Lights_Back`
   - `Environment`

2. **Compositor Setup:**
   - Add File Output node, rename to `RenderSetOutput`
   - Create input slots:
     - `XXX_Beauty` - connected to Image socket
     - `XXX_Depth` - connected to Depth socket
     - `XXX_Normal` - connected to Normal socket

3. **Create Render Sets:**

   **Set 1: "Character_Front"**
   - Output Path: `//renders/front/`
   - Collections: `Character_Mesh`, `Lights_Front`, `Environment`
   - Enabled: ✓

   **Set 2: "Character_Side"**
   - Output Path: `//renders/side/`
   - Collections: `Character_Mesh`, `Lights_Side`, `Environment`
   - Enabled: ✓

   **Set 3: "Character_Back"**
   - Output Path: `//renders/back/`
   - Collections: `Character_Mesh`, `Lights_Back`, `Environment`
   - Enabled: ✓

#### Rendering

**Option 1: Render one set**
1. Click the `Character_Front` tab
2. Click `Render Current Set`

**Result:**
- Files saved to `//renders/front/`:
  - `Character_Front_Beauty.png`
  - `Character_Front_Depth.png`
  - `Character_Front_Normal.png`

**Option 2: Render all enabled sets**
1. Ensure all three sets have `Enabled for Render` checked
2. Click `Render Selected Sets`

**Result:**
- All three sets render in sequence
- Each outputs to its respective directory with proper naming

---

## ⚙️ Technical Details

### Compositor Integration

The addon manipulates the **File Output** node in the compositor:

1. **Discovery:**
   - Searches scene.node_tree for a node of type `OUTPUT_FILE`
   - Matches by the name specified in settings

2. **State Caching:**
   - Before rendering, caches:
     - Original `base_path`
     - Original file slot names/paths

3. **Configuration:**
   - For each render set:
     - Sets `base_path` to the render set's output path
     - Renames file slots that start with the prefix
     - Replaces prefix with render set name

4. **Restoration:**
   - After all renders complete:
     - Restores `base_path` to original
     - Restores all file slot names to original

### Visibility Management

**Viewport Visibility:**
- Controlled via `collection.hide_viewport`
- Modified by Show/Hide and Solo operators
- Can be synced to render visibility

**Render Visibility:**
- Controlled via `collection.hide_render`
- Optionally synced from viewport visibility (if setting enabled)
- Original states are cached and restored

**Solo Mode:**
- Caches all collection visibility states as JSON
- Hides all collections, shows only the set's collections
- Toggling again restores cached states

---

## 🔧 Troubleshooting

### Issue: "File Output node 'RenderSetOutput' not found"

**Cause:** No File Output node with the specified name exists in compositor

**Solution:**
1. Switch to Compositing workspace
2. Enable `Use Nodes` in compositor
3. Add a File Output node (`Shift+A` → Output → File Output)
4. Rename it to `RenderSetOutput` (or change the setting to match your node name)

---

### Issue: Nothing renders / blank output

**Cause:** No collections are visible or connected to the compositor

**Solution:**
1. Ensure collections in the render set contain visible objects
2. Verify the File Output node is properly connected to render layers
3. Check that `Sync Renderer to Viewport Visibility` is configured correctly
4. Test a manual render (F12) first to ensure compositor setup works

---

### Issue: File names don't change

**Cause:** File Output slot names don't start with the configured prefix

**Solution:**
1. Check the `Name Prefix` setting (default: `XXX`)
2. In the File Output node, rename input slots to start with this prefix:
   - Good: `XXX_Beauty`, `XXX_Depth`
   - Bad: `Beauty`, `Depth`
3. Only slots starting with the prefix will be renamed

---

### Issue: Outputs save to wrong directory

**Cause:** Output path is relative or invalid

**Solution:**
1. Use `//` for project-relative paths: `//renders/character/`
2. Or use absolute paths: `C:/Projects/MyScene/renders/`
3. Ensure directories exist or the addon will attempt to create them

---

### Issue: Solo mode doesn't restore properly

**Cause:** Visibility cache was corrupted or cleared

**Solution:**
1. Manually toggle collection visibility in the Outliner
2. Turn off solo mode by clicking `Un-Solo Set`
3. If stuck, restart Blender (visibility states are stored per session)

---

## 💡 Tips & Best Practices

### Naming Conventions

**Render Sets:**
- Use descriptive names: `Character_Front`, `Prop_Chair_Red`
- Names become part of file names, so keep them filesystem-safe
- Avoid special characters: `/`, `\`, `:`, `*`, `?`, `<`, `>`, `|`

**File Output Slots:**
- Use consistent prefixes: `XXX_Beauty`, `XXX_Depth`, `XXX_Normal`
- Everything after the prefix is preserved: `XXX_AO` → `Character_AO`

### Compositor Setup

**Best Practice:**
1. Create one **File Output** node for the addon
2. Connect all render passes you need
3. Name slots with the prefix pattern
4. Leave the base path as `//` (it will be overridden per set)

**Example Node Setup:**
```
[Render Layers]
  ├─ Image → [File Output: XXX_Beauty]
  ├─ Depth → [File Output: XXX_Depth]
  ├─ Normal → [File Output: XXX_Normal]
  └─ Mist → [File Output: XXX_Mist]
```

### Organizing Collections

**Strategy 1: By Asset**
- Render Sets represent different assets
- Collections: `Character_A`, `Character_B`, `Prop_Chair`
- Each set includes one main collection + environment

**Strategy 2: By Variation**
- Render Sets represent variations of the same asset
- Collections: `Lights_Setup1`, `Lights_Setup2`, `Material_Red`, `Material_Blue`
- Mix and match collections per set

**Strategy 3: By Camera Angle**
- Render Sets represent camera positions
- Collections remain the same, camera changes per set
- Note: Addon doesn't change active camera (do this manually or with drivers)

### Performance

**For Large Scenes:**
- Render sets sequentially (one at a time)
- Each render is a full F12 render with compositor
- Consider rendering during off-hours for batch jobs

**For Many Sets:**
- Use `Render Selected Sets` to skip unwanted variations
- Toggle `Enabled for Render` to control which sets render in batch

### File Management

**Output Paths:**
- Use project-relative paths: `//renders/characters/`
- Creates subdirectories per render set automatically
- Keeps all outputs organized

**Versioning:**
- Include version in set names: `Character_v01`, `Character_v02`
- Or use different output paths per version

---

## 🛣️ Future Enhancements

Potential features for future versions:

- [ ] Support for multiple File Output nodes
- [ ] Camera switching per render set
- [ ] Render settings override per set (samples, resolution)
- [ ] Animation/frame range rendering
- [ ] Export render set configurations to JSON
- [ ] Import/export presets
- [ ] Render queue with priority system

---

## 📜 Version History

### Version 1.0.0 (Current)
- Initial release
- Render set management (add, remove, tabs)
- Collection assignment per set
- Visibility controls (show/hide, solo)
- Three render modes (current, selected, all)
- Automatic File Output node configuration
- Prefix replacement system
- Viewport/render visibility sync
- Logging system
- Settings panel

---

## 🙏 Credits

**Concept & Development:** Claude AI + Stephan Viranyi
**Inspired by:** Production render pipeline needs across VFX and game development

---

## 📄 License

This addon is provided under the GPL v2 license for educational and commercial use.

---

## 📮 Contact & Support

**Author:** Stephan Viranyi
**GitHub:** [github.com/Stephk0/Toolings](https://github.com/Stephk0/Toolings)

For issues, suggestions, or contributions:
1. Ensure you're using Blender 4.0 or later
2. Verify the File Output node is properly configured
3. Check the log for error messages
4. Submit detailed bug reports with steps to reproduce

---

**Happy Rendering! 🎨✨**

*Part of the ClaudeVibe Toolings collection - Professional tools for Blender artists*
