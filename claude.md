# Claude AI Context - Stephko Toolings

> Context file for Claude AI to understand this codebase structure and development guidelines

## Project Overview

**Name:** Stephko Toolings (ClaudeVibe_WIPs)
**Author:** Stephan Viranyi (Stephko)
**Primary Focus:** Production-ready tools for Blender, Unity, and 3DS Max workflows
**Active Development:** Blender addons and geometry nodes

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
│   │   └── Compositor Render Sets/  # Compositor render management
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

**Documentation:**
- Each addon has its own README.md
- Include usage examples
- Document all properties and operators
- Provide troubleshooting section

## Key Features to Understand

### Mass Collection Exporter v12
**File:** `Blender/Addons/ClaudeVibe_WIPs/MassExporter/Mass_Collection_Exporter_v12.py`

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

**Important Implementation Details:**
- Uses temporary collections for non-destructive operations
- Handles parent-child relationships with "Apply Only Visible" option
- Batch collection management interface for efficient workflow
- Implements custom export presets
- Comprehensive error handling
- Undo-safe operations

### Compositor Render Sets v1.7.0
**File:** `Blender/Addons/ClaudeVibe_WIPs/Compositor Render Sets/`

**Core Functionality:**
- Multi-render setup management for compositor workflows
- Create Node Setup feature for automated compositor node creation
- Mute Unused File Output Nodes optimization
- Batch render set operations
- Node group organization and management

**Key Features:**
- Automated node setup creation for efficient compositor workflows
- Smart file output node management
- UI improvements for better usability
- Comprehensive render set controls

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

### Latest Updates (Branch: optimistic-dewdney)
1. **Commit 4a8e61b** - Add batch collection management and Create Node Setup features
2. **Commit 79ffbc1** - Add 'Mute Unused File Output Nodes' feature to Compositor Render Sets
3. **Commit 4693fca** - Refactor Compositor Render Sets v1.7.0 - UI improvements and fixes
4. **Commit 3f7e4b7** - Update Compositor Render Sets to v1.7.0 with major improvements
5. **Commit 2483b12** - Clean up mass exporter UI and improve descriptions
6. **Commit 8bf8028** - Updated attribute functions, removed old instancer, added Compositor Render Sets
7. **Commit 80264e5** - Add 'Apply Only Visible' modifier feature to mass exporter v12

### Active Development Areas
- Compositor Render Sets v1.7.0 enhancements (node automation, optimization)
- Mass Exporter refinement (batch collection management, UI/UX improvements)
- Geometry node library expansion
- Compositor workflow integration
- Modifier handling improvements

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

**Last Updated:** 2025-12-01
**Documentation Version:** 1.1
**Primary Branch:** main
**Active Worktree:** optimistic-dewdney

---

*This file helps Claude AI understand the codebase context, structure, and development guidelines. Update as the project evolves.*
