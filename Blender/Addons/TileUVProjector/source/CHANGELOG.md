# Tile UV Projector v1.8.0 — changelog

User docs: [README](../README.md).

## v1.8.0 - release readiness

Packaging
- Added `blender_manifest.toml`, so the addon installs as a Blender 4.2+
  extension rather than legacy-only.
- Added a `LICENSE` (GPL-3.0-or-later) and an SPDX header, and declared the
  license in the manifest.
- The zip now puts `__init__.py`, `blender_manifest.toml`, `LICENSE` and
  `README.md` at the **archive root**, per `_TOOLING_STRUCTURE.md`. The previous
  layout wrapped them in a folder, which cannot install as an extension.
- Removed the duplicated `source/tile_uv_projector.py`; it was a byte-identical
  copy of `__init__.py` and only a drift risk. Install instructions updated.

Data loss and crashes
- **Multi-object Edit Mode no longer wrecks the non-active meshes.** All objects
  in Edit Mode are now collected and placed together.
- Fixed a panel crash: with **Per Object** enabled and no active object, every
  sidebar redraw raised.
- The tile picker and adjust mode can no longer run at the same time. Two live
  modals starved each other, and a re-project underneath a live adjust session
  could write stale UVs back over the new placement.
- Adjust mode no longer writes viewport settings back into a 3D view that has
  been closed, or into the previous file's viewport after a file load.

Correctness
- A selection that is degenerate on one axis is now centred in the tile instead
  of being silently collapsed onto its left or bottom padded edge.
- The tile is validated before any mesh is touched, so a rejected apply no
  longer leaves a new UV layer or modified seams behind.
- Custom tiles honour per-object padding, and an inverted or zero-area tile
  reports that instead of blaming padding.
- **Generate from Grid** reads the same grid the panel shows.
- Relax runs one `minimize_stretch` with N iterations instead of N separate
  operator calls - up to 500 of them, each with its own undo push.
- Project From View reports a clear error outside the 3D Viewport instead of
  raising a raw context error.
- The unapplied-scale warning now actually tests non-uniformity; a uniform 2.0
  scale no longer triggers it.
- UDIM atlases are no longer reported as missing files.
- Repeated tile splits stop accumulating `(bottom) (bottom)` suffixes.

Robustness and polish
- Both "Close Picker" and "Exit Adjust Mode" escalate: a second press forces the
  release, so neither mode can strand you with overlays switched off.
- The picker overlay is drawn only in the viewport it was opened in, instead of
  ghosting into every other 3D view.
- The picker's draw callback is exception-guarded and redraws only when the
  hovered tile actually changes.
- Dense grids no longer lock the UI: tile labels are skipped below a readable
  size, and grids over 1024 tiles show a hint instead of a button per tile.
- The panel thumbnail is clamped to the sidebar the same way the overlay is, so
  the clickable columns line up with the picture.
- The atlas preview cache is only invalidated for images actually used as
  atlases, instead of on every image update in the file.
- Tooltips added to the eleven properties that had none, including the operator
  properties shown in F3 search and the redo panel.

## v1.7.0
- Fixed: the exit button did nothing while adjusting. Two causes - the modal
  swallowed the click before it reached the sidebar, and the operator reset the
  class state behind the modal's back, leaving it running and eating every
  event. Clicks outside the 3D view now pass through to the sidebar, and the
  button asks the modal to wind itself up.
- Renamed: **Default UV Scale** is now **Tile Scale**, and lives in its own
  section under Projection instead of inside Grid Settings.
- Renamed: the **Fine Adjust** panel is now **Adjust after Project**.
- Changed: **Snap Increments** is a collapsed sub-panel rather than an
  always-open box.
- Removed: the Debug Log option and all console logging, and the key-hint block
  in the panel. The key hints still appear in the status bar while the mode is
  running, which is where Blender's own transforms put them.

## v1.6.0
- Added: **Snap Increments (Ctrl)** in the Fine Adjust panel. Move (in tile
  divisions), Scale and Rotate steps are all editable instead of hard-coded.
- Added: **Default UV Scale** in Grid Settings. An optional fixed scale applied
  inside the tile after projecting, about a tile-relative pivot, so a scale of
  `(0.5, 1.0)` at pivot `(0.5, 0.5)` lands the UVs half as wide in the middle of
  the tile. Applies to both grid tiles and custom atlas tiles.

## v1.5.0
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

## v1.4.5
- Changed: fine adjust now holds one BMesh for the session, re-acquiring it only
  when Blender invalidates it, and logs any change of BMesh identity.
- Added: when the persistence check fails, a controlled probe writes a known UV,
  reads it back before and after the flush, and prints which of the two steps
  loses it. Diagnostic only; the probe value is written and put straight back.

## v1.4.4
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

## v1.4.3
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

## v1.4.2
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

## v1.4.1
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

## v1.4.0
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

## v1.3.1
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

## v1.3.0
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
