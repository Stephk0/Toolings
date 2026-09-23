# Compositor Render Sets — developer notes

Implementation and maintenance notes. User docs: [README](../README.md).

## Dev deploy
Run `install_to_blender.ps1` at the tool root — it copies `source/` into the
highest installed Blender's `extensions\user_default\` folder. Restart Blender.

## Folder layout

```
Compositor Render Sets/
├── README.md               # this file
├── install_to_blender.ps1  # one-click dev deploy
├── source/                 # addon code (WMH architecture)
│   ├── __init__.py         # thin: bl_info + register wiring
│   ├── blender_manifest.toml
│   ├── core/               # pure Python, bpy-free, unit-tested
│   │   ├── naming.py       # prefix/slot/output-path computations
│   │   └── logbuf.py       # capped log buffer helpers
│   ├── blender/            # bpy boundary
│   │   ├── compat.py       # Blender 4.x / 5.0+ compositor API layer
│   │   ├── visibility.py   # collection/modifier/object visibility sync
│   │   ├── node_state.py   # File Output node cache/configure/restore
│   │   ├── properties.py   # PropertyGroups
│   │   ├── operators.py    # all operators
│   │   └── panels.py       # UI lists + panels
│   └── tests/              # pytest over core/ (no bpy needed)
└── distribution/           # current installable zip (+ archive/)
```

Run the unit tests without Blender: `python -m pytest source/tests`

## ⚙️ Technical Details

### Compositor Integration

The addon manipulates the **File Output** node in the compositor:

1. **Discovery:**
   - Searches scene.node_tree for a node of type `OUTPUT_FILE`
   - Matches by the name specified in settings

2. **State Caching:**
   - Before rendering, caches:
     - Original `base_path`
     - Original file slot names/paths

3. **Configuration:**
   - For each render set:
     - Sets `base_path` to the render set's output path
     - Renames file slots that start with the prefix
     - Replaces prefix with render set name

4. **Restoration:**
   - After all renders complete:
     - Restores `base_path` to original
     - Restores all file slot names to original

### Visibility Management

**Viewport Visibility:**
- Controlled via `collection.hide_viewport`
- Modified by Show/Hide and Solo operators
- Can be synced to render visibility

**Render Visibility:**
- Controlled via `collection.hide_render`
- Optionally synced from viewport visibility (if setting enabled)
- Original states are cached and restored

**Solo Mode:**
- Caches all collection visibility states as JSON
- Hides all collections, shows only the set's collections
- Toggling again restores cached states

## 🛣️ Future Enhancements

Potential features for future versions:

- [ ] Support for multiple File Output nodes
- [ ] Camera switching per render set
- [ ] Render settings override per set (samples, resolution)
- [ ] Animation/frame range rendering
- [ ] Export render set configurations to JSON
- [ ] Import/export presets
- [ ] Render queue with priority system
