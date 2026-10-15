import math

import pytest

from core import constraint as C
from core import transform as T
from core import vec
from tests.meshes import cube_with_cuts, on_cube_surface


def approx_pt(p, q, tol=1e-6):
    return all(abs(a - b) <= tol for a, b in zip(p, q))


def solve_ring(mode, ring_axis_values, ring_index, op, axis=2, **kw):
    positions, edges, faces, rings = cube_with_cuts(ring_axis_values, axis=axis)
    sel = set()
    for ri in (ring_index if isinstance(ring_index, (list, tuple)) else [ring_index]):
        sel.update(rings[ri])
    mesh = C.MeshData(positions, edges, faces, sel)
    pts = {v: positions[v] for v in sel}
    targets = op(pts)
    cons = C.build_constraints(mesh, mode, **kw)
    return positions, rings, sel, C.solve(cons, targets)


# -- The acceptance test from the brief ------------------------------------

@pytest.mark.parametrize("angle_deg", [10, 30, 44])
@pytest.mark.parametrize("rot_axis", [(1, 0, 0), (0, 1, 0), (1, 1, 0)])
def test_rotating_loop_with_edge_constraint_keeps_cube(angle_deg, rot_axis):
    """Cube + one horizontal loop, rotate the loop: verts only move along the
    vertical edges, so the cube stays a cube and the loop is sheared."""
    angle = math.radians(angle_deg)

    def op(pts):
        piv = T.pivot_point(list(pts.values()), T.PIVOT_MEDIAN)
        return T.rotate(pts, piv, rot_axis, angle)

    positions, rings, sel, out = solve_ring(C.MODE_EDGE, [0.0], 1, op)
    for v, p in out.items():
        x0, y0, _ = positions[v]
        assert approx_pt((p[0], p[1]), (x0, y0)), "vert left its vertical rail"
        assert on_cube_surface(p)
    # The loop really moved (sheared), and stays planar.
    zs = [out[v][2] for v in rings[1]]
    assert max(abs(z) for z in zs) > 0.1
    a, b, c, d = (out[v] for v in rings[1])
    n = vec.cross(vec.sub(b, a), vec.sub(c, a))
    assert abs(vec.dot(n, vec.sub(d, a))) < 1e-6


def test_rotate_about_x_gives_exact_shear():
    angle = math.radians(30)

    def op(pts):
        return T.rotate(pts, (0, 0, 0), (1, 0, 0), angle)

    positions, rings, sel, out = solve_ring(C.MODE_EDGE, [0.0], 1, op)
    for v in rings[1]:
        y0 = positions[v][1]
        assert out[v][2] == pytest.approx(y0 * math.sin(angle))


def test_free_rotation_would_break_the_cube():
    angle = math.radians(30)
    positions, edges, faces, rings = cube_with_cuts([0.0])
    pts = {v: positions[v] for v in rings[1]}
    out = T.rotate(pts, (0, 0, 0), (0, 0, 1), angle)
    assert not all(on_cube_surface(p) for p in out.values())


def test_rotation_about_loop_axis_slides_along_loop_edges():
    """Rotating the loop about its own normal has no component along the
    crossing edges, so (as in Max) the verts slide along the loop's own
    edges instead: still on the cube, still at z=0."""
    def op(pts):
        return T.rotate(pts, (0, 0, 0), (0, 0, 1), math.radians(20))

    positions, rings, sel, out = solve_ring(C.MODE_EDGE, [0.0], 1, op)
    for v, p in out.items():
        assert on_cube_surface(p)
        assert p[2] == pytest.approx(0.0)


# -- Move ----------------------------------------------------------------------

def test_move_diagonal_only_keeps_rail_component():
    positions, rings, sel, out = solve_ring(
        C.MODE_EDGE, [0.0], 1, lambda pts: T.translate(pts, (0.7, -0.3, 0.4)))
    for v, p in out.items():
        x0, y0, _ = positions[v]
        assert approx_pt(p, (x0, y0, 0.4))


def test_move_past_end_clamps_at_corner():
    positions, rings, sel, out = solve_ring(
        C.MODE_EDGE, [0.0], 1, lambda pts: T.translate(pts, (0, 0, 5)))
    for v, p in out.items():
        x0, y0, _ = positions[v]
        assert approx_pt(p, (x0, y0, 1.0))


def test_move_stops_at_selected_neighbour_loop():
    # Two loops selected (z=-0.5 and z=0.5); the lower one may not slide past
    # the upper one when stop_at_selected is on.
    positions, edges, faces, rings = cube_with_cuts([-0.5, 0.5])
    sel = set(rings[1])
    mesh = C.MeshData(positions, edges, faces, sel | set(rings[2]))
    cons = C.build_constraints(mesh, C.MODE_EDGE, stop_at_selected=True)
    pts = {v: positions[v] for v in sel}
    out = C.solve(cons, T.translate(pts, (0, 0, 3)))
    for v in sel:
        assert out[v][2] == pytest.approx(0.5)


def test_slide_continues_past_vertex_on_straight_rail():
    # A straight 4-vertex polyline; slide vertex 1 by 1.5 -> lands on edge 2-3.
    positions = [(0, 0, 0), (1, 0, 0), (2, 0, 0), (3, 0, 0)]
    edges = [(0, 1), (1, 2), (2, 3)]
    mesh = C.MeshData(positions, edges, [], {1})
    cons = C.build_constraints(mesh, C.MODE_EDGE)
    out = C.solve(cons, {1: (2.5, 0.3, 0)})
    assert approx_pt(out[1], (2.5, 0, 0))


# -- Scale ---------------------------------------------------------------------

@pytest.mark.parametrize("factors", [(1.6, 1.0, 1.0), (1.6, 1.6, 1.6), (0.4, 1.2, 1.2)])
def test_scale_two_loops_slides_them_along_x(factors):
    def op(pts):
        piv = T.pivot_point(list(pts.values()), T.PIVOT_MEDIAN)
        return T.scale(pts, piv, factors)

    positions, rings, sel, out = solve_ring(C.MODE_EDGE, [-0.5, 0.5], [1, 2], op, axis=0)
    for v, p in out.items():
        x0, y0, z0 = positions[v]
        assert approx_pt(p, (x0 * factors[0], y0, z0))
        assert on_cube_surface(p)


def test_scale_loop_on_cone_slides_along_slant():
    # Frustum: bottom ring radius 2 at z=0, mid ring radius 1.5 at z=1,
    # top ring radius 1 at z=2. Scaling the mid ring up must move it down
    # the slanted edges (staying on the cone surface).
    rings, positions = [], []
    for z, r in ((0.0, 2.0), (1.0, 1.5), (2.0, 1.0)):
        ring = []
        for k in range(8):
            a = 2 * math.pi * k / 8
            ring.append(len(positions))
            positions.append((r * math.cos(a), r * math.sin(a), z))
        rings.append(ring)
    faces = []
    for r0, r1 in zip(rings, rings[1:]):
        for i in range(8):
            j = (i + 1) % 8
            faces.append((r0[i], r0[j], r1[j], r1[i]))
    from tests.meshes import edges_from_faces
    mesh = C.MeshData(positions, edges_from_faces(faces), faces, set(rings[1]))
    cons = C.build_constraints(mesh, C.MODE_EDGE)
    pts = {v: positions[v] for v in rings[1]}
    out = C.solve(cons, T.scale(pts, (0, 0, 1), (1.2, 1.2, 1.2)))
    for v in rings[1]:
        x, y, z = out[v]
        r = math.hypot(x, y)
        assert z < 1.0
        assert r == pytest.approx(2.0 - 0.5 * z, abs=1e-6)  # on the slant


# -- Face / Normal ---------------------------------------------------------

def test_face_constraint_rotation_keeps_verts_on_cube_surface():
    def op(pts):
        return T.rotate(pts, (0, 0, 0), (0, 0, 1), math.radians(30))

    positions, rings, sel, out = solve_ring(C.MODE_FACE, [0.0], 1, op)
    moved = False
    for v, p in out.items():
        assert on_cube_surface(p)
        moved |= not approx_pt(p, positions[v])
    assert moved


def test_face_constraint_move_rejects_off_surface_motion():
    positions, rings, sel, out = solve_ring(
        C.MODE_FACE, [0.0], 1, lambda pts: T.translate(pts, (0.3, 5.0, 0.25)))
    for v, p in out.items():
        assert on_cube_surface(p)
        assert p[2] == pytest.approx(0.25)


def test_normal_constraint_pushes_along_normal():
    positions, edges, faces, rings = cube_with_cuts([0.0])
    top = set(rings[-1])
    mesh = C.MeshData(positions, edges, faces, top)
    cons = C.build_constraints(mesh, C.MODE_NORMAL)
    pts = {v: positions[v] for v in top}
    out = C.solve(cons, T.translate(pts, (0.5, 0.5, 0.5)))
    for v in top:
        n = mesh.vertex_normal(v)
        d = vec.sub(out[v], positions[v])
        assert vec.length(vec.cross(d, n)) < 1e-9


def test_none_mode_is_free():
    positions, rings, sel, out = solve_ring(
        C.MODE_NONE, [0.0], 1, lambda pts: T.translate(pts, (1, 2, 3)))
    for v, p in out.items():
        assert approx_pt(p, vec.add(positions[v], (1, 2, 3)))


def test_fully_selected_mesh_falls_back_to_all_edges():
    positions, edges, faces, rings = cube_with_cuts([0.0])
    allv = set(range(len(positions)))
    mesh = C.MeshData(positions, edges, faces, allv)
    cons = C.build_constraints(mesh, C.MODE_EDGE)
    v = rings[1][0]
    out = C.solve(cons, {v: vec.add(positions[v], (0, 0, 0.3))})
    assert approx_pt(out[v], vec.add(positions[v], (0, 0, 0.3)))


# -- transform helpers ---------------------------------------------------------

def test_mask_vector_and_pivots():
    assert T.mask_vector((1, 2, 3), (False, False, True)) == (0, 0, 3)
    pts = [(0, 0, 0), (2, 0, 0), (2, 4, 0)]
    assert approx_pt(T.pivot_point(pts, T.PIVOT_BOUNDS), (1, 2, 0))
    assert approx_pt(T.pivot_point(pts, T.PIVOT_CURSOR, cursor=(5, 5, 5)), (5, 5, 5))
