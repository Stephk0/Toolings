bl_info = {
    "name": "Edge Constraint Mode",
    "author": "Stephan Viranyi",
    "version": (1, 1, 2),
    "blender": (4, 5, 0),
    "location": "View3D > Header (toggle) — then G / R / S in Mesh Edit mode",
    "description": (
        "3ds Max-style edge constraint: while the mode is on, Move/Rotate/"
        "Scale of the selection is projected onto each vertex's incident edges."
    ),
    "category": "Mesh",
}

import bpy
import bmesh
from bpy.types import Operator, PropertyGroup
from bpy.props import BoolProperty, EnumProperty, PointerProperty
from mathutils import Vector, Matrix


# ============================================================================
# CORE SOLVER
# ============================================================================
#
# The solver is the only place that "knows" about edge topology. Anything that
# can produce a per-vertex world-space delta (G/R/S modal here, the multi-gizmo
# later, a custom op, …) feeds into project_deltas_onto_edges() and gets back
# new world positions. This keeps the rest of the addon transform-agnostic.

class EdgeConstraintSolver:
    """Project per-vertex world-space deltas onto the verts' incident edges.

    For each selected vertex we pick the incident edge whose tangent best aligns
    with the requested motion (largest |dot|), then move the vertex along that
    tangent by the projected scalar. If the projected distance overshoots the
    edge, we walk into the next connected edge (only along edges between two
    *unselected* verts — selected-to-selected edges would just drag neighbours
    around with us).
    """

    def __init__(self, bm, selected_verts, *, world_matrix,
                 stop_at_selection=True, max_walk_edges=8):
        self.bm = bm
        self.world_matrix = world_matrix.copy()
        self.world_matrix_inv = world_matrix.inverted_safe()
        # Rotation/scale part only (no translation) — for transforming directions
        self.world_dir = world_matrix.to_3x3()
        self.world_dir_inv = self.world_dir.inverted_safe()

        self.selected = list(selected_verts)
        self.selected_set = set(v.index for v in self.selected)
        self.stop_at_selection = stop_at_selection
        self.max_walk_edges = max_walk_edges

        # Snapshot original *local* positions so apply_deltas() always works from
        # the same baseline within a single modal session.
        self.original_local = {v.index: v.co.copy() for v in self.selected}

    # -- helpers ----------------------------------------------------------

    def _incident_edges_local(self, v):
        """Yield (other_vert, tangent_local, length_local) for each edge on v."""
        for e in v.link_edges:
            other = e.other_vert(v)
            if other is None:
                continue
            tangent = other.co - v.co
            length = tangent.length
            if length < 1e-8:
                continue
            yield other, tangent / length, length

    def _best_edge_for_local_dir(self, v, dir_local):
        """Return (other_vert, tangent_local, length, signed_scalar) of the
        incident edge whose tangent best matches dir_local."""
        best = None
        best_abs = -1.0
        for other, tangent, length in self._incident_edges_local(v):
            scalar = dir_local.dot(tangent)
            if abs(scalar) > best_abs:
                best_abs = abs(scalar)
                best = (other, tangent, length, scalar)
        return best

    # -- public API -------------------------------------------------------

    def restore(self):
        """Restore selected verts to their snapshot local positions."""
        for v in self.selected:
            base = self.original_local.get(v.index)
            if base is not None:
                v.co = base

    def apply_deltas(self, world_deltas):
        """world_deltas: dict[v.index] -> Vector (world-space).

        Resets each selected vert to its snapshot position, then slides it along
        its best-aligned incident edge by the *projected* length |delta·tangent|.
        If the projection exceeds the edge length, walks past the next vertex
        and re-projects whatever delta hasn't been consumed yet.
        """
        for v in self.selected:
            base_local = self.original_local.get(v.index)
            if base_local is None:
                continue
            v.co = base_local

            wd = world_deltas.get(v.index)
            if wd is None or wd.length < 1e-9:
                continue

            # Bring delta into the object's local space (rotation/scale only;
            # we're transforming a direction, not a point).
            remaining = self.world_dir_inv @ wd
            if remaining.length < 1e-9:
                continue

            current_vert = v
            current_pos = base_local.copy()
            walked = 0
            while walked <= self.max_walk_edges:
                best = self._best_edge_for_local_dir(current_vert, remaining)
                if best is None:
                    break
                other, tangent, length, scalar = best
                # scalar = remaining · tangent (signed projected length).
                # If the projection is basically zero, the constraint absorbs
                # all the motion at this vert — done.
                if abs(scalar) < 1e-6:
                    break
                move_dir = tangent if scalar > 0 else -tangent
                wanted = abs(scalar)
                step = min(wanted, length)
                current_pos = current_pos + move_dir * step

                # If we used up the projection within this edge, we're done —
                # the component perpendicular to the tangent is what the
                # edge constraint rejects.
                if step >= wanted - 1e-9:
                    break

                # Otherwise we hit the edge's far end and want to keep going:
                # consume the parallel part we just moved, walk to the next
                # vert, and re-project whatever's left.
                if self.stop_at_selection and other.index in self.selected_set:
                    break
                remaining = remaining - move_dir * step
                current_vert = other
                walked += 1

            v.co = current_pos


# ============================================================================
# PROPERTIES
# ============================================================================

class EdgeConstraintModeSettings(PropertyGroup):
    """Scene-level state for the edge constraint mode."""

    enabled: BoolProperty(
        name="Edge Constraint Mode",
        description="When ON, G/R/S in Mesh Edit mode are constrained to slide selected verts along their incident edges",
        default=False,
        update=lambda self, ctx: _on_enabled_toggled(self, ctx),
    )

    stop_at_selected: BoolProperty(
        name="Stop at Selected",
        description="When walking past an edge end, stop if the next vertex is also selected (prevents selected verts from colliding)",
        default=True,
    )


# ============================================================================
# MODAL TRANSFORM OPERATOR
# ============================================================================

TRANSFORM_TYPE_ITEMS = (
    ('TRANSLATE', "Translate", "Move selection along incident edges"),
    ('ROTATE',    "Rotate",    "Rotate selection — per-vert motion projected onto incident edges"),
    ('RESIZE',    "Resize",    "Scale selection — per-vert motion projected onto incident edges"),
)

TRANSFORM_TYPE_LABELS = {ident: label for ident, label, _desc in TRANSFORM_TYPE_ITEMS}


def _get_view3d_region(context):
    """Find the (region, rv3d) pair for the current 3D view, or (None, None)."""
    region = context.region
    rv3d = context.region_data
    if region and rv3d:
        return region, rv3d
    return None, None


def _pivot_world(context, selected_verts, world_matrix):
    """Pivot in world space — currently median of selection.

    Centralized so we can swap in 3D-cursor / active-element / etc. later without
    touching the transform math.
    """
    if not selected_verts:
        return Vector((0.0, 0.0, 0.0))
    acc = Vector((0.0, 0.0, 0.0))
    for v in selected_verts:
        acc += world_matrix @ v.co
    return acc / len(selected_verts)


class MESH_OT_edge_constraint_transform(Operator):
    """Modal transform that projects motion onto each vert's incident edges.

    transform_type chooses how the per-vertex world-space delta is computed
    from mouse motion. The same solver is used for all three.
    """
    bl_idname = "mesh.edge_constraint_transform"
    bl_label = "Edge Constraint Transform"
    bl_options = {'REGISTER', 'UNDO', 'BLOCKING'}

    transform_type: EnumProperty(
        items=TRANSFORM_TYPE_ITEMS,
        default='TRANSLATE',
    )

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return (context.mode == 'EDIT_MESH'
                and obj is not None
                and obj.type == 'MESH')

    # -- lifecycle ---------------------------------------------------------

    def invoke(self, context, event):
        self._obj = context.active_object
        self._bm = bmesh.from_edit_mesh(self._obj.data)
        self._world = self._obj.matrix_world.copy()

        sel = [v for v in self._bm.verts if v.select]
        if not sel:
            self.report({'WARNING'}, "Nothing selected")
            return {'CANCELLED'}

        settings = context.scene.edge_constraint_mode
        self._solver = EdgeConstraintSolver(
            self._bm, sel,
            world_matrix=self._world,
            stop_at_selection=settings.stop_at_selected,
        )

        # Snapshot world-space positions of selected verts (for rotate/scale).
        self._world_origins = {v.index: self._world @ v.co.copy() for v in sel}
        self._pivot_world = _pivot_world(context, sel, self._world)

        # Mouse / region setup
        region, rv3d = _get_view3d_region(context)
        if region is None or rv3d is None:
            self.report({'WARNING'}, "Run from a 3D Viewport")
            return {'CANCELLED'}
        self._region = region
        self._rv3d = rv3d
        self._start_mx = event.mouse_region_x
        self._start_my = event.mouse_region_y

        # For translate we need a viewport->world basis for converting mouse
        # pixels to a world-space drag vector. We use the view's right/up axes.
        self._view_right = rv3d.view_matrix.inverted().to_3x3() @ Vector((1, 0, 0))
        self._view_up = rv3d.view_matrix.inverted().to_3x3() @ Vector((0, 1, 0))
        # Pixels-per-world-unit at the pivot's depth.
        self._world_per_pixel = self._estimate_world_per_pixel(region, rv3d)

        context.window_manager.modal_handler_add(self)
        context.area.tag_redraw()
        self._update_header(context)
        return {'RUNNING_MODAL'}

    def _estimate_world_per_pixel(self, region, rv3d):
        # Use view_distance / region width as a coarse scale factor.
        # Good enough for a drag; the user fine-tunes by feel.
        if rv3d.is_perspective:
            return max(rv3d.view_distance / max(region.width, 1), 1e-6)
        return max(rv3d.view_distance / max(region.width, 1), 1e-6) * 2.0

    def _update_header(self, context, extra=""):
        label = TRANSFORM_TYPE_LABELS[self.transform_type]
        msg = f"Edge Constraint {label}: LMB / Enter confirm, RMB / Esc cancel"
        if extra:
            msg = f"{msg}   |   {extra}"
        context.area.header_text_set(msg)

    def _finish(self, context, cancelled):
        if cancelled and getattr(self, "_solver", None):
            self._solver.restore()
        if getattr(self, "_bm", None):
            bmesh.update_edit_mesh(self._obj.data)
        context.area.header_text_set(None)
        context.area.tag_redraw()
        return {'CANCELLED' if cancelled else 'FINISHED'}

    # -- per-frame delta computation --------------------------------------

    def _world_deltas_for_translate(self, mx, my):
        dx = (mx - self._start_mx) * self._world_per_pixel
        dy = (my - self._start_my) * self._world_per_pixel
        world_delta = self._view_right * dx + self._view_up * dy
        return {idx: world_delta for idx in self._world_origins}

    def _world_deltas_for_rotate(self, mx, my):
        # Mouse angle around the pivot (in screen space) defines the rotation.
        from bpy_extras.view3d_utils import location_3d_to_region_2d
        pivot_2d = location_3d_to_region_2d(self._region, self._rv3d, self._pivot_world)
        if pivot_2d is None:
            return {idx: Vector() for idx in self._world_origins}

        import math
        start_ang = math.atan2(self._start_my - pivot_2d.y, self._start_mx - pivot_2d.x)
        curr_ang = math.atan2(my - pivot_2d.y, mx - pivot_2d.x)
        angle = curr_ang - start_ang

        # Axis = view forward (so the on-screen rotation matches what the user sees).
        view_forward = self._rv3d.view_matrix.inverted().to_3x3() @ Vector((0, 0, -1))
        rot = Matrix.Rotation(angle, 4, view_forward.normalized())

        deltas = {}
        for idx, p in self._world_origins.items():
            new_p = self._pivot_world + (rot @ (p - self._pivot_world))
            deltas[idx] = new_p - p
        return deltas

    def _world_deltas_for_resize(self, mx, my):
        from bpy_extras.view3d_utils import location_3d_to_region_2d
        pivot_2d = location_3d_to_region_2d(self._region, self._rv3d, self._pivot_world)
        if pivot_2d is None:
            return {idx: Vector() for idx in self._world_origins}

        start_r = max(((self._start_mx - pivot_2d.x) ** 2 + (self._start_my - pivot_2d.y) ** 2) ** 0.5, 1.0)
        curr_r = max(((mx - pivot_2d.x) ** 2 + (my - pivot_2d.y) ** 2) ** 0.5, 1.0)
        s = curr_r / start_r

        deltas = {}
        for idx, p in self._world_origins.items():
            new_p = self._pivot_world + (p - self._pivot_world) * s
            deltas[idx] = new_p - p
        return deltas

    def _compute_world_deltas(self, mx, my):
        if self.transform_type == 'TRANSLATE':
            return self._world_deltas_for_translate(mx, my)
        if self.transform_type == 'ROTATE':
            return self._world_deltas_for_rotate(mx, my)
        return self._world_deltas_for_resize(mx, my)

    # -- modal -------------------------------------------------------------

    def modal(self, context, event):
        if event.type in {'RIGHTMOUSE', 'ESC'}:
            return self._finish(context, cancelled=True)

        if event.type in {'LEFTMOUSE', 'RET', 'NUMPAD_ENTER'} and event.value == 'PRESS':
            return self._finish(context, cancelled=False)

        if event.type == 'MOUSEMOVE':
            mx, my = event.mouse_region_x, event.mouse_region_y
            deltas = self._compute_world_deltas(mx, my)
            self._solver.apply_deltas(deltas)
            bmesh.update_edit_mesh(self._obj.data)
            context.area.tag_redraw()
            return {'RUNNING_MODAL'}

        return {'RUNNING_MODAL'}


# ============================================================================
# CLEANUP HELPER (recovery from older versions)
# ============================================================================
#
# v1.1.0 and v1.1.1 hid the built-in tool gizmos via space.show_gizmo_tool =
# False and could fail to restore them. We force the flag back on for every
# VIEW_3D space on register so anyone upgrading from those versions doesn't
# stay stuck with hidden gizmos.

def _force_restore_builtin_tool_gizmos():
    try:
        wm = bpy.context.window_manager
    except Exception:
        return
    if wm is None:
        return
    for window in wm.windows:
        for area in window.screen.areas:
            if area.type != 'VIEW_3D':
                continue
            for space in area.spaces:
                if space.type == 'VIEW_3D':
                    space.show_gizmo_tool = True


# ============================================================================
# MODE TOGGLE + KEYMAP MANAGEMENT
# ============================================================================

# Keymap entries we own; emptied on disable so we never leave orphans behind.
_owned_keymap_items = []


def _install_keymaps():
    wm = bpy.context.window_manager
    kc = wm.keyconfigs.addon
    if kc is None:
        return
    km = kc.keymaps.new(name='Mesh', space_type='EMPTY')
    for key, ttype in (('G', 'TRANSLATE'), ('R', 'ROTATE'), ('S', 'RESIZE')):
        kmi = km.keymap_items.new(
            MESH_OT_edge_constraint_transform.bl_idname,
            key, 'PRESS',
        )
        kmi.properties.transform_type = ttype
        _owned_keymap_items.append((km, kmi))


def _uninstall_keymaps():
    while _owned_keymap_items:
        km, kmi = _owned_keymap_items.pop()
        try:
            km.keymap_items.remove(kmi)
        except Exception:
            pass


def _on_enabled_toggled(settings, context):
    if settings.enabled:
        _install_keymaps()
    else:
        _uninstall_keymaps()
    for area in context.screen.areas:
        area.tag_redraw()


class VIEW3D_OT_edge_constraint_toggle(Operator):
    """Toggle Edge Constraint Mode"""
    bl_idname = "view3d.edge_constraint_toggle"
    bl_label = "Toggle Edge Constraint Mode"
    bl_options = {'REGISTER'}

    def execute(self, context):
        s = context.scene.edge_constraint_mode
        s.enabled = not s.enabled
        return {'FINISHED'}


# ============================================================================
# HEADER UI
# ============================================================================

def _draw_header(self, context):
    # Only show in Mesh Edit mode — the mode isn't useful elsewhere yet.
    if context.mode != 'EDIT_MESH':
        return
    s = context.scene.edge_constraint_mode
    layout = self.layout
    row = layout.row(align=True)
    row.operator(
        VIEW3D_OT_edge_constraint_toggle.bl_idname,
        text="",
        icon='SNAP_EDGE',
        depress=s.enabled,
    )


# ============================================================================
# AUTO-DISABLE WHEN LEAVING EDIT MODE
# ============================================================================

from bpy.app.handlers import persistent


@persistent
def _on_depsgraph_update(scene, depsgraph):
    # If the user leaves edit mode while constraint mode is on, silently turn
    # the mode off so the keymap overrides aren't active during object-mode
    # navigation (where they'd be confusing).
    s = getattr(scene, "edge_constraint_mode", None)
    if s is None or not s.enabled:
        return
    obj = bpy.context.view_layer.objects.active if bpy.context.view_layer else None
    if obj is None or obj.mode != 'EDIT' or obj.type != 'MESH':
        s.enabled = False  # update callback will uninstall keymaps


# ============================================================================
# REGISTRATION
# ============================================================================

classes = (
    EdgeConstraintModeSettings,
    MESH_OT_edge_constraint_transform,
    VIEW3D_OT_edge_constraint_toggle,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.Scene.edge_constraint_mode = PointerProperty(type=EdgeConstraintModeSettings)
    bpy.types.VIEW3D_HT_header.append(_draw_header)
    if _on_depsgraph_update not in bpy.app.handlers.depsgraph_update_post:
        bpy.app.handlers.depsgraph_update_post.append(_on_depsgraph_update)
    # Recover from prior versions that may have left show_gizmo_tool=False.
    _force_restore_builtin_tool_gizmos()


def unregister():
    if _on_depsgraph_update in bpy.app.handlers.depsgraph_update_post:
        bpy.app.handlers.depsgraph_update_post.remove(_on_depsgraph_update)
    bpy.types.VIEW3D_HT_header.remove(_draw_header)
    _uninstall_keymaps()
    _force_restore_builtin_tool_gizmos()
    del bpy.types.Scene.edge_constraint_mode
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)


if __name__ == "__main__":
    register()
