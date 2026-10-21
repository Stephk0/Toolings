# Addon architecture and release

WMH split pitfalls and release habits. Standard: skill `wmh-tool-architecture`; layout:
`Blender/Addons/_TOOLING_STRUCTURE.md`; release CLI: `Blender/Addons/_release/README.md`.

- [WMH core/blender split gotchas](#feedback_wmh_split_gotchas)
- [Every addon change ships a versioned zip](#feedback_blender_addon_always_zip)

<a id="feedback_wmh_split_gotchas"></a>

## WMH core/blender split gotchas

*Traps hit splitting Compositor Render Sets v2.0.0 (the reference implementation) into `core/` + `blender/`.*

1. **Guard the bpy import in `source/__init__.py`** (`try: import bpy` → only then
   `from .blender import register, unregister`), or a `conftest.py` that stubs the package.
   Otherwise pytest imports the package while collecting `source/tests/` and dies on
   `import bpy`.
2. Blender 4.x `CompositorNodeOutputFile.file_slots.remove()` takes the input **socket**
   (`node.inputs[0]`), not the slot item (TypeError). Blender 5's
   `file_output_items.remove(item)` takes the item.
3. Blender 5 File Output has a per-node `file_name`; any cache/restore of node state must
   round-trip it or user filenames are wiped.
4. `Scene.use_nodes` is deprecated (removal expected in 6.0): `hasattr`-guard it. A fresh 5.0
   scene may have no compositing node group: create a `CompositorNodeTree` and assign
   `scene.compositing_node_group`.

**Why:** these break silently or only outside Blender.

**How to apply:** smoke-test headless on **both 4.5 and 5.0**
(`blender --background --factory-startup --python smoke.py`) with a real operation through
the addon (here a 32×32 Workbench render). That run caught #2 and proved #3.

<a id="feedback_blender_addon_always_zip"></a>

## Every addon change ships a versioned zip

*The user installs by dragging the zip into Blender; build it after every change without being asked.*

**How to apply:** `python Blender/Addons/_release/release.py release <Tool> <part>` (or
`build <Tool> [--force]` for an unreleased version). It bumps `bl_info`/`VERSION`, the
manifest and the doc version lines, builds into the tool's `distribution/`, moves the old
zip to `distribution/archive/` and verifies the result. Each tool's `release.toml` records
its zip layout (files at root vs. wrapped in the addon folder); never change a tool's layout
on the side. Old zips are never deleted. Write the CHANGELOG entry yourself; new rows in the
repo-level tool lists are manual too (rule in the repo `CLAUDE.md`).
