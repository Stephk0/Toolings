---
description: Set up or change how the Blender library publishes to the Google Shared Drive
argument-hint: [show | doctor | init | a plain-English change, e.g. "block on geonode layout"]
allowed-tools: Bash(python:*), Bash(git:*), Read, Glob, AskUserQuestion
---

# Configure the library publisher

Interactive setup for `Blender/Addons/ClaudeVibe_WIPs/LibraryPublisher/publish_config.json`
— destination, scope, catalog renaming, criteria and triggers.

Request: **$ARGUMENTS**

CLI (the only way to write the file — never hand-edit the JSON, `set` validates
keys and rejects typos):

```
python "Blender/Addons/ClaudeVibe_WIPs/LibraryPublisher/source/cli.py" config show
python "…/source/cli.py" config doctor
python "…/source/cli.py" config set <dotted.key>=<json-or-bare-value> [...]
python "…/source/cli.py" config init [--force]
```

## What to do

1. **Always read the current state first** with `config show`. Then act on
   `$ARGUMENTS`:
   - `show` / empty → present the current config in a readable summary and stop
   - `doctor` → run `config doctor` and report what is missing
   - `init` → only if no config exists yet, or the user explicitly asked to reset
   - anything else → translate their plain-English request into `config set`
     calls using the key map below

2. **Confirm before writing** when a change is destructive or wide-reaching
   (disabling a whole scope, turning the catalog rewrite off, switching backend).
   For a single unambiguous tweak, just make it and say what you set.

3. **After any `set`, re-run `config show`** and report the resulting state plus
   any remaining problems. `set` prints outstanding validation problems itself —
   relay them, don't hide them.

4. Do not run a publish from this command. Point at `/publish-library` instead.

## Key map

**Destination — Google Shared Drive via rclone (the CI-capable path)**

| what | key |
|---|---|
| backend | `delivery.backend` = `rclone` \| `robocopy` \| `copy` |
| rclone remote name | `delivery.rclone.remote` |
| path to rclone.exe (not needed if on PATH) | `delivery.rclone.executable` |
| folder inside the drive | `delivery.rclone.path` |
| Shared Drive id | `delivery.rclone.team_drive` |
| service-account env var | `delivery.rclone.service_account_env` |
| mounted-drive path (robocopy/copy) | `delivery.local.path` |
| remove files the source no longer has | `delivery.delete_extraneous` |
| local swap-in-place instead of file-by-file | `delivery.atomic` |
| never write anything | `delivery.dry_run` |

`delivery.rclone.executable` accepts a file OR the unzipped folder, and expands
env vars. A path that does not resolve is an error, never a silent fallback to
PATH. Warn if it points inside `Downloads`: the folder name carries the version,
so a future rclone upgrade breaks it.

If they have no rclone remote yet, walk them through it rather than guessing:
`rclone config` → `n` → name it → `drive` → leave client id/secret blank →
scope `1` (full) → advanced `n` → for a Shared Drive answer yes to the team
drive question and pick it from the list. For a service account instead, set
`service_account_file` and share the Shared Drive with that account's email as
Content manager.

**Scope — what gets published**

- `scope.entries.<i>.enabled` — toggle a whole scope (0 = geonodes, 1 = shading,
  2 = addon_zips by default; confirm the index with `config show` first)
- `scope.entries.<i>.include` / `.exclude` — JSON arrays of globs; `**` crosses
  directories, a pattern with no `/` matches the basename at any depth
- `scope.entries.<i>.dest` — folder name on the drive
- `scope.entries.<i>.flatten` — collapse subfolders (used for the addon zips)

To add a whole new scope entry, append to the `scope.entries` array — that needs
a small edit rather than a `set`, so read the file, add the object with the same
shape as its siblings, and validate afterwards.

**Catalog renaming — the ST3E_Ext side-by-side trick**

| what | key |
|---|---|
| rewrite on/off | `catalog.enabled` |
| mode | `catalog.mode` = `rename_paths` (keeps UUIDs) \| `off` |
| the rename rules | `catalog.rename` = `[{"from":"ST3E","to":"ST3E_Ext"}]` |
| simple-name separator | `catalog.simple_name_separator` |

Explain the trade-off if they ask: `rename_paths` keeps every catalog UUID, so
the published `.blend` files are byte-identical copies and no Blender pass is
needed. The cost is that both libraries define the same UUIDs under different
paths. If that ever misbehaves in the Asset Browser's "All Libraries" view, the
fix is a UUID remap, which needs a headless Blender pass over every file —
a bigger change, not a config flag.

**Criteria — quality gates, per check**

Each check takes `off` | `warn` | `block`:

| check | key | what it catches |
|---|---|---|
| geonode layout R1–R11 | `criteria.geonode_layout.mode` | unframed/overlapping graphs; drives `LLMGeonodePipeline/layout_audit.py` so the publish bar equals the authoring bar |
| asset marked | `criteria.asset_marked.mode` | a `.blend` with nothing marked as an asset — invisible in the browser |
| catalog assigned | `criteria.catalog_assigned.mode` | assets in no catalog, or a UUID absent from the catalog file |
| self-contained | `criteria.no_external_deps.mode` | absolute-path library links and missing textures — these break for everyone else on the drive |

Related keys:
- `criteria.<check>.applies_to` — which scope entries it runs on
- `criteria.geonode_layout.blocking_rules` — which audit rules count as hard
  failures rather than advisories
- `criteria_policy.on_block` = `skip_file` (withhold that file, publish the rest,
  exit non-zero) | `abort_publish` (deliver nothing) | `ignore`
- `criteria_policy.verbose` — list passing files too

Two things worth telling the user: any check that is not `off` makes a publish
launch Blender once (adds ~1–3 s per `.blend`), and a `block`-mode check that
cannot be run at all — no Blender available — fails the publish rather than
quietly skipping the gate.

**Triggers**

| trigger | keys |
|---|---|
| manual | `triggers.manual.enabled` |
| git hook | `triggers.git_hook.enabled`, `.hook` (`pre-push` \| `post-commit`), `.branches` (JSON array), `.background` |
| GitHub Action | `triggers.github_action.enabled`, `.branches`, `.paths` |
| Blender button | `triggers.blender_button.enabled`, `.refresh_after` |

The git hook needs activating once per clone (it is tracked in the repo, not in
`.git/`):

```
python "…/LibraryPublisher/source/cli.py" install-hooks     # sets core.hooksPath
python "…/LibraryPublisher/source/cli.py" uninstall-hooks
```

`triggers.github_action.paths` mirrors the workflow's own `on.push.paths`. If you
change it here, say clearly that `.github/workflows/publish-library.yml` needs
the same edit — the config cannot reach into the workflow file.

## Guardrails

- `config set` refuses unknown keys by design. If it errors, the key is wrong —
  check `config show --json`, don't work around it by editing the file.
- Never put credentials in the config. The service-account JSON path lives in an
  environment variable, named by `delivery.rclone.service_account_env`.
- `publish_config.json` is gitignored on purpose: this repo is PUBLIC and the
  config carries the Shared Drive id, the internal destination path and machine
  paths. Never suggest committing it, and never echo the team drive id into a
  tracked file. A fresh clone runs `config init`.
- After changing anything that affects what ships, suggest
  `/publish-library status` as the safe next step.
