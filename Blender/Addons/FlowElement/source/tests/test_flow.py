import math
import random

import pytest

from core import vec
from core.flow import arc_offset, predict_on_line, solve as _solve
from core.topology import Topology, continuation, opposite_pairs


def cylinder(segments=16, rings=7, radius=1.0, height=1.0):
    pos = {}
    for r in range(rings):
        for j in range(segments):
            a = 2 * math.pi * j / segments
            pos[r * segments + j] = (radius * math.cos(a), radius * math.sin(a), r * height)
    faces = []
    for r in range(rings - 1):
        for j in range(segments):
            j1 = (j + 1) % segments
            faces.append([r * segments + j, r * segments + j1,
                          (r + 1) * segments + j1, (r + 1) * segments + j])
    return pos, faces


def uv_sphere(segments=24, rings=16, radius=1.0):
    pos = {}
    for r in range(1, rings):  # skip poles: open top/bottom keeps the grid all-quad
        theta = math.pi * r / rings
        for j in range(segments):
            phi = 2 * math.pi * j / segments
            pos[(r - 1) * segments + j] = (
                radius * math.sin(theta) * math.cos(phi),
                radius * math.sin(theta) * math.sin(phi),
                radius * math.cos(theta))
    faces = []
    for r in range(rings - 2):
        for j in range(segments):
            j1 = (j + 1) % segments
            faces.append([r * segments + j, (r + 1) * segments + j,
                          (r + 1) * segments + j1, r * segments + j1])
    return pos, faces


def solve(pos, faces, moving, **kw):
    return _solve(pos, Topology.from_faces(faces), moving, **kw)


def radius_xy(p):
    return math.hypot(p[0], p[1])


# --- arc math -------------------------------------------------------------------------------

def test_arc_offset_exact_on_circle():
    pts = [(math.cos(a), math.sin(a), 0.0) for a in (math.radians(d) for d in (-90, -45, 45, 90))]
    p1, p2, p3, p4 = pts
    # vertex flattened onto the chord
    v = vec.lerp(p2, p3, 0.5)
    got = predict_on_line({0: p1, 1: p2, 2: v, 3: p3, 4: p4}, 2, (0, 1, 3, 4))
    assert got == pytest.approx((1.0, 0.0, 0.0), abs=1e-9)


def test_arc_offset_collinear_is_zero():
    assert arc_offset((-1, 0, 0), (0, 0, 0), (1, 0, 0), 0.5) == (0.0, 0.0, 0.0)


def test_half_circle_at_chord_end_is_finite():
    # circle through a, p2, p3 is a half circle and t = 1: 0/0 in the height formula
    assert arc_offset((0, 1, 0), (-1, 0, 0), (1, 0, 0), 1.0) == pytest.approx((0, 0, 0))


def test_s_bend_averages_to_chord():
    # p1 above, p4 below: the two circles bend opposite ways and cancel
    p1, p2, p3, p4 = (-2, 1, 0), (-1, 0, 0), (1, 0, 0), (2, -1, 0)
    pos = {0: p1, 1: p2, 2: (0, 0.5, 0), 3: p3, 4: p4}
    got = predict_on_line(pos, 2, (0, 1, 3, 4))
    assert got == pytest.approx((0.0, 0.0, 0.0), abs=1e-9)


def test_keeps_parameter_along_chord():
    p1, p2, p3, p4 = (-2, 0, 0), (-1, 0, 0), (1, 0, 0), (2, 0, 0)
    pos = {0: p1, 1: p2, 2: (0.4, 0.3, 0), 3: p3, 4: p4}
    assert predict_on_line(pos, 2, (0, 1, 3, 4)) == pytest.approx((0.4, 0.0, 0.0))


# --- topology -------------------------------------------------------------------------------

def test_fan_and_opposites_on_grid():
    pos, faces = cylinder()
    topo = Topology.from_faces(faces)
    v = 3 * 16 + 5
    ring, closed = topo.fan(v)
    assert closed and len(ring) == 4
    pairs = {frozenset(p) for p in opposite_pairs(topo, pos, v)}
    assert pairs == {frozenset((2 * 16 + 5, 4 * 16 + 5)), frozenset((3 * 16 + 4, 3 * 16 + 6))}
    assert continuation(topo, pos, 2 * 16 + 5, v) == 1 * 16 + 5


def test_boundary_vertex_fan_is_open():
    pos, faces = cylinder()
    ring, closed = Topology.from_faces(faces).fan(3)
    assert not closed and len(ring) == 3


# --- solver ---------------------------------------------------------------------------------

def _ring_edges(ring, segments):
    return [(ring * segments + j, ring * segments + (j + 1) % segments) for j in range(segments)]


@pytest.mark.parametrize("segments", [8, 16, 32])
def test_edge_flow_restores_flattened_cylinder_ring(segments):
    pos, faces = cylinder(segments)
    ring = 3
    moving = {ring * segments + j for j in range(segments)}
    for v in moving:  # scale the ring towards the axis (uniform flatten)
        x, y, z = pos[v]
        pos[v] = (x * 0.6, y * 0.6, z)
    out = solve(pos, faces, moving, excluded_edges=_ring_edges(ring, segments))
    for v in moving:
        assert radius_xy(out[v]) == pytest.approx(1.0, abs=1e-6)
        assert out[v][2] == pytest.approx(3.0)


def test_edge_flow_squashed_ring():
    # squashed in X only: vertices also leave their angle, restored onto the cylinder
    segments = 16
    pos, faces = cylinder(segments)
    moving = {3 * segments + j for j in range(segments)}
    for v in moving:
        x, y, z = pos[v]
        pos[v] = (x * 0.5, y, z)
    out = solve(pos, faces, moving, excluded_edges=_ring_edges(3, segments))
    for v in moving:
        assert radius_xy(out[v]) == pytest.approx(1.0, abs=1e-6)


def test_edge_flow_noisy_ring():
    segments = 24
    pos, faces = cylinder(segments)
    rnd = random.Random(4)
    moving = {3 * segments + j for j in range(segments)}
    for v in moving:
        x, y, z = pos[v]
        s = rnd.uniform(0.8, 1.2)
        pos[v] = (x * s, y * s, z + rnd.uniform(-0.1, 0.1))
    out = solve(pos, faces, moving, excluded_edges=_ring_edges(3, segments))
    for v in moving:
        assert radius_xy(out[v]) == pytest.approx(1.0, abs=0.01)


def test_two_adjacent_rings_converge():
    segments = 16
    pos, faces = cylinder(segments, rings=9)
    rings = (3, 4)
    moving = {r * segments + j for r in rings for j in range(segments)}
    for v in moving:
        x, y, z = pos[v]
        pos[v] = (x * 0.5, y * 0.5, z)
    excluded = _ring_edges(3, segments) + _ring_edges(4, segments)
    out = solve(pos, faces, moving, excluded_edges=excluded)
    for v in moving:
        assert radius_xy(out[v]) == pytest.approx(1.0, abs=1e-3)


def test_vertex_flow_single_dent_on_sphere():
    pos, faces = uv_sphere()
    v = 7 * 24 + 3
    pos[v] = vec.scale(pos[v], 0.7)
    out = solve(pos, faces, {v})
    assert vec.length(out[v]) == pytest.approx(1.0, abs=0.01)


@pytest.mark.parametrize("size", [(4, 5), (8, 10)])
def test_face_flow_flattened_sphere_patch(size):
    pos, faces = uv_sphere(48, 32)
    rows, cols = size
    patch = [f for f in faces if 10 * 48 <= f[0] < (10 + rows) * 48 and f[0] % 48 in range(4, 4 + cols)]
    moving = {i for f in patch for i in f}
    # flatten the patch onto the plane through its centroid along the mean normal
    c = vec.scale(tuple(sum(pos[i][k] for i in moving) for k in range(3)), 1.0 / len(moving))
    n = vec.normalized(c)
    for i in moving:
        d = vec.dot(vec.sub(pos[i], c), n)
        pos[i] = vec.sub(pos[i], vec.scale(n, d))
    before = max(abs(vec.length(pos[i]) - 1.0) for i in moving)
    out = solve(pos, faces, moving)
    after = max(abs(vec.length(out[i]) - 1.0) for i in moving)
    assert before > 0.03
    assert after < 1e-6


def test_flat_plane_stays_flat():
    # 5x5 grid, middle vertex lifted: vertex flow puts it back on the plane
    n = 5
    pos = {r * n + c: (float(c), float(r), 0.0) for r in range(n) for c in range(n)}
    faces = [[r * n + c, r * n + c + 1, (r + 1) * n + c + 1, (r + 1) * n + c]
             for r in range(n - 1) for c in range(n - 1)]
    v = 2 * n + 2
    pos[v] = (2.0, 2.0, 0.5)
    out = solve(pos, faces, {v})
    assert out[v] == pytest.approx((2.0, 2.0, 0.0), abs=1e-9)


def test_tension_zero_is_linear():
    pos, faces = cylinder(8)
    v = 3 * 8
    pos[v] = (0.5, 0.0, 3.0)
    out = solve(pos, faces, {v}, tension=0.0, excluded_edges=_ring_edges(3, 8))
    # the axis line is straight anyway; ring-only flow at tension 0 lands on the chord
    out2 = solve(pos, faces, {v}, tension=0.0,
                 excluded_edges=[(v, 2 * 8), (v, 4 * 8)])
    assert out[v] == pytest.approx((1.0, 0.0, 3.0))
    assert out2[v][0] == pytest.approx(math.cos(math.radians(45)))


def test_face_flow_flattened_cylinder_half():
    # a wide patch spanning a third of the cylinder, flattened to its chord plane
    segments = 24
    pos, faces = cylinder(segments, rings=12)
    patch = [f for f in faces if 3 * segments <= f[0] < 8 * segments and f[0] % segments < 8]
    moving = {i for f in patch for i in f}
    for i in moving:
        x, y, z = pos[i]
        pos[i] = (min(x, math.cos(math.radians(60))) if x > 0 else x, y, z)
    out = solve(pos, faces, moving)
    assert len(out) == len(moving)
    for i in moving:
        assert radius_xy(out[i]) == pytest.approx(1.0, abs=1e-5)


def test_line_without_fixed_anchor_is_skipped():
    # whole cylinder ring selected in vertex mode: the ring line never leaves the selection,
    # only the axis line is used
    segments = 12
    pos, faces = cylinder(segments)
    moving = {3 * segments + j for j in range(segments)}
    for v in moving:
        x, y, z = pos[v]
        pos[v] = (x * 0.7, y * 0.7, z)
    out = solve(pos, faces, moving)
    for v in moving:
        assert radius_xy(out[v]) == pytest.approx(1.0, abs=1e-6)
