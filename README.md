# Stephko Toolings

> Production-ready tools for Blender, Unity, and 3DS Max workflows

[![Blender](https://img.shields.io/badge/Blender-4.5+-orange.svg)](https://www.blender.org/)
[![3DS Max](https://img.shields.io/badge/3DS%20Max-Legacy-blue.svg)](https://www.autodesk.com/products/3ds-max/)
[![License](https://img.shields.io/badge/License-Free-green.svg)](LICENSE)

---

## 🚀 Quick Start

**New to these tools?** → Start here: [Complete Documentation Index](DOCUMENTATION_INDEX.md)

**Looking for specific tool?** → Jump to sections below

---

## 📦 What's Inside

### 🔷 Blender Tools (Active Development)

**Addons** - 16 production-ready helpers across export, modeling, modifiers, UV, naming, rigging and render:
- **Mass Collection Exporter** - Batch export collections/objects with suffix grouping & parent-empty handling
- **Synced Modifiers** - Keep modifiers synchronized across objects via drivers
- **Compositor Render Sets** - Multi-render-setup management with batch rendering
- **Modifier List (Stephko fork)** - Enhanced modifier-stack UI (list / popup / sidebar)
- **Tile UV Projector** - Tile-based UV projection for texture-atlas workflows
- **Smart Crease / Smart Collapse / Smart Set Orientation / Center Edges** - 3ds Max / Maya-style modeling helpers
- **Edge Constraint Mode** - Verts slide along topology during transforms
- **Add Bounds To Name** - Rename objects from bounding-box dimensions
- **Quick Animation Export / Animation Layers Quick Export** - One-click animation/action export
- **Skin Transfer Setup** - Per-part skin setup (as-is / data transfer / bind-to-bone)
- **Edit Mode Overlay / Toggle Modifier Display** - Viewport & modifier-display helpers
- [See the full roster with versions](DOCUMENTATION_INDEX.md#blender-addons)

**Geometry Nodes** - 37-modifier **ST3E library** (Add Modifier → ST3E): deformers, generators,
topology & attribute tools, plus a procedural tree generator.
- [Full library reference](Blender/Geonodes/README.md)

### 🔶 Unity Tools (Planned)
Import automation and workflow helpers - Coming soon!

### 🔸 3DS Max Tools (Legacy - ST3E)
Comprehensive MaxScript collection - [Documentation](https://docs.google.com/document/d/1fIKEurSNeaazzYsPnCTYT7bVO4R4btWzTzvLRpjNutY/edit?usp=sharing)

> ⚠️ **Note:** 3DS Max tools are in maintenance mode (development stopped 2023)

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

## 📚 Documentation

**Quick Links:**
- 📖 [Complete Documentation Index](DOCUMENTATION_INDEX.md) - Start here!
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
- **Version:** 2020+ (some scripts should work with older versions)
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
**AI Assistance:** Claude AI (Anthropic) for code generation and documentation with Blender MCP 
**Testing:** Personal production use + community feedback

**Built With:**
- Blender Python API
- MaxScript (3DS Max)
- Love for efficient workflows ❤️


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


---

## 🔔 Stay Updated

Watch this repository or star it to be notified of updates!

**Recent Updates:**
- June 2026: ST3E Geometry Nodes library expanded to 37 modifiers (Add Modifier → ST3E)
- June 2026: Documentation refresh — full 16-addon roster + geonode library reference
- Earlier: Mass Exporter v13.6, Synced Modifiers v2.5, Tile UV Projector, Edge Constraint Mode

---

## 🙏 Acknowledgments

Thanks to:
- Blender Community
- Blender Foundation for amazing software
- Anthropic for Claude AI assistance
- 3D community for feedback and testing
- Everyone using and enjoying these tools!

---

**⭐ Don't forget to check out the [Complete Documentation Index](DOCUMENTATION_INDEX.md)!**

---

*Built with ❤️ for the 3D community*

**Happy Creating! 🚀**
