# ST3E geonode modifier — build recipe and publish traps

Start here for any ST3E geonode-modifier work under `Blender/Geonodes/`. The step-by-step
procedure (menu requirements, Selection gate, icon steps) is `Blender/Geonodes/AUTHORING.md`;
the layout and interface rules are `Blender/Addons/LLMGeonodePipeline/GEONODE_CRITERIA.md`.

**What exists → `Blender/Geonodes/README.md`; how each was built → its `Blender/Geonodes/_build/` script.**

- [Build recipe](#st3e_gn_build_recipe)
- [Publish traps](#st3e_gn_publish_traps)
- [Retiring a geonode](#st3e_gn_retire_checklist)

<a id="st3e_gn_build_recipe"></a>

## Build recipe

*The ordered steps for a new or changed ST3E modifier, each linking the page that holds the details*

1. **Target Blender 5.0, build headless** when no live MCP is connected
   (`blender --background --factory-startup <file> --python <s>.py`; flush stdout +
   `os._exit(0)` after save). Verify live when you can. →
   [headless](../headless-and-automation.md#feedback_blender_version_and_headless)
2. **Ship a demo object** with the modifier attached and save a full mainfile. →
   [asset files](asset-files.md#feedback_geonode_file_needs_object)
3. **Author the graph** with the Blender 5 idioms: Menu defaults and overrides
   ([menus](sockets-and-menus.md#feedback_gn_menu_socket_default)), one menu → master
   `MenuSwitch(INT)` → Index Switches ([pattern](sockets-and-menus.md#feedback_gn_menu_to_index_switch)),
   GN math is float32. Frame and label every node.
4. **Adding a socket to a published tool:** declare it last, then `move_to_parent` it. →
   [identifiers](sockets-and-menus.md#gn_socket_identifiers_by_creation_order)
5. **Selection:** route it through `GNG_SelectionGate` in a `Selection` panel (AUTHORING.md,
   "Selection gate").
6. **Deformers:** Center + gizmo + Symmetry + Affect Axes + preview cage, and direction by
   axis or empty. → [deformers](techniques.md#feedback_gn_deformer_center_gizmo_symmetry),
   [direction](techniques.md#feedback_gn_object_direction_axis)
7. **Panels, names, tooltips:** GEONODE_CRITERIA "Interface (socket) conventions".
8. **Lay out and gate the save:** `run_pipeline.py -- <GN_X>` in `LLMGeonodePipeline/`
   (tidy → `layout_audit.py` R1–R13 → geometry-unchanged) or the `geonode-layout-mcp` skill. →
   [layout traps](layout.md#feedback_gn_node_layout_spacing)
9. **Publish:** AUTHORING.md "Making a group appear under Add Modifier → ST3E", plus the
   [publish traps](#st3e_gn_publish_traps) below.
10. **Icon:** skill `geonode-icons` (`_icons/icon.py probe → build → ship`). →
    [icon pipeline](asset-files.md#project_geonode_icon_pipeline)
11. **Verify:** effect happens, identity at neutral parameters, no NaN, gizmo on/off vert count
    equal, a top-down render of the demo file. Delete throwaway `_*.py`.

**How to apply:** follow the steps in order. Once a file has been tidied or holds user test
objects, change it with a metadata-only or patch script (`_build/publish_gn_mosaic.py`,
`_build/patch_gn_*.py`), never by re-running its builder.

<a id="st3e_gn_publish_traps"></a>

## Publish traps

*The Add Modifier → ST3E menu needs asset mark + leaf catalog + Geometry in/out + `is_modifier` + `ST3E` tag; the misses are invisible in the Asset Browser*

The checklist itself is in `Blender/Geonodes/AUTHORING.md`. Catalogs
(`Blender/blender_assets.cats.txt`; library root = `Blender/`):

| catalog | UUID | use |
|---|---|---|
| `ST3E` | `f9ab2fa9-3a4e-491a-abaa-558cd5c029d0` | root — **never** assign an asset here |
| `ST3E/Deform` | `bacd112a-8e87-47c2-afbc-818a11c75c08` | modifiers |
| `ST3E/Generate` | `8872522f-45b7-4541-a557-5b69bcbfcee2` | modifiers |
| `ST3E/Modify` | `9b90781b-f051-4cdb-9dcb-c8909914a87b` | modifiers |
| `ST3E/Scatter & Instancing` | `25b9ecc2-4cf7-41b3-83c3-152a2eccbc77` | modifiers |
| `ST3E/Shading` | `3c7d5e91-2b64-4f8a-9d13-6a0e5f2c8b47` | shader groups |
| `ST3E/Group` | `5d2a7c14-9e3b-4f06-8c72-1b4e6a9d3f58` | `GNG_*` / helper groups |

- **`is_modifier` defaults OFF** on new groups. The Asset Browser shows the asset anyway, so
  the only symptom is absence from the Add Modifier menu (the GN_ShearGeometry bug). Set
  `is_modifier=True`, `is_tool=False` on the deliverable group only — never on `GNG_*` or other
  helpers, which are asset-marked for node-editor reuse.
- **The tag is separate from the catalog:** `asset_data.tags.new("ST3E")`. Normalize stray tags.
- **Build scripts copied from old ones carry the root UUID.** Sweep all files in one headless
  pass with `bpy.data.libraries.load(f, assets_only=True)` and print `asset_data.catalog_id`.
  That call raises "Cannot load from the current blend file" for the file that is open — skip it.
- **Only the original carries the asset mark.** Local copies of a group in other files get
  `asset_clear()` (+ fake user). An append audit can't tell linked from local copies — open the
  file and check `ng.library`.
- Fill socket `description`s and `asset_data.description` (the browser tooltip). Only fill
  EMPTY descriptions, and only on the home group (the one named after the file).
- `GN_VariousTest.blend` is scratch; `GN_EdgeDestruct.blend` keeps third-party `G_*` helpers on
  foreign catalogs on purpose.

**How to apply:** after publishing, cold-verify by appending the group via `assets_only=True`
into a fresh file: catalog UUID resolves to a leaf, traits set, tooltips filled, it still
evaluates.

<a id="st3e_gn_retire_checklist"></a>

## Retiring a geonode

*Deleting or merging a modifier reaches far beyond its .blend — grep the repo for its name*

Prove the replacement first (e.g. GN_Spherify vs GN_Cast Sphere mode gave bit-identical
evaluated positions across several settings), and check nothing links the group.

**How to apply:** remove or update
- the `.blend` + `.blend1`, `_build/build_*` / `verify_*`, `tidy_layout.TARGETS` and CLI examples;
- `_icons/recipes.py`, `_icons/out/<name>.png` + its row in `out/manifest.json` (a JSON list),
  `_icons/ICONS.md` mentions;
- the `Blender/Geonodes/README.md` row and `DOCUMENTATION_INDEX.md` counts;
- `Blender/Knowledge/DEPENDENCY_REPORT.md` — a dated snapshot: add a "since the scan" note,
  don't fake a re-scan.

Leave alone: LibraryPublisher `.staging` / `.last_publish` manifests (generated — the next
publish rewrites them), unrelated 3ds Max scripts, and prose that only uses the word as an
example. Findings attributed to the old tool are re-attributed, not deleted.
