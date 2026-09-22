# Blender/Addons — addon work rules

Each subfolder is an independent addon. Layout, release and zip steps:
`_TOOLING_STRUCTURE.md`. New tools and big refactors follow the `wmh-tool-architecture`
skill (bpy-free `core/` + `blender/` UI + headless pytest).

## Conventions

- `bl_info` dict (plus `blender_manifest.toml` for 4.2+ extensions); bump both on release.
- Class names `CATEGORY_OT_name` / `CATEGORY_PT_name` / `CATEGORY_UL_name`; `bl_idname`
  in `category.name` form. Properties via `bpy.props.*`, snake_case.
- Python files lowercase_with_underscores; addon display names may use spaces
  ("Smart Crease").
- Operators support undo (`bl_options = {'REGISTER', 'UNDO'}`), report user-facing errors
  via `self.report`, and expose a debug-logging toggle where the tool is non-trivial.

## Operator patterns

Blender manages operator lifecycle — `MyOperator()` cannot be instantiated. To share logic
between operators, call the method unbound and pass `self` explicitly:

```python
MyOperator.method_name(self, context, args)
```

Used e.g. by MassExporter to share export logic between the main and quick-export operators.
Prefer moving shared logic into plain functions (or `core/`) for new code.

## Before calling a change done

- Test in a live Blender via Blender MCP, or headless (`--background --factory-startup`).
- Verify undo/redo and viewport updates.
- Build the versioned zip and update the tool's README version line and CHANGELOG.

## Known traps

Read before touching the area: `../Knowledge/bpy-api-gotchas.md` (modals, BMesh, draw
handlers, bpy wrappers), `../Knowledge/export-pipeline.md` (any exporter),
`../Knowledge/addon-architecture.md` (WMH split, zips).

## Tool-specific context

Complex tools carry their own agent notes — read them before editing:
- `SyncedModifiers/source/CLAUDE.md` — driver-based sync architecture
- `docs/compositor-render-sets-patterns.md` — Compositor Render Sets patterns
- `MassExporter/EXPORT_FLOW.md` — export pipeline and settings priority
