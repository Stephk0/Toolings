# LLM Geonode Pipeline — developer notes

Implementation and maintenance notes. User docs: [README](README.md).

## Folder layout

```
LLMGeonodePipeline/
├── README.md
├── addon/                     # the Blender MCP bridge extension (install this)
│   ├── __init__.py            # socket server + main-thread queue + 7 handlers
│   ├── compat.py              # version-specific names (blf/gpu/screenshot)
│   ├── layout.py              # deterministic layered layout (MCP autolayout_pass)
│   ├── blender_manifest.toml
│   └── test_layout.py         # headless tests (not shipped in the zip)
├── server.py                  # MCP server (FastMCP) — forwards the 7 tools over the socket
├── pyproject.toml             # MCP server deps (mcp[cli], pillow)
├── tidy_layout.py             # DEFAULT engine: deterministic tidy + orthogonal routing (importable + CLI)
├── layout_audit.py            # shared verifier: scores a graph against rules R1–R5
├── prepare_capture.py         # opens/frames a node editor + starts the server (MCP prerequisite)
├── run_pipeline.py            # ORCHESTRATOR: tidy (default) → verify BOTH goals → save
├── group_frames.py           # Setup for huge graphs (GUI only): big frames → GNG_* helper groups
├── polish_layout.py           # optional 2nd pass (GUI only): P1 orthogonal wires, measured AS DRAWN
├── CHANGELOG.md
└── distribution/
    ├── LLMGeonodePipeline_v1.2.0.zip   # ← install this extension
    └── archive/
```

## The two goals (verified together)

`run_pipeline.py` applies the default `tidy_layout` and **only saves if both hold**:

- **Goal 1 — routing correctness:** the mesh output is byte-identical after
  layout (tidy only moves nodes / adds reroutes; it must never change geometry).
- **Goal 2 — readability rules (`layout_audit`):**
  - **R1 no overlaps** — no two real-node bounding boxes overlap *(BLOCKING)*
  - **R2 reroutes clear** — no reroute sits inside a node body *(BLOCKING)*
  - **R3 left-to-right** — every logical link (traced through reroutes) flows +x *(advisory)*
  - **R4 frames labeled** — every frame carries a label *(advisory)*
  - **R5 row clearance** — ≥70px between nodes that share a vertical span *(advisory)*
  - **R12 no collinear wires** — no two wires drawn on top of each other *(BLOCKING)*
  - **R13 wires clear of nodes** — no lane painted along a node's border *(BLOCKING)*

**Blocking vs advisory** (policy in `layout_audit.py`: `BLOCKING` / `ADVISORY`):
R1+R2 are structural integrity — a failure means the graph renders *broken*
(overlapping bodies / hidden reroutes), so the file is **not saved**. R12+R13
join them because a wire drawn on top of another wire, or on a node's outline,
is just as broken — the graph *looks* connected differently than it is. R3–R5 are
readability quality and never block. R3 is advisory on purpose: feedback/preview
topologies (a deformer's `Set Position` feeding a preview `Switch` / gizmo `Join`
placed upstream) have legitimate backward links and can never hit zero.

The gate fires for real: re-running tidy on already-routed output once overlapped a
node (R1), and the pipeline refused to save — the two engines guard each other.

### Every group the tool owns, not just the outer tree

**A node group is a graph the user opens and reads, so it is held to the same
R1–R13 bar as the tree that instances it.** `tidy_layout.own_trees(ng)` walks the
`GeometryNodeGroup` nodes transitively and `process_file` tidies *every* local
group it finds; `run_pipeline`'s gate audits each one and **a blocking failure in
any helper blocks the save**. Two deliberate exclusions:

- **Linked groups are skipped.** They belong to the `.blend` they live in (that
  file tidies and audits them), and a linked datablock cannot be edited from here
  anyway. So `GN_VertexDataComposer` tidies itself + `GNG_VertexChannel`, and
  leaves the linked `GNG_AmbientOcclusion` to `GN_AmbientOcclusion.blend`.
- **Unreachable groups are left alone** — third-party or leftover datablocks
  sitting in the file that the tool does not instance are not ours to rewrite.

This was added after `GNG_AmbientOcclusion` shipped as an untidied pile: the
pipeline had only ever laid out `bpy.data.node_groups[<file name>]`.

**The engine is not idempotent — run it twice.** The second pass reliably improves
R3/R6, because the first pass is what gives the frames their real drawn extents
(`node.dimensions` is only valid post-draw). `GN_AmbientOcclusion` went 5 backward
links → 0, and the helper 10 → 2, on the second run, then held steady on the third.

**Open backlog** (found when helpers were first audited, nothing rewritten yet):
- BLOCKING R1/R2 in helpers: `GNG_ObjectDirection` in GN_Bend + GN_ShearGeometry (the
  9-node variant; the 5-node one elsewhere passes, so the helper has drifted between files),
  `GN_InsetFaces` in GN_MeshFromImage, most of GN_CellFrac's imported `G_*` groups.
- About 12 files are skipped entirely because no tree is named after the file
  (`process_file` requires `node_groups[fname]`): GN_ExtrudeSelection, GN_InsetFace,
  GN_Mirror_Groupable, GN_SimpleTransform, GN_Solidify2, GN_SplitByAttribute,
  GN_CollectionInstancer, GN_DisplaceByImage, GN_EdgeDestruct*, GN_VariousTest,
  GN_AttributeFunctions_4.5, GN_treeGenerator_03.

## Polish pass (`polish_layout.py`)

`tidy_layout` routes against `_socket_y`, a headless estimate that ignores vector
sliders, node buttons (dropdowns), group panels and multi-input sockets. Measured on the
first three graphs polished (2026-09-26): 34–65 kinked reroute links per tree, entries up to
88px off. `route_around_nodes` and `_route_back` add kinks by design (stubs at a fixed
`_ymid`).

- **Socket positions.** No RNA for them, so `SocketLocator` reads
  `bNodeSocket.runtime->location` with ctypes. The `runtime` offset comes from the file's
  own SDNA (a `copy=True, compress=False` save to temp); the `location` offset inside the
  runtime is calibrated on the tree's reroutes, whose socket position equals the reroute's
  location. Values are in view space: node space × `ui_scale` (offset 24 on 5.0). Any
  mismatch raises `NotDrawn` and nothing is touched. SDNA padding is 4-aligned relative
  to the `SDNA` block start, not the file offset — aligning to the file broke the parse on
  every file whose block happened to start unaligned.
- **CLI gate is "no worse than before"**: the blocking scores are taken per tree after the
  first draw and compared after the pass. A failure the tidy left behind doesn't stop the
  save. Files with no tree named after them fall back to every local modifier tree.
- **Only valid after a draw.** `draw_tree` pins the tree in a node editor and forces
  `wm.redraw_timer`. Hence GUI only; the CLI registers a timer and `os._exit`s when done.
- **P1** (`measure`): a link touching a reroute that is off-axis by more than `TOL` in both
  X and Y. `entry` = reroute→socket, `exit` = socket→reroute, `lane` = reroute→reroute.
- **Fix, per horizontal run** (reroutes chained by H links): if all touched sockets agree,
  slide the run onto that Y (only Y moves, so V legs stay vertical). With disagreeing
  sockets, slide only within `SNAP_MAX` (never drag a route-around detour back through what
  it avoided) and **jog** the rest: a new reroute at the member's X and the socket's Y. A jog
  whose vertical leg would hug the node pulls the run end out to `JOG_CLEAR`, then steps out
  by `JOG_STEP` for up to `JOG_TRIES` if it lands on another lane (R12).
- **Gate, per run** (`LocalGate`): kept only if P1 drops and no BLOCKING rule gets worse;
  otherwise reverted from its `_Journal`. Scored only on the links incident to the touched
  reroutes (R2, R7, R12, R13, P1) against cached segments and frame boxes — real nodes never
  move, so R1 can't change. Same `layout_audit` helpers and thresholds; the CLI's full audit
  at the end stays the authority. A full re-audit per attempt took >30 min on GN_Mosaic. `logical_links` is compared once at the end (mismatch →
  revert all), the CLI also checks evaluated geometry before saving.
- **Links are held as name/identifier keys** — a wrapper kept across a jog and its revert
  points at a removed link, and a socket wrapper taken off a removed link can make
  `links.new` return `None` (see `Knowledge/bpy-api-gotchas.md`).

## Splitting huge graphs (`group_frames.py`)

Uses `node.group_make` (needs a drawn node editor), one top-level frame at a time, with
`--min` function nodes (30). Zone safety: a zone's body is everything forward-reachable
from its input up to its paired output; a frame is grouped only if it holds all of it or
none of it. Geometry is compared after every frame and a changing grouping is undone with
`group_ungroup`. Found on GN_Mosaic (2026-09-27): grouping "Contour Rows" emptied the
output (cause not investigated — the frame stays ungrouped) and `group_make` returned
CANCELLED for "Shatter Build". Neither file passed the blocking rules before grouping;
after grouping + two tidy passes + polish both are strictly better on every blocking count
(Mosaic R12 841→586, R13 361→274; TileableMeshNoise R12 364→291, R13 406→120), saved
against that pre-grouping baseline rather than the zero-failure gate.

## Customizing

The suite is meant to be edited:
- **Change the default layout** → edit `tidy_layout.py` (or swap the engine call in
  `run_pipeline.py`).
- **Change the rules / thresholds** → edit `layout_audit.py` (`MIN_CLEAR`,
  `BLOCKING_RULES` live in `run_pipeline.py`).
- **Change the AI workflow** → edit the `geonode-layout-mcp` skill.

Because `layout_audit` is the single source of truth for both engines, editing a
rule there automatically re-gates the deterministic pipeline *and* the guidance
the MCP workflow checks against.

## Version notes

Targets Blender **4.2 LTS**–**5.x** (tested 5.0). Version-specific names live in
`addon/compat.py`. `tidy_layout.py` and `layout_audit.py` both trace reroutes by
`.name` (bpy `is` is unreliable after a file reopen).

## Changing the AI workflow

The agent-side workflow lives in the `geonode-layout-mcp` skill (`.claude/skills/`); the criteria it enforces are in [GEONODE_CRITERIA.md](GEONODE_CRITERIA.md).
