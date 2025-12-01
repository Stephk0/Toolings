# Installation Guide - Stephko Toolings

**Version:** 1.0  
**Last Updated:** 2024

> Step-by-step installation instructions for Blender, 3ds Max, and Unity tools

---

## 📋 Table of Contents

- [Prerequisites](#prerequisites)
- [Blender Installation](#blender-installation)
  - [Addon Installation](#blender-addon-installation)
  - [Geometry Nodes Installation](#geometry-nodes-installation)
- [3ds Max Installation](#3ds-max-installation)
  - [Scripts Installation](#scripts-installation)
  - [Modifiers Installation](#modifiers-installation)
- [Unity Installation](#unity-installation)
- [Troubleshooting](#troubleshooting)
- [Verification](#verification)

---

## ✅ Prerequisites

### System Requirements

| Platform | Requirement | Notes |
|----------|-------------|-------|
| **Blender** | Version 4.0+ | 4.5+ recommended |
| **3ds Max** | Version 2020+ | 2020-2023 tested |
| **Unity** | Version 2021+ | For export workflow |
| **OS** | Windows 10+ | Mac/Linux for Blender |

### Before You Start

1. **Backup** your existing addons/scripts
2. **Close** target applications
3. **Download** or clone this repository
4. **Extract** to accessible location

```bash
# Clone repository
git clone https://github.com/Stephk0/Toolings.git

# Or download ZIP and extract
```

---

## 🔷 Blender Installation

### Blender Addon Installation

#### Method 1: Install from Disk (Recommended)

**Step-by-Step:**

1. **Open Blender**
2. Go to `Edit` > `Preferences` (or `Ctrl + Alt + U`)
3. Click on `Add-ons` tab
4. Click `Install...` button (top right)
5. Navigate to addon location:
   ```
   Toolings/Blender/Addons/ClaudeVibe_WIPs/[addon_name]/
   ```
6. Select the `.py` file
7. Click `Install Add-on`
8. **Enable** the addon by checking the checkbox
9. **Verify** addon appears in list

**Available Addons:**

```
Smart Collapse → smart_collapse.py
Smart Crease → smart_crease.py
Mass Collection Exporter → mass_exporter_FIXED_v12.py
Smart Set Orientation → smart_set_orientation_addon.py
Center Loops → center_loops_addon.py
Toggle Modifier Display → modifier_display_toggle_edit_only.py
Edit Mode Overlay → edit_mode_overlay_addon_Opus.py
Edge Constraint Mode → [package folder]
```

#### Method 2: Manual Installation

**For Advanced Users:**

1. **Locate Blender addons folder:**

   **Windows:**
   ```
   %APPDATA%\Blender Foundation\Blender\[version]\scripts\addons\
   ```
   
   **Mac:**
   ```
   ~/Library/Application Support/Blender/[version]/scripts/addons/
   ```
   
   **Linux:**
   ```
   ~/.config/blender/[version]/scripts/addons/
   ```

2. **Copy addon files:**
   - For single-file addons: Copy `.py` file directly
   - For package addons: Copy entire folder

3. **Restart Blender**

4. **Enable addons:**
   - `Edit` > `Preferences` > `Add-ons`
   - Search for addon name
   - Enable checkbox

#### Installation Verification

**Check addon is working:**

1. **Smart Collapse:**
   - Enter Edit Mode
   - Select 2 vertices
   - Press `Ctrl + Alt + X`
   - Should see "Collapsed" or "Merged" message

2. **Mass Collection Exporter:**
   - Press `N` to open sidebar
   - Look for "Mass Exporter" tab
   - Panel should be visible

3. **Smart Crease:**
   - Enter Edit Mode
   - Select edges
   - Press `Shift + E`
   - Modal operator should activate

---

### Geometry Nodes Installation

**Step-by-Step:**

1. **Open Blender**
2. Go to `Edit` > `Preferences`
3. Click on `File Paths` tab
4. Scroll to `Asset Libraries` section
5. Click `+` (Add) button
6. **Set Name:** "Stephko Geonodes" (or your choice)
7. **Browse to folder:**
   ```
   Toolings/Blender/Geonodes/
   ```
8. Click `OK`

**Usage:**

1. Open `Asset Browser` (Shift + F2 or View menu)
2. Select "Stephko Geonodes" from dropdown
3. **Drag and drop** nodes onto your geometry
4. Nodes are automatically linked

**Available Geonodes:**

```
✓ GN_AttributeFunctions_4.5
✓ GN_CollectionInstancer
✓ GN_Delete
✓ GN_ExtrudeSelection
✓ GN_FillBorder
✓ GN_GrowSelection
✓ GN_InsetFace
✓ GN_Instancer
✓ GN_MeshFromImage
✓ GN_SimpleTransform
✓ GN_Solidify2
✓ GN_SplitByAttribute
✓ GN_VariousTest
```

**Note:** Some nodes may require third-party geometry node dependencies.

---

## 🔶 3ds Max Installation

### Scripts Installation

**Important:** Development discontinued in 2023. Tools provided as-is.

#### Step-by-Step:

1. **Locate 3ds Max scripts folder:**
   ```
   C:\Program Files\Autodesk\[Max Version]\scripts\
   ```
   
   **Examples:**
   ```
   C:\Program Files\Autodesk\3ds Max 2023\scripts\
   C:\Program Files\Autodesk\3ds Max 2022\scripts\
   ```

2. **Copy folders from:**
   ```
   Toolings/3DSMAX/Scripts/
   ```

3. **Copy these folders:**
   - `ST3E` → Complete folder
   - `Startup` → Complete folder

4. **Final structure:**
   ```
   C:\Program Files\Autodesk\[Max Version]\scripts\
   ├── ST3E\
   │   ├── CoordinateSystem\
   │   ├── Editing\
   │   ├── Inspection\
   │   ├── etc...
   └── Startup\
       ├── ST3E_Startup.ms
       └── ViewportOverlay.ms
   ```

5. **Restart 3ds Max**

#### Verification:

1. **Check startup script ran:**
   - Look for startup messages in MAXScript Listener (F11)

2. **Check scripts available:**
   - Access various menus (right-click, Edit menu, etc.)
   - Look for ST3E commands

3. **Check toolsets:**
   - Look for MatIDToolBox
   - Look for PolyDrawOptions

---

### Modifiers Installation

#### Step-by-Step:

1. **Locate 3ds Max plugins folder:**
   ```
   C:\Program Files\Autodesk\[Max Version]\Plugins\
   ```

2. **Copy from:**
   ```
   Toolings/3DSMAX/Modifiers/Custom Modifiers/
   ```

3. **Copy all .ms files:**
   - Modifier_EPoly_*.ms
   - Modifier_SimpleMesh_*.ms
   - Modifier_SimpleMod_*.ms

4. **Final location:**
   ```
   C:\Program Files\Autodesk\[Max Version]\Plugins\
   ├── Modifier_EPoly_autoSmooth.ms
   ├── Modifier_EPoly_bevel.ms
   ├── Modifier_EPoly_connect.ms
   ├── ... (all 24 modifier files)
   ```

5. **Restart 3ds Max**

#### Verification:

1. **Select an object**
2. **Open Modifier Panel**
3. **Click Modifier List dropdown**
4. **Look for custom modifiers:**
   - EPoly Auto Smooth
   - EPoly Bevel
   - SimpleMesh Material ID by SG
   - SimpleMod Boxify
   - etc.

---

## 🔷 Unity Installation

**Status:** Planned - Not yet available

**Future Installation:**
1. Import Unity package
2. Configure import settings
3. Set up material pipeline

**Current Workflow:**
- Use Blender Mass Exporter
- Export as FBX with Unity settings
- Import into Unity normally

---

## 🛠️ Troubleshooting

### Blender Issues

#### "Addon doesn't appear after installation"

**Causes & Solutions:**

1. **Wrong Blender version:**
   ```
   Solution: Check minimum version requirement
   Most addons: Blender 4.0+
   Some work on: Blender 3.0+
   ```

2. **Python error on enable:**
   ```
   Solution: Check System Console
   Windows: Window > Toggle System Console
   Look for error messages
   Report errors with details
   ```

3. **Addon installed but not showing:**
   ```
   Solution: Search in addon preferences
   Type addon name in search box
   May be disabled or filtered
   ```

#### "Hotkey doesn't work"

**Causes & Solutions:**

1. **Keymap conflict:**
   ```
   Solution: Check keymap preferences
   Edit > Preferences > Keymap
   Search for addon name
   Look for conflicts (yellow warning)
   Remap if necessary
   ```

2. **Wrong mode/context:**
   ```
   Solution: Check you're in correct mode
   Smart Collapse: Edit Mode
   Smart Orientation: Any Mode
   Toggle Modifier: Edit Mode only
   ```

#### "Geometry nodes not showing"

**Causes & Solutions:**

1. **Asset library not set:**
   ```
   Solution: Check File Paths
   Verify library path is correct
   Check import method is "Link"
   ```

2. **Wrong asset browser:**
   ```
   Solution: Check dropdown
   Select "Stephko Geonodes" library
   Not "Current File" or other library
   ```

---

### 3ds Max Issues

#### "Scripts not appearing in menus"

**Causes & Solutions:**

1. **Incorrect installation:**
   ```
   Solution: Verify folder structure
   Should be: scripts/ST3E/[subfolders]
   Not: scripts/Scripts/ST3E/[subfolders]
   ```

2. **Startup script failed:**
   ```
   Solution: Check MAXScript Listener
   Press F11
   Look for error messages
   ```

3. **Permission issues:**
   ```
   Solution: Run 3ds Max as Administrator
   Right-click 3ds Max icon
   Select "Run as administrator"
   ```

#### "Custom modifiers not showing"

**Causes & Solutions:**

1. **Files in wrong location:**
   ```
   Solution: Verify Plugins folder
   Files should be directly in Plugins/
   Not in Plugins/Custom Modifiers/
   ```

2. **Script security:**
   ```
   Solution: Check script security settings
   Customize > Preferences > MAXScript
   Set to appropriate security level
   ```

#### "MVP-Graveyard scripts not working"

**Expected Behavior:**
```
These are experimental/abandoned features
Not supported or maintained
May not work in current Max version
Use at your own risk
```

---

### General Issues

#### "Can't find installation folder"

**Windows Show Hidden Folders:**
```
1. Open File Explorer
2. Click View tab
3. Check "Hidden items"
4. Navigate to folders listed above
```

**Mac Show Hidden Folders:**
```
1. In Finder press: Cmd + Shift + .
2. Hidden folders now visible
3. Navigate using ~/ paths
```

#### "Permission denied when copying"

**Solution:**
```
1. Close target application
2. Run File Explorer as Administrator (Windows)
3. Try copying again
4. If still fails, check folder permissions
```

#### "After installation, nothing works"

**Systematic Check:**
```
1. Verify correct folder location
2. Check file/folder names are exact
3. Restart application completely
4. Check addon/script is enabled
5. Look for error messages in console
6. Try one addon at a time
```

---

## ✓ Verification Checklist

### Blender Addons

Use this checklist after installation:

```
☐ Smart Collapse
   ☐ Installed and enabled
   ☐ Ctrl + Alt + X works in Edit Mode
   ☐ Menu item appears in Delete menu

☐ Smart Crease
   ☐ Installed and enabled
   ☐ Shift + E activates modal
   ☐ HUD appears on use

☐ Mass Collection Exporter
   ☐ Installed and enabled
   ☐ Panel appears in N-Panel
   ☐ Can add collections

☐ Smart Set Orientation
   ☐ Installed and enabled
   ☐ Ctrl + D works
   ☐ Creates orientations

☐ Center Loops
   ☐ Installed and enabled
   ☐ Ctrl + Shift + C works
   ☐ Menu items appear

☐ Toggle Modifier Display
   ☐ Installed and enabled
   ☐ D key works in Edit Mode
   ☐ Shift + D works

☐ Edit Mode Overlay
   ☐ Installed and enabled
   ☐ Panel appears in View tab
   ☐ Overlay shows in Edit Mode

☐ Edge Constraint Mode (Optional/Experimental)
   ☐ Installed and enabled
   ☐ Panel appears in Tool tab
   ☐ Enable button works
```

### Blender Geometry Nodes

```
☐ Asset Library configured
☐ Geonodes folder path correct
☐ Import method set to "Link"
☐ Nodes visible in Asset Browser
☐ Can drag-drop nodes
☐ Nodes function correctly
```

### 3ds Max ST3E

```
☐ Scripts folder contains ST3E
☐ Scripts folder contains Startup
☐ Plugins folder contains modifiers
☐ 3ds Max restarted after install
☐ Startup messages visible (F11)
☐ Context menu items appear
☐ Custom modifiers in list
☐ MatIDToolBox accessible
```

---

## 📞 Support

### Still Having Issues?

**Get Help:**

1. **Check documentation:**
   - Master Documentation
   - Individual addon READMEs
   - Quick Reference Guide

2. **Search existing issues:**
   - GitHub Issues
   - Community discussions

3. **Report new issue:**
   - Include software version
   - Include OS version
   - Include error messages
   - Include steps to reproduce
   - Include screenshots if relevant

**Contact:**
- **Email:** stephko@viranyi.de
- **GitHub:** [github.com/Stephk0/Toolings](https://github.com/Stephk0/Toolings)

---

## 🎓 Next Steps

### After Installation

1. **Read Quick Reference:**
   - Learn hotkeys
   - Understand workflows
   - See common operations

2. **Try each tool:**
   - Test in safe environment
   - Follow addon READMEs
   - Experiment with features

3. **Integrate into workflow:**
   - Start with 1-2 tools
   - Build muscle memory
   - Gradually add more tools

4. **Customize settings:**
   - Adjust preferences
   - Remap hotkeys if needed
   - Configure per project

### Learning Resources

- **Master Documentation:** Complete tool reference
- **Quick Reference:** Fast lookup for hotkeys
- **Individual READMEs:** Detailed per-tool guides
- **3ds Max Docs:** [Google Docs Link](https://docs.google.com/document/d/1fIKEurSNeaazzYsPnCTYT7bVO4R4btWzTzvLRpjNutY/edit?usp=sharing)

---

## 🔄 Updating

### Blender Addons

**Update Process:**

1. **Download new version**
2. **Disable old version** in preferences
3. **Install new version** using same method
4. **Enable new version**
5. **Restart Blender** (recommended)

**Note:** Settings usually preserved

### 3ds Max Tools

**Update Process:**

1. **Backup existing files**
2. **Close 3ds Max**
3. **Replace files** in scripts/plugins folders
4. **Restart 3ds Max**

**Note:** No active development, unlikely to have updates

---

## 📝 Installation Notes

### Important Points

1. **Blender:**
   - Each addon installs independently
   - Can enable/disable individually
   - Geometry nodes are separate system
   - No dependencies between addons

2. **3ds Max:**
   - Scripts and modifiers separate
   - Some scripts depend on Startup script
   - No longer actively developed
   - May have compatibility issues with new Max versions

3. **Best Practices:**
   - Install one at a time
   - Test each installation
   - Keep backup of originals
   - Document custom modifications

---

**Installation complete? Proceed to:** [Quick Reference Guide](QUICK_REFERENCE.md)

**Made with ❤️ by Stephan Viranyi**

