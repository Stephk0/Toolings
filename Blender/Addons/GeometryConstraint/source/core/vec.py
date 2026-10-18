"""Tiny tuple-based 3D vector helpers.

core/ must stay importable in plain CPython (no bpy, no mathutils), so the
solver works on 3-tuples of floats.
"""

import math

EPS = 1e-12


def add(a, b):
    return (a[0] + b[0], a[1] + b[1], a[2] + b[2])


def sub(a, b):
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def mul(a, s):
    return (a[0] * s, a[1] * s, a[2] * s)


def dot(a, b):
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def cross(a, b):
    return (
        a[1] * b[2] - a[2] * b[1],
        a[2] * b[0] - a[0] * b[2],
        a[0] * b[1] - a[1] * b[0],
    )


def length_sq(a):
    return dot(a, a)


def length(a):
    return math.sqrt(dot(a, a))


def dist_sq(a, b):
    return length_sq(sub(a, b))


def normalized(a):
    n = length(a)
    if n < EPS:
        return (0.0, 0.0, 0.0)
    return (a[0] / n, a[1] / n, a[2] / n)


def lerp(a, b, t):
    return (a[0] + (b[0] - a[0]) * t,
            a[1] + (b[1] - a[1]) * t,
            a[2] + (b[2] - a[2]) * t)


def mean(points):
    n = len(points)
    if not n:
        return (0.0, 0.0, 0.0)
    sx = sy = sz = 0.0
    for p in points:
        sx += p[0]
        sy += p[1]
        sz += p[2]
    return (sx / n, sy / n, sz / n)


def bounds_center(points):
    if not points:
        return (0.0, 0.0, 0.0)
    xs, ys, zs = zip(*points)
    return ((min(xs) + max(xs)) * 0.5,
            (min(ys) + max(ys)) * 0.5,
            (min(zs) + max(zs)) * 0.5)


def rotate_about_axis(p, axis, angle):
    """Rodrigues rotation of vector p about unit axis by angle (radians)."""
    k = normalized(axis)
    c = math.cos(angle)
    s = math.sin(angle)
    kxp = cross(k, p)
    kdp = dot(k, p)
    return (
        p[0] * c + kxp[0] * s + k[0] * kdp * (1.0 - c),
        p[1] * c + kxp[1] * s + k[1] * kdp * (1.0 - c),
        p[2] * c + kxp[2] * s + k[2] * kdp * (1.0 - c),
    )


def closest_point_on_segment(p, a, b):
    ab = sub(b, a)
    denom = length_sq(ab)
    if denom < EPS:
        return a
    t = dot(sub(p, a), ab) / denom
    if t <= 0.0:
        return a
    if t >= 1.0:
        return b
    return add(a, mul(ab, t))


def closest_point_on_triangle(p, a, b, c):
    """Closest point to p on triangle abc (Ericson, Real-Time Collision Detection 5.1.5)."""
    ab = sub(b, a)
    ac = sub(c, a)
    ap = sub(p, a)
    d1 = dot(ab, ap)
    d2 = dot(ac, ap)
    if d1 <= 0.0 and d2 <= 0.0:
        return a

    bp = sub(p, b)
    d3 = dot(ab, bp)
    d4 = dot(ac, bp)
    if d3 >= 0.0 and d4 <= d3:
        return b

    vc = d1 * d4 - d3 * d2
    if vc <= 0.0 and d1 >= 0.0 and d3 <= 0.0:
        v = d1 / (d1 - d3)
        return add(a, mul(ab, v))

    cp = sub(p, c)
    d5 = dot(ab, cp)
    d6 = dot(ac, cp)
    if d6 >= 0.0 and d5 <= d6:
        return c

    vb = d5 * d2 - d1 * d6
    if vb <= 0.0 and d2 >= 0.0 and d6 <= 0.0:
        w = d2 / (d2 - d6)
        return add(a, mul(ac, w))

    va = d3 * d6 - d5 * d4
    if va <= 0.0 and (d4 - d3) >= 0.0 and (d5 - d6) >= 0.0:
        w = (d4 - d3) / ((d4 - d3) + (d5 - d6))
        return add(b, mul(sub(c, b), w))

    denom = va + vb + vc
    if abs(denom) < EPS:
        # Degenerate triangle: fall back to its longest edge.
        return min(
            (closest_point_on_segment(p, a, b),
             closest_point_on_segment(p, b, c),
             closest_point_on_segment(p, c, a)),
            key=lambda q: dist_sq(p, q),
        )
    inv = 1.0 / denom
    v = vb * inv
    w = vc * inv
    return add(a, add(mul(ab, v), mul(ac, w)))
