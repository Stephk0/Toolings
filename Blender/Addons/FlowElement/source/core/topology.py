"""Local mesh adjacency: neighbours, ordered vertex fans, edge continuation.

Works on a plain-data mesh fragment: ``faces`` as vertex-index lists (consistent winding),
``edges`` as index pairs, ``positions`` as ``{index: (x, y, z)}``. Only the fans of vertices
whose faces are *all* present are meaningful — callers pass the faces around every vertex
they ask about.
"""

from . import vec

# A continuation edge must keep going roughly the same way (cos 70°).
CONTINUE_MIN_DOT = 0.34
# Two edges count as "opposite" through a vertex when they are at least ~105° apart.
OPPOSITE_MAX_DOT = -0.25


def edge_key(a, b):
    return (a, b) if a < b else (b, a)


class Topology:
    """Lazy, cached adjacency over any mesh source.

    ``corner_links(v)`` returns ``[(prev, next), ...]`` — the neighbours before and after ``v``
    in each face around it; ``neighbors(v)`` returns every vertex sharing an edge with ``v``.
    """

    def __init__(self, corner_links, neighbors):
        self._corner_links_fn = corner_links
        self._neighbors_fn = neighbors
        self._links = {}
        self._nbs = {}
        self._fans = {}

    @classmethod
    def from_faces(cls, faces, edges=()):
        links, nbs = {}, {}
        for face in faces:
            n = len(face)
            for i, v in enumerate(face):
                a, b = face[i - 1], face[(i + 1) % n]
                links.setdefault(v, []).append((a, b))
                nbs.setdefault(v, set()).update((a, b))
        for a, b in edges:
            nbs.setdefault(a, set()).add(b)
            nbs.setdefault(b, set()).add(a)
        return cls(lambda v: links.get(v, []), lambda v: nbs.get(v, set()))

    def corner_links(self, v):
        if v not in self._links:
            self._links[v] = list(self._corner_links_fn(v))
        return self._links[v]

    def neighbors(self, v):
        if v not in self._nbs:
            self._nbs[v] = set(self._neighbors_fn(v))
        return self._nbs[v]

    def fan(self, v):
        """Ordered neighbours around ``v`` and whether the fan closes.

        Returns ``(ring, closed)`` or ``None`` when the vertex is non-manifold, has wire
        edges, or the winding is inconsistent — callers then fall back to geometry.
        """
        if v in self._fans:
            return self._fans[v]
        result = self._build_fan(v)
        self._fans[v] = result
        return result

    def _build_fan(self, v):
        links = self.corner_links(v)
        if not links:
            return None
        nxt = {}
        prevs = set()
        for a, b in links:
            if a in nxt:  # same neighbour starts two corners: non-manifold or flipped
                return None
            nxt[a] = b
            prevs.add(a)
        starts = [a for a in prevs if a not in set(nxt.values())]
        if len(starts) > 1:
            return None
        closed = not starts
        start = starts[0] if starts else links[0][0]
        ring = [start]
        cur = start
        while cur in nxt:
            cur = nxt[cur]
            if cur == start:
                break
            ring.append(cur)
            if len(ring) > len(links) + 1:
                return None
        if set(ring) != self.neighbors(v):
            return None  # wire edges or a second, disconnected fan
        if closed and len(ring) != len(links):
            return None
        return ring, closed


def continuation(topo, positions, n, came_from):
    """The vertex that continues the line ``came_from -> n`` one edge further.

    Regular interior vertex with even valence: the topologically opposite neighbour.
    Otherwise the neighbour best aligned with the incoming direction, if close enough.
    """
    fan = topo.fan(n)
    if fan is not None:
        ring, closed = fan
        if closed and len(ring) % 2 == 0 and came_from in ring:
            i = ring.index(came_from)
            return ring[(i + len(ring) // 2) % len(ring)]

    direction = vec.normalized(vec.sub(positions[n], positions[came_from]))
    best, best_dot = None, CONTINUE_MIN_DOT
    for m in topo.neighbors(n):
        if m == came_from or m not in positions:
            continue
        d = vec.dot(vec.normalized(vec.sub(positions[m], positions[n])), direction)
        if d > best_dot:
            best, best_dot = m, d
    return best


def opposite_pairs(topo, positions, v, excluded_edges=frozenset()):
    """Pairs of neighbours ``(a, b)`` whose edges form a straight-through line at ``v``.

    Edges in ``excluded_edges`` (keys from :func:`edge_key`) are not used — in edge mode
    those are the selected loop edges, leaving the crossing ring.
    """
    def usable(n):
        return edge_key(v, n) not in excluded_edges

    fan = topo.fan(v)
    if fan is not None:
        ring, closed = fan
        if closed and len(ring) % 2 == 0:
            half = len(ring) // 2
            return [
                (ring[i], ring[i + half])
                for i in range(half)
                if usable(ring[i]) and usable(ring[i + half])
            ]

    nbs = [n for n in topo.neighbors(v) if usable(n) and n in positions]
    dirs = {n: vec.normalized(vec.sub(positions[n], positions[v])) for n in nbs}
    pairs = set()
    for a in nbs:
        best, best_dot = None, OPPOSITE_MAX_DOT
        for b in nbs:
            if b == a:
                continue
            d = vec.dot(dirs[a], dirs[b])
            if d < best_dot:
                best, best_dot = b, d
        if best is not None:
            pairs.add(edge_key(a, best))
    return sorted(pairs)
