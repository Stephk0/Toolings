# bpy API gotchas

Python-API traps that fail silently: stale wrappers, lazy data, modal lifecycle.

- [BMesh is rebuilt on every undo push — never cache it in a modal](#feedback_blender_bmesh_invalidated_by_undo_push)
- [Image.has_data is not a health check; modal operators need cancel()](#feedback_blender_gpu_image_and_modal_teardown)
- [Draw handlers: gate on the datablock (==), not region identity](#feedback_blender_draw_handler_context_gating)
- [Never key sets on id() of bpy wrappers](#feedback_blender_no_id_on_bpy_wrappers)
- [Blender 5 links its essentials brushes into every .blend](#feedback_blender_bundled_essentials_false_deps)
- [Constraining native transforms: post-process in depsgraph_update_post](#finding_native_transform_postprocess)
- [links.new can return None for a socket taken off a removed link](#links_new_stale_socket)
- [activate_init is ignored under use_property_split](#activate_init_property_split)

Duplicate names / `.001`: see [Export pipeline](export-pipeline.md#feedback_blender_unique_names).

<a id="feedback_blender_bmesh_invalidated_by_undo_push"></a>

## BMesh is rebuilt on every undo push — never cache it in a modal

*A modal launched from a `{'REGISTER','UNDO'}` operator outlives the BMesh it captured; writes to cached elements land in an orphan with no error.*

The launching operator pushes an undo step as it returns, which rebuilds the edit BMesh, so
the modal's first event already works on an orphan. Worse: caching
`context.active_object.data` and calling `bmesh.from_edit_mesh()` on it later returns a
**throwaway** BMesh. Writes read back correctly right after assignment, then vanish; the tell
is that "before" values are pristine on every event. Found in Tile UV Projector 1.4.1
(cost four releases).

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

- **Don't "optimise" the flush.** `bmesh.update_edit_mesh(me, loop_triangles=False)` gives
  the same silent symptom for UV edits (the viewport draws from tessellated loops). Use the
  plain call, then `tag_redraw()` every VIEW_3D and IMAGE_EDITOR.
- Consume `INBETWEEN_MOUSEMOVE` along with `MOUSEMOVE`; tablets send mostly the former.
- Ratio drags (`now_d / start_d`) are dead when the drag starts on the anchor; use
  `(now_d + K) / (start_d + K)`, K ≈ 60 px. Wrap angle deltas with `(a + pi) % (2*pi) - pi`.

**Why:** silent no-ops cost far more than crashes, and blanket try/except hides them.

**How to apply:** re-resolve the edit object, mesh, BMesh and elements from live context on
every modal event. Verify persistence once (re-read one written element on the next event)
and report loudly on mismatch.

<a id="feedback_blender_gpu_image_and_modal_teardown"></a>

## Image.has_data is not a health check; modal operators need cancel()

*Buffers load lazily and `reload()` frees them, so `has_data`/`size` are false for good images; and modals torn down outside `modal()` leak class state.*

1. A valid texture reports `has_data == False`, `size == (0, 0)` most of the time and always
   right after `reload()`. Only a missing file gives the magenta texture, so check that:

   ```python
   def image_is_resolvable(img):
       if img.source in {'GENERATED', 'VIEWER'} or img.packed_file:
           return True
       path = bpy.path.abspath(img.filepath_raw, library=img.library)
       return os.path.exists(path) if path else bool(img.has_data)
   ```

   Then call `gpu.texture.from_image(img)`; requesting the texture loads the buffer. It
   returns the magenta placeholder instead of raising for a missing file. Cache the
   `exists` result; draw handlers run every frame. Fallback without the full buffer: build a
   GPUTexture from `img.preview` (`image_pixels_float` → `Buffer('FLOAT', n, px)` →
   `GPUTexture((w, h), format='RGBA16F', data=buf)`).
2. Blender ends modals without calling `modal()` on file load, area close, script reload or
   undo. A class-level `_is_active` then stays True and `poll()` blocks the tool forever.
   Add `cancel()`, a `@persistent` `load_post` reset, and treat "`_is_active` but no draw
   handle" as not running.

**Why:** both look like "the tool broke after reloading a texture" (Tile UV Projector 1.3.1).

<a id="feedback_blender_draw_handler_context_gating"></a>

## Draw handlers: gate on the datablock (==), not region identity

*`SpaceXxx.draw_handler_add` fires for every area of that type with fresh context wrappers, so `context.region is my_region` is always False.*

```python
def draw():
    space, region = bpy.context.space_data, bpy.context.region
    if space is None or region is None:
        return
    shown = getattr(space, "edit_tree", None) or getattr(space, "node_tree", None)
    if shown != my_tree:                 # datablock compare, persistent
        return
    v2d = region.view2d                  # live region at draw time
```

Found when the GeoNode Layout MCP's node-index stamps never rendered (Blender 5.0). Same root
cause as the next section.

<a id="feedback_blender_no_id_on_bpy_wrappers"></a>

## Never key sets on id() of bpy wrappers

*Every attribute access returns a fresh wrapper and CPython recycles freed ids, so `id()`-keyed visited sets report false hits.*

MassExporter's layer-collection BFS (`_get_layer_collection_path`) keyed on `id(lc)` and
returned `[]` on a deep scene, which silently disabled the unhide pipeline; a 2-level test
passed (fixed in 13.6.2).

**How to apply:** key on the datablock name, compare with `==` (compares the underlying
pointer), or keep one materialised list of wrappers. Test tree walks on a deep real
hierarchy.

<a id="feedback_blender_bundled_essentials_false_deps"></a>

## Blender 5 links its essentials brushes into every .blend

*Every file carries absolute-path links to Blender's install-dir brush libraries, with asset-marked brushes in Blender's own catalogs; audits must filter them.*

An "absolute library = not portable" check flags every file, and asset inventories
over-count. Caught on LibraryPublisher's first criteria run: `no_external_deps` in `block`
mode would have withheld nearly the whole library.

**How to apply:**
- Skip datablocks with `library is not None` or `override_library is not None`.
- Treat a library as bundled when it lies under `bpy.utils.resource_path('LOCAL')`,
  `resource_path('SYSTEM')` or `dirname(bpy.app.binary_path)` (also match
  `datafiles/assets`). Apply the same filter to `bpy.utils.blend_paths(absolute=True)`.
- Reference: LibraryPublisher `source/checks/blender_inspect.py` (`_bundled_roots`,
  `_is_bundled`).

<a id="finding_native_transform_postprocess"></a>

## Constraining native transforms: post-process in depsgraph_update_post

*There is no hook into Blender's transform system, but rewriting the selected verts in a `depsgraph_update_post` handler works for every keymap, gizmo and menu, and the undo step keeps the result.*

Measured in a real UI (4.0.2) and headless (5.0) for Geometry Constraint.

- During a modal transform each mouse move recomputes the verts from the stored originals,
  then updates the depsgraph. Rewriting `BMVert.co` there (+ `bmesh.update_edit_mesh`) runs
  before the draw, with no drift.
- On confirm no recalc follows, so the pushed undo step holds the corrected positions.
- `Window.modal_operators` (4.2+) shows a running `TRANSFORM_OT_*`; extrude + move appears
  as its own `MESH_OT_*` macro.
- Operators called from Python never appear in `wm.operators`, so headless tests can't
  detect their own transform there.
- F9 is "undo, then exec": `undo_post` fires first. Tell it from Ctrl+Z by comparing
  positions at the next update with the post-undo snapshot.
- Your own `update_edit_mesh` re-fires the handler: guard with a flag, skip no-op writes.

**Why:** remapping G/R/S to a custom modal misses gizmos, other keymaps and menus, and
re-implements axis locks, numeric input, snapping and pivots.

**How to apply:** snapshot the selection while idle, freeze it when a transform starts,
project every update from the frozen snapshot, never from the previous frame. Reference:
`GeometryConstraint/source/blender/live.py` + `core/live.py`.

<a id="links_new_stale_socket"></a>

## links.new can return None for a socket taken off a removed link

*After `ng.links.remove(link)`, re-fetch sockets from their node; `link.to_socket` may be stale.*

Blender 5.0, `polish_layout._jog`: `ts = link.to_socket; ng.links.remove(link);
ng.links.new(reroute.outputs[0], ts)` returned **None** (no error, no link) when `ts` was a
reroute input. Most calls worked, so the graph silently lost one connection.

**How to apply:** store links as `(from node, from socket identifier, to node, to socket
identifier)`, look sockets up from `ng.nodes[...]` after removals, and check `links.new`'s
return value.

<a id="activate_init_property_split"></a>

## activate_init is ignored under use_property_split

*A props dialog meant to open with its text field already editing does nothing when the layout uses property split.*

Blender 5.0, real UI, 2026-10-21 (Modifier Stack Actions, Extract As dialog).
`row = layout.row(); row.activate_init = True; row.prop(self, "name")` inside an
`invoke_props_dialog` draw opens with the text selected, so typing replaces it. With
`layout.use_property_split = True` the field opens idle and typed keys go nowhere.

**How to apply:** draw such dialogs without property split, and check with a real UI run;
background mode never draws the dialog.
