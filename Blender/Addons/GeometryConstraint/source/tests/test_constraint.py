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


def test_rotation_about_loop_axis_is_absorbed():
    """Rotating the loop about its own normal has no component along the
    crossing edges; the sideways part is rejected (Max: motion across the
    edge is ignored), so nothing moves - the loop doesn't slide along itself."""
    def op(pts):
        return T.rotate(pts, (0, 0, 0), (0, 0, 1), math.radians(20))

    positions, rings, sel, out = solve_ring(C.MODE_EDGE, [0.0], 1, op)
    for v, p in out.items():
        assert approx_pt(p, positions[v])


def test_tilting_a_round_loop_keeps_hinge_verts_in_place():
    """Cylinder loop rotated about a horizontal axis: the hinge verts (on the
    rotation axis's plane) have purely sideways motion and must stay put, the
    rest only move vertically -> a clean planar tilt."""
    n = 16
    rings, positions = [], []
    for z in (-1.0, 0.0, 1.0):
        ring = []
        for k in range(n):
            a = 2 * math.pi * k / n
            ring.append(len(positions))
            positions.append((math.cos(a), math.sin(a), z))
        rings.append(ring)
    faces = [(r0[i], r0[(i + 1) % n], r1[(i + 1) % n], r1[i])
             for r0, r1 in zip(rings, rings[1:]) for i in range(n)]
    from tests.meshes import edges_from_faces
    mesh = C.MeshData(positions, edges_from_faces(faces), faces, set(rings[1]))
    cons = C.build_constraints(mesh, C.MODE_EDGE)
    pts = {v: positions[v] for v in rings[1]}
    out = C.solve(cons, T.rotate(pts, (0, 0, 0), (1, 0, 0), math.radians(25)))
    for v, p in out.items():
        x0, y0, _ = positions[v]
        assert approx_pt((p[0], p[1]), (x0, y0))
        assert p[2] == pytest.approx(y0 * math.sin(math.radians(25)), abs=1e-9)


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


def test_move_stops_at_unselected_loop():
    # Only the upper loop (z=0.5) is selected; moving it down must stop on the
    # existing, unselected loop at z=-0.5 instead of sliding through to z=-1.
    positions, edges, faces, rings = cube_with_cuts([-0.5, 0.5])
    sel = set(rings[2])
    mesh = C.MeshData(positions, edges, faces, sel)
    cons = C.build_constraints(mesh, C.MODE_EDGE)
    pts = {v: positions[v] for v in sel}
    out = C.solve(cons, T.translate(pts, (0, 0, -3)))
    for v in sel:
        assert out[v][2] == pytest.approx(-0.5)


def test_scaling_two_selected_loops_slides_them_along_the_rungs():
    # Vertex mode, loops at z=+-0.6 scaled 0.25 about the centre: the motion
    # points mostly sideways along the loops, but the verts may only slide
    # along the vertical rung between the loops - the cube stays a cube.
    positions, edges, faces, rings = cube_with_cuts([-0.6, 0.6])
    sel = set(rings[1]) | set(rings[2])
    mesh = C.MeshData(positions, edges, faces, sel)
    pts = {v: positions[v] for v in sel}
    piv = T.pivot_point(list(pts.values()), T.PIVOT_MEDIAN)
    out = C.solve(C.build_constraints(mesh, C.MODE_EDGE), T.scale(pts, piv, (0.25,) * 3))
    for v in sel:
        x, y, z = positions[v]
        assert approx_pt(out[v], (x, y, z * 0.25)), (v, out[v])


def _two_front_edges():
    # Loops at z=-0.5 / z=0.5; select only their edges on the x=+1 face (edge
    # select mode), NOT the vertical cube edges joining them.
    positions, edges, faces, rings = cube_with_cuts([-0.5, 0.5])
    lo, hi = (rings[1][0], rings[1][3]), (rings[2][0], rings[2][3])
    sel = set(lo) | set(hi)
    sel_edges = {lo, hi}
    mesh = C.MeshData(positions, edges, faces, sel, selected_edges=sel_edges)
    return positions, mesh, sel


def test_scaling_two_selected_edges_slides_them_along_the_joining_edges():
    positions, mesh, sel = _two_front_edges()
    pts = {v: positions[v] for v in sel}
    piv = T.pivot_point(list(pts.values()), T.PIVOT_MEDIAN)
    out = C.solve(C.build_constraints(mesh, C.MODE_EDGE), T.scale(pts, piv, (0.3, 0.3, 0.3)))
    for v in sel:
        x, y, z = positions[v]
        assert approx_pt(out[v], (x, y, z * 0.3)), (v, out[v])


def test_rotating_two_selected_edges_keeps_them_on_the_cube_edges():
    positions, mesh, sel = _two_front_edges()
    pts = {v: positions[v] for v in sel}
    piv = T.pivot_point(list(pts.values()), T.PIVOT_MEDIAN)
    out = C.solve(C.build_constraints(mesh, C.MODE_EDGE),
                  T.rotate(pts, piv, (1, 0, 0), math.radians(30)))
    moved = False
    for v in sel:
        x, y, _z = positions[v]
        assert out[v][0] == pytest.approx(x) and out[v][1] == pytest.approx(y), (v, out[v])
        assert -1.0 - 1e-6 <= out[v][2] <= 1.0 + 1e-6
        moved |= abs(out[v][2] - positions[v][2]) > 0.05
    assert moved


def test_slide_stops_at_next_vertex_by_default():
    positions = [(0, 0, 0), (1, 0, 0), (2, 0, 0), (3, 0, 0)]
    edges = [(0, 1), (1, 2), (2, 3)]
    mesh = C.MeshData(positions, edges, [], {1})
    cons = C.build_constraints(mesh, C.MODE_EDGE)
    out = C.solve(cons, {1: (2.5, 0.3, 0)})
    assert approx_pt(out[1], (2, 0, 0))


def test_slide_continues_past_vertex_on_straight_rail():
    # Stop at Vertices off: slide vertex 1 by 1.5 -> lands on edge 2-3.
    positions = [(0, 0, 0), (1, 0, 0), (2, 0, 0), (3, 0, 0)]
    edges = [(0, 1), (1, 2), (2, 3)]
    mesh = C.MeshData(positions, edges, [], {1})
    cons = C.build_constraints(mesh, C.MODE_EDGE, stop_at_vertices=False)
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


def test_face_constraint_moves_a_patch_as_a_whole():
    """A selected patch on a bumpy grid dragged sideways: every vert stays on
    the original surface and the trailing verts keep up (no squashing)."""
    import math as m
    n, size = 16, 4.0

    def h(x, y):
        return 0.3 * m.sin(1.5 * x) * m.cos(1.5 * y)

    positions, idx = [], {}
    for j in range(n + 1):
        for i in range(n + 1):
            x, y = -size / 2 + size * i / n, -size / 2 + size * j / n
            idx[i, j] = len(positions)
            positions.append((x, y, h(x, y)))
    faces = [(idx[i, j], idx[i + 1, j], idx[i + 1, j + 1], idx[i, j + 1])
             for j in range(n) for i in range(n)]
    from tests.meshes import edges_from_faces
    sel = {idx[i, j] for i in range(4, 8) for j in range(6, 10)}
    mesh = C.MeshData(positions, edges_from_faces(faces), faces, sel)
    cons = C.build_constraints(mesh, C.MODE_FACE, reach=8)
    pts = {v: positions[v] for v in sel}
    out = C.solve(cons, T.translate(pts, (0.75, 0.0, 0.4)))
    shifts = [out[v][0] - positions[v][0] for v in sel]
    assert min(shifts) > 0.6, "trailing verts were left behind"
    # On the surface: each result lies on some original triangle.
    tris = [t for f in faces for t in C._triangulate(positions, f)]
    for p in out.values():
        d = min(vec.dist_sq(p, vec.closest_point_on_triangle(p, *t)) for t in tris)
        assert d < 1e-12
