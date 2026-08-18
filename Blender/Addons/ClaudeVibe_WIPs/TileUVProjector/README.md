# Tile UV Projector v1.6.0

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
- **Default UV Scale** - Optional fixed scale applied inside the tile after
  projecting, about a tile-relative pivot
- **Tile Splitting** - Split custom tiles horizontally or vertically
- **Grid-to-Custom** - Generate custom tiles from uniform grid as starting point
- **Fine Adjust** - Optional interactive transform mode after projecting, with
  Blender's own transform keys (G/S/R, axis constraints, typed values) and
  optional distraction-free viewport

## Installation

### Method 1: Single File (Recommended)
1. Open Blender > Edit > Preferences > Add-ons
2. Click "Install..."
3. Select `tile_uv_projector.py`
4. Enable the addon

### Method 2: Folder Installation
1. Copy the `TileUVProjector` folder to your Blender addons directory
2. Restart Blender and enable the addon

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

### Default UV Scale

Under **Grid Settings**, next to Padding. Enable **Default UV Scale** and every
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

### Fine Adjust

Enable **Fine Adjust** (checkbox on the panel header) and every tile you apply
hands straight over to an interactive transform mode, so you can nudge the UVs
into place while watching the texture on the model. It can also be started on
its own with **Adjust Current UVs**, without re-projecting.

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
increments are editable under **Snap Increments (Ctrl)** in the Fine Adjust
panel:

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
| Default UV Scale | Apply a fixed scale inside the tile after projecting | Off |
| Scale X / Y | The scale to apply | 1.0, 1.0 |
| Pivot X / Y | Anchor for that scale, in tile space | 0.5, 0.5 |
| Snap Move | Ctrl-snap step when moving, in tile divisions | 8 |
| Snap Scale | Ctrl-snap step when scaling | 0.1 |
| Snap Rotate | Ctrl-snap step when rotating, in degrees | 5.0 |
| Fine Adjust After Project | Enter transform mode after applying a tile | Off |
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

## Changelog

### v1.6.0
- Added: **Snap Increments (Ctrl)** in the Fine Adjust panel. Move (in tile
  divisions), Scale and Rotate steps are all editable instead of hard-coded.
- Added: **Default UV Scale** in Grid Settings. An optional fixed scale applied
  inside the tile after projecting, about a tile-relative pivot, so a scale of
  `(0.5, 1.0)` at pivot `(0.5, 0.5)` lands the UVs half as wide in the middle of
  the tile. Applies to both grid tiles and custom atlas tiles.

### v1.5.0
- Fixed: holding `Ctrl` to snap did nothing. The modifier state was read off
  whichever event happened to be in hand, and the flags on synthetic movement
  events are not reliable. Ctrl and Shift are now tracked from their own key
  events, and pressing either takes effect immediately instead of waiting for
  the next mouse move.
- Changed: a move now snaps to **1/8 of a tile** per axis instead of a fixed
  0.05 UV, and snaps where the tile lands rather than how far it travelled. The
  old grid could not express a tile centre, so snapping pulled tiles off-tile.
- Changed: `Z` is now the V-axis constraint key so XZ work reads naturally;
  `Y` remains as an alias.
- Added: `MMB` during a transform picks the axis from the direction dragged so
  far, and pressing it on the current axis releases the constraint.
- Added: the header shows `[snap]` and `[precise]` while those modifiers are
  held.

### v1.4.5
- Changed: fine adjust now holds one BMesh for the session, re-acquiring it only
  when Blender invalidates it, and logs any change of BMesh identity.
- Added: when the persistence check fails, a controlled probe writes a known UV,
  reads it back before and after the flush, and prints which of the two steps
  loses it. Diagnostic only; the probe value is written and put straight back.

### v1.4.4
- Fixed: the real cause of fine adjust doing nothing. The mesh was resolved from
  a `context.active_object.data` reference captured in `invoke()`, so
  `bmesh.from_edit_mesh()` handed back a throwaway BMesh rebuilt from that
  datablock instead of the live edit BMesh. Every write landed in a copy that
  was discarded before the next event - the value even read back correctly
  immediately after assignment, which is why it looked like working code. The
  edit mesh is now resolved from `context.edit_object` on every event.
- Added: a one-shot persistence check. If an edit does not survive to the next
  read, fine adjust now says so loudly instead of silently doing nothing.
- Fixed: `INBETWEEN_MOUSEMOVE` is now consumed as well as `MOUSEMOVE`, so drags
  from high-rate mice and tablets are smooth rather than stuttering.

### v1.4.3
- Added: **Debug Log** toggle in the Fine Adjust panel (on by default). Traces
  invoke, every event, every transform step and every mesh flush to the system
  console, so a fine adjust that does nothing can say where it stopped.
- Added: **Force Exit** button, shown while fine adjust is running. Releases a
  session that has stopped responding and restores the recorded overlay and
  shading state - previously a stuck session meant overlays stayed off.
- Fixed: `modal_handler_add()` returning false is now detected and reported
  instead of leaving the mode looking active while receiving no events.
- Fixed: errors while writing UVs printed nothing at all. They now print a
  traceback and report the reason.

### v1.4.2
- Fixed: fine adjust still did not move anything on screen. v1.4.1 flushed UV
  edits with `loop_triangles=False` as a per-mouse-move optimisation, but the
  viewport draws textures from the tessellated loop data - so the UVs changed in
  the mesh while the screen kept showing the old ones. Flushing is back to the
  full default `bmesh.update_edit_mesh(mesh)`, and every 3D view and UV editor
  is tagged for redraw.
- Changed: loops are collected with the same helper and iteration order the
  apply operators already use, instead of index-based re-resolution.
- Changed: a fine adjust that cannot reach the UVs now reports the reason once,
  in the status bar and the console, instead of silently doing nothing.

### v1.4.1
- Fixed: fine adjust ran but nothing moved. The modal is launched from inside an
  operator flagged `{'REGISTER', 'UNDO'}`, so Blender pushed an undo step and
  rebuilt the edit-mesh BMesh the instant that operator returned - leaving the
  modal writing UVs into an orphaned mesh, with no error to show for it. Loops
  are now recorded as `(face index, loop offset)` and re-resolved against the
  current BMesh on every event.
- Fixed: scale drag did nothing when the transform started near the centre of
  the viewport, because the raw distance ratio was pinned at 1.0. The ratio is
  softened so zero movement still means no scaling at any starting distance.
- Fixed: rotate drag could jump a half turn when the pointer crossed directly
  behind the anchor, and produced nonsense when sitting exactly on it.
- Changed: UV edits flush with `loop_triangles=False, destructive=False` and tag
  the viewport region directly, so dragging updates live and cheaply.

### v1.4.0
- Added: **Fine Adjust** mode - an interactive UV transform that runs in the 3D
  viewport after a tile is projected, or on demand. Supports `G`/`S`/`R`, `X`/`Y`
  axis constraints, typed numeric values, `Ctrl` snapping and `Shift` precision,
  with per-step confirm/cancel and a whole-mode cancel that restores the UVs.
- Added: optional **Hide Overlays & Gizmos** and **Flat Textured Shading** while
  adjusting. Both record the viewport state on entry and restore exactly that
  state on exit, including when Blender tears the mode down itself. Properties
  that already held the wanted value are neither changed nor restored.
- Changed: the tile picker now closes before applying a tile, so the picker and
  fine adjust are never both live.

### v1.3.1
- Fixed: v1.3.0 used `Image.has_data` / `Image.size` to decide whether an atlas
  was usable. Blender loads image buffers lazily and `Image.reload()`
  deliberately frees the buffer for re-reading, so valid textures reported
  "Image data not loaded", **Reload** always claimed failure, and the picker
  opened onto an empty grid. A missing file on disk is now the only hard error;
  everything else asks Blender for the GPU texture, which is what makes it load.
- Added: an explicit "Enter Edit Mode to pick tiles" hint, so a greyed-out
  **Pick Tile** button no longer reads as a broken button.
- Changed: file-existence checks are cached per refresh token instead of running
  a disk stat on every panel redraw and every overlay frame.

### v1.3.0
- Fixed: reloading or repathing an atlas texture could leave the tile picker
  drawing Blender's magenta *missing image* placeholder. Pixel availability is
  now checked before the GPU texture is built, so the placeholder can never be
  mistaken for the atlas.
- Fixed: the tile picker could get permanently stuck as "active" when Blender
  tore the modal operator down outside `modal()` (file load, area close, script
  reload), which blocked tile picking entirely. Added `cancel()`, a `load_post`
  reset, and a self-healing active check.
- Added: **Reload** and **Refresh Preview** buttons plus a texture status line in
  both Grid Settings and the Grid panel.
- Added: **Find Missing Files** shortcut when the atlas path is broken.
- Added: preview-thumbnail fallback so the overlay still shows the picture from
  the preview window when the full-resolution buffer is unavailable.

## Requirements

- Blender 4.5+
- No external dependencies

## Author

Stephan Viranyi (stephko@viranyi.de)
