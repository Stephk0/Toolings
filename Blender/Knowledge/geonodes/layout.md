# Geonode layout

Traps in scripting node layout. The layout **rules** (R1–R13, spacing, frames, Group Input fans,
subway wiring) live in `Blender/Addons/LLMGeonodePipeline/GEONODE_CRITERIA.md`; the tidy engine's
internals in that folder's `DEVELOPMENT.md`. Live flow: skill `geonode-layout-mcp`.

- [Layout scripting traps](#feedback_gn_node_layout_spacing)
- [Wire lane legibility](#feedback_gn_wire_lane_legibility)
- [The pipeline tidies every group, helpers included](#feedback_geonode_pipeline_tidies_every_group)
- [Reading drawn socket positions (no RNA for them)](#socket_runtime_location)

<a id="feedback_gn_node_layout_spacing"></a>

## Layout scripting traps

*Moving nodes and relinking wires is "lossless" only if you guard multi-input order, wrapper identity and the baseline snapshot*

**How to apply:**
- **Absolute placement:** set every `NodeFrame.location = (0,0)`; a child's `.location` is then
  absolute (child locations are frame-relative). `node.location` is the TOP-LEFT corner.
- **Sizes headless:** `n.width` is reliable; `n.dimensions` is 0 until the editor draws. That is
  why the engine is not idempotent (run it twice) and why `polish_layout.py` exists.
- **Relinking into a multi-input socket** (Join Geometry) appends the link at the END → output
  vertex order changes (same set, shifted indices — breaks index/UV/shape keys). `socket.links`
  order is not reliable. Snapshot each multi-input's sources (traced through reroutes) and
  re-stack them afterwards (`tidy_layout.multi_input_order` / `restore_multi_input_order`).
- **Compare bpy wrappers with `==`, never `is`** — `node.parent is frame` and `l.to_node is node`
  fail after save/reopen (a reroute dissolve severed the spine: links 81→22, 0 verts). See
  [bpy wrappers](../bpy-api-gotchas.md#feedback_blender_no_id_on_bpy_wrappers).
- **Mutating `ng.links` invalidates other link wrappers** — collect
  `(from_node, from_socket.identifier, to_node, to_socket.identifier)` first, then mutate and
  re-fetch sockets by identifier. See [stale sockets](../bpy-api-gotchas.md#links_new_stale_socket)
  and [relink by identifier](sockets-and-menus.md#feedback_gn_link_rewire_gotchas).
- **Take the geometry baseline BEFORE any mutation.** A baseline taken after a broken pass matches
  itself and "passes". To bisect which pass broke eval, re-snapshot after each pass (check first
  that a no-op re-snapshot matches).
- **When `run_pipeline` refuses to save** a big graph over a few leftover reroutes inside node
  bodies (R2) or lane clashes (R12/R13): run a nudge loop — audit → shift each offending reroute
  clear of its blocker (delta in absolute space, walking frame parents) → re-audit → save gated
  on the blocking rules AND geometry unchanged. Don't loosen the gate.
- Verify with the evaluated-geometry gate in every relevant state (preview on and off,
  index-strict). Visual quality can't be checked headless — the node editor must be screenshotted.

<a id="feedback_gn_wire_lane_legibility"></a>

## Wire lane legibility

*A graph can pass every node rule and still be unreadable — the defect is in the wires; lessons for anyone writing a router*

Rules: GEONODE_CRITERIA §3 (R12 no collinear wires, R13 no lane on a node border, both blocking).
Found on `SH_ScreenCavity`: 10 exactly collinear wire pairs and 13 runs 2px off a node border
while R1–R11 all passed.

**How to apply (router design):**
- Every drawn segment goes through ONE allocator; segments with no freedom (socket stubs, trunk
  hops, direct wires) are still recorded, or later allocations are blind to them.
- Never "give up and accept a known clash" — the last resort is a jog that maximises separation.
- Run the repair pass last, on the graph as drawn — node-moving passes can recreate collisions.
- A daisy-chained bus must chain monotonically away from its entry point or it retraces itself.
- Verify a re-route by diffing logical connectivity (each real input traced through reroutes to
  its source), before vs after.
- Check the save gate can fire: a build once tested a dict key the audit never emits, so
  "not saving" was unreachable.
- Every hypothesis formed by reading the router code was wrong — measure the failing file.

**Density limit:** machine-generated mega-graphs (GN_Mosaic ~2800 nodes) have no corridors left
for R12/R13; the gate correctly leaves them untouched.

<a id="feedback_geonode_pipeline_tidies_every_group"></a>

## The pipeline tidies every group, helpers included

*Every local group a geonode instances is tidied and audited, and the engine must run twice*

Rule and mechanics: GEONODE_CRITERIA criterion 5 and `LLMGeonodePipeline/DEVELOPMENT.md`
("Every group the tool owns"). Open backlog is listed there too.

**How to apply:** give a Repeat/Simulation Zone's input and output their OWN frames — a frame is
one layout band, so one frame around both ends drags the body left of its input (R3 10 → 3).

<a id="socket_runtime_location"></a>

## Reading drawn socket positions (no RNA for them)

*`NodeSocket` has no location property; read `bNodeSocket.runtime->location` via ctypes, only after the editor drew the tree*

Headless socket-height estimates are off by up to 88px (vector sliders, dropdowns, panels).
Verified on Blender 5.0 (`LLMGeonodePipeline/polish_layout.py`).

**How to apply:**
- `runtime` offset in `bNodeSocket`: parse the SDNA of an uncompressed copy
  (`save_as_mainfile(copy=True, compress=False)`); 520 on 5.0. SDNA padding is 4-aligned relative
  to the SDNA block start, not the file offset.
- `location` offset inside runtime: calibrate on reroutes (a reroute's socket sits at its
  location); 24 bytes on 5.0.
- Values are in view space: **node space × `preferences.system.ui_scale`** — same for
  `region.view2d.view_to_region`.
- Only after a draw: pin the tree (`space.pin = True; space.node_tree = ng`) and run
  `wm.redraw_timer(type='DRAW_WIN_SWAP')`. Not available in `--background`.
- `bpy.ops.node.view_selected` did nothing from a timer; `view2d.zoom_border` + `view2d.pan` worked.
