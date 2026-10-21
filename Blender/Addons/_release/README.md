# Release CLI

Builds the installable zip of any addon in `Blender/Addons/`, keeps its version in step
everywhere it is written down, and checks the whole folder for drift. Pure stdlib Python
3.11+, no Blender needed.

```
python Blender/Addons/_release/release.py status            # every tool at a glance
python Blender/Addons/_release/release.py release "Smart Crease" patch
```

| Command | What it does |
|---------|--------------|
| `status [tool]` | Version in bl_info, manifest, current zip, README and `DOCUMENTATION_INDEX.md`; flags stale zips and files no spec covers |
| `check [tool]` | Same, exits 1 when something needs attention (hooks, CI) |
| `bump <tool> <major\|minor\|patch\|X.Y.Z>` | Writes the version into bl_info / `VERSION`, `blender_manifest.toml`, the README version line / badge / title / zip name, and the index row |
| `docs <tool>` | Re-syncs those doc slots to the code version without bumping |
| `build <tool>` | Builds `<stem>_v<version>.zip`, compiles every `.py` in it, checks the versions inside, then moves the previous zip to `distribution/archive/` |
| `release <tool> <part>` | `bump` + `build` |
| `init <tool>` / `init --all` | Writes the tool's `release.toml` from its current zip |

`bump`, `docs`, `build` and `release` take `--dry-run`. Tool names match the folder or the zip
stem, ignoring case, spaces, `-` and `_` (`smartcrease`, `tileuv`).

## release.toml

Each tool folder has one. It says what goes into the zip and how it is laid out, so a build
reproduces the previous zip exactly. `init` inferred all of them from the zips shipped on
2026-10-08 and confirmed each one rebuilds to the same file list.

```toml
zip_stem = "CenterEdges"      # zip name: CenterEdges_v1.5.1.zip
wrapper = "CenterEdges"       # folder inside the zip; "" = files at the archive root
source_dir = "source"
include = []                  # globs relative to source_dir (* = one segment, ** = any depth)
exclude = ["*.md"]

[files]                       # published path = source path relative to the tool folder
"README.md" = "README.md"
"__init__.py" = "source/center_loops_addon.py"
```

A new module that neither `include` nor `exclude` matches shows up in `status` and as a build
warning. Add it to one of them.

## Safety rules

- Zips are never deleted. A version that is already in `archive/` is refused. A zip of the
  current version whose content differs from the source is refused too: bump, or pass
  `--force` to rebuild it in place.
- A zip that fails verification (no `__init__.py`, a syntax error, a version mismatch inside)
  is discarded before `distribution/` is touched.
- Builds are deterministic: the same sources give a byte-identical zip.
- Doc edits touch only version slots. History such as "since v1.2.0" is left alone.
- `build` warns when the CHANGELOG has no entry for the version. Write that entry yourself.
- A new addon, a rename or a changed feature set also needs its row and description in the
  root `README.md`, `DOCUMENTATION_INDEX.md` and `QUICK_REFERENCE.md`. The CLI does not add
  rows; do it by hand (rule in the repo `CLAUDE.md`).

## Tests

`python -m pytest Blender/Addons/_release/tests`. The tests build fake tools in a temp folder
and never touch the repo.
