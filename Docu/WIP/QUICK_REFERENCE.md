# Quick Reference Guide - Stephko Toolings

**Version:** 1.0  
**Last Updated:** 2024

> Fast reference for hotkeys, workflows, and common operations

---

## 🎹 Blender Hotkeys

### Core Addons

| Addon | Hotkey | Context | Function |
|-------|--------|---------|----------|
| **Smart Collapse** | `Ctrl + Alt + X` | Edit Mode | Collapse/Merge vertices intelligently |
| **Smart Crease** | `Shift + E` | Edit Mode | Adjust crease values with modal control |
| **Smart Orientation** | `Ctrl + D` | Any Mode | Set/toggle transform orientation |
| **Center Loops** | `Ctrl + Shift + C` | Edit Mode | Center edge loops/vertices |
| **Toggle Modifier** | `D` | Edit Mode | Toggle modifier display |
| **Toggle On Cage** | `Shift + D` | Edit Mode | Toggle on-cage display |

### Smart Crease Modal Keys

| Key | Function | Description |
|-----|----------|-------------|
| `Mouse Move` | Adjust | Drag to change crease value |
| `Shift` | Fine Tune | 10x slower adjustment |
| `Ctrl` | Snap | Snap to 0.1 increments |
| `Alt` | Reset | Set to 0.0 |
| `V` | Toggle | Toggle between 0 and 1 |
| `Numbers` | Input | Type exact value |
| `Backspace` | Clear | Clear numeric input |
| `Enter`/`LMB` | Confirm | Apply changes |
| `Esc`/`RMB` | Cancel | Restore original |

---

## 🎯 Common Workflows

### Blender: Clean Export to Unity

**Using Mass Collection Exporter:**

```
1. Open N-Panel > Mass Exporter
2. Add collection to list
3. Enable "Join Empty Children"
4. Enable "Apply Modifiers Before Join"
5. Set Export Path
6. Configure FBX settings:
   - Apply Scaling: FBX Units Scale
   - Apply Transform: ✓ Enabled
   - Axis: -Z Forward, Y Up
7. Click "Export All Collections"
```

**Result:** Clean, Unity-ready FBX with proper scale and orientation

---

### Blender: Topology Cleanup

**Using multiple tools in sequence:**

```
1. Select uneven edge loops
2. Press Ctrl + Shift + C (Center Loops)
   → Evens out topology

3. Select unnecessary vertices
4. Press Ctrl + Alt + X (Smart Collapse)
   → Removes extra geometry

5. Select sharp edges
6. Press Shift + E (Smart Crease)
   → Type "1" for full crease
   → Prepare for subdivision

7. Press Ctrl + D (Smart Orientation)
   → Align to geometry
   → Transform in correct space
```

**Result:** Clean, even topology ready for subdivision

---

### Blender: Edit Mode with Clean Geometry View

**Using modifier toggles:**

```
1. Enter Edit Mode (Tab)
2. Press D
   → First press: Sync modifiers with viewport
   → Work with modifiers visible

3. Press D again
   → Disable all modifiers in edit mode
   → See clean base geometry

4. Press Shift + D
   → Toggle on-cage display
   → For subdivision surfaces
```

**Result:** Quick toggle between full stack and base geometry

---

### 3ds Max: Mesh Preparation for Export

**Using ST3E tools:**

```
1. Use PolyFlowTools
   → Fix edge flow issues

2. Apply MaterialIDBySG modifier
   → Set material IDs from smoothing groups

3. Use SmartIsolate
   → Focus on problem areas

4. Apply CleanCollapse
   → Collapse modifiers cleanly

5. Run ResetPositionRotationScale
   → Zero out transforms
```

**Result:** Clean mesh ready for export

---

## 🎨 Blender Addon Locations

### Panel Locations

| Addon | Panel Location |
|-------|----------------|
| Mass Collection Exporter | 3D View > N-Panel > Mass Exporter |
| Edit Mode Overlay | 3D View > N-Panel > View Tab |
| Edge Constraint Mode | 3D View > N-Panel > Tool Tab |

### Menu Locations

| Addon | Menu Path |
|-------|-----------|
| Smart Collapse | Edit Mode > X (Delete) > Smart Collapse |
| | Edit Mode > Right-click > Delete > Smart Collapse |
| Smart Crease | Edit Mode > Ctrl + E (Edge Menu) > Smart Crease |
| Center Loops | Edit Mode > Right-click > Edge > Center Loops |
| | Edit Mode > Ctrl + E > Center Loops |

---

## 🔧 3ds Max ST3E Locations

### Scripts by Category

**Edit Poly Operations:**
- Located in: Right-click context menu (Edit Poly mode)
- Access via: Quad menu shortcuts

**Viewport Tools:**
- Located in: Viewport right-click
- Access via: Custom shortcuts

**Scene Management:**
- Located in: Main toolbar
- Access via: Custom shortcuts (configurable)

**Material ID Tools:**
- Located in: Modify panel
- Access via: MatIDToolBox floater

---

## 💡 Pro Tips

### Blender Modeling

**Smart Collapse:**
- Works on mixed selections (connected + disconnected)
- Automatically chooses best method
- Use for quick cleanup after Boolean operations

**Smart Crease:**
- Type exact values for precision
- Use V key for quick 0/1 toggle
- Shift for fine control
- Face mode affects boundary edges only

**Center Loops:**
- Use "Average" mode for all face types
- Use "Opposite Pairs" for quad-only topology
- Enable "Weight by Edge Length" for natural results

**Smart Orientation:**
- Press once to create custom from selection
- Press again to toggle Custom/Local
- Works differently based on mode and selection

**Mass Exporter:**
- Use "Join Empty Children" for Unity
- Enable "Move Empties to Origin" for centered pivots
- Apply modifiers before join for baked geometry

### Blender Workflow

**Edit Mode Efficiency:**
```
D → Toggle all modifiers on/off
Shift + D → Toggle cage display
Ctrl + D → Set orientation to geometry
Ctrl + Shift + C → Center selected loops
Ctrl + Alt + X → Smart merge/collapse
Shift + E → Adjust crease values
```

**Export Pipeline:**
```
1. Organize in collections
2. Parent to empties for centers
3. Use Mass Exporter for batch
4. One-click Unity-ready FBX
```

---

## 🎯 Decision Trees

### When to Use Which Tool

**Need to merge vertices?**
```
Do edges connect them?
├─ Don't know → Use Smart Collapse (auto-detects)
├─ Yes → Smart Collapse (will use Collapse)
└─ No → Smart Collapse (will use Merge at Center)
```

**Need to adjust crease?**
```
What are you selecting?
├─ Vertices → Smart Crease (vertex mode)
├─ Edges → Smart Crease (edge mode)
└─ Faces → Smart Crease (boundary edges mode)
```

**Need to set orientation?**
```
Do you have selection?
├─ Yes → Ctrl + D (creates custom)
│   └─ Press again → Toggle Custom/Local
└─ No → Ctrl + D (toggles Local/Global)
```

**Need to export to Unity?**
```
Single object?
├─ Yes → Standard FBX export
└─ No → Use Mass Exporter
    ├─ Organized by empties? → Enable "Join Empty Children"
    ├─ Multiple collections? → Batch export
    └─ Need materials? → Set material override
```

---

## 📊 Hotkey Priority

### Most Used (Daily)

1. `Ctrl + Alt + X` - Smart Collapse
2. `D` - Toggle Modifier Display
3. `Ctrl + D` - Smart Orientation
4. `Shift + E` - Smart Crease

### Situational (As Needed)

1. `Ctrl + Shift + C` - Center Loops
2. `Shift + D` - Toggle On Cage
3. Mass Exporter (panel-based)
4. Edit Mode Overlay (panel-based)

### 3ds Max Most Used

1. `SmartIsolate` - Isolate selection
2. `PolyFlowTools` - Fix edge flow
3. `CleanCollapse` - Collapse stack
4. `MaterialIDBySG` - Set material IDs

---

## 🔄 Workflow Presets

### Character Modeling

```
1. Block out base form
2. Center Loops for even topology
3. Smart Crease for detail definition
4. Smart Orientation for aligned transforms
5. Toggle Modifier Display to work with/without SubD
6. Smart Collapse for cleanup
7. Mass Export to engine
```

### Hard Surface

```
1. Boolean operations
2. Smart Collapse to clean up
3. Smart Crease for hard edges (1.0)
4. Center Loops for even panels
5. Smart Orientation for bevel alignment
6. Mass Export with material overrides
```

### Asset Creation

```
1. Model in collections
2. Parent to empties for pivots
3. Smart Crease for bake definition
4. Mass Export with "Join Empty Children"
5. Unity import with proper scale
```

---

## 🎓 Learning Path

### Beginner
1. Install 2-3 essential addons
2. Learn default hotkeys
3. Practice Smart Collapse and Toggle Modifier
4. Explore panel features

### Intermediate
1. Master all hotkey combinations
2. Use Smart Crease modal controls
3. Set up Mass Exporter workflow
4. Create custom keyboard shortcuts

### Advanced
1. Combine tools in sequences
2. Create scripted workflows
3. Customize addon preferences
4. Optimize for specific projects

---

## 🔖 Bookmarks

### Frequently Accessed

**Documentation:**
- Master Documentation: See MASTER_DOCUMENTATION.md
- Installation Guide: See INSTALLATION.md
- Individual addon READMEs

**External:**
- [3ds Max ST3E Docs](https://docs.google.com/document/d/1fIKEurSNeaazzYsPnCTYT7bVO4R4btWzTzvLRpjNutY/edit?usp=sharing)
- [Author Portfolio](https://www.artstation.com/stephko)
- [GitHub Repository](https://github.com/Stephk0/Toolings)

---

## 📝 Notes

### Customization

All Blender hotkeys can be remapped:
```
Edit > Preferences > Keymap
Search for addon name
Modify key binding
```

### Performance Tips

- Disable unused addons for performance
- Use Debug Mode in Mass Exporter for troubleshooting
- Center Loops works best on manifold geometry
- Smart Crease is instant (no performance impact)

### Compatibility

- **Blender 4.5+** recommended
- **3.0+** supported (most addons)
- **3ds Max 2020-2023** for ST3E
- **Unity 2021+** for export workflow

---

## 🆘 Quick Troubleshooting

### Hotkey Not Working
```
1. Check you're in correct mode (Edit/Object)
2. Verify addon is enabled
3. Look for keymap conflicts
4. Try accessing via menu instead
```

### Addon Not Showing
```
1. Check Blender version compatibility
2. Verify installation folder
3. Check addon is enabled in preferences
4. Restart Blender
```

### Export Issues
```
1. Enable Debug Mode
2. Check console for errors
3. Verify export path exists
4. Test with single object first
```

---

## 🎯 Summary

### Most Important Hotkeys

```
Ctrl + Alt + X → Smart Collapse (topology cleanup)
Shift + E → Smart Crease (edge control)
Ctrl + D → Smart Orientation (transform space)
D → Toggle Modifiers (edit mode view)
```

### Essential Workflows

```
Topology → Center Loops + Smart Collapse
Crease → Smart Crease + Smart Collapse
Export → Mass Exporter (Unity optimized)
View → Toggle Modifier Display (clean geometry)
```

### Remember

- **Tools work together** - Combine for best results
- **Context matters** - Behavior changes with mode/selection
- **Practice hotkeys** - Faster than menu navigation
- **Read full docs** - This is just quick reference

---

**For complete information, see:** [Master Documentation](MASTER_DOCUMENTATION.md)

**Made with ❤️ by Stephan Viranyi**

