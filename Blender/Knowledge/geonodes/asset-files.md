# Geonode asset files

What a shipped geonode .blend must contain, how to verify it, and its icon.

- [Every geonode .blend ships an object with the modifier](#feedback_geonode_file_needs_object)
- [Delete the factory Cube from headless demo scenes](#feedback_geonode_demo_scene_hygiene)
- [Asset Browser icon pipeline](#project_geonode_icon_pipeline)

<a id="feedback_geonode_file_needs_object"></a>

## Every geonode .blend ships an object with the modifier

*Save a full mainfile with a demo object using the modifier — never an asset-only `libraries.write` file*

An asset-only file holds the group as a fake-user orphan: opening it shows an empty scene and
the group is hard to reach. Building one inside a live session once left the user with an
empty Geometry Nodes modifier and a "missing" asset.

**How to apply:**
- Build headless (`--factory-startup`), not in the user's live session.
- Create a fitting primitive, `obj.modifiers.new("GN", "NODES").node_group = ng`, select and
  activate it, then `bpy.ops.wm.save_as_mainfile(filepath=path)`.
- Publish per [the build recipe](asset-checklist.md#st3e_gn_build_recipe).
- Several files in one launch: `bpy.ops.wm.read_factory_settings(use_empty=True)` between them.
- Extracting a group from another file: `libraries.write(tmp, {ng}, path_remap='ABSOLUTE')` →
  fresh mainfile → append → purge the stale tmp library entry → demo object → publish → save;
  reset linked helper paths to relative (`//SHG_TileableNoise.blend`).

<a id="feedback_geonode_demo_scene_hygiene"></a>

## Delete the factory Cube from headless demo scenes

*Headless builds ship the factory Cube (plus Light/Camera) next to `GN_Demo`; numeric checks pass, only a render catches it*

`--factory-startup` starts in the default scene, so `save_as_mainfile` keeps its objects. The
Cube has no modifier, so every verify check passes; it reads as part of the tool's output when
the user opens the file.

**How to apply:**
- Before creating the demo object, remove the factory meshes:
  `for o in [o for o in bpy.data.objects if o.type == 'MESH']: bpy.data.objects.remove(o, do_unlink=True)`.
- Finish every build with a **top-down render of the demo file** (Cycles CPU, ~24 samples, ortho
  camera + sun; for tileable output, `obj.copy()` 3×3) and Read the PNG. It catches seams, gap
  shapes and stray objects that field checks can't.
- **Probing a demo file:** the demo object already carries the real modifier, so a stacked probe
  modifier sees the already-processed mesh. Remove existing modifiers first, or read the real one.
- Scene-only fixes to a tidied/published file go in a small script that asserts node
  positions and evaluated vert/face counts are unchanged — never re-run the builder.

<a id="project_geonode_icon_pipeline"></a>

## Asset Browser icon pipeline

*Icons are rendered and embedded headlessly by `Blender/Geonodes/_icons/` — use the `geonode-icons` skill*

The contract is `_icons/ICONS.md`, the findings `_icons/GOTCHAS.md`; `_icons/coverage.py`
lists what still lacks an icon.

**How to apply:** run the skill (`icon.py probe → build → ship`) and look at every PNG — the
`expect=` gate only proves the modifier changed something. Re-probe a group's interface before
writing or re-running a recipe: the user edits the source `.blend`s between sessions.
