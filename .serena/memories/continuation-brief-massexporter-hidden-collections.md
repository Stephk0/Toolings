# Continuation Brief: Mass Exporter — Export Hidden Collections fix

## Context
Mass Collection Exporter (`Blender/Addons/ClaudeVibe_WIPs/MassExporter/source/__init__.py`, Blender 5.0).
User reported "Export Hidden Collections" failing: a collection nested under an eye-hidden parent
(`sk_char_player_skin_flame_001` under `Cosmetic_Flame_001`) was not exported correctly because parent
collections were not being unhidden. Requirement: unhide ALL ancestors up the chain before export.
**Status: SOLVED and verified live in the user's scene. User confirmed "that worked".**

## Progress (COMPLETE)
Two distinct bugs found and fixed in the visibility-isolation core
(`_unhide_collection_for_export` / `_restore_collection_for_export` / `_get_layer_collection_path`):

1. **v13.6.1** — Master-LayerCollection `exclude` cascade leak. Assigning `.exclude` on the master
   (Scene Collection) layer collection cascade-resets every descendant's `exclude` across the view
   layer, wiping state before it was recorded → excluded collections silently re-included after export.
   Fix: never write `exclude` on master (skip via `is_master` flag, stored in 4-tuple backup); restore
   layer collections deepest-first (reverse capture order) because `exclude` is hierarchical.

2. **v13.6.2** (the actual user-reported bug) — `_get_layer_collection_path` BFS used `id(lc)` as its
   visited-set key. Blender re-creates LayerCollection wrappers on every `.children` access and CPython
   recycles freed wrappers' id()s → false "already visited" collisions → search aborts, returns `[]` →
   unhide pipeline does nothing → parent eye stays on. Fix: key visited-set on `lc.collection.name`.
   Same anti-pattern fixed in the `seen_colls = {id(coll)}` dedup (→ `coll.name`).

Verified live: path now resolves full chain; parent eye clears during unhide; both meshes
(`sk_char_player_skin_flame_001` + `_cloth`) become visible+selectable; real export wrote a 1.79 MB
FBX containing both; eye restored to hidden afterward. Test scaffolding (`MX_*` collections) cleaned up.

## Decisions
- Bumped VERSION + blender_manifest.toml to 13.6.2 (both files).
- Deployed source to installed extension at
  `C:\Users\Stephko\AppData\Roaming\Blender Foundation\Blender\5.0\extensions\user_default\mass_collection_exporter\`.
- Archived old zips; built `distribution/MassExporter_v13.6.2.zip` (root-level __init__.py +
  blender_manifest.toml + README.md), verified contains the fix.
- Did NOT run `bpy.ops.script.reload()` — it kills the blender-mcp socket (port 9876). Hot-patched the
  fix into the live session for testing instead.
- Saved two reusable gotcha memories (auto-memory dir): `feedback_blender_no_id_on_bpy_wrappers` and
  `feedback_blender_master_layercollection_exclude`.

## Next Steps
- User should restart Blender (or reinstall MassExporter_v13.6.2.zip) so the fully deployed 13.6.2 is
  active (current session only has the hot-patched path function).
- Changes are uncommitted on branch `main` — commit if/when the user asks.

## Open Questions
- None. Feature confirmed working by user.
