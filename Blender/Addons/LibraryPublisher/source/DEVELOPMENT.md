# Library Publisher — developer notes

Implementation and maintenance notes. User docs: [README](../README.md).

## Layout

```
LibraryPublisher/
├── README.md                     this file
├── publish_config.json           the live config (gitignored - per machine)
├── install_to_blender.ps1        one-click dev deploy
├── hooks/                        tracked git hooks (pre-push, post-commit)
├── source/
│   ├── __init__.py               thin: bl_info + register/unregister
│   ├── cli.py                    the entry point every trigger uses
│   ├── core/                     pure Python, bpy-FREE, unit-tested
│   │   ├── config.py             schema, defaults, validation, dotted-path edits
│   │   ├── selection.py          scope config -> deterministic file list
│   │   ├── catalogs.py           cats.txt parsing + the ST3E_Ext rename
│   │   ├── criteria.py           check planning, interpretation, block/warn policy
│   │   ├── manifest.py           hashes, incremental diff, provenance
│   │   ├── delivery.py           staging + rclone / robocopy / copy backends
│   │   ├── publish.py            the orchestrator
│   │   └── shell.py              subprocess, git info, Blender discovery
│   ├── blender/                  bpy boundary: preferences, operators, panel
│   ├── checks/blender_inspect.py runs INSIDE headless Blender, emits JSON facts
│   └── tests/                    pytest over core/ — 135 tests, no bpy
└── distribution/                 installable zip (older builds in archive/)
```

Per the WMH architecture standard: all policy and computation lives in bpy-free
`core/`, which is why the criteria policy layer is unit-testable without Blender
and why the Blender button can run a publish on a worker thread safely.

```
python -m pytest source/tests -q
```

## Notes

- Working state (`.staging/`, `.staging_batch/`, `.last_publish/`) is gitignored.
- The manifest cache in `.last_publish/` is what makes runs incremental. If it is
  missing (fresh clone, CI runner) the publisher fetches the manifest from the
  drive with `rclone cat`; failing that it falls back to a full comparison.
- `delivery.atomic` swaps the tree in place and is for **local** backends. For
  rclone, atomicity comes from `--delete-after`: stale files are removed only once
  every upload has succeeded, so a failed run never leaves holes in the library.
