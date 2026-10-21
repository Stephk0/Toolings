# Headless Blender and automation

Driving Blender from scripts: live MCP, --background runs, rendering, screenshots.

- [Blender MCP — verify live instead of reasoning](#reference_blender_mcp)
- [Editing .blend files headlessly](#feedback_blender_version_and_headless)
- [Headless render and compositor on Blender 5](#feedback_blender_headless_render_and_text)
- [One .blend per process when diffing evaluated geometry](#feedback_blender_multifile_eval_contamination)
- [Capturing addon UI screenshots via MCP](#feedback_blender_ui_screenshot_automation)
- [Real-UI tests without a desktop: Xvfb + event_simulate](#finding_xvfb_event_simulate)
- [Real-UI demo capture on Windows: screenshots, menus, typing](#finding_windows_real_ui_capture)
- [`pip install bpy` gives a headless Blender 5.0 anywhere](#finding_pypi_bpy)
- [Background transform ops ignore the Pivot Point without a 3D View](#finding_background_transform_pivot)

<a id="reference_blender_mcp"></a>

## Blender MCP — verify live instead of reasoning

*Run addon and geonode checks in the user's live Blender through `mcp__blender__*` instead of reasoning about API behaviour.*

Tools are deferred: load them with ToolSearch first. Start with `get_addon_status` (Blender
version, whether the bridge addon is current) and `get_scene_info`; run code with
`execute_blender_code`, look with `look`. If `get_addon_status` reports the bridge addon as
outdated or not connected, tell the user (`uvx mcp-for-blender install-addon`) and fall back
to headless runs.

**How to apply:** it is the user's live scene with possibly unsaved work: create test objects
in a throwaway collection and remove them afterwards; never delete or reset their data.

<a id="feedback_blender_version_and_headless"></a>

## Editing .blend files headlessly

*Without a live MCP connection, drive Blender 5.0 with `--background --factory-startup`, one file per process.*

```powershell
& "C:\Program Files\Blender Foundation\Blender 5.0\blender.exe" --background --factory-startup "<file.blend>" --python "<script.py>"
```

- Target 5.0; keep 4.5 working when the tool supports it (run the same check on both).
  `*_4.5.blend` names are legacy; saving in 5.0 upgrades them, which is fine.
- `--factory-startup` matters: `GN_AttributeFunctions_4.5.blend` carries an addon whose GPU
  draw handlers crash `--background` with EXCEPTION_ACCESS_VIOLATION.
- End scripts with `sys.stdout.flush()` then `os._exit(0)` (after `save_mainfile()`): skips
  crashing addon teardown, and `os._exit` otherwise drops buffered (piped) output.
- Delete throwaway `_*.py` scripts afterwards (`_TOOLING_STRUCTURE.md` junk rules).

<a id="feedback_blender_headless_render_and_text"></a>

## Headless render and compositor on Blender 5

*In `--background`, render with Cycles CPU, build the compositor as a node group, and expect two API surprises with asset loading and Menu sockets.*

Verified on 5.0, Windows, `--background --factory-startup` (geonode icon pipeline). Icon- and
text-specific traps (variable fonts, sizing by a capital, shadows/halos) live in
`Blender/Geonodes/_icons/GOTCHAS.md`.

- **Cycles CPU, not EEVEE.** Headless EEVEE goes through the GPU driver and segfaults
  (`nvoglv64`) partway through batches, and crashes on a scene with no lights. Cycles CPU at
  256 px renders in under a second; stacked Transparent BSDFs need ~512 samples.
- **The compositor is a node group.** `Scene.node_tree` and `Composite` are gone: build a
  `CompositorNodeTree` ending in `NodeGroupOutput`, assign `scene.compositing_node_group`.
  `AlphaOver` inputs: `Background`, `Foreground`, `Factor`, `Straight Alpha`. To layer above a
  composited overlay, use a second view layer. Never set `exclude` on the master layer
  collection ([Export pipeline](export-pipeline.md#feedback_blender_master_layercollection_exclude)).
- **Asset previews are writable:** `bpy.ops.ed.lib_id_load_custom_preview(filepath=…)` under
  `temp_override(id=<id>)` stores 256×256 and survives save/reload.
- **`libraries.load(..., assets_only=True)` mutates the name list you pass** into
  datablocks. Pass a copy.
- **Menu sockets can't be overridden on a modifier from Python.** The stored integer is a
  value id the RNA doesn't expose. On a throwaway copy of the group, write the item name onto
  the interface default and delete the modifier override (Blender then logs an expected
  `Missing property for input socket` warning). See
  [Geonode sockets](geonodes/sockets-and-menus.md#feedback_gn_menu_socket_default).

<a id="feedback_blender_multifile_eval_contamination"></a>

## One .blend per process when diffing evaluated geometry

*Looping `wm.open_mainfile` over several files in one background process produces false evaluated-geometry differences.*

GN_PointsToSpheres reported two identical modifier states as different, reproducibly, but
only after another .blend had been opened in the same process. The diff was the whole
evaluated `UVMap` layer (realized-instance data); positions, counts and normals matched. One
process per file: 36/36 pass. Something in the evaluated/instance cache survives
`open_mainfile`.

**How to apply:** for any check comparing evaluated geometry across files (unchanged gates,
truth tables, A/B diffs), run one Blender process per file. A single-process sweep is a
pre-filter only; re-run a "failing" file alone before concluding anything.

<a id="feedback_blender_ui_screenshot_automation"></a>

## Capturing addon UI screenshots via MCP

*In-process recipes for panel screenshots in a live Blender (5.0); never inject OS-level input.*

- **Area shot:** `bpy.ops.screen.screenshot_area(filepath=...)` under
  `temp_override(window, area, region)`; works with the window occluded. Crop with numpy on
  the loaded image's pixels (row 0 = bottom).
- **N-panel tab:** `region.active_panel_category = 'Tab'` only inside a
  `temp_override(window, area, region=ui_region)` and after one redraw
  (`bpy.ops.wm.redraw_timer(type='DRAW_WIN_SWAP')`); otherwise it is read-only.
- **Sidebar width isn't scriptable** (`region.width` is read-only). For wide shots
  re-register the panel with `bl_ui_units_x = 36` and open it with
  `bpy.ops.wm.call_panel(name=..., keep_open=True)`.
- Popups freeze their content (re-open per state); re-registering a panel moves it to the
  end of its parent's subpanels (toggle the addon to restore); `open_mainfile` closes popups.
- The splash screen only goes away by loading a .blend.
- **Never inject OS clicks** (SetCursorPos/mouse_event): several Blender instances with
  unsaved work may be open and clicks land on whatever is topmost. Identify the MCP Blender
  by `os.getpid()` inside it; `Get-Process blender` lists all of them. For driven input use
  a separate `--enable-event-simulate` instance (next sections).

<a id="finding_xvfb_event_simulate"></a>

## Real-UI tests without a desktop: Xvfb + event_simulate

*Blender's full UI runs under Xvfb, and `Window.event_simulate` can press real keys and drag real gizmos, but four traps make simulated input silently do nothing.*

Measured on Blender 4.0.2 (apt) under Xvfb with Mesa llvmpipe, 2026-10-15.
Recipe: `GeometryConstraint/source/tests/headless/gui_drive.py`.

```bash
Xvfb :99 -screen 0 1600x1000x24 &
DISPLAY=:99 blender --factory-startup --enable-event-simulate --python drive.py -- args
```

Step the test from a `bpy.app.timers` generator: yield a delay after each
batch of events so Blender processes them and redraws.

1. **The splash screen eats the first key presses.** Move the mouse into the
   viewport and send ESC first.
2. **Key events need `x=, y=`.** Without them they land at window (0, 0),
   which is the timeline, so `G` moves keyframes instead of verts. Pass the
   current cursor position with every key event.
3. **`ctrl=True` on a key event leaves Ctrl logically held.** Later drags
   then snap in 1 m increments. Send an explicit `LEFT_CTRL` RELEASE with
   the flags cleared after any modifier combo.
4. **Gizmo drags need a big first step.** Send roughly 10 px moves until the
   drag threshold opens, then fine steps. Tiny steps never start the
   transform (the header shows `D: 0`).

Also:

- Scripted scene setup isn't an undo step. Call
  `bpy.ops.ed.undo_push(message=...)` after it, or Ctrl+Z undoes your setup
  and the object reference dies.
- `bpy.ops.screen.screenshot*` returns black under llvmpipe. Grab the X
  display instead: `xwd -root -display :99 | convert xwd:- png:out.png`,
  then crop to `area.x/y/width/height` (X origin is top-left).
- `screen.screen_full_area()` called from a timer segfaulted 4.0.2. Don't
  toggle full-screen areas while driving the UI.

**Why:** each trap gives a clean "nothing happened" run. Here they cost
five debugging rounds.

<a id="finding_windows_real_ui_capture"></a>

## Real-UI demo capture on Windows: screenshots, menus, typing

*On Windows the Xvfb recipe isn't needed: `screen.screenshot` reads the real framebuffer, popups included. But menus remember the last pick, letter keys hit accelerators, and text needs TEXTINPUT PRESS.*

Measured on Blender 5.0, Windows 11, ui_scale 1.25, 2026-10-21. Recipe:
`Blender/Addons/ModifierStackActions/source/tests/headless/ui_driver.py` + `demo_media.py`.

```
blender --factory-startup --enable-event-simulate --window-geometry 0 0 1920 1080 --python drive.py
```

- `bpy.ops.screen.screenshot(filepath=...)` under a `temp_override(window, screen, area)`
  captures the whole window **with open menus and dialogs**. The OS cursor is not in it; draw
  it afterwards from the positions you sent.
- **Find panel positions by probing.** Append a draw function to `UI_MT_button_context_menu`
  that records `context.button_pointer`, right-click down a column every 6-8 px, ESC after
  each. Gives the y of every modifier header.
- **Menus open with the last-clicked item under the cursor**, matched by label. Fixed offsets
  from the click point break after the first pick. Track the last pick, and reset when its
  label changes (e.g. "Show Up To Here" becomes "Restore Modifier Stack").
- **Letter keys go to the menu under the cursor.** With a submenu open but the mouse still on
  the parent item, typing `s` fires the parent's `S` accelerator. Move into the submenu along
  the item's row first; then `SEARCH_ON_KEY_PRESS` opens the search.
- **Text fields:** `event_simulate('TEXTINPUT', 'PRESS', unicode=ch)`. `value` must be
  `'PRESS'` when `unicode` is set. In a props dialog, Enter once confirms the text, again
  runs OK.
- `preferences.view.show_tooltips = False`, or hover pauses put tooltips in the shots.

**Why:** each of these produced a run that looked fine until you checked the screenshots.
Clicks landed on the wrong menu entry, and typed text went to hotkeys.

<a id="finding_pypi_bpy"></a>

## `pip install bpy` gives a headless Blender 5.0 anywhere

*The PyPI `bpy` wheel (Python 3.11, ~380 MB) is a full Blender 5.0 for headless checks and Workbench renders, even where download.blender.org is blocked.*

`uv venv -p python3.11 && uv pip install bpy==5.0.0`. Workbench rendering
needs EGL (`apt install libegl1 libgl1-mesa-dri`). Import `bpy` before
`bmesh` / `mathutils`, which only exist after `bpy` loads. No UI (use
apt's Blender + Xvfb for that, see above).

<a id="finding_background_transform_pivot"></a>

## Background transform ops ignore the Pivot Point without a 3D View

*In `--background` (or the PyPI `bpy` module), `bpy.ops.transform.rotate/resize` with no VIEW_3D context acts as if the pivot were the median: 3D Cursor, Active Element and Individual Origins have no effect.*

Measured on Blender 5.0 (PyPI `bpy`), 2026-10-15. Selecting one vertex,
setting `transform_pivot_point = 'CURSOR'` and rotating 90° about Z left the
vertex in place (it rotated about itself). The same call inside a 3D View
context rotated it about the cursor.

**Why:** the transform reads the pivot through the view context. With no
area it falls back to the median. Tests that check pivot behaviour pass for
the wrong reason or fail confusingly.

**How to apply:** run the op inside the startup layout's 3D View (the
factory startup has one, even in background mode), or pass
`center_override=` explicitly:

```python
win = bpy.context.window_manager.windows[0]
area = next(a for a in win.screen.areas if a.type == 'VIEW_3D')
region = next(r for r in area.regions if r.type == 'WINDOW')
with bpy.context.temp_override(window=win, area=area, region=region):
    bpy.ops.transform.rotate(value=0.4, orient_axis='Y')
```

