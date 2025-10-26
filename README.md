# Stephko Toolings

> Production-ready tools for Blender, Unity, and 3DS Max workflows

[![Blender](https://img.shields.io/badge/Blender-4.5+-orange.svg)](https://www.blender.org/)
[![3DS Max](https://img.shields.io/badge/3DS%20Max-Legacy-blue.svg)](https://www.autodesk.com/products/3ds-max/)
[![License](https://img.shields.io/badge/License-Free-green.svg)](LICENSE)

---

## 🚀 Quick Start

**New to these tools?** → Start here: [Complete Documentation Index](DOCUMENTATION_INDEX.md)

**Looking for specific tool?** → Jump to sections below

**Want to export assets?** → Check out [Mass Exporter v12](Blender/Addons/ClaudeVibe_WIPs/MassExporter/README.md)

---

## 📦 What's Inside

### 🔷 Blender Tools (Active Development)

**Addons** - Production-ready modeling helpers:
- **[Mass Collection Exporter v12](Blender/Addons/ClaudeVibe_WIPs/MassExporter/README.md)** - Batch export with smart empty handling ⭐ Most Popular
- **Smart Crease** - Intelligent edge crease management
- **Smart Collapse** - Context-aware mesh collapsing
- **Smart Orientation** - Auto transform orientation
- **Center Edges/Loops** - Edge loop centering
- **Edge Constraint Mode** - Edge-aligned transforms
- **Edit Mode Overlay** - Enhanced viewport feedback
- **Toggle Modifier Display** - Quick modifier visibility

**Geometry Nodes** - Procedural helpers:
- Attribute manipulation, instancing, selection tools, and more
- [See full list](DOCUMENTATION_INDEX.md#geometry-nodes)

### 🔶 Unity Tools (Planned)
Import automation and workflow helpers - Coming soon!

### 🔸 3DS Max Tools (Legacy - ST3E)
Comprehensive MaxScript collection - [Documentation](https://docs.google.com/document/d/1fIKEurSNeaazzYsPnCTYT7bVO4R4btWzTzvLRpjNutY/edit?usp=sharing)

> ⚠️ **Note:** 3DS Max tools are in maintenance mode (development paused 2023)

---

## ⚡ Quick Installation

### Blender Addons

**Option A: Direct Install**
```
1. Download addon .py file
2. Blender → Edit → Preferences → Add-ons
3. Click "Install..." and select file
4. Enable checkbox
```

**Option B: Manual Install**
```
1. Copy .py file to:
   Windows: %APPDATA%\Blender Foundation\Blender\[version]\scripts\addons\
   macOS: ~/Library/Application Support/Blender/[version]/scripts/addons/
   Linux: ~/.config/blender/[version]/scripts/addons/
2. Restart Blender
3. Enable in Preferences
```

### Geometry Nodes
```
1. Preferences → File Paths → Asset Libraries
2. Add path to Blender/Geonodes/ folder
3. Set Import Method: Link
4. Access via Asset Browser (drag & drop)
```

### 3DS Max Tools (ST3E)
```
Scripts: Copy ST3E + Startup folders → [MaxRoot]\scripts\
Modifiers: Copy Custom Modifiers contents → [MaxRoot]\Plugins\
```

[Detailed Installation Instructions](DOCUMENTATION_INDEX.md#installation-guides)

---

## 🎯 Popular Use Cases

### Game Asset Export Pipeline
```
Use Case: Export props/buildings to Unity/Unreal
Tool: Mass Exporter v12
Workflow:
  1. Organize in collections with parent empties
  2. Configure export settings (FBX, Unity preset)
  3. Batch export all assets
  4. Import directly to game engine
```

### Modular Building System
```
Use Case: Export building components as merged meshes
Tool: Mass Exporter + Empty Parents
Workflow:
  1. Parent building parts under empties
  2. Enable "Join Empty Children"
  3. Export as single merged FBX per building
  4. Use in game as prefabs
```

### Hard Surface Modeling
```
Use Case: Fast boolean-heavy modeling
Tools: Smart Crease + Smart Collapse + Edge Constraint
Workflow:
  1. Use Edge Constraint for precise placement
  2. Smart Crease for bevel control
  3. Smart Collapse for cleanup
```

[More Workflows & Examples](DOCUMENTATION_INDEX.md#workflow-examples)

---

## 📚 Documentation

**Quick Links:**
- 📖 [Complete Documentation Index](DOCUMENTATION_INDEX.md) - Start here!
- 🚀 [Mass Exporter Guide](Blender/Addons/ClaudeVibe_WIPs/MassExporter/README.md) - Most comprehensive
- 🔧 [Installation Guide](DOCUMENTATION_INDEX.md#installation-guides)
- 🐛 [Troubleshooting](DOCUMENTATION_INDEX.md#troubleshooting)
- 📝 [Quick Reference](QUICK_REFERENCE.md)

**Per-Tool Documentation:**
Each addon folder contains its own README with detailed usage instructions.

---

## ⚙️ Requirements

### Blender
- **Version:** 4.5+ (tested and recommended)
- **Platform:** Windows, macOS, Linux
- **Dependencies:** None (pure Python)

### 3DS Max (Legacy)
- **Version:** 2018+ (should work with older)
- **Platform:** Windows only
- **Dependencies:** MaxScript runtime (included with Max)

---

## 🎨 Project Status

| Tool Category | Status | Development |
|--------------|--------|-------------|
| Blender Addons | ✅ Active | New features, bug fixes |
| Blender GeoNodes | ✅ Active | New nodes, optimization |
| Unity Tools | 🔄 Planned | Future expansion |
| 3DS Max (ST3E) | ⚠️ Maintenance | Bug fixes only |

---

## 🤝 Contributing

While this is primarily a personal toolset, feedback and suggestions are welcome!

**Ways to contribute:**
- Report bugs or issues via email
- Suggest features or improvements
- Share workflows and use cases
- Create tutorial content

**Not accepting pull requests** at this time, but feel free to fork and modify for your needs!

---

## 📞 Contact & Support

**Author:** Stephan Viranyi (Stephko)

📧 Email: stephko@viranyi.de  
🎨 Portfolio: [ArtStation](https://www.artstation.com/stephko)  
💼 LinkedIn: [stephanviranyi](https://www.linkedin.com/in/stephanviranyi/)

**Getting Help:**
1. Check the [Documentation Index](DOCUMENTATION_INDEX.md)
2. Enable Debug/Verbose mode
3. Check console for errors
4. Email with details (tool, version, error message)

---

## 📜 License

**Free & Open Use**

✅ Use in personal projects  
✅ Use in commercial projects  
✅ Modify and customize  
✅ Share with others  
✅ Learn from the code

❌ Attribution appreciated but not required  
❌ No warranty provided (use at own risk)

---

## 🌟 Credits

**Development:** Stephan Viranyi  
**AI Assistance:** Claude AI (Anthropic) for code generation and documentation  
**Testing:** Personal production use + community feedback

**Built With:**
- Blender Python API
- MaxScript (3DS Max)
- Love for efficient workflows ❤️

---

## 🗺️ Roadmap

### Current Focus (2024-2025)
- ✅ Mass Exporter v12 - Complete rewrite with fallback export
- ✅ Documentation overhaul
- 🔄 Additional Blender addons
- 🔄 More geometry node presets

### Future Plans
- Unity import automation tools
- Blender-Unity material bridge
- Export preset manager
- Performance optimizations

### Maintenance
- 3DS Max tools preserved but frozen
- Bug fixes for reported issues
- Documentation updates

---

## 📈 Version History

**Latest Release:** Mass Exporter v12.0.0
- ✅ Export meshes without empties (fallback mode)
- ✅ Enhanced error handling
- ✅ Better validation and debugging

[See Changelog](Blender/Addons/ClaudeVibe_WIPs/CHANGELOG.md)

---

## 🎓 Learning Resources

### Getting Started
1. Read the [Documentation Index](DOCUMENTATION_INDEX.md)
2. Install [Mass Exporter](Blender/Addons/ClaudeVibe_WIPs/MassExporter/README.md) first
3. Experiment with other addons
4. Check out example workflows

### Advanced Usage
- Combine multiple addons for complex workflows
- Create custom export presets
- Build automation scripts
- Integrate with your pipeline

### External Resources
- [Blender Documentation](https://docs.blender.org/)
- [Unity FBX Import Guide](https://docs.unity3d.com/Manual/ImportingModelFiles.html)
- [3DS Max MaxScript Reference](https://help.autodesk.com/view/3DSMAX/2024/ENU/?guid=MAXDEV_MaxScript_en)

---

## 💡 Tips & Tricks

**Blender Workflow Tips:**
- Use Collections to organize exports
- Name your empties meaningfully (they become filenames)
- Test with Debug Tools before final export
- Enable Debug Mode to see what's happening
- Use Geometry Nodes for repetitive tasks

**Unity Integration:**
- Use FBX format with "FBX Units Scale"
- Set Forward: -Z, Up: Y for Unity
- Enable "Apply Transform" for clean imports
- Parent empty names become prefab names

**Performance:**
- Export in batches for large scenes
- Use "Apply Modifiers Before Join" sparingly
- Disable texture embedding unless needed
- Keep collection hierarchies simple

---

## 🏆 Showcase

**Want to share your work using these tools?**

Send examples to stephko@viranyi.de with:
- Project name and description
- Which tools you used
- How they helped your workflow
- Permission to showcase

Featured projects may be added to documentation!

---

## ⚡ Quick Command Reference

### Blender Shortcuts (addon-specific)

Most addons add operators accessible via:
- `F3` → Search menu (search addon name)
- `N` → Side panel (many addons add panels)
- Context menus in Edit Mode

### Common Commands
- Mass Exporter: `N` panel → Mass Exporter tab
- Debug Tools: "Move Empties to Origin", "Join ALL Empties"
- Smart tools: Usually in `F3` search menu

[Full Command Reference](QUICK_REFERENCE.md)

---

## 🔔 Stay Updated

Watch this repository or star it to be notified of updates!

**Recent Updates:**
- October 2025: Mass Exporter v12 released
- October 2025: Complete documentation overhaul
- October 2025: Documentation index created

---

## 🙏 Acknowledgments

Thanks to:
- Blender Foundation for amazing software
- Anthropic for Claude AI assistance
- 3D community for feedback and testing
- Everyone using and enjoying these tools!

---

## 📋 Repository Structure

```
Stephko_Tooling/Toolings/
├── Blender/
│   ├── Addons/
│   │   └── ClaudeVibe_WIPs/
│   │       ├── MassExporter/          ← Start here!
│   │       ├── Smart Crease/
│   │       ├── Smart Collapse/
│   │       ├── Smart Orientation/
│   │       ├── Center Edges/
│   │       ├── Edge Constraint Mode/
│   │       ├── Edit Mode Overlay/
│   │       └── Toggle Modifier Display/
│   └── Geonodes/                      ← Geometry nodes
├── 3DSMAX/
│   ├── Modifiers/                     ← Custom modifiers
│   └── Scripts/                       ← ST3E scripts
├── Unity/                             ← Coming soon
├── DOCUMENTATION_INDEX.md             ← Complete docs
├── QUICK_REFERENCE.md                 ← Cheat sheet
└── README.md                          ← You are here
```

---

**⭐ Don't forget to check out the [Complete Documentation Index](DOCUMENTATION_INDEX.md)!**

---

*Built with ❤️ for the 3D community*

**Happy Creating! 🚀**
