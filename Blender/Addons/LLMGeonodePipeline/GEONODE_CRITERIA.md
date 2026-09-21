# Geometry Nodes — Authoring & Tidying Criteria (ST3E)

Canonical criteria for **creating**, **tidying**, or otherwise **altering** any
geonode in `Blender/Geonodes/` — same bar for all three. Tool-agnostic: this file
lives with the pipeline, not in any AI config. Deterministic enforcement is this
folder's `layout_audit.py` (rules R1–R13) and `run_pipeline.py` (gates saves on
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
   **Every lane is its own visible line (R12/R13)** — the half of "subway map"
   that used to be unwritten, and the half the engine kept violating
   (2026-08-19 user image-diff on SH_ScreenCavity: the user had to *drag
   reroutes aside* to discover that one apparent wire was three):
   - **No two wires share a line.** Two parallel runs closer than ~12px that
     co-extend for more than ~40px are ONE line to the eye. Parallel lanes are
     spaced a full `LANE_STEP` (28px) apart; two signals never occupy one X.
   - **No lane is painted on a node's border.** A run within ~22px of a node
     edge merges with the node outline. Lanes sit in the CENTRE of the corridor
     between node columns, ≥30px (`NODE_CLEAR`) clear of any body.
   - **A router may never "give up and accept a clash".** When a bounded search
     runs out of room the fallback is a *jog* that maximises separation — worst
     case a visibly parallel wire, never a hidden one. (All three historical
     give-up paths produced exactly this defect.)
   - Deterministic enforcement: `layout_audit` R12/R13, both **BLOCKING**, plus
     the `tidy_layout.separate_wire_lanes` repair pass that re-measures the
     graph as *drawn* after every node-moving pass has run.
4. **Feeders align to the socket they feed** (2026-07-10 user image-diff on
   GN_Wave's Displace Direction frame): when a consumer is TALL with inputs
   spread over its height (Index Switch, Menu Switch, big Group Output), place
   each feeder so its OUTPUT sits at the Y of its target INPUT SOCKET —
   staggered feeder rows with short direct wires, not one top-aligned row whose
   wires dive across the frame. Corollary: **move the blocker, don't detour the
   wire** — a feeder that anchors low vacates the straight path between its row
   neighbours, so adjacent links stay direct instead of getting reroute lanes.
   (Engine: socket-anchored Y refinement in `tidy_layout`, columns swept
   right-to-left.)
5. **Every group is a graph.** A helper group (`GNG_*`, or any nested node group)
   is something the user opens and reads, so it gets the SAME treatment as the
   tree that instances it — labeled function frames, panels, subway wiring, and a
   full tidy + R1–R13 audit. "The tool is tidy" is false while one of its groups
   is a pile at the origin. `run_pipeline.py` enforces this: it tidies every LOCAL
   group reachable from the main tree (`tidy_layout.own_trees`) and a blocking
   failure in any of them blocks the save. Linked groups are skipped on purpose —
   the `.blend` that owns a group is the one that tidies it.
   - **Run the tidy twice.** The engine is not idempotent: `node.dimensions` is
     only valid post-draw, so the first pass is what gives frames their real
     extents and the second pass is measurably better (GN_AmbientOcclusion: 5
     backward links → 0; its helper 10 → 2, then stable).
   - A **Repeat / Simulation Zone brackets its body, but a frame is ONE layout
     band** — put the zone's input and output in their OWN frames, created before
     and after the body frames, or the whole loop body lands left of its own input
     and every entry link reads backwards.
6. **Spacing.** No overlapping node bodies (R1), ≥70px clearance between nodes
   sharing a row (R5). Use real drawn `dimensions` when available — socket-count
   estimates miss unlinked vector inputs (3 sliders each). Frames stay compact:
   a band is only as tall as its content actually needs.

## Interface (socket) conventions

- **Panels (R10).** Organize modifier inputs with `ng.interface.new_panel(name)`
  + `interface.move_to_parent(socket, panel, index)`. Convention:
  `Geometry` + `Selection` stay top-level → **base-params panel named after the
  effect** → optional `Affect Axes` (default_closed) → `Center` (pivot tools) →
  `Preview` (default_closed). Even a small tool gets one named base panel.
  NB: top-level interface items report an implicit ROOT panel with an empty
  name — "in a panel" means a NAMED panel.
- **A `Selection` gate always ships with its invert.** Any tool that exposes a boolean
  selection input also exposes **`Invert Selection`** directly beneath it, in the same
  panel. Implementation is one `FunctionNodeBooleanMath` set to **XOR** between the
  Group Input and every consumer of the selection, in its own frame labeled
  `Selection Gate  (Selection XOR Invert Selection)`. XOR is the whole trick: off is an
  exact passthrough, on is the complement — so adding it to an existing tool cannot
  change a single vertex (verify with the A/B/C/D truth table: `(Sel 1, Inv 0)` must
  equal `(Sel 0, Inv 1)`, and `(Sel 0, Inv 0)` must equal `(Sel 1, Inv 1)`). Drive the
  gate through the modifier's *sets via attribute* binding and one vertex group serves
  as both a mask and its complement.
  **Adding a `Selection` that defaults to True is NOT backward compatible.** Blender
  backfills a newly added group input on an *already existing* modifier with the
  type's zero value, never with the socket default (verified across a save/reload:
  GN_Wireframe went to 0 vertices). So a new default-True bool silently kills every
  instance of that modifier in scenes saved beforehand. Set the value explicitly on
  every modifier instance in the shipped .blend, and document the manual re-tick for
  users. Adding a default-FALSE bool (like `Invert Selection`) has no such problem.
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
   subway routing. It covers every local group the tool owns, not just the outer
   tree (criterion 5). **Run it twice** — the engine is not idempotent.
4. **Audit + verify**: `layout_audit` R1–R13 on EVERY tree the tool owns, AND
   evaluated-geometry-unchanged.
   Never save when a blocking rule fails or geometry changed.

## Publishing

Asset checklist (mark, ST3E catalog `f9ab2fa9…`, `ST3E` tag, `is_modifier=True`,
demo object attached, full mainfile save): memory
`project_geonode_modifier_asset_checklist`. Target Blender 5.0; no external
dependencies — keep .blend files self-contained (no absolute-path libraries).
