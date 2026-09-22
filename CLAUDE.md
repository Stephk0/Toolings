# Stephko Toolings — agent guide

Production tools for Blender (active), Unity (occasional), and 3DS Max (maintenance only,
bug fixes). Author: Stephan Viranyi (Stephko).

This file holds only repo-wide rules and pointers. Tool details live next to the tool;
version history lives in each tool's CHANGELOG and in git — never add changelog entries here.

## Repo shape

This is a **collection of independent projects**, not one codebase. Treat each tool as its
own project with its own scope; do not assume shared dependencies or architecture.

| Path | What |
|------|------|
| `Blender/Addons/<Tool>/` | One folder per addon: `README.md` + `source/` + `distribution/` (+ `archive/`) + optional `assets/`. Convention and release steps: `Blender/Addons/_TOOLING_STRUCTURE.md` |
| `Blender/Addons/LLMGeonodePipeline/` | GeoNode Layout MCP server + `GEONODE_CRITERIA.md` |
| `Blender/Addons/docs/` | Shared addon-dev notes (not a tool) |
| `Blender/Geonodes/` | Geometry Nodes asset `.blend` files, icon pipeline in `_icons/` |
| `Blender/Shading/` | Blender re-creations of Unity URP shaders |
| `Blender/MCP/` | Legacy tree-generator MCP scripts |
| `Unity/` | Unity tools (`ModelImportProcessor/`) |
| `3DSMAX/` | MaxScript (ST3E), maintenance mode |
| `docs-site/` | Astro/Starlight docs site |

Addons were flattened on 2026-09-18 from `Blender/Addons/ClaudeVibe_WIPs/<Tool>` to
`Blender/Addons/<Tool>`. Any path containing `ClaudeVibe_WIPs` is stale.

Current tool versions: `DOCUMENTATION_INDEX.md`. When a version here and in code disagree,
trust `source/__init__.py` / `blender_manifest.toml`.

## Where to look

| Task | Read first |
|------|-----------|
| Any Blender addon work | `Blender/Addons/CLAUDE.md`, then the tool's `README.md` (and `CLAUDE.md` if present) |
| New addon, or refactor a monolithic one | skill `wmh-tool-architecture` (reference implementation: Compositor Render Sets v2.0.0) |
| Any Geometry Nodes work (create / tidy / alter) | skill `geonode-layout-mcp` — always first. Criteria: `Blender/Addons/LLMGeonodePipeline/GEONODE_CRITERIA.md`. Folder rules: `Blender/Geonodes/CLAUDE.md` |
| Geonode icons | `Blender/Geonodes/_icons/ICONS.md` + `GOTCHAS.md` |
| Publishing the asset library | skill `publish-library` / `publish-library-config` |
| Unity / C# | `Unity/CLAUDE.md` |
| Resuming earlier work | skill `continue-last` (Serena `continuation-brief-*` memories) |

## Hard rules

- **Pure Python, no external dependencies** in Blender addons.
- **Target Blender 5.0**, keep 4.5+ working unless told otherwise.
- **Always build a versioned installable zip** after any addon change (files at archive
  root, into the tool's `distribution/`, previous zip to `distribution/archive/`).
- **Exporters never mutate source data** — destructive ops on duplicates, in-place changes
  restored in `finally`.
- **Comment geonodes like code** — labeled frames and named nodes.
- Do not remove features or rename things arbitrarily; update the tool's README and
  CHANGELOG with every behavior change.

## Tooling

- **Serena** is the primary code-intelligence toolset (see global CLAUDE.md for startup).
  Serena project memories live in `.serena/memories/`.
- **Blender MCP** (`mcp__blender__*`) drives a live Blender — use it to verify addon and
  geonode behavior instead of reasoning only. Multiple Blender instances may be open; never
  inject OS-level clicks.
- **GeoNode Layout MCP** (`geonode-layout`) — used through the `geonode-layout-mcp` skill.
- Headless edits when no live Blender is connected:
  `blender --background --factory-startup`, one `.blend` per process.

## Git

Primary branch `main`. Branch before committing. Never commit `__pycache__`, `tmpclaude-*`,
`.pytest_cache`, or scratch probe scripts.
