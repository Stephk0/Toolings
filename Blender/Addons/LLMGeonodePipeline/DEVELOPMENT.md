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
