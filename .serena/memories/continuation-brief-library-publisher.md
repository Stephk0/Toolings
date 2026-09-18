# LibraryPublisher — continuation brief (updated 2026-08-19)

Publishes the ST3E Blender asset library to a **Google Shared Drive** as `ST3E_Ext`, so the
shared copy loads *beside* the local library in Blender's Asset Browser instead of merging
into it. Built from scratch this session; live and publishing.

## Context

`Blender/Addons/LibraryPublisher/` — **v1.3.0**, 181 pytest tests (none import
bpy). WMH split: bpy-free `core/` + `blender/` UI + `checks/` (run INSIDE headless Blender) +
`cli.py`. Every trigger funnels through `source/cli.py`, so there is one code path.

```
core/  config selection catalogs criteria manifest delivery publish shell
checks/ blender_inspect.py (criteria facts) · blender_remap_catalogs.py (rewrites catalog_id)
```

**Destination:** `DistrictSharedDrive:3D/Tooling/Blender/ST3E_Ext` (team drive
`0APZXuAVWoNn5Uk9PVA`). Deliberately a **fresh subfolder** — the sibling
`3D/Tooling/Blender/{Geonodes,Addons,Geonodes_External}/` is a hand-made older mirror (418
objects) that must stay untouched; `rclone sync` cannot reach outside its own destination, so
`delete_extraneous` is safe to leave on.

**rclone:** `D:\Stephko_Tooling\Toolings\rclone\rclone.exe` (v1.75.0), gitignored — it lives
inside the repo and is 85 MB. Path is in `delivery.rclone.executable`; it does not need PATH.

**Currently on the drive:** 109 objects / 25.6 MiB, published from commit `2087fe9`, still
using **`rename_paths`** (shared UUIDs). The remap is built and verified but NOT yet published.

## Progress

**Committed and pushed** (`main` in sync with `origin/main` @ `2e35d9f`):
- `3fe7035` LibraryPublisher v1.0 (tool, workflow, slash commands, gitignore)
- `edba0b7` fixed GN_Mosaic stale weak-ref + un-marked GNG_VertexChannel as an asset
- `1458c41` TileUVProjector v1.6.0 · `921e2b0` SH_ScreenCavity (user's work, committed on request)
- `2e35d9f` CI workflow skips cleanly when credentials are absent

**UNCOMMITTED — the v1.3.0 work:** `remap_uuids` mode, `strip_segments`, dot-folder exclusion,
README + slash-command docs, `distribution/LibraryPublisher_v1.3.0.zip`.

**Working tree has ~71 uncommitted entries and most are NOT LibraryPublisher** —
LLMGeonodePipeline changes, many modified `Blender/Geonodes/*.blend`, MassExporter docs.
Do not sweep-commit; only ever commit LibraryPublisher paths without asking.

## Decisions

- **Catalog transform, Variant A → B.** Started `rename_paths` (rewrite paths, keep UUIDs →
  published .blend files are byte-identical copies, no Blender needed). User hit the predicted
  UUID collision, so `remap_uuids` was added: new ids from
  `uuid5(catalog.uuid_namespace, original_uuid)` — a hash, deterministic forever.
  **Crucial second half:** assets key on the UUID, so the published .blend copies must also be
  rewritten (`asset_data.catalog_id`) or every asset shows as *Unassigned*.
  `catalog_simple_name` is read-only in Blender — don't try to set it.
- **Never touch the source.** Staged `.blend` files are physically COPIED (never hardlinked)
  when remapping, so a write can't reach the repo. Verified: staged `GN_Bend` carries
  `651ea579…`, repo file still `bacd112a…`, git clean.
- **Staging is persistent + incremental** (`.staging/` + `.staging_state.json`). A file is
  re-copied and re-remapped only when its source hash OR the catalog *fingerprint* changed.
  Full run (criteria over 59 + remap over 49) ≈ 29 s.
- **`publish_config.json` is gitignored** — the repo is PUBLIC and the config holds the Shared
  Drive id, internal paths and machine paths. Fresh clone runs `cli.py config init`.
- **Criteria:** `no_external_deps` = block, others warn; `on_block: skip_file`. Withholding
  files exits **3** so CI can't go green while the library shrinks. A block-mode check that
  *cannot run* fails the publish rather than silently becoming no gate.
- **Two false-positive filters, both found on real data:** Blender 5 auto-links its essentials
  brush libraries into every file (absolute paths), and `<temp>/copybuffer.blend` + headless
  scratch copies live in the OS temp dir. Without both filters `no_external_deps` withheld
  nearly the whole library.
- **Addons ship as self-contained folders:** `README.md` + `TUTORIAL.md` + `assets/**` + the
  current zip, with `strip_segments: ["distribution"]` removing the pointless level.
- **CI is optional.** No repo secrets exist, so the workflow now skips green with a notice
  naming the three secrets. Local publishing is the primary path.

## Next Steps

1. **Commit the LibraryPublisher v1.3.0 changes** (only those paths).
2. **`/publish-library`** to take `remap_uuids` live. Expect ~49 .blend files to re-upload with
   new ids; anyone with the shared library loaded sees the catalogs replaced. Last dry run:
   10 added, 60 changed, 3 removed.
3. **Verify in Blender** that `ST3E` and `ST3E_Ext` now show as two separate trees in the Asset
   Browser's *All Libraries* view — this is the whole point and is still unproven.
4. Register the drive folder in Blender (`…/ST3E_Ext`), mark it *Available offline* in Drive for
   Desktop. Do NOT also register the parent `3D/Tooling/Blender/` — its old cats.txt declares
   `ST3E_Ext` on the same UUID and would collide.
5. Optional: `cli.py install-hooks` (sets `core.hooksPath`; not yet active, so pushes publish
   nothing). Optional: create a GCP service account + the 3 repo secrets to enable CI.

## Open Questions

- **Does the remap actually fix the Asset Browser collision?** Unverified — needs a look in
  Blender after publishing. If it does not, the mechanism is sound and the problem lies
  elsewhere (e.g. both folders registered).
- **6 files are withheld every publish** for genuinely broken external deps:
  `GN_DisplaceByImage` (4 missing .tif under `D:\Work_DistrictGames\`), `GN_EdgeDestruct` and
  `GN_MeshFromImage` (absolute Dropbox links), `GN_Solidify2` (bradley_geo_nodes_presets),
  `GN_ExtrudeSelection` (missing Higgsas lib), `GN_treeGenerator_03` (missing .py text blocks).
  Fixing these is unstarted.
- `catalog.stamp_header` writes the commit SHA into `cats.txt`, so that file changes after
  **every** commit and "nothing changed → skip" rarely fires. Set `stamp_header=false` if the
  short-circuit matters more than the in-file stamp.
- 7 tools ship a README with no zip (AddBoundsToName, Center Edges, Edit Mode Overlay, Smart
  Collapse, Smart Crease, Smart Set Orientation, Toggle Modifier Display) — some were built
  since; confirm whether README-only tools should publish at all.
- `GN_AttributeFunctions_4.5.blend` has 4 asset-marked `GNG_` helpers on the null catalog UUID —
  same defect as the fixed `GNG_VertexChannel`, left alone because that file may intend to
  expose its helpers.
- TileUVProjector `source/__init__.py` and `source/tile_uv_projector.py` are **byte-identical,
  2750 lines each** (pre-existing). They will drift the first time one is edited.
- **Never change `catalog.uuid_namespace`** once anything has shipped — it re-derives every id
  and orphans what is already on the drive.
