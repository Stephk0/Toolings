# Blender Knowledge

Engineering findings for Blender tooling in this repo: API traps, pipeline rules, and
build recipes that were expensive to learn. Each section records the symptom, the cause,
and how to apply it. Read the relevant page before working in that area.

| Page | Covers |
|------|--------|
| [bpy-api-gotchas.md](bpy-api-gotchas.md) | BMesh after undo, modal teardown, draw handlers, `id()` on wrappers, unique names, bundled brush libraries |
| [export-pipeline.md](export-pipeline.md) | No source mutation, hidden objects, LayerCollection exclude, `modifier_apply` vs `show_viewport`, FBX normals |
| [headless-and-automation.md](headless-and-automation.md) | Blender MCP, `--background` edits, headless rendering/compositor, one file per process, UI screenshots |
| [addon-architecture.md](addon-architecture.md) | WMH split gotchas, zip/release habit |
| [shading.md](shading.md) | Unity URP shader ports, camera-space Z flip, EEVEE cavity/curvature |
| [geonodes/asset-checklist.md](geonodes/asset-checklist.md) | **Start here for geonode modifiers**: build recipe, roster of built modifiers, publish checklist |
| [geonodes/asset-files.md](geonodes/asset-files.md) | Demo object, demo-scene hygiene, icon pipeline |
| [geonodes/layout.md](geonodes/layout.md) | Node spacing, frames, wire lanes, tidying helper groups |
| [geonodes/nodes-and-fields.md](geonodes/nodes-and-fields.md) | Domain/field semantics and node behaviour surprises |
| [geonodes/sockets-and-menus.md](geonodes/sockets-and-menus.md) | Relinking, interface sockets, Menu sockets |
| [geonodes/techniques.md](geonodes/techniques.md) | Deformer center/gizmo/symmetry, direction by axis/object, region fill, shared AO core |
| [DEPENDENCY_REPORT.md](DEPENDENCY_REPORT.md) | External-dependency audit of every geonode `.blend` (2026-07-17) |

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

Keep findings true: when code or Blender changes make one wrong, fix or delete it. Dates
and version numbers in older sections reflect when they were written.
