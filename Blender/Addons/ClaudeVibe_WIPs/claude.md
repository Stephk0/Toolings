# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a collection of Blender addons (Python-based plugins) designed to enhance 3D modeling workflows. Each addon is a standalone tool that integrates with Blender's UI and extends its functionality. The repository contains both stable addons and work-in-progress features.

## Repository Structure

The codebase is organized as a collection of independent Blender addons, each in its own directory:

- **MassExporter/** - Batch collection export system with complex empty/parent handling
- **Compositor Render Sets/** - Automated compositor-based rendering with File Output node management
- **Edit Mode Overlay/** - Visual overlay indicator for edit mode
- **edge_constraint_mode/** - 3ds Max/Maya-style edge constraint transforms
- **Smart Crease/** - Context-sensitive crease editing with modal controls
- **Smart Collapse/** - Intelligent merge/collapse hybrid operator
- **Smart Set Orientation/** - Maya-style automatic transform orientation management
- **Center Edges/** - Edge loop and vertex centering tools
- **Toggle Modifier Display/** - Keyboard shortcuts for modifier visibility in edit mode

Each addon directory typically contains:
- One or more `.py` files (the addon code)
- A `README.md` with user documentation
- Some addons may have a `WIP/` subdirectory for experimental versions

## Development Workflow

### Installing/Testing Addons in Blender

To test an addon during development:
```bash
# Method 1: Install via Blender UI
# Edit > Preferences > Add-ons > Install... > Select the .py file

# Method 2: Copy to Blender addons folder
# Windows: %APPDATA%\Blender Foundation\Blender\[version]\scripts\addons\
# macOS: ~/Library/Application Support/Blender/[version]/scripts/addons/
# Linux: ~/.config/blender/[version]/scripts/addons/
```

After installation, enable the addon in Blender Preferences > Add-ons panel.

### Blender Addon Architecture

All addons follow Blender's standard addon structure:

1. **bl_info dictionary** - Metadata (name, author, version, blender version, category)
2. **Operators** - Classes inheriting from `bpy.types.Operator` that perform actions
3. **Panels** - Classes inheriting from `bpy.types.Panel` for UI in the 3D viewport sidebar (N-panel)
4. **Properties** - Custom properties stored on scenes/objects using `bpy.props`
5. **Registration** - `register()` and `unregister()` functions to load/unload the addon

### Common Blender API Patterns

**BMesh Operations:**
- Use `bmesh.from_edit_mesh()` for edit mode mesh access
- Always call `bmesh.update_edit_mesh()` after modifications
- BMesh provides direct vertex/edge/face manipulation

**Modal Operators:**
- Used for interactive tools (like Smart Crease, Edge Constraint Mode)
- `invoke()` - Called when operator starts
- `modal()` - Called on every event (mouse move, key press)
- Return `{'RUNNING_MODAL'}`, `{'FINISHED'}`, or `{'CANCELLED'}`

**Property Groups:**
- Custom settings stored using `PropertyGroup` classes
- Registered to Scene/Object with `PointerProperty`
- Accessed via `context.scene.custom_props`

**Context Sensitivity:**
- Operators check `context.mode` (e.g., 'EDIT_MESH', 'OBJECT')
- Use `poll()` classmethod to enable/disable operators based on context

**Visibility Management:**
- **CRITICAL**: Use `LayerCollection.hide_viewport` for eye icon in outliner
- **NOT**: `Collection.hide_viewport` (global, doesn't affect outliner)
- Use `find_layer_collection()` to recursively find LayerCollection from Collection
- Always update both 3D Viewport and Outliner areas after visibility changes

## Key Architectural Patterns

### 1. Mass Exporter - Complex Export Pipeline

The Mass Exporter (v12) is the most complex addon with these key components:

- **Collection Management**: Tracks multiple collections with individual export settings
- **Parent Empty System**: Handles hierarchy of Empty objects with mesh children
- **Join Operations**: On-demand mesh joining without affecting source scene
- **Export Formats**: Supports FBX, OBJ, Collada, glTF with format-specific options

Important architecture notes:
- Core logic is extracted into standalone functions (e.g., `move_empties_to_origin_core_logic`) to be reused by both UI buttons and export operators
- Uses temporary duplicates for non-destructive joins
- Fallback system: attempts empty-based export, falls back to regular mesh export if no empties found

### 2. Modal Transform Operators

Several addons use modal operators for real-time interaction:

**Smart Crease:**
- Modifier keys: Shift (precision), Ctrl (snap), Alt (toggle 0/1), Number keys (presets)
- Decimal input system via numpad or Shift+keys
- Context-aware: adapts to vertex/edge/face mode
- HUD rendering with GPU overlay

**Edge Constraint Mode:**
- Mathematical edge projection system (`EdgeConstraintSolver` class)
- Adjacency graph for topology navigation
- G/R/S hotkeys switch between translate/rotate/scale modes
- GPU-rendered edge path visualization

### 3. Context-Aware Tool Design

Multiple addons use selection context to determine behavior:

**Smart Set Orientation:**
- Selection hash tracking using MD5 to detect changes
- Different behavior in Object vs Edit mode
- Automatic custom orientation creation from selection

**Smart Collapse:**
- Analyzes topology to choose between Collapse vs Merge at Center
- Fallback chain: try collapse → fallback to merge if fails

### 4. Compositor & Render Pipeline Integration

**Compositor Render Sets** demonstrates advanced pipeline patterns:

- **Render Handlers**: Use `bpy.app.handlers.render_complete` for async render detection
- **Node State Management**: Cache and restore File Output node settings between renders
- **Modal Rendering**: Sequential render queue with state restoration after completion
- **Visibility Orchestration**: Sync LayerCollection, Collection, and Modifier visibility states

**Critical Pattern - State Restoration:**
```python
# Cache original state
original_state = cache_node_state(node)

# For each render set:
restore_node_state(node, original_state)  # Reset to original
configure_node_for_set(node, render_set)  # Apply new settings
render()

# Final restoration
restore_node_state(node, original_state)
```

## Blender Version Compatibility

- Minimum Blender version: **3.0+** (most addons)
- Some features require Blender **4.0+** (vertex crease support in Smart Crease)
- Python version: 3.10+ (bundled with Blender)

## MCP Server Configuration

**IMPORTANT**: Claude Code and Claude Desktop maintain **separate configuration files** and do not automatically share MCP server settings.

### Configuration Locations

- **Claude Desktop**: `%APPDATA%\Claude\claude_desktop_config.json` (Windows)
- **Claude Code**:
  - **Per-Project Configuration**: `~/.claude.json` under the `projects` key (recommended)
  - **Global Settings** (deprecated for MCP): `~/.claude/settings.json`

**Note:** Claude Code uses a **per-project MCP server configuration system** stored in `~/.claude.json`. Each project directory has its own `mcpServers` section under the `projects` key. The `settings.json` file is used for other settings but NOT for MCP server configuration.

### Configured MCP Servers

This project uses three MCP servers for enhanced development capabilities:

1. **Filesystem Server** (`@modelcontextprotocol/server-filesystem`)
   - Command: `npx -y @modelcontextprotocol/server-filesystem`
   - Provides file access to project directories
   - Accessible paths:
     - Desktop, Downloads
     - Unity game prototype Assets folders
     - Blender addons workspace (this repository)
     - Toolings root directory

2. **Blender MCP** (`blender-mcp`)
   - Command: `uvx blender-mcp`
   - Provides direct Blender integration via MCP protocol
   - Connects to Blender on port 9876
   - Enables Python script execution, scene manipulation, and addon testing
   - **Requires**: Blender running with MCP server enabled

3. **Unity MCP** (`MCPForUnityServer`)
   - Command: `uv.exe run --directory [path] server.py`
   - Provides Unity Editor integration
   - Connects to Unity on port 6400
   - Version: 4.1.1
   - Dependencies: httpx>=0.27.2, mcp[cli]>=1.15.0

### Verifying MCP Server Status

After configuring or modifying MCP servers:

1. **Restart Claude Code** for changes to take effect
2. Check for MCP-provided tools with `mcp__` prefix:
   - `mcp__blender__*` - Blender operations
   - `mcp__filesystem__*` - File operations
   - `mcp__unityMCP__*` - Unity operations
3. If servers don't connect, check:
   - Executables exist: `npx --version`, `uvx --version`
   - Blender/Unity are running (for respective servers)
   - Configuration syntax is valid JSON

### Configuration Template

**Per-Project Configuration (in `~/.claude.json`):**

```json
{
  "projects": {
    "D:\\Your\\Project\\Path": {
      "mcpServers": {
        "filesystem": {
          "type": "stdio",
          "command": "npx",
          "args": ["-y", "@modelcontextprotocol/server-filesystem", "C:\\path\\to\\dir"],
          "env": {}
        },
        "blender": {
          "type": "stdio",
          "command": "uvx",
          "args": ["blender-mcp"],
          "env": {}
        },
        "unityMCP": {
          "type": "stdio",
          "command": "C:\\path\\to\\uv.exe",
          "args": ["run", "--directory", "C:\\path\\to\\src", "server.py"],
          "env": {}
        }
      },
      "allowedTools": [],
      "mcpContextUris": [],
      "enabledMcpjsonServers": [],
      "disabledMcpjsonServers": []
    }
  }
}
```

**Important:** Replace `D:\\Your\\Project\\Path` with the actual absolute path to your project directory.

### Troubleshooting MCP Servers

**Problem**: MCP servers configured in Claude Desktop but not available in Claude Code
**Solution**: MCP servers must be configured per-project in `~/.claude.json` under the `projects.[project_path].mcpServers` key, not in `~/.claude/settings.json`

**Problem**: Error: `'\' is not recognized as an internal or external command`
**Solution**: Corrupted MCP server entries in `~/.claude.json`. Check for servers with `"command": "\\"` and remove them. Add properly formatted MCP servers to the current project's configuration instead.

**Problem**: Blender MCP server can't connect
**Solution**: Ensure Blender is running and the MCP server addon is enabled in Blender

**Problem**: MCP tools not appearing after configuration
**Solution**:
1. Verify configuration is in the correct location (`~/.claude.json` under `projects` key)
2. Check debug logs at `~/.claude/debug/[latest].txt` for connection errors
3. Restart Claude Code completely (not just reload)

## Common Development Tasks

### Testing an Addon
1. Copy the `.py` file to Blender's addons folder
2. Restart Blender or reload scripts (`F3` > "Reload Scripts")
3. Enable in Preferences > Add-ons
4. Check the 3D Viewport sidebar (press `N`) for the addon's panel

### Debugging
- Use Blender's System Console: `Window > Toggle System Console`
- Print statements appear in the console
- Many addons have debug modes that output verbose logging

### Modifying Existing Addons
When updating an addon:
1. Always increment the version number in `bl_info`
2. Preserve existing user settings/properties
3. Test in both Edit Mode and Object Mode (if applicable)
4. Check console for errors and warnings

### Creating New Operators
```python
class MESH_OT_my_operator(bpy.types.Operator):
    bl_idname = "mesh.my_operator"  # Used in bpy.ops.mesh.my_operator()
    bl_label = "My Operator"
    bl_options = {'REGISTER', 'UNDO'}  # Makes it undoable

    @classmethod
    def poll(cls, context):
        # Only available in Edit Mode on mesh objects
        return context.mode == 'EDIT_MESH'

    def execute(self, context):
        # Your code here
        return {'FINISHED'}
```

### Adding UI Panels
```python
class VIEW3D_PT_my_panel(bpy.types.Panel):
    bl_label = "My Tool"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Tool'  # Tab name in sidebar
    bl_context = 'mesh_edit'  # Only show in edit mode

    def draw(self, context):
        layout = self.layout
        layout.operator("mesh.my_operator")
```

## Git Workflow

- **Main branch**: `main`
- Blend1 files (auto-save backups) are gitignored
- The repository tracks standalone Python files, not installed addon packages

## Important Notes

- Each addon is completely independent - no shared libraries between addons
- READMEs contain user-facing documentation; technical details are in code comments
- Many addons were developed collaboratively with Claude AI (noted in credits)
- WIP folders contain experimental/debugging versions - production code is at the root of each addon folder
- When multiple versions exist (e.g., mass_exporter_v1.py, v2.py, etc.), the highest version number or "FIXED" suffix indicates the current stable version

## Common Pitfalls & Solutions

### Visibility Not Working
**Problem**: Collection visibility changes don't show in outliner
**Solution**: Use `LayerCollection.hide_viewport`, not `Collection.hide_viewport`
```python
layer_coll = find_layer_collection(view_layer.layer_collection, collection)
layer_coll.hide_viewport = False  # Correct - controls eye icon
```

### Modal Operator with Rendering
**Problem**: `context.scene.render.is_rendering` doesn't exist
**Solution**: Use render handlers to detect completion
```python
bpy.app.handlers.render_complete.append(self.on_render_complete)
# In modal: check self._render_complete flag
```

### Node State Not Restoring
**Problem**: File Output node state accumulates changes across renders
**Solution**: Restore to cached original state BEFORE each configuration
```python
# Wrong: configure → render → configure → render
# Right: restore → configure → render → restore → configure → render
```

### Modifier Sync
**Problem**: Viewport modifiers don't match render
**Solution**: Sync `modifier.show_render = modifier.show_viewport`

## Testing Checklist for New/Modified Addons

1. Does the addon register/unregister cleanly?
2. Does it work in the correct mode (Edit/Object)?
3. Are all operators undoable (`'UNDO'` in bl_options)?
4. Does it handle edge cases (no selection, wrong object type)?
5. Are error messages clear and actionable?
6. Is the bl_info version incremented?
7. Does it work with multi-object selection (if applicable)?
8. Are state changes properly cached and restored?
9. Does visibility sync work with LayerCollections?
10. Are render handlers properly installed and removed?

## Recent Development Activity

### Latest Updates (December 2024)

#### Mass Exporter Improvements
- **Clean up mass exporter UI and improve descriptions** (commit 2483b12)
  - Enhanced user interface clarity and better description text
  - Improved user guidance throughout the export workflow

- **Add 'Apply Only Visible' modifier feature to mass exporter v12** (commit 80264e5)
  - New feature allowing selective application of only visible modifiers during export
  - Provides greater control over modifier stack during export operations
  - Enhances export workflow flexibility

#### New Addon: Compositor Render Sets
- **Added Compositor Render Sets** (commit 8bf8028)
  - Complete compositor toolset for managing multiple render configurations
  - Automated File Output node management for batch rendering
  - 1,719 lines of Python implementation
  - Comprehensive 577-line README with full documentation
  - Demonstrates advanced render handler and node state management patterns

#### Attribute Functions & Geometry Nodes Updates
- **Major updates to GN_AttributeFunctions_4.5.blend** (commit 8bf8028)
  - Removed legacy Instancer system (replaced by CollectionInstancer)
  - Enhanced attribute manipulation capabilities
  - File expanded from ~3.1MB to ~3.5MB with new features

#### Collection Instancer Enhancements
- **Collection Instancer improvements** (commit c11d959)
  - New grid instancing capability
  - Replaces older Instancer geometry node system
  - Better integration with collection-based workflows

#### Extrude Selection Updates
- **Post-merge functionality** (commit c11d959)
  - Added ability to merge vertices after extrusion
  - Streamlines extrusion workflows

#### Mirror Groupable Refinements
- **Ongoing Mirror Groupable improvements** (commits 3f4ecd7, 56a6fa6, 2fec3a0)
  - Multiple bug fixes and stability improvements
  - Enhanced mirror operations with better grouping system integration

#### Tileable Noise/Voronoi
- **Added tileable procedural textures** (commit 2fec3a0)
  - Updated SHG_TileableNoise.blend with new patterns
  - Voronoi noise support for seamless tiling
  - File expanded from ~586KB to ~890KB

### Earlier Recent Work (Last 2 Months)

#### New Geometry Node Tools
- **Grow Selection** (commit 9821f57) - Topology-based selection expansion
- **Mesh from Image** (commit 9821f57) - First pass at image-to-mesh conversion
- **Smart Collapse** (commit 6295f07) - Intelligent merge/collapse hybrid
- **Custom Solidify** (commit b357d8c) - Alternative solidify implementation

#### Attribute Function Improvements
- **Set Attributes** (commit 3c96e73) - Added value inversion features
- **Attribute node cleanup** (commit 3e56e56) - Cleaner node organization
- **Smart Crease fixes** (commits ae13f4d, a4e4d2e)
  - Fixed crease 1/0 toggle functionality
  - Moved toggle to Alt modifier key
  - When no face boundary exists, creases all edges
  - Preferences now properly handle increment and HUD size settings

#### Repository Maintenance
- **Removed .blend1 autosave files** (commit 419424f)
  - Cleaned up ~10 autosave files from git tracking
  - Reduced repository clutter and size
  - .blend1 files remain in .gitignore

#### Documentation Updates
- Multiple README improvements across various tools
- Better organization and clarity in project documentation

## Additional Resources

For comprehensive Blender addon development guidance, see:
- **docs/blender-tooling-specialist-agent.md** - Complete agent specification with architectural patterns, workflows, and best practices
