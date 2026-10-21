# Modifier Stack Actions — developer notes

Implementation and maintenance notes. User docs: [README](../README.md).

## Layout (WMH split)

```
source/
├── __init__.py            # bl_info + register/unregister only
├── blender_manifest.toml
├── core/
│   └── stack.py           # bpy-free: hide/restore/extract plans, preview state JSON
├── blender/
│   ├── properties.py      # Object.modifier_stack_actions_state (JSON string, saved in .blend)
│   ├── insert.py          # Add Modifier Before/After: native menu wrapper + depsgraph move
│   ├── clipboard.py       # object.modifier_stack_copy / _paste (Before/After)
│   ├── operators.py       # object.modifier_up_to_here / _restore / modifier_extract_up_to_here / modifier_stack_move
│   └── ui.py              # UI_MT_button_context_menu entries + DATA_PT_modifiers banner
└── tests/
    ├── pytest.ini         # rootdir = tests/, never imports the bpy addon package
    ├── test_stack.py      # core (no bpy)
    └── headless/
        ├── blender_checks.py  # operators in real Blender, exits 1 on failure
        ├── ui_driver.py       # real-UI helpers: event_simulate, screenshots, timer stepping
        └── demo_media.py      # demo video / GIF / stills from the real UI
```

## Tests

```
cd source/tests && python -m pytest -q
"C:\Program Files\Blender Foundation\Blender 5.0\blender.exe" --background --factory-startup --python source/tests/headless/blender_checks.py
```

Both pass on Blender 5.0 and 4.5.

## Demo media (real UI)

```
blender --factory-startup --enable-event-simulate --window-geometry 0 0 1920 1080 ^
    --python source/tests/headless/demo_media.py -- capture <shots_dir>
python source/tests/headless/demo_media.py <shots_dir> <out_dir>      # needs PIL
blender -b --factory-startup --python source/tests/headless/demo_media.py -- encode <out_dir>/frames <out.mp4>
```

Step 1 opens a Blender window for about two minutes and drives it with simulated input. Real
mouse and keyboard input to that window is ignored while it runs. It doubles as the end-to-end
UI test: every menu entry is clicked for real, Add After goes through the submenu's own
search, and the log prints the resulting stack. Last run 2026-10-21, Blender 5.0, Windows,
ui_scale 1.25. `MENU_OFFSETS` are measured at that scale; re-measure on another one.
Outputs: `assets/demo/` (MP4, GIF, full-window stills with cursor) and the cropped README
images in `assets/`. The docs-site page uses copies in `docs-site/src/assets/tools/modifier-stack-actions/`.

## Implementation notes

- **Menu hook.** The modifier header's dropdown menu is drawn in C and can't be extended from
  Python. The tool appends to `UI_MT_button_context_menu`, the right-click menu of every button.
  The modifier is taken from `context.button_pointer` (the struct owning the clicked property,
  also for Geometry Nodes inputs), else from the panel's `context.modifier` pointer.
- **Preview state** lives on the object as JSON `{"v", "target", "hidden"}`. Restore matches by
  name, so modifiers deleted in between are skipped. Renaming a hidden modifier during a preview
  leaves it hidden.
- **Extract** follows the exporter rule: flags flipped for the evaluation are restored in
  `finally`, then `bpy.data.meshes.new_from_object(..., preserve_all_data_layers=True)` on the
  evaluated object. Only `show_viewport` is touched, so this evaluates the viewport stack.
- **Extract As...** is the same operator with `ask_name=True`, drawn under
  `operator_context = 'INVOKE_DEFAULT'` (menu items default to EXEC, which skips `invoke`).
  `invoke` prefills `new_name` and opens `invoke_props_dialog`. A blank `new_name` falls back
  to `core.stack.extract_name`.
- **Add Before/After.** `object.modifier_add` always appends, and the asset entries of
  `OBJECT_MT_modifier_add` are drawn in C, so they can't point at our own operator. The
  `OBJECT_MT_modifier_stack_add_before/after` menus draw the native menu through
  `menu_contents` and arm a pending insert (object, anchor, position, stack snapshot). A
  `depsgraph_update_post` handler moves the single new modifier (`core.stack.find_added`)
  with `ObjectModifiers.move`, then a timer pushes an undo step. The insert is dropped when:
  the stack changes in any other way, the native menu draws outside our wrapper (prepended
  hook, guarded by `_drawing_wrapper`), a file loads, or 120 s pass. Updates that leave the
  stack alone keep it armed, because a stale update can flush inside `modifier_add` before the
  modifier exists. The wrapper hides the native Search entry (INVOKE context) and draws its own
  search over the wrapper, since searching the native menu would disarm.
- **Extract As dialog** opens with the name field in edit mode via `row.activate_init`. It
  only works on a row and stops working under `layout.use_property_split` (Blender 5.0), so the
  dialog draws without property split.
- Operators take `object_name` / `modifier_name` (the menu always fills both). Empty names fall
  back to `context.object` + `modifiers.active`.
