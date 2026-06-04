# Tile UV Projector - Status & Architecture

## Current Version: v1.2.0
**Location:** `Blender/Addons/ClaudeVibe_WIPs/TileUVProjector/`
**Files:** `__init__.py`, `tile_uv_projector.py` (installable copy), `README.md`

## What It Does
Tile-based UV projection for texture atlas workflows. User selects faces, picks a tile (from grid or atlas overlay), addon projects/unwraps/relaxes/fits UVs into that tile with padding.

## Architecture

### Two Interaction Modes
1. **Button grid in N-panel** — always available as fallback, proportional sizing via W:H fields
2. **Viewport overlay picker** (modal operator `TILEUV_OT_pick_tile`) — draws atlas image + grid lines in 3D viewport using `gpu` module, clickable tiles with hover highlight. Docked to right edge of viewport near N-panel. Persistent: stays open after each click, ESC to close.

### Key Classes
- `TILEUV_Settings` — PropertyGroup on Scene, stores grid cols/rows, padding, proportion W:H, atlas_image pointer, clear_seams, auto_seams, unwrap_method, relax, projection_method, advanced grid settings
- `TILEUV_OT_apply_to_tile` — core operator: clear seams → mark boundary seams → project from view → unwrap → relax → normalize+place UVs into tile
- `TILEUV_OT_pick_tile` — modal with GPU draw handler, class-level state (`_is_active`, `_should_close`), `TILEUV_OT_close_picker` signals it to exit
- `TILEUV_OT_apply_to_custom_tile` — same pipeline but for custom atlas rects

### Panel Structure (N-panel > "Tile UV" tab)
- `TILEUV_PT_main` — top-level, advanced grid toggle
- `TILEUV_PT_grid_settings` — cols/rows, padding, proportion W:H, atlas texture selector
- `TILEUV_PT_unwrap_settings` — clear seams, auto seams, method, relax
- `TILEUV_PT_projection` — view / unwrap only
- `TILEUV_PT_grid_ui` — atlas preview (template_icon) + open picker button + button grid fallback. When picker active: shows status + close button only.
- `TILEUV_PT_advanced_grid` — custom tile list, bounds editor, split, generate from grid

## Known Limitations / Design Decisions
- Blender panels cannot overlay interactive elements on images. The atlas preview (`template_icon`) is display-only; the viewport overlay modal is the clickable version.
- `template_preview` was tried but breaks panel rendering silently. `template_icon` with `preview_ensure()` + try/except is the safe approach.
- Clear seams runs BEFORE auto seams to fix incorrect unwrap splits from stale seams.
- GPU drawing uses `gpu.shader.from_builtin('IMAGE')` for atlas texture, `'UNIFORM_COLOR'` for grid/highlights, `blf` for text labels.

## Open Items / Future Work
- User wanted atlas preview in panel to be directly clickable (impossible in Blender's UI system — overlay is the workaround)
- Could explore `GizmoGroup` for persistent viewport interaction without modal blocking
- Advanced grid mode doesn't have the overlay picker yet (only uniform grid)
- README.md is at v1.1.0, needs update to v1.2.0
