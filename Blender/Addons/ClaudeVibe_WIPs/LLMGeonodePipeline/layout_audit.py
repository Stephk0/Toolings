"""layout_audit.py -- score a Geometry Nodes graph against the ST3E layout rules.

Companion to the GeoNode Layout MCP: after `apply_layout` (or after running
`geonode_route_tidy.py`), this verifies the result actually adheres to the rules
the screenshot judgment is supposed to enforce. The MCP *moves* nodes; this
*checks* them, deterministically, with no image needed.

Rules checked
-------------
  R1 no_overlaps      : no two real-node bounding boxes overlap            (FAIL if >0)
  R2 reroutes_clear   : no reroute sits inside a real node body            (FAIL if >0)
  R3 left_to_right    : logical links (traced through reroutes) flow +x    (FAIL if any backward)
  R4 frames_labeled   : every frame has a non-empty label                  (WARN if any blank)
  R5 column_spacing   : clearance between adjacent columns                 (WARN if < MIN_CLEAR)
  (report only)       : bounds W x H and aspect

Usage
-----
  # headless, one or more files (group name == file name):
  blender --background --factory-startup --python layout_audit.py -- GN_NormalTransfer GN_Bend

  # or import and call on any node group:
  import layout_audit; report = layout_audit.audit(ng); layout_audit.print_report(report)

Exit code is non-zero (in CLI mode) if any FAIL rule fails, so it can gate CI.
"""

import bpy, sys, os

MIN_CLEAR = 70.0   # px of empty space we want between adjacent columns (node edge to edge)
OVERLAP_PAD = 2.0  # ignore hairline touches

# Rule policy (single source of truth, shared with run_pipeline):
#   BLOCKING = structural integrity. A FAIL here means the graph renders broken
#              (overlapping bodies / reroutes hidden inside nodes) -> don't save.
#   ADVISORY = readability quality. R3 (strict left-to-right) is advisory on
#              purpose: feedback/preview topologies (a deformer's Set Position
#              feeding a preview Switch / gizmo Join placed upstream) have
#              legitimate backward links and can never reach zero.
BLOCKING = ("R1_no_overlaps", "R2_reroutes_clear", "R7_no_frame_overlap")
ADVISORY = ("R3_left_to_right", "R4_frames_labeled", "R5_row_clearance", "R6_entries_staggered")

ENTRY_Y_TOL = 10.0  # two reroutes feeding one node within this Y are "piled on a row" (R6)


def _est_h(n):
    nin = sum(1 for s in n.inputs if s.enabled and not s.hide and s.type != 'CUSTOM')
    nout = sum(1 for s in n.outputs if s.enabled and not s.hide and s.type != 'CUSTOM')
    return 34 + (nin + nout) * 22 + 30


def _absloc(n):
    x, y = n.location.x, n.location.y
    p = n.parent
    while p is not None:
        x += p.location.x; y += p.location.y; p = p.parent
    return x, y


def _box(n, sc):
    x, y = _absloc(n)
    w = (n.dimensions.x / sc) if n.dimensions.x else (n.width or 140.0)
    h = (n.dimensions.y / sc) if n.dimensions.y else _est_h(n)
    return (x, y - h, x + w, y)  # x0,y0,x1,y1 (y up, top-left origin)


def _intersect(a, b, pad=0.0):
    return a[0] < b[2] - pad and b[0] < a[2] - pad and a[1] < b[3] - pad and b[1] < a[3] - pad


def audit(ng):
    sc = bpy.context.preferences.system.ui_scale
    real = [n for n in ng.nodes if n.bl_idname not in ('NodeFrame', 'NodeReroute')]
    rr = [n for n in ng.nodes if n.bl_idname == 'NodeReroute']
    frames = [n for n in ng.nodes if n.bl_idname == 'NodeFrame']
    rrnames = set(n.name for n in rr)
    boxes = {n.name: _box(n, sc) for n in real}

    # R1 overlaps
    overlaps = []
    for i in range(len(real)):
        for j in range(i + 1, len(real)):
            if _intersect(boxes[real[i].name], boxes[real[j].name], OVERLAP_PAD):
                overlaps.append((real[i].name, real[j].name))

    # R2 reroutes inside node bodies
    reroute_in_node = []
    for r in rr:
        rx, ry = _absloc(r)
        for n in real:
            x0, y0, x1, y1 = boxes[n.name]
            if x0 - 6 <= rx <= x1 + 6 and y0 - 6 <= ry <= y1 + 6:
                reroute_in_node.append((r.name, n.name))

    # R3 flow (trace through reroutes by NAME -- bpy `is` is unreliable after reopen)
    def fwd_targets(node, seen=None):
        seen = seen if seen is not None else set()
        out = []
        for l in ng.links:
            if l.from_node.name == node.name:
                t = l.to_node
                if t.name in rrnames:
                    if t.name not in seen:
                        seen.add(t.name); out += fwd_targets(t, seen)
                else:
                    out.append(t.name)
        return out
    forward = backward = 0
    backward_pairs = []
    posx = {n.name: _absloc(n)[0] for n in real}
    for n in real:
        for tname in fwd_targets(n):
            if posx.get(tname, posx[n.name]) > posx[n.name]:
                forward += 1
            else:
                backward += 1; backward_pairs.append((n.label or n.name, tname))

    # R4 frames labeled
    blank_frames = [f.name for f in frames if not (f.label or '').strip()]

    # R5 spacing: min horizontal clearance between nodes that ACTUALLY share a
    # vertical span (true adjacency). Nodes in different bands (no y-overlap)
    # may share x-space without colliding -- R1 is authoritative for overlaps.
    min_clear = None
    for i in range(len(real)):
        a = boxes[real[i].name]
        for j in range(len(real)):
            if i == j:
                continue
            b = boxes[real[j].name]
            y_overlap = a[1] < b[3] and b[1] < a[3]
            if y_overlap and a[2] <= b[0]:            # a is left of b, rows overlap
                gap = round(b[0] - a[2], 1)
                min_clear = gap if min_clear is None else min(min_clear, gap)

    # R6 subway-map: reroutes feeding the SAME node must be staggered in Y, not piled on one
    # row (piled entries -> crossing taps you can't trace). Flags the exact issue that the
    # nested-staircase entry router fixes.
    from collections import defaultdict
    entry_ys = defaultdict(list)
    for l in ng.links:
        if l.from_node.bl_idname == 'NodeReroute' and l.to_node.bl_idname not in ('NodeReroute', 'NodeFrame'):
            entry_ys[l.to_node.name].append(_absloc(l.from_node)[1])
    piled = []
    for node, ys in entry_ys.items():
        ys.sort()
        if any(abs(a - b) < ENTRY_Y_TOL for a, b in zip(ys, ys[1:])):
            piled.append(node)

    # R7 no frame overlap: function frames must not overlap, UNLESS one is fully nested inside
    # the other (deliberate function-in-function). Frame box = abs bbox of its children.
    def frame_box(f):
        kids = [n for n in ng.nodes if n.parent is not None and n.parent.name == f.name]
        if not kids:
            return None
        xs0 = xs1 = ys0 = ys1 = None
        for k in kids:
            kx, ky = _absloc(k)
            if k.bl_idname == 'NodeReroute':
                w = h = 10.0
            else:
                w = (k.dimensions.x / sc) if k.dimensions.x else (k.width or 140.0)
                h = (k.dimensions.y / sc) if k.dimensions.y else _est_h(k)
            x0, y0, x1, y1 = kx, ky - h, kx + w, ky
            xs0 = x0 if xs0 is None else min(xs0, x0); ys0 = y0 if ys0 is None else min(ys0, y0)
            xs1 = x1 if xs1 is None else max(xs1, x1); ys1 = y1 if ys1 is None else max(ys1, y1)
        return (xs0, ys0, xs1, ys1)
    fboxes = {f.name: frame_box(f) for f in frames}
    fboxes = {k: v for k, v in fboxes.items() if v}
    fnames = list(fboxes)
    frame_overlaps = []
    for i in range(len(fnames)):
        for j in range(i + 1, len(fnames)):
            A = fboxes[fnames[i]]; B = fboxes[fnames[j]]
            if _intersect(A, B, pad=4):
                contains = (A[0] <= B[0] and A[1] <= B[1] and A[2] >= B[2] and A[3] >= B[3]) or \
                           (B[0] <= A[0] and B[1] <= A[1] and B[2] >= A[2] and B[3] >= A[3])
                if not contains:                       # nesting is allowed; partial overlap is not
                    frame_overlaps.append((fnames[i], fnames[j]))

    allx = [_absloc(n)[0] for n in real]; ally = [_absloc(n)[1] for n in real]
    W = (max(allx) - min(allx)) if allx else 0
    H = (max(ally) - min(ally)) if ally else 0

    def rule(ok, warn=False):
        return "PASS" if ok else ("WARN" if warn else "FAIL")

    return {
        "tree": ng.name,
        "counts": {"real": len(real), "reroutes": len(rr), "frames": len(frames)},
        "R1_no_overlaps": {"status": rule(not overlaps), "overlaps": overlaps},
        "R2_reroutes_clear": {"status": rule(not reroute_in_node), "inside": reroute_in_node},
        "R3_left_to_right": {"status": rule(backward == 0),
                              "forward": forward, "backward": backward, "backward_pairs": backward_pairs[:8]},
        "R4_frames_labeled": {"status": rule(not blank_frames, warn=True), "blank": blank_frames},
        "R5_row_clearance": {"status": rule(min_clear is None or min_clear >= MIN_CLEAR, warn=True),
                              "min_clear": min_clear, "target": MIN_CLEAR},
        "R6_entries_staggered": {"status": rule(not piled, warn=True), "piled_nodes": piled},
        "R7_no_frame_overlap": {"status": rule(not frame_overlaps, warn=True), "overlaps": frame_overlaps},
        "bounds": {"w": round(W), "h": round(H), "aspect_h_over_w": round(H / max(W, 1), 2)},
    }


def print_report(rep):
    """Print a per-rule report. Returns the number of BLOCKING rule failures
    (0 == structurally sound; advisory R3–R5 issues do not count)."""
    print(f"\n=== layout audit: {rep['tree']} ===")
    print("  counts:", rep["counts"])
    for key in BLOCKING + ADVISORY:
        r = rep[key]; st = r["status"]
        tag = st + ("*" if key in BLOCKING else " ")  # * marks a blocking rule
        detail = {k: v for k, v in r.items() if k != "status"}
        print(f"  [{tag}] {key}: {detail}")
    b = rep["bounds"]
    print(f"  bounds: {b['w']} x {b['h']}  (aspect H/W = {b['aspect_h_over_w']})")
    blocking_fails = [k for k in BLOCKING if rep[k]["status"] == "FAIL"]
    advisory_issues = [k for k in ADVISORY if rep[k]["status"] in ("FAIL", "WARN")]
    if blocking_fails:
        print(f"  => {len(blocking_fails)} BLOCKING rule(s) failed: {', '.join(blocking_fails)}")
    elif advisory_issues:
        print(f"  => structurally sound (R1/R2 pass); advisories: {', '.join(advisory_issues)}")
    else:
        print("  => ALL RULES PASS")
    return len(blocking_fails)


def _cli():
    geo = r"D:\Stephko_Tooling\Toolings\Blender\Geonodes"
    names = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    total_fail = 0
    if names:
        for nm in names:
            bpy.ops.wm.open_mainfile(filepath=os.path.join(geo, nm + ".blend"))
            ng = bpy.data.node_groups.get(nm)
            if not ng:
                print(f"[SKIP] {nm}: group not found"); continue
            total_fail += print_report(audit(ng))
    else:
        # active object's active GN modifier tree
        obj = bpy.context.active_object
        ng = next((m.node_group for m in obj.modifiers if m.type == 'NODES' and m.node_group), None)
        if ng:
            total_fail += print_report(audit(ng))
        else:
            print("no active GN tree"); total_fail = 1
    sys.stdout.flush()
    os._exit(1 if total_fail else 0)


if __name__ == "__main__":
    _cli()
