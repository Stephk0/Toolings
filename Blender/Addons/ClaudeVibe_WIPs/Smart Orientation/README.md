# Smart Set Orientation

**Version:** 1.5.0  
**Authors:** Stephko, Claude AI  
**License:** GPL v2  
**Blender Version:** 3.0+

## Overview

Smart Set Orientation is a Blender addon that intelligently manages transform orientations based on your current context and selection. It eliminates the need to manually switch between orientation modes by automatically detecting what you're working on and setting the most appropriate orientation.

## Features

- **Context-Aware Orientation Switching**: Automatically determines the best orientation based on your current mode and selection
- **Custom Orientation Creation**: Creates custom orientations from your selection in Edit Mode
- **Selection Change Detection**: Intelligently tracks selection changes using hash-based comparison
- **Smart Toggling**: Toggle between relevant orientations with a single hotkey
- **Clean Integration**: Works seamlessly with Blender's native transform system

## Installation

1. Download `smart_set_orientation_addon.py`
2. Open Blender
3. Go to `Edit > Preferences > Add-ons`
4. Click `Install...` and select the downloaded file
5. Enable the addon by checking the box next to "Smart Set Orientation"

## Usage

### Keyboard Shortcut

**`Ctrl + D`** - Smart Set Orientation

Press this hotkey in the 3D Viewport to intelligently switch transform orientations.

### Behavior by Context

#### Edit Mode - With Selection

**First Press:**
- Creates a custom transform orientation based on your current selection
- Perfect for aligning transforms to selected edges, faces, or vertex groups

**Subsequent Presses (same selection):**
- Toggles between the custom orientation and Local orientation
- Allows quick switching between custom alignment and object-local space

**When Selection Changes:**
- Automatically creates a new custom orientation based on the new selection
- Previous custom orientation is preserved and can be accessed

#### Edit Mode - No Selection

- **First Press:** Sets to Local orientation
- **Second Press:** Toggles to Global orientation
- **Third Press:** Returns to Local orientation
- Cycles between Local and Global orientations

#### Object Mode - With Selection

- **First Press:** Sets to Local orientation
- **Second Press:** Toggles to Global orientation
- Useful for quickly switching between object-local and world space

#### Object Mode - No Selection

- Automatically sets to Global orientation
- Ensures consistent world-space orientation when no objects are selected

#### Other Modes (Sculpt, Pose, etc.)

- Defaults to Global orientation
- Provides a consistent baseline for other editing modes

## How It Works

### Selection Tracking

The addon uses MD5 hashing to track your selection state:
- Generates a unique hash based on selected vertices, edges, and faces
- Detects when you've changed your selection
- Automatically creates new orientations when selection changes
- Toggles between orientations when working with the same selection

### Custom Orientation Management

- Custom orientations are created using Blender's native `transform.create_orientation` operator
- The addon tracks the most recently created custom orientation
- Previous custom orientations remain available in your scene
- Orientations can be overwritten or preserved based on your workflow

### Context Override System

- Uses Blender's context override to ensure operators work correctly
- Finds appropriate 3D Viewport regions automatically
- Handles edge cases where multiple viewports exist

## Preferences

Access addon preferences in `Edit > Preferences > Add-ons > Smart Set Orientation`

The preferences panel shows:
- Quick usage guide
- Keyboard shortcut reference
- Author information

## Use Cases

### Modeling Workflows

1. **Align to Edge Flow:**
   - Select an edge or face aligned with your desired direction
   - Press `Ctrl + D` to create orientation
   - Transform follows your mesh topology

2. **Quick Local/Global Switching:**
   - Working in Edit Mode without selection
   - Press `Ctrl + D` to toggle between Local and Global
   - No need to open orientation menu

3. **Object Space Control:**
   - Select object in Object Mode
   - Press `Ctrl + D` to toggle between Local and Global
   - Quick access to both spaces

### Advanced Techniques

- **Planar Modeling:** Select a face, create custom orientation, extrude along the face normal
- **Edge Loop Alignment:** Select aligned edges, create orientation, scale or move along the loop
- **Multi-Object Consistency:** Toggle to Global when working across multiple objects

## Technical Details

### Selection Hash Algorithm

```python
# Combines vertex, edge, and face indices into unique hash
selected_verts = tuple(sorted(v.index for v in bm.verts if v.select))
selected_edges = tuple(sorted(e.index for e in bm.edges if e.select))
selected_faces = tuple(sorted(f.index for f in bm.faces if f.select))
selection_str = f"v{selected_verts}_e{selected_edges}_f{selected_faces}"
hash = hashlib.md5(selection_str.encode()).hexdigest()
```

### Context Validation

- Checks for valid 3D Viewport context before execution
- Verifies appropriate region types (WINDOW)
- Handles context override for operator execution
- Falls back gracefully on errors

## Troubleshooting

### "This operator must be called from a 3D Viewport"
- Ensure your cursor is in the 3D Viewport when pressing `Ctrl + D`
- The operator only works in 3D View context

### "Failed to create orientation"
- Make sure you have valid geometry selected in Edit Mode
- Check that your mesh has proper selection (vertices, edges, or faces)
- Try re-selecting elements if the issue persists

### Custom orientation not switching
- The addon tracks the most recent custom orientation
- If multiple custom orientations exist, manually select from the orientation dropdown
- Press `Ctrl + D` again to toggle after manual selection

### Keymap conflicts
- If `Ctrl + D` doesn't work, check for conflicts in `Edit > Preferences > Keymap`
- Search for "Smart Set Orientation" and verify the binding
- Remap to alternative key combination if needed

## Version History

### Version 1.5.0
- Current stable release
- Selection hash tracking system
- Custom orientation toggle functionality
- Context-aware mode handling
- Improved error handling and reporting

## Contributing

This addon is part of the ClaudeVibe toolset. For issues, suggestions, or contributions:
- Report bugs with detailed steps to reproduce
- Include Blender version and OS information
- Describe expected vs actual behavior

## Credits

**Developed by:** Stephko  
**AI Assistant:** Claude (Anthropic)  
**License:** GNU General Public License v2

## License

This program is free software; you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation; either version 2 of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.

---

**Enhance your Blender workflow with intelligent orientation management!**
