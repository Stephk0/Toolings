"""Plain-data test meshes."""


def edges_from_faces(faces):
    seen = set()
    out = []
    for f in faces:
        for i, a in enumerate(f):
            b = f[(i + 1) % len(f)]
            key = (min(a, b), max(a, b))
            if key not in seen:
                seen.add(key)
                out.append(key)
    return out


def cube_with_cuts(axis_values, axis=2):
    """2x2x2 cube (from -1..1) sliced by loops at the given coordinates along
    `axis`. Returns (positions, edges, faces, rings) where rings[i] holds the
    4 vertex indices of the i-th slice (slice 0 = -1, last = +1)."""
    levels = [-1.0] + sorted(axis_values) + [1.0]
    corners = [(1, 1), (-1, 1), (-1, -1), (1, -1)]   # CCW around the axis
    other = [i for i in range(3) if i != axis]
    positions, rings = [], []
    for lv in levels:
        ring = []
        for a, b in corners:
            p = [0.0, 0.0, 0.0]
            p[axis] = lv
            p[other[0]] = float(a)
            p[other[1]] = float(b)
            ring.append(len(positions))
            positions.append(tuple(p))
        rings.append(ring)
    faces = [tuple(reversed(rings[0])), tuple(rings[-1])]
    for r0, r1 in zip(rings, rings[1:]):
        for i in range(4):
            j = (i + 1) % 4
            faces.append((r0[i], r0[j], r1[j], r1[i]))
    return positions, edges_from_faces(faces), faces, rings


def on_cube_surface(p, tol=1e-6):
    inside = all(abs(c) <= 1.0 + tol for c in p)
    on_face = any(abs(abs(c) - 1.0) <= tol for c in p)
    return inside and on_face
