# Stephko Toolings - Quick Reference

> Fast lookup guide for common tasks and commands

## 📑 Table of Contents

- [Installation Quick Commands](#installation-quick-commands)
- [Blender Addon Commands](#blender-addon-commands)
- [Export Presets](#export-presets)
- [Common Workflows](#common-workflows)
- [Keyboard Shortcuts](#keyboard-shortcuts)
- [Troubleshooting Quick Fixes](#troubleshooting-quick-fixes)

---

## 📥 Installation Quick Commands

### Blender Addon Install
```
Method 1 (Direct):
Edit → Preferences → Add-ons → Install → Select .py file → Enable

Method 2 (Manual):
Copy to: %APPDATA%\Blender Foundation\Blender\[version]\scripts\addons\
Restart Blender → Enable in Preferences
```

### Geometry Nodes Install
```
Preferences → File Paths → Asset Libraries → Add Folder
Set: [Path]/Blender/Geonodes/ with "Link" import method
```

### 3DS Max Install
```
Scripts: Copy to [MaxRoot]\scripts\
Modifiers: Copy to [MaxRoot]\Plugins\
Restart 3DS Max
```

---

## 🔷 Blender Addon Commands

### Access Methods
| Method | How | When |
|--------|-----|------|
| Search | `F3` → Type addon name | Quick access |
| N-Panel | `N` → Find addon tab | Full interface |
| Context Menu | Right-click in Edit Mode | Context-specific |

### Mass Exporter v12

**Location:** `N` Panel → Mass Exporter tab

**Quick Operations:**
```
Export All Collections      → Main export button
Move Empties to Origin      → Debug tool (test positioning)
Join ALL Empties            → Debug tool (preview join)
```

**Common Settings:**

```
Unity Export:
  Format: FBX
  Apply Scaling: FBX Units Scale
  Apply Transform: ☑ ON
  Forward: -Z
  Up: Y
  
Unreal Export:
  Format: FBX
  Apply Scaling: FBX Units Scale
  Forward: -Y
  Up: Z

Individual Objects:
  Merge to Single: ☐ OFF
  
Single Merged File:
  Merge to Single: ☑ ON
  
With Parent Empties:
  Use Parent Empties: ☑ ON
  Center Parent Empties: ☑ ON
  
Join All to One:
  Join Empty Children: ☑ ON
  Apply Modifiers Before Join: ☑ ON (optional)
```

### Smart Crease

**Access:** `F3` → "Smart Crease"

**Quick Commands:**
```
Apply Crease        → Set crease value to selection
Clear Crease        → Remove crease from selection
```

### Smart Collapse

**Access:** `F3` → "Smart Collapse"

**Quick Commands:**
```
Collapse Edges      → Intelligent edge collapse
Collapse Vertices   → Merge vertices
```

### Smart Orientation

**Access:** `F3` → "Smart Orientation"

**Quick Commands:**
```
Set from Face       → Orient to selected face
Set from Edge       → Orient to selected edge
```

### Center Edges/Loops

**Access:** `F3` → "Center Loops"

**Quick Commands:**
```
Center Loop         → Center edge loop
Center Selection    → Center edge selection
```

### Edit Mode Overlay

**Location:** `N` Panel → Overlay tab

**Quick Toggles:**
```
Toggle Overlay      → Show/hide enhanced feedback
Color Settings      → Customize appearance
```

### Toggle Modifier Display

**Access:** `F3` → "Toggle Modifiers"

**Quick Commands:**
```
Toggle All          → Show/hide all modifiers in edit mode
Toggle Selected     → Toggle only selected object's modifiers
```

---

## 📤 Export Presets

### Unity FBX (Recommended)
```
Format: FBX
Apply Scaling: FBX Units Scale
Apply Transform: ON
Forward: -Z
Up: Y
Use Parent Empties: ON (if organized)
Center Parent Empties: ON
```

### Unreal FBX
```
Format: FBX
Apply Scaling: FBX Units Scale
Apply Transform: ON
Forward: -Y
Up: Z
Use Parent Empties: ON (if organized)
```

### Generic FBX
```
Format: FBX
Apply Scaling: FBX Units Scale
Forward: -Z
Up: Y
```

### OBJ (Compatibility)
```
Format: OBJ
Export Materials: ON
Apply Modifiers: ON
```

### glTF (Web/Modern)
```
Format: GLTF
Use Selection: ON
```

---

## 🔄 Common Workflows

### Workflow 1: Export Props Individually
```
1. Create collection "Props"
2. Add props as separate objects
3. Mass Exporter:
   - Add collection
   - Enable export ☑
   - Merge to Single: ☐ OFF
   - Set export path
4. Export All
→ Result: Prop1.fbx, Prop2.fbx, Prop3.fbx...
```

### Workflow 2: Export Merged Collection
```
1. Create collection "Building"
2. Add all building parts
3. Mass Exporter:
   - Add collection
   - Enable export ☑
   - Merge to Single: ☑ ON
   - Set export path
4. Export All
→ Result: Building.fbx (all parts merged)
```

### Workflow 3: Modular System with Empties
```
1. Create collection "ModularPieces"
2. For each variant:
   - Create empty
   - Parent meshes under empty
3. Mass Exporter:
   - Add collection
   - Enable export ☑
   - Use Parent Empties: ☑ ON
   - Center Parent Empties: ☑ ON
   - Set export path
4. Export All
→ Result: Each empty exports as separate file
```

### Workflow 4: Everything as One Mesh
```
1. Create collection with empties + children
2. Mass Exporter:
   - Add collection
   - Enable export ☑
   - Use Parent Empties: ☑ ON
   - Join Empty Children: ☑ ON
   - Apply Modifiers Before Join: ☑ ON
   - Set export path
3. Export All
→ Result: SingleMergedFile.fbx
```

### Workflow 5: Sub-Collections as Separate Files
```
1. Create parent collection "Assets"
2. Add sub-collections:
   - Furniture
   - Decorations
   - Props
3. Mass Exporter:
   - Add "Assets"
   - Enable export ☑
   - Sub-Collections as Single: ☑ ON
   - Set export path
4. Export All
→ Result: Furniture.fbx, Decorations.fbx, Props.fbx
```

---

## ⌨️ Keyboard Shortcuts

### Blender General
```
F3          → Search menu (access all addons)
N           → Toggle side panel (addon panels)
Tab         → Toggle Edit Mode
Ctrl+Z      → Undo
Ctrl+Shift+Z → Redo
```

### Addon-Specific
Most addons use:
```
F3 → [Addon Name]     → Quick access
N → [Addon Tab]       → Full interface
```

### Recommended Custom Shortcuts
Add these via: Edit → Preferences → Keymap

```
Mass Exporter Panel:
  Key: Alt+E
  Command: wm.call_menu
  
Smart Crease:
  Key: Shift+E
  Command: mesh.smart_crease
  
Smart Collapse:
  Key: Shift+X
  Command: mesh.smart_collapse
```

---

## 🐛 Troubleshooting Quick Fixes

### Issue: Addon doesn't appear
```
✓ Enable in Preferences → Add-ons
✓ Check Blender version (4.5+ required)
✓ F3 → "Reload Scripts"
✓ Check System Console for errors (Window → Toggle System Console)
```

### Issue: Export fails
```
✓ Collection selected and enabled
✓ Export path exists and is writable
✓ Objects are visible (not hidden)
✓ Enable Debug Mode
✓ Check Console output
```

### Issue: Nothing exports
```
✓ Export checkbox is checked ☑
✓ Collection has mesh objects
✓ Export path is valid
✓ Objects are not excluded/hidden
```

### Issue: Wrong scale in Unity
```
✓ Apply Scaling: FBX Units Scale
✓ Apply Transform: ON
✓ Don't use "Export at Origin" + "Apply Transforms" together
```

### Issue: Empties not moving/joining
```
✓ Use Parent Empties: ON
✓ Empties have mesh children
✓ Empties in enabled collection
✓ Test with debug buttons first
```

### Issue: Export takes forever
```
✓ Reduce "Apply Modifiers Before Join"
✓ Export smaller batches
✓ Simplify heavy geometry
✓ Disable texture embedding
```

---

## 🎯 Quick Decision Trees

### "Which export mode should I use?"

```
Need individual files?
  ├─ YES → Merge to Single: OFF
  └─ NO  → Merge to Single: ON

Have parent empties?
  ├─ YES → Use Parent Empties: ON
  │        Want each empty separate?
  │        ├─ YES → Join Empty Children: OFF
  │        └─ NO  → Join Empty Children: ON
  └─ NO  → Use Parent Empties: OFF

Need sub-collections separate?
  ├─ YES → Sub-Collections as Single: ON
  └─ NO  → Process as one collection
```

### "Which format should I use?"

```
Target Engine?
  ├─ Unity  → FBX (Units Scale, -Z forward, Y up)
  ├─ Unreal → FBX (Units Scale, -Y forward, Z up)
  ├─ Web    → glTF
  └─ Other  → FBX (generic) or OBJ (max compatibility)
```

---

## 📊 Addon Feature Matrix

| Feature | Mass Exporter | Smart Crease | Smart Collapse | Smart Orient | Center Loops |
|---------|--------------|--------------|----------------|--------------|--------------|
| Edit Mode | ✓ | ✓ | ✓ | ✓ | ✓ |
| N-Panel | ✓ | ✗ | ✗ | ✗ | ✗ |
| Object Mode | ✓ | ✗ | ✗ | ✗ | ✗ |
| Undo Support | ✓ | ✓ | ✓ | ✓ | ✓ |
| Debug Mode | ✓ | ✗ | ✗ | ✗ | ✗ |

---

## 🎨 Common Export Scenarios

### Scenario A: Game Props
```
Setup: Individual static meshes
Format: FBX
Settings:
  ☐ Merge to Single
  ☑ Apply Transform
  ☑ FBX Units Scale
```

### Scenario B: Building Module
```
Setup: Modular pieces under empties
Format: FBX
Settings:
  ☑ Use Parent Empties
  ☑ Center Parent Empties
  ☐ Join Empty Children
```

### Scenario C: Level Chunk
```
Setup: Complete scene section
Format: FBX
Settings:
  ☑ Use Parent Empties
  ☑ Join Empty Children
  ☑ Apply Modifiers
```

### Scenario D: Character + Outfit Variations
```
Setup: Base + outfit sub-collections
Format: FBX
Settings:
  ☑ Sub-Collections as Single
  ☑ Merge to Single (per sub)
```

---

## 🔢 Default Values Reference

### Mass Exporter Defaults
```
Export Format: FBX
Forward Axis: -Z
Up Axis: Y
Apply Scaling: FBX Units Scale
Apply Transform: ON
Export at Origin: OFF
Apply Transforms: OFF
Override Materials: OFF
Debug Mode: OFF
```

### Empty Centering Defaults
```
Center Parent Empties: ON
Move Empties to Origin on Export: OFF
Join Empty Children: OFF
Apply Modifiers Before Join: OFF
```

---

## 📝 Notes & Tips

### General Tips
- Always test with a simple scene first
- Use Debug Mode when things go wrong
- Name things clearly (names become filenames)
- Keep collection hierarchies simple
- Organize before exporting

### Performance Tips
- Export in batches for large projects
- Apply modifiers manually when possible
- Use instancing for repeated elements
- Keep poly counts reasonable
- Optimize textures before export

### Unity Integration
- Use FBX with recommended settings
- Import at scale 1.0 in Unity
- Apply materials in Unity after import
- Use prefab variants for variations
- Check normals after import

---

## 🔗 Quick Links

- [Complete Documentation](DOCUMENTATION_INDEX.md)
- [Mass Exporter Full Guide](Blender/Addons/ClaudeVibe_WIPs/MassExporter/README.md)
- [Main README](README.md)
- [ST3E Documentation](https://docs.google.com/document/d/1fIKEurSNeaazzYsPnCTYT7bVO4R4btWzTzvLRpjNutY/edit?usp=sharing)

---

## 📞 Need More Help?

1. Check the [Complete Documentation](DOCUMENTATION_INDEX.md)
2. Enable Debug Mode
3. Check System Console
4. Email: stephko@viranyi.de

---

**Last Updated:** October 2025  
**Version:** 1.0

---

*Quick reference for efficient workflows! ⚡*
