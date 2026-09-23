# Tile UV Projector v1.8.0

Tile-based UV projection and placement for texture atlas workflows in Blender.

## Overview

Select mesh faces, click a tile in the grid, and the addon automatically projects, unwraps, relaxes, and fits the UVs into that tile with padding. Ideal for texture atlas creation and tile-based texturing workflows.

## Features

- **Uniform Grid Mode** - Configurable X/Y grid (default 4x4) with clickable tile buttons
- **Proportional Grid Buttons** - W:H proportion field controls button aspect ratio to match your texture
- **Atlas Texture Preview** - Load your texture atlas and see it above the grid for visual reference
- **Live Texture Updates** - Reload the atlas from disk without leaving the panel; the preview thumbnail and the tile picker overlay always show the same, current picture
- **Custom Atlas Mode** - Define arbitrary UV rectangles for non-uniform atlases
- **Clear Seams** - Clears existing seams on selected faces before unwrapping (fixes incorrect splits)
- **Auto Seams** - Automatically marks seams on selection boundary
- **Multiple Unwrap Methods** - Angle Based, Conformal
- **UV Relaxation** - Optional post-unwrap relaxation with configurable iterations
- **View Projection** - Projects UVs from current viewport before unwrapping
- **Padding Control** - Configurable padding inside each tile to prevent bleeding
- **Tile Scale** - Optional fixed scale applied inside the tile after
  projecting, about a tile-relative pivot
- **Tile Splitting** - Split custom tiles horizontally or vertically
- **Grid-to-Custom** - Generate custom tiles from uniform grid as starting point
- **Fine Adjust** - Optional interactive transform mode after projecting, with
  Blender's own transform keys (G/S/R, axis constraints, typed values) and
  optional distraction-free viewport

## Installation

Drag `TileUVProjector_v1.8.0.zip` from `distribution/` into a Blender window,
or use **Edit > Preferences > Add-ons > Install from Disk** and pick the same
zip. Blender 4.5 and newer install it as an extension; the addon then appears
under **View3D > Sidebar > Tile UV** in Edit Mode.

## Usage

1. Open the **N-panel** in the 3D Viewport
2. Find the **"Tile UV"** tab
3. Enter **Edit Mode** and select faces
4. Configure grid size, unwrap method, and padding
5. Click a tile button in the grid to project UVs into that tile

### Uniform Grid Mode
- Set columns (X) and rows (Y) for your atlas layout
- Each button in the grid shows its (col, row) coordinate
- Grid is drawn with row 0 at the bottom (matching UV space)

### Custom Atlas Mode
- Toggle "Advanced Grid" to switch modes
- Add tiles manually or generate from uniform grid
- Edit tile UV bounds (Min U/V, Max U/V)
- Split tiles horizontally or vertically for subdivision
- Click "Apply to [tile]" to project into the selected tile

### Choosing the Atlas Texture

The **Atlas Texture** field is Blender's standard ID selector
(`layout.template_ID`). Its dropdown lists every Image datablock in the current
file — `bpy.data.images` — which is the same list you see in the Image Editor or
in a Shader Editor Image Texture node. Anything loaded through **Open**, packed
into the .blend, generated, or already used by a material shows up there.

That one datablock is the single source of truth: the panel thumbnail and the
tile picker overlay both read it, so they can never show different pictures.

### Tile Scale

Its own section, directly under **Projection**. Enable **Tile Scale** and every
tile you apply gets a fixed scale inside its tile, straight after the UVs are
fitted - a standing offset like Padding, but with its own anchor.

- **Scale X / Y** - the scale to apply. `(0.5, 1.0)` is half as wide at full
  height; `(0.5, 0.5)` is half size in both directions.
- **Pivot X / Y** - the anchor, in tile space. `(0.5, 0.5)` is the tile centre,
  `(0, 0)` its lower-left corner, `(1, 1)` its upper-right.

So a scale of `(0.5, 1.0)` about a pivot of `(0.5, 0.5)` leaves the UVs half as
wide and sitting in the middle of the tile. The same scale about `(0, 0.5)` pins
them to the tile's left edge instead.

The scale is applied to the *usable* tile rect, meaning the rect already inset by
Padding, so the result stays inside the padded area. Values above 1.0 are allowed
and will push the UVs past the tile bounds - that is left to you rather than
clamped.

### Updating the Atlas Texture

Both **Grid Settings** and the **Grid** panel show the atlas texture's state
directly under the image field:

- A status line with the resolution (`2048 x 2048`). Blender loads image buffers
  lazily, so an image that has not been drawn yet reads as
  `name (loads on use)` — that is normal, not an error, and it resolves itself
  the moment anything draws the image.
- A red warning appears only when the file genuinely cannot be found on disk,
  which is the one case that produces Blender's magenta placeholder.
- **Reload** — re-reads the image from disk (`Image.reload`) and rebuilds its
  preview thumbnail. Use this after re-exporting the atlas from Photoshop /
  Substance / etc.
- **Refresh Preview** — rebuilds only the thumbnail from the pixel data already
  in memory. Use it for generated or painted images that were never on disk.
- **Find Missing Files** — appears only when the atlas path is broken, and opens
  Blender's standard missing-file search.

The picker overlay never draws Blender's magenta "missing image" placeholder. If
the atlas file is missing it falls back to the preview thumbnail, or draws a dark
panel with the reason written across it. Either way the grid stays clickable —
a broken texture never blocks tile picking.

### Adjust after Project

Enable **Adjust after Project** (checkbox on the panel header) and every tile you
apply hands straight over to an interactive transform mode, so you can nudge the
UVs into place while watching the texture on the model. It can also be started on
its own with **Adjust Current UVs**, without re-projecting.

While the mode runs, the key hints appear in the status bar and the current
state in the area header. **Exit Adjust Mode** in the panel leaves the mode and
keeps the changes; the sidebar stays clickable throughout.

The keys are Blender's own transform keys:

| Key | Action |
|-----|--------|
| `G` / `S` / `R` | Move / Scale / Rotate the selected UVs |
| `X` / `Z` | Constrain to the U or V axis (press again to release) |
| `MMB` | Pick the axis from the direction dragged so far |
| `0-9` `.` `-` | Type an exact value; `Backspace` edits, `-` flips the sign |
| `Ctrl` | Snap - 1/8 tile for a move, 0.1 for a scale, 5 degrees for a turn |
| `Shift` | Precision - one tenth of the mouse movement |
| `Enter` / `LMB` | Confirm the current move/scale/rotate |
| `Esc` / `RMB` | Cancel the current move/scale/rotate |
| `Enter` (idle) | Confirm everything and leave fine adjust |
| `Esc` (idle) | Undo everything and leave fine adjust |

`Z` is the V-axis key rather than `Y`, so an XZ modelling habit carries straight
over. `Y` still works as an alias.

So `S` `Z` `0.5` scales the UVs to half height along V, and `G` `X` `-0.25`
shifts them exactly one tile left on a 4-wide grid. Transforms pivot on the
centre of the selected UVs, and rotation is aspect corrected using the
**Proportion W:H** values so a turn stays square on a non-square atlas.

Snapping applies to where the tile **lands**, not to how far it moved. All three
increments are editable under **Snap Increments**, a collapsed sub-panel of
**Adjust after Project**:

| Setting | Default | Meaning |
|---------|---------|---------|
| Move | 8 | Snap to 1/N of a tile on each axis |
| Scale | 0.1 | Snap the scale factor to this step |
| Rotate | 5.0 | Snap the angle to this many degrees |

The move increment is expressed in **divisions of a tile** rather than raw UV
units on purpose. On a 4x4 grid, 8 divisions is 0.03125 UV, which keeps every
tile centre and tile edge exactly on the grid at any grid size. A fixed UV
increment cannot: the tile centres of a 4x4 sit at 0.125, 0.375, 0.625, 0.875, so
a round 0.05 grid would drag every tile off the tile it was just placed on.

The header shows `[snap]` and `[precise]` while those modifiers are held.

Mouse dragging works too and updates live as you move: one viewport width of
travel equals 1.0 UV unit for moves, while scale and rotate track the distance
and angle from the centre of the viewport. Scale stays responsive even when the
drag starts on the viewport centre, and rotation takes the short way round when
the pointer crosses straight behind the anchor.

Two optional view helpers, both off-by-default-safe:

- **Hide Overlays & Gizmos** - switches off the viewport overlays and gizmos for
  an unobstructed look at the texture.
- **Flat Textured Shading** - switches to Solid shading with flat lighting and
  texture colour, so the atlas is seen unlit and unshaded.

Both are strictly *record and restore*. Only the properties that actually needed
changing are recorded, and on exit each one is written back to the value it held
on entry - so if you were already working with overlays off, they stay off, and
if you were in Rendered shading you land back in Rendered shading. Nothing is
hard-coded on the way out, and the restore also runs when the mode is torn down
by Blender rather than by you.

## Settings

| Setting | Description | Default |
|---------|-------------|---------|
| Columns/Rows | Grid dimensions | 4x4 |
| Padding | Inner tile padding (UV space) | 0.005 |
| Proportion W:H | Texture aspect ratio for button sizing | 1:1 |
| Atlas Texture | Image to show as preview above grid | None |
| Clear Seams | Clear existing seams on selection before unwrap | On |
| Auto Seams | Mark seams on selection boundary | On |
| Unwrap Method | Angle Based / Conformal | Angle Based |
| Relax | Post-unwrap relaxation | Off |
| Relax Iterations | Number of relaxation passes | 10 |
| Projection | View / Unwrap Only | View |
| Tile Scale | Apply a fixed scale inside the tile after projecting | Off |
| Scale X / Y | The scale to apply | 1.0, 1.0 |
| Pivot X / Y | Anchor for that scale, in tile space | 0.5, 0.5 |
| Snap Move | Ctrl-snap step when moving, in tile divisions | 8 |
| Snap Scale | Ctrl-snap step when scaling | 0.1 |
| Snap Rotate | Ctrl-snap step when rotating, in degrees | 5.0 |
| Adjust after Project | Enter transform mode after applying a tile | Off |
| Hide Overlays & Gizmos | Hide overlays during fine adjust | On |
| Flat Textured Shading | Solid + flat lighting + texture colour during fine adjust | On |

## Edge Cases

- **No faces selected** - Operation cancelled with warning
- **Zero-area UV bounds** - Operation cancelled with warning
- **Non-uniform scale** - Warning shown, suggests applying transforms
- **Padding too large** - Error if padding exceeds tile size
- **Atlas file missing** - Panel shows a red warning with Reload and Find
  Missing Files; the overlay draws the reason instead of a magenta texture
- **Atlas buffer not loaded yet** - Not an error. Blender loads image pixels on
  demand, so the status line reads "loads on use" until something draws it
- **Picker torn down by a file load or script reload** - Picker state self-heals,
  so "Pick Tile" never gets stuck showing "Close Picker"

## Multi-Object Edit Mode

Blender's uv operators act on every mesh in Edit Mode, so Tile UV Projector does
too: selected faces across all objects currently in Edit Mode are collected,
measured together, and placed into the tile as one island. Previously only the
active object was placed, while the others were projected and unwrapped and then
left wherever the projection put them - their old UVs destroyed with no warning.

## Requirements

- Blender 4.5+
- No external dependencies
- Packaged with a `blender_manifest.toml`, so it installs as a Blender 4.2+
  extension as well as a legacy add-on

## License

GPL-3.0-or-later. See `LICENSE` in the addon folder.

## Author

Stephan Viranyi (stephko@viranyi.de)

---

[Changelog](source/CHANGELOG.md)
