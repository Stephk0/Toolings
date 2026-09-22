# Geonode asset files

What a shipped geonode .blend must contain, and its icon.

> Migrated verbatim from Claude auto-memory on 2026-09-22. Dates and version numbers are from when each note was written — trust the code when they disagree.

- [Every geonode .blend ships an object with the modifier](#feedback_geonode_file_needs_object)
- [Delete the factory Cube from headless demo scenes](#feedback_geonode_demo_scene_hygiene)
- [Asset Browser icon pipeline](#project_geonode_icon_pipeline)

<a id="feedback_geonode_file_needs_object"></a>

## Every geonode .blend ships an object with the modifier

*Every standalone geonode .blend must ship with a scene object that has the GN modifier attached — never asset-only files*

When creating a standalone Geometry Nodes `.blend` (one GN group per file under `Blender/Geonodes/`), **ALWAYS place an object in the scene and attach the GN modifier to it** (a real object whose `modifiers.new('NODES').node_group = ng`), and save a **FULL mainfile** (`bpy.ops.wm.save_as_mainfile(filepath=...)`), NOT an asset-only `bpy.data.libraries.write({ng}, fake_user=True)` partial file.

**Why (user instruction, 2026-06-03):** "Always place an object in the scene and attach the geonode modifier to it so that there's at least one object in the scene using the modifier otherwise the user will have a hard time accessing the modifier geometry node." An asset-only file has the group as a fake-user ORPHAN with no object using it — opening it shows an empty scene, the group isn't easy to reach/edit, and the workflow breaks. This exact mistake (using `libraries.write` for `GN_RandomizePosition.blend`) led to the user's live session ending up as a Plane with an EMPTY Geometry Nodes modifier and the asset appearing "missing" — a data-loss scare that needed a File→Revert.

**How to apply (headless, non-disruptive — don't build in the user's live session):**
1. `blender --background --factory-startup <new>.blend? no` → launch with `--factory-startup`, build the group, then:
2. Create a fitting primitive (subdivided cube/cylinder/grid via bmesh) as the demo object; `obj.modifiers.new("GN","NODES").node_group = ng`; select + make active.
3. Asset-mark per [ST3E geonode modifier — build recipe, roster, publish checklist](asset-checklist.md) (asset_mark, catalog `f9ab2fa9-3a4e-491a-abaa-558cd5c029d0`, tag `ST3E`, `is_modifier=True`).
4. Lay out nodes with the `tidy_layout` algo from [Geonode layout](layout.md#feedback_gn_node_layout_spacing); frame+label everything.
5. `bpy.ops.wm.save_as_mainfile(filepath=path)`; flush stdout + `os._exit(0)`.
6. To build MANY files in one headless launch, loop: `bpy.ops.wm.read_factory_settings(use_empty=True)` between each to reset to a clean empty file.

Related: [ST3E geonode modifier — build recipe, roster, publish checklist](asset-checklist.md), [Headless Blender and automation](../headless-and-automation.md#feedback_blender_version_and_headless), [Headless Blender and automation](../headless-and-automation.md#reference_blender_mcp).

<a id="feedback_geonode_demo_scene_hygiene"></a>

## Delete the factory Cube from headless demo scenes

*Headless geonode builds ship the factory-startup Cube in the demo scene unless you delete it — only a render catches it*

A geonode build script run as `blender --background --factory-startup --python build.py`
starts in the **default startup scene**, so `save_as_mainfile` ships the factory `Cube`
(plus Light/Camera) alongside `GN_Demo`. Every numeric check still passes — the Cube is a
separate object with no modifier — so it is invisible to the verify matrix. It only showed
up as a fat 2 m square sitting in the middle of the demo grid in a **top-down Cycles render**.

**Why:** the demo file is what the user opens to see the tool working; a stray unrelated cube
reads as part of the tool's output.

**How to apply:**
- In every build script, before creating the demo object:
  `for o in list(bpy.data.objects):`
  `    if o.type == 'MESH': bpy.data.objects.remove(o, do_unlink=True)`
- Always do one **top-down render of the demo file** as the last verification step
  (`sc.render.engine='CYCLES'; cycles.samples=24; ortho camera + sun`, then Read the PNG).
  Cheap, and it catches what field math checks structurally cannot — same lesson as the
  GN_Mosaic/GN_TileableMeshNoise seam renders in [ST3E geonode modifier — build recipe, roster, publish checklist](asset-checklist.md).
- Known offender still in the library: **`GN_DeleteStrayGeometry.blend`** ships
  `Cube.001`/`Light.001`/`Camera.001`. `GN_Wave` / `GN_NormalTransfer` are clean references.
- Scene-only fixes to an already-tidied/published file go in a small separate script that
  asserts node count/positions AND evaluated vert/face counts are unchanged before saving —
  never re-run the builder (it would discard the tidy layout and any user test objects).

Related: [Geonode asset files](asset-files.md#feedback_geonode_file_needs_object), [Headless Blender and automation](../headless-and-automation.md#feedback_blender_version_and_headless).

<a id="project_geonode_icon_pipeline"></a>

## Asset Browser icon pipeline

*ST3E geonode Asset-Browser icons — the framed-Suzanne render pipeline in Blender/Geonodes/_icons, its effect-check gate, and the traps that cost time*

Pointer memory. The ST3E geonode modifier icons are generated by a two-stage
headless pipeline in `Blender/Geonodes/_icons/`. **The real documentation is in
that folder** — `ICONS.md` is the contract (every constant, the recipe format,
the workflow) and `GOTCHAS.md` records the findings. Serena memory
`geonode_icon_pipeline` mirrors this pointer inside the repo.

Built 2026-09-20/21. 13 recipes done and embedded, 39 modifiers still to do —
run `coverage.py` for the live list rather than trusting any number written
down.

**Shape:** stage A renders `out/<GROUP>.png` from a throwaway scene (node
groups appended as copies, library never touched); stage B embeds them into
each `.blend` via `ed.lib_id_load_custom_preview` under `temp_override(id=ng)`
and is the only step that saves. Always cold-verify after embedding.

**The load-bearing idea:** each recipe declares `expect=` and the build diffs
the evaluated mesh before/after the modifier, writing **no PNG** if nothing
changed. Most of these modifiers do nothing without specific setup, so without
that gate the library fills with identical Suzannes. But green only proves
something changed, not that the icon reads — look at every PNG.

**Two traps:** headless EEVEE segfaults in `nvoglv64` mid-batch and cannot
render a lightless scene at all in `--background`, so both stages use Cycles
CPU. And the user edits the source `.blend`s between sessions — re-probe a
group's interface before writing or re-running a recipe rather than trusting
recorded socket names.

Related: [ST3E geonode modifier — build recipe, roster, publish checklist](asset-checklist.md),
[Headless Blender and automation](../headless-and-automation.md#feedback_blender_version_and_headless), [Headless Blender and automation](../headless-and-automation.md#reference_blender_mcp),
[Geonode sockets, interfaces and menus](sockets-and-menus.md#feedback_gn_menu_socket_default), [Headless Blender and automation](../headless-and-automation.md#feedback_blender_ui_screenshot_automation).
