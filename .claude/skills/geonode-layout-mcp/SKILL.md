---
name: geonode-layout-mcp
description: The entry point for ANY Geometry Nodes work — creating, tidying, or otherwise altering a geonode. Loads the ST3E criteria (GEONODE_CRITERIA.md) and the GeoNode Layout MCP flow (capture → autolayout/reason → apply → verify → audit R1–R11). Use whenever a geonode is created, tidied, refactored, or edited, when the user mentions "layout MCP", "capture_graph / apply_layout / autolayout_pass", "tidy the nodes", or when a newly-authored geonode needs its graph laid out and checked.
---

# GeoNode work — criteria + Layout MCP

**FIRST: Read the canonical criteria** —
`Blender/Addons/ClaudeVibe_WIPs/LLMGeonodePipeline/GEONODE_CRITERIA.md`.
They apply to creating, tidying, and altering alike (function frames, interface
panels + unique naming, per-function group inputs, subway wiring, deformer
conventions, publishing checklist). The criteria deliberately live with the
pipeline — outside the AI config — so they version with the tooling; this skill
is just the trigger that loads them.

An MCP bridge that reads a Geometry Nodes graph as an **annotated screenshot +
structured table** and rearranges it **deterministically**. Layout/readability is
a *visual* judgment the serialized tree can't carry; topology and writes are data.

- **Suite:** `Blender/Addons/ClaudeVibe_WIPs/LLMGeonodePipeline/` — MCP bridge
  (`addon/`, `server.py`) + deterministic engine (`tidy_layout.py`) + shared
  verifier (`layout_audit.py`) + orchestrator (`run_pipeline.py`). Full docs in
  that folder's `README.md`.
- **MCP server name:** `geonode-layout` (configured under the `Toolings` project in
  `~/.claude.json`). Tools: `capture_graph`, `apply_layout`, `autolayout_pass`.
- **Socket:** the addon runs a server on `localhost:9877` inside Blender; start it
  from the Node Editor N-panel ("GN Layout MCP" tab) or `bpy.ops.gnlayout.start_server()`.
- **Default automated path:** for a headless, non-interactive tidy of a published
  geonode, prefer `run_pipeline.py` (below) — it applies `tidy_layout` and gates the
  save on BOTH geometry-unchanged and the audit rules. Use the MCP tools when you
  want AI *visual* judgment (custom, non-layered arrangements).

## Mental model — judge once, write once

1. **`capture_graph`** → one response: annotated image (each node stamped with an
   integer index) **+** a JSON table of `nodes` (index/name/type/`abs_loc`/`dim`/
   `parent`) and `links` (by index).
2. Reason over the whole graph and emit the **entire** new layout at once — or call
   **`autolayout_pass`** for a deterministic left-to-right layered layout.
3. **`apply_layout`** writes every `node.location` in **one batched pass** (absolute
   node space; frames applied before children).
4. *(optional)* **`capture_graph`** again to verify it reads cleanly.

Core loop = **2 round trips**, 3 with a verify. **Never re-capture between writes** —
writes are deterministic, so you already know where you placed everything. The
index is the identity key: use it to refer to one exact node in `apply_layout`.

## Prerequisite — an open node editor

`capture_graph` fails loud (`no NODE_EDITOR area open…`) unless a Geometry Nodes
editor is open showing the target tree. Set that up first with the helper (paste
into the live Blender via blender-mcp `execute_blender_code`):

```python
import sys; sys.path.append(r"D:\Stephko_Tooling\Toolings\Blender\Addons\ClaudeVibe_WIPs\LLMGeonodePipeline")
import prepare_capture; prepare_capture.prepare(tree="GN_NormalTransfer",
    filepath=r"D:\Stephko_Tooling\Toolings\Blender\Geonodes\GN_NormalTransfer.blend")
```
It opens the file, activates the object holding the tree, switches an area to a
framed GN editor, and (re)starts the server. Then call `capture_graph`.

## The layout rules (what "good" means)

After `apply_layout`, verify the result adheres to these — run
`layout_audit.py` (headless: `blender --background --factory-startup
--python layout_audit.py -- GN_NormalTransfer`, or `import layout_audit;
layout_audit.print_report(layout_audit.audit(ng))`):

- **R1 no overlaps** — no two real-node bounding boxes overlap. **(BLOCKING)**
- **R2 reroutes clear** — no reroute sits inside a node body. **(BLOCKING)**
- **R3 left-to-right** — every logical link (traced through reroutes) flows +x. *(advisory)*
- **R4 frames labeled** — every frame carries a label (comment your graph, like code). *(advisory)*
- **R5 row clearance** — ≥ ~70px between nodes that share a vertical span. *(advisory)*
  (Nodes in different vertical *bands* may share x-space without colliding — R1 is
  the real overlap check; R5 only compares nodes that actually share a row.)
- **R6 entries staggered** — no two reroutes feeding the SAME node share a Y. *(advisory)*
  Piled entries = crossing taps you can't trace. `route_into_nodes` prevents this by
  nesting multi-socket entries into a staircase (topmost socket → lane nearest the node).
- **R7 no frame overlap** — frames never partially overlap; full nesting is fine. **(BLOCKING)**
- **R8 nodes framed** — every function node lives inside a labeled frame; Group
  Input/Output buses exempt. *(advisory — the creation criterion "frame + label like code")*
- **R9 unique socket names** — no two interface sockets share a display name.
  *(advisory — duplicates silently miswire ANY by-name scripting; this changed real
  geometry once: two "Auto Angle Degrees" inputs.)*
- **R10 sockets in panels** — params organized via `interface.new_panel`; only
  `Geometry` + `Selection` may stay top-level. *(advisory — creation criterion)*
- **R11 no needless reroutes** — a rerouted link whose direct wire would be short
  (<~300px) and unobstructed stays DIRECT. *(advisory — lines only bend for a reason;
  the engine's `_adjacent_direct` test enforces this at routing time)*

**The full creation/tidying criteria live in `LLMGeonodePipeline/GEONODE_CRITERIA.md`**
— tidying is held to the SAME bar as authoring (function frames, panels + naming,
per-function group inputs, subway wiring). The audit mirrors it as R1–R11.

**Subway-map principle (the visual north star):** you must be able to trace which
station (node) feeds which via which line. Lines/reroutes/nodes should almost never
intersect or obstruct — reroutes build *around* nodes in the way, kept horizontal &
vertical. A track may split from a shared source, but every path stays readable —
and a track that doesn't need to bend doesn't get reroutes at all (R11).
R1/R2/R6/R11 + the router's node-aware lanes enforce this.

**Blocking vs advisory** (policy: `layout_audit.BLOCKING` / `ADVISORY`): only R1+R2+R7
block a `run_pipeline` save (structural integrity — overlaps / hidden reroutes make
a graph *broken*). R3 is advisory because feedback/preview topologies (a deformer's
`Set Position` → preview `Switch` / gizmo `Join` upstream) have legitimate backward
links and can't reach zero. R8–R10 are advisory because fixing them takes semantic
judgment (see the garbled-graph workflow below). `tidy_layout` defaults were
tightened (`row_gap` 55, `band_gap` 120) — verified safe (R1/R2 pass) on both a
simple graph and a gizmo-heavy deformer.

Also keep: generous spacing, labeled frames grouping logical sections
(`frame.location=(0,0)` makes child `.location` absolute — the trick for stamping
frames without shifting children).

## Tidying a garbled graph — isolate functions FIRST

The deterministic engine layers and routes, but it cannot invent semantics: an
unframed 90-node soup tidies into a *readable soup*. When R8 reports many unframed
nodes, do this order (full criteria: `LLMGeonodePipeline/GEONODE_CRITERIA.md`):

1. **Capture** the graph and identify the logical functions from connectivity +
   node semantics (what feeds the output? which cluster builds the selection?
   which is debug viewers?). This is the AI-judgment step.
2. **Create labeled function frames** via blender-mcp `execute_blender_code`:
   `f = ng.nodes.new("NodeFrame"); f.label = "Corner Damage"; f.location = (0,0)`
   then parent the cluster's nodes (`n.parent = f` — with the frame at (0,0),
   child locations stay absolute). Park debug Viewer clusters in their own
   "Debug" frame (or ask the user whether to delete them).
3. **Fix the interface**: rename duplicate socket names (R9 — rename, don't
   reorder, so modifier overrides survive), group params into panels (R10):
   Selection top-level → effect panel(s) → Affect Axes/Center/Preview.
4. **Then run the deterministic tidy** (`tidy_and_route` live or `run_pipeline.py`
   headless) and audit. Frames drive the band layout, so step 2 is what makes
   step 4 come out readable.
5. Geometry-unchanged is non-negotiable at every step: snapshot evaluated verts
   before, compare after, never save on mismatch.

## Two layout engines — pick per need

Both live in `LLMGeonodePipeline/` and are scored by the same `layout_audit`.

| | **GeoNode Layout MCP** (`autolayout_pass`) | **`tidy_layout.py`** (`tidy_and_route`) |
|---|---|---|
| What | fast node *reposition*, layered L→R | full pipeline: dissolve reroutes → layer → localize group-inputs → **orthogonal reroute routing** → declutter |
| Wires | direct (straight) | subway-map orthogonal buses + taps |
| Footprint | compact (single row + lower band) | taller: frames cascade as diagonal bands |
| Group inputs | stay as long wires | localized per-frame (short) |
| Judgment | AI reasons over the *screenshot* (custom, non-layered arrangements) | deterministic, geometry-safety-checked, saves only if verts unchanged |
| Use when | quick tidy, interactive iteration, arrangements a human eyes | the **default** for publishing a geonode to the ST3E library |

**`run_pipeline.py` is the default composition:** it applies `tidy_layout` and
gates the save on BOTH geometry-unchanged AND the `layout_audit` rules — the two
engines verify each other. `blender --background --factory-startup --python
run_pipeline.py -- GN_NormalTransfer`. It **won't save** if a blocking rule (R1/R2/R7)
fails (this fired in practice — re-tidying already-routed output overlapped a node).

Both satisfy R1–R4. Verified on `GN_NormalTransfer` (2026-07): MCP autolayout →
compact aspect ~0.36; `tidy_layout` → 0 overlaps, 20/20 links L→R, 21 orthogonal
reroutes, aspect ~0.86. **Run `layout_audit.py` after either** to confirm.

## Gotchas (all bitten in practice)

- **Draw-handler gating:** the index-stamp handler fires for *every* node editor
  with transient context wrappers — gate on the persistent tree datablock (`==`),
  never region/area identity (`is`). See memory `feedback_blender_draw_handler_context_gating`.
- **`is` vs `==` on bpy wrappers:** after a file reopen, `node_a is node_b` fails
  even for the same node — compare by `.name` or `==`. Both `layout_audit.py` and
  `tidy_layout.py` trace reroutes by name for this reason.
- **`node.dimensions` is only valid post-draw** — capture serializes after the
  screenshot forces a redraw; the audit reads `dimensions` (divide by `ui_scale`
  for node-space) with an `_est_h` fallback.
- **Menu → dropdown pattern:** a front-end `Menu` input drives a `Menu Switch(INT)`
  → `Index Switch`; the modifier override is an int. See memory
  `feedback_gn_menu_to_index_switch`.
- **GI fans are exempt from ALL routing passes** — group-input param links stay
  straight direct wires (a parallel dashed ribbon), parked below-left of their
  consumers; far consumers get their own small GI labeled by its interface panel.
  Lane-routing GI links once stacked 7 reroute rows across a frame label.
- **Server persistence:** the socket server + main-thread timer survive
  `open_mainfile` (persistent timer + module-global). Re-`start_server()` is a safe
  no-op ("already running").

## Companion files (all in `LLMGeonodePipeline/`)

- `run_pipeline.py` — default orchestrator: tidy → verify both goals → save.
- `tidy_layout.py` — deterministic engine (`tidy_and_route`, `process_file`).
- `layout_audit.py` — score a tree against R1–R11 (CLI or importable); the shared
  rule set both engines are checked against.
- `prepare_capture.py` — open + frame a node editor and start the server.
- `GEONODE_CRITERIA.md` — the canonical creation/tidying criteria (read it first).
- Suite `README.md`. Rules memory:
  `feedback_gn_node_layout_spacing`; rewiring safety: `feedback_gn_link_rewire_gotchas`
  (relink by identifier, viewer dynamic sockets, geometry-unchanged gate).
