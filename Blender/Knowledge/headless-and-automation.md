# Headless Blender and automation

Driving Blender from scripts: live MCP, --background runs, rendering, screenshots.

> Migrated verbatim from Claude auto-memory on 2026-09-22. Dates and version numbers are from when each note was written — trust the code when they disagree.

- [Blender MCP — verify live instead of reasoning](#reference_blender_mcp)
- [Target Blender 5.0; editing .blend files headlessly](#feedback_blender_version_and_headless)
- [Headless render, compositor and text on Blender 5](#feedback_blender_headless_render_and_text)
- [One .blend per process when diffing evaluated geometry](#feedback_blender_multifile_eval_contamination)
- [Capturing addon UI screenshots via MCP](#feedback_blender_ui_screenshot_automation)

<a id="reference_blender_mcp"></a>

## Blender MCP — verify live instead of reasoning

*Blender MCP server is connected — can execute Python in Blender directly to test addons, inspect scene state, and verify behavior*

Blender MCP server (`blender-mcp` via `uvx`) is connected on localhost:9876. Tools available via ToolSearch under `mcp__blender__*` (deferred — load with ToolSearch before first call).

**Why:** User explicitly confirmed (2026-04-22) that Blender MCP should be actively used for testing, not just code generation. Avoids the "wrote code, never verified" failure mode common in Blender addon work where API quirks bite silently.

**How to apply:**
- For Blender addon/geonode work, prefer *verifying* behavior via `mcp__blender__execute_blender_code` over reasoning-only claims.
- Useful tools: `execute_blender_code` (run arbitrary bpy), `get_scene_info`, `get_object_info`, `get_viewport_screenshot` for visual verification.
- Load schemas with `ToolSearch query "select:mcp__blender__<name>"` — they are deferred by default.
- The scene state is the user's live Blender — don't delete/modify objects gratuitously; clean up test artifacts when done.

<a id="feedback_blender_version_and_headless"></a>

## Target Blender 5.0; editing .blend files headlessly

*Always target Blender 5.0 (not 4.5); how to edit .blend files headlessly when the live MCP isn't connected*

The user is on **Blender 5.0** — use `C:\Program Files\Blender Foundation\Blender 5.0\blender.exe`, not 4.3/4.4/4.5, even for files named `*_4.5.blend` (those are just legacy names; saving in 5.0 upgrades them in place, which is fine).

**Why:** user explicitly said "stop using blender 4.5, we are on blender 5" (2026-06-02).

**How to apply — editing a `.blend` when the live Blender MCP is NOT connected** (`execute_blender_code` returns "Could not connect to Blender"): drive Blender headlessly:
`& "C:\Program Files\Blender Foundation\Blender 5.0\blender.exe" --background --factory-startup "<file.blend>" --python "<script.py>"`
- `--factory-startup` is important for `GN_AttributeFunctions_4.5.blend`: it carries a custom addon (Figaro / modern_primitive) whose GPU draw handlers crash with EXCEPTION_ACCESS_VIOLATION in `--background`. Factory startup skips user addons; node-group data is unaffected.
- In the script, flush stdout (`print(...); sys.stdout.flush()`) and end with `os._exit(0)` after `bpy.ops.wm.save_mainfile()` to skip any crashing addon teardown and not lose buffered output.
- Prefer the live MCP ([Headless Blender and automation](headless-and-automation.md#reference_blender_mcp)) when Blender is actually open; fall back to headless only when it isn't.
- Clean up the throwaway `_*.py` scripts afterward (per `Blender/Addons/_TOOLING_STRUCTURE.md` junk rules).

**Blender 5 GN API change (probe before assuming 4.x):** the **Merge by Distance** node (`GeometryNodeMergeByDistance`) no longer has a `.mode` python property — `Mode` is now an INPUT **socket** (a NodeSocketMenu, items "All"/"Connected", default "All"). Node inputs are `Geometry, Selection, Mode, Distance`. So wrapping it just means exposing all 4 sockets to the group; no Menu-Switch-between-two-nodes trick needed. When unsure of a node's 5.0 surface, probe `n.bl_rna.properties` + `n.inputs`/`n.outputs` in a throwaway group first.

Related: [Geonode sockets, interfaces and menus](geonodes/sockets-and-menus.md#feedback_gn_menu_socket_default), [ST3E geonode modifier — build recipe, roster, publish checklist](geonodes/asset-checklist.md).

<a id="feedback_blender_headless_render_and_text"></a>

## Headless render, compositor and text on Blender 5

*Headless Blender 5 rendering, compositing and text — EEVEE is unreliable in background, the compositor is a node group, and variable fonts break glyph fills*

Findings from building the geonode icon pipeline
([Geonode asset files](geonodes/asset-files.md#project_geonode_icon_pipeline)). All verified on Blender 5.0, Windows,
`--background --factory-startup`.

**Render headlessly with Cycles CPU, not EEVEE.** Headless EEVEE goes through
the GPU driver and segfaults in `nvoglv64` partway through a batch — including
on probes that passed unchanged minutes earlier. It also **cannot render a
scene with no lights at all** in background mode (a pure-emission flat scene
crashes outright). Cycles CPU is driver-independent and a 256px render costs
well under a second. Stacked Transparent-BSDF overlays need samples: at 16 the
gradients dither, 512 is clean and still fast at that size.

**Blender 5 compositor is a node group.** `Scene.node_tree` and the
`Composite` node are gone: build a `CompositorNodeTree`, terminate with
`NodeGroupOutput`, assign to `scene.compositing_node_group`. `AlphaOver` inputs
are `Background` / `Foreground` / `Factor` / `Straight Alpha`. To layer
something *above* a composited overlay, it needs its own **view layer** —
chain `layerA -> over image -> over layerB` in one render. Set `exclude` only
on child layer collections, never the master (see
[Export pipeline](export-pipeline.md#feedback_blender_master_layercollection_exclude)).

**Asset previews are writable and persist.**
`bpy.ops.ed.lib_id_load_custom_preview(filepath=…)` under
`bpy.context.temp_override(id=<id>)` stores 256x256 with
`is_image_custom=True` and survives save/reload. `preview_ensure()` +
`image_pixels_float` also works.

**Variable fonts can render wrong glyphs.** Blender fills the capital **A** of
Familjen Grotesk's variable build (`[wght].ttf`, what Google Fonts ships) as a
solid triangle — leg aperture closed, counter collapsed. Reproducible at 400px,
so not a size artefact; every other glyph is fine and the **static** builds are
correct. It is the font-to-curve conversion choking on the variable outline.
Prefer a static instance and vendor it next to the scripts.

**Size text by a reference capital, not the string's bbox.** A bbox includes
whatever ascenders/descenders the string happens to contain, so "Spherify"
comes out smaller than "Subdivide". Measure `H` at em size 1.0 and derive from
that ratio.

**A diagonal drop shadow offset by `d` on both axes is `d*sqrt(2)` away** —
divide by sqrt(2) if the number is meant to be the real distance. And a drop
shadow alone will not carry white text over a white subject; it needs a halo of
offset copies.

**`libraries.load(..., assets_only=True)` mutates the list you pass** — after
the `with` block the names have been replaced in place by datablocks. Copy it
first.

**Menu sockets cannot be overridden on a modifier from Python.** The integer a
modifier stores for a `NodeSocketMenu` is a value id not exposed through the
RNA (`enum_items` gives only name/description). Write the item **name** onto
the node group's interface default and delete the modifier override instead —
only safe on a throwaway copy of the group. Blender then logs
`WARNING … Missing property for input socket "X"`, which is expected. See also
[Geonode sockets, interfaces and menus](geonodes/sockets-and-menus.md#feedback_gn_menu_socket_default).

<a id="feedback_blender_multifile_eval_contamination"></a>

## One .blend per process when diffing evaluated geometry

*Opening several .blend files in ONE background Blender process corrupts evaluated-mesh comparisons — run one process per file before trusting a geometry diff*

A verification harness that loops `wm.open_mainfile` over many .blend files in a
single `blender --background` process produces **false geometry differences**.
GN_PointsToSpheres reported two provably-identical modifier states as different —
reproducibly, and surviving a "read twice until two samples agree" stabiliser — but
only when another .blend had been opened earlier in the same process. The diff was
its whole evaluated `UVMap` layer (0 vs 1), i.e. realized-instance data, while
positions, counts, normals and material indices all matched.

**Why:** something in the evaluated/instance cache is not reset by `open_mainfile`.
Same test, one process per file: 36/36 pass.

**How to apply:** for any check that compares *evaluated* geometry across files
(geometry-unchanged gates, truth tables, A/B asset diffs), give each file its own
Blender process — pass the file as an argument and loop in the shell. A single-process
sweep is fine as a fast pre-filter, but **never conclude an asset is broken from it**;
re-run that one file alone first. Cost me a long detour on 2026-09-21 chasing a
"failing" XOR node that was provably a single boolean node with one output link.
Related: [Headless Blender and automation](headless-and-automation.md#feedback_blender_version_and_headless),
[ST3E geonode modifier — build recipe, roster, publish checklist](geonodes/asset-checklist.md).

<a id="feedback_blender_ui_screenshot_automation"></a>

## Capturing addon UI screenshots via MCP

*Recipes and pitfalls for capturing Blender addon UI screenshots headlessly via MCP (sidebar tabs, wide panel popups, splash, region limits, OS-input dangers)*

Recipes for automating Blender UI screenshots through `mcp__blender__execute_blender_code` (proven on Blender 5.0, MassExporter tutorial 2026-07-13):

- **Screenshot an area:** `bpy.ops.screen.screenshot_area(filepath=...)` under `temp_override(window, area, region)`. Captures the area incl. its sidebar even if the Blender window is occluded. Crop with numpy on `bpy.data.images` pixels (row 0 = bottom).
- **Set the N-panel tab:** `region.active_panel_category = 'Tab Name'` works ONLY inside `temp_override(window=win, area=area, region=ui_region)` and after at least one redraw (`bpy.ops.wm.redraw_timer(type='DRAW_WIN_SWAP')`); otherwise it raises read-only.
- **Sidebar width is NOT scriptable.** `region.width` is read-only and scales with ui_scale (content units stay constant → truncation identical at any scale). For readable wide shots use `bpy.ops.wm.call_panel(name=..., keep_open=True)` after re-registering the panel class with `bl_ui_units_x = 36` (must unregister/register — the attr is read at registration).
- **Popup gotchas:** popups freeze their drawn content (no live update — re-open per state); re-registering a panel moves it to the END of its parent's subpanel order (restore by disabling/enabling the addon); reloading the file (`wm.open_mainfile`) closes all popups.
- **Splash screen:** cursor_warp/fullscreen toggles do NOT dismiss it; loading a .blend does. Save scene to scratchpad and reopen.
- **NEVER inject OS-level clicks (SetCursorPos/mouse_event)** to drag Blender UI: SetForegroundWindow is blocked from background processes, multiple Blender instances may be open (user's unsaved work!), and clicks land on whatever window is topmost. Verify with WindowFromPoint→pid before any synthetic click, or better, stay in-process.
- `Get-Process blender` matches ALL Blender instances — identify the MCP-connected one by `os.getpid()` inside Blender.

**Why:** rediscovering these costs hours; the OS-click pitfall risks the user's unsaved scenes.
**How to apply:** for any addon-documentation or UI-verification task needing screenshots, follow the in-process recipes above; see [Headless Blender and automation](headless-and-automation.md#reference_blender_mcp).
