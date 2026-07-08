# WMH Architecture Adoption — core/blender split, headless tests, snippets, installer

> Forward-direction architecture standard for the Toolings suite. Both `ClaudeVibe_WIPs`
> and `wmh-dcc-tooling` (github.com/Windmillhill-Games/wmh-dcc-tooling) are **ours** — same
> owner, free to share code and patterns. WMH is the more mature reference we adapt FROM.
> Goal: adapt EXISTING tools to this scheme AND build NEW tools with it from day one.
> Operationalized as the `wmh-tool-architecture` skill (`.claude/skills/`).

Supersedes the old single-`.py`-file guidance in `blender_addon_creation_workflow.md`
(that "no ZIP / single .py" advice is legacy). Current truth = `_TOOLING_STRUCTURE.md`
(README + source/ + distribution/ + assets/) EXTENDED with the code layout below.

## High-priority principles (P1, P2, P5)

### P1 — `core/` + `blender/` split with headless pytest
Every WMH tool separates pure logic from Blender UI so `core/` can be unit-tested without
launching Blender (rig_rebuild 94 tests, greyboxing 66, hex_grid 28 — all bpy-free pytest).
Our tools are monolithic single-`__init__.py` files (MassExporter is internally v13.6.0 in
ONE file) — only hand-testable in-app.

Code layout INSIDE each tool's existing `source/`:
```
<ToolName>/
  README.md            # stays at tool root (per _TOOLING_STRUCTURE.md)
  source/
    __init__.py        # thin: bl_info/manifest + register()/unregister() wiring only
    core/              # pure Python, bpy-FREE, unit-tested
    blender/           # UI only: operators.py, panels.py, properties.py
    tests/             # pytest over core/ — runs without Blender
    blender_manifest.toml
  distribution/  (+ archive/)
  assets/
```
Rule of thumb: anything that's computation, parsing, naming, math, or data transforms goes
in `core/` and imports NO bpy. Anything touching `bpy`/`context`/depsgraph/operators/panels
stays in `blender/`. `__init__.py` only wires registration.

Examples of logic to extract to `core/`:
- MassExporter: suffix-grouping / base-name logic, name-collision handling, LayerCollection
  exclude restore order, hidden-object collect/restore.
- AddBoundsToName: unit conversion, rounding, swizzle, format helpers.
- SyncedModifiers: sync-ID hashing, source-suffix parsing.

Start with the BIGGEST tools (MassExporter, SyncedModifiers, Compositor Render Sets) where
testability pays off most; leave tiny single-operator tools alone.
Reference docs in the WMH repo: `docs/blender-npanel-scripting-guide.md`,
`docs/architecture-evolution-plan.md`.

### P2 — snippet_manager + snippet_manager_api (MCP synergy)
Adopt WMH `snippet_manager` (RAG-searchable Python snippet library, EmbeddingGemma 308M,
keyword fallback if deps absent) + `snippet_manager_api` (agent-callable facade
`get_snippet_api()`, 15 methods: execute / search / validate / sequences / metadata / status).
We already drive Blender live via MCP — this gives the agent a searchable library of vetted,
parameterized patterns to run instead of regenerating code each time.
How to apply: deploy both addons (RAG opt-in via `pip install chromadb onnxruntime
transformers huggingface-hub`); seed the library with our recurring Blender patterns and the
fixes from these memories; wire MCP to prefer `search`→`execute` over raw code-gen; keep
suite-wide snippets at Project scope (Project → User → Defaults) so they version with the repo.

### P5 — `install_to_blender.ps1` one-click dev installer
WMH tools ship a per-addon `install_to_blender.ps1` that auto-detects the highest installed
Blender (registry → common paths → folder picker) and deploys to
`%APPDATA%\Blender Foundation\Blender\<ver>\extensions\user_default\<addon>`. No hot-reload —
restart Blender after deploy. KEEP building the release zip (always-zip rule stands) and ADD
this script per tool for fast dev iteration. One template, parameterized by addon folder name.

## Cross-pollination roster (lower priority, free to lift)
- multi_modifier_driver ↔ SyncedModifiers: complementary (theirs = transient session + direct
  value-set + own 25-step undo; ours = persistent driver-based sync with Source:ID hashes).
  Their `EDGE_CASES_ANALYSIS.md` is portable hardening: library-linked filtering,
  `context.scene.objects` vs `bpy.data.objects` scoping, cross-target param-type validation,
  node-tree-swap detection on refresh, separate-undo trap, 500-target cap.
- viewport_pie_menu: extensible Shift+W pie (1 tool + 7 free slots) — launcher to consolidate
  our scattered modal ops (Smart Crease/Collapse/Set Orientation, Center Edges, Toggle Modifier
  Display, EdgeConstraintMode).
- rig_rebuild + greyboxing: mature Blender→Unity export pipelines — reference for the planned
  Unity track and MassExporter game-asset focus.
- ascii_fbx_import: imports ASCII FBX (stock Blender is binary-only); relevant to legacy 3DS Max
  tooling. `core/fbx_strip.py` independently reusable.
- hex_grid: Python data model → point cloud → GeoNodes instancing + GPU modal editing — template
  for GeoNode-driven interactive tools.
- blender_hapi / houdini_mcp: only if Houdini enters the pipeline (none today); houdini_mcp's
  55-tool MCP design is a reference for extending our Blender-MCP usage.

## Adoption order
1. core/blender split on the big tools (P1).
2. snippet_manager(_api) for the MCP workflow (P2).
3. Port multi_modifier_driver edge-case fixes into SyncedModifiers.
4. viewport_pie_menu launcher for scattered modal tools.
5. Template install_to_blender.ps1 across tools (P5).
