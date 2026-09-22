# Geonode layout

Node spacing, frames and wire lanes. Enforced by the `geonode-layout-mcp` skill.

> Migrated verbatim from Claude auto-memory on 2026-09-22. Dates and version numbers are from when each note was written — trust the code when they disagree.

- [Node spacing and frames](#feedback_gn_node_layout_spacing)
- [Wire lane legibility](#feedback_gn_wire_lane_legibility)
- [The pipeline tidies every group, helpers included](#feedback_geonode_pipeline_tidies_every_group)

<a id="feedback_gn_node_layout_spacing"></a>

## Node spacing and frames

*When building/arranging Blender geometry nodes, space nodes generously and keep frames+labels — cramped layouts are unreadable*

When I arrange Blender geometry nodes via the MCP, lay them out with generous padding — roughly 300–380 px between columns and 250–400 px between vertically stacked nodes (tall texture nodes need more). My first pass on GN_RandomizePosition was cramped/overlapping and the user had to pull every node apart to read it.

**Why:** Default/tight placement produces crossing wires and overlapping bodies that are unreadable to a human reviewing the graph.

**How to apply:** Place nodes by data flow left→right in distinct columns. Trick for absolute placement: set every `NodeFrame.location = (0,0)`, then a child's `.location` equals its absolute world position (child loc is relative to its parent frame). `node.location` is the node's TOP-LEFT corner. Always keep nodes inside labeled frames and set descriptive `node.label`s — comment geonodes like code (see project CLAUDE.md).

**Programmatic layout rule `tidy_layout(ng)` (2026-06-03, derived from the user re-arranging GN_RandomizePosition by hand — image diff: my first pass had OVERLAPPING FRAMES + tight stacking; theirs had clear non-overlapping blocks with big padding and every label readable). Codified, deterministic, re-runnable — apply it after building any group:**
1. **Columns = longest dependency path.** For each non-frame node, `depth = max(depth(pred))+1` (cycle-guarded DFS over links, skipping NodeFrames). That column index is its X order — guarantees every node sits strictly right of its inputs. Group Output ends deepest.
2. **Column X from REAL node widths** (`n.width` is reliable even headless; `n.dimensions` is 0 until the editor draws). `colx[c] = colx[c-1] + max_width_in_col(c-1) + COL_GAP`, `COL_GAP≈140`. Texture/Index/MenuSwitch nodes are ~150 wide, so a fixed pitch of ~300–340 also works; width-aware is tighter.
3. **Frames become vertical BANDS so they never overlap** (this was THE fix — overlapping frames are the #1 unreadability cause). Group interior nodes by `node.parent` frame (unframed = its own band). Order bands top→down by mean member depth (earlier-stage frames higher). Each band stacks its nodes per-column from the band top, `ROW_GAP≈90`, `BAND_GAP≈170` between bands, `LABEL_PAD≈46` at band top for the frame header. Columns stay globally aligned across bands so wires read left→right.
4. **Estimate height** for row stacking (no `dimensions` headless): `h ≈ 34 + (n_in+n_out)*22 + props*30 + 14` (props≈1 for texture/math/menu/index/named-attr nodes).
5. **Group Input/Output = a left/right bus**, excluded from bands and vertically centred: input at `colx[0]-width-COL_GAP`, output at `colx[max]+width+COL_GAP`, both at mid-Y of the whole span. Reads as input-bus-left → stages → output-right.
6. Within a column, order nodes by the barycenter (avg Y) of already-placed predecessors to reduce wire crossings.

The full function was applied to `GN_RandomizePosition.blend` headlessly and saved; **screenshot-verify via [Headless Blender and automation](../headless-and-automation.md#reference_blender_mcp) when Blender reconnects and fine-tune BAND/GAP constants if blocks feel cramped or too sparse.** Related: [Geonode sockets, interfaces and menus](sockets-and-menus.md#feedback_gn_menu_to_index_switch), [ST3E geonode modifier — build recipe, roster, publish checklist](asset-checklist.md).

**Wire-routing tidy pass `route_tidy(ng)` (2026-06-04/05, evolved over ~8 image-diff rounds on GN_Spherify with the user). ALL steps are functionally lossless — VERIFY eval byte-identical in EVERY relevant state (e.g. preview ON *and* OFF; index-by-index, not just sorted) and DON'T save on FAIL. Run order matters. Helper `fname_of(n)=n.parent.name if n.parent else None`.**
Steps (in order):
1. **dissolve_reroutes** FIRST (makes the pass idempotent — re-running won't compound). Follow each reroute chain back to the real source, remove all reroutes, reconnect real source→real targets.
2. **LOCAL Group Input per frame** — one `NodeGroupInput` parented inside each frame, placed left of that cluster, wired only to that cluster's consumers; hide every UNUSED output socket (`o.hide=True`, only works on UNCONNECTED sockets → hide AFTER wiring). Multiple Group Inputs are interchangeable. Kills the long diagonal fan from one far Group Input.
3. **place_output_rightmost** — Group OUTPUT must be the single rightmost node: `gout.x = max(node.x+width over all others) + ~260` (big enough that its own reroute bus at `x-140` clears all content), align `gout.y` to the node feeding it. Do this BEFORE rerouting so the output link routes to the final position.
4. **reroute geometry+field SPINE (cross-frame, single-input only)** — orthogonal H-V-H with **TWO** reroutes per link: A at `(dest.x-140, source.y)`, B at `(dest.x-140, dest.y)`, wired source→A→B→dest (horizontal, vertical bus segment, horizontal). A single waypoint gives a diagonal — you need two for true right angles. **Reroutes UNPARENTED** (parent=None) — parenting them to a frame drags that frame's bounding box out and buries its label.
5. **route_fanout_bus** — a source feeding ≥2 STACKED nodes in one frame (e.g. `Center` → SeparateXYZ + the gizmos) → ONE vertical bus just left of the stack (`bus_x = min(target.x)-45`): source→R0(bus_x, source.y), then chain R0→R1→R2… one reroute per target at its height, each reroute also tapping horizontally into its target. This is the USER'S preferred fan-out (vertical bus + horizontal taps), MUCH cleaner than over-the-top detours.
6. **route_around_nodes** — for remaining single same-frame links, route up-and-over the row ONLY if the straight path ACTUALLY passes through another node's body (precise crossing test: interpolate wire-y at each candidate node's x-overlap, check vs its y-range). Don't over-route links that are already clean. **Rule the user stated: NEVER cross another node.**
7. **declutter_reroutes** LAST — nudge any reroute still inside a node's bbox vertically out of it (a few passes). No reroute may hide behind/in front of a node.

**HARD gotchas (each caused a wrong result before fixing):**
- **Frame identity: compare `node.parent` by NAME, never `is`/`is not`** — bpy wrappers fail identity even for the same frame, so `a.parent is b.parent` INVERTS cross-frame vs intra-frame detection (this single bug produced the nonsense 38/12/0 reroute counts and rerouted the wrong links). Dict keys/`==` on wrappers DO work; only `is` is broken.
- **NEVER reroute into a MULTI-INPUT socket** (`socket.is_multi_input`, e.g. Join Geometry). Re-adding the link appends it to the END of the merge order → output VERTEX ORDER reshuffles (set identical, `positions[i]` shift — breaks index/UV/shape-key). I tried order-preserving via `socket.links` but that order is UNRELIABLE → still reordered. Just skip multi-input dests; those few links stay direct.
- **Mutating `ng.links` invalidates the OTHER cached link wrappers mid-loop** → stale `l.from_socket`. FIX: collect `(from_node, from_socket.identifier, to_node, to_socket.identifier)` first, then mutate, re-fetching sockets by identifier (`next(s for s in node.inputs if s.identifier==ident)`; `node.inputs[x]` subscripts by NAME). Node/socket wrappers survive link edits; link wrappers don't.
- **Verification trap:** take the baseline snapshot BEFORE any mutation (I once sampled it after `dissolve`, which had silently severed the geometry spine → the broken state matched itself → "eval-identical" passed falsely and I saved a broken file). Restore from git if you corrupt a saved .blend.

**FINAL refinements (2026-06-05) — the working tool is `Blender/Geonodes/geonode_route_tidy.py` (rolled out to all 9 deformers, ShearGeometry excluded as hand-laid):**
- **Re-spread + CASCADE layout first** (a `tidy_layout` re-run inside the pass): columns by **PER-BAND LOCAL depth** (longest path using only intra-frame links) so each frame is only as wide as ITS OWN chain — a cross-frame link must NOT inflate a frame's width (that was the big empty-space bug: the Join inherited Spherify's high global depth → flung to far-right columns). Bands **cascade** (each frame starts right of the previous: `band_x += band_width + 140`) so geometry flows forward, no backward jumps/dead space. Tight gaps: `col_gap≈85`, `row_gap≈175` (loose vertical so stacked gizmos have room), `band_gap≈230`.
- **Vertical LANE allocator** (subway-map): every vertical run picks a clear X by shifting LEFT from `dest.x-140` until it overlaps no existing run in X(±30) AND Y. Parallel, non-overlapping lines you can trace. Shared `placed` list across the spine + Join passes.
- **Multi-input (Join) geometry reroutes ARE fine** after all — I was wrong to skip them outright. Appending reorders the Join, but the REAL output (preview OFF; gizmos add 0 verts) keeps its vertex order; only the never-exported PREVIEW-ON order shuffles. Verify with **OFF index-strict AND ON same-set** (sorted), not ON index-strict.
- **declutter** nudges reroutes off node bodies AND off each other (never two on one spot).
- Run order: snapshot baseline → dissolve → tidy_layout(cascade) → localize GIs → place_output_rightmost → spine(lanes) → multiinput(lanes) → fanout_bus → around_nodes → declutter → verify → save.

**LIMIT (2026-06-05): a reroute/bus pass can't fully match hand-tidying — sometimes a FUNCTION NODE itself must be REPOSITIONED.** The user's final Spherify edit *moved the `Center Marker` gizmo node* to a clearer spot so its fan resolves cleanly; reroutes alone (which never move the function nodes) get ~90% there but a tightly-stacked cluster still reads busy. Repositioning nodes for tidiness is a visual judgment that CANNOT be verified headless, so don't blindly auto-move nodes — get the automated pass to ~90% and let the user hand-finish individual node moves, OR spread a stacked cluster's row gap during the build's `tidy_layout` so later fan-outs have room.

Verified on GN_Spherify: 3 local Group Inputs, 8 spine reroutes, 5 fan-out-bus, 9 around-node, output rightmost, decluttered — eval byte-identical (preview on & off). **Visual look CANNOT be checked headless (MCP screenshots the 3D viewport, not the node editor) — the user eyeballs each round and sends a screenshot; iterate on Spherify, then roll the SAME pass across all deformers.** If the user re-saves over a routed file, just re-run (idempotent via step 1).

**FINAL ARCHITECTURE (2026-06-05, rolled out to all 9 deformers, rated 7/10 by user — good enough to ship):** the separate spine/multiinput/fanout passes were UNIFIED into one `route_branches(ng, placed, hplaced, boxes)` that groups EVERY real link by its SOURCE socket and routes each source ONCE. This was THE fix for "shared-source reroutes must daisy-chain, never stack duplicates on the same line" (user marked green overlap areas):
- **1 target, same-frame** → leave DIRECT (route_around handles crossings). **1 target, cross-frame** → H-V-H (`_route_v`, 2 reroutes).
- **≥2 targets** → ONE shared branch off the source: STACKED (x-range ≤200) = vertical bus; SPREAD = horizontal TRUNK at source height flowing RIGHT, tap DOWN per column. Targets sharing a row/col REUSE the same reroute (dedupe by `round(_ymid(b)/8)*8`) so two reroutes never land on one spot.
- **Node-aware lanes:** `_vlane`/`_hlane` now reject any X/Y that passes through a node BODY (`_hits_node`/`_hits_node_h`), not just other reroutes — buses no longer slice through nodes. `boxes=node_boxes(ng)` computed once before routing (reroutes added after, so static).
- **BACKWARD links** (target left of/under source, e.g. AxisBounds→Range) caused overshoot+self-cross: `_route_back` routes exit-right → drop to a clear `_hlane` BELOW → run left → rise into target FROM ITS LEFT (approaches rightward, never overshoots). 4 reroutes. In a fan, targets are split fwd/bwd; bwd each `_route_back`.
- **Flow = western reading order** (right + down): trunks sit at source height (`ddir=-1` nudges DOWN if blocked), taps drop down. Don't route trunks ABOVE the cluster (that made the entry go UP/backward).
- **HARD BUG (cost a corrupt-eval round): `dissolve_reroutes` `back()` used `l.to_node is node`** — `is` FAILS on bpy wrappers after save/reopen, so back() found no links → returned None → spine severed (links 81→22, geo→0 verts). It only "worked" during the original in-session rollout because wrappers were identity-stable. **FIX: `l.to_node == node`** (`==` works, `is` doesn't — same gotcha as frame `.parent`). To bisect "which pass broke eval", run each pass then re-snap (selfcheck first that a no-op re-snap matches itself).
- **Run order now:** snapshot baseline (BEFORE any mutation) → dissolve → tidy_layout(cascade) → localize GIs → place_output_rightmost → `route_branches` → route_around_nodes → declutter → verify (OFF index-strict + ON same-set) → save only if ok.
- Tool runs a subset via argv: `blender --background --factory-startup --python geonode_route_tidy.py -- GN_Taper GN_Bend`.
- **Remaining ~7/10 limit (user accepted):** local Group Input nodes still fan out as short DIAGONAL stubs (GIs are excluded from `route_branches`) and a few cross; orthogonalizing GI fan-outs through the same shared-branch logic is the biggest lever to reach ~9 but was deferred. Center-cluster vertical lanes can still read as one thick band.

**RELOCATED + TIGHTENED (2026-07-02):** the tool moved to `Blender/Addons/LLMGeonodePipeline/tidy_layout.py` (git-mv from `Geonodes/geonode_route_tidy.py`) and is now importable (`tidy_and_route(ng)`, `process_file(gate=…)`; the batch loop is under `__main__`). **The old "generous 300px / row_gap 175 / band_gap 230" guidance is REVISED DOWN:** defaults are now `row_gap=55, band_gap=120` — the 175/230 values sprawled badly (user image-diff: `GN_NormalTransfer` was ~2126 tall/aspect 0.86; tightened to ~1300/0.52 with the SAME frame-band + orthogonal-routing structure). Tighter is SAFE because the adaptive lane router (`_vlane`/`_hlane`) still fits — verified R1/R2/R5 all pass at tight spacing on BOTH a simple graph and the gizmo-heavy `GN_Wave`. **New verification layer `layout_audit.py` + `run_pipeline.py`** (same folder): `run_pipeline -- <GN_X>` applies tidy then gates the save on geometry-unchanged AND audit rules. **Rule policy (single source of truth `layout_audit.BLOCKING/ADVISORY`): only R1 (no-overlaps) + R2 (reroutes-clear) BLOCK a save; R3 (left-to-right), R4 (frames-labeled), R5 (row-clearance) are ADVISORY.** R3 is advisory on purpose: feedback/preview topologies (a deformer's `Set Position` → preview `Switch` / gizmo `Join` placed upstream by longest-path layering) have LEGITIMATE backward links and can never reach zero — `GN_Wave` has 2 and is otherwise perfect. See skill `geonode-layout-mcp` and [ST3E geonode modifier — build recipe, roster, publish checklist](asset-checklist.md).

**Compact fan-out routing (2026-07-02, user image-diff — wanted image-2 tight reroutes):** `_hlane` (the horizontal-trunk lane allocator in `route_branches`) was DOWN-only (`ddir=-1`), so a fan whose trunk collided with its own target nodes at source height got shoved ~400px BELOW a whole lower row (Object Info/Sample) and looped back up — an ugly deep detour. FIX: make `_hlane` **bidirectional** — search both ways from `hy0`, take the NEAREST clear lane (prefer `ddir` on ties). Now the trunk hops a few px UP into the thin header gap between the frame label and the top node row and taps down — compact bus right at the row. Verified: `GN_NormalTransfer` Mask-Source fan went from y-1545 → y-1089; R1/R2 still pass; `GN_Wave` gizmo fans unregressed. The long INTER-BAND vertical drops (sources at top of band 1 → targets in band 2 below) are inherent to vertical band-stacking and are NOT changed by this (they use `_vlane`, not `_hlane`) — shortening them would need band-height reduction, not routing.

**Nested-staircase node entries (2026-07-02, user image-diff — subway-map principle):** the user's north star — you must trace which station→which via which line; lines/reroutes/nodes almost never intersect; reroutes build AROUND nodes; keep H/V; a track may split from a shared source but stays readable. Concrete defect they flagged: multiple wires entering ONE node (e.g. 3 field wires into the Index-Switch "Mask Source": Index/Item_1/Item_2) all had their entry reroute parked at `node_y-35` → piled on ONE horizontal row → taps crossed, unreadable. FIX = new pass `route_into_nodes` (runs BEFORE `route_branches`, so rerouted links become source→reroute→reroute→target and route_branches skips them): group cross-band single-target links by TARGET node; for ≥2 entries, sort by target-socket Y and route a nested staircase — entry reroute at each SOCKET's Y (staggered, via new headless-safe `_socket_y(node,sock,is_input)`: outputs stack below header, inputs stack in lower part), lanes nested so TOPMOST socket → lane NEAREST the node (`base_x - k*30`), lower sockets further left → taps nest without crossing. `_route_v` also switched to `_socket_y` for both ends so single entries are pure-horizontal too. New ADVISORY audit rule **R6_entries_staggered**: flags any node whose incoming reroutes share a Y (within `ENTRY_Y_TOL=10`). Verified: GN_NormalTransfer Index@x800(nearest)/Item_1@770/Item_2@740 staggered, R6 PASS; GN_Wave unregressed (node-entries=0). The stale on-disk roster files (tidied pre-improvement) trip R6/R3 as advisories until re-run through `run_pipeline`.

**Subway-map round 2 (2026-07-02) — no circling, reroutes framed, no frame overlap:**
(1) **Fan circling** = SPREAD-fan per-column tap used `_vlane` (shifts LEFT on clash) → a later tap landed left of an earlier one → wire looped back under the intervening node. FIX: SPREAD trunk marches strictly RIGHT — `tap_x = max(target_x-30, last_x+28)`, shift RIGHT only to clear nodes; taps drop at `_socket_y`. Second cause: `route_into_nodes` was stealing ONE branch of a multi-target source fan (fragmenting it) — FIX: skip links whose source socket has `src_fanout>1` (leave whole fans to route_branches). (2) **Reroutes framed by function** = new final pass `frame_reroutes` parents each reroute to the comment frame whose NODE bbox (±60px margin) contains it; gap reroutes stay unparented. Frames are at (0,0) during the script so parenting needs no coord fix; on reload frames shrinkwrap to include framed reroutes (band-stacked frames only grow in X/within-band → no new overlap). Cross-function wires get a framed EXIT reroute added just right of the source (`E` in `_route_v`/`route_into_nodes`) + framed ENTRY at target + gap bends = user's "≥2, one framed per function, extras to dodge nodes". (3) **R7_no_frame_overlap** audit rule, now BLOCKING: frame abs-bboxes (incl. framed reroutes) must not partially overlap; full nesting (one inside another) allowed. Roster now audits R1/R2/R7 blocking, R3/R4/R5/R6 advisory. Verified GN_NormalTransfer: fan 1010→1050→1285 (monotonic), 18/29 reroutes framed, R7 pass, geometry unchanged.

**CRITERIA PROMOTED TO REPO (2026-07-09):** the canonical creation+tidying criteria now live checked-in at `Blender/Addons/LLMGeonodePipeline/GEONODE_CRITERIA.md` (user request; `Blender/Geonodes/CLAUDE.md` is a stub pointing at the geonode-layout-mcp skill, which must be invoked for ANY geonode create/tidy/alter work) — tidying is held to the same bar as creation. `layout_audit.py` gained advisory rules **R8 nodes-framed** (function isolation), **R9 unique-socket-names** (duplicate display names miswire by-name scripting — see [Geonode sockets, interfaces and menus](sockets-and-menus.md#feedback_gn_link_rewire_gotchas); NB top-level interface items report an implicit ROOT panel with empty name, so "in a panel" must require a NAMED panel), **R10 sockets-in-panels**, **R11 no-needless-reroutes**. `tidy_layout.py` now keeps DIRECT wires for adjacent targets (`_adjacent_direct`: dx<300, dy<240, straight path clear — per-branch even inside fans; constants kept in sync with the audit, and audit `_est_h` matches engine `est_h` incl. the unlinked-vector +54/socket term so headless estimates agree). For garbled unframed graphs the skill's workflow is: AI-isolate functions into labeled frames FIRST (capture → frames at loc(0,0) → parent nodes), fix interface (dedupe names, panels), THEN deterministic tidy + audit.

**SOCKET-ANCHORED FEEDERS + R7 ENFORCEMENT (2026-07-10, user before/after image-diff on GN_Wave "Displace Direction"):** the engine top-aligned every column node, so feeders of a TALL consumer (Index Switch — inputs span 100s of px) sat in one row with wires diving across the frame, and a mid-row node (`unit normal`) blocked the straight Menu→Index path forcing an over-the-top detour. The user's hand-fix defined two rules: (1) **a feeder aligns its OUTPUT to the Y of the input SOCKET it feeds** — `tidy_layout` now sweeps band columns right-to-left computing each feeder's anchor from `_socket_y` of its targets (greedy top-down within the column, never overlapping); staggered feeder rows, short direct wires, ~3× more compact frames. (2) **Move the blocker, don't detour the wire** — the low-anchored feeder vacates the straight path, so `_adjacent_direct` keeps the link direct. Fallout fixed the same day: compacter bands exposed that **post-layout extensions (below-left localized GIs, exit reroutes) corner-cross neighbour frame boxes at diagonal band junctions through EMPTY space** → new `separate_frames` end pass (audit-identical partial-overlap test, shifts the lower frame's contents straight DOWN — down-only so vertical lanes stay orthogonal; nesting untouched), and `layout_audit` R7 now truly FAILs (was WARN despite being in BLOCKING — masked two pre-existing corner-crossings in GN_NormalTransfer/GN_RadialArray). Verified: 5-file dry-run + GN_Wave all green, geometry unchanged.

**GI-FAN RULES (2026-07-09, user before/after image-diff on EdgeDestruct "Damage Noise Field"):** the engine's `route_around_nodes` had detoured Group-Input param links over the frame top as ~7 stacked 24px lanes crossing the frame LABEL. The user's hand-fix defined the standard: (1) **GI param fans stay straight direct wires, always** — all routing passes now exempt `NodeGroupInput` sources; a long parallel dashed ribbon is the desired look. (2) **GI placement = below-left of its consumers** (ribbon sweeps the clear corridor); a **single consumer ≳900px right of the rest gets its OWN small GI parked directly left of it** (localize_group_inputs now x-clusters at 900px). (3) **GI label = the interface PANEL name** when all carried sockets share one named panel (user labeled theirs "Edge Damage"), else `In: <frame>`. (4) `col_gap` 85→130 — the user widened columns considerably; tight columns cramp frames and leave no clear corridors. Verified on GN_Wave: reroutes 46→36, around 7→2, all rules pass, geometry unchanged.

<a id="feedback_gn_wire_lane_legibility"></a>

## Wire lane legibility

*Node-graph wires must each be their OWN visible line — no two lanes on one X, none on a node border; a router may never \"give up and accept a clash\*

A node graph can pass every structural layout rule and still be unreadable, because
structural rules look at NODES and the defect is in the WIRES. Found 2026-08-19 by a user
image-diff on `SH_ScreenCavity`: the user had to *drag reroutes aside* to discover that one
apparent wire was three separate signals. Measured on the saved file — 10 exactly-collinear
wire pairs (0.0px apart, up to 3453px of shared extent) and 13 vertical runs sitting 2.0px
off a node's right border, merged with the node outline. `layout_audit` R1–R11 all PASS.

**Why:** two failure shapes, both easy to reintroduce in any router.
1. **A reservation ledger with holes.** Lanes were reserved in bare lists that only two
   helpers fed; the spread-fan path derived its drop lane from the target's own X and
   neither consulted nor recorded anything, so two fans over one node column landed on the
   same line *by construction*.
2. **"Give up and accept a known clash."** Three code paths committed to a position they
   had already measured as colliding when their bounded search ran out. The worst had its
   escape loop guarded by the *target's* right edge instead of the *blocking* node's, so it
   stopped walking while still inside the clearance pad — 2px from the border.

**How to apply:**
- Every drawn segment goes through ONE allocator. Segments the caller has no freedom over
  (socket stubs, trunk hops) are still *recorded*, or later allocations are blind to them.
- A router's last resort is a **jog that maximises separation**, never a snap onto an
  occupied lane. Worst case must be a visibly parallel wire, not a hidden one.
- Lanes sit in the **centre of the corridor** between node columns, ≥30px clear of any body.
  A 16px "clearance" still reads as part of the node's outline.
- Run a repair pass **last**, on the graph as actually *drawn* — passes that move nodes
  (declutter, frame separation) run after routing and can recreate the collision.
- Enforce it deterministically: `layout_audit` R12 (no two wires <12px apart sharing >40px
  of extent) and R13 (no lane within 22px of a node border), both BLOCKING.
- Verify a re-route by diffing **logical connectivity** — trace every real-node input back
  through reroute chains to its originating socket, before vs after. Node positions change;
  the connection set must be identical.
- Check the save gate actually fires. The shader build tested `rep.get(rule, {}).get("fail")`
  — a key the audit never emits — so "BLOCKING FAILURES → not saving" was unreachable and
  the defective file saved anyway.

**Defect shapes to check for (all found by MEASURING a specific failure, never by reading
the code — every hypothesis formed by reasoning alone was wrong):**
- A daisy-chained bus that chains to the topmost row first **retraces its own line** when
  the source sits below its targets. Chain monotonically AWAY from the entry point, both
  directions (a reroute output may fan, so splitting is free).
- A repair pass that slides a column sideways **moves trunk taps** and can push one past
  its predecessor, reversing a trunk hop. Any move needs a window that preserves the
  ordering and minimum length of every run attached to the group.
- **Direct (unrouted) wires are drawn segments too.** Seed them into the ledger before
  routing, mirroring EVERY condition under which the router leaves a link direct — a
  same-frame single-target link stays direct at ANY length, not just short ones.
- A leg whose Y is pinned to a source socket but which runs thousands of px is a **lane,
  not a stub** — allocate it, or drop to an allocated one when its line is taken.
- Post-routing passes that nudge nodes off obstacles must **remember the rows they used**,
  or two escapees from one node land on an identical line.

**Density limit:** machine-generated mega-graphs (GN_Mosaic 2807 nodes/1723 reroutes,
GN_TileableMeshNoise 1813/1125) cannot satisfy R12/R13 — there is no corridor left. The
gate correctly leaves them untouched; they need a layout-aware generator, not a tidier.

Engine + rules: `Blender/Addons/LLMGeonodePipeline/` (`tidy_layout.Lanes`,
`separate_wire_lanes`, `layout_audit` R12/R13); criteria §3 in `GEONODE_CRITERIA.md`.
Related: [Geonode layout](layout.md#feedback_gn_node_layout_spacing), [ST3E geonode modifier — build recipe, roster, publish checklist](asset-checklist.md).

<a id="feedback_geonode_pipeline_tidies_every_group"></a>

## The pipeline tidies every group, helpers included

*Every node group a geonode owns must be tidied and audited, not just the tree named after the file — and the tidy engine is not idempotent, run it twice*

User, 2026-09-21, on `GNG_AmbientOcclusion` shipping as an untidied pile:
*"generally speaking if you have a group it also needs to be tidy."*

**Why:** a node group is a graph the user opens and reads. "The tool is tidy" is
false while one of its helper groups is a heap at the origin. `run_pipeline.py`
had only ever laid out `bpy.data.node_groups[<file name>]`, so every `GNG_*`
helper in the library was skipped in silence — the audit never even looked at it.

**How to apply:**
- `tidy_layout.own_trees(ng)` walks `GeometryNodeGroup` nodes transitively and
  returns the main tree plus every LOCAL group it instances; `process_file` tidies
  all of them and `run_pipeline._audit_gate(trees)` audits each — a BLOCKING
  failure in ANY tree blocks the save. Linked groups are skipped on purpose (the
  .blend that owns a group tidies it); unreachable groups are somebody else's.
- **Run the tidy twice.** The engine is NOT idempotent: `node.dimensions` is only
  valid post-draw, so pass 1 is what gives frames their real extents and pass 2 is
  measurably better, then stable (GN_AmbientOcclusion 5 backward links → 0, its
  helper 10 → 2, unchanged on pass 3).
- Authoring a **Repeat / Simulation Zone**: give the zone input and output their
  OWN frames, created before and after the body frames. A frame is ONE layout
  band, so one frame around both ends drags the whole loop body left of its own
  input and every entry link reads backwards (R3 went 10 → 3 on that fix alone).

Written into the canonical criteria as **criterion 5 "Every group is a graph"**
(`Blender/Addons/LLMGeonodePipeline/GEONODE_CRITERIA.md`), the suite README and
the `geonode-layout-mcp` skill. See [Geonode techniques](techniques.md#project_gn_ambient_occlusion),
[Geonode layout](layout.md#feedback_gn_node_layout_spacing), [Geonode layout](layout.md#feedback_gn_wire_lane_legibility).

**Known backlog this exposed** (nothing rewritten yet, user's call):
- BLOCKING R1/R2 in helpers: `GNG_ObjectDirection` in GN_Bend + GN_ShearGeometry
  (the 9-node variant only — the 5-node one elsewhere passes, so the same helper
  has drifted between files), `GN_InsetFaces` in GN_MeshFromImage, and most of
  GN_CellFrac's imported `G_*` groups.
- **~12 files are skipped by the pipeline entirely** because no tree is named
  after the file (GN_ExtrudeSelection, GN_InsetFace, GN_Mirror_Groupable,
  GN_SimpleTransform, GN_Solidify2, GN_SplitByAttribute, GN_CollectionInstancer,
  GN_DisplaceByImage, GN_EdgeDestruct*, GN_VariousTest, GN_AttributeFunctions_4.5,
  GN_treeGenerator_03). `process_file` hard-requires `node_groups[fname]`.
