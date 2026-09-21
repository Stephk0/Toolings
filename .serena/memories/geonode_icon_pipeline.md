# ST3E geonode icon pipeline

Generates the Asset-Browser previews for every ST3E Geometry Nodes modifier:
a 256x256 framed render of Suzanne per modifier, embedded into each source
`.blend` as a custom ID preview.

**Everything lives in `Blender/Geonodes/_icons/`. Read `ICONS.md` (the
contract) and `GOTCHAS.md` (the hard-won findings) there before touching it.**
This memory is only a pointer plus the facts you need to not get lost.

## Shape

Two stages, both Blender 5.0 headless with `--factory-startup`:

- **Stage A** `build_icons.py` -> `out/<GROUP>.png`. Appends each node group as
  a **copy** into a throwaway scene, so it never touches the library.
- **Stage B** `embed_icons.py` -> writes the PNGs into each `.blend` via
  `ed.lib_id_load_custom_preview` under `temp_override(id=ng)`. The only step
  that saves. Has `--dry-run`. Always follow with a cold verify
  (`libraries.load(assets_only=True)` on the closed file).

Supporting: `recipes.py` (one entry per modifier), `stage.py` (scene, prep
steps, effect checker, framing, label), `make_frames.py` (per-catalog frame
PNGs), `coverage.py` (what still needs an icon), `fonts/` (vendored static
Familjen Grotesk + OFL).

## The idea worth keeping

A recipe declares `expect=` (deform / verts_up / verts_down / topology /
attribute:<name>). Every build diffs the evaluated mesh before and after the
modifier and **fails the icon if nothing measurably changed**, writing no PNG.
Many of these modifiers do nothing without specific setup (material indices, an
Object socket, a named attribute), and a silently unmodified Suzanne is a worse
icon than a missing one.

Green is necessary, not sufficient - it proves something changed, not that the
icon reads. Look at every PNG.

## Status (2026-09-21)

13 recipes done and embedded, 39 `is_modifier` groups still to do, 10 legacy /
helper groups on the null catalog correctly excluded. Run `coverage.py` for the
live list. Unexercised prep classes: named-attribute / boundary selection, and
the `base=` overrides (Erosion wants a terrain grid, Mosaic a bounded plane).

`GN_TileableMeshNoise` still sits on the flat ST3E root catalog - per
`mem:geonode_modifier_asset_checklist` conventions it should be on a leaf
sub-catalog.

## Two traps that will cost you an hour

- **Headless EEVEE is not dependable.** It segfaults in `nvoglv64` mid-batch
  and cannot render a lightless scene in background mode at all. Both stages
  use **Cycles on CPU**.
- **The source `.blend`s change under you.** `GN_Wave` gained Ripple/Affect
  sockets and `GN_Delete` renamed `On Domain` -> `Domain` mid-session. Always
  re-probe a group's interface before writing or re-running a recipe; a rename
  surfaces as `KeyError: no such input socket(s)` from `set_params`.
