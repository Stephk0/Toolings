# Smart Isolate — developer notes

Implementation and maintenance notes. User docs: [README](../README.md).
Original: `3DSMAX/Scripts/ST3E/Inspection/SmartIsolate.mcr`.

## Layout (WMH split)

```
source/
├── __init__.py            # bl_info + register/unregister only
├── blender_manifest.toml
├── core/
│   └── isolate.py         # decide() / apply() / prune(): the isolation stack, bpy-free
├── blender/
│   ├── preferences.py     # AddonPreferences (nested, same/empty selection, keep cameras/lights, view)
│   ├── operators.py       # view3d.smart_isolate, view3d.smart_isolate_exit, per-viewport stacks
│   ├── keymap.py          # Numpad / and / in "3D View" (addon keyconfig overrides Local View)
│   └── ui.py              # "Isolated N" button appended to VIEW3D_HT_header
└── tests/
    ├── pytest.ini         # rootdir = tests/, never imports the bpy addon package
    └── test_isolate.py
```

## How it works

Blender's Local View cannot nest, so only the first level uses
`view3d.localview` (it stores the view to return to and sets
`space.local_view`). Every later level edits local-view membership directly
with `Object.local_view_set(space, state)`. Leaving calls `view3d.localview`
again.

State is a stack of frozensets of `Object.session_uid` (stable across
renames) per `SpaceView3D.as_pointer()`, in a module dict. It is not saved:
when the operator finds a viewport in local view with no stack (native Local
View, or a reopened file) it adopts the current members as level 1. Deleted
objects are pruned on each press.

The selection is `context.selected_objects`, which Blender already filters to
the local view. Objects outside the current level therefore cannot start a
REPLACE in nested mode; they only do in non-nested mode via subsets.

Keep View on Exit saves `region_3d` location/rotation/distance/perspective,
sets `preferences.view.smooth_view = 0` for the exit (restored in `finally`)
and writes the view back.

The operators have no UNDO flag, like `view3d.localview`.

## Tests

```
cd "Blender/Addons/Smart Isolate/source/tests"
python -m pytest -q
```

Live check (Blender MCP): build a temp scene, drive `view3d.smart_isolate`
with `temp_override(window, area, region, space_data)`, read
`ob.local_view_get(space)` (raises when the space is not in local view).

## Dev deploy

`install_to_blender.ps1` copies `source/` to the newest Blender's
`extensions/user_default/smart_isolate`.
