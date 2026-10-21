# Blender Knowledge

Engineering findings for Blender tooling in this repo: API traps, pipeline rules, and
build recipes that were expensive to learn. Each section records the symptom, the cause,
and how to apply it. Read the relevant page before working in that area.

| Page | Covers |
|------|--------|
| [bpy-api-gotchas.md](bpy-api-gotchas.md) | BMesh after undo, modal teardown, draw handlers, `id()` on wrappers, bundled brush libraries, post-processing native transforms, stale link sockets, dialog text focus |
| [export-pipeline.md](export-pipeline.md) | No source mutation, hidden objects, LayerCollection exclude, `modifier_apply` vs hidden modifiers / shape keys, `.001` names, FBX normals |
| [headless-and-automation.md](headless-and-automation.md) | Blender MCP, `--background` edits, headless rendering/compositor, one file per process, UI screenshots, real-UI driving (Xvfb, Windows capture), PyPI `bpy`, background pivots |
| [addon-architecture.md](addon-architecture.md) | WMH split gotchas, zip/release habit (`release.py`) |
| [shading.md](shading.md) | Unity URP shader ports, camera-space Z flip, EEVEE cavity/curvature |
| [geonodes/asset-checklist.md](geonodes/asset-checklist.md) | **Start here for geonode modifiers**: build recipe, publish traps and catalog UUIDs, retiring a geonode |
| [geonodes/asset-files.md](geonodes/asset-files.md) | Demo object, demo-scene hygiene and verify render, icon pipeline pointer |
| [geonodes/layout.md](geonodes/layout.md) | Layout scripting traps, save-gate nudge loop, wire lanes, tidying helper groups, drawn socket positions |
| [geonodes/nodes-and-fields.md](geonodes/nodes-and-fields.md) | Domain/field semantics, node behaviour surprises, properties that became menu sockets, face-domain delete |
| [geonodes/sockets-and-menus.md](geonodes/sockets-and-menus.md) | Relinking, zero backfill, Menu sockets, interface identifier order |
| [geonodes/techniques.md](geonodes/techniques.md) | Deformer center/gizmo/symmetry, direction by axis/object, region fill, AO core, per-region aggregates, tileable lattice noise |
| [DEPENDENCY_REPORT.md](DEPENDENCY_REPORT.md) | Snapshot external-dependency audit of the geonode `.blend` files (2026-07-17) |

## Adding a finding

Add a section to the matching page (create a page when no topic fits and list it above):

```markdown
<a id="short_slug"></a>

## One-line claim

*One-sentence summary.*

What happens, measured on which Blender version.

**Why:** cause, and what it cost.

**How to apply:** the rule, with a code snippet when it helps.
```

Keep findings true and short:
- When code or Blender changes make one wrong, fix or delete it. Dates and version numbers
  say when it was measured.
- Record the rule and the evidence, not the story of finding it. Git keeps the history.
- Per-modifier or per-tool build detail belongs in that tool's docs or build script; only
  lessons that apply elsewhere go here.
- Rules that already live in `GEONODE_CRITERIA.md`, a skill, or a tool's `DEVELOPMENT.md`
  get a link, not a copy.
