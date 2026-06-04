# Procedural Tree Generator - Documentation

**Version:** 1.0 - Phase 1 MVP
**Status:** ✅ Functional (Core features implemented)
**Blender Version:** 4.5+ Required
**Author:** Stephan Viranyi (Stephko)
**Date:** 2025-12-03

---

## 📁 Documentation Structure

This folder contains complete documentation for the Procedural Tree Generator:

```
TreeGenDocu/
├── README.md                                    # ← You are here
├── ProceduralTreeGenerator_Specification.md    # Complete technical specification
├── SETUP_INSTRUCTIONS.md                        # Quick start & usage guide
└── MCP_INTEGRATION.md                           # Future AI automation guide
```

**Parent Directory:**
```
Blender/Geonodes/
├── setup_tree_generator.py        # Main setup script
├── quick_test_scene.py             # Quick test scene creator
└── TreeGenDocu/                    # Documentation folder
```

---

## 🚀 Quick Start (3 Steps)

### 1. Open Blender 4.5+

### 2. Run Quick Test Scene
In Blender's Scripting workspace:
- Open `quick_test_scene.py`
- Click "Run Script" (▶ icon)
- Wait for completion message

### 3. Adjust Parameters
In Modifier Properties panel:
- Find "ProceduralTreeGenerator" modifier
- Adjust sliders to grow your tree:
  - **Iterations:** 2-3 for starters
  - **Branch Length:** 1.0-2.0
  - **Angular Spread:** 0.3-0.5
  - **Random Seed:** Change for variations

**Done! You now have a procedural tree!**

---

## 📚 Documentation Files

### 1. [ProceduralTreeGenerator_Specification.md](./ProceduralTreeGenerator_Specification.md)

**Purpose:** Complete technical specification

**Contains:**
- System architecture
- Mathematical formulas
- All planned features (Phases 1-7)
- Attribute structure
- Implementation guidelines
- 90+ pages of detailed specs

**Read this if:**
- You want to understand the full system
- You're extending functionality
- You need technical details
- You're implementing advanced features

**Skip this if:**
- You just want to use it
- You're getting started

---

### 2. [SETUP_INSTRUCTIONS.md](./SETUP_INSTRUCTIONS.md)

**Purpose:** Practical usage guide

**Contains:**
- Quick start instructions
- Parameter explanations
- Troubleshooting
- Performance tips
- Node organization details
- Advanced usage examples

**Read this if:**
- **You're using this for the first time** ← START HERE!
- You need help with parameters
- Something isn't working
- You want to customize

**Skip this if:**
- You already have it working
- You're a developer (read spec instead)

---

### 3. [MCP_INTEGRATION.md](./MCP_INTEGRATION.md)

**Purpose:** Future AI automation possibilities

**Contains:**
- MCP (Model Context Protocol) overview
- How Claude AI could control Blender
- Proposed API functions
- Implementation concepts
- Alternative workflows

**Read this if:**
- You're interested in AI automation
- You want conversational tree generation
- You're building an MCP server
- You want batch processing

**Skip this if:**
- MCP isn't relevant to you
- You just want manual control
- You're getting started (this is advanced)

---

## 📦 What's Included

### ✅ Phase 1 Features (Implemented)

| Feature | Status | Description |
|---------|--------|-------------|
| Input Processing | ✅ Done | Converts curves/edges to tree trunk |
| Branch Iteration | ✅ Done | Repeat Zones for multi-level branching |
| Random Distribution | ✅ Done | Seeded randomness for reproducibility |
| Basic Growth Direction | ✅ Done | Parent normal + random variation |
| Attribute System | ✅ Done | Core attributes stored correctly |
| Geometry Builder | ✅ Done | Curve to mesh with radius control |
| User Parameters | ✅ Done | 5 main controls exposed |
| Frame Organization | ✅ Done | Nodes organized in 5 frames |

### 🔄 Future Features (Planned)

| Phase | Features | Status |
|-------|----------|--------|
| **Phase 2** | Sun/Gravity/Wind forces, Thickness decay | 📋 Planned |
| **Phase 3** | Procedural canopy system | 📋 Planned |
| **Phase 4** | Mesh canopy integration | 📋 Planned |
| **Phase 5** | Leaf/asset scattering | 📋 Planned |
| **Phase 6** | Polish and optimization | 📋 Planned |
| **Phase 7** | MCP integration | 📋 Conceptual |

See full specification for detailed roadmap.

---

## 🎯 Parameters Reference

Quick parameter guide (see SETUP_INSTRUCTIONS.md for details):

| Parameter | Range | Default | Effect |
|-----------|-------|---------|--------|
| **Base Thickness** | 0.01-2.0m | 0.1m | Trunk/branch radius |
| **Branch Length** | 0.1-10.0m | 1.0m | How long branches grow |
| **Iterations** | 0-10 | 2 | Subdivision levels |
| **Random Seed** | 0-999,999 | 0 | Variation control |
| **Angular Spread** | 0.0-1.0 | 0.3 | Randomness/chaos |

**Pro Tip:** Start with defaults, then adjust one parameter at a time!

---

## 🛠️ Node Tree Organization

The setup script creates **5 organized frames:**

```
TreeGenerator_Main Node Group
│
├── 📦 INPUT PROCESSING (Green)
│   ├── Mesh to Curve
│   ├── Resample Curve
│   └── Set Curve Normal
│
├── 🏷️ ATTRIBUTE INITIALIZATION (Blue)
│   ├── Store iteration_level
│   ├── Store branch_id
│   ├── Store branch_thickness
│   └── Store curve_parameter
│
├── 🌿 BRANCH GENERATION (Red)
│   ├── Repeat Zone Input
│   ├── Sample Curve (spawn points)
│   ├── Create Curve Line
│   ├── Join Geometry
│   └── Repeat Zone Output
│
├── 🧭 GROWTH DIRECTION (Orange)
│   ├── Normal Node
│   ├── Random Vector
│   ├── Mix Vector
│   └── Normalize
│
└── 🔨 GEOMETRY BUILDER (Purple)
    ├── Set Curve Radius
    ├── Curve Circle (profile)
    ├── Curve to Mesh
    └── Set Shade Smooth
```

**To View:**
1. Select tree object
2. Switch to "Geometry Nodes" workspace
3. See organized frames with color coding

---

## 📝 Attributes Created

The system creates these named attributes:

| Attribute | Type | Usage |
|-----------|------|-------|
| `iteration_level` | Int | Branch generation depth (0=trunk) |
| `branch_id` | Int | Unique identifier per branch |
| `branch_thickness` | Float | Radius for mesh conversion |
| `curve_parameter` | Float | Position along curve [0-1] |

**Future phases will add:**
- `parent_branch_id` (hierarchy tracking)
- `growth_direction` (vector storage)
- `canopy_distance` (growth limiting)
- And more...

---

## 🎨 Example Workflows

### Workflow 1: Quick Tree
```
1. Run quick_test_scene.py
2. Adjust Iterations to 3
3. Change Random Seed until you like it
4. Done!
```

### Workflow 2: Custom Trunk
```
1. Add > Curve > Bezier
2. Edit curve (Tab key) to shape trunk
3. Exit edit mode
4. Run setup_tree_generator.py
5. Adjust parameters
```

### Workflow 3: Forest Variation
```
1. Create one tree (Workflow 1)
2. Duplicate object (Shift+D)
3. Change Random Seed on duplicate
4. Repeat for multiple variations
5. Arrange in scene
```

### Workflow 4: Export for Game Engine
```
1. Create tree
2. Adjust to final parameters
3. Select tree object
4. File > Export > FBX
5. Use in Unity/Unreal/Godot
```

---

## ⚠️ Troubleshooting

### Common Issues:

**No branches appear:**
- ✓ Check Iterations > 0
- ✓ Verify Branch Length > 0
- ✓ Try higher Angular Spread (0.5)

**Blender freezes:**
- ✓ Reduce Iterations to 2-3
- ✓ Lower resample count in script
- ✓ Disable viewport real-time update

**Weird shapes:**
- ✓ Try different Random Seed
- ✓ Adjust Angular Spread
- ✓ Check input curve isn't degenerate

**Can't find modifier:**
- ✓ Look for "ProceduralTreeGenerator" in Modifier Properties
- ✓ Wrench icon in properties panel
- ✓ Make sure script ran successfully

**See SETUP_INSTRUCTIONS.md for detailed troubleshooting!**

---

## 🔗 Related Files

### Main Scripts:
- `../setup_tree_generator.py` - Main installer (run this on trunk curve)
- `../quick_test_scene.py` - Auto-creates test scene (easiest start)

### Example Files (to be created):
- `../GN_treeGenerator_02.blend` - Example blend file
- Save your trees as .blend for reuse!

---

## 📊 Performance Guidelines

| Scenario | Recommended Settings | Expected Performance |
|----------|---------------------|---------------------|
| **Viewport Work** | Iterations: 2-3 | Smooth/Interactive |
| **Final Render** | Iterations: 3-5 | Some lag acceptable |
| **High Detail** | Iterations: 5-7 | Slow but manageable |
| **Extreme** | Iterations: 8+ | ⚠️ Very slow! |

**Memory Usage:**
- Typical tree (3 iterations): ~50-100 MB
- Complex tree (5 iterations): ~200-500 MB
- Extreme (7+ iterations): 1+ GB

---

## 🎓 Learning Path

### Beginner:
1. Run `quick_test_scene.py`
2. Play with 5 main parameters
3. Try different Random Seeds
4. Read SETUP_INSTRUCTIONS.md

### Intermediate:
1. Create custom trunk curves
2. Edit node tree manually
3. Add simple modifications
4. Understand frame organization

### Advanced:
1. Read full specification
2. Implement Phase 2 features
3. Add custom attributes
4. Optimize performance
5. Build MCP integration

---

## 📞 Support & Contribution

### Issues:
- Check SETUP_INSTRUCTIONS.md troubleshooting
- Review specification for technical details
- Verify Blender version (4.5+ required)

### Enhancement Ideas:
- Implement Phase 2+ features from specification
- Optimize for larger trees
- Add more presets
- Build MCP server integration

### Feedback:
- What features do you need most?
- What's confusing in documentation?
- What trees do you want to make?

---

## 📜 Version History

**v1.0 (2025-12-03):**
- ✅ Phase 1 MVP complete
- ✅ Core branch generation working
- ✅ 5 frames organized
- ✅ 5 user parameters
- ✅ Complete documentation
- ✅ Setup scripts functional

**Upcoming v1.1:**
- 🔄 Thickness/length decay
- 🔄 Gravity effect
- 🔄 Sun direction (phototropism)
- 🔄 Improved randomness

See specification for full roadmap.

---

## 📖 Documentation Map

**Start Here:**
```
New User → SETUP_INSTRUCTIONS.md → Quick Start → Experiment
```

**Deep Dive:**
```
Developer → ProceduralTreeGenerator_Specification.md → Implement Features
```

**Automation:**
```
MCP Interest → MCP_INTEGRATION.md → Plan Integration
```

**This README:**
```
Overview & Navigation → Points to other docs → Gets you started quickly
```

---

## 🌳 Happy Tree Growing!

You now have everything you need to create procedural trees!

**Next Steps:**
1. ✅ Run `quick_test_scene.py`
2. ✅ Adjust parameters
3. ✅ Make amazing trees!
4. ✅ Share your results!

Questions? Check the other documentation files!

---

**Maintained by:** Stephan Viranyi (Stephko)
**Contact:** stephko@viranyi.de
**Portfolio:** https://www.artstation.com/stephko
**Last Updated:** 2025-12-03
**License:** Part of Stephko Toolings

---

*"A tree is known by its fruit; a tool is known by its documentation."* 🌳📚
