# Smart Crease Add-on for Blender

A context-sensitive crease tool that adapts to Vertex/Edge/Face selection modes, providing modal mouse control, quick preset keys, Alt toggle functionality, and real-time HUD display.
Integrates particullary well with Solidify Plus using crease edges from vertex crease feature for rim creases.

**Version**: 1.5.1  
**Blender**: 4.0+  
**Author**: Stephan Viranyi + Claude  
**Repository**: [Stephko Toolings](https://github.com/Stephk0/Toolings)

---

## Features

### Context-Sensitive Operation
- **Vertex Mode**: Edits vertex crease on selected vertices
- **Edge Mode**: Edits edge crease on selected edges  
- **Face Mode**: Edits edge crease on boundary edges of selected faces. If entire mesh/island is selected (no boundaries possible), affects all edges of selection

### Quick Preset Keys
- **Keys 1-9**: Set crease to 0.1 through 0.9 instantly
  - Press `1` → 0.1 crease
  - Press `5` → 0.5 crease  
  - Press `9` → 0.9 crease
- **Key 0**: Set crease to 1.0 (full crease)
- Perfect for rapid, repeatable crease values

### Alt Toggle
- **Alt Key**: Intelligently toggles between 0 and 1
  - If current value ≈ 0.0 → sets to 1.0
  - If current value ≈ 1.0 → sets to 0.0
  - If in between → first press goes to 1.0, next press to 0.0, then alternates

### Modal Mouse Controls
- **Mouse Drag**: Smoothly adjust crease values from 0.0 to 1.0
- **Shift**: Precision mode (10x reduced sensitivity for fine control)
- **Ctrl**: Snap mode (snaps to increments set in preferences)

### Decimal Input
- **Numpad**: Type decimal values directly (e.g., `0.75`)
  - Use numpad period for decimal point
- **Shift + Number Keys**: Alternative to numpad for decimal input
  - Shift+5, Period, Shift+7, Shift+5 → 0.575
- **Backspace**: Clear numeric input character by character
- Numeric input overrides mouse movement until cleared or confirmed

### Visual Feedback
- **Live HUD**: Displays current crease value and active domain at mouse position
- Format: `Smart Crease — [Domain]: [Value]`
- Automatically shows domain context:
  - `Vertex` in vertex mode
  - `Edge` in edge mode
  - `Face→Boundary` in face mode
- Font size adjustable in preferences

### Confirmation
- **Left Mouse / Enter / Space**: Confirm and apply changes
- **Right Mouse / Esc**: Cancel and restore original values

---

## Installation

1. Download `smart_crease.py`
2. Open Blender (version 4.0 or later)
3. Go to: **Edit > Preferences > Add-ons**
4. Click **"Install..."** and select `smart_crease.py`
5. Enable the add-on by checking the checkbox next to **"Mesh: Smart Crease"**

---

## Usage

### Basic Workflow

1. **Enter Edit Mode** (Tab) on a mesh object
2. **Select elements** (vertices, edges, or faces)
3. **Activate Smart Crease**: Press **Shift+E**
4. **Adjust crease** using any method:
   - **Quick presets**: Press `1`-`9` for 0.1-0.9, or `0` for 1.0
   - **Alt toggle**: Press Alt to toggle between 0 and 1
   - **Mouse drag**: Drag to smoothly adjust
   - **Decimal input**: Type exact value using numpad or Shift+keys
5. **Confirm**: Left-click or press Enter
6. **Cancel**: Right-click or press Esc

### Selection Mode Behavior

#### Vertex Mode (1 key)
- Operates on **vertex crease** attribute
- Affects selected vertices only
- Useful for controlling subdivision at specific vertices
- Works with Subdivision Surface modifier

#### Edge Mode (2 key)
- Operates on **edge crease** attribute
- Affects selected edges only
- Standard crease behavior for Subdivision Surface
- Most common use case for hard edges

#### Face Mode (3 key)
- Operates on **boundary edges** of selected faces
- Only affects edges with exactly one adjacent face selected
- Perfect for creating hard edges around face selections
- If entire mesh/island is selected (no boundaries), affects all edges
- Warning shown if no boundary edges exist

### Modifier Keys Reference

| Key | Function | Description |
|-----|----------|-------------|
| **1-9** | Quick Preset | Set crease to 0.1-0.9 instantly |
| **0** | Full Crease | Set crease to 1.0 (maximum) |
| **Alt** | Toggle | Intelligently toggle between 0 and 1 |
| **Shift** | Precision | Fine control (10x slower mouse movement) |
| **Ctrl** | Snap | Snap to increments (configurable) |
| **Numpad** | Decimal Input | Type exact values (e.g., 0.75) |
| **Shift+Keys** | Alt Decimal | Alternative to numpad for decimals |
| **Backspace** | Clear | Remove last digit of numeric input |

### Input Method Examples

#### Quick Presets
```
Press 5 → 0.5 crease (instant)
Press 8 → 0.8 crease (instant)
Press 0 → 1.0 crease (instant)
```

#### Alt Toggle
```
Current: 0.0 → Press Alt → 1.0
Current: 1.0 → Press Alt → 0.0
Current: 0.5 → Press Alt → 1.0 → Press Alt again → 0.0
```

#### Decimal Input (Numpad)
```
Type: 0.75 → Sets crease to 0.75
Type: .5 → Sets crease to 0.5
Type: 1 → Sets crease to 1.0
```

#### Decimal Input (Shift+Keys)
```
Hold Shift, press: 0, period, 3, 3 → Sets crease to 0.33
Hold Shift, press: period, 7, 5 → Sets crease to 0.75
```

---

## Preferences

Access via: **Edit > Preferences > Add-ons > Smart Crease**

### Available Settings

- **Mouse Sensitivity** (0.001 - 0.02, default 0.005)  
  Adjust drag responsiveness. Higher = faster changes

- **Snap Increment** (0.01 - 0.5, default 0.1)  
  Snap step size when Ctrl is held (e.g., 0.1 snaps to 0.0, 0.1, 0.2...)

- **HUD Font Size** (10 - 30, default 16)  
  Adjust on-screen display text size for better visibility

---

## Tips & Tricks

### Rapid Workflow
Use quick presets for speed:
- Select sharp edges → Shift+E → `0` (full crease)
- Select semi-sharp edges → Shift+E → `7` (0.7 crease)
- Select soft edges → Shift+E → `3` (0.3 crease)

### Creating Sharp Borders
1. Select faces in Face Mode (key 3)
2. Press Shift+E
3. Press `0` for full crease (or Alt toggle to 1.0)
4. Only the boundary edges become sharp

### Precise Decimal Control
1. Start with quick preset (e.g., press `5` for 0.5)
2. Then drag with Shift for fine-tuning
3. OR type exact value (numpad: `0.527`)

### Soft/Hard Edge Transition
Create smooth transitions:
```
Edge 1: Press 9 (0.9 crease)
Edge 2: Press 6 (0.6 crease)
Edge 3: Press 3 (0.3 crease)
Result: Gradual sharpness falloff
```

### Quick Reset
- Press **Alt** to toggle to 0.0 (removes all crease)
- Right-click to cancel and restore all original values

### Batch Operations
- Select multiple vertices/edges/faces
- All selected elements receive the same crease value
- Median of current values shown as starting point
- Perfect for uniform sharpness across edge loops

---

## Technical Details

### Requirements
- Blender 4.0 or later (for vertex crease support)
- Works in Edit Mode only
- Requires active mesh object with geometry

### Data Attributes
- **Vertex Crease**: Custom float layer (`crease_vert`)
  - Created automatically if doesn't exist
  - Persistent across sessions
- **Edge Crease**: Built-in edge crease attribute
  - Native Blender attribute
  - Range: 0.0 to 1.0
- Both fully compatible with Subdivision Surface modifier

### Performance
- Uses BMesh for efficient per-element access
- Batch operations on all selected elements simultaneously
- Smooth viewport updates during modal operation
- Single undo step per operation
- No performance impact when not active

### Keyboard Shortcuts
Default keymap: **Shift+E** in Edit Mode
- Overrides default Crease Edge tool in Vertex and Face modes
- Same hotkey as standard edge crease for consistency
- Can be customized in Blender's Keymap preferences

---

## Troubleshooting

### "No selected elements" warning
**Cause**: No vertices/edges/faces selected  
**Solution**:
- Ensure elements are selected in Edit Mode (orange highlight)
- Check that selection matches current mode (1/2/3 keys)
- Press A to select all if needed

### "No boundary edges found" in Face Mode
**Cause**: Entire mesh is selected (no boundaries to detect)  
**Solution**:
- Deselect some faces to create boundary edges
- OR switch to Edge Mode (key 2) to crease specific edges manually
- Face mode needs at least one unselected face to find boundaries

### Keymap conflict with Shift+E
**Issue**: Add-on uses Shift+E (same as standard Crease)  
**Impact**: Minimal - Smart Crease provides all standard functionality plus more  
**Solution**: If needed, modify keymap in Edit > Preferences > Keymap

### HUD not visible
**Solutions**:
- Increase HUD font size in addon preferences
- HUD appears at initial mouse click position
- Ensure 3D viewport is visible and active
- Check if viewport overlay is enabled (not in camera view)

### Numeric input not working
**Solutions**:
- Ensure NumLock is on (for numpad input)
- Use Shift+number keys as alternative
- Check keyboard layout (some keyboards have different numpad layouts)

### Crease not showing in viewport
**Solutions**:
- Add Subdivision Surface modifier to see crease effect
- Increase subdivision levels (2+ recommended)
- Check modifier is enabled for viewport (eye icon)

---

## Known Limitations

- Single mesh object operation only (no multi-object edit mode support)
- Face mode requires at least one boundary edge to detect boundaries
- Numeric input limited to positive values (0-1 range enforced)
- No support for negative crease values (Blender limitation)

---

## Compatibility

- **Tested**: Blender 4.0, 4.1, 4.2, 4.3+
- **Platform**: Windows, macOS, Linux
- **Dependencies**: None (uses built-in Blender modules)
- **Python**: 3.10+ (included with Blender 4.0+)

---

## Version History

### Version 1.5.1 (Current)
- Quick preset keys (1-9 = 0.1-0.9, 0 = 1.0)
- Alt key toggle between 0 and 1
- Decimal input via numpad
- Shift+keys alternative for decimal input
- Preferences for sensitivity, snap increment, HUD size
- Full vertex/edge/face mode support
- Modal operator with live HUD
- Precision and snap modifiers

### Version 1.0.0 (Initial Release)
- Basic crease functionality
- V key toggle
- Simple mouse drag control

---

## Support & Links

- **GitHub Repository**: [Stephko Toolings](https://github.com/Stephk0/Toolings)
- **Author Portfolio**: [Stephan Viranyi on ArtStation](https://www.artstation.com/stephko)
- **Issues**: Report bugs or request features on GitHub

For issues or feature requests:
1. Ensure you're using Blender 4.0 or later
2. Verify the add-on is properly installed and enabled
3. Check this documentation for solutions
4. Submit detailed bug reports with Blender version and steps to reproduce

---

## License

This add-on is provided as-is for educational and production use. Feel free to modify and distribute according to your needs. Attribution appreciated but not required.

---

**Enjoy precise crease control with Smart Crease!** 🎨✨

*Part of the Stephko Toolings collection - Professional tools for 3D artists*
