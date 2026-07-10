# Geometry Nodes — Authoring & Tidying Criteria (ST3E)

Canonical criteria for **creating**, **tidying**, or otherwise **altering** any
geonode in `Blender/Geonodes/` — same bar for all three. Tool-agnostic: this file
lives with the pipeline, not in any AI config. Deterministic enforcement is this
folder's `layout_audit.py` (rules R1–R11) and `run_pipeline.py` (gates saves on
geometry-unchanged + blocking rules). Live interactive flow: skill
`geonode-layout-mcp`.

## Graph organization — "comment your geonodes like code"

1. **Function isolation (R8).** Every node lives inside a **labeled frame** that
   names its function (e.g. "Corner Damage Cubes", "Edge Damage Profile",
   "Final Boolean"). Frames are the unit of readability — a graph without
   function frames is a garbled mess regardless of routing. Group Input/Output
   buses are exempt. Frames never partially overlap; full nesting is fine (R7).
   Frame labels non-empty always (R4).
2. **Per-function Group Inputs.** One local `NodeGroupInput` per frame, wired
   only to that frame's consumers, unused sockets hidden. Never one giant Group
   Input fanning diagonals across the whole graph. Refinements (2026-07-09
   user image-diff on EdgeDestruct's Damage Noise Field frame):
   - **GI param fans are straight direct wires, always** — a ribbon of long
     parallel dashed lines reads fine; NEVER detour GI links through reroute
     lanes (the engine once stacked 7 lanes across a frame label doing this).
     All routing passes exempt `NodeGroupInput` sources.
   - **Park the GI below-left of its consumers** so the ribbon sweeps the clear
     corridor under the frame's nodes; a **single far consumer (≳900px right)
     gets its own small GI directly left of it** instead of one long wire.
   - **Label = the interface PANEL name** when all carried sockets share one
     named panel (e.g. "Edge Damage"), else `In: <function frame>`.
   (The tidy engine's `localize_group_inputs` implements all of this.)
3. **Wires = subway map.** Left→right flow (R3), orthogonal reroute runs that
   never pass through a node body (R2), entries into one node staggered per
   socket (R6), shared-source fans daisy-chain off ONE branch.
   **Lines only bend for a reason (R11): if the target is adjacent
   (≲300px, small rise, clear straight path) the link stays a DIRECT wire — no
   reroutes.** Reroutes are for building around obstacles and long runs, not
   decoration.
4. **Spacing.** No overlapping node bodies (R1), ≥70px clearance between nodes
   sharing a row (R5). Use real drawn `dimensions` when available — socket-count
   estimates miss unlinked vector inputs (3 sliders each).

## Interface (socket) conventions

- **Panels (R10).** Organize modifier inputs with `ng.interface.new_panel(name)`
  + `interface.move_to_parent(socket, panel, index)`. Convention:
  `Geometry` + `Selection` stay top-level → **base-params panel named after the
  effect** → optional `Affect Axes` (default_closed) → `Center` (pivot tools) →
  `Preview` (default_closed). Even a small tool gets one named base panel.
  NB: top-level interface items report an implicit ROOT panel with an empty
  name — "in a panel" means a NAMED panel.
- **Unique display names (R9).** Never two interface sockets with the same name
  — any by-name scripting silently miswires (bit us: two "Auto Angle Degrees"
  inputs re-linked to the wrong socket and changed the geometry). Rename to
  distinct, specific names (e.g. "Edge Auto Angle" vs "Corner Auto Angle").
- **Naming.** Title Case, effect-specific, no defaults like "Socket"/"Value".
  Every socket gets a `description` (tooltip) — only fill EMPTY ones on existing
  groups, never clobber.
- **Menus.** Menu sockets need a string `default_value`; the modifier override
  is an INT. One menu drives ONE master `MenuSwitch(INT)` → `IndexSwitch` nodes
  (never two Menu Switches off one menu).

## Deformer conventions (tools with a pivot)

Editable `Center` (TRANSLATION) + `Show Center Gizmo` (3 linear arrows + CROSS
marker, overlay-only) in a `Center` panel; `Symmetry` (abs-distance) only for
gradient-along-axis effects; `Affect X/Y/Z` filters for scaling effects;
`Show Deformation Preview` bbox cage (`GNG_DeformCage`) in a `Preview` panel.
Details: memory `feedback_gn_deformer_center_gizmo_symmetry`.

## Tidying an existing messy graph — order of operations

1. **Isolate functions first** (this makes everything after easier): capture the
   graph (`geonode-layout-mcp`), identify logical functions from connectivity +
   node semantics, create labeled frames and parent the nodes (trick: keep
   `frame.location=(0,0)` so child locations stay absolute). This is an AI/human
   judgment step — the deterministic engine cannot invent semantics.
2. **Fix the interface**: dedupe socket names (R9 — rename, don't reorder, so
   modifier overrides survive), group params into panels (R10), fill empty
   tooltips.
3. **Run the deterministic tidy**: `run_pipeline.py -- <GN_X>` (headless) or
   `tidy_layout.tidy_and_route(ng)` live — layering, per-function inputs,
   subway routing.
4. **Audit + verify**: `layout_audit` R1–R11 AND evaluated-geometry-unchanged.
   Never save when a blocking rule fails or geometry changed.

## Publishing

Asset checklist (mark, ST3E catalog `f9ab2fa9…`, `ST3E` tag, `is_modifier=True`,
demo object attached, full mainfile save): memory
`project_geonode_modifier_asset_checklist`. Target Blender 5.0; no external
dependencies — keep .blend files self-contained (no absolute-path libraries).
