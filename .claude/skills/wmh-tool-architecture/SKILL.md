---
name: wmh-tool-architecture
description: Build a NEW Blender/DCC tool or refactor an EXISTING one to the WMH architecture standard — a bpy-free core/ + blender/ UI split with headless pytest, plus folder layout, dev installer, and snippet/MCP wiring. Use whenever creating a new addon in ClaudeVibe_WIPs, restructuring a monolithic __init__.py tool, or when the user mentions "the architecture scheme", "core/blender split", "WMH pattern", or "make this testable".
---

# WMH Tool Architecture

The standard for every tool in this suite. Adapted from our own `wmh-dcc-tooling` repo
(github.com/Windmillhill-Games/wmh-dcc-tooling) — both repos are ours, free to share code.
Full rationale + cross-pollination roster: Serena memory `wmh_architecture_adoption`.
Folder convention this extends: `ClaudeVibe_WIPs/_TOOLING_STRUCTURE.md`.

## The core idea (P1)

Separate **pure logic** (no `bpy`) from **Blender UI**. The bpy-free part gets unit-tested
with pytest and never needs Blender open to verify. This is the single biggest quality lever
— do it for every non-trivial tool.

```
<ToolName>/
├── README.md               # tool root — version, install, layout (per _TOOLING_STRUCTURE.md)
├── source/
│   ├── __init__.py         # THIN: bl_info / manifest + register()/unregister() wiring ONLY
│   ├── core/               # pure Python, bpy-FREE, deterministic, unit-tested
│   │   ├── __init__.py
│   │   └── *.py            # parsing, math, naming, data transforms, algorithms
│   ├── blender/            # UI + bpy boundary
│   │   ├── __init__.py
│   │   ├── operators.py    # bpy.types.Operator — orchestrate core/, touch context
│   │   ├── panels.py       # bpy.types.Panel
│   │   └── properties.py   # PropertyGroup + callbacks
│   ├── tests/              # pytest over core/ — NO bpy import
│   │   └── test_*.py
│   └── blender_manifest.toml
├── distribution/           # current installable zip (+ archive/ for old ones)
├── assets/                 # screenshots (omit if none)
└── install_to_blender.ps1  # one-click dev deploy (P5)
```

## The boundary rule

- **Goes in `core/`** (import NO bpy): computation, parsing, string/name logic, geometry math
  on plain arrays, rounding/units/swizzle, sync-ID hashing, suffix grouping, validation,
  data models, serialization. Must be importable in plain CPython.
- **Goes in `blender/`**: anything touching `bpy`, `context`, depsgraph, operators, panels,
  property registration, `bpy.data`, view-layer/collection state, FBX/export operator calls.
- **`__init__.py`**: only `bl_info`, imports, and `register()`/`unregister()`. No logic.

If a function needs both, split it: a bpy-free computational kernel in `core/`, a thin
`blender/` wrapper that gathers inputs from context, calls the kernel, applies results.

## Building a NEW tool — checklist

1. Create `<ToolName>/` with the four folders (`source/`, `distribution/`, `assets/`) per
   `_TOOLING_STRUCTURE.md`; add `source/core/`, `source/blender/`, `source/tests/`.
2. Write the algorithm in `core/` FIRST, with `tests/test_*.py` proving it — run pytest with
   the suite's bundled Python (no Blender needed). Red-green before any UI.
3. Add `blender/operators.py|panels.py|properties.py` that import from `core/` and wire context.
4. Keep `__init__.py` thin (bl_info + register/unregister).
5. Add `install_to_blender.ps1` (template below) and a `README.md` from the convention.
6. Verify live via Blender MCP (`mcp__blender__execute_blender_code`) — see memory
   `reference_blender_mcp`.
7. Build the versioned distribution zip (always-zip rule) with files at archive root.

## Refactoring an EXISTING monolith — checklist

1. Read the single `__init__.py`; list every function and classify core vs UI by the boundary
   rule above. Trust `source/__init__.py` VERSION, not the folder name.
2. Create `core/` and move pure functions there one cluster at a time; replace bpy calls inside
   them with plain-data inputs/outputs. Add a pytest as you move each cluster.
3. Leave operators/panels/properties in `blender/`, importing the relocated core functions.
4. Run pytest green, then verify behavior unchanged in Blender via MCP.
5. Bump version, rebuild zip, move old zip to `distribution/archive/`.
6. Priority targets (biggest payoff): MassExporter, SyncedModifiers, Compositor Render Sets.
   Skip tiny single-operator tools.

## install_to_blender.ps1 (P5) — template

Auto-detect highest Blender, deploy the addon folder to the extensions dir. Adapt `$AddonName`.

```powershell
param([string]$AddonName = "<addon_folder>")
$ErrorActionPreference = "Stop"
# find highest installed Blender userdata dir
$root = Join-Path $env:APPDATA "Blender Foundation\Blender"
$ver  = Get-ChildItem $root -Directory | Where-Object { $_.Name -match '^\d+\.\d+$' } |
        Sort-Object { [version]$_.Name } -Descending | Select-Object -First 1
if (-not $ver) { throw "No Blender userdata under $root" }
$dest = Join-Path $ver.FullName "extensions\user_default\$AddonName"
$src  = Join-Path $PSScriptRoot "source"
if (Test-Path $dest) { Remove-Item $dest -Recurse -Force }
Copy-Item $src $dest -Recurse -Force
Write-Host "Deployed $AddonName to $dest — restart Blender (no hot-reload)."
```

## Related high-priority adoptions (full detail in memory `wmh_architecture_adoption`)

- **P2 snippet_manager(_api)**: RAG-searchable snippet library + agent-callable API; wire MCP to
  `search`→`execute` vetted patterns instead of regenerating code. Seed with our recurring fixes.
- Cross-pollination: port `multi_modifier_driver` EDGE_CASES into SyncedModifiers; use
  `viewport_pie_menu` as a launcher for scattered modal ops; `rig_rebuild`/`greyboxing` for the
  Unity track.

## Gotchas

- Target Blender 5.0+ (extension/manifest system); see memory `feedback_blender_version_and_headless`.
- `core/` tests must not import bpy — if a test needs bpy, the logic belongs in `blender/`, or the
  bpy dependency should be parameterized out.
- Old memory `blender_addon_creation_workflow` (single .py, no zip) is LEGACY — this skill +
  `_TOOLING_STRUCTURE.md` supersede it.
- Never commit `__pycache__`, `tmpclaude-*`, scratch probes.
