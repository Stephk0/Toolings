# Edit Mode Overlay - Blender Addon

A Blender addon that displays a customizable overlay banner when working in edit mode, helping you stay aware of your current editing state.

![Version](https://img.shields.io/badge/version-1.1.0-blue)
![Blender](https://img.shields.io/badge/blender-2.80+-orange)

## Features

- **Visual Indicator**: Displays a prominent overlay when entering any edit mode
- **Fully Customizable**: Adjust text, colors, size, position, and transparency
- **Multiple Edit Modes Support**: Works with:
  - Edit Mesh
  - Edit Curve
  - Edit Armature
  - Edit Metaball
  - Edit Lattice
  - Edit Surface
  - Edit Text
  - Edit Grease Pencil
- **Easy Toggle**: Quick enable/disable from the 3D viewport sidebar
- **Non-Intrusive**: Transparent overlay that doesn't obstruct your workflow

## Installation

1. Download the `edit_mode_overlay_addon_Opus.py` file
2. Open Blender
3. Go to `Edit` > `Preferences` > `Add-ons`
4. Click `Install...` button
5. Navigate to the downloaded `.py` file and select it
6. Enable the addon by checking the checkbox next to "3D View: Edit Mode Overlay"

## Usage

### Quick Access Panel

1. In the 3D Viewport, press `N` to open the sidebar
2. Navigate to the `View` tab
3. Find the "Edit Mode Overlay" panel
4. Use the **Enable/Disable Overlay** button to toggle the overlay
5. Adjust quick settings directly in the panel:
   - Overlay Text
   - Width
   - Height

### Full Preferences

Click the **More Settings** button in the panel or go to `Edit` > `Preferences` > `Add-ons` > `Edit Mode Overlay` to access all options:

#### Text Settings
- **Overlay Text**: Custom message to display (default: ">>> IN EDIT MODE <<<")
- **Text Color**: RGB color for the text
- **Text Size Factor**: Scale text size relative to rectangle height (10% - 90%)

#### Rectangle Settings
- **Width**: Overlay width in pixels (100 - 2000px)
- **Height**: Overlay height in pixels (30 - 300px)
- **Overlay Color**: RGB color for the background rectangle
- **Overlay Opacity**: Transparency level (0.0 - 1.0)

#### Position Settings
- **Distance from Top**: Vertical offset from viewport top (0 - 500px)
- **Horizontal Alignment**: Left, Center, or Right alignment
- **Horizontal Offset**: Additional horizontal adjustment (-500 to +500px)

## Default Settings

The addon comes with sensible defaults:
- **Text**: ">>> IN EDIT MODE <<<"
- **Size**: 512px × 64px
- **Position**: Top center, 64px from top
- **Colors**: Orange background (#FF8000), white text
- **Opacity**: 80%

## Use Cases

- **Prevent Accidental Edits**: Clear visual reminder when in edit mode
- **Teaching/Streaming**: Help viewers know when you're in edit mode
- **Multi-Monitor Setups**: Easy status check without looking at mode selector
- **Custom Workflows**: Adapt the overlay to match your UI theme

## Requirements

- Blender 2.80 or higher
- Supports both OpenGL and newer rendering backends

## Tips

- Use **high contrast colors** for better visibility
- Adjust **opacity** if the overlay is too distracting
- Position the overlay in a **less critical area** of your viewport
- Use **shorter text** for smaller rectangles
- Changes update in **real-time** as you adjust settings

## Troubleshooting

**Overlay not showing:**
- Make sure you're in one of the supported edit modes
- Check that the overlay is enabled (button should say "Disable Overlay")
- Verify you're in a 3D Viewport

**Text is too small/large:**
- Adjust the "Text Size Factor" in preferences
- Increase/decrease the rectangle height

**Overlay in wrong position:**
- Check "Horizontal Alignment" setting
- Adjust "Distance from Top" value
- Use "Horizontal Offset" for fine-tuning

## Known Limitations

- Only appears in 3D Viewports
- Draws on top of all viewport content
- Settings are global (not per-scene or per-workspace)

## Version History

### v1.1.0
- Added customizable text size factor
- Improved text positioning and centering
- Enhanced preferences UI with grouped settings
- Added quick settings panel in viewport sidebar

### v1.0.0
- Initial release
- Basic overlay functionality
- Customizable colors, size, and position

## Contributing

Feel free to submit issues, feature requests, or pull requests to improve this addon.

## License

This addon is provided as-is for free use and modification.

## Credits

Created with assistance from Claude (Anthropic)

---

**Enjoy your enhanced Blender workflow! 🎨**
