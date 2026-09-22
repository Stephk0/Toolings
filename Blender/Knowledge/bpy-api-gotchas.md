# bpy API gotchas

Python-API traps that fail silently: stale wrappers, lazy data, modal lifecycle.

> Migrated verbatim from Claude auto-memory on 2026-09-22. Dates and version numbers are from when each note was written — trust the code when they disagree.

- [BMesh is rebuilt on every undo push — never cache it in a modal](#feedback_blender_bmesh_invalidated_by_undo_push)
- [Image.has_data is not a health check; modal operators need cancel()](#feedback_blender_gpu_image_and_modal_teardown)
- [Draw handlers: gate on the datablock (==), not region identity](#feedback_blender_draw_handler_context_gating)
- [Never key sets on id() of bpy wrappers](#feedback_blender_no_id_on_bpy_wrappers)
- [Duplicate names get .001 — free the name first](#feedback_blender_unique_names)
- [Blender 5 links its essentials brushes into every .blend](#feedback_blender_bundled_essentials_false_deps)

<a id="feedback_blender_bmesh_invalidated_by_undo_push"></a>

## BMesh is rebuilt on every undo push — never cache it in a modal

*A modal started from inside a {'REGISTER','UNDO'} operator outlives the BMesh it captured - the undo push rebuilds it and cached BMLoopUV writes vanish with no error*

Found fixing Tile UV Projector fine adjust (v1.4.0 → v1.4.1), see
(`Blender/Addons/TileUVProjector/`).

**Blender rebuilds the edit-mesh BMesh on every undo push.** If a modal operator
captures BMesh elements in `invoke()` and is *launched from inside another
operator flagged `{'REGISTER', 'UNDO'}`*, that operator pushes an undo step the
moment it returns — so the modal's very first event is already working against
an orphaned BMesh.

The failure mode is the nasty one: **no exception**. Writes to the stale
`BMLoopUV` succeed into the orphan, `bmesh.update_edit_mesh(mesh)` flushes the
*current* BMesh instead, and nothing moves on screen. It reads as "my transform
maths is wrong" when the maths is fine.

**The mesh datablock reference is the part that actually kills you.** Caching
`context.active_object.data` in `invoke()` and passing it to
`bmesh.from_edit_mesh()` on later events returns a THROWAWAY BMesh rebuilt from
that datablock, not the live edit BMesh. Writes land in a copy that is discarded
before the next event — and they read back correctly immediately after
assignment, so a debug trace of `before -> after` looks perfect. The tell is that
`before` is the pristine original on EVERY event.

Resolve the mesh from live context every time:

```python
def _edit_mesh(self, context):
    obj = getattr(context, "edit_object", None) or context.active_object
    if obj is None or obj.type != 'MESH' or obj.mode != 'EDIT':
        return None
    return obj.data                            # never cache this

def _fetch_loops(self, context):
    bm = bmesh.from_edit_mesh(self._edit_mesh(context))
    return get_selected_face_uv_loops(bm, bm.loops.layers.uv.active)
```

Never cache the BMesh, its elements, OR the mesh they came from across modal
events. Same trap applies to any modal that survives an operator call, an undo,
or a mode toggle.

**Verify persistence once.** Re-read one element on the second apply and compare
against what was written; report loudly on mismatch. This failure mode is
invisible from inside the transform and cost four releases to find.

**Do NOT "optimise" the flush.** `bmesh.update_edit_mesh(me,
loop_triangles=False)` looks right for a UV-only edit and produces the SAME
silent symptom: the viewport draws textures from the tessellated loop data, so
the UVs change in the mesh and the screen keeps showing the old ones. Always use
the plain full `bmesh.update_edit_mesh(mesh)`, then `area.tag_redraw()` on every
VIEW_3D and IMAGE_EDITOR. This cost an extra release on top of the BMesh bug —
two different causes, one identical "nothing happens" symptom.

Collect elements with the same helper and iteration order the working operators
already use, rather than inventing index-based re-resolution: fewer API
assumptions (`face.loops[i]`, `ensure_lookup_table()`) that cannot be verified
without a live Blender.

One related detail from the same fix:
- A drag driven by `now_distance / start_distance` is dead when the drag starts
  on the anchor (ratio pinned at 1.0). Soften it:
  `(now_d + K) / (start_d + K)` with K ≈ 60px — zero movement still yields
  exactly 1.0 at any starting distance. For angle drags, wrap the delta with
  `(a + pi) % (2*pi) - pi` or crossing the ±pi seam snaps a half turn.

**Why:** silent no-ops are far more expensive to diagnose than crashes, and the
guard-everything-in-try/except reflex actively hides them. Make the failure path
report once (status bar + console) instead of returning None quietly — three
release cycles were spent guessing at a bug that could have announced itself.
Correctness first: never add a performance shortcut to a code path that has not
yet been seen working.

Also consume `INBETWEEN_MOUSEMOVE` alongside `MOUSEMOVE` in modal transforms —
high-rate mice and tablets send mostly the former.

**How to apply:** In any Blender modal touching mesh data, re-resolve the edit
object, its mesh, the BMesh and its elements from live context on every event. Related: [bpy API gotchas](bpy-api-gotchas.md#feedback_blender_gpu_image_and_modal_teardown),
[bpy API gotchas](bpy-api-gotchas.md#feedback_blender_no_id_on_bpy_wrappers).

<a id="feedback_blender_gpu_image_and_modal_teardown"></a>

## Image.has_data is not a health check; modal operators need cancel()

*Image.has_data/size are NOT health checks (lazy loading + reload() frees the buffer) - only a missing file is a real error; and modal operators need cancel() or their class state leaks*

Learned while fixing Tile UV Projector v1.3.0 → v1.3.1
(see `Blender/Addons/TileUVProjector/`).

**1. `Image.has_data` and `Image.size` are NOT validity checks.** Blender loads
image buffers lazily and frees them under its image cache limit, and
`Image.reload()` *deliberately* drops the buffer so it is re-read on next use.
So a perfectly good texture reports `has_data == False` and `size == (0, 0)`
most of the time — and **always** in the moment right after a reload. Gating on
them condemns working images: valid atlases showed "no pixel data", the Reload
button reported failure on every press, and the picker opened onto an empty grid.

The only condition that reliably produces Blender's magenta *missing image*
texture is **the file not existing on disk**. Check that instead:

```python
def image_is_resolvable(img):
    if img.source in {'GENERATED', 'VIEWER'} or img.packed_file:
        return True
    path = bpy.path.abspath(img.filepath_raw, library=img.library)
    return os.path.exists(path) if path else bool(img.has_data)
```

Then just call `gpu.texture.from_image(img)` — **requesting the GPU texture is
what makes Blender load the buffer**. Do not try to pre-verify it. Cache the
`os.path.exists` result behind a refresh token; a draw handler runs per frame.

Related trap that is real: `gpu.texture.from_image()` does not raise for a truly
missing image, it returns the magenta placeholder, so `try/except` around it
never fires. Handle that by checking the path, not the buffer. Useful fallback
when the full-res buffer is unavailable: build a GPUTexture from the preview
thumbnail (`img.preview.image_size` + `image_pixels_float.foreach_get` →
`Buffer('FLOAT', n, px)` → `GPUTexture((w,h), format='RGBA16F', data=buf)`) —
that is literally the picture `template_icon` shows.

**2. Modal operators need `cancel(self, context)`.** Blender tears a modal down
without routing through `modal()` on file load, area close, script reload, or an
undo that swallows it. Any class-level `_is_active` flag then stays True forever
and its `poll()` blocks the operator from ever running again — the button looks
alive but does nothing. Fix with all three: a `cancel()` that cleans up, a
`@persistent load_post` reset, and a self-healing check that treats
"`_is_active` True but draw handle is None" as not running.

**Why:** Both look like "the tool broke after I reloaded a texture", so they get
misdiagnosed as addon logic bugs. And the has_data trap is worse than the
original bug — it breaks the working case, not just the broken one.

**How to apply:** Never gate rendering on `has_data`/`size`. Gate on the file
path. Give every modal operator a `cancel()` plus a load_post state reset.
Related: [bpy API gotchas](bpy-api-gotchas.md#feedback_blender_draw_handler_context_gating).

<a id="feedback_blender_draw_handler_context_gating"></a>

## Draw handlers: gate on the datablock (==), not region identity

*Space-type draw handlers fire for ALL areas with transient context wrappers — gate on persistent datablock (==), never region/area wrapper identity (is)*

A `bpy.types.SpaceXxx.draw_handler_add(..., 'WINDOW', 'POST_PIXEL')` handler is
**global to that editor type** — it fires for every area/region of that type, and
inside it `bpy.context.region`/`context.area` are **fresh transient wrappers**,
not the objects you captured at registration. So `if bpy.context.region is not my_region: return` always returns early → handler draws nothing.

**Why:** bpy wrappers are recreated per access; `is` on region/area wrappers
fails. (Same root cause as [bpy API gotchas](bpy-api-gotchas.md#feedback_blender_no_id_on_bpy_wrappers), different
symptom — there it was dedup sets, here it's draw-handler gating.)

**How to apply:** gate on the persistent **datablock** with `==`, and read the
live region/space from context at draw time:
```python
def draw():
    space = bpy.context.space_data
    region = bpy.context.region
    if space is None or region is None: return
    shown = getattr(space, "edit_tree", None) or getattr(space, "node_tree", None)
    if shown != my_tree: return          # datablock compare, persistent
    v2d = region.view2d                   # live region, exact view2d
    ...
```
Caught while building the GeoNode Layout MCP (`blender-geonode-layout-mcp`): the
node-index stamps silently failed to render into `screenshot_area` captures until
the guard was switched from region identity to tree-datablock equality. Verified
live in Blender 5.0 — see [Headless Blender and automation](headless-and-automation.md#reference_blender_mcp).

<a id="feedback_blender_no_id_on_bpy_wrappers"></a>

## Never key sets on id() of bpy wrappers

*Never use Python id() of bpy struct wrappers (LayerCollection, Collection, Object) as an identity/visited key — wrappers are transient and id()s get recycled, causing false collisions*

Blender re-creates the Python wrapper object for a bpy struct on **every attribute access** (e.g. `lc.children`, `lc.collection` each hand back a fresh throwaway wrapper). Once a temporary wrapper is garbage-collected, CPython freely **recycles its `id()`** for the next wrapper. So a `visited = set()` keyed on `id(wrapper)` produces **false "already visited" hits**, and a tree/graph walk can abort early.

**Real bug it caused:** MassExporter `_get_layer_collection_path` used `id(lc)` in its BFS visited-set. On a deep real scene it returned `[]` for a nested collection, which silently disabled the whole unhide pipeline → eye-hidden parent collections (`LayerCollection.hide_viewport`) were never revealed → nested objects exported wrong/empty. A minimal 2-level test passed (no id collision), masking it. Fixed in MassExporter v13.6.2 by keying the visited-set on `lc.collection.name`. Same bug existed in a `seen_colls = {id(coll)}` dedup, also fixed.

**Why:** id() of a bpy wrapper is NOT a stable identity — it identifies the short-lived Python object, not the underlying Blender datablock.

**How to apply:** For visited-sets / dedup / membership over bpy structs, key on something stable: the datablock **name** (unique per blend for collections/objects), or use `==` comparison (bpy implements it by underlying data pointer), or hold a single materialized list of wrappers and reuse those exact references. Verify graph/tree walks against a DEEP real hierarchy, not just a 2-level toy. Relates to [Export pipeline](export-pipeline.md#feedback_blender_master_layercollection_exclude) and [Headless Blender and automation](headless-and-automation.md#feedback_blender_version_and_headless).

<a id="feedback_blender_unique_names"></a>

## Duplicate names get .001 — free the name first

*Blender auto-appends .001/.002 to duplicate object names — always rename explicitly after duplication to avoid name pollution in exports or data references*

Blender enforces unique names across all objects in `bpy.data.objects`. When you duplicate an object, the copy gets `.001` appended automatically if the original name is taken.

**Why:** This bit us when creating temporary modifier-apply copies for export — the copy came out as `ObjectName.001` instead of `ObjectName`, so exported files had wrong mesh names.

**How to apply:** Whenever creating a temporary duplicate that should impersonate the original name:
1. Rename the original to a guaranteed-unique temp: `obj.name = f"__temp_{obj.name}"`
2. Assign the real name to the copy: `copy.name = original_name`
3. In cleanup: **delete copies first**, then rename originals back — if you rename original while the copy still holds the name, Blender creates a conflict again.

Pattern:
```python
original_name = obj.name
obj.name = f"__temp_{original_name}"   # free up the name
copy.name = original_name              # copy gets the clean name

# cleanup:
bpy.ops.object.delete()                # delete copies first
obj.name = original_name               # then restore — no conflict
```

<a id="feedback_blender_bundled_essentials_false_deps"></a>

## Blender 5 links its essentials brushes into every .blend

*Blender 5 auto-links its essentials brush libraries into EVERY .blend with absolute paths — any self-contained/asset-inventory audit must filter linked datablocks and install-dir libraries or it flags every file*

Blender 5 silently links its own **essentials brush** asset libraries into every
`.blend` (`essentials_brushes-mesh_sculpt.blend`, `…-mesh_vertex.blend`) as
**absolute paths into the install dir**. Two consequences for any audit that asks
"is this file self-contained?" or "what assets does this file own?":

1. `bpy.data.libraries` contains absolute-path entries in a pristine file. An
   "absolute library link = broken portability" check flags **every single file**.
2. Those libraries bring asset-marked datablocks with them (brushes "Paint Hard",
   "Draw") sitting in **Blender's own catalog UUIDs**, not yours. So an asset
   inventory over-counts, and a "are all assets in a known catalog?" check
   complains about catalogs that were never yours.

**Filters that fix it:**

- Skip datablocks where `datablock.library is not None` (and
  `override_library is not None`) — a linked asset is not one this file publishes.
- Treat a library path as bundled when it lives under
  `bpy.utils.resource_path('LOCAL')`, `bpy.utils.resource_path('SYSTEM')`, or
  `os.path.dirname(bpy.app.binary_path)`; belt-and-braces also match
  `datafiles/assets` in the normcased path.
- `bpy.utils.blend_paths(absolute=True, packed=False, local=False)` needs the same
  bundled filter before treating a non-existent path as a missing dependency.

**Why:** caught on LibraryPublisher's first real criteria run — the
`no_external_deps` check (in `block` mode) would have withheld nearly the entire
asset library from publishing. Asset counts also dropped from 2–4 to 1 per file
once linked datablocks were excluded, which is the correct number.

**How to apply:** any headless `.blend` inspection that reasons about
dependencies or asset ownership needs both filters from the start. See
`Blender/Addons/LibraryPublisher/` (`source/checks/blender_inspect.py`,
`_bundled_roots` / `_is_bundled`) and the asset checklist in
[ST3E geonode modifier — build recipe, roster, publish checklist](geonodes/asset-checklist.md).
