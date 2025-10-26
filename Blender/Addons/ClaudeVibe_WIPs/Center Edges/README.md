# Center Loops - Blender Addon

A Blender addon for centering edge and vertex loops in mesh editing. This tool helps maintain even topology by centering edge loops between perpendicular edges, working seamlessly with triangles, quads, and n-gons. Inspired by 3ds max center loops

## Features

- **Center Edge Loops**: Automatically center selected edge loops between their perpendicular edges
- **Center Vertices**: Center selected vertices between their connected neighbors
- **Universal Compatibility**: Works with triangles, quads, and n-gons
- **Multiple Centering Modes**: Choose between average or opposite pairs methods
- **Edge Length Weighting**: Option to weight vertex centering by edge length
- **Quick Access**: Available via Edge Menu, Context Menu, and keyboard shortcut

## Installation

1. Download the `center_loops_addon.py` file
2. Open Blender and go to `Edit` → `Preferences` → `Add-ons`
3. Click `Install...` and select the downloaded file
4. Enable the addon by checking the box next to "Mesh: Center Loops"

## Usage

### Center Edge Loops

Centers selected edge loops between their perpendicular edges, ideal for maintaining even topology in quad strips and edge flows.

**Access Methods:**
- **Hotkey**: `Ctrl + Shift + C` (in Edit Mode)
- **Edge Menu**: Edit Mode → Select edges → Right-click → `Edge` menu → `Center Loops`
- **Context Menu**: Edit Mode → Select edges → Right-click → `Center Loops`

**Steps:**
1. Enter Edit Mode (`Tab`)
2. Switch to Edge Select mode (`2`)
3. Select one or more edges you want to center
4. Press `Ctrl + Shift + C` or access via menu
5. Choose centering mode if prompted:
   - **Average**: Uses average of all perpendicular vertices (default, works best for all face types)
   - **Opposite Pairs**: Averages pairs of opposite vertices (optimized for quads)

**Best For:**
- Evening out edge loops in character models
- Correcting topology flow in hard surface modeling
- Maintaining symmetry in organic modeling
- Cleaning up subdivided or extruded geometry

### Center Vertices

Centers selected vertices based on the positions of their connected neighbors.

**Access Methods:**
- **Context Menu**: Edit Mode → Select vertices → Right-click → `Center Vertices`
- **Edge Menu**: Edit Mode → `Edge` menu → `Center Vertices`

**Steps:**
1. Enter Edit Mode (`Tab`)
2. Switch to Vertex Select mode (`1`)
3. Select vertices you want to center
4. Access via right-click menu or Edge menu
5. Optional: Enable "Weight by Edge Length" to give more influence to shorter edges

**Options:**
- **Weight by Edge Length**: When enabled, vertices closer to the selected vertex have more influence on the final position

## Use Cases

### Example 1: Fixing Uneven Quad Strips
When you have a row of quads where the middle edge loop isn't centered:
1. Select the middle edge loop
2. Press `Ctrl + Shift + C`
3. The edge loop will center itself between the parallel edges

### Example 2: Cleaning Up Extruded Geometry
After extruding faces and the new edge loop is uneven:
1. Select the new edge loop
2. Use Center Loops to even it out
3. Works great with both regular and irregular topology

### Example 3: Vertex Smoothing
For fine control over vertex positions without full smoothing:
1. Select problem vertices
2. Use Center Vertices to average their position with neighbors
3. Enable edge length weighting for more natural results

## Technical Details

### How It Works

**Edge Loop Centering:**
- Identifies perpendicular edges connected to each vertex of the selected edge
- Calculates the average position of perpendicular vertices
- Moves edge vertices to the calculated center position
- Handles multiple face types simultaneously (tris, quads, ngons)

**Vertex Centering:**
- Finds all connected vertices through manifold edges
- Calculates weighted or unweighted average of neighbor positions
- Moves vertex to the averaged position

### Requirements

- Blender 2.80 or higher
- Works in Edit Mode only
- Requires manifold edges (edges connected to 2 faces)

## Tips & Tricks

- **Multiple Edges**: You can select multiple edges at once - the operator will process them all
- **Mixed Topology**: The addon automatically detects and adapts to different face types
- **Undo**: Like all Blender operations, you can undo with `Ctrl + Z`
- **Fine Control**: For subtle adjustments, you can run the operator multiple times at lower strengths
- **Selection Mode**: The context menu adapts based on your current selection mode (edge/vertex)

## Troubleshooting

**"No valid edges selected" warning:**
- Make sure you're in Edge Select mode
- Ensure selected edges are manifold (connected to exactly 2 faces)
- Non-manifold edges (boundary edges, loose edges) won't be processed

**Unexpected results:**
- Try switching between Average and Opposite Pairs centering modes
- Some topology configurations may require manual adjustment after centering
- Check that you've selected the correct edges/vertices

**Hotkey doesn't work:**
- Make sure you're in Edit Mode
- Check if another addon is using the same hotkey combination
- You can reassign the hotkey in Blender's Keymap preferences

## Version History

- **v1.5.1**: Current version with full tri/quad/ngon support
- Improved perpendicular vertex detection
- Added detailed reporting of processed face types

## Credits

**Authors:** Stephko, Claude AI  
**Category:** Mesh  
**License:** Feel free to use and modify

## Support

For issues, suggestions, or contributions, feel free to modify and improve this addon for your needs.

---

*This addon is designed to streamline mesh editing workflows and maintain clean topology in 3D modeling projects.*
