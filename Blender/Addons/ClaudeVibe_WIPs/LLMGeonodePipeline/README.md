# LLM Geonode Pipeline

**Version:** 1.1.0 · **Blender:** 4.2 LTS – 5.x (tested 5.0) · Windows

A suite for **reading and laying out Blender Geometry Nodes graphs**, combining two
engines that verify each other against one shared definition of "a good layout":

1. **`tidy_layout`** — a deterministic pipeline (layered columns + orthogonal
   reroute routing + group-input localization), geometry-safety-checked. This is
   the **default** applied to every graph.
2. **GeoNode Layout MCP** — a socket bridge that lets an AI read a graph as an
   annotated screenshot + structured table and rearrange it by *visual* judgment
   (`capture_graph → apply_layout`). For interactive / non-standard arrangements.

Both are scored by the same **`layout_audit`** rules, so they can't drift apart.

## Folder layout

```
LLMGeonodePipeline/
├── README.md
├── addon/                     # the Blender MCP bridge extension (install this)
│   ├── __init__.py            # socket server + main-thread queue + 3 handlers
│   ├── compat.py              # version-specific names (blf/gpu/screenshot)
│   ├── layout.py              # deterministic layered layout (MCP autolayout_pass)
│   ├── blender_manifest.toml
│   └── test_layout.py         # headless tests (not shipped in the zip)
├── server.py                  # MCP server (FastMCP) — forwards the 3 tools over the socket
├── pyproject.toml             # MCP server deps (mcp[cli], pillow)
├── tidy_layout.py             # DEFAULT engine: deterministic tidy + orthogonal routing (importable + CLI)
├── layout_audit.py            # shared verifier: scores a graph against rules R1–R5
├── prepare_capture.py         # opens/frames a node editor + starts the server (MCP prerequisite)
├── run_pipeline.py            # ORCHESTRATOR: tidy (default) → verify BOTH goals → save
├── CHANGELOG.md
└── distribution/
    ├── LLMGeonodePipeline_v1.1.0.zip   # ← install this extension
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

**Blocking vs advisory** (policy in `layout_audit.py`: `BLOCKING` / `ADVISORY`):
R1+R2 are structural integrity — a failure means the graph renders *broken*
(overlapping bodies / hidden reroutes), so the file is **not saved**. R3–R5 are
readability quality and never block. R3 is advisory on purpose: feedback/preview
topologies (a deformer's `Set Position` feeding a preview `Switch` / gizmo `Join`
placed upstream) have legitimate backward links and can never hit zero.

The gate fires for real: re-running tidy on already-routed output once overlapped a
node (R1), and the pipeline refused to save — the two engines guard each other.

## Usage

### Default automated path — `run_pipeline.py`
```bash
blender --background --factory-startup --python run_pipeline.py -- GN_NormalTransfer [GN_Bend ...]
```
Opens each `Geonodes/<name>.blend`, tidies it, verifies both goals, saves if both pass.

### Just tidy (no audit gate) — `tidy_layout.py`
```bash
blender --background --factory-startup --python tidy_layout.py -- GN_NormalTransfer
```
Its `TARGETS` list (top of the file) is the default roster when no names are passed.

### Just audit an existing graph — `layout_audit.py`
```bash
blender --background --factory-startup --python layout_audit.py -- GN_NormalTransfer
# exits non-zero if any blocking rule fails (CI-gateable)
```

### Interactive / AI-judged layout — the MCP
1. Install `distribution/LLMGeonodePipeline_v1.1.0.zip`
   (`Preferences ▸ Add-ons ▸ Install from Disk…`), enable it, and **Start** the
   server from the Node Editor N-panel ("GN Layout MCP" tab, port `9877`).
2. Point your MCP client at `server.py` (registered as `geonode-layout` under the
   `Toolings` project in `~/.claude.json`).
3. Get an editor ready with `prepare_capture.py`, then loop
   `capture_graph → apply_layout → capture_graph (verify)`. Run `layout_audit`
   afterward to confirm the same rules. Full workflow: the **`geonode-layout-mcp`**
   project skill.

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

## MCP server setup

```bash
cd LLMGeonodePipeline
uv pip install -e .        # or: pip install mcp[cli] pillow
```
`~/.claude.json` entry (under the `Toolings` project):
```jsonc
"geonode-layout": {
  "command": "…/uv.exe",
  "args": ["run","--no-project","--with","mcp[cli]","--with","pillow","python",
           "D:/…/LLMGeonodePipeline/server.py"],
  "env": { "GNLAYOUT_PORT": "9877" }
}
```

## ⚠️ Security note

The bridge executes **writes against the live `.blend`** (moves nodes) and
`run_pipeline`/`tidy_layout` **save files in place**. Run only against work you can
recover (saved / versioned); the socket binds `localhost` only.

## Version notes

Targets Blender **4.2 LTS**–**5.x** (tested 5.0). Version-specific names live in
`addon/compat.py`. `tidy_layout.py` and `layout_audit.py` both trace reroutes by
`.name` (bpy `is` is unreliable after a file reopen).
