---
description: Publish the Blender asset library to the Google Shared Drive as ST3E_Ext
argument-hint: [status | check | dry-run | force] (default: status then publish)
allowed-tools: Bash(python:*), Bash(git:*), Read, Glob
---

# Publish the Blender asset library

Publishes the curated Blender library (geonodes, shading, current addon zips) to
the Google Shared Drive, with catalog paths renamed to `ST3E_Ext` so it sits
beside the local library in Blender's Asset Browser instead of merging into it.

Tool root: `Blender/Addons/ClaudeVibe_WIPs/LibraryPublisher`
Everything below is a thin wrapper over `source/cli.py` — the same entry point
the git hook, the GitHub Action and the Blender button all use.

Requested mode: **$ARGUMENTS** (empty means: report, then publish for real)

## What to do

1. **Always start with a report.** Run:

   ```
   python "Blender/Addons/ClaudeVibe_WIPs/LibraryPublisher/source/cli.py" status
   ```

   That never writes anything. Show the user, in your own words:
   - how many files are selected, per scope
   - the catalog renames it will apply
   - the incremental diff (added / changed / removed)
   - any warnings, especially a catalog that matched no rename rule (that one
     would collide with the local library and defeat the whole point) or a
     destination collision

2. **Branch on `$ARGUMENTS`:**

   | argument | do this |
   |---|---|
   | `status` (or the word "check the state") | stop after step 1 |
   | `check` | run `cli.py check --verbose` — criteria only, launches Blender, no delivery |
   | `dry-run` | run `cli.py --dry-run publish` |
   | `force` | run `cli.py publish --force` (delivers even when nothing changed) |
   | empty / `publish` | if step 1 showed changes, run `cli.py publish`; if it showed none, say so and stop rather than forcing |

3. **If the config is not ready** (`status` reports "NOT READY" or a config
   error), do not guess values. Tell the user what is missing and point them at
   `/publish-library-config`.

4. **If delivery fails**, run
   `python "…/LibraryPublisher/source/cli.py" config doctor`
   and report which row failed. The usual causes are: rclone not installed, the
   rclone remote not configured, or the service-account env var unset.

5. **Report the outcome plainly.** Include the file count, the commit that was
   published, and the destination. If files were withheld by a blocking criteria
   check, list them — a smaller library than expected must never be silent.

## Guardrails

- Never edit `publish_config.json` from this command. Configuration is
  `/publish-library-config`'s job.
- Never publish from a branch other than the configured ones without saying so
  explicitly first; `status` shows the current branch.
- If the working tree is dirty, mention it — the published `LIBRARY_VERSION.txt`
  records the commit, and a dirty tree means the drive holds something that is
  not in any commit.
- The Shared Drive copy is a build artifact. Never treat it as a source, and
  never sync in the reverse direction.
