# Addon architecture and release

WMH split pitfalls and the zip/release habit. Standard: skill `wmh-tool-architecture`, layout: `Blender/Addons/_TOOLING_STRUCTURE.md`.

> Migrated verbatim from Claude auto-memory on 2026-09-22. Dates and version numbers are from when each note was written — trust the code when they disagree.

- [WMH core/blender split gotchas](#feedback_wmh_split_gotchas)
- [Always build a versioned zip after an addon change](#feedback_blender_addon_always_zip)

<a id="feedback_wmh_split_gotchas"></a>

## WMH core/blender split gotchas

*Gotchas when refactoring an addon to the WMH core/blender split, learned on Compositor Render Sets v2.0.0 (first adopted tool)*

Compositor Render Sets v2.0.0 (2026-07-02) is the FIRST tool refactored to the WMH core/blender split — use it as the reference implementation. Gotchas hit:

**Why:** these break silently or only outside Blender, so they're easy to ship broken.

**How to apply:**
1. `source/__init__.py` must guard the bpy-boundary import (`try: import bpy` → only then `from .blender import register, unregister`), otherwise pytest imports the package `__init__` while collecting `source/tests/` and dies on `import bpy`.
2. Blender 4.x `CompositorNodeOutputFile.file_slots.remove()` takes the input SOCKET (`node.inputs[0]`), NOT the slot item — passing the slot raises TypeError. Blender 5's `file_output_items.remove(item)` takes the item.
3. Blender 5 File Output has a per-node `file_name` field — any cache/restore of node state must round-trip it or user filenames get wiped.
4. `Scene.use_nodes` is deprecated, removal expected in Blender 6.0 — always `hasattr` guard; on a fresh 5.0 scene the compositing node group may not exist (create via `bpy.data.node_groups.new(..., 'CompositorNodeTree')` + assign `scene.compositing_node_group`).
5. Best verification: headless smoke test on BOTH 4.5 and 5.0 (`blender --background --factory-startup --python smoke.py`) doing a real 32×32 Workbench render through the addon — it caught #2 and proved #3. See [Headless Blender and automation](headless-and-automation.md#feedback_blender_version_and_headless), related root-layer-collection rule in [Export pipeline](export-pipeline.md#feedback_blender_master_layercollection_exclude).

<a id="feedback_blender_addon_always_zip"></a>

## Always build a versioned zip after an addon change

*After any code change to a Blender addon in this repo, always build a versioned installable zip without waiting to be asked*

> **Superseded details (2026-09-22):** zips now go in the tool's own `distribution/`
> (previous zip to `distribution/archive/`), per `Blender/Addons/_TOOLING_STRUCTURE.md` —
> not beside the addon folder. Archive layout is **unresolved**: `_TOOLING_STRUCTURE.md` says
> files at archive root, this note says wrap in the addon folder. Current builds split:
> extensions with `blender_manifest.toml` (TileUVProjector 1.8.0, LibraryPublisher 1.3.0)
> have files at root; legacy `bl_info` addons (Smart Crease, SyncedModifiers, …) are
> folder-wrapped. Match the tool's previous zip until this is settled.

After any change to a Blender addon under `Blender/Addons/<AddonName>/`, always produce a versioned installable zip in `Blender/Addons/` (sibling to the addon folder), named `<AddonBase>_v<VERSION>.zip` (e.g. `MassExporter_v13.3.3.zip`).

**Why:** The zips are the user's drag-and-drop delivery artifact — they install/test the addon by dropping the zip into Blender. Leaving them to ask for the zip every time is friction; they have made this an explicit standing instruction ("take note to make sure to do that always"). The CLAUDE.md already documents the zip pattern for Mass Exporter — treat it as the norm for all addons in this folder.

**How to apply:**
- Bump `VERSION` in the addon's `__init__.py` AND the matching `version = "..."` in `blender_manifest.toml` in the same edit pass.
- Archive layout: **wrap the addon files in the addon's folder at the zip root** (e.g. `TileUVProjector/__init__.py`, `TileUVProjector/README.md`). Blender's drag-and-drop installer expects the folder structure so it can install the package as `addons/<AddonName>/`. Putting files at the bare zip root is wrong and the user corrected this. Mirror the internal structure of the addon folder exactly, including the outer dir.
- Exception: a couple of legacy zips in this folder (e.g. older MassExporter builds) flattened files to the root. Do not copy that pattern — the user has standardized on folder-at-root going forward.
- Place the zip alongside prior versions in `Blender/Addons/` (not inside the addon folder).
- Don't delete older version zips — the user keeps the history.
- Build this even for small fixes; the user treats each committed change as a releasable build.
