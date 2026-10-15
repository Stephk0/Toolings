"""Edge / Face / Normal constraint solver (bpy-free).

Model (mirrors 3ds Max Editable Poly "Constraints"):

* The transform (move / rotate / scale, any pivot, any axis lock) first
  computes a *free* target position for every selected vertex.
* The constraint then snaps that target back onto the vertex's allowed
  geometry, measured on the ORIGINAL mesh:

  EDGE   - the closest point on the vertex's "rail" network: the edges that
           leave the vertex towards unselected geometry, continued edge by
           edge for ``reach`` steps so a vertex can slide past a corner.
  FACE   - the closest point on the surface of the polygons around the
           vertex (again grown ``reach`` rings), so it slides over the
           surface instead of leaving it.
  NORMAL - the target projected onto the vertex normal line.

Rails deliberately skip edges/faces that lie *inside* the selection: a
selected loop on a cube can only slide along the edges that cross it, which
is exactly what turns a rotation of that loop into a shear that keeps the
cube a cube.

Everything here works on plain 3-tuples; the Blender wrapper converts to and
from world space so object scale does not skew the projection.
"""

from . import vec

MODE_NONE = 'NONE'
MODE_EDGE = 'EDGE'
MODE_FACE = 'FACE'
MODE_NORMAL = 'NORMAL'
MODES = (MODE_NONE, MODE_EDGE, MODE_FACE, MODE_NORMAL)

DEFAULT_REACH = 4
# Walking past a vertex only continues onto an edge within ~60 deg of the
# previous one.
TURN_LIMIT_COS = 0.5
# Score multiplier for edges whose both ends are selected (e.g. the loop's own
# edges): they still work as rails, but a crossing edge wins unless the
# in-loop edge is much better aligned.
IN_SELECTION_BIAS = 0.5


class MeshData:
    """Plain-data mesh snapshot: positions, edges, faces, selection."""

    def __init__(self, positions, edges, faces, selected, normals=None):
        self.positions = [tuple(p) for p in positions]
        self.edges = [tuple(e) for e in edges]
        self.faces = [tuple(f) for f in faces]
        self.selected = set(selected)
        self._normals = normals

        n = len(self.positions)
        self.vert_edges = [[] for _ in range(n)]
        for ei, (a, b) in enumerate(self.edges):
            self.vert_edges[a].append(ei)
            self.vert_edges[b].append(ei)

        self.vert_faces = [[] for _ in range(n)]
        self.edge_faces = {}
        for fi, f in enumerate(self.faces):
            for i, v in enumerate(f):
                self.vert_faces[v].append(fi)
                key = _edge_key(v, f[(i + 1) % len(f)])
                self.edge_faces.setdefault(key, []).append(fi)

    def other(self, ei, v):
        a, b = self.edges[ei]
        return b if a == v else a

    def edge_fully_selected(self, ei):
        a, b = self.edges[ei]
        return a in self.selected and b in self.selected

    def face_fully_selected(self, fi):
        return all(v in self.selected for v in self.faces[fi])

    def vertex_normal(self, v):
        if self._normals is not None:
            return vec.normalized(self._normals[v])
        acc = (0.0, 0.0, 0.0)
        for fi in self.vert_faces[v]:
            acc = vec.add(acc, _face_area_normal(self.positions, self.faces[fi]))
        return vec.normalized(acc)


def _edge_key(a, b):
    return (a, b) if a < b else (b, a)


def _face_area_normal(positions, face):
    """Newell normal scaled by area (unnormalized)."""
    nx = ny = nz = 0.0
    count = len(face)
    for i in range(count):
        cx, cy, cz = positions[face[i]]
        nx_, ny_, nz_ = positions[face[(i + 1) % count]]
        nx += (cy - ny_) * (cz + nz_)
        ny += (cz - nz_) * (cx + nx_)
        nz += (cx - nx_) * (cy + ny_)
    return (nx * 0.5, ny * 0.5, nz * 0.5)


# ---------------------------------------------------------------------------
# Per-vertex constraint shapes
# ---------------------------------------------------------------------------

class _FreeConstraint:
    def project(self, target):
        return target


class EdgeRails:
    """Slide a vertex along its edges, 3ds Max style.

    The displacement picks the incident edge it is most aligned with (largest
    positive dot), the vertex moves by the projected length, and if that runs
    past the edge's far vertex the leftover keeps going along the next edge -
    but only one that roughly continues the path (within ``turn_limit``), so
    a loop slides along a bent column of edges but stops at a cube corner
    instead of wrapping onto the cap.
    """

    def __init__(self, mesh, v, *, reach=DEFAULT_REACH, stop_at_selected=True,
                 turn_limit_cos=TURN_LIMIT_COS):
        self.mesh = mesh
        self.v = v
        self.origin = mesh.positions[v]
        self.reach = reach
        self.stop_at_selected = stop_at_selected
        self.turn_limit_cos = turn_limit_cos

    def _edges_from(self, u, came_from):
        """Yield (other, unit_dir, length, prefers) for u's edges."""
        pos = self.mesh.positions
        for ei in self.mesh.vert_edges[u]:
            w = self.mesh.other(ei, u)
            if w == came_from:
                continue
            d = vec.sub(pos[w], pos[u])
            ln = vec.length(d)
            if ln < 1e-12:
                continue
            # Edges that leave the selection are the "real" rails; edges
            # inside it only win when they are clearly better aligned.
            leaves = not self.mesh.edge_fully_selected(ei)
            yield w, vec.mul(d, 1.0 / ln), ln, leaves

    def project(self, target):
        mesh = self.mesh
        remaining = vec.sub(target, self.origin)
        if vec.length_sq(remaining) < 1e-24:
            return self.origin
        pos = self.origin
        u, came_from, prev_dir = self.v, None, None
        for _step in range(max(1, self.reach)):
            best = None
            best_score = 1e-9
            for w, t, ln, leaves in self._edges_from(u, came_from):
                if prev_dir is not None and vec.dot(t, prev_dir) < self.turn_limit_cos:
                    continue
                s = vec.dot(remaining, t)
                score = s * (1.0 if leaves else IN_SELECTION_BIAS)
                if score > best_score + 1e-12:
                    best_score, best = score, (w, t, ln, s)
            if best is None:
                break
            w, t, ln, s = best
            if s <= ln:
                return vec.add(pos, vec.mul(t, s))
            # Ran past the far vertex: land on it, consume, keep walking.
            pos = mesh.positions[w]
            remaining = vec.sub(remaining, vec.mul(t, ln))
            if self.stop_at_selected and w in mesh.selected:
                break
            came_from, u, prev_dir = u, w, t
        return pos


class FacePatch:
    """A set of triangles; project() returns the closest point on the patch."""

    def __init__(self, origin, triangles):
        self.origin = origin
        self.triangles = triangles

    def project(self, target):
        if not self.triangles:
            return self.origin
        best = self.origin
        best_d = vec.dist_sq(target, best)
        for a, b, c in self.triangles:
            q = vec.closest_point_on_triangle(target, a, b, c)
            d = vec.dist_sq(target, q)
            if d < best_d - 1e-15:
                best, best_d = q, d
        return best


class NormalLine:
    def __init__(self, origin, normal):
        self.origin = origin
        self.normal = normal

    def project(self, target):
        if vec.length_sq(self.normal) < 1e-20:
            return self.origin
        t = vec.dot(vec.sub(target, self.origin), self.normal)
        return vec.add(self.origin, vec.mul(self.normal, t))


# ---------------------------------------------------------------------------
# Builders
# ---------------------------------------------------------------------------

def edge_rails_for(mesh, v, *, reach=DEFAULT_REACH, stop_at_selected=True):
    return EdgeRails(mesh, v, reach=reach, stop_at_selected=stop_at_selected)


def _triangulate(positions, face):
    p0 = positions[face[0]]
    return [(p0, positions[face[i]], positions[face[i + 1]])
            for i in range(1, len(face) - 1)]


def face_patch_for(mesh, v, *, reach=DEFAULT_REACH, stop_at_selected=True):
    """Collect the surface triangles vertex v may slide over."""
    start = [fi for fi in mesh.vert_faces[v] if not mesh.face_fully_selected(fi)]
    fallback = not start
    if fallback:
        start = list(mesh.vert_faces[v])

    seen = set(start)
    frontier = list(start)
    depth = 1
    while frontier and depth < reach:
        nxt = []
        for fi in frontier:
            f = mesh.faces[fi]
            for i, a in enumerate(f):
                b = f[(i + 1) % len(f)]
                if stop_at_selected and (a in mesh.selected and b in mesh.selected):
                    # Don't grow across a selected edge; another selected
                    # vertex owns the surface on the far side.
                    if v not in (a, b):
                        continue
                for nf in mesh.edge_faces.get(_edge_key(a, b), ()):
                    if nf in seen:
                        continue
                    if not fallback and mesh.face_fully_selected(nf):
                        continue
                    seen.add(nf)
                    nxt.append(nf)
        frontier = nxt
        depth += 1

    tris = []
    for fi in seen:
        tris.extend(_triangulate(mesh.positions, mesh.faces[fi]))
    return FacePatch(mesh.positions[v], tris)


def build_constraints(mesh, mode, *, reach=DEFAULT_REACH, stop_at_selected=True):
    """Return {vert_index: constraint} for every selected vertex."""
    out = {}
    for v in mesh.selected:
        if mode == MODE_EDGE:
            out[v] = edge_rails_for(mesh, v, reach=reach,
                                    stop_at_selected=stop_at_selected)
        elif mode == MODE_FACE:
            out[v] = face_patch_for(mesh, v, reach=reach,
                                    stop_at_selected=stop_at_selected)
        elif mode == MODE_NORMAL:
            out[v] = NormalLine(mesh.positions[v], mesh.vertex_normal(v))
        else:
            out[v] = _FreeConstraint()
    return out


def solve(constraints, targets):
    """Project free targets {v: point} through constraints -> {v: point}."""
    return {v: constraints[v].project(t) if v in constraints else t
            for v, t in targets.items()}
