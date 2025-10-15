# Smart Crease Add-on for Blender

A context-sensitive crease tool that intelligently adapts to Vertex/Edge/Face selection modes, providing modal mouse control, 0/1 toggle functionality, and real-time HUD display.

## Features

### Context-Sensitive Operation
- **Vertex Mode**: Edits vertex crease on selected vertices
- **Edge Mode**: Edits edge crease on selected edges  
- **Face Mode**: Edits edge crease on boundary edges of selected faces

### Modal Controls
- **Mouse Drag**: Smoothly adjust crease values from 0.0 to 1.0
- **Shift**: Fine-tune mode (10x reduced sensitivity)
- **Ctrl**: Snap to 0.1 increments
- **Alt**: Reset crease to 0.0
- **V Key**: Toggle between 0 and 1 (alternates intelligently)

### Numeric Input
- Type numbers directly (e.g., `0.5`, `.75`, `1`) to set exact values
- **Backspace**: Clear numeric input character by character
- Numeric input overrides mouse movement until cleared

### Visual Feedback
- **Live HUD**: Displays current crease value and active domain at drag position
- Format: `Smart Crease — [Domain]: [Value]`
- Automatically shows domain context (Vertex, Edge, or Face→Boundary)

### Confirmation
- **Left Mouse / Enter / Space**: Confirm and apply changes
- **Right Mouse / Esc**: Cancel and restore original values

## Installation

1. Download `smart_crease.py`
2. Open Blender (version 4.0 or later)
3. Go to: Edit > Preferences > Add-ons
4. Click "Install..." and select `smart_crease.py`
5. Enable the add-on by checking the checkbox next to "Mesh: Smart Crease"

## Usage

### Basic Workflow

1. **Enter Edit Mode** (Tab) on a mesh object
2. **Select elements** (vertices, edges, or faces)
3. **Activate Smart Crease**: Press **Shift+E**
4. **Adjust crease**:
   - Drag mouse left/right or up/down to change value
   - OR type a numeric value (e.g., `0.5`)
   - OR press **V** to toggle between 0 and 1
5. **Confirm**: Left-click or press Enter
6. **Cancel**: Right-click or press Esc

### Selection Mode Behavior

#### Vertex Mode (1 key)
- Operates on **vertex crease** attribute
- Affects selected vertices only
- Useful for controlling subdivision at specific vertices

#### Edge Mode (2 key)
- Operates on **edge crease** attribute
- Affects selected edges only
- Standard crease behavior for Subdivision Surface

#### Face Mode (3 key)
- Operates on **boundary edges** of selected faces
- Only affects edges with exactly one adjacent face selected
- Perfect for creating hard edges around face selections
- Warning shown if no boundary edges exist (entire mesh selected)

### Modifier Keys

| Key | Effect |
|-----|--------|
| **Shift** | Fine-tune mode (10x slower movement) |
| **Ctrl** | Snap to 0.1 increments |
| **Alt** | Reset to 0.0 |
| **V** | Toggle 0/1 (alternates intelligently) |

### Toggle Behavior (V Key)

The V key intelligently toggles crease values:
- If current value ≈ 0.0 → sets to 1.0
- If current value ≈ 1.0 → sets to 0.0  
- If in between → first press goes to 1.0, next press to 0.0, then alternates

### Numeric Input Examples

- Type `1` → set to 1.0
- Type `0.5` → set to 0.5
- Type `.75` → set to 0.75
- Press Backspace to clear last digit
- Press Alt to reset and clear numeric input

## Preferences

Access preferences via: Edit > Preferences > Add-ons > Smart Crease

### Available Settings

- **Mouse Sensitivity** (0.001 - 0.02): Adjust drag responsiveness
- **Toggle Key** (default: V): Customize the 0/1 toggle hotkey
- **Snap Increment** (0.01 - 0.5): Snap step size when Ctrl is held
- **HUD Font Size** (10 - 30): Adjust on-screen display text size

## Subdivision Surface Integration

Smart Crease works seamlessly with the Subdivision Surface modifier:

1. Add a **Subdivision Surface** modifier to your mesh
2. Use Smart Crease to mark sharp edges/vertices
3. Crease value of **1.0** = completely sharp (no subdivision)
4. Crease value of **0.0** = fully smooth (standard subdivision)
5. Values between 0-1 provide partial sharpness

## Tips & Tricks

### Creating Sharp Borders
1. Select faces in Face Mode (3)
2. Press Shift+E and set crease to 1.0 (or press V)
3. Only the boundary edges become sharp

### Precise Control
1. Start dragging to see current value
2. Hold **Shift** for fine adjustments
3. OR type exact value (e.g., `0.33`)

### Quick Reset
- Press **Alt** while dragging to instantly reset to 0.0
- Right-click to cancel and restore all original values

### Batch Operations
- Select multiple vertices/edges/faces
- All selected elements receive the same crease value
- Median of current values shown as starting point

## Technical Details

### Requirements
- Blender 4.0 or later (for vertex crease support)
- Works in Edit Mode only
- Requires active mesh object

### Data Attributes
- **Vertex Crease**: Custom float layer (`vertex_crease`)
- **Edge Crease**: Built-in edge crease attribute (0-1 range)
- Both compatible with Subdivision Surface modifier

### Performance
- Uses BMesh for efficient per-element access
- Batch operations on all selected elements
- Smooth viewport updates during modal operation
- Single undo step per operation

## Troubleshooting

### "No selected elements" warning
- Ensure elements are selected in Edit Mode
- Check that selection matches current mode (Vertex/Edge/Face)

### "No boundary edges found" in Face Mode
- Occurs when entire mesh is selected (no boundaries)
- Deselect some faces to create boundary edges
- OR switch to Edge Mode to crease specific edges

### Keymap conflict with Shift+E
- The add-on uses Shift+E (same as standard Crease)
- It overrides the default in Vertex and Face modes
- To change hotkey: modify preferences or keymap

### HUD not visible
- Check HUD font size in preferences
- HUD appears at initial click position
- Ensure 3D viewport is visible and active

## Known Limitations

- Single mesh object operation only (no multi-object edit)
- Face mode requires at least one boundary edge
- Numeric input limited to positive values (0-1 range enforced)

## Compatibility

- **Tested**: Blender 4.0+
- **Platform**: Windows, macOS, Linux
- **Dependencies**: None (uses built-in Blender modules)

## License

This add-on is provided as-is for educational and production use. Feel free to modify and distribute according to your needs.

## Version History

### Version 1.0.0
- Initial release
- Full Vertex/Edge/Face mode support
- Modal operator with HUD
- 0/1 toggle functionality
- Numeric input support
- Precision and snap modifiers
- Preferences panel

## Support

For issues or feature requests, ensure you're using Blender 4.0 or later and have the add-on properly installed and enabled.

---

**Enjoy precise crease control with Smart Crease!** 🎨✨
