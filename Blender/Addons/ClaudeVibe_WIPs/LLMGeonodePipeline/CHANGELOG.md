# Changelog — LLM Geonode Pipeline

## v1.1.3 — 2026-07-02

Subway-map routing round 2: no circling fans, reroutes framed by function, no frame overlap.

- **Fan circling fixed:** the SPREAD-fan trunk now marches strictly RIGHT — each tap_x
  is forced `>= previous_tap + spacing` and only ever shifts RIGHT to clear a node.
  (The old per-column `_vlane` shifted LEFT on clash, so a later tap landed left of an
  earlier one and the wire looped back on itself under the intervening node.)
- **`route_into_nodes` no longer steals fan branches:** a source socket feeding >1 target
  is left whole to `route_branches`. (Grabbing one branch of a fan for the entry-staircase
  fragmented the source and was a second cause of the loop.)
- **Reroutes framed by function (`frame_reroutes`, new final pass):** each reroute is
  parented to the comment frame it sits inside (with a small margin). Cross-function wires
  keep a framed EXIT reroute in the source function and a framed ENTRY in the target
  (added `E` exit reroute in `_route_v`/`route_into_nodes`), with gap bends between —
  the "≥2, one per function, extras to dodge nodes" model.
- **R7 `no_frame_overlap` is now BLOCKING:** frames may not partially overlap (full nesting
  is allowed). Verified: `GN_NormalTransfer` — fan flows 1010→1050→1285 (no loop), 18/29
  reroutes framed into their function, frames don't overlap, all rules pass.

## v1.1.2 — 2026-07-02

Subway-map entry routing — wires into the same node no longer pile on one row.

- **`route_into_nodes` (new pass, runs before `route_branches`):** all cross-band
  wires entering the SAME node are routed as a nested, non-crossing staircase — each
  entry reroute sits at its target SOCKET's Y (staggered), and lanes nest so the
  TOPMOST socket turns in the lane closest to the node, lower sockets progressively
  further left. Replaces the old habit of parking every entry reroute at `node_y-35`
  (one horizontal row → crossing taps you couldn't trace).
- **`_socket_y` helper (headless-safe):** enter/leave a node AT socket height, so taps
  are pure-horizontal. `_route_v` now uses it for single entries too.
- **New audit rule `R6_entries_staggered` (advisory):** flags any node whose incoming
  reroutes share a Y (within `ENTRY_Y_TOL`) — the exact "piled entries" defect. Encodes
  the subway-map principle so it's regression-checked.
- Verified: `GN_NormalTransfer` Mask-Source entries nest cleanly (Index@x800 nearest,
  Item_1@770, Item_2@740; R6 PASS). `GN_Wave` unregressed (R1/R2 pass); its stale
  on-disk copy trips R6 on one node — a re-run fixes it.

## v1.1.1 — 2026-07-02

Tighter layouts + rule-policy split.

- **`tidy_layout` packs tighter by default:** `row_gap` 175→55, `band_gap` 230→120.
  Cuts the vertical sprawl (`GN_NormalTransfer` height ~2126→~1300, aspect 0.86→0.52)
  without changing the frame-band structure or orthogonal routing.
- **Rule policy split (single source of truth in `layout_audit.py`):**
  `BLOCKING = (R1 no-overlaps, R2 reroutes-clear)` gate the save; `ADVISORY =
  (R3 left-to-right, R4 frames-labeled, R5 row-clearance)` inform only. R3 became
  advisory because feedback/preview topologies (deformer preview-cage / gizmo joins)
  have legitimate backward links — verified: `GN_Wave` is structurally sound (R1/R2
  pass) at tight spacing but has 2 inherent backward joins.
- `run_pipeline.py` now references `layout_audit.BLOCKING/ADVISORY`; dry-run verdict
  (`save=False`) no longer misreports as a failure.
- **Compact fan-out routing (`_hlane` bidirectional):** the horizontal-trunk lane
  allocator now searches BOTH directions from the source and takes the nearest clear
  lane. Fixes the deep fan-out detour where a down-only search got shoved ~400px below
  a whole lower row of nodes and looped back — now a short hop up into the header gap.
  Verified: `GN_NormalTransfer`'s Mask-Source fan moved from y-1545 to y-1089 (compact
  bus right at the row, matching the target layout); `GN_Wave` (gizmo) unregressed.

## v1.1.0 — 2026-07-02

Consolidated the GeoNode Layout MCP and the deterministic `tidy_layout` engine
into one maintained suite (`LLMGeonodePipeline/`).

- **Merged** the MCP bridge (`addon/`, `server.py`), the deterministic pipeline
  (`tidy_layout.py`, moved from `Blender/Geonodes/geonode_route_tidy.py`), and the
  companion scripts (`layout_audit.py`, `prepare_capture.py`) into one folder.
- **`tidy_layout.py` refactored** to expose an importable API
  (`tidy_and_route`, `process_file(gate=…)`, `eval_positions`) under an
  `if __name__ == "__main__"` CLI — was a run-once script.
- **NEW `run_pipeline.py` orchestrator:** applies `tidy_layout` by default, then
  gates the save on BOTH goals — geometry unchanged AND the `layout_audit` rules
  (R1–R5). The two engines now verify each other through one shared rule set.
- MCP server path updated in `~/.claude.json` (`…/LLMGeonodePipeline/server.py`).
- Addon bumped to 1.1.0 (unchanged behavior; repackaged as
  `LLMGeonodePipeline_v1.1.0.zip`, old zip archived).

## v1.0.0 — 2026-06-26

Initial release. AI-driven Geometry Nodes layout suite (read + layout only).

**Addon (`geonode_layout_addon`)**
- TCP socket server inside Blender with a main-thread task queue
  (`bpy.app.timers`-drained) so the socket thread never touches `bpy`.
- Three handlers, all main-thread:
  - `capture_graph` — annotated screenshot (index stamped per node via
    `view2d.view_to_region`, drawn inside Blender) **plus** the node/link table,
    in one response. Dimensions read post-draw.
  - `apply_layout` — one batched write of `node.location` (absolute node space;
    frames applied before children).
  - `autolayout_pass` — deterministic layered layout (returns moves, never
    auto-applies).
- N-panel (`GN Layout MCP` tab in the Node Editor) to start/stop the server.

**MCP server (`server.py`)**
- FastMCP process forwarding the three tools over the socket; Pillow used only
  to downscale the capture image to `max_px`.

**Verified live (Blender 5.0.0):** all acceptance criteria pass — legible
indices matching the table, links resolving by index, nonzero post-draw
dimensions, exact `apply_layout` placement, non-overlapping left-to-right
autolayout, and a full socket round-trip through the main-thread queue.

**Fixed during bring-up:** index stamps were not rendering into the capture
because the draw handler gated on transient region-wrapper identity (`is`).
Now gates on the persistent tree datablock (`==`) and reads the live region
from context at draw time.
