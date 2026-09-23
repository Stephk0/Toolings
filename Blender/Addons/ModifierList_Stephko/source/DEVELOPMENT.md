# Modifier List (Stephko fork) — developer notes

Implementation and maintenance notes. User docs: [README](../README.md).

## Folder layout
- `source/` — full addon tree (`__init__.py`, `modules/`, `addon_registration.py`,
  `icons/`, `dev_tools/`, `tests/`, `docs/`, `CHANGELOG.md`, `LICENSE`)
- `distribution/` — current installable zip; older builds in `distribution/archive/`

> Upstream project retains its own `LICENSE` and `CHANGELOG.md` inside `source/`.

See the repo-level `_TOOLING_STRUCTURE.md` for the standard tool layout.
