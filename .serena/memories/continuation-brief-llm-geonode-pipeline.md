# LLM Geonode Pipeline — continuation brief (updated 2026-07-10)

Suite that reads + lays out Blender Geometry-Nodes graphs. Two engines that verify each other
via one shared audit. Work continues after this compact.

## Location & structure
`Blender/Addons/ClaudeVibe_WIPs/LLMGeonodePipeline/`
- `addon/` — Blender MCP-bridge extension (socket server :9877 + 7 handlers); installed zip
  `distribution/LLMGeonodePipeline_v1.2.0.zip`.
- `server.py` — FastMCP server, MCP name `geonode-layout`, configured in `~/.claude.json`
  under the Toolings project keys. Tools: `capture_graph`, `apply_layout`, `autolayout_pass`
  + **v1.2.0 self-sufficiency ports of blender-mcp** — `execute_blender_code` (120s budget,
  stdout relayed), `get_scene_info` (incl. all GeometryNodeTree names), `get_object_info`
  (incl. EVALUATED mesh counts = the geometry gate), `get_viewport_screenshot`.
  **blender-mcp no longer required for geonode work; prefer the bridge's own tools.**
  Addon prefs: opt-in "Auto-start server" (startup + load_post) for unattended sessions.
  Windows bind is exclusive (`SO_EXCLUSIVEADDRUSE`) — a 2nd Blender start fails loudly
  instead of silently stealing :9877 (SO_REUSEADDR double-bind bit during bring-up).
- `tidy_layout.py` — DEFAULT deterministic engine (`tidy_and_route(ng)`, `process_file`).
- `layout_audit.py` — shared rule set (`audit(ng)`, `print_report`, `BLOCKING`/`ADVISORY`).
- `run_pipeline.py` — orchestrator: tidy then GATE save on geometry-unchanged AND blocking rules.
  `blender --background --factory-startup --python run_pipeline.py -- GN_Wave`.
- `prepare_capture.py` — opens a .blend + frames a GN editor + starts the server.
- **`GEONODE_CRITERIA.md` — THE canonical creation/tidying criteria (read first for ANY geonode
  work).** Routed via skill `.claude/skills/geonode-layout-mcp/SKILL.md`, `Blender/Geonodes/CLAUDE.md`
  stub, and a root `claude.md` bullet. Deep internals: auto-memories `feedback_gn_node_layout_spacing`,
  `gn-link-rewire-gotchas`, `project_geonode_modifier_asset_checklist` (roster/publish).

## Audit rules (layout_audit.py)
BLOCKING: R1 no node overlaps · R2 reroutes clear · R7 no partial frame overlap (FIXED 2026-07-10:
now truly FAILs; was WARN, which masked 2 pre-existing corner-crossings — see separate_frames).
ADVISORY: R3 left-to-right (deformer preview/debug feedbacks are legit) · R4 frames labeled ·
R5 row clearance ≥70 · R6 entries staggered · **R8 nodes framed · R9 unique socket names ·
R10 sockets in NAMED panels (implicit root panel doesn't count) · R11 no needless reroutes**
(R8–R11 added 2026-07-09, mirror the creation criteria).

## Engine rules distilled from user image-diffs (the loop that works)
User hand-edits a pipeline result, sends before/after screenshots; we diff → encode → regression
GN_Wave headless + live EdgeDestruct. Key encoded rules: relink by socket IDENTIFIER (dup display
names miswired geometry); Blender-5 Viewer sockets self-delete on unlink → viewers kept direct +
`__extend__` fallback; `est_h` prefers drawn dimensions (unlinked vector inputs +54px each);
adjacent targets (<300px dx, <240 dy, clear straight path) keep DIRECT wires, per-branch in fans;
**GI param fans exempt from ALL routing (straight dashed ribbons)**, localized GIs split per
x-cluster (>900px), parked below-left, labeled by interface PANEL name; `col_gap=130`.
2026-07-10 GN_Wave image-diff round: **socket-anchored Y** — band columns swept right-to-left,
each feeder's OUTPUT aligned to the Y of the input socket it feeds (tall Index/Menu Switch
consumers get staggered feeder rows; "move the blocker, don't detour the wire"); bands compact
(height from actual bottoms). Fallout: below-band GIs/exit reroutes corner-crossed neighbour
frames at diagonal band junctions → **`separate_frames`** end pass shifts the lower frame's
contents straight DOWN (down-only keeps lanes orthogonal); resolved 2 pre-existing + 1 new R7
case (NormalTransfer, RadialArray, Bend). 5-file dry-run + GN_Wave: all green, geom unchanged.

## State (updated 2026-07-10)
- `4691ca3` + `e8a2431` PUSHED to origin/main (criteria workflow + EdgeDestruct tidy).
- **UNCOMMITTED in working tree:** (a) v1.2.0 autonomy release (addon hosts its own
  execute_blender_code / scene / object / screenshot handlers on :9877, auto-start pref,
  exclusive port bind; zip repackaged) — done in a parallel session; (b) socket-anchored Y +
  separate_frames + R7 FAIL fix (tidy_layout.py, layout_audit.py, CHANGELOG, GEONODE_CRITERIA);
  (c) GN_Wave.blend re-tidied with the final engine (all gates green).
- **UNCOMMITTED (user scoped commit):** 4 extracted library geonodes in `Blender/Geonodes/`:
  `GN_Erosion`, `GN_NoiseDisplace`, `GN_VoronoiDisplace`, `GN_RandomDistribute` — extracted from
  `D:\Work_DistrictGames\Assets\Environment\TextureGenerator\textureGenerator_template.blend`
  2026-07-09; template relinked to them (46 swaps / 23 objects eval-verified; backup
  `_pre-library-relink.bak.blend`). Roster now 31 ST3E modifiers.

## Open threads
1. EdgeDestruct: user-added `Factor` input outside any panel (R10) — ask which panel.
2. Function-framing pass (R8) for the 3 unframed extracts (Erosion/NoiseDisplace/Voronoi);
   RandomDistribute has 2 partially-overlapping pre-existing frames (R7 WARN).
3. Commit the 4 extracted blends when user says so; more texgen extractions proposed:
   Fix Pivot + Grid/Cube primitives; reconcile local GN_CollectionInstancerModel FORK vs library;
   template double-links GN_SimpleTransform (repo + Dropbox).
4. EdgeDestruct_fixed still links external libs (bradley presets, Dropbox) — localization pending.
5. Optional: re-run pipeline across full roster to bring stale files to the new standard.

## How to iterate
1. Edit engine/audit. 2. `run_pipeline.py -- GN_Wave` headless (dry-check regression).
3. Live Blender: geonode-layout :9877 alone suffices (v1.2.0); `execute_blender_code` →
`prepare_capture.prepare(...)` then `capture_graph` to eyeball. Addon hot-swap recipe:
disable addon → copy `addon/*.py` + manifest over
`%APPDATA%/Blender Foundation/Blender/5.0/extensions/user_default/geonode_layout_mcp/`
→ purge `sys.modules['bl_ext.user_default.geonode_layout_mcp*']` → enable → start server.
NOTE 2026-07-10: a stale v1.1.0 server in the GN_Wave Blender window still held :9877 —
user must Stop it (N-panel) or close that instance, then start the server in the current one. Gotcha: bpy `is` fails after reopen — compare by `.name`/`==`.
Re-tidying already-routed output is non-idempotent for fine detail — prefer fresh state via git.
