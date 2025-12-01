# Stephko Toolings

**Professional 3D Tools for Blender, 3ds Max, and Unity**

[![License](https://img.shields.io/badge/license-Free-green.svg)](LICENSE)
[![Blender](https://img.shields.io/badge/Blender-4.5+-orange.svg)](https://www.blender.org/)
[![3ds Max](https://img.shields.io/badge/3ds_Max-2020--2023-blue.svg)](https://www.autodesk.com/products/3ds-max/)
[![Status](https://img.shields.io/badge/status-Active-brightgreen.svg)](https://github.com/Stephk0/Toolings)

> Collection of production-proven tools designed to enhance 3D modeling workflows and boost productivity

---

## 📋 Table of Contents

- [Overview](#overview)
- [Quick Start](#quick-start)
- [Blender Tools](#blender-tools)
- [3ds Max Tools](#3ds-max-tools)
- [Unity Tools](#unity-tools)
- [Installation](#installation)
- [Documentation](#documentation)
- [Contributing](#contributing)
- [License](#license)
- [Contact](#contact)

---

## 🎯 Overview

Stephko Toolings is a comprehensive suite of 3D modeling tools developed for real-world production use. Each tool addresses specific workflow challenges encountered in professional 3D work.

### What's Included

| Platform | Tools | Status |
|----------|-------|--------|
| **Blender** | 8 Addons + 14 Geonodes | ✅ Active Development |
| **3ds Max** | 50+ Scripts + 24 Modifiers | 📦 Archived (2023) |
| **Unity** | Pipeline Tools | 🔮 Planned |

### Key Features

- ✨ **Production-Tested**: Used in real projects
- 🎨 **Artist-Friendly**: Intuitive interfaces and hotkeys
- 🚀 **Performance-Focused**: Optimized for speed
- 🆓 **Free Forever**: Open for use and modification
- 📚 **Well-Documented**: Comprehensive guides and examples

---

## ⚡ Quick Start

### Blender (Fastest Way)

```bash
# 1. Clone or download this repository
git clone https://github.com/Stephk0/Toolings.git

# 2. In Blender:
Edit > Preferences > Add-ons > Install from Disk

# 3. Navigate to:
Toolings/Blender/Addons/ClaudeVibe_WIPs/[addon_name]/

# 4. Select the .py file and enable the addon
```

### 3ds Max

```
1. Copy ST3E and Startup folders to:
   C:\Program Files\Autodesk\[MaxVersion]\scripts\

2. Copy Custom Modifiers to:
   C:\Program Files\Autodesk\[MaxVersion]\Plugins\

3. Restart 3ds Max
```

📖 **[Full Installation Guide](INSTALLATION.md)** | 📚 **[Complete Documentation](MASTER_DOCUMENTATION.md)**

---

## 🔷 Blender Tools

**Version**: Blender 4.5+  
**Status**: ✅ Active Development

### Featured Addons

<table>
<tr>
<td width="50%">

#### 🎯 Smart Collapse
**Hotkey:** `Ctrl + Alt + X`

Intelligently collapses edges or merges vertices based on topology analysis.

**Use Cases:**
- Topology cleanup
- Poly count reduction
- Boolean operation cleanup

[📖 Full Documentation →](Blender/Addons/ClaudeVibe_WIPs/Smart%20Collapse/)

</td>
<td width="50%">

#### ⚡ Smart Crease
**Hotkey:** `Shift + E`

Context-sensitive crease tool with modal controls and HUD display.

**Features:**
- Modal mouse control
- Numeric input
- Live preview
- Vertex/Edge/Face modes

[📖 Full Documentation →](Blender/Addons/ClaudeVibe_WIPs/Smart%20Crease/)

</td>
</tr>
<tr>
<td width="50%">

#### 📦 Mass Collection Exporter
**Location:** N-Panel > Mass Exporter

Batch export system with Unity-optimized FBX settings.

**Features:**
- Per-collection settings
- Empty-based organization
- On-demand joining
- Material overrides

[📖 Full Documentation →](Blender/Addons/ClaudeVibe_WIPs/MassExporter/)

</td>
<td width="50%">

#### 🧭 Smart Set Orientation
**Hotkey:** `Ctrl + D`

Context-aware transform orientation management.

**Features:**
- Automatic orientation detection
- Custom orientation creation
- Smart toggling
- Selection tracking

[📖 Full Documentation →](Blender/Addons/ClaudeVibe_WIPs/Smart%20Orientation/)

</td>
</tr>
<tr>
<td width="50%">

#### 🎯 Center Loops
**Hotkey:** `Ctrl + Shift + C`

Center edge loops and vertices for even topology.

**Features:**
- Multiple centering modes
- Works with all face types
- Edge length weighting
- Quick access via menu

[📖 Full Documentation →](Blender/Addons/ClaudeVibe_WIPs/Center%20Edges/)

</td>
<td width="50%">

#### 👁️ Toggle Modifier Display
**Hotkey:** `D` / `Shift + D`

Quick modifier visibility control in Edit Mode.

**Features:**
- Edit Mode only
- Intelligent parity system
- On-cage toggle
- Multi-object support

[📖 Full Documentation →](Blender/Addons/ClaudeVibe_WIPs/Toggle%20Modifier%20Display/)

</td>
</tr>
<tr>
<td width="50%">

#### 🎨 Edit Mode Overlay
**Location:** N-Panel > View Tab

Customizable overlay banner for edit mode awareness.

**Features:**
- Visual indicator
- Fully customizable
- All edit modes
- Real-time updates

[📖 Full Documentation →](Blender/Addons/ClaudeVibe_WIPs/Edit%20Mode%20Overlay/)

</td>
<td width="50%">

#### 🔗 Edge Constraint Mode
**Status:** Experimental

3ds Max-style edge constraint functionality.

**Features:**
- Edge-constrained transforms
- G/R/S hotkey integration
- Visual feedback
- Advanced options

[📖 Full Documentation →](Blender/Addons/ClaudeVibe_WIPs/edge_constraint_mode/)

</td>
</tr>
</table>

### Geometry Nodes

**14+ Node Presets** for procedural workflows:

- Attribute Functions
- Collection Instancer
- Delete Selection
- Extrude Selection
- Fill Border
- Grow Selection
- Inset Face
- Mesh From Image
- Simple Transform
- Solidify
- Split By Attribute
- And more...

**Installation:** Set as Asset Library with "Link" import method

---

## 🔶 3ds Max Tools (ST3E)

**Version**: Final Release (2023)  
**Status**: 📦 Archived  

Stephko's 3ds Max Extensions (ST3E) - A comprehensive collection of 50+ scripts and 24 custom modifiers.

### Highlights

<details>
<summary><b>Scripts (50+)</b></summary>

**Editing Operations:**
- Auto-smooth helpers
- Chamfer without smoothing
- Enhanced connects
- Edge flow tools
- Loop selection utilities
- Smart remove/weld
- And more...

**Inspection Tools:**
- Display knot points
- Material ID visualization
- Object name overlay
- Smart isolate
- Wireframe modes

**Scene Management:**
- Clean collapse
- Reference extraction
- Layer manager
- Transform reset
- Instance preservation

</details>

<details>
<summary><b>Custom Modifiers (24)</b></summary>

**Edit Poly:**
- Auto-smooth, Bevel, Connect
- Delete, Extrude, Inset
- Outline, Extrude Along Spline

**Simple Mesh:**
- Material ID by Smoothing Group
- SG shifters and converters
- UV offset by Material ID
- Vertex color/weight tools

**Simple Mod:**
- Boxify, Cylindrify, Spherify
- Offset, Pinch, Scale

</details>

📚 **[Full 3ds Max Documentation](https://docs.google.com/document/d/1fIKEurSNeaazzYsPnCTYT7bVO4R4btWzTzvLRpjNutY/edit?usp=sharing)**

---

## 🔷 Unity Tools

**Status**: 🔮 Planned

Future additions will focus on:
- Asset import pipeline
- Blender to Unity workflow
- Material automation
- Scene organization

---

## 💾 Installation

### Blender Addons

#### Method 1: Install from Disk
```
1. Blender > Edit > Preferences > Add-ons
2. Click "Install..." button
3. Navigate to addon .py file
4. Enable the checkbox
```

#### Method 2: Manual Copy
```
Copy to: %APPDATA%\Blender Foundation\Blender\[version]\scripts\addons\
Restart Blender
Enable in Preferences > Add-ons
```

### Blender Geometry Nodes
```
1. Preferences > File Paths > Asset Libraries
2. Add Geonodes folder as new library
3. Set import method to "Link"
4. Access via Asset Browser
```

### 3ds Max

#### Scripts
```
Copy: ST3E + Startup folders
To: C:\Program Files\Autodesk\[MaxVersion]\scripts\
```

#### Modifiers
```
Copy: Contents of Custom Modifiers folder
To: C:\Program Files\Autodesk\[MaxVersion]\Plugins\
```

📖 **[Detailed Installation Guide →](INSTALLATION.md)**

---

## 📚 Documentation

### Quick Links

- 📘 **[Master Documentation](MASTER_DOCUMENTATION.md)** - Complete guide to all tools
- 🚀 **[Quick Reference](QUICK_REFERENCE.md)** - Hotkeys and common workflows
- 📖 **[Installation Guide](INSTALLATION.md)** - Step-by-step setup
- ❓ **[FAQ](FAQ.md)** - Common questions and troubleshooting
- 📝 **[Changelog](CHANGELOG.md)** - Version history and updates

### Per-Tool Documentation

Each addon includes:
- Comprehensive README
- Usage examples
- Troubleshooting guide
- Tips and tricks

### External Resources

- **3ds Max ST3E Full Docs:** [Google Docs Link](https://docs.google.com/document/d/1fIKEurSNeaazzYsPnCTYT7bVO4R4btWzTzvLRpjNutY/edit?usp=sharing)
- **GitHub Repository:** [github.com/Stephk0/Toolings](https://github.com/Stephk0/Toolings)

---

## 🎓 Learning Resources

### Video Tutorials
*Coming Soon*

### Blog Posts
*Coming Soon*

### Example Files
Check the `examples/` folder for sample .blend files demonstrating tool usage.

---

## 🤝 Contributing

Want to improve these tools?

### Ways to Contribute

1. **Report Issues**
   - Use GitHub Issues
   - Include reproduction steps
   - Provide system info

2. **Suggest Features**
   - Explain the use case
   - Describe expected behavior
   - Consider alternatives

3. **Submit Code**
   - Fork the repository
   - Make your changes
   - Submit pull request

4. **Share Feedback**
   - Workflow improvements
   - Documentation updates
   - General suggestions

### Development Guidelines

- Follow existing code style
- Comment complex logic
- Update documentation
- Test thoroughly
- One feature per PR

---

## 📊 Statistics

- **Total Tools:** 92+
- **Lines of Code:** 50,000+
- **Active Users:** Growing
- **Last Updated:** 2024
- **Years in Development:** 3+

---

## 🏆 Showcase

### Used In Projects

These tools have been used in:
- Game development pipelines
- Arch visualization
- Product design
- Character modeling
- Hard surface workflows
- Procedural generation

*Submit your project to be featured!*

---

## ❓ FAQ

<details>
<summary><b>Are these tools free?</b></summary>

Yes! All tools are free to use and modify for personal and commercial projects.
</details>

<details>
<summary><b>Which Blender version do I need?</b></summary>

Blender 4.0 or higher is recommended. Most tools work on 3.0+.
</details>

<details>
<summary><b>Can I use these in commercial projects?</b></summary>

Yes! There are no restrictions on commercial use.
</details>

<details>
<summary><b>Will 3ds Max tools be updated?</b></summary>

No, development ceased in 2023. Focus shifted to Blender.
</details>

<details>
<summary><b>How do I report bugs?</b></summary>

Use GitHub Issues with:
- Software version
- Steps to reproduce
- Expected vs actual behavior
- Screenshots if relevant
</details>

---

## 📄 License

**License:** Free to share and extend

These tools are provided free of charge for educational and commercial use.  
Feel free to modify and redistribute with attribution.

**No Warranty:** Tools are provided "as-is" without warranty of any kind.

---

## 📞 Contact

**Author:** Stephan Viranyi

### Get in Touch

- **Email:** [stephko@viranyi.de](mailto:stephko@viranyi.de)
- **Portfolio:** [artstation.com/stephko](https://www.artstation.com/stephko)
- **LinkedIn:** [linkedin.com/in/stephanviranyi](https://www.linkedin.com/in/stephanviranyi/)
- **GitHub:** [github.com/Stephk0](https://github.com/Stephk0)

### Support the Project

If you find these tools useful:
- ⭐ Star the repository
- 📢 Share with colleagues
- 🐛 Report bugs
- 💡 Suggest improvements
- 🖼️ Share your work

---

## 🙏 Acknowledgments

### Special Thanks

- **Claude AI** - Development assistance
- **Blender Foundation** - Amazing software
- **Community Contributors** - Feedback and testing
- **Users** - For making this worthwhile

### Tools & Technologies

- Developed with: Python, MaxScript
- Tested on: Blender 4.5, 3ds Max 2023
- AI Assisted: Claude (Anthropic)
- Version Control: Git, GitHub

---

## 🗺️ Roadmap

### Near Term (2024)
- [ ] Complete all Blender addon documentation
- [ ] Create video tutorial series
- [ ] Add more geometry node presets
- [ ] Improve mass exporter performance

### Mid Term (2025)
- [ ] Unity tools development
- [ ] Expanded workflow integration
- [ ] Community templates library
- [ ] Automated testing suite

### Long Term
- [ ] Houdini tools exploration
- [ ] Web-based documentation
- [ ] Plugin marketplace presence
- [ ] Educational content

---

## 📈 Version History

### 2024
- ✅ Complete documentation rewrite
- ✅ 8 stable Blender addons
- ✅ Mass Exporter v12 release
- ✅ GitHub repository organization

### 2023
- ✅ 3ds Max ST3E final release
- ✅ Complete migration to Blender focus
- ✅ Edge Constraint Mode development

### 2022-Earlier
- ✅ ST3E development (50+ scripts)
- ✅ Custom modifier library (24 modifiers)
- ✅ Workflow optimization research

---

## 🎯 Mission Statement

**Making professional 3D workflows accessible to all artists.**

These tools represent years of production experience distilled into practical solutions. Every tool solves real problems encountered in actual projects.

The goal is simple:
- **Save time** on repetitive tasks
- **Reduce friction** in workflows
- **Empower artists** with better tools
- **Share knowledge** freely

---

## 🌟 Star History

[![Star History Chart](https://api.star-history.com/svg?repos=Stephk0/Toolings&type=Date)](https://star-history.com/#Stephk0/Toolings&Date)

---

<div align="center">

**Made with ❤️ by Stephan Viranyi**

*Bringing professional 3D workflows to artists worldwide*

[⬆ Back to Top](#stephko-toolings)

</div>

