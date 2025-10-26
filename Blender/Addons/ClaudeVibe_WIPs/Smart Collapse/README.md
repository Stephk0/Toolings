# Smart Collapse - Blender Addon

![Version](https://img.shields.io/badge/version-1.0.0-blue)
![Blender](https://img.shields.io/badge/blender-4.0+-orange)
![Status](https://img.shields.io/badge/status-stable-green)

**Author:** Stephan Viranyi + Claude  
**Category:** Mesh Editing  
**License:** Free to share and extend

---

## 🎯 Overview

Smart Collapse eliminates the frustration of switching between "Collapse" and "Merge at Center" operations and combines them into one single hotkey.

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
2. Select **2 or more vertices** (or select edges / faces)
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


---

## 🙏 Credits

**Concept & Development:** Stephan Viranyi + Claude AI  
**Testing:** Community feedback  
**Inspired by:** 3ds Max Collapse Poly Operation

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

**Happy Modeling! 🎨✨**

