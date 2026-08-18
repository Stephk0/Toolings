# Library Publisher

**Version:** 1.1.0 · **Blender:** 4.2+ (developed and verified on 5.0) · **Category:** Import-Export

Publishes the ST3E Blender asset library to a **Google Shared Drive**, renaming the
asset catalogs to `ST3E_Ext` on the way out so the shared copy loads *beside* your
local library in Blender's Asset Browser instead of merging into it.

It is a publish pipeline first and an addon second: the CLI is the real tool, and
the Blender button is one of four triggers into it.

---

## The idea

This is not a folder sync. It is a one-way **publish with a transform**:

```
D:\Stephko_Tooling\Toolings\Blender     the source of truth (git)
        │
        ├─ select      curated by include/exclude globs, not mirrored
        ├─ transform   blender_assets.cats.txt rewritten: ST3E -> ST3E_Ext
        ├─ check       optional criteria gates (one headless Blender pass)
        ├─ stage       full tree assembled locally, hardlinked
        └─ deliver     rclone / robocopy / copy  ->  Google Shared Drive
```

Four things follow from that, and they are deliberate:

- **Never bidirectional.** The drive holds a build artifact. A `README_DO_NOT_EDIT.txt`
  goes out with every publish saying so. Edits there are lost on the next run.
- **Curated.** A raw copy of `Blender/` would ship `_backup_publish_fix/`,
  `*_fixed.blend`, `TreeGenDocu/` iterations and the whole addon source tree.
- **Branch-gated.** The hook and the Action publish from `main` only, so WIP
  geonodes on a feature branch never leak into the shared library.
- **Provenance-stamped.** `publish_manifest.json` and `LIBRARY_VERSION.txt` at the
  drive root record the commit, the per-file hashes and anything withheld.

### How the `ST3E_Ext` rename works

A catalog line is `UUID:catalog/path:simple name`, and every asset inside a `.blend`
stores the catalog **UUID** — not the path. So the publisher rewrites only the path
and the simple name, and carries the UUIDs across untouched:

```
f9ab2fa9-…:ST3E:ST3E                 ->  f9ab2fa9-…:ST3E_Ext:ST3E_Ext
bacd112a-…:ST3E/Deform:ST3E-Deform   ->  bacd112a-…:ST3E_Ext/Deform:ST3E_Ext-Deform
```

The assets still resolve; they simply appear under a differently named tree. That
is why **the published `.blend` files are byte-identical copies** and a publish
needs no Blender at all when criteria are off.

The trade-off to know about: both libraries then define the same UUIDs under
different paths. In practice each library renders its own catalog tree from its own
`cats.txt`. If the Asset Browser's *All Libraries* view ever merges them anyway,
the fix is a deterministic UUID remap — which requires a headless Blender pass
rewriting `asset_data.catalog_id` in all 60+ files. That is a different mode, not a
config flag; `catalog.mode` is where it would live.

---

## Install

**CLI only** (all you need for the slash commands, hook and Action):

```
python source/cli.py config init
python source/cli.py config doctor
```

**As a Blender addon** (for the in-Blender button):

```powershell
.\install_to_blender.ps1
```

Then point it at this folder — the installed addon is a *copy* and cannot find the
repo by itself: `Preferences > Add-ons > Library Publisher > LibraryPublisher Folder`.

Panel: `3D View > Sidebar (N) > ST3E > Library Publisher`.

### rclone against a Google Shared Drive

rclone is the only external dependency, and only for the `rclone` backend
(`winget install Rclone.Rclone`, or use the `robocopy` backend against a mounted
Drive letter instead).

It does **not** need to be on PATH — rclone ships as a single self-contained exe,
so point the config straight at it (a directory works too, and env vars expand):

```
python source/cli.py config set delivery.rclone.executable=C:/tools/rclone/rclone.exe
```

An explicit path that does not resolve is an error rather than a silent fallback
to PATH, so you can never end up running a different rclone than the configured one.
Avoid pointing it inside `Downloads`: the unzipped folder name carries the version
number, so the next rclone upgrade breaks the path.

Then create the remote — this part is interactive (it opens a browser):

```
rclone config
  n  ->  name it (e.g. st3e_gdrive)  ->  storage: drive
  client id / secret: blank
  scope: 1 (full access)
  advanced: n  ->  answer YES to the Shared Drive question, pick it from the list
```

For unattended use (CI, or no browser), use a **service account** instead: create
one in Google Cloud, download its JSON key, share the Shared Drive with the
service account's email as *Content manager*, and point the env var named by
`delivery.rclone.service_account_env` (default `ST3E_GDRIVE_SA_JSON`) at the key
file. Service accounts work cleanly on Shared Drives, unlike on My Drive.

**Google Drive for Desktop tip:** mark the published folder *Available offline*.
In streaming mode the first open of each `.blend` stalls while Drive fetches it.

---

## The four triggers

| # | Trigger | How |
|---|---|---|
| 1 | **Manual** | `/publish-library` in Claude Code, or `python source/cli.py publish` |
| 2 | **On git push** | tracked `hooks/pre-push`; activate once with `cli.py install-hooks` |
| 3 | **On push to main (GitHub)** | `.github/workflows/publish-library.yml` — the authoritative publish |
| 4 | **Blender button** | sidebar panel; runs `core/` on a worker thread so the UI never freezes |

All four funnel through `source/cli.py`, so there is one code path to reason about.

The git hook is tracked in the repo rather than living in `.git/hooks`, so it is
versioned. `install-hooks` sets `core.hooksPath` to this tool's `hooks/` folder.
**The hook never fails a push** — a publish problem must not stand between you and
your remote; it logs to `.last_publish/hook.log` and returns 0.

Trigger 3 needs three repo secrets: `GDRIVE_SERVICE_ACCOUNT` (the JSON, pasted
whole), `GDRIVE_TEAM_DRIVE_ID`, `GDRIVE_TARGET_PATH`. It defines the rclone remote
purely through `RCLONE_CONFIG_*` env vars, so no `rclone.conf` is ever needed.

---

## Configuration

`publish_config.json`, edited through `/publish-library-config` or the CLI. Never
hand-edit it — `config set` validates keys and **rejects unknown ones**, so a typo
fails loudly instead of writing dead config.

**The config is deliberately NOT tracked in git.** It holds machine paths
(`repo_root`, the rclone executable) and, more importantly, the destination's
Shared Drive id and internal folder path — and this repository is public. A fresh
clone generates its own:

```
python source/cli.py config init      # writes a complete default
python source/cli.py config doctor    # then tells you what is still missing
```

```
python source/cli.py config show
python source/cli.py config set delivery.rclone.remote=st3e_gdrive
python source/cli.py config set criteria.geonode_layout.mode=block
python source/cli.py config set 'triggers.git_hook.branches=["main","release"]'
python source/cli.py config doctor      # checks tools, credentials, paths
```

Sections: `source`, `scope`, `catalog`, `delivery`, `criteria`, `criteria_policy`,
`triggers`, `manifest`, `blender`. See the slash command for the full key map.

### Criteria — the quality gates

Each check is `off` | `warn` | `block`:

| Check | Catches |
|---|---|
| `geonode_layout` | R1–R11 layout violations. **Drives `LLMGeonodePipeline/layout_audit.py` directly** rather than reimplementing it, so the publish bar and the authoring bar cannot drift apart |
| `asset_marked` | a `.blend` with nothing marked as an asset — invisible in the browser |
| `catalog_assigned` | assets in no catalog, or a UUID absent from the catalog file |
| `no_external_deps` | absolute-path library links and missing textures — these break for everyone else on the drive |

`criteria_policy.on_block` decides what a `block` failure does: `skip_file`
(withhold that file, publish the rest, exit non-zero), `abort_publish`, or `ignore`.

Two behaviours worth knowing:

- **All checks off ⇒ Blender is never launched** and the publish is pure file I/O.
  Any check on costs one headless Blender pass, ~2.5 s per `.blend`.
- **A `block`-mode check that cannot run fails the publish.** If you asked for a
  gate and Blender is unavailable, publishing anyway would silently downgrade you
  to no gate at all. This is why the GitHub Action switches checks off explicitly
  unless it installed Blender.

Blender auto-links its own essentials brush libraries into every file with absolute
paths, and linked datablocks are not ours to publish — both are filtered out
(`criteria.no_external_deps.ignore_bundled_libraries`). Without that filter,
`no_external_deps` in its default `block` mode withholds nearly the whole library.

---

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

---

## Everyday use

```
python source/cli.py status            # what would ship + the diff; writes nothing
python source/cli.py check --verbose   # criteria only (launches Blender)
python source/cli.py publish           # for real
python source/cli.py publish --force   # even if nothing changed
python source/cli.py --dry-run publish # full run, no writes
```

`status` is always safe. A publish with no changes skips delivery entirely rather
than re-uploading; incrementality comes from content hashes in the manifest plus
the backend's own checksum comparison.

---

## Notes

- Working state (`.staging/`, `.staging_batch/`, `.last_publish/`) is gitignored.
- The manifest cache in `.last_publish/` is what makes runs incremental. If it is
  missing (fresh clone, CI runner) the publisher fetches the manifest from the
  drive with `rclone cat`; failing that it falls back to a full comparison.
- `delivery.atomic` swaps the tree in place and is for **local** backends. For
  rclone, atomicity comes from `--delete-after`: stale files are removed only once
  every upload has succeeded, so a failed run never leaves holes in the library.
