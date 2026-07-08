"""Deterministic layered (Sugiyama-style) layout for Geometry Nodes graphs.

Pure stdlib -- no ``bpy`` import here so it can be unit-tested headlessly.
All coordinates are in *node space* (the same space as ``node.location``),
with +x pointing right and +y pointing up.  ``node.location`` is the
**top-left** corner of a node, so a node occupies::

    [x, x + w]  x  [y - h, y]

The algorithm:

1. Longest-path layering assigns every node a layer (column) so that every
   link points from a lower layer to a higher one -> strict left-to-right flow.
2. One barycenter sweep orders nodes within each column to reduce crossings.
   Ties break on the original index, so the result is fully deterministic.
3. Columns are spaced by the widest node in the previous column + ``x_gap``.
4. Within a column, nodes are stacked top-to-bottom using their real heights
   + ``y_gap`` so bounding boxes never overlap.

``compute_layout`` returns ``{index: (x, y)}`` -- the new top-left corner of
every laid-out node.  Frame nodes are *not* passed in (they shrink-wrap their
children automatically), so the caller filters them out first.
"""

from __future__ import annotations


def _layer_assignment(ids, edges):
    """Longest-path layering. Returns ``{id: layer_int}`` and the pred map.

    Robust against the (illegal for GN, but cheap to guard) possibility of a
    cycle: the relaxation loop is capped at ``len(ids)`` passes.
    """
    pred = {n: [] for n in ids}
    for s, d in edges:
        if s in pred and d in pred and s != d:
            pred[d].append(s)

    layer = {n: 0 for n in ids}
    # Relax: layer[d] = max(layer[s] + 1).  A DAG converges in <= depth passes.
    for _ in range(len(ids) + 1):
        changed = False
        for s, d in edges:
            if s in layer and d in layer and s != d:
                want = layer[s] + 1
                if layer[d] < want:
                    layer[d] = want
                    changed = True
        if not changed:
            break
    return layer, pred


def compute_layout(nodes, links, x_gap=80.0, y_gap=40.0, origin=(0.0, 0.0)):
    """Compute a clean left-to-right layout.

    Parameters
    ----------
    nodes : dict[int, dict]
        ``{index: {"w": float, "h": float}}`` for every node to place.
        Frame nodes must already be excluded.
    links : list[tuple[int, int]]
        ``(from_index, to_index)`` pairs.  Indices not present in ``nodes``
        (e.g. links to a frame) are ignored.
    x_gap, y_gap : float
        Spacing between columns / stacked nodes, in node-space units.
    origin : (float, float)
        Top-left anchor of the whole layout (first column, first row).

    Returns
    -------
    dict[int, tuple[float, float]]
        ``{index: (x, y)}`` new top-left position per node.
    """
    ids = list(nodes.keys())
    if not ids:
        return {}

    edges = [(int(a), int(b)) for (a, b) in links if int(a) in nodes and int(b) in nodes]
    layer, pred = _layer_assignment(ids, edges)

    max_layer = max(layer.values())
    columns = {}
    for n in ids:
        columns.setdefault(layer[n], []).append(n)

    # Deterministic seed order, then one left-to-right barycenter sweep.
    pos_in_col = {}
    for L in range(max_layer + 1):
        col = columns.get(L, [])
        if L == 0:
            col.sort()  # stable seed by original index
        else:
            def barycenter(n):
                ps = [pos_in_col[p] for p in pred[n] if p in pos_in_col]
                return sum(ps) / len(ps) if ps else 0.0
            col.sort(key=lambda n: (barycenter(n), n))
        for i, n in enumerate(col):
            pos_in_col[n] = i
        columns[L] = col

    # X per column: cumulative width of preceding columns + gaps.
    col_width = {
        L: max((nodes[n]["w"] for n in columns.get(L, [])), default=0.0)
        for L in range(max_layer + 1)
    }
    col_x = {}
    x = float(origin[0])
    for L in range(max_layer + 1):
        col_x[L] = x
        x += col_width[L] + x_gap

    # Y within a column: stack downward (y decreases) using real heights.
    moves = {}
    for L in range(max_layer + 1):
        y = float(origin[1])
        for n in columns.get(L, []):
            moves[n] = (col_x[L], y)
            y -= nodes[n]["h"] + y_gap

    return moves


def has_overlaps(nodes, placement):
    """Test helper: True if any two placed bounding boxes overlap.

    ``nodes`` -> ``{index: {"w","h"}}``; ``placement`` -> ``{index: (x, y)}``.
    """
    boxes = []
    for idx, (x, y) in placement.items():
        w = nodes[idx]["w"]
        h = nodes[idx]["h"]
        boxes.append((x, y - h, x + w, y))  # (xmin, ymin, xmax, ymax)
    for i in range(len(boxes)):
        for j in range(i + 1, len(boxes)):
            ax0, ay0, ax1, ay1 = boxes[i]
            bx0, by0, bx1, by1 = boxes[j]
            if ax0 < bx1 and bx0 < ax1 and ay0 < by1 and by0 < ay1:
                return True
    return False
