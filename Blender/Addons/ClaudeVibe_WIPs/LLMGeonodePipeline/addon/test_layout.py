"""Headless tests for the deterministic layout engine (no bpy needed).

Run:  python -m pytest test_layout.py   (or just: python test_layout.py)
"""

import layout


def _grid(n, w=140.0, h=100.0):
    return {i: {"w": w, "h": h} for i in range(n)}


def test_left_to_right_flow():
    nodes = _grid(4)
    links = [(0, 1), (1, 2), (2, 3)]  # straight chain
    m = layout.compute_layout(nodes, links)
    xs = [m[i][0] for i in range(4)]
    assert xs == sorted(xs) and len(set(xs)) == 4  # strictly increasing columns


def test_no_overlaps_with_duplicates_and_disconnected():
    nodes = _grid(7)
    # three nodes (3,4,5) all feed node 2 -> stacked; node 6 disconnected
    links = [(0, 1), (1, 2), (3, 2), (4, 2), (5, 2)]
    m = layout.compute_layout(nodes, links)
    assert not layout.has_overlaps(nodes, m)


def test_deterministic():
    nodes = _grid(5)
    links = [(0, 2), (1, 2), (2, 3), (2, 4)]
    a = layout.compute_layout(nodes, links)
    b = layout.compute_layout(nodes, links)
    assert a == b


def test_empty():
    assert layout.compute_layout({}, []) == {}


def test_predecessor_left_of_successor():
    nodes = _grid(3)
    links = [(0, 2), (1, 2)]
    m = layout.compute_layout(nodes, links)
    assert m[0][0] < m[2][0] and m[1][0] < m[2][0]


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for fn in fns:
        fn()
        print(f"ok  {fn.__name__}")
    print(f"\n{len(fns)} passed")
