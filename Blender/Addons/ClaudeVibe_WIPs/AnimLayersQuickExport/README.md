# Animation Layers Quick Export

One-click non-destructive merge + FBX export for rigs using the
[Animation Layers](https://blendermarket.com/products/animation-layers) addon
by Tal Hershkovich.

## What it does

Animation Layers lets you stack animation clips as layers on a rig. The
addon ships two one-click export modes that both leave the layer stack
exactly as the animator had it before clicking:

- **Merged** — bakes all layers into a single FBX (Unity / Unreal style).
  Internally calls Animation Layers' `Merge Down` with `direction=ALL`,
  exports, then restores the original Anim_Layers + NLA tracks from a
  pre-merge snapshot.
- **Per Layer** — exports each Animation Layer as its own FBX, named after
  the layer's action (vanilla per-action workflow). For each layer the
  active layer index is switched so the FBX exporter bakes that layer's
  action data only; same prefix/suffix conventions apply.

Either way the animator never sees the destructive operation. They keep
working with the layer stack they had before clicking the button.

## Requirements

- Blender **4.2+**
- Animation Layers addon **2.3.4+** installed and enabled

If Animation Layers isn't detected, the panel and header button gracefully
disable themselves with a clear message.

## Installation

1. Download `AnimLayersQuickExport_v0.1.0.zip`
2. In Blender: `Edit > Preferences > Add-ons > Install from Disk`
3. Pick the zip and enable the addon
4. Make sure **Animation Layers** is also installed and enabled

## Where to find it

- **Header button**: 3D Viewport top-right header, next to the gizmo/overlay toggles.
  Greyed out when the active object isn't an armature with Animation Layers data.
- **Panel**: 3D Viewport sidebar (`N`) → `Animation` tab → inside the
  *Animation Layers* panel as a *Quick Export* sub-panel (collapsed by default).

## Settings

| Setting | What it does |
|---|---|
| **Export Path** | Folder to write the FBX to (relative `//` paths supported). |
| **Export Mode** | `Merged` (one FBX, layers baked) or `Per Layer` (one FBX per layer). |
| **Filename Source** | `Active Action Name` / `Armature Name` / `Custom`. In Per-Layer mode the per-file name uses the layer's action name (or layer name) regardless. |
| **Prefix / Suffix** | Strings prepended/appended to the resolved filename. |
| **Scope** | `Active Only` / `Active + Children` / `Selected Armatures + Children`. |
| **Bake Step** | Frame step passed to the Animation Layers merge. |
| **Smart Bake** | Use AL smart-bake (preserves keyframe density). |
| **FBX Animation** | All standard FBX animation flags (all bones, NLA strips, all actions, force start/end keying, sampling rate, simplify). |
| **FBX Armature** | Add leaf bones, primary/secondary bone axes, armature node type. |
| **FBX General** | Unit scale, scale options, bake space transform, axis forward/up, path mode. |

## License

GPL-3.0-or-later
