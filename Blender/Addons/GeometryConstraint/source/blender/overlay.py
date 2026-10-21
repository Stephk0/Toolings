"""Viewport overlay: the edges / faces / normals a live transform is held to.

Like Edge Slide's yellow guide lines. While a native transform runs, the
live handler hands over the constraint shapes of each edited object (world
space); this POST_VIEW draw callback shows them:

  Edge   - every edge a selected vertex could slide along (dim) and the
           edges it is sliding along right now (bright)
  Face   - the surface the vertices slide over (tinted)
  Normal - each vertex's normal line
"""

import bpy
import gpu
from gpu_extras.batch import batch_for_shader
from mathutils import Vector

from ..core import constraint as C

COLOR = (1.0, 0.8, 0.15)
DIM_ALPHA, HOT_ALPHA, FACE_ALPHA = 0.45, 1.0, 0.12
DIM_WIDTH, HOT_WIDTH = 1.5, 3.0

_shapes = {}        # object name -> {"dim": [(a, b)], "hot": [(a, b)], "tris": [(a, b, c)]}
_handle = None


def static_shapes(constraints, mode, normal_length):
    """The part of the overlay that doesn't change during a drag."""
    dim, tris = set(), set()
    for c in constraints.values():
        if mode == C.MODE_EDGE and isinstance(c, C.EdgeRails):
            dim.update(c.candidate_edges())
        elif mode == C.MODE_FACE and isinstance(c, C.FacePatch):
            tris.update(c.triangles)
        elif mode == C.MODE_NORMAL and isinstance(c, C.NormalLine):
            o, n = c.origin, c.normal
            dim.add((tuple(o[i] - n[i] * normal_length for i in range(3)),
                     tuple(o[i] + n[i] * normal_length for i in range(3))))
    return {"dim": list(dim), "tris": list(tris)}


def show(obj_name, static, constraints):
    hot = [seg for c in constraints.values() if isinstance(c, C.EdgeRails) for seg in c.path]
    _shapes[obj_name] = {"dim": static["dim"], "tris": static["tris"], "hot": hot}
    _redraw()


def hide(obj_name=None):
    if obj_name is None:
        had = bool(_shapes)
        _shapes.clear()
    else:
        had = _shapes.pop(obj_name, None) is not None
    if had:
        _redraw()


def _redraw():
    wm = getattr(bpy.context, "window_manager", None)
    for win in (wm.windows if wm else ()):
        for area in win.screen.areas:
            if area.type == 'VIEW_3D':
                area.tag_redraw()


def _lines(segs, alpha, width):
    if not segs:
        return
    shader = gpu.shader.from_builtin('POLYLINE_UNIFORM_COLOR')
    coords = [p for seg in segs for p in seg]
    batch = batch_for_shader(shader, 'LINES', {"pos": coords})
    region = bpy.context.region
    shader.uniform_float("viewportSize", (region.width, region.height))
    shader.uniform_float("lineWidth", width)
    shader.uniform_float("color", (*COLOR, alpha))
    batch.draw(shader)


def _toward_eye(points, factor=0.002):
    """Pull the tint a hair toward the viewer so it doesn't z-fight the mesh."""
    rv3d = bpy.context.region_data
    inv = rv3d.view_matrix.inverted()
    if rv3d.is_perspective:
        eye = inv.translation
        return [p + (eye - p) * factor for p in map(Vector, points)]
    toward = inv.to_3x3() @ Vector((0.0, 0.0, 1.0)) * (rv3d.view_distance * factor)
    return [Vector(p) + toward for p in points]


def _draw():
    if not _shapes:
        return
    from . import live
    if live.transform_running(bpy.context.window_manager) is False:
        return      # confirmed / cancelled without an update to clear us yet
    gpu.state.blend_set('ALPHA')
    gpu.state.depth_mask_set(False)
    shader = gpu.shader.from_builtin('UNIFORM_COLOR')
    for sh in _shapes.values():
        if sh["tris"]:
            # Faces respect depth (no tint through other objects); lines draw
            # on top, like Edge Slide's guides.
            gpu.state.depth_test_set('LESS_EQUAL')
            coords = _toward_eye([p for tri in sh["tris"] for p in tri])
            batch = batch_for_shader(shader, 'TRIS', {"pos": coords})
            shader.uniform_float("color", (*COLOR, FACE_ALPHA))
            batch.draw(shader)
        gpu.state.depth_test_set('NONE')
        _lines(sh["dim"], DIM_ALPHA, DIM_WIDTH)
        _lines(sh["hot"], HOT_ALPHA, HOT_WIDTH)
    gpu.state.depth_test_set('NONE')
    gpu.state.depth_mask_set(True)
    gpu.state.blend_set('NONE')


def register():
    global _handle
    if _handle is None:
        _handle = bpy.types.SpaceView3D.draw_handler_add(_draw, (), 'WINDOW', 'POST_VIEW')


def unregister():
    global _handle
    if _handle is not None:
        bpy.types.SpaceView3D.draw_handler_remove(_handle, 'WINDOW')
        _handle = None
    _shapes.clear()
