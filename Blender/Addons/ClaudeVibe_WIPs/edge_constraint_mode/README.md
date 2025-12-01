# Edge Constraint Mode for Blender

**Version:** 1.1.0  
**Author:** Stephan Viranyi + Claude  
**Category:** Mesh Editing  
**Blender:** 3.0+

## 🎯 Overview

Edge Constraint Mode brings **3ds Max and Maya-style edge constraint** functionality to Blender. When enabled, all transforms (Translate, Rotate, Scale) are constrained to flow along existing edge topology—similar to Blender's Edge Slide, but working for rotation and scaling as well.

## ✨ Features

### Core Functionality
- ✅ **Modal Operator**: Seamless integration with Blender's transform system
- ✅ **G/R/S Hotkeys**: Natural workflow - press G (translate), R (rotate), or S (scale)
- ✅ **Edge-Constrained Motion**: All transforms flow along connected edge paths
- ✅ **Visual Feedback**: GPU-rendered edge path visualization in viewport
- ✅ **Multi-Component Support**: Works with vertices, edges, and faces

### Constraint Options
- 🔒 **Clamp to Boundaries**: Stop at edge endpoints (no overshoot)
- 🎯 **Selected Edges Only**: Constrain motion to selected edges only
- 📏 **Even Spacing**: Maintain proportional distances (like Edge Slide 'Even' mode)

### Advanced Options
- 📌 **Respect Pinned Vertices**: Keep pinned vertices fixed during transformation
- 🔀 **Stop at Non-Manifold**: Don't cross non-manifold boundaries
- 🗺️ **Preserve UV Stretch**: Experimental UV layout preservation

## 📦 Installation

### Method 1: Manual Installation
1. Copy `edge_constraint_mode.py` to your Blender addons folder:
   - Windows: `%APPDATA%\Blender Foundation\Blender\[version]\scripts\addons\`
   - Mac: `~/Library/Application Support/Blender/[version]/scripts/addons/`
   - Linux: `~/.config/blender/[version]/scripts/addons/`

2. Open Blender → Edit → Preferences → Add-ons
3. Search for "Edge Constraint Mode"
4. Enable the checkbox

### Method 2: Install from File
1. Open Blender → Edit → Preferences → Add-ons
2. Click "Install..." button
3. Navigate to `edge_constraint_mode.py`
4. Select and click "Install Add-on"
5. Enable the checkbox

## 🚀 Usage

### Quick Start
1. Switch to **Edit Mode** (Tab)
2. Select vertices, edges, or faces
3. Open **Sidebar** (press N)
4. Go to **Tool** tab
5. Click **"Enable Edge Constraint"** button
6. Press **G** (translate), **R** (rotate), or **S** (scale)
7. Move mouse to see edge-constrained transformation
8. **Left-click or Enter** to confirm
9. **Right-click or ESC** to cancel

### Detailed Workflow

#### Translation Along Edges
1. Enable Edge Constraint Mode
2. Press **G** to enter translate mode
3. Move mouse horizontally/vertically
4. Vertices slide along connected edge paths
5. Confirm with **LMB** or **Enter**

#### Rotation Along Edges
1. Enable Edge Constraint Mode
2. Press **R** to enter rotate mode
3. Move mouse to rotate around pivot
4. Each vertex follows its connected edge topology
5. Confirm with **LMB** or **Enter**

#### Scaling Along Edges
1. Enable Edge Constraint Mode
2. Press **S** to enter scale mode
3. Move mouse to scale from pivot
4. Radial motion constrained to edge paths
5. Confirm with **LMB** or **Enter**

### Tips & Tricks
- 🖱️ **Mouse Wheel**: Adjust transformation sensitivity (scroll up/down)
- 🎚️ **Options Panel**: Toggle settings before starting transformation
- 👁️ **Visual Feedback**: Green lines show active edge paths during transform
- ⚡ **Multiple Components**: Select multiple elements for complex transformations
- 🔄 **Combine with Modifiers**: Works alongside proportional editing (with limitations)

## ⚙️ Options Reference

### Constraint Options
| Option | Description | Default |
|--------|-------------|---------|
| **Clamp to Boundaries** | Stop at edge endpoints instead of overshooting | ✅ ON |
| **Selected Edges Only** | Only slide along selected edges | ❌ OFF |
| **Even Spacing** | Maintain proportional distances | ❌ OFF |

### Advanced Options
| Option | Description | Default |
|--------|-------------|---------|
| **Respect Pinned Vertices** | Keep pinned verts fixed | ✅ ON |
| **Stop at Non-Manifold** | Don't cross non-manifold boundaries | ❌ OFF |
| **Preserve UV Stretch** | Maintain UV layout (experimental) | ❌ OFF |

## 🎓 Technical Details

### Architecture
- **Modal Operator**: Uses Blender's modal system for real-time interaction
- **BMesh Integration**: Direct mesh editing for performance
- **GPU Drawing**: Hardware-accelerated visual feedback
- **Topology Analysis**: Efficient adjacency graph computation

### Transform Algorithms
- **Translation**: Projects displacement onto best-aligned edge directions
- **Rotation**: Converts rotation to per-vertex displacement, then projects to edges
- **Scale**: Converts radial scaling to displacement, then projects to edges

### Performance Notes
- Adjacency graph cached on invoke (one-time computation)
- Incremental updates during mouse movement
- Optimized for selections up to ~10,000 vertices
- GPU drawing uses hardware acceleration

## 🔧 Troubleshooting

### Issue: Addon doesn't appear in preferences
**Solution**: Make sure the .py file is in the correct addons folder

### Issue: "Edge Constraint Mode requires Edit Mode" warning
**Solution**: Switch to Edit Mode (Tab key) before enabling

### Issue: No vertices selected warning
**Solution**: Select at least one vertex/edge/face in Edit Mode

### Issue: Transforms don't follow edges as expected
**Solution**: 
- Check if "Selected Edges Only" is enabled when you want all edges
- Try adjusting sensitivity with mouse wheel
- Verify mesh has valid edge topology (no isolated vertices)

### Issue: Visual feedback lines not showing
**Solution**: 
- GPU drawing requires Blender 3.0+
- Check if viewport shading is not interfering
- Try toggling the mode off and on again

## 🆚 Comparison with Native Tools

| Feature | Edge Constraint Mode | Native Edge Slide | Native Transform |
|---------|---------------------|-------------------|------------------|
| Translate along edges | ✅ | ✅ | ❌ |
| Rotate along edges | ✅ | ❌ | ❌ |
| Scale along edges | ✅ | ❌ | ❌ |
| Multi-edge paths | ✅ | ✅ | ❌ |
| Visual feedback | ✅ | ✅ | ❌ |
| Works with faces | ✅ | ❌ | ✅ |

## 🛣️ Roadmap / Future Features

- [ ] Support for numerical input (type exact values)
- [ ] Integration with Blender's constraint system
- [ ] Custom hotkey configuration in preferences
- [ ] Geodesic vs. local tangent mode toggle
- [ ] Live pivot adjustment (drag to set pivot)
- [ ] Undo/Redo step integration
- [ ] Support for curve objects
- [ ] Batch operation recording

## 📚 Resources

- **GitHub Repository**: https://github.com/Stephk0/Toolings
- **Author's Artstation**: https://www.artstation.com/stephko
- **Maintainer**: Stephan Viranyi + Claude

## 📄 License

This addon is provided as-is for educational and commercial use.  
Please maintain attribution to the original authors.

## 🙏 Credits

**Concept**: Inspired by edge constraint workflows in 3ds Max and Maya  
**Development**: Stephan Viranyi + Claude  
**Testing**: Community feedback welcome!

## 📮 Contact & Support

For issues, suggestions, or contributions:
- Visit the GitHub repository
- Check Artstation profile for updates
- Submit issues or pull requests on GitHub

---

**Made with ❤️ by Stephan Viranyi + Claude**  
*Bringing professional 3D workflows to Blender*
