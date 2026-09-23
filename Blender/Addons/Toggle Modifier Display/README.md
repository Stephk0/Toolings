# Modifier Display Toggle (Edit Mode)

A Blender addon that provides quick keyboard shortcuts to toggle modifier visibility in Edit Mode, helping you work more efficiently with complex modifier stacks.

## Overview

Instead of manually enabling/disabling modifiers in the modifier panel, you can quickly sync or disable modifier display with simple keyboard shortcuts.

## Features

- **Edit Mode Display Toggle (D key)**: Smart toggle that syncs edit mode display with viewport visibility
- **On Cage Display Toggle (Shift+D)**: Toggle the "on cage" display for modifiers that support it
- **Parity System**: First press syncs edit mode with viewport, second press disables all
- **Edit Mode Only**: Prevents accidental toggling in Object Mode
- **Multi-Object Support**: Works with Mesh, Curve, Surface, Font, and Lattice objects

## Installation

1. Grab `distribution/ToggleModifierDisplay_v1.3.0.zip`
2. Open Blender and drag the zip straight into the Blender window
   (or go to `Edit > Preferences > Add-ons > Install from Disk...` and pick the zip)
3. Enable the addon by checking the checkbox next to "3D View: Modifier Display Toggle (Edit Mode)"

## Usage

### Modifier Display Toggle (D Key)

**First Press:**
- Syncs edit mode display to match viewport visibility
- All modifiers visible in viewport will become visible in edit mode
- All modifiers hidden in viewport will be hidden in edit mode

**Second Press:**
- Disables all modifier display in edit mode
- Viewport settings remain unchanged
- Useful for working on base geometry without modifier interference

### On Cage Toggle (Shift+D)

**First Press:**
- Syncs "on cage" display to match viewport visibility
- Applies to modifiers that support cage display (Subdivision Surface, Mirror, etc.)

**Second Press:**
- Disables all "on cage" display
- Useful when you want to see the base geometry while editing

## Workflow Example

1. Enter Edit Mode on an object with modifiers
2. Press **D** to sync edit mode display with viewport (all visible modifiers now show in edit mode)
3. Work on your geometry with modifiers visible
4. Press **D** again to disable all modifiers for clean base geometry editing
5. Use **Shift+D** to toggle cage display for supported modifiers

## Supported Object Types

- Mesh
- Curve
- Surface
- Font (Text)
- Lattice

## Keyboard Shortcuts

- **D** (in Edit Mode) - Toggle modifier edit mode display
- **Shift+D** (in Edit Mode) - Toggle on cage display

## Troubleshooting

**Q: The D key doesn't work**
- Ensure you're in Edit Mode (not Object Mode)
- Check if another addon is using the same keybinding
- Verify the addon is enabled in preferences

**Q: Some modifiers don't toggle**
- Not all modifiers support "on cage" display (use Shift+D)
- Ensure modifiers are actually present on the object

**Q: Nothing happens when I press D**
- Check the Info panel (Window > Toggle System Console) for operator messages
- Verify your object type is supported

## Support

For issues, suggestions, or contributions, please refer to the project repository or contact the addon authors.

## License

This program is free software; you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation; either version 2 of the License, or (at your option) any later version.

---

**Note**: This addon is part of the Stephko Toolings collection (`Blender/Addons/`) and is in active development.

---

[Developer notes](source/DEVELOPMENT.md)
