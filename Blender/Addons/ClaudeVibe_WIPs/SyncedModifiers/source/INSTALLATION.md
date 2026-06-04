# Synced Modifiers v2.4.0 - Installation Guide

## Installation Methods

### Method 1: Install from ZIP (Recommended)

1. Create a ZIP file of the `SyncedModifiers` folder
2. In Blender: Edit → Preferences → Add-ons
3. Click "Install..." button
4. Select the ZIP file
5. Enable the addon by checking the box next to "Object: Synced Modifiers"

### Method 2: Manual Installation

1. Copy the entire `SyncedModifiers` folder to:
   - **Windows**: `C:\Users\<YourUsername>\AppData\Roaming\Blender Foundation\Blender\<version>\scripts\addons\`
   - **macOS**: `/Users/<YourUsername>/Library/Application Support/Blender/<version>/scripts/addons/`
   - **Linux**: `/home/<YourUsername>/.config/blender/<version>/scripts/addons/`

2. Restart Blender
3. Go to Edit → Preferences → Add-ons
4. Search for "Synced Modifiers"
5. Enable it by checking the box

## Troubleshooting

### Addon doesn't appear in the list

1. **Check Blender Console for errors**:
   - Windows: Window → Toggle System Console
   - macOS/Linux: Run Blender from terminal to see output

2. **Look for error messages** like:
   - `Failed to register <class>: <error message>`
   - Import errors
   - Python syntax errors

3. **Check Blender version**:
   - Minimum required: Blender 2.91.0
   - Best compatibility: Blender 4.0+
   - The addon has been tested on Blender 5.0

4. **Verify file structure**:
   ```
   SyncedModifiers/
   ├── __init__.py
   ├── properties_data_modifiers.py
   ├── blender_manifest.toml
   ├── CLAUDE.md
   └── (other .md files)
   ```

5. **Try reinstalling**:
   - Remove the addon completely
   - Restart Blender
   - Install again

### Addon loads but geometry nodes don't work

This is normal for older Blender versions (pre-4.0). The geometry nodes features require the newer interface API:
- Vanilla modifiers will still work perfectly
- Geometry nodes support requires Blender 4.0+

### Still having issues?

1. Open Blender's System Console (Window → Toggle System Console)
2. Try to enable the addon
3. Copy any error messages
4. Check the error messages for clues:
   - "Failed to register" → specific class has an issue
   - "ImportError" → missing dependency or Python version issue
   - "AttributeError" → API compatibility issue

## Verification

Once installed successfully, you should see:
1. **N-Panel**: Press `N` in 3D Viewport → "Item" tab → "Synced Modifiers" panel
2. **Keyboard Shortcut**: `Alt+J` opens the Synced Modifiers popup
3. **Add Menu**: Shift+A in 3D Viewport → "Synced Modifiers" option added

## Features

### Vanilla Modifiers
- Add modifiers to multiple objects simultaneously
- Sync modifier properties using Blender's driver system
- Works with: Array, Mirror, Bevel, Solidify, Subdivision Surface, and 40+ other modifiers

### Geometry Nodes (Blender 4.0+)
- Add synced geometry nodes modifiers
- Automatic driver creation for scalar/vector inputs
- Sync buttons for Object/Collection/Material inputs
- Support for library-linked node groups

## Getting Help

If you encounter issues:
1. Check the Blender console for error messages
2. Verify your Blender version (should be 2.91.0 or newer)
3. Try the addon with vanilla modifiers first to confirm it's working
4. For geometry nodes, ensure you're using Blender 4.0+
