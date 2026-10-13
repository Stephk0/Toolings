# Library Publisher — changelog

## v1.3.1 (2026-10-13)
- **Fix:** the default config still pointed at `Blender/Addons/ClaudeVibe_WIPs`, which no longer
  exists since the addons were flattened into `Blender/Addons`. A fresh `config init` would have
  staged nothing: the source folder, the geonode-layout audit module and the packaged-zip glob now
  use the current paths.
- **Fix:** the sidebar hint for an unset repo path now names `Blender/Addons/LibraryPublisher`.

## v1.3.0 (2026-09-05)
- `remap_uuids` catalog mode: published catalogs get deterministic new UUIDs
  (`uuid5(catalog.uuid_namespace, original)`), and `asset_data.catalog_id` is rewritten in the
  staged `.blend` copies so assets keep their catalog. Staged files that get rewritten are
  copied, never hardlinked.
- `strip_segments` drops the `distribution` level from published paths; dot-folders are skipped.

Earlier versions: see git history (`git log -- Blender/Addons/LibraryPublisher`).
