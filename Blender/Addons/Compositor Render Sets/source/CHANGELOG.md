# Compositor Render Sets — changelog

User docs: [README](../README.md).

## Version 2.0.0 (Current - 2026-07-02) — WMH Architecture + Bug Fixes

**Architecture refactor** — the 2,800-line single file is now a proper package
following the suite's WMH standard: bpy-free `core/` (unit-tested with pytest,
27 tests), `blender/` bpy boundary, thin `__init__.py`, extension manifest,
dev-install script, and a versioned distribution zip. Verified end-to-end with
headless renders on Blender 4.5 (prefix-replacement path) and 5.0
(`file_name`-field path).

**Bug fixes:**
- **Abort Render started a render instead of aborting one** — it invoked
  `bpy.ops.render.render`; it is now a pure recovery action (restores the File
  Output node from the cached state and clears stuck flags)
- **Blender 5 `file_name` field wiped after every render** — the field is now
  cached and restored with the rest of the node state
- **State restoration now guaranteed via try/finally** — an exception
  mid-render no longer leaves the node reconfigured, visibility mangled, and
  `is_rendering` stuck on
- **Create Node Setup was broken on Blender 4.x** — `file_slots.remove()`
  was called with the slot instead of the input socket (TypeError)
- **Create Node Setup on a fresh Blender 5 scene** — now creates the
  compositing node group when none exists yet
- **Root (master) layer collection is never touched anymore** — hiding it and
  syncing its state onto `hide_render` could blank the entire render
- **Modifier/object sync now includes nested sub-collections**
  (`all_objects` instead of direct `objects`)
- Render mode is a proper enum (the phantom `'selected'` mode could crash
  batch setup with an IndexError)
- Panel log is capped at 200 lines instead of growing unboundedly in the
  .blend; `Scene.use_nodes` access is guarded for its removal in Blender 6.0

**Improvements:**
- Console debug spam is now opt-in via the new **Debug Console Output**
  setting (Settings section)
- Layer-collection lookups use a prebuilt map instead of repeated recursive
  searches; per-set mute-state snapshots no longer double-mute
- Blender min version raised to 4.2 (extension system)

## Version 1.7.1 (2025-12-09)
- **Blender 5.0 Compatibility:** Added support for Blender 5.0's new File Output node `filename` field
  - Automatic version detection: uses `filename` field in Blender 5.0+, prefix replacement in Blender 4.x
  - File output nodes properly reset after each render set
  - Backward compatible with Blender 4.x
- **Performance Optimization:** Modifier sync filtering
  - New option: "Only Sync Modifiers in Render Set" (enabled by default)
  - Only syncs modifiers on objects in render set collections (not all scene objects)
  - Significantly reduces debug output and improves render performance
  - UI: Filter checkbox appears as sub-option when modifier sync is enabled
- **Bug Fix:** Fixed syntax error preventing addon installation (property definition at line 316)

## Version 1.9.0
- **Bug Fix:** Override Output Node Settings now correctly uses the specified File Output node
  - Per-set override nodes are now properly found and configured
  - Override node name and prefix are correctly applied during rendering
  - Mute Unused File Output Nodes now correctly identifies and unmutes override nodes
  - All override nodes are properly restored to original state after rendering
  - Fixed slot path handling to prioritize the correct 'path' attribute
  - Override node states are now pre-cached before rendering to preserve original values
- Fixed issue where override settings were ignored and global settings were always used
- Fixed potential "file_nametex_" filename corruption by improving slot path getter/setter priority

## Version 1.8.0
- **UI Improvement:** All main sections are now collapsible/foldable
  - Render Set Setup (expanded by default)
  - Constant Render Set Collections (expanded by default)
  - Render (expanded by default)
  - Settings (collapsed by default)
  - Log (collapsed by default)
- Space-saving UI for cleaner workspace organization

## Version 1.7.0
- Added batch collection management
- Create Node Setup feature
- Mute Unused File Output Nodes feature

## Version 1.0.0
- Initial release
- Render set management (add, remove, tabs)
- Collection assignment per set
- Visibility controls (show/hide, solo)
- Three render modes (current, selected, all)
- Automatic File Output node configuration
- Prefix replacement system
- Viewport/render visibility sync
- Logging system
- Settings panel
