"""Flow solver: rebuild curvature of moving vertices from the surrounding geometry.

Each moving vertex ``v`` gets a set of *lines*: pairs of opposite edges through it. A line is
walked outward on both sides, through any other moving vertices, until it reaches fixed
geometry — the anchors ``A1``/``B1`` — plus one more vertex beyond each (``A2``/``B2``):

    A2 ---- A1 ---- (moving ...) v (... moving) ---- B1 ---- B2

The circle through ``(A2, A1, B1)`` and the circle through ``(A1, B1, B2)`` each predict where
``v`` sits on the arc between ``A1`` and ``B1``; the two are averaged (circle-average — exact
on circles, the straight chord at an S-bend inflection). A line only constrains ``v`` across
its own direction, so the lines through ``v`` are combined by least squares on their
perpendicular components — exact where lines cross on a cylinder or sphere, where a plain
average of their points would cut inside the surface. Each vertex keeps its parameter along
every line, so it moves across the lines, never along them.

Anchors are always fixed geometry, so the solve is direct — no slow fairing iterations, and
whole flattened patches come back in one pass.
"""

import math

from . import vec
from .topology import continuation, edge_key, opposite_pairs

MODE_VERTEX = "VERTEX"
MODE_EDGE = "EDGE"
MODE_FACE = "FACE"

MAX_WALK = 256  # edges walked per side before a line is given up
TANGENT_DT = 1e-3  # chord-parameter step for the curve tangent at the prediction


def arc_offset(a, p2, p3, t):
    """Offset from the chord point ``lerp(p2, p3, t)`` to the circle through ``a, p2, p3``."""
    chord = vec.sub(p3, p2)
    chord_len2 = vec.dot(chord, chord)
    if chord_len2 < 1e-20:
        return (0.0, 0.0, 0.0)
    chord_len = math.sqrt(chord_len2)

    ap = vec.sub(a, p2)
    perp = vec.sub(ap, vec.scale(chord, vec.dot(ap, chord) / chord_len2))
    perp_len = vec.length(perp)
    if perp_len < 1e-9 * chord_len:
        return (0.0, 0.0, 0.0)  # collinear: straight line

    pa, qa = vec.sub(p2, a), vec.sub(p3, a)
    denom = vec.length(pa) * vec.length(qa) * chord_len
    if denom < 1e-20:
        return (0.0, 0.0, 0.0)
    k = 2.0 * vec.length(vec.cross(pa, qa)) / denom  # curvature 1/R

    h = chord_len * 0.5
    k = min(k, 1.0 / h)  # at most a half circle between p2 and p3
    x = (t - 0.5) * chord_len
    # height of the circle above the chord at x, written to stay stable as k -> 0
    den = math.sqrt(max(0.0, 1.0 - (k * x) ** 2)) + math.sqrt(max(0.0, 1.0 - (k * h) ** 2))
    if den < 1e-12:
        return (0.0, 0.0, 0.0)  # half circle, v on a chord end: the arc meets the chord there
    height = k * (h * h - x * x) / den
    # the circle's centre is on a's side of the chord; the arc p2-p3 bulges away from it
    return vec.scale(perp, -height / perp_len)


def chord_param(positions, v, line):
    p2, p3 = positions[line[1]], positions[line[2]]
    chord = vec.sub(p3, p2)
    chord_len2 = vec.dot(chord, chord)
    if chord_len2 < 1e-20:
        return None
    return min(1.0, max(0.0, vec.dot(vec.sub(positions[v], p2), chord) / chord_len2))


def predict_on_line(positions, v, line, tension=1.0, t=None):
    """Where ``v`` should sit on ``line = (p1, p2, p3, p4)`` (p1/p4 may be ``None``).

    ``t`` is the chord parameter between p2 and p3; by default ``v``'s own projection, so
    the vertex keeps its place along the line.
    """
    i1, i2, i3, i4 = line
    p2, p3 = positions[i2], positions[i3]
    chord = vec.sub(p3, p2)
    chord_len2 = vec.dot(chord, chord)
    if chord_len2 < 1e-20:
        return None
    if t is None:
        t = min(1.0, max(0.0, vec.dot(vec.sub(positions[v], p2), chord) / chord_len2))
    base = vec.lerp(p2, p3, t)

    offsets = [arc_offset(positions[i], p2, p3, t) for i in (i1, i4) if i is not None]
    if not offsets:
        return base
    acc = (0.0, 0.0, 0.0)
    for o in offsets:
        acc = vec.add(acc, o)
    return vec.add(base, vec.scale(acc, tension / len(offsets)))


def line_tangent(positions, v, line, tension, t):
    """Unit tangent of the predicted curve at chord parameter ``t``."""
    a = predict_on_line(positions, v, line, tension, max(0.0, t - TANGENT_DT))
    b = predict_on_line(positions, v, line, tension, min(1.0, t + TANGENT_DT))
    if a is None or b is None:
        return None
    return vec.normalized(vec.sub(b, a))


def _solve3(m, b):
    """Solve the 3x3 system ``m x = b`` (Cramer); ``None`` when singular."""
    def det(c0, c1, c2):
        return vec.dot(c0, vec.cross(c1, c2))
    cols = [tuple(m[r][c] for r in range(3)) for c in range(3)]
    d = det(*cols)
    if abs(d) < 1e-12:
        return None
    return (det(b, cols[1], cols[2]) / d, det(cols[0], b, cols[2]) / d,
            det(cols[0], cols[1], b) / d)


def combine_lines(displacements):
    """Least-squares displacement from ``[(d_i, u_i), ...]``.

    Each line asks for displacement ``d_i`` but only across its tangent ``u_i``; solve
    ``sum(P_i) d = sum(P_i d_i)`` with ``P_i = I - u_i u_i^T``.
    """
    m = [[0.0] * 3 for _ in range(3)]
    b = (0.0, 0.0, 0.0)
    for d, u in displacements:
        for r in range(3):
            for c in range(3):
                m[r][c] += (1.0 if r == c else 0.0) - u[r] * u[c]
        b = vec.add(b, vec.sub(d, vec.scale(u, vec.dot(u, d))))
    if len(displacements) == 1:
        return b
    # tiny ridge keeps near-parallel lines solvable without biasing the result
    n = float(len(displacements))
    for r in range(3):
        m[r][r] += 1e-6 * n
    x = _solve3(m, b)
    return x if x is not None else vec.scale(b, 1.0 / n)


def walk_to_anchor(topo, positions, moving, v, first):
    """Follow the line ``v -> first`` until it leaves the moving set.

    Returns ``(A1, A2)`` — the first fixed vertex and the one beyond it (``None`` where the
    line ends) — or ``None`` if the line never reaches fixed geometry.
    """
    prev, cur = v, first
    for _ in range(MAX_WALK):
        if cur not in moving:
            return cur, continuation(topo, positions, cur, prev)
        nxt = continuation(topo, positions, cur, prev)
        if nxt is None or nxt == v:
            return None
        prev, cur = cur, nxt
    return None


def build_lines(topo, positions, moving, v, excluded_edges=frozenset()):
    lines = []
    for a, b in opposite_pairs(topo, positions, v, excluded_edges):
        side_a = walk_to_anchor(topo, positions, moving, v, a)
        side_b = walk_to_anchor(topo, positions, moving, v, b)
        if side_a and side_b:
            lines.append((side_a[1], side_a[0], side_b[0], side_b[1]))
    return lines


def moving_vertices(mode, selected_verts=(), selected_edges=(), selected_faces=()):
    if mode == MODE_FACE:
        return {i for f in selected_faces for i in f}
    if mode == MODE_EDGE:
        return {i for e in selected_edges for i in e}
    return set(selected_verts)


class _Overlay:
    """Read-through view of ``base`` positions with this solve's updates on top."""

    def __init__(self, base):
        self.base = base
        self.updates = {}

    def __getitem__(self, i):
        p = self.updates.get(i)
        return p if p is not None else tuple(self.base[i])

    def __contains__(self, i):
        return i in self.updates or i in self.base


def solve(positions, topo, moving, excluded_edges=(), tension=1.0, passes=4):
    """Return ``{index: new_position}`` for every moving vertex that has a usable line.

    ``topo`` is a :class:`Topology`; ``positions`` any mapping ``index -> xyz`` covering the
    walked lines. ``excluded_edges`` (index pairs) never start a line — pass the selected
    edges in edge mode so loops flow across their crossing ring. Extra ``passes`` re-evaluate
    the chord parameters and line tangents at the already-corrected positions; the anchors
    never move, so this is a refinement, not a fairing iteration.
    """
    moving = set(moving)
    excluded = frozenset(edge_key(a, b) for a, b in excluded_edges)
    pos = _Overlay(positions)
    lines = {v: build_lines(topo, pos, moving, v, excluded) for v in moving}
    active = [v for v in moving if lines[v]]

    for _ in range(max(1, passes)):
        updates = {}
        for v in active:
            wanted = []
            for ln in lines[v]:
                t = chord_param(pos, v, ln)
                if t is None:
                    continue
                p = predict_on_line(pos, v, ln, tension, t)
                u = line_tangent(pos, v, ln, tension, t)
                if p is not None and u is not None:
                    wanted.append((vec.sub(p, pos[v]), u))
            if not wanted:
                continue
            updates[v] = vec.add(pos[v], combine_lines(wanted))
        pos.updates.update(updates)

    return dict(pos.updates)
