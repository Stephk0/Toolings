# Smart Isolate

**Version:** 1.0.1 · **Blender:** 4.5+ (built for 5.0) · **Category:** 3D View

Local View that works like the ST3E Smart Isolate for 3ds Max. It takes over
Blender's Local View keys (**Numpad /** and **/**), so you keep your muscle
memory and get a better isolate:

- **Select objects, press the key:** they are isolated. The view does not
  zoom or move (switch on **Frame Selection** if you want Blender's zoom).
- **Select some of the isolated objects, press again:** isolate deeper. You
  can go as many levels deep as you like.
- **Press again without changing the selection:** step back one level. From
  the first level this leaves isolation.
- **Press with nothing selected:** leave isolation and see everything again.

No separate "exit" button is needed. The 3D Viewport header shows
**Isolated** (or **Isolated 2**, **Isolated 3** … when nested); click it to
leave isolation at once.

## Settings

*Edit ▸ Preferences ▸ Add-ons ▸ Smart Isolate*

| Setting | Default | What it does |
|---------|---------|--------------|
| Nested Isolation | On | Selecting part of the isolated objects isolates deeper. Off: the new selection replaces the isolation, like 3ds Max. |
| Same Selection | Step Back One Level | What pressing with an unchanged selection does. Or: Exit Isolation. |
| Nothing Selected | Exit Isolation | What pressing with nothing selected does. Or: Step Back One Level. |
| Keep Cameras | On | Cameras stay visible while isolated. |
| Keep Lights | On | Lights stay visible and keep lighting the isolated objects in Material Preview and Rendered shading. |
| Frame Selection | Off | Zoom to the isolated objects when isolating. |
| Keep View on Exit | On | Leaving isolation keeps your current view. Off: jump back to the view from before isolating (Blender's default). |
| Header Indicator | On | Show the isolation level in the 3D Viewport header. |

The hotkeys are listed in the same panel; untick one there, or rebind it.

## Good to know

- Isolation is per 3D Viewport, like Local View.
- Only objects you can see in the viewport count as the selection. To
  isolate something outside the current isolation, step back first.
- If a file was saved while isolated, the isolation is restored as one level
  when you open it again.
- Isolating does not touch your objects' hide settings; it is Blender's own
  Local View underneath.

Developer notes: [source/DEVELOPMENT.md](source/DEVELOPMENT.md) ·
History: [source/CHANGELOG.md](source/CHANGELOG.md)
