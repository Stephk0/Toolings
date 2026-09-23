# Developing Stephko Toolings

For building, changing, or releasing the tools. Artist-facing docs live in the
[README](README.md) and each tool's own `README.md`; this page is the map for everything behind
them.

## Where things live

| Kind of document | Where | Audience |
|------------------|-------|----------|
| Tool usage (install, panels, workflows, troubleshooting) | `<Tool>/README.md` | Artists and users |
| Architecture, folder layout, tests, build steps | `<Tool>/source/DEVELOPMENT.md` | Developers |
| Version history | `<Tool>/source/CHANGELOG.md` | Developers (and curious users) |
| Instructions for AI coding assistants | `CLAUDE.md` files (repo root, `Blender/Addons/`, `Blender/Geonodes/`, `Unity/`) | LLM agents |
| Engineering findings — API traps, pipeline rules, recipes | [`Blender/Knowledge/`](Blender/Knowledge/README.md) | Developers and agents |

Keep READMEs free of implementation notes, agent instructions, and changelog detail — put them
in the files above and link to them.

## Conventions

- **[Tool folder convention](Blender/Addons/_TOOLING_STRUCTURE.md)** — `README.md` + `source/` +
  `distribution/` (+ `archive/`) + optional `assets/`, and the release steps.
- **Pure Python, no external dependencies** in addons. Target Blender 5.0, keep 4.5+ working.
- **Every addon change ships a versioned zip** in `distribution/`; the previous zip moves to
  `distribution/archive/`.
- **Exporters never mutate source data** — destructive ops run on duplicates, in-place changes
  are restored in `finally`.
- **New tools and refactors** follow the WMH split: a bpy-free `core/` with headless pytest and
  a thin `blender/` UI layer. Reference implementation:
  [Compositor Render Sets](Blender/Addons/Compositor%20Render%20Sets/source/DEVELOPMENT.md).

## Engineering knowledge

Check [`Blender/Knowledge/`](Blender/Knowledge/README.md) before debugging a silent failure.

| Page | Covers |
|------|--------|
| [bpy API gotchas](Blender/Knowledge/bpy-api-gotchas.md) | BMesh after undo, modal teardown, draw handlers, `id()` on wrappers, unique names |
| [Export pipeline](Blender/Knowledge/export-pipeline.md) | No source mutation, hidden objects, LayerCollection exclude, `modifier_apply` vs `show_viewport` |
| [Headless & automation](Blender/Knowledge/headless-and-automation.md) | Blender MCP, `--background` edits, headless rendering, UI screenshots |
| [Addon architecture](Blender/Knowledge/addon-architecture.md) | The WMH split and its gotchas |
| [Shading](Blender/Knowledge/shading.md) | URP shader ports, camera-space Z flip, EEVEE cavity/curvature |
| [Dependency report](Blender/Knowledge/DEPENDENCY_REPORT.md) | External-dependency audit of every geonode file |

## Geometry Nodes authoring

- **[Authoring guide](Blender/Geonodes/AUTHORING.md)** — making a group appear under
  *Add Modifier → ST3E*, demo objects, the Asset Browser icon pipeline.
- [Geonode asset checklist](Blender/Knowledge/geonodes/asset-checklist.md) — build recipe,
  roster, publish checklist. Also: [layout](Blender/Knowledge/geonodes/layout.md) ·
  [nodes & fields](Blender/Knowledge/geonodes/nodes-and-fields.md) ·
  [sockets & menus](Blender/Knowledge/geonodes/sockets-and-menus.md) ·
  [techniques](Blender/Knowledge/geonodes/techniques.md) ·
  [asset files](Blender/Knowledge/geonodes/asset-files.md)
- Icon pipeline: [`_icons/ICONS.md`](Blender/Geonodes/_icons/ICONS.md) ·
  [`_icons/GOTCHAS.md`](Blender/Geonodes/_icons/GOTCHAS.md)

## Internal tooling

| Tool | What it does | Docs |
|------|--------------|------|
| **LLM Geonode Pipeline** | Reads and lays out Geometry Nodes graphs — the `tidy_layout` engine plus the GeoNode Layout MCP server | [README](Blender/Addons/LLMGeonodePipeline/README.md) · [criteria](Blender/Addons/LLMGeonodePipeline/GEONODE_CRITERIA.md) |
| **Library Publisher** | Publishes the asset library to the Shared Drive; its criteria gates run the geonode layout audit | [README](Blender/Addons/LibraryPublisher/README.md) · [dev notes](Blender/Addons/LibraryPublisher/source/DEVELOPMENT.md) |
| **Docs site** | Astro/Starlight build of these docs | [README](docs-site/README.md) |

## Git

Primary branch `main`. Branch before committing. Never commit `__pycache__`, `tmpclaude-*`,
`.pytest_cache`, or scratch probe scripts.
