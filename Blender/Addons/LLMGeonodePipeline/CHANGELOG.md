# Changelog — LLM Geonode Pipeline

## Unreleased — 2026-09-26

- **Shader trees.** `tidy_layout` / `place_output_rightmost` no longer require Group
  Input/Output nodes: material, world and light trees use their active output node
  (`io_nodes`). New `tidy_shader(tree)` lays out a shader graph with the layered pass and
  Blender's own curved wires (the orthogonal reroute routing made shader graphs harder to
  read), and parks nodes that don't reach the output in a grey `Unused` frame below the
  graph. Gated by `logical_links` — real-node connections through reroutes must be
  identical before and after. First used on the 21 materials of the character example.
- **Fix:** `place_output_rightmost` compared node wrappers with `is`, which never matches
  for bpy wrappers, so the output was never aligned to its feeder and got a reroute
  detour. Now `==`. Geonode trees get the same alignment.

## v1.3.0 — 2026-08-19

Wire-legibility release. Found by a user image-diff on **SH_ScreenCavity**: the
graph passed every rule (R1–R11 all PASS) yet its wires were unreadable — the
user had to drag reroutes aside to reveal that one apparent line was three
separate signals. Measured on the saved file: **10 exactly-collinear wire pairs**
(0.0px apart, up to **3453px** of shared extent) and **13 vertical runs sitting
2.0px off a node's right border**, merged with the node outline.

**Root cause — the reservation system had holes, and three routers were allowed
to give up.** `placed`/`hplaced` were bare lists that only `_vlane`/`_hlane` fed;
`route_branches`' spread-fan path derived each drop lane straight from the
target's own X and never consulted *or* recorded anything, so two fans over one
node column landed on the same line by construction. Separately, three code paths
accepted a *known* clash when their bounded search ran out — `_vlane`'s `minx`
snap, the tap escape loop's `tap_x < target_right` guard (it stopped walking while
still inside the clearance pad, 2px from the border), and `_hlane`'s accept-start
fallback.

- **NEW `Lanes` allocator** — the one ledger every drawn segment goes through.
  Allocates *and* records; socket stubs and trunk hops the caller has no freedom
  over are recorded too, so later allocations can see them. Bidirectional search
  from the corridor centre; the last resort is a **jog** that maximises
  separation, never a snap onto an occupied lane.
- **Gutter-centred lanes** — a lane now targets the CENTRE of the free corridor
  between node columns and keeps `NODE_CLEAR` (30px, was a 16px hairline) from
  any body, so a bus reads as its own line instead of as part of a node's edge.
- **All routers converted**: `route_into_nodes`, `route_branches` (both the
  stacked-bus and spread-trunk paths), `route_around_nodes`, `_route_v`,
  `_route_back`. `route_around_nodes` no longer cycles lanes `(i % 6) * 24` —
  which guaranteed a collision on the 7th detour and reserved nothing.
- **Stacked bus exit is a lane, not a stub**: parking `R0` at the source's socket
  Y put two buses whose sources shared a socket row on one line for 3220px
  (Camera Right vs Nx/Ny, both at y=-88). It now goes through `hlane`.
- **NEW `separate_wire_lanes` repair pass** — runs LAST, on the graph as actually
  *drawn*. `declutter_reroutes` and `separate_frames` move things after routing,
  so lanes clear at allocation time can still collide at save time. Slides whole
  same-column / same-row reroute groups apart, with a travel budget derived from
  what a shift would bend, and treats immovable direct node-to-node wires as
  first-class obstacles.
- **NEW BLOCKING rules R12 + R13** (`layout_audit`) — no two wires drawn on top of
  each other; no lane painted along a node's border. Nothing in R1–R11 ever looked
  at a *wire*, which is why the defective graph passed the gate and was saved.
  `wire_segments()` is exported so engine and audit measure the same thing.
- **FIXED: the shader save gate never fired.** `_build/tidy_shader_group.py` tested
  `rep.get(rule, {}).get("fail")` — a key the audit never emits (it reports
  `{"status": "FAIL"}`), so "BLOCKING FAILURES -> not saving" was unreachable and
  SH_ScreenCavity saved despite failing.
- Verified on SH_ScreenCavity: R12 11→0, R13 13→0, all blocking rules PASS, and
  the 82 logical (reroute-traced) connections are **identical** before and after.
  Cost on the worst-case graph (GN_Mosaic, 2828 nodes / 3487 links): 90s → 98s.

**Rolling the new gate over the whole ST3E library (41 geonodes) surfaced five more
routing defects that R1–R11 had never been able to see.** 33/41 passed at first; each
fix below was found by measuring a specific failure, not by reasoning about the code.

- **FIXED: the stacked bus retraced its own line.** It always chained `R0` → topmost
  row, so whenever the source sat BELOW its targets the bus climbed past every row and
  descended back down the same X — one wire crossing itself (GN_Erosion_3D: 936px). It
  now chains monotonically AWAY from `R0` in each direction, splitting at `R0` when it
  sits between its rows (a reroute output may fan, so the split is free).
- **FIXED: `separate_wire_lanes` was blind to reroute→node stubs.** Only lanes and
  direct node-to-node wires were obstacles, so a trunk could sit 3.5px off an entry
  stub. Stubs are rebuilt every pass and tagged with an owner, so a group is blocked by
  other groups' stubs but never flees its own.
- **FIXED: `separate_wire_lanes` was itself reversing trunks.** Sliding a vertical group
  sideways moves a trunk TAP, and it could be pushed past its predecessor — GN_Erosion's
  trunk ran 1715 → 1996 → **1804** → 2040, so two hops of one trunk overlapped by 192px.
  A move now carries a window `(dlo, dhi)` that preserves the ordering and minimum length
  of every run attached to the group.
- **FIXED: direct wires were never in the ledger** — the last category of drawn segment
  nobody recorded, so a trunk could be allocated 7px from one. `seed_direct_wires` now
  records them up front, mirroring BOTH conditions under which a router leaves a link
  direct (adjacent-and-clear, and same-frame single-target at any length).
- **FIXED: `_route_v`'s horizontal exit leg is a lane, not a stub.** Its Y is pinned to
  the source socket and it can run for thousands of px; when that line is already taken
  it now drops to an allocated `hlane` first.
- `declutter_reroutes` also remembers escape rows, so two reroutes squeezing past one
  node no longer land on an identical Y.
- **Result: 39/41 saved**, geometry unchanged on every one. The two holdouts are the
  machine-generated giants — GN_Mosaic (2807 nodes / 1723 reroutes) and
  GN_TileableMeshNoise (1813 / 1125) — where lane density leaves no corridor to satisfy
  R12/R13; the gate left both files untouched rather than degrade them.

## v1.2.0 — 2026-07-10

Autonomy release: the pipeline no longer needs blender-mcp. The four tools it
used to borrow from the blender-mcp server (:9876) are now native handlers on
the bridge's own socket (:9877), exposed by `server.py`:

- **`execute_blender_code`** — arbitrary Python on Blender's main thread, `bpy`
  in scope, stdout captured (truncated past 60k chars). 120 s main-thread
  budget (other handlers keep 30 s) via new per-handler `HANDLER_TIMEOUTS`;
  `_send_command` takes a matching per-call socket timeout.
- **`get_scene_info`** — scene/filepath/object summary tailored to geonode work:
  per-object GN modifier groups + ALL `GeometryNodeTree` names in the file.
- **`get_object_info`** — transform, visibility, collections, modifier stack,
  materials, world bbox, and for meshes both base AND **evaluated** (depsgraph)
  vert/edge/poly counts — the geometry-unchanged gate as a first-class tool.
- **`get_viewport_screenshot`** — first open VIEW_3D area via
  `compat.screenshot_area`, downscaled server-side (`max_px`, default 800).
- **Auto-start preference (addon prefs, default OFF):** starts the socket
  server on Blender startup / file load so unattended sessions are reachable
  without clicking the N-panel (deferred one timer tick + `load_post`, no-op
  when already running).
- **FIXED: exclusive port bind on Windows** (`SO_EXCLUSIVEADDRUSE`): with the
  old `SO_REUSEADDR`, a second Blender instance could silently double-bind
  :9877 and steal connections — a stale server then answered with stale
  handlers (bit for real during the v1.2.0 bring-up). Now the second start
  fails loudly ("only one Blender can own the port").
- Addon + manifest bumped to 1.2.0; repackaged as `LLMGeonodePipeline_v1.2.0.zip`
  (old zip archived). Skill/README/prepare_capture updated: prepare an editor via
  the bridge's own `execute_blender_code`; blender-mcp is optional everywhere.

Layout engine (repo scripts, not part of the addon zip) — from the GN_Wave
user image-diff:

- **Socket-anchored Y refinement** in `tidy_layout`: sweeping band columns
  right-to-left, each feeder aligns its OUTPUT to the Y of the input socket it
  feeds. Tall consumers (Index/Menu Switch) get staggered feeder rows with short
  direct wires instead of a top-aligned row + diving wires; a feeder that
  anchors low vacates the straight path between its row neighbours (move the
  blocker, don't detour). Bands are also more compact (height from actual node
  bottoms).
- **`separate_frames` R7 enforcement pass** at the end of `tidy_and_route`:
  post-layout extensions (below-left localized GIs, exit reroutes) could make
  two frame boxes corner-cross at a diagonal band junction; partial overlaps are
  now resolved by shifting the lower frame's contents straight down (down-only,
  so vertical lanes stay orthogonal).
- **`layout_audit` R7 actually FAILS now** (was returning WARN despite being in
  `BLOCKING` — the bug had been masking two pre-existing corner-crossings in
  GN_NormalTransfer and GN_RadialArray; both now resolve via `separate_frames`).

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
