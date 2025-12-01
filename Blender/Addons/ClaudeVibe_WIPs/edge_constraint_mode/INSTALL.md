# Edge Constraint Mode - Installation & Quick Start

## 📦 Installation

### Method 1: Direct Installation (Recommended)

1. **Locate the addon folder:**
   ```
   D:\Stephko_Tooling\Toolings\Blender\Addons\ClaudeVibe_WIPs\edge_constraint_mode
   ```

2. **Open Blender Preferences:**
   - Go to `Edit > Preferences` (or press `Ctrl + Alt + U`)

3. **Install the addon:**
   - Click on the `Add-ons` tab
   - Click `Install...` button at the top
   - Navigate to the `edge_constraint_mode` folder
   - Select the folder (or zip it first and select the zip file)
   - Click `Install Add-on`

4. **Enable the addon:**
   - Search for "Edge Constraint Mode" in the add-ons list
   - Check the box next to `Mesh: Edge Constraint Mode`
   - The addon is now active!

### Method 2: Script Installation (for testing)

If you want to test the addon without installing it permanently:

```python
import sys
import importlib

# Add the addon path
addon_path = r"D:\Stephko_Tooling\Toolings\Blender\Addons\ClaudeVibe_WIPs"
if addon_path not in sys.path:
    sys.path.insert(0, addon_path)

# Import and register
import edge_constraint_mode
importlib.reload(edge_constraint_mode)
edge_constraint_mode.register()
```

Paste this into Blender's Python Console or Text Editor and run it.

---

## 🚀 Quick Start (30 seconds to first use)

### Step-by-Step First Use

1. **Select a mesh object** and press `Tab` to enter Edit Mode

2. **Select some geometry:**
   - Select vertices (1 or more)
   - Or select edges
   - Or select faces

3. **Open the sidebar:**
   - Press `N` key
   - Go to the `Tool` tab

4. **Find the panel:**
   - Look for "Edge Constraint Mode" panel
   - It should be near the top

5. **Click the button:**
   - Click `Activate Edge Constraint Mode`

6. **Transform your selection:**
   - Move your mouse to slide along edges
   - Press `G` for Translate (default)
   - Press `R` for Rotate
   - Press `S` for Scale

7. **Confirm or cancel:**
   - `Left Mouse Button` or `Enter` to confirm
   - `Right Mouse Button` or `Esc` to cancel

**That's it! You're now using Edge Constraint Mode!** 🎉

---

## 🎯 5-Minute Tutorial

### Tutorial 1: Basic Edge Sliding

**Goal:** Move the top face of a cube down while staying on the vertical edges.

```
1. Open Blender with default scene (cube)
2. Tab into Edit Mode
3. Press 3 to switch to Face select mode
4. Click the top face
5. Press N → Tool tab → Edge Constraint Mode panel
6. Click "Activate Edge Constraint Mode"
7. Move mouse downward
8. Watch the face slide down the vertical edges
9. Click LMB to confirm
```

### Tutorial 2: Rotating with Edge Constraint

**Goal:** Rotate a selection while keeping it on the surface topology.

```
1. Select multiple vertices on your mesh
2. Activate Edge Constraint Mode
3. Press R to switch to Rotate mode
4. Move mouse left/right to rotate
5. Notice how vertices slide along edges to approximate rotation
6. Click LMB to confirm
```

### Tutorial 3: Using Settings

**Goal:** Constrain sliding to only selected edges.

```
1. Select an edge loop (Alt + Click an edge)
2. Shift + Select the edges you want it to slide along
3. In Edge Constraint panel, enable "Constrain to Selected Edges Only"
4. Activate Edge Constraint Mode
5. Now the vertices will only slide on your selected edges
6. Adjust and confirm
```

---

## ⚙️ Essential Settings

### Quick Settings Reference

| Setting | Default | What it does |
|---------|---------|--------------|
| **Constrain to Selected Edges Only** | OFF | Limits sliding to selected edges |
| **Even Spacing** | OFF | Maintains uniform vertex spacing |
| **Clamp to Boundaries** | ON | Stops at edge endpoints |
| **Stop at Non-Manifold** | ON | Prevents crossing non-manifold edges |
| **Pivot Mode** | Center | Choose pivot for rotation/scale |

### Sensitivity Settings

| Setting | Default | Adjust if... |
|---------|---------|--------------|
| **Translate Sensitivity** | 0.01 | ...movement is too fast or too slow |
| **Rotate Sensitivity** | 1.0 | ...rotation is too fast or too slow |
| **Scale Sensitivity** | 1.0 | ...scaling is too fast or too slow |

---

## 🎨 Common Use Cases

### For Hard Surface Modeling
- Adjusting chamfer edges
- Repositioning boolean cut edges
- Fine-tuning mechanical details

### For Character Modeling
- Adjusting muscle flow edge loops
- Tweaking facial topology
- Repositioning anatomical features

### For Retopology
- Moving retopo loops along surface
- Adjusting edge flow
- Creating clean topology

### For General Modeling
- Any time you need precise edge-aligned transforms
- When you want rotation/scale to follow topology
- Maintaining clean edge flow

---

## ⌨️ Keyboard Shortcuts

| Key | Action |
|-----|--------|
| `N` | Show/hide sidebar (to access panel) |
| `Tab` | Toggle Edit Mode |
| `G` | Switch to Translate mode |
| `R` | Switch to Rotate mode |
| `S` | Switch to Scale mode |
| `LMB` or `Enter` | Confirm transformation |
| `RMB` or `Esc` | Cancel transformation |

---

## ❓ Troubleshooting

### "I don't see the panel"
- Make sure you're in Edit Mode (Tab)
- Press N to show sidebar
- Look in the Tool tab
- Scroll down if needed

### "Nothing happens when I activate it"
- Make sure you have geometry selected
- Check that you're in Edit Mode on a mesh object
- Try selecting different geometry (vertices, edges, or faces)

### "Movement is too sensitive"
- Lower the Translate/Rotate/Scale Sensitivity in the settings
- Move your mouse more slowly
- Try reducing sensitivity to 0.001 for very fine control

### "Vertices jump around unexpectedly"
- Enable "Stop at Non-Manifold"
- Enable "Clamp to Boundaries"
- Check if "Constrain to Selected Edges Only" should be enabled
- Make sure your mesh has clean topology

### "The addon doesn't install"
- Make sure you're selecting the entire folder
- Or try zipping the folder first
- Check that all files are present (__init__.py required)
- Restart Blender after installation

---

## 📚 Additional Resources

### Documentation
- **README.md** - Overview and features
- **USAGE_GUIDE.md** - Comprehensive usage guide with examples
- **This file** - Installation and quick start

### Links
- **GitHub:** [https://github.com/Stephk0/Toolings](https://github.com/Stephk0/Toolings)
- **ArtStation:** [https://www.artstation.com/stephko](https://www.artstation.com/stephko)
- **Report Issues:** [GitHub Issues](https://github.com/Stephk0/Toolings/issues)

---

## 🎓 Learning Path

### Beginner (First Hour)
1. ✅ Install the addon
2. ✅ Try basic translation (Tutorial 1)
3. ✅ Experiment with different selections
4. ✅ Try rotation and scale modes

### Intermediate (First Day)
1. ✅ Learn all settings
2. ✅ Try "Constrain to Selected Edges Only"
3. ✅ Experiment with pivot modes
4. ✅ Adjust sensitivity settings for your workflow

### Advanced (First Week)
1. ✅ Integrate into your modeling workflow
2. ✅ Combine with other Blender tools
3. ✅ Use for retopology projects
4. ✅ Create complex edge-constrained transformations

---

## 💡 Pro Tips

1. **Start with low sensitivity** - It's easier to increase than decrease
2. **Use with proportional editing** - Can create smooth, organic adjustments
3. **Combine with Loop Cut** - Cut first, then constrain to adjust
4. **Set pivot to 3D cursor** - For precise rotation/scale origins
5. **Enable "Selected Edges Only"** - For maximum control over slide paths

---

## 🔄 Updating the Addon

If you receive an update:

1. Remove the old version:
   - Edit > Preferences > Add-ons
   - Find "Edge Constraint Mode"
   - Click Remove

2. Install the new version:
   - Follow installation instructions above
   - Select the updated folder

3. Restart Blender (recommended)

---

## 👥 Credits

**Author:** Stephan Viranyi + Claude  
**Version:** 1.0.0  
**License:** GPL v2+  

---

## 🆘 Getting Help

**Before asking for help:**
1. ✅ Check this Quick Start guide
2. ✅ Read the USAGE_GUIDE.md
3. ✅ Look at the troubleshooting section
4. ✅ Make sure you're in Edit Mode with geometry selected

**If you still need help:**
1. Check GitHub Issues for similar problems
2. Create a new issue with:
   - Blender version
   - Steps to reproduce
   - Screenshot if possible
   - What you expected vs what happened

---

## 🎉 You're Ready!

You now have everything you need to start using Edge Constraint Mode. 

**Remember the basics:**
- `Tab` for Edit Mode
- `N` for Sidebar
- Select geometry
- Click "Activate Edge Constraint Mode"
- `G/R/S` to transform
- `LMB` to confirm

**Happy modeling!** 🎨

---

*Last updated: October 2025*  
*Edge Constraint Mode v1.0.0*
