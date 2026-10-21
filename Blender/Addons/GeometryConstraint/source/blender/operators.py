"""Constrained Move / Rotate / Scale operator + mode operators.

The operator only gathers mesh data and turns mouse/keyboard input into a
transform; all geometry decisions live in core/ (constraint.py, transform.py).
"""

import math
import time

import bmesh
import bpy
from bpy.props import (BoolVectorProperty, EnumProperty, FloatProperty,
                       FloatVectorProperty)
from bpy.types import Operator
from bpy_extras import view3d_utils
from mathutils import Matrix, Vector

from ..core import constraint as C
from ..core import transform as T
from .live import update_normals
from .properties import CONSTRAINT_ITEMS, TYPE_ITEMS, active_mode

TRANSFORM_ITEMS = (
    ('TRANSLATE', "Move", "Move the selection"),
    ('ROTATE', "Rotate", "Rotate the selection"),
    ('RESIZE', "Scale", "Scale the selection"),
)
TRANSFORM_LABELS = {i: n for i, n, _d in TRANSFORM_ITEMS}
CONSTRAINT_LABELS = {i[0]: i[1] for i in CONSTRAINT_ITEMS}

SNAP_TRANSLATE = 0.1
SNAP_ROTATE = math.radians(5.0)
SNAP_SCALE = 0.1
SCALE_SOFTEN_PX = 60.0   # see Knowledge/bpy-api-gotchas.md (ratio drags)


def _log(settings, msg):
    if settings is not None and settings.debug:
        print(f"[GeometryConstraint] {msg}")


# ---------------------------------------------------------------------------
# Mesh gathering / writing (the bpy boundary)
# ---------------------------------------------------------------------------

class _ObjectSession:
    """Snapshot of one edit-mode object: world-space originals + constraints.

    Holds only plain data and the object *name*: the BMesh is re-resolved on
    every write because undo pushes rebuild it (Knowledge/bpy-api-gotchas.md).
    """

    def __init__(self, obj_name, world, originals, constraints, active):
        self.obj_name = obj_name
        self.world = world
        self.world_inv = world.inverted_safe()
        self.originals = originals          # {vert index: world tuple}
        self.constraints = constraints
        self.active = active                # world tuple or None


def _edit_objects(context):
    objs = getattr(context, "objects_in_mode_unique_data", None) or []
    if not objs and context.edit_object is not None:
        objs = [context.edit_object]
    return [o for o in objs if o.type == 'MESH' and o.mode == 'EDIT']


def _active_point(bm, world):
    elem = bm.select_history.active
    if elem is None:
        return None
    if isinstance(elem, bmesh.types.BMVert):
        return tuple(world @ elem.co)
    if isinstance(elem, bmesh.types.BMEdge):
        return tuple(world @ ((elem.verts[0].co + elem.verts[1].co) * 0.5))
    if isinstance(elem, bmesh.types.BMFace):
        return tuple(world @ elem.calc_center_median())
    return None


def gather_sessions(context, mode, *, reach, stop_at_selected, stop_at_vertices=True):
    sessions = []
    for obj in _edit_objects(context):
        bm = bmesh.from_edit_mesh(obj.data)
        bm.verts.index_update()
        selected = [v.index for v in bm.verts if v.select and not v.hide]
        if not selected:
            continue
        world = obj.matrix_world.copy()
        normal_mat = world.to_3x3().inverted_safe().transposed()
        positions = [tuple(world @ v.co) for v in bm.verts]
        normals = [tuple((normal_mat @ v.normal).normalized()) for v in bm.verts]
        edges = [(e.verts[0].index, e.verts[1].index) for e in bm.edges if not e.hide]
        sel_edges = [(e.verts[0].index, e.verts[1].index) for e in bm.edges
                     if e.select and not e.hide]
        faces = [tuple(v.index for v in f.verts) for f in bm.faces if not f.hide]
        mesh = C.MeshData(positions, edges, faces, selected, normals,
                          selected_edges=sel_edges)
        constraints = C.build_constraints(mesh, mode, reach=reach,
                                          stop_at_selected=stop_at_selected,
                                          stop_at_vertices=stop_at_vertices)
        originals = {i: positions[i] for i in selected}
        sessions.append(_ObjectSession(obj.name, world, originals, constraints,
                                       _active_point(bm, world)))
    return sessions


def write_positions(sessions, results):
    """results: list (parallel to sessions) of {vert index: world tuple}."""
    for sess, res in zip(sessions, results):
        obj = bpy.data.objects.get(sess.obj_name)
        if obj is None or obj.mode != 'EDIT':
            continue
        bm = bmesh.from_edit_mesh(obj.data)
        bm.verts.ensure_lookup_table()
        inv = sess.world_inv
        for i, p in res.items():
            bm.verts[i].co = inv @ Vector(p)
        update_normals(bm, res.keys())
        bmesh.update_edit_mesh(obj.data)


def _pivot(context, sessions):
    ts = context.scene.tool_settings
    pts = [p for s in sessions for p in s.originals.values()]
    active = next((s.active for s in sessions
                   if s.obj_name == getattr(context.active_object, "name", None)
                   and s.active is not None), None)
    return T.pivot_point(pts, ts.transform_pivot_point,
                         cursor=tuple(context.scene.cursor.location), active=active)


# ---------------------------------------------------------------------------
# Constrained transform
# ---------------------------------------------------------------------------

class MESH_OT_geometry_constraint_transform(Operator):
    """Move / Rotate / Scale with the active sub-object constraint (Edge / Face / Normal)"""
    bl_idname = "mesh.geometry_constraint_transform"
    bl_label = "Constrained Transform"
    bl_options = {'REGISTER', 'UNDO', 'BLOCKING'}

    transform_type: EnumProperty(name="Transform", items=TRANSFORM_ITEMS, default='TRANSLATE')
    constraint: EnumProperty(name="Constraint", items=CONSTRAINT_ITEMS, default=C.MODE_EDGE)
    use_scene_constraint: bpy.props.BoolProperty(
        name="Use Scene Constraint",
        description="Take the constraint from the header setting instead of the Constraint property",
        default=True, options={'SKIP_SAVE'},
    )
    value: FloatVectorProperty(name="Move", subtype='TRANSLATION', size=3, default=(0.0, 0.0, 0.0))
    angle: FloatProperty(name="Angle", subtype='ANGLE', default=0.0)
    axis: FloatVectorProperty(name="Axis", subtype='DIRECTION', size=3, default=(0.0, 0.0, 1.0))
    scale: FloatVectorProperty(name="Scale", subtype='XYZ', size=3, default=(1.0, 1.0, 1.0))
    orient_matrix: FloatVectorProperty(
        name="Orientation", subtype='MATRIX', size=(3, 3),
        default=((1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0)),
        options={'HIDDEN'},
    )
    constraint_axis: BoolVectorProperty(name="Axis Lock", size=3, default=(False, False, False))

    @classmethod
    def poll(cls, context):
        return context.mode == 'EDIT_MESH'

    # -- shared core ---------------------------------------------------------

    def _settings(self, context):
        return context.scene.geometry_constraint

    def _basis(self):
        m = Matrix(self.orient_matrix)
        # Columns are the orientation axes.
        return tuple(tuple(m.col[i]) for i in range(3))

    def _targets(self, sess, pivot):
        pts = sess.originals
        if self.transform_type == 'TRANSLATE':
            return T.translate(pts, tuple(self.value))
        if self.transform_type == 'ROTATE':
            return T.rotate(pts, pivot, tuple(self.axis), self.angle)
        return T.scale(pts, pivot, tuple(self.scale), self._basis())

    def _apply(self, context):
        t0 = time.perf_counter()
        s = self._settings(context)
        even = self.constraint == C.MODE_EDGE and s.even_slide
        results = [C.solve(sess.constraints, self._targets(sess, self._pivot_pt), even=even)
                   for sess in self._sessions]
        write_positions(self._sessions, results)
        _log(s,
             f"{self.transform_type} solved {sum(len(r) for r in results)} verts "
             f"in {(time.perf_counter() - t0) * 1000:.1f} ms")

    def _restore(self):
        write_positions(self._sessions, [dict(s.originals) for s in self._sessions])

    def _prepare(self, context):
        s = self._settings(context)
        if self.use_scene_constraint:
            self.constraint = active_mode(s)
        self._sessions = gather_sessions(context, self.constraint, reach=s.reach,
                                         stop_at_selected=s.stop_at_selected,
                                         stop_at_vertices=s.stop_at_vertices)
        if not self._sessions:
            return False
        self._pivot_pt = _pivot(context, self._sessions)
        return True

    def execute(self, context):
        if not self._prepare(context):
            self.report({'WARNING'}, "Nothing selected")
            return {'CANCELLED'}
        self._apply(context)
        return {'FINISHED'}

    # -- interactive -----------------------------------------------------------

    def invoke(self, context, event):
        if context.area is None or context.area.type != 'VIEW_3D' or context.region_data is None:
            return self.execute(context)
        if not self._prepare(context):
            self.report({'WARNING'}, "Nothing selected")
            return {'CANCELLED'}
        self._region = context.region
        self._rv3d = context.region_data
        self._axis_lock = [False, False, False]
        self._lock_space = None        # None / 'GLOBAL' / 'LOCAL'
        self._lock_key = None
        self._numeric = ""
        self._reset_drag(event)
        self.value = (0.0, 0.0, 0.0)
        self.angle = 0.0
        self.scale = (1.0, 1.0, 1.0)
        self._sync_orientation(context)
        context.window_manager.modal_handler_add(self)
        self._update_header(context)
        return {'RUNNING_MODAL'}

    def _reset_drag(self, event):
        self._start = Vector((event.mouse_region_x, event.mouse_region_y))
        self._mouse = self._start.copy()
        pivot_2d = self._pivot_2d()
        self._prev_ang = math.atan2(*(self._start - pivot_2d).yx) if pivot_2d else 0.0
        self._accum_ang = 0.0

    def _pivot_2d(self):
        return view3d_utils.location_3d_to_region_2d(self._region, self._rv3d,
                                                     Vector(self._pivot_pt))

    def _sync_orientation(self, context):
        if self._lock_space == 'LOCAL' and context.active_object is not None:
            m = context.active_object.matrix_world.to_3x3().normalized()
        else:
            m = Matrix.Identity(3)
        self.orient_matrix = m
        self.constraint_axis = self._axis_lock

    def _locked(self):
        return [i for i in range(3) if self._axis_lock[i]]

    def _toward_viewer(self):
        return (self._rv3d.view_rotation @ Vector((0.0, 0.0, 1.0))).normalized()

    def _numeric_value(self):
        if self._numeric in ("", "-", ".", "-."):
            return None
        try:
            return float(self._numeric)
        except ValueError:
            return None

    def _compute(self, ctrl):
        basis = [Vector(c) for c in self._basis()]
        locked = self._locked()
        num = self._numeric_value()
        pivot = Vector(self._pivot_pt)

        if self.transform_type == 'TRANSLATE':
            if num is not None:
                d = basis[locked[0]] * num if len(locked) == 1 else basis[0] * num
            elif len(locked) == 1:
                d = self._axis_drag(basis[locked[0]], pivot)
            else:
                a = view3d_utils.region_2d_to_location_3d(self._region, self._rv3d, self._start, pivot)
                b = view3d_utils.region_2d_to_location_3d(self._region, self._rv3d, self._mouse, pivot)
                d = b - a
                if locked:
                    d = Vector(T.mask_vector(tuple(d), self._axis_lock, self._basis()))
            if ctrl and num is None:
                comps = [round(d.dot(b) / SNAP_TRANSLATE) * SNAP_TRANSLATE for b in basis]
                d = basis[0] * comps[0] + basis[1] * comps[1] + basis[2] * comps[2]
            self.value = d

        elif self.transform_type == 'ROTATE':
            viewer = self._toward_viewer()
            if len(locked) == 1:
                axis = basis[locked[0]].copy()
                if axis.dot(viewer) < 0.0:
                    axis.negate()
            else:
                axis = viewer
            ang = math.radians(num) if num is not None else self._accum_ang
            if ctrl and num is None:
                ang = round(ang / SNAP_ROTATE) * SNAP_ROTATE
            self.axis = axis
            self.angle = ang

        else:
            if num is not None:
                f = num
            else:
                p2 = self._pivot_2d() or self._start
                d0 = (self._start - p2).length
                d1 = (self._mouse - p2).length
                f = (d1 + SCALE_SOFTEN_PX) / (d0 + SCALE_SOFTEN_PX)
                if ctrl:
                    f = round(f / SNAP_SCALE) * SNAP_SCALE
            if not locked:
                self.scale = (f, f, f)
            else:
                self.scale = tuple(f if self._axis_lock[i] else 1.0 for i in range(3))

    def _axis_drag(self, axis, pivot):
        s0 = view3d_utils.location_3d_to_region_2d(self._region, self._rv3d, pivot)
        s1 = view3d_utils.location_3d_to_region_2d(self._region, self._rv3d, pivot + axis)
        if s0 is None or s1 is None or (s1 - s0).length < 1e-3:
            a = view3d_utils.region_2d_to_location_3d(self._region, self._rv3d, self._start, pivot)
            b = view3d_utils.region_2d_to_location_3d(self._region, self._rv3d, self._mouse, pivot)
            return axis * (b - a).dot(axis)
        ax2d = s1 - s0
        t = (self._mouse - self._start).dot(ax2d) / ax2d.length_squared
        return axis * t

    def _update_header(self, context):
        cons = CONSTRAINT_LABELS.get(self.constraint, self.constraint)
        if self.transform_type == 'TRANSLATE':
            v = Vector(self.value)
            info = f"D: {v.x:.4f}  {v.y:.4f}  {v.z:.4f}  ({v.length:.4f})"
        elif self.transform_type == 'ROTATE':
            info = f"Rot: {math.degrees(self.angle):.2f}°"
        else:
            sx, sy, sz = self.scale
            info = f"Scale: {sx:.3f}  {sy:.3f}  {sz:.3f}"
        if self._numeric:
            info += f"  [{self._numeric}|]"
        locked = "".join("XYZ"[i] for i in self._locked())
        if locked:
            info += f"  along {locked} ({(self._lock_space or 'GLOBAL').title()})"
        context.area.header_text_set(
            f"{cons} Constraint {TRANSFORM_LABELS[self.transform_type]}  {info}"
            "   —  X/Y/Z axis (Shift: plane), type value, Ctrl snap, G/R/S switch")

    def _finish(self, context, cancelled):
        if cancelled:
            self._restore()
        if context.area is not None:
            context.area.header_text_set(None)
            context.area.tag_redraw()
        return {'CANCELLED'} if cancelled else {'FINISHED'}

    def cancel(self, context):
        self._finish(context, True)

    def modal(self, context, event):
        etype, val = event.type, event.value

        if etype in {'RIGHTMOUSE', 'ESC'} and val == 'PRESS':
            return self._finish(context, True)
        if etype in {'LEFTMOUSE', 'RET', 'NUMPAD_ENTER', 'SPACE'} and val == 'PRESS':
            return self._finish(context, False)

        changed = False
        if etype in {'MOUSEMOVE', 'INBETWEEN_MOUSEMOVE'}:
            self._mouse = Vector((event.mouse_region_x, event.mouse_region_y))
            p2 = self._pivot_2d()
            if p2 is not None:
                ang = math.atan2(*(self._mouse - p2).yx)
                delta = (ang - self._prev_ang + math.pi) % (2 * math.pi) - math.pi
                self._accum_ang += delta
                self._prev_ang = ang
            changed = True

        elif val == 'PRESS' and etype in {'X', 'Y', 'Z'}:
            i = "XYZ".index(etype)
            key = (i, event.shift)
            if self._lock_key != key:
                self._lock_key, self._lock_space = key, 'GLOBAL'
            elif self._lock_space == 'GLOBAL':
                self._lock_space = 'LOCAL'
            else:
                self._lock_key, self._lock_space = None, None
            if self._lock_key is None:
                self._axis_lock = [False, False, False]
            elif event.shift:
                self._axis_lock = [j != i for j in range(3)]
            else:
                self._axis_lock = [j == i for j in range(3)]
            self._sync_orientation(context)
            changed = True

        elif val == 'PRESS' and etype in {'G', 'R', 'S'}:
            new = {'G': 'TRANSLATE', 'R': 'ROTATE', 'S': 'RESIZE'}[etype]
            if new != self.transform_type:
                self.transform_type = new
                self.value, self.angle, self.scale = (0, 0, 0), 0.0, (1, 1, 1)
                self._numeric = ""
                self._reset_drag(event)
                changed = True

        elif val == 'PRESS' and etype == 'BACK_SPACE':
            self._numeric = self._numeric[:-1]
            changed = True

        elif val == 'PRESS' and event.ascii and event.ascii in "0123456789.-":
            if event.ascii == "-":
                self._numeric = self._numeric[1:] if self._numeric.startswith("-") else "-" + self._numeric
            else:
                self._numeric += event.ascii
            changed = True

        elif etype in {'LEFT_CTRL', 'RIGHT_CTRL'}:
            changed = True

        if changed:
            self._compute(event.ctrl)
            self._apply(context)
            self._update_header(context)
            context.area.tag_redraw()
        return {'RUNNING_MODAL'}


# ---------------------------------------------------------------------------
# Mode operators
# ---------------------------------------------------------------------------

def _report_state(op, s):
    state = CONSTRAINT_LABELS[s.mode] if s.enabled else "Off"
    op.report({'INFO'}, f"Geometry Constraint: {state}")


class VIEW3D_OT_geometry_constraint_toggle(Operator):
    """Turn the transform constraint on / off (right-click > Assign Shortcut to bind a key, e.g. Shift+X like 3ds Max)"""
    bl_idname = "view3d.geometry_constraint_toggle"
    bl_label = "Toggle Transform Constraint"
    bl_options = {'REGISTER'}

    @classmethod
    def poll(cls, context):
        # Edit-mesh only, so a key bound in the 3D View keymap stays free
        # for its usual job in other modes.
        return context.mode == 'EDIT_MESH'

    def execute(self, context):
        s = context.scene.geometry_constraint
        s.enabled = not s.enabled
        _report_state(self, s)
        return {'FINISHED'}


_EDIT_MESH_POLL = classmethod(lambda cls, context: context.mode == 'EDIT_MESH')


def _type_toggle(mode, label):
    """One operator per type (no properties), so every hotkey has its own
    keymap name and right-click > Assign Shortcut binds exactly that one."""

    def execute(self, context):
        s = context.scene.geometry_constraint
        if s.enabled and s.mode == mode:
            s.enabled = False
        else:
            s.mode = mode
            s.enabled = True
        _report_state(self, s)
        return {'FINISHED'}

    return type(f"VIEW3D_OT_geometry_constraint_{mode.lower()}", (Operator,), {
        "__doc__": (f"Turn the {label} constraint on, or off if it is already on "
                    "(right-click > Assign Shortcut to bind a key)"),
        "bl_idname": f"view3d.geometry_constraint_{mode.lower()}",
        "bl_label": f"Toggle {label} Constraint",
        "bl_options": {'REGISTER'},
        "poll": _EDIT_MESH_POLL,
        "execute": execute,
    })


def _cycle(key, order, label, doc):
    def execute(self, context):
        s = context.scene.geometry_constraint
        nxt = C.next_in_cycle(active_mode(s), order)
        if nxt == C.MODE_NONE:
            s.enabled = False
        else:
            s.mode = nxt
            s.enabled = True
        _report_state(self, s)
        return {'FINISHED'}

    return type(f"VIEW3D_OT_geometry_constraint_cycle_{key}", (Operator,), {
        "__doc__": doc + " (right-click > Assign Shortcut to bind a key)",
        "bl_idname": f"view3d.geometry_constraint_cycle_{key}",
        "bl_label": label,
        "bl_options": {'REGISTER'},
        "poll": _EDIT_MESH_POLL,
        "execute": execute,
    })


TYPE_TOGGLES = tuple(_type_toggle(i[0], i[1]) for i in TYPE_ITEMS)
CYCLES = (
    _cycle("full", C.CYCLE_FULL, "Cycle Constraint: Off > Edge > Face > Normal",
           "Each press steps to the next constraint type, then off"),
    _cycle("surface", C.CYCLE_SURFACE, "Cycle Constraint: Off > Edge > Face",
           "Each press steps through the constraints that keep the selection on the "
           "surface (Edge, Face), then off"),
)


class VIEW3D_OT_geometry_constraint_set(Operator):
    """Pick the constraint type and turn the constraint on"""
    bl_idname = "view3d.geometry_constraint_set"
    bl_label = "Set Transform Constraint"
    bl_options = {'REGISTER'}

    mode: EnumProperty(name="Constraint", items=TYPE_ITEMS, default=C.MODE_EDGE)

    def execute(self, context):
        s = context.scene.geometry_constraint
        s.mode = self.mode
        s.enabled = True
        return {'FINISHED'}


classes = (
    MESH_OT_geometry_constraint_transform,
    VIEW3D_OT_geometry_constraint_toggle,
    *TYPE_TOGGLES,
    *CYCLES,
    VIEW3D_OT_geometry_constraint_set,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
