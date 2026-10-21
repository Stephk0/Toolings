# Smart Wireframe View — developer notes

Implementation and maintenance notes. User docs: [README](../README.md).
Original: `3DSMAX/Scripts/ST3E/Inspection/WireframeEdgeFaceOff.mcr`.

## Layout (WMH split)

```
source/
├── __init__.py            # bl_info + register/unregister only
├── blender_manifest.toml
├── core/
│   └── cycle.py           # OFF / OVERLAYS / WIREFRAME, state_of / flags_of / next_state, bpy-free
├── blender/
│   ├── preferences.py     # which states are in the cycle, all viewports
│   ├── operators.py       # view3d.smart_wireframe_cycle (reverse prop)
│   └── keymap.py          # Shift+Alt+Z forward, Ctrl+Shift+Alt+Z reverse, "3D View"
└── tests/
    ├── pytest.ini
    └── test_cycle.py
```

## How it works

The state is read from the active viewport's `overlay.show_overlays` and
`overlay.show_wireframes` (wireframe counts only while overlays are on), the
next enabled state is picked by `core.cycle.next_state`, and both flags are
written explicitly so every state is exact. With All 3D Viewports the active
viewport decides the state and every VIEW_3D area of the screen gets it.

## Tests

```
cd "Blender/Addons/Smart Wireframe View/source/tests"
python -m pytest -q
```

## Dev deploy

`install_to_blender.ps1` copies `source/` to the newest Blender's
`extensions/user_default/smart_wireframe_view`.
