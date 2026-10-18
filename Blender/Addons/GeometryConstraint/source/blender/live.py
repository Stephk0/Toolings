"""Live mode: constrain Blender's own transforms.

While the scene's constraint is Edge / Face / Normal, every native transform
(G / R / S or W / E / R in any keymap, the tool gizmos, Mesh > Transform, F3,
scripts, Adjust Last Operation) runs as usual and writes its free result;
this depsgraph handler snaps the selected vertices back onto the mesh in the
same update, before the viewport draws it. Decisions about *what* to project
from live in core/live.py; the geometry in core/constraint.py.
"""

import time

import bmesh
import bpy
from bpy.app.handlers import persistent
from mathutils import Vector

from ..core import constraint as C
from ..core.live import LiveTracker, same_positions

# Native operators whose result gets constrained.
TRANSFORM_OPS = {
    "TRANSFORM_OT_translate", "TRANSFORM_OT_rotate", "TRANSFORM_OT_resize",
    "TRANSFORM_OT_transform", "TRANSFORM_OT_trackball", "TRANSFORM_OT_shear",
    "TRANSFORM_OT_tosphere", "TRANSFORM_OT_push_pull", "TRANSFORM_OT_bend",
    "TRANSFORM_OT_shrink_fatten",
}

_trackers = {}          # object name -> LiveTracker
_busy = False           # re-entrancy guard: our own update_edit_mesh re-fires the handler


def _settings(scene):
    s = getattr(scene, "geometry_constraint", None)
    if s is None or not s.enabled or not s.live:
        return None
    return s


def _edit_objects(context):
    objs = getattr(context, "objects_in_mode_unique_data", None) or []
    if not objs and context.edit_object is not None:
        objs = [context.edit_object]
    return [o for o in objs if o.type == 'MESH' and o.mode == 'EDIT']


def _last_op(wm):
    ops = wm.operators
    if not len(ops):
        return 0, ""
    op = ops[-1]
    return op.as_pointer(), op.bl_idname


def transform_running(wm):
    """True/False from Window.modal_operators (Blender 4.2+), else None."""
    found_any = False
    for win in wm.windows:
        mods = getattr(win, "modal_operators", None)
        if mods is None:
            return None
        found_any = True
        names = [op.bl_idname for op in mods]
        if any(n in TRANSFORM_OPS for n in names):
            # A macro (extrude + move, duplicate + move ...) also lists its
            # own id; leave those unconstrained like Max does.
            return all(n in TRANSFORM_OPS or not n.startswith("MESH_OT_") for n in names)
    return False if found_any else None


def _read(obj, bm):
    world = obj.matrix_world
    sel = [v for v in bm.verts if v.select and not v.hide]
    key = (len(bm.verts), len(bm.edges), len(bm.faces), hash(tuple(v.index for v in sel)))
    positions = {v.index: tuple(world @ v.co) for v in sel}
    return key, positions


def _constraints_for(base, obj, bm, settings):
    ck = (settings.mode, settings.reach, settings.stop_at_selected,
          settings.stop_at_vertices, obj.name)
    cons = base.cache.get(ck)
    if cons is not None:
        return cons
    world = obj.matrix_world
    normal_mat = world.to_3x3().inverted_safe().transposed()
    positions = [tuple(world @ v.co) for v in bm.verts]
    for i, p in base.positions.items():
        positions[i] = p                      # selected verts at their pre-transform spot
    normals = [tuple((normal_mat @ v.normal).normalized()) for v in bm.verts]
    edges = [(e.verts[0].index, e.verts[1].index) for e in bm.edges if not e.hide]
    sel_edges = [(e.verts[0].index, e.verts[1].index) for e in bm.edges
                 if e.select and not e.hide]
    faces = [tuple(v.index for v in f.verts) for f in bm.faces if not f.hide]
    mesh = C.MeshData(positions, edges, faces, base.positions.keys(), normals,
                      selected_edges=sel_edges)
    if settings.mode == C.MODE_NORMAL:
        # Normals of the moved mesh are wrong; use the pre-transform ones.
        mesh._normals = None
    cons = C.build_constraints(mesh, settings.mode, reach=settings.reach,
                               stop_at_selected=settings.stop_at_selected,
                               stop_at_vertices=settings.stop_at_vertices)
    base.cache.clear()
    base.cache[ck] = cons
    return cons


def _apply(obj, bm, base, positions, settings):
    cons = _constraints_for(base, obj, bm, settings)
    result = C.solve(cons, positions)
    if same_positions(result, positions):
        return positions
    inv = obj.matrix_world.inverted_safe()
    bm.verts.ensure_lookup_table()
    for i, p in result.items():
        bm.verts[i].co = inv @ Vector(p)
    bmesh.update_edit_mesh(obj.data, loop_triangles=True, destructive=False)
    return result


@persistent
def on_depsgraph_update(scene, _depsgraph=None):
    global _busy
    if _busy:
        return
    settings = _settings(scene)
    if settings is None:
        return
    context = bpy.context
    if context.mode != 'EDIT_MESH':
        return
    wm = context.window_manager
    op_id, op_name = _last_op(wm)
    running = transform_running(wm)
    is_t = op_name in TRANSFORM_OPS
    _busy = True
    t0 = time.perf_counter()
    try:
        for obj in _edit_objects(context):
            bm = bmesh.from_edit_mesh(obj.data)
            bm.verts.index_update()
            key, positions = _read(obj, bm)
            tr = _trackers.setdefault(obj.name, LiveTracker())
            base = tr.decide(key, positions, last_op=op_id, last_is_transform=is_t,
                             transform_running=running)
            if base is not None and positions:
                positions = _apply(obj, bm, base, positions, settings)
                if settings.debug:
                    print(f"[GeometryConstraint] live {settings.mode} on {obj.name}: "
                          f"{len(positions)} verts, {(time.perf_counter() - t0) * 1000:.1f} ms "
                          f"(op {op_name or '-'}, running={running})")
            tr.settle(key, positions, op_id)
    except Exception as exc:          # never break the user's session from a handler
        print(f"[GeometryConstraint] live handler error: {exc!r}")
        _trackers.clear()
    finally:
        _busy = False


@persistent
def on_undo_redo(scene, *_args):
    if _settings(scene) is None or bpy.context.mode != 'EDIT_MESH':
        _trackers.clear()
        return
    for obj in _edit_objects(bpy.context):
        try:
            bm = bmesh.from_edit_mesh(obj.data)
        except (ReferenceError, ValueError):
            continue
        _key, positions = _read(obj, bm)
        _trackers.setdefault(obj.name, LiveTracker()).note_undo(positions)


@persistent
def on_load(*_args):
    _trackers.clear()


def reset():
    """Forget snapshots (mode toggled, settings changed)."""
    _trackers.clear()


_HANDLERS = (
    (bpy.app.handlers.depsgraph_update_post, on_depsgraph_update),
    (bpy.app.handlers.undo_post, on_undo_redo),
    (bpy.app.handlers.redo_post, on_undo_redo),
    (bpy.app.handlers.load_post, on_load),
)


def register():
    for lst, fn in _HANDLERS:
        if fn not in lst:
            lst.append(fn)


def unregister():
    for lst, fn in _HANDLERS:
        if fn in lst:
            lst.remove(fn)
    _trackers.clear()
