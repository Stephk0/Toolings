# Smart Collapse - Blender Addon

![Version](https://img.shields.io/badge/version-1.0.0-blue)
![Blender](https://img.shields.io/badge/blender-4.0+-orange)
![Status](https://img.shields.io/badge/status-stable-green)

**Author:** Stephan Viranyi + Claude  
**Category:** Mesh Editing  
**License:** Free to share and extend

---

## 🎯 Overview

Smart Collapse brings intelligent vertex/edge collapsing to Blender by automatically detecting topology and choosing the optimal merge method. It eliminates the frustration of switching between "Collapse" and "Merge at Center" operations.

### The Problem
In vanilla Blender:
- **Collapse** only works when edges exist between vertices
- **Merge at Center** is needed when no topology connects the vertices
- You need to manually choose the right operation based on your selection

### The Solution
Smart Collapse analyzes your selection and automatically:
- ✅ Uses **Collapse** when topology exists (preserves edge flow)
- ✅ Falls back to **Merge at Center** when vertices are disconnected
- ✅ Works in a single operation with one hotkey

---

## ✨ Features

### Core Functionality
- **Topology Detection**: Automatically analyzes selected vertices and edges
- **Smart Decision Making**: Chooses the optimal merge operation
- **Fallback System**: Gracefully handles collapse failures
- **User Feedback**: Clear messages about which method was used

### Supported Operations
| Selection | Topology | Method Used | Result |
|-----------|----------|-------------|--------|
| 2+ vertices | Connected edges | Collapse | Preserves edge flow |
| 2+ vertices | No connection | Merge at Center | Creates clean merge |
| Selected edges | Any | Collapse | Standard collapse |

---

## 📦 Installation

### Method 1: Install from File
1. Download `smart_collapse.py`
2. Open Blender
3. Go to `Edit` → `Preferences` → `Add-ons`
4. Click `Install...` button
5. Navigate to and select `smart_collapse.py`
6. Enable the checkbox next to **"Mesh: Smart Collapse"**

### Method 2: Manual Installation
1. Copy `smart_collapse.py` to Blender's addons folder:
   - **Windows:** `%APPDATA%\Blender Foundation\Blender\[version]\scripts\addons\`
   - **Mac:** `~/Library/Application Support/Blender/[version]/scripts/addons/`
   - **Linux:** `~/.config/blender/[version]/scripts/addons/`
2. Restart Blender
3. Enable in Preferences → Add-ons

---

## 🚀 Usage

### Quick Start
1. Enter **Edit Mode** (Tab)
2. Select **2 or more vertices** (or select edges)
3. Press **`Ctrl + Alt + X`**
   - OR Right-click → **Delete** menu → **Smart Collapse**
   - OR Press **X** → **Smart Collapse**
4. Vertices merge using the optimal method

### Detailed Workflow

#### Scenario 1: Connected Vertices (Collapse)
```
Before:          After Smart Collapse:
  A---B            A+B (merged)
  |   |              |
  C---D              C---D

Selection: A and B
Result: Collapsed along edge flow
```

#### Scenario 2: Disconnected Vertices (Merge at Center)
```
Before:          After Smart Collapse:
  A       B          A+B (at center point)
  
  C       D          C       D

Selection: A and B (no edge between them)
Result: Merged at center point
```

#### Scenario 3: Multiple Edge Selection
```
Before:          After Smart Collapse:
  A---B---C        A---C
      |                |
      D                D

Selection: Edges A-B and B-C
Result: B collapsed, maintains topology
```

---

## 🎮 Controls

### Keyboard Shortcut
**`Ctrl + Alt + X`** - Execute Smart Collapse

### Menu Locations
1. **Delete Menu:**
   - Edit Mode → Right-click → Delete → Smart Collapse
   
2. **Delete Pie Menu:**
   - Edit Mode → Press X → Smart Collapse (in list)

### Alternative Access
You can also find it in:
- Search Menu (`F3`) → Type "Smart Collapse"

---

## 💡 Use Cases

### 1. Cleaning Up Topology
**Problem:** After Boolean operations, you have unnecessary vertices that need removal.

**Solution:**
```
1. Select vertices to merge
2. Press Ctrl + Alt + X
3. Smart Collapse handles both connected and disconnected cases
```

### 2. Reducing Poly Count
**Problem:** Need to reduce polygon count while preserving edge flow.

**Solution:**
```
1. Select edges to collapse
2. Smart Collapse preserves topology
3. Faster than manually choosing operations
```

### 3. Merging Disconnected Vertices
**Problem:** Need to merge vertices that aren't connected by edges.

**Solution:**
```
1. Select disconnected vertices
2. Smart Collapse automatically uses merge at center
3. No need to switch operations manually
```

### 4. Mixed Selections
**Problem:** Selection contains both connected and disconnected elements.

**Solution:**
```
1. Select all vertices
2. Smart Collapse handles each case appropriately
3. Saves time over doing it manually
```

---

## 🔧 Technical Details

### Detection Algorithm
```python
1. Get selected vertices and edges
2. Check if any edges exist in selection
3. If edges exist → Use standard collapse
4. If no edges:
   a. Check if 2 vertices share an edge
   b. If yes → Use collapse
   c. If no → Use merge at center
5. Handle any collapse failures → Fallback to merge
```

### Requirements
- **Blender Version:** 4.0 or higher
- **Mode:** Edit Mode only
- **Object Type:** Mesh objects
- **Minimum Selection:** 2 vertices

### Performance
- Lightweight operation
- No heavy calculations
- Works on selections of any size
- Instant execution

---

## 🎓 Tips & Tricks

### Workflow Optimization
1. **Bulk Operations:** Select multiple vertices and run once
2. **Edge Flow Preservation:** Smart Collapse maintains topology when possible
3. **Quick Cleanup:** Faster than manually switching between operations
4. **Undo Friendly:** Standard Blender undo (`Ctrl + Z`) works normally

### Best Practices
✅ **Do:**
- Use for quick vertex/edge cleanup
- Let it automatically choose the best method
- Combine with other modeling operations
- Use on mixed selections confidently

❌ **Don't:**
- Expect it to work with single vertex (needs 2+)
- Use in Object Mode (Edit Mode only)
- Worry about topology detection (it's automatic)

---

## 🐛 Troubleshooting

### Issue: "Select at least 2 vertices" warning
**Cause:** Only 0-1 vertices selected  
**Solution:** Select 2 or more vertices

### Issue: Nothing happens when pressing hotkey
**Cause:** Not in Edit Mode or wrong context  
**Solution:** 
1. Press `Tab` to enter Edit Mode
2. Ensure you're in a 3D Viewport
3. Try accessing via menu instead

### Issue: Unexpected merge behavior
**Cause:** Topology might not be what you expect  
**Solution:**
- Check the Info panel for which method was used
- Visualize edges with `Alt + Shift + Z` (wireframe toggle)
- Manually verify topology before operation

### Issue: Keymap conflict
**Cause:** Another addon using `Ctrl + Alt + X`  
**Solution:**
1. Go to Edit → Preferences → Keymap
2. Search for "Smart Collapse"
3. Remap to different key combination

---

## 📊 Comparison with Blender Native Tools

| Feature | Smart Collapse | Native Collapse | Native Merge at Center |
|---------|---------------|-----------------|----------------------|
| Topology Detection | ✅ Automatic | ❌ Manual | ❌ Manual |
| Works on Disconnected | ✅ Yes | ❌ No | ✅ Yes |
| Works on Connected | ✅ Yes | ✅ Yes | ✅ Yes (suboptimal) |
| Single Hotkey | ✅ Yes | ✅ Yes | ✅ Yes |
| Smart Fallback | ✅ Yes | ❌ No | ❌ No |
| Decision Making | ✅ Automatic | ❌ Manual | ❌ Manual |

---

## 🛣️ Roadmap

### Planned Features
- [ ] Preference for default collapse method
- [ ] Option to disable automatic fallback
- [ ] Support for curve objects
- [ ] Custom distance threshold for "close enough" merges
- [ ] Batch operation reporting (show stats)

### Under Consideration
- [ ] Preview mode before execution
- [ ] Weighting options for merge position
- [ ] Integration with vertex groups
- [ ] Normal averaging options

---

## 🤝 Contributing

Want to improve Smart Collapse? Here's how:

1. **Report Bugs:**
   - Include Blender version
   - Describe steps to reproduce
   - Provide example .blend file if possible

2. **Suggest Features:**
   - Explain the use case
   - Describe expected behavior
   - Consider edge cases

3. **Submit Improvements:**
   - Fork the code
   - Make your changes
   - Submit with clear description

---

## 📜 Version History

### Version 1.0.0 (Current)
- Initial release
- Topology detection system
- Smart collapse/merge logic
- Fallback handling
- Menu and keymap integration
- User feedback messages

---

## 🙏 Credits

**Concept & Development:** Stephan Viranyi + Claude AI  
**Testing:** Community feedback  
**Inspired by:** 3ds Max Target Weld and Maya Merge Vertex workflow

---

## 📄 License

This addon is provided free of charge for educational and commercial use.  
Feel free to modify and redistribute with attribution.

---

## 📮 Contact & Support

**Author:** Stephan Viranyi  
**Email:** stephko@viranyi.de  
**Portfolio:** [artstation.com/stephko](https://www.artstation.com/stephko)  
**GitHub:** [github.com/Stephk0/Toolings](https://github.com/Stephk0/Toolings)

---

## 🎨 About the Author

Stephan Viranyi is a 3D artist and technical artist specializing in modeling tools and workflow optimization. With experience across Blender, 3ds Max, and Unity, Stephan creates tools that solve real production challenges.

**Check out more tools:**
- Mass Collection Exporter
- Smart Crease
- Smart Set Orientation
- Center Loops
- And more in the Stephko Toolings collection

---

**Happy Modeling! 🎨✨**

*Make vertex merging smart again.*

