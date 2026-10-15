"""Free (unconstrained) transform math on plain points (bpy-free).

These produce the per-vertex *targets* that the constraint solver then snaps
back onto the mesh. ``basis`` is an orthonormal orientation given as three
world-space axis tuples (X, Y, Z) — e.g. Global, Local or View.
"""

from . import vec

PIVOT_MEDIAN = 'MEDIAN_POINT'
PIVOT_BOUNDS = 'BOUNDING_BOX_CENTER'
PIVOT_CURSOR = 'CURSOR'
PIVOT_ACTIVE = 'ACTIVE_ELEMENT'
PIVOT_INDIVIDUAL = 'INDIVIDUAL_ORIGINS'

IDENTITY_BASIS = ((1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0))


def pivot_point(points, mode, *, cursor=None, active=None):
    """Pick the transform center. INDIVIDUAL_ORIGINS falls back to median."""
    if mode == PIVOT_BOUNDS:
        return vec.bounds_center(points)
    if mode == PIVOT_CURSOR and cursor is not None:
        return tuple(cursor)
    if mode == PIVOT_ACTIVE and active is not None:
        return tuple(active)
    return vec.mean(points)


def _to_basis(d, basis):
    return (vec.dot(d, basis[0]), vec.dot(d, basis[1]), vec.dot(d, basis[2]))


def _from_basis(c, basis):
    return vec.add(vec.add(vec.mul(basis[0], c[0]), vec.mul(basis[1], c[1])),
                   vec.mul(basis[2], c[2]))


def mask_vector(d, axes, basis=IDENTITY_BASIS):
    """Keep only the components of d along the enabled basis axes."""
    c = _to_basis(d, basis)
    c = tuple(c[i] if axes[i] else 0.0 for i in range(3))
    return _from_basis(c, basis)


def translate(points, offset):
    return {k: vec.add(p, offset) for k, p in points.items()}


def rotate(points, pivot, axis, angle):
    out = {}
    for k, p in points.items():
        out[k] = vec.add(pivot, vec.rotate_about_axis(vec.sub(p, pivot), axis, angle))
    return out


def scale(points, pivot, factors, basis=IDENTITY_BASIS):
    """Non-uniform scale about pivot; factors are per basis axis."""
    out = {}
    for k, p in points.items():
        c = _to_basis(vec.sub(p, pivot), basis)
        c = (c[0] * factors[0], c[1] * factors[1], c[2] * factors[2])
        out[k] = vec.add(pivot, _from_basis(c, basis))
    return out
