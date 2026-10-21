# Smart Wireframe View

**Version:** 1.0.0 · **Blender:** 4.5+ (built for 5.0) · **Category:** 3D View

One hotkey to step through the three ways you usually look at a model,
like the ST3E Wireframe / Edged Faces toggle for 3ds Max:

1. **Overlays Off** — the clean shaded model
2. **Overlays** — Blender's normal overlays (grid, outlines, gizmos …)
3. **Overlays + Wireframe** — overlays plus the geometry wireframe on every
   object, to read the topology

**Shift+Alt+Z** steps forward (it takes over Blender's Toggle Overlays key),
**Ctrl+Shift+Alt+Z** steps backward. The status bar shows which state you are
in.

## Settings

*Edit ▸ Preferences ▸ Add-ons ▸ Smart Wireframe View*

| Setting | Default | What it does |
|---------|---------|--------------|
| Overlays Off / Overlays / Overlays + Wireframe | All on | Which states the cycle goes through. Untick one to skip it, e.g. untick Overlays Off for a two-state toggle. |
| All 3D Viewports | Off | Change every 3D Viewport in the window, not just the one under the mouse. |

The hotkeys are listed in the same panel; untick one there, or rebind it.
The wireframe's look (Threshold, Opacity) is still set in the viewport's
Overlays popover.

Developer notes: [source/DEVELOPMENT.md](source/DEVELOPMENT.md) ·
History: [source/CHANGELOG.md](source/CHANGELOG.md)
