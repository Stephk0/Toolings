# Claude AI Context - Stephko Toolings

> Context file for Claude AI to understand this codebase structure and development guidelines

## Project Overview

**Name:** Stephko Toolings (ClaudeVibe_WIPs)
**Author:** Stephan Viranyi (Stephko)
**Primary Focus:** Production-ready tools for Blender, Unity, and 3DS Max workflows
**Active Development:** Blender addons and geometry nodes

**IMPORTANT - Project Structure:**
- This is a **compilation of independent projects**, NOT a single monolithic codebase
- Each addon in `Blender/Addons/ClaudeVibe_WIPs/` is a **separate, standalone project**
- Each geometry node asset in `Blender/Geonodes/` is an **independent tool**
- Addons may occasionally reference other addons within the same folder structure
- When working on one addon, treat it as its own project with its own scope
- Do not assume shared dependencies or unified architecture between addons

## Repository Structure

```
Stephko_Tooling/
├── Blender/
│   ├── Addons/ClaudeVibe_WIPs/     # Python addons
│   │   ├── MassExporter/            # Collection batch export tool
│   │   ├── Smart Crease/            # Edge crease management
│   │   ├── Smart Collapse/          # Context-aware mesh collapse
│   │   ├── Smart Set Orientation/   # Transform orientation helper
│   │   ├── Center Edges/            # Edge loop centering
│   │   ├── Edit Mode Overlay/       # Viewport feedback
│   │   ├── Toggle Modifier Display/ # Modifier visibility toggle
│   │   ├── Compositor Render Sets/  # Compositor render management
│   │   └── AddBoundsToName/         # Object dimension-based renaming
│   └── Geonodes/                    # Geometry node presets
│       ├── GN_AttributeFunctions_4.5.blend
│       ├── GN_CollectionInstancer.blend
│       └── [other geometry node assets]
├── Unity/                           # Unity tools (planned)
├── 3DSMAX/                          # MaxScript tools (maintenance mode)
│   ├── Scripts/ST3E/                # MaxScript utilities
│   └── Modifiers/                   # Custom modifiers
├── README.md                        # Main documentation
├── DOCUMENTATION_INDEX.md           # Complete tool index
├── QUICK_REFERENCE.md               # Quick command reference
└── claude.md                        # This file
```

## Development Context

### Current Development Status

| Category | Status | Priority |
|----------|--------|----------|
| Blender Addons | ✅ Active | High |
| Blender GeoNodes | ✅ Active | Medium |
| Unity Tools | 🔄 Planned | Low |
| 3DS Max (ST3E) | ⚠️ Maintenance | Bug fixes only |

### Technology Stack

**Blender:**
- Python 3.11+ (Blender 4.5+)
- Blender Python API (bpy)
- No external dependencies
- Pure Python implementations

**3DS Max (Legacy):**
- MaxScript
- 3DS Max 2020+
- Development paused 2023

### Code Style & Conventions

**Python (Blender Addons):**
- Follow Blender addon conventions
- Use `bl_info` dictionary for addon metadata
- Operator classes inherit from `bpy.types.Operator`
- Panel classes inherit from `bpy.types.Panel`
- Properties use `bpy.props.*` types
- Register/unregister functions for addon lifecycle

**Naming Conventions:**
- Addons: Mixed case with spaces (e.g., "Smart Crease")
- Python files: lowercase with underscores
- Classes: PascalCase with BL prefix (e.g., `OBJECT_OT_operator_name`)
- Properties: snake_case
- bl_idname: CATEGORY_PT/OT_name format

**Blender Operator Patterns:**
- Operators cannot be instantiated with `ClassName()` - Blender manages their lifecycle
- To share methods between operators, use unbound method pattern:
  ```python
  # Instead of: instance = MyOperator()
  # Use: MyOperator.method_name(self, context, args)
  ```
- Always pass `self` explicitly when calling unbound methods
- Common use case: sharing export logic between main export and quick export operators

**Documentation:**
- Each addon has its own README.md
- Include usage examples
- Document all properties and operators
- Provide troubleshooting section

## Key Features to Understand

### Mass Collection Exporter v12.1
**File:** `Blender/Addons/ClaudeVibe_WIPs/MassExporter/mass_exporter_FIXED_v12.py`

**Core Functionality:**
- Batch export multiple collections
- Batch collection management (add/remove collections from export list)
- Smart parent-child relationship handling
- Empty parent preservation/removal options
- Automatic mesh joining
- Multiple format support (FBX, OBJ, DAE, glTF)
- Material override system
- Origin auto-move functionality
- Debug logging system
- Apply Only Visible modifiers option
- Quick export from selection (export collection or sub-collections of selected object)

**Important Implementation Details:**
- Uses temporary collections for non-destructive operations
- Handles parent-child relationships with "Apply Only Visible" option
- Batch collection management interface for efficient workflow
- Implements custom export presets
- Comprehensive error handling
- Undo-safe operations
- Unbound method pattern for cross-operator method sharing (Blender operator compatibility)
- Quick export buttons find immediate collection from selected object and use configured settings

### Compositor Render Sets v1.7.4
**File:** `Blender/Addons/ClaudeVibe_WIPs/Compositor Render Sets/`

**Core Functionality:**
- Multi-render setup management for compositor workflows
- Create Node Setup feature for automated compositor node creation
- Mute Unused File Output Nodes optimization
- Synchronous batch render set operations
- Node group organization and management
- Blender 5.0 compatibility with new filename field support

**Key Features:**
- Automated node setup creation for efficient compositor workflows
- Smart file output node management (Blender 4.x and 5.0 compatible)
- Modifier sync filtering for performance optimization
- Reliable synchronous batch rendering (v1.7.3-1.7.4)
- Proper node restoration between renders with override support
- Console-based progress tracking
- UI improvements for better usability
- Comprehensive render set controls
- Automatic version detection for backward compatibility

### Add Bounds To Name v1.0
**File:** `Blender/Addons/ClaudeVibe_WIPs/AddBoundsToName/__init__.py`

**Core Functionality:**
- Automatic object renaming based on bounding box dimensions
- Flexible unit conversion (meters, centimeters, millimeters)
- Smart rounding system (floor, ceiling, standard rounding)
- Axis swizzling for custom dimension ordering
- Batch processing support for multiple objects
- Custom preset save/load system

**Key Features:**
- **Dual Bounds Calculation:** Object bounds (with modifiers) or mesh bounds (base geometry only)
- **Format Customization:** Prefix/suffix placement, custom separators, digit padding
- **Numeric Styles:** Integer or float output with configurable decimal places
- **Rounding Modes:** None, Round, Floor, Ceil with custom increments
- **Axis Ordering:** All 6 permutations of XYZ (XYZ, XZY, YXZ, YZX, ZXY, ZYX)
- **Preset System:** Save/load custom configurations for workflow standardization
- **Batch Operations:** Rename active object or all selected objects at once
- **Unit Suffixes:** Optional display of unit abbreviations (e.g., "100cm")

**User Interface:**
- 3D Viewport Sidebar panel (N key → "Bounds Name" tab)
- Organized sections: Presets, Units & Rounding, Formatting, Measurement, Actions
- Real-time feedback with debug mode option
- Undo support for all rename operations

**Example Use Cases:**
- Production asset organization: `tree_large_5x8x5`
- Export size validation: `platform_100x100x10cm`
- Modular building sets: `wall_400x200x10cm`
- Mesh optimization tracking: `rock_highpoly_2.5x1.8x2.1`

**Implementation Details:**
- Pure Python, no external dependencies
- Helper functions for unit conversion, rounding, swizzle, formatting
- Preset storage in Blender's user scripts directory
- JSON-based preset serialization
- Comprehensive error handling with debug logging

### Procedural Tree Generator v1.0
**Location:** `Blender/Geonodes/setup_tree_generator.py`
**Documentation:** `Blender/Geonodes/TreeGenDocu/`

**Core Functionality:**
- Fully procedural tree generation using Geometry Nodes
- Iterative branch spawning with Repeat Zones (Blender 4.5+)
- Organized node tree with 5 functional frames
- Reproducible randomness with seed control
- MCP-compatible for AI-assisted creation

**Phase 1 Features (Implemented):**
- Input processing (mesh/curve conversion, resampling)
- Core attribute system (iteration_level, branch_id, branch_thickness, curve_parameter)
- Multi-level branch generation (0-10 iterations)
- Random spawn point selection
- Basic growth direction (parent normal + random variation)
- Curve to mesh with radius control
- 5 user parameters exposed

**User Parameters:**
- Base Thickness (0.01-2.0m) - Trunk and branch radius
- Branch Length (0.1-10.0m) - Branch growth length
- Iterations (0-10) - Subdivision depth
- Random Seed (0-999999) - Variation control
- Angular Spread (0.0-1.0) - Randomness/chaos factor

**Setup Scripts:**
- `setup_tree_generator.py` - Main Geometry Nodes installer
- `quick_test_scene.py` - Automated test scene creator
- `send_to_blender.py` - MCP integration utility

**Phase 2+ Planned:**
- Natural growth forces (gravity, sun direction, wind)
- Thickness/length decay per iteration
- Canopy system (procedural and mesh-based)
- Leaf/asset scattering system
- Advanced optimization

**Documentation Files:**
- `README.md` - Quick start and navigation
- `SETUP_INSTRUCTIONS.md` - Detailed usage guide
- `ProceduralTreeGenerator_Specification.md` - 90-page technical spec
- `MCP_INTEGRATION.md` - AI automation guide

### Geometry Node Assets
**Location:** `Blender/Geonodes/*.blend`

**Key Node Groups:**
- `GN_AttributeFunctions_4.5` - Attribute manipulation (updated from GN_Attributes)
- `GN_CollectionInstancer` - Advanced instancing (replaces old GN_Instancer)
- `GN_Delete`, `GN_ExtrudeSelection`, `GN_FillBorder` - Modeling operations
- `GN_GrowSelection` - Selection expansion
- `GN_Compositor Render Sets` - Compositor integration

**Usage Pattern:**
- Assets linked from Asset Browser
- Import method: Link (not Append)
- Designed for procedural workflows

## Recent Changes & Context

### Latest Updates (2025-12-11)

1. **Add Bounds To Name v1.1.3** - Smart Float Formatting
   - **NEW:** Omit Decimal Zero option for clean float output (1x1.5x1 instead of 1.0x1.5x1.0)
   - **v1.1.2:** Simplified axis swizzle UI labels (X/Y/Z instead of 1st/2nd/3rd)
   - **v1.1.1:** 2D pattern detection support (detects both `1x2` and `1x2x3` formats)
   - **v1.1.0:** Independent axis swizzling, replace previous bounds, erase Blender numbering
   - **v1.0.0:** Initial release with full specification implementation
   - Complete dimension-based object renaming system
   - Flexible unit conversion (meters, centimeters, millimeters)
   - Smart rounding modes (none, round, floor, ceil) with custom increments
   - Custom preset save/load system for workflow standardization
   - Batch processing for multiple objects
   - Dual bounds calculation (object vs mesh bounds)
   - Comprehensive formatting options (prefix/suffix, separators, padding)
   - Full documentation and test suite included

### Previous Updates (2025-12-10)

2. **Compositor Render Sets v1.7.3-1.7.4** - Batch Render Overhaul
   - Complete rewrite of batch rendering system using synchronous rendering
   - Fixed batch render with override output node settings (only outputting one file)
   - Removed complex async modal/handler system
   - Implemented simple synchronous render loop (mimics "Render Current Set")
   - Proper node restoration between each render (global and override nodes)
   - Removed all progress bar code (was causing crashes)
   - Console-based progress tracking only
   - Reliable batch rendering for all configurations (global, override, mixed)

### Previous Updates (2025-12-09)

3. **Compositor Render Sets v1.7.1** - Blender 5 Compatibility & Performance
   - Fixed syntax error preventing addon installation (line 316 property definition)
   - Added Blender 5.0 file output node support (new `filename` field)
   - Implemented automatic version detection for file output nodes
   - Added modifier sync filtering: "Only Sync Modifiers in Render Set" option
   - Performance optimization: Only syncs modifiers on objects in render set collections
   - Reduced debug output for cleaner console
   - UI: Modifier filter checkbox appears as sub-option when sync is enabled
   - Backward compatible with Blender 4.x (uses prefix replacement logic)

### Previous Updates (2025-12-03)

4. **Blender MCP Integration** - ✅ Successfully Connected
   - Integrated Blender MCP server (`blender-mcp`) with Claude Code
   - Direct control of Blender through natural language
   - Socket-based communication on localhost:9876
   - Tested with object creation (icosphere, cylinder)
   - Scripts: `send_to_blender.py` for direct socket communication

5. **Procedural Tree Generator v1.0** - Phase 1 MVP Complete
   - Full Geometry Nodes implementation based on 90-page specification
   - 5 organized node frames (Input, Attributes, Branch Generation, Growth Direction, Geometry Builder)
   - Iterative branch generation using Repeat Zones
   - User parameters: Base Thickness, Branch Length, Iterations, Random Seed, Angular Spread
   - Setup scripts: `setup_tree_generator.py`, `quick_test_scene.py`
   - Complete documentation in `TreeGenDocu/` folder
   - Ready for Phase 2 development (gravity, sun, wind forces)

6. **Mass Exporter v12.1** - Fixed critical AttributeError bugs
   - Fixed unbound method calls across operators (MASSEXPORTER_OT_export_selected_collection and MASSEXPORTER_OT_export_selected_subcollections)
   - Fixed "Export Collection of Selected" button removing unwanted "_main" suffix
   - Improved quick export buttons to properly use configured export settings
   - Updated UI labels for clarity ("Quick Export from Selection")

7. **Earlier Updates (Branch: optimistic-dewdney)**
   - **Commit 4a8e61b** - Add batch collection management and Create Node Setup features
   - **Commit 79ffbc1** - Add 'Mute Unused File Output Nodes' feature to Compositor Render Sets
   - **Commit 4693fca** - Refactor Compositor Render Sets v1.7.0 - UI improvements and fixes
   - **Commit 3f7e4b7** - Update Compositor Render Sets to v1.7.0 with major improvements
   - **Commit 2483b12** - Clean up mass exporter UI and improve descriptions
   - **Commit 8bf8028** - Updated attribute functions, removed old instancer, added Compositor Render Sets
   - **Commit 80264e5** - Add 'Apply Only Visible' modifier feature to mass exporter v12

### Active Development Areas
- **Procedural Tree Generator Phase 2** - Natural growth forces (gravity, sun, wind)
- **MCP-Enhanced Workflows** - AI-assisted Blender control and iteration
- Mass Exporter bug fixes and stability improvements
- Quick export functionality refinement
- Compositor Render Sets v1.7.4 - Batch rendering complete, stable and reliable
- Geometry node library expansion
- Compositor workflow integration

### MCP Integration (Model Context Protocol)

**Status:** ✅ Active and Working

**Configuration:**
- Server: `blender-mcp` (via `uvx blender-mcp`)
- Transport: stdio
- Connection: Socket on localhost:9876
- Configuration File: `C:\Users\Stephko\.claude.json`

**Capabilities:**
- Execute arbitrary Python code in Blender
- Create and modify 3D objects
- Adjust procedural tree parameters
- Get scene information
- Render and capture screenshots
- Export objects to various formats

**Usage:**
```
Natural Language → Claude Code → MCP Server → Blender Socket → Blender Python API
```

**Example Commands:**
- "Create a tree with 3 iterations"
- "Add a cylinder at position (2,0,0)"
- "Get information about the current scene"
- "Render the viewport and save as image"

**Scripts:**
- `Blender/MCP/send_to_blender.py` - Direct socket communication utility
- Available command types: `execute_code`, `get_scene_info`, `get_object_info`, `get_viewport_screenshot`

## Common Development Tasks

### When Working on Blender Addons

**Before Making Changes:**
1. Test in Blender 4.5+ environment
2. Check for breaking changes in Blender API
3. Maintain backward compatibility when possible
4. Update addon version in bl_info

**Code Quality Checks:**
- No external dependencies
- Proper error handling
- Undo support for operators
- User-friendly error messages
- Debug mode for troubleshooting

**Testing Requirements:**
- Test with various collection hierarchies (for Mass Exporter)
- Test with different selection types (edges, faces, vertices)
- Verify undo/redo functionality
- Check viewport updates
- Test export path validation

### When Creating New Tools

**Addon Structure:**
```python
bl_info = {
    "name": "Tool Name",
    "author": "Stephan Viranyi",
    "version": (1, 0),
    "blender": (4, 5, 0),
    "category": "Appropriate Category"
}

# Operator classes
# Panel classes
# Property groups

def register():
    # Registration code

def unregister():
    # Cleanup code

if __name__ == "__main__":
    register()
```

## AI Assistance Guidelines

### When I Ask for Help With:

**Bug Fixes:**
- Check related operators and properties
- Review error handling
- Consider edge cases
- Test undo/redo impact

**New Features:**
- Follow existing code patterns
- Maintain UI consistency
- Add debug logging
- Update README documentation

**Optimization:**
- Profile performance first
- Avoid premature optimization
- Consider viewport responsiveness
- Test with large datasets

**Documentation:**
- Update README files
- Keep DOCUMENTATION_INDEX.md in sync
- Use clear, concise language
- Include usage examples

## Important Notes

### Do NOT:
- Add external Python dependencies (pure Python only)
- Break compatibility with Blender 4.5+
- Remove features without discussion
- Change naming conventions arbitrarily
- Skip documentation updates

### DO:
- Follow Blender Python API best practices
- Maintain undo support
- Add helpful error messages
- Include debug options
- Test thoroughly before committing
- Update version numbers
- Document breaking changes

## External Resources

**Blender Python API:**
- https://docs.blender.org/api/current/
- bpy.types, bpy.ops, bpy.props modules

**Testing Environment:**
- Blender 4.5+ required
- Windows primary development platform
- Test on clean Blender installations

## Contact & Collaboration

**Author:** Stephan Viranyi
**Email:** stephko@viranyi.de
**Portfolio:** https://www.artstation.com/stephko
**LinkedIn:** https://www.linkedin.com/in/stephanviranyi/

**AI Collaboration:**
- Claude AI (Anthropic) for code generation and documentation
- Blender MCP integration for development workflow

## Project Philosophy

**Core Principles:**
1. **Production-Ready** - Tools must work reliably in real workflows
2. **No Over-Engineering** - Simple, focused solutions
3. **User-Friendly** - Clear UI and helpful error messages
4. **Performance-Conscious** - Responsive even with large datasets
5. **Well-Documented** - Every tool has clear documentation

**Development Approach:**
- Iterate based on real production needs
- Personal workflow testing before release
- Community feedback integration
- Maintain backward compatibility when feasible

---

**Last Updated:** 2025-12-11
**Documentation Version:** 1.7
**Primary Branch:** main
**Active Worktree:** optimistic-dewdney
**MCP Status:** ✅ Connected (blender-mcp on localhost:9876)

---

*This file helps Claude AI understand the codebase context, structure, and development guidelines. Update as the project evolves.*
- This project has the Serena MCP server configured. Use at all times applicable, especially core programming tasks and guided or free form idiation.
- like in code, comment your geonodes as well by framing and naming nodes. it will be easier to understand for a human