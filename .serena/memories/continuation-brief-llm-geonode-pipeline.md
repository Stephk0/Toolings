# LLM Geonode Pipeline — continuation brief (2026-07-02)

Suite that reads + lays out Blender Geometry-Nodes graphs. Two engines that verify each other
via one shared audit. Resume here tomorrow.

## Location & structure
`Blender/Addons/ClaudeVibe_WIPs/LLMGeonodePipeline/` (consolidated 2026-07-02 from the old
`GeoNode Layout MCP/` folder + `Geonodes/geonode_route_tidy.py`, via git mv).
- `addon/` — Blender MCP-bridge extension (`__init__.py` socket server + main-thread queue +
  3 handlers; `compat.py`; `layout.py` = MCP `autolayout_pass` layered layout; `blender_manifest.toml` v1.1.0; `test_layout.py`). Installed zip: `distribution/LLMGeonodePipeline_v1.1.0.zip`.
- `server.py` + `pyproject.toml` — FastMCP server (tools `capture_graph`, `apply_layout`,
  `autolayout_pass`), MCP name `geonode-layout`, socket `localhost:9877`. Configured in
  `~/.claude.json` under BOTH `Toolings` project keys → `.../LLMGeonodePipeline/server.py`.
- `tidy_layout.py` — DEFAULT deterministic engine (was route_tidy). Importable:
  `tidy_and_route(ng)`, `process_file(fname, save, gate)`, `_cli()` under `__main__`.
  `TARGETS` list = the ST3E roster it batch-tidies. `GN` files live in `Blender/Geonodes/`.
- `layout_audit.py` — shared rule set (single source of truth). `audit(ng)`, `print_report`,
  `BLOCKING`/`ADVISORY` tuples, `_socket_y`, `MIN_CLEAR`, `ENTRY_Y_TOL`.
- `run_pipeline.py` — ORCHESTRATOR: applies tidy_layout then GATES save on geometry-unchanged
  AND blocking audit rules. `blender --background --factory-startup --python run_pipeline.py -- GN_NormalTransfer`.
- `prepare_capture.py` — opens a .blend + frames a GN node editor + starts server (prereq for MCP capture).
- Skill: `.claude/skills/geonode-layout-mcp/SKILL.md`. Repo memory (broader): auto-memory
  `feedback_gn_node_layout_spacing` (has ALL the routing internals + gotchas) and
  `project_geonode_modifier_asset_checklist` (roster/publish). Also `feedback_blender_draw_handler_context_gating`.

## Audit rules (layout_audit.py)
BLOCKING (fail → don't save): R1 no node overlaps · R2 reroutes clear of node bodies ·
R7 no frame overlap (partial overlap banned; full nesting allowed).
ADVISORY (report only): R3 left-to-right flow (advisory because deformer preview/gizmo joins
have legit backward links) · R4 frames labeled · R5 row clearance ≥70px · R6 entries staggered
(no two reroutes feeding one node share a Y).

## Layout model + subway-map principles (user's north star)
Trace which station(node)→which via which line. Lines/reroutes/nodes almost never intersect;
reroutes build AROUND nodes; keep H/V; a track may split from a shared source but stays readable.
- tidy_layout: columns by longest path, frames as vertical BANDS (cascade down+right), tight
  gaps `row_gap=55, band_gap=120`.
- Routing (`route_branches` + helpers): `_route_v` H-V-H for single cross-frame; SPREAD fan =
  trunk marches strictly RIGHT (monotonic tap_x, shift RIGHT only) — fixed the circling loop;
  STACKED fan = vertical bus. `_hlane` is bidirectional (nearest clear lane) to avoid deep detours.
- `route_into_nodes` (runs BEFORE route_branches): multiple cross-band wires into ONE node →
  nested staircase, entry reroute at each SOCKET's Y, TOPMOST socket → lane nearest node.
  SKIPS fan sources (source socket with >1 target) so it never fragments a fan.
- Cross-function wire = framed EXIT reroute in source frame + gap bend(s) + framed ENTRY in
  target frame (the `E` reroute added in `_route_v`/`route_into_nodes`).
- `frame_reroutes` (LAST pass): parents each reroute to the comment frame whose node-bbox
  (±60px margin) contains it; gap reroutes stay unparented. Frames at (0,0) during script →
  parenting needs no coord fix.

## Current state (GN_NormalTransfer.blend = the live test case)
The normal-transfer modifier (Source Object → Sample Nearest Surface → Set Mesh Normal; mask via
front-end Menu → Menu Switch(INT) → Index Switch: None/Attribute/Open-Boundary-Edges; Invert).
Published ST3E asset (asset+catalog+ST3E tag+is_modifier; demo objs GN_Demo + GN_Demo_Source).
Latest tidy: fan flows 1010→1050→1285 (NO circle), 18/29 reroutes framed into their function,
frames don't overlap, ALL 7 rules pass, geometry unchanged, saved. Verified live in Blender 5.0.

## OPEN ITEM to resume tomorrow
The inter-band vertical TRACKS (long wires from Inputs band down to Main Flow band across the
gap) still cross the open gap in parallel — inherent to stacking the two functions as vertical
bands. Next idea: bundle inter-band tracks into one shared corridor / reduce their crossings.
Get the user's eye on whether current result matches their image-2 target before more changes.
Also pending (optional): run `run_pipeline` across the full ~27-modifier roster to bring stale
files (tidied pre-improvement, trip R3/R6 advisories) up to the new standard.

## How to iterate (workflow)
1. Edit `tidy_layout.py`/`layout_audit.py`. 2. `run_pipeline.py -- GN_NormalTransfer` (rebuild a
FRESH file first via the scratchpad `build_normaltransfer.py` from temp lib
`%TEMP%/GN_NormalTransfer_export.blend`, because re-tidying already-routed output is non-idempotent).
3. Open in live Blender via `prepare_capture.prepare(...)`, then MCP `capture_graph` to eyeball.
Blender MCP (blender-mcp on :9876) + geonode-layout MCP (:9877) both used live this session.
Gotcha: bpy `is` fails after reopen — compare by `.name`/`==` (both scripts trace reroutes by name).
