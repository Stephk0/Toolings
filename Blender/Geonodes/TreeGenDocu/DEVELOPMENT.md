# Procedural Tree Generator — developer notes

Structure, roadmap and automation notes. User docs: [README](README.md).

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

## 🔗 Related Files

### Main Scripts:
- `../setup_tree_generator.py` - Main installer (run this on trunk curve)
- `../quick_test_scene.py` - Auto-creates test scene (easiest start)

### Example Files (to be created):
- `../GN_treeGenerator_02.blend` - Example blend file
- Save your trees as .blend for reuse!

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
