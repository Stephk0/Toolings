import bpy, sys, os
from collections import defaultdict
GEO = r"D:\Stephko_Tooling\Toolings\Blender\Geonodes"
TARGETS = ["GN_Spherify", "GN_Twist", "GN_Taper", "GN_Wave", "GN_Bend", "GN_Stretch",
           "GN_Inflate", "GN_Smooth", "GN_RandomizePosition",
           "GN_Triangulate", "GN_Subdivide", "GN_Wireframe", "GN_RadialArray",
           "GN_Displace", "GN_MeshBoolean", "GN_Cast", "GN_Scatter"]

def isock(node, ident): return next(s for s in node.inputs if s.identifier == ident)
def osock(node, ident): return next(s for s in node.outputs if s.identifier == ident)
def fname_of(n): return n.parent.name if n.parent else None   # frame identity by NAME (bpy wrappers fail `is`)
def est_h(n):
    nin = sum(1 for s in n.inputs if s.enabled and not s.hide and s.type != 'CUSTOM')
    nout = sum(1 for s in n.outputs if s.enabled and not s.hide and s.type != 'CUSTOM')
    return 34 + (nin + nout) * 22 + 30

def tidy_layout(ng, col_gap=85, row_gap=175, band_gap=230, label_pad=48):
    """Re-spread: columns by longest-path depth, frames as vertical bands, generous row gap
    so stacked clusters (gizmos) have room for clean fan-outs. (run with a SINGLE Group Input)"""
    nodes = [n for n in ng.nodes if n.bl_idname != "NodeFrame"]
    for f in [x for x in ng.nodes if x.bl_idname == "NodeFrame"]: f.location = (0.0, 0.0)
    g_in = next(n for n in nodes if n.bl_idname == "NodeGroupInput")
    g_out = next(n for n in nodes if n.bl_idname == "NodeGroupOutput")
    preds = {n: set() for n in nodes}
    for l in ng.links:
        if l.from_node.bl_idname == "NodeFrame" or l.to_node.bl_idname == "NodeFrame": continue
        preds[l.to_node].add(l.from_node)
    depth = {}
    def d(n, s=()):
        if n in depth: return depth[n]
        if n in s: return 0
        v = 0
        for p in preds[n]: v = max(v, d(p, s + (n,)) + 1)
        depth[n] = v; return v
    for n in nodes: d(n)
    interior = [n for n in nodes if n not in (g_in, g_out)]
    maxcol = max((depth[n] for n in interior), default=1)
    colw = {c: 150.0 for c in range(maxcol + 1)}
    for n in interior: colw[depth[n]] = max(colw[depth[n]], n.width or 150)
    colx, x = {}, 0.0
    for c in range(maxcol + 1): colx[c] = x; x += colw[c] + col_gap
    bands = defaultdict(list)
    for n in interior: bands[fname_of(n)].append(n)
    order = sorted(bands, key=lambda b: sum(depth[n] for n in bands[b]) / len(bands[b]))
    top = 0.0; band_x = 0.0          # CASCADE: each band starts right of the previous one (forward geo flow)
    for b in order:
        bn = bands[b]; bset = set(bn)
        # LOCAL depth: longest path using ONLY intra-band links -> band is only as wide as its own chain
        lpred = {n: set() for n in bn}
        for l in ng.links:
            if l.from_node in bset and l.to_node in bset:
                lpred[l.to_node].add(l.from_node)
        ldepth = {}
        def ld(n, s=()):
            if n in ldepth: return ldepth[n]
            if n in s: return 0
            v = 0
            for p in lpred[n]: v = max(v, ld(p, s + (n,)) + 1)
            ldepth[n] = v; return v
        for n in bn: ld(n)
        maxld = max(ldepth.values())
        lcolw = {c: 150.0 for c in range(maxld + 1)}
        for n in bn: lcolw[ldepth[n]] = max(lcolw[ldepth[n]], n.width or 150)
        lcolx = {}; lx = band_x
        for c in range(maxld + 1): lcolx[c] = lx; lx += lcolw[c] + col_gap
        bycol = defaultdict(list)
        for n in bn: bycol[ldepth[n]].append(n)
        pad = label_pad if b is not None else 0.0; band_h = 0.0
        for c, ns in bycol.items():
            ns.sort(key=lambda n: n.name); yy = top - pad
            for n in ns: n.location = (lcolx[c], yy); yy -= (est_h(n) + row_gap)
            band_h = max(band_h, (top - pad) - yy)
        top -= (band_h + band_gap)
        band_x = lx + 140            # next band cascades right of this one's actual width
    g_in.location = (-340, top / 2.0)
    g_out.location = (band_x + 160, top / 2.0)

def place_output_rightmost(ng):
    gout = next(n for n in ng.nodes if n.bl_idname == 'NodeGroupOutput')
    others = [n for n in ng.nodes if n.bl_idname not in ('NodeFrame', 'NodeGroupOutput')]
    maxr = max(n.location.x + (n.width or 140) for n in others)
    feed = [l.from_node for l in ng.links if l.to_node is gout and l.from_node.bl_idname != 'NodeReroute']
    if feed: gout.location.y = feed[0].location.y
    gout.location.x = maxr + 260   # clear of content + room for its reroute bus (rx = x-140)

def declutter_reroutes(ng):
    """Nudge any reroute that overlaps a real node body out (vertically), so none hide behind nodes."""
    rr = [n for n in ng.nodes if n.bl_idname == 'NodeReroute']
    boxes = [(n.location.x, n.location.y, (n.width or 140), est_h(n))
             for n in ng.nodes if n.bl_idname not in ('NodeReroute', 'NodeFrame')]
    M = 14
    for _ in range(3):
        for r in rr:
            for nx, ny, w, h in boxes:
                if nx - M <= r.location.x <= nx + w + M and ny - h - M <= r.location.y <= ny + M:
                    up, down = ny + M + 10, ny - h - M - 10
                    r.location.y = up if abs(up - r.location.y) <= abs(down - r.location.y) else down
    # reroutes off EACH OTHER (never two on the same spot)
    for _ in range(5):
        for i in range(len(rr)):
            for j in range(i + 1, len(rr)):
                a, b = rr[i], rr[j]
                if abs(a.location.x - b.location.x) < 12 and abs(a.location.y - b.location.y) < 18:
                    b.location.y -= 22

def dissolve_reroutes(ng):
    rr = [n for n in ng.nodes if n.bl_idname == 'NodeReroute']
    if not rr: return 0
    rrset = set(rr)
    def back(node):
        ls = [l for l in ng.links if l.to_node == node]   # '==' works on bpy wrappers; 'is' does NOT (fails after save/reopen)
        if not ls: return None
        fn, fs = ls[0].from_node, ls[0].from_socket
        return back(fn) if fn in rrset else fs
    fixes = []
    for l in list(ng.links):
        if l.from_node in rrset and l.to_node not in rrset:
            rs = back(l.from_node)
            if rs: fixes.append((rs, l.to_node, l.to_socket.identifier))
    for n in rr: ng.nodes.remove(n)
    for rs, tnode, tident in fixes:
        ng.links.new(rs, isock(tnode, tident))
    return len(rr)

def localize_group_inputs(ng):
    gis = [n for n in ng.nodes if n.bl_idname == 'NodeGroupInput']; giset = set(gis)
    items = [(l.from_socket.name, l.to_node, l.to_socket.identifier) for l in ng.links if l.from_node in giset]
    for l in list(ng.links):
        if l.from_node in giset: ng.links.remove(l)
    byframe = defaultdict(list); framemap = {}
    for name, tnode, ident in items:
        fn = fname_of(tnode); byframe[fn].append((name, tnode, ident))
        if tnode.parent: framemap[fn] = tnode.parent
    for fn, its in byframe.items():
        nodes_in = [t for _, t, _ in its]
        minx = min(n.location.x for n in nodes_in); avgy = sum(n.location.y for n in nodes_in) / len(nodes_in)
        lgi = ng.nodes.new("NodeGroupInput")
        if framemap.get(fn): lgi.parent = framemap[fn]
        lgi.location = (minx - 300, avgy)
        for name, tnode, ident in its:
            ng.links.new(lgi.outputs[name], isock(tnode, ident))
        conn = set(l.from_socket.name for l in ng.links if l.from_node is lgi)
        for o in lgi.outputs:
            if o.name and o.name not in conn: o.hide = True
    for g in gis:
        if not any(l.from_node is g for l in ng.links): ng.nodes.remove(g)
    return sum(1 for n in ng.nodes if n.bl_idname == 'NodeGroupInput')

def node_boxes(ng, exclude=()):
    """Real-node bounding boxes (NOT frames/reroutes) for node-aware lane routing. Reroutes are
    added DURING routing, so compute this once from the static nodes and reuse."""
    ex = set(exclude)
    return [(n.location.x, n.location.y, (n.width or 140), est_h(n))
            for n in ng.nodes
            if n.bl_idname not in ('NodeFrame', 'NodeReroute') and n not in ex]

def _hits_node(rx, ymin, ymax, boxes, pad=16):
    """True if a vertical run at X=rx spanning [ymin,ymax] passes through any node body."""
    for nx, ny, w, h in boxes:
        if nx - pad <= rx <= nx + w + pad and not (ymax < ny - h - pad or ymin > ny + pad):
            return True
    return False

def _hits_node_h(hy, xmin, xmax, boxes, pad=16):
    """True if a horizontal run at Y=hy spanning [xmin,xmax] passes through any node body."""
    for nx, ny, w, h in boxes:
        if ny - h - pad <= hy <= ny + pad and not (xmax < nx - pad or xmin > nx + w + pad):
            return True
    return False

def _vlane(rx0, ymin, ymax, placed, boxes=(), step=26, pad=14, minx=None):
    """Pick a clear vertical-bus X for [ymin,ymax]: shift LEFT from rx0 until it overlaps no
    existing run in `placed` (X within step AND Y) AND passes through no node body (`boxes`).
    Subway-map: parallel, non-overlapping lines that never cut through a station."""
    rx = rx0
    def clash(x):
        if any(abs(x - vx) < step and not (ymax < lo - pad or ymin > hi + pad) for vx, lo, hi in placed):
            return True
        return _hits_node(x, ymin, ymax, boxes)
    while clash(rx):
        rx -= step
        if minx is not None and rx < minx:   # ran out of room on the left -> snap to minx and accept
            rx = minx; break
    placed.append((rx, ymin, ymax))
    return rx

def _hlane(hy0, xmin, xmax, hplaced, boxes=(), step=24, pad=14, ddir=-1):
    """Pick a clear horizontal-trunk Y for [xmin,xmax]: shift from hy0 (ddir=-1 -> DOWN, keeping
    western reading flow) until it overlaps no existing trunk in `hplaced` AND no node body."""
    hy = hy0
    def clash(y):
        if any(abs(y - vy) < step and not (xmax < lo - pad or xmin > hi + pad) for vy, lo, hi in hplaced):
            return True
        return _hits_node_h(y, xmin, xmax, boxes)
    while clash(hy):
        hy += step * ddir
    hplaced.append((hy, xmin, xmax))
    return hy

def _route_back(ng, fs, ts, a, b, placed, hplaced, boxes):
    """Target sits LEFT of (or under) its source -> can't flow rightward. Route exit-right, drop to a
    clear horizontal lane BELOW, run left to just-left-of-target, rise into it. 4 reroutes, fully
    orthogonal, approaches the target from the left (rightward) so the wire never overshoots/self-crosses."""
    a_right = a.location.x + (a.width or 140)
    rx_out = a_right + 25
    rx_in = b.location.x - 35
    xlo, xhi = min(rx_in, rx_out), max(rx_in, rx_out)
    lane_y = _hlane(min(_ymid(a), _ymid(b)) - 70, xlo, xhi, hplaced, boxes, ddir=-1)
    placed.append((rx_out, min(lane_y, _ymid(a)), max(lane_y, _ymid(a))))
    placed.append((rx_in, min(lane_y, _ymid(b)), max(lane_y, _ymid(b))))
    P0 = ng.nodes.new("NodeReroute"); P0.location = (rx_out, _ymid(a))
    P1 = ng.nodes.new("NodeReroute"); P1.location = (rx_out, lane_y)
    P2 = ng.nodes.new("NodeReroute"); P2.location = (rx_in, lane_y)
    P3 = ng.nodes.new("NodeReroute"); P3.location = (rx_in, _ymid(b))
    ng.links.new(fs, P0.inputs[0]); ng.links.new(P0.outputs[0], P1.inputs[0])
    ng.links.new(P1.outputs[0], P2.inputs[0]); ng.links.new(P2.outputs[0], P3.inputs[0])
    ng.links.new(P3.outputs[0], ts)

def _route_v(ng, fs, ts, a, b, placed, boxes=(), hplaced=None):
    a_right = a.location.x + (a.width or 140)
    if b.location.x < a_right + 50:                 # backward / overshoot risk -> over-under route
        _route_back(ng, fs, ts, a, b, placed, hplaced if hplaced is not None else [], boxes); return
    soy = a.location.y - 35; diy = b.location.y - 35
    rx = _vlane(b.location.x - 140, min(soy, diy), max(soy, diy), placed, boxes, minx=a_right + 20)
    A = ng.nodes.new("NodeReroute"); A.location = (rx, soy)
    B = ng.nodes.new("NodeReroute"); B.location = (rx, diy)
    ng.links.new(fs, A.inputs[0]); ng.links.new(A.outputs[0], B.inputs[0]); ng.links.new(B.outputs[0], ts)

def _ymid(node): return node.location.y - 22   # link y at a node's first socket (approx)

def route_branches(ng, placed, hplaced, boxes):
    """Group EVERY real link by its SOURCE socket, then route each source ONCE:
      - 1 target, cross-frame -> orthogonal H-V-H (2 reroutes in a clear lane).
      - 1 target, same-frame  -> leave direct (route_around handles any node crossing).
      - >=2 targets           -> ONE SHARED daisy-chained branch off the source (never duplicate
        reroutes on the same line): STACKED targets -> a vertical bus; SPREAD targets -> a horizontal
        trunk at source height that splits off a tap per column then continues right. Targets sharing
        a row/column reuse the SAME reroute (deduped) so no two reroutes ever land on one spot."""
    bysrc = defaultdict(list)
    for l in ng.links:
        a, b = l.from_node, l.to_node
        if a.bl_idname in ('NodeReroute', 'NodeGroupInput') or b.bl_idname == 'NodeReroute': continue
        bysrc[(a, l.from_socket.identifier)].append((b, l.to_socket.identifier))
    items = sorted(bysrc.items(), key=lambda kv: -max(b.location.x for b, _ in kv[1]))  # rightmost first
    n_hv = 0; n_fan = 0
    for (a, fid), tg in items:
        fs = osock(a, fid); a_right = a.location.x + (a.width or 140)
        if len(tg) == 1:
            b, tid = tg[0]
            if fname_of(a) is not None and fname_of(a) == fname_of(b):
                continue                                        # same-frame single: leave direct
            ts = isock(b, tid)
            for l in list(ng.links):
                if l.from_socket == fs and l.to_socket == ts: ng.links.remove(l); break
            _route_v(ng, fs, ts, a, b, placed, boxes, hplaced); n_hv += 2
            continue
        ys = [b.location.y for b, _ in tg]; xs = [b.location.x for b, _ in tg]
        if max(ys) - min(ys) < 50 and max(xs) - min(xs) < 80:
            continue                                            # tight cluster: short direct lines read fine
        sock = {}                                               # drop originals, remember target sockets
        for b, tid in tg:
            ts = isock(b, tid); sock[(b, tid)] = ts
            for l in list(ng.links):
                if l.from_socket == fs and l.to_socket == ts: ng.links.remove(l); break
        # split BACKWARD targets (left of/under source) -> each over-under routed (no overshoot)
        bwd = [(b, tid) for b, tid in tg if b.location.x < a_right + 50]
        for b, tid in bwd:
            _route_back(ng, fs, sock[(b, tid)], a, b, placed, hplaced, boxes); n_fan += 1
        tg = [(b, tid) for b, tid in tg if b.location.x >= a_right + 50]
        if not tg: continue
        if len(tg) == 1:                                        # one forward target left -> simple H-V-H
            b, tid = tg[0]; _route_v(ng, fs, sock[(b, tid)], a, b, placed, boxes, hplaced); n_hv += 2
            continue
        ys = [b.location.y for b, _ in tg]; xs = [b.location.x for b, _ in tg]
        if max(xs) - min(xs) <= 200:
            # ---- STACKED: one vertical bus, reroutes deduped per ROW ----
            ymin = min(ys + [a.location.y]) - 35; ymax = max(ys + [a.location.y])
            bus_x = _vlane(min(xs) - 45, ymin, ymax, placed, boxes, minx=a_right + 25)
            rows = defaultdict(list)
            for b, tid in tg: rows[round(_ymid(b) / 8) * 8].append((b, tid))
            R0 = ng.nodes.new("NodeReroute"); R0.location = (bus_x, _ymid(a)); ng.links.new(fs, R0.inputs[0])
            prev = R0
            for ry in sorted(rows, reverse=True):               # top -> bottom (flow DOWN)
                R = ng.nodes.new("NodeReroute"); R.location = (bus_x, ry)
                ng.links.new(prev.outputs[0], R.inputs[0]); prev = R
                for b, tid in rows[ry]: ng.links.new(R.outputs[0], sock[(b, tid)]); n_fan += 1
        else:
            # ---- SPREAD: horizontal trunk at source height (flows RIGHT), tap DOWN per column ----
            tx0 = a_right + 25; txmax = max(xs) + 5
            trunk_y = _hlane(_ymid(a), tx0, txmax, hplaced, boxes, ddir=-1)
            E = ng.nodes.new("NodeReroute"); E.location = (tx0, trunk_y); ng.links.new(fs, E.inputs[0])
            prev = E
            cols = defaultdict(list)
            for b, tid in tg: cols[round(b.location.x / 12) * 12].append((b, tid))
            for cx in sorted(cols):                             # left -> right along the trunk
                col = cols[cx]; col_ys = [_ymid(b) for b, _ in col] + [trunk_y]
                tap_x = _vlane(cx - 32, min(col_ys) - 12, max(col_ys), placed, boxes, minx=tx0)
                T = ng.nodes.new("NodeReroute"); T.location = (tap_x, trunk_y)
                ng.links.new(prev.outputs[0], T.inputs[0]); prev = T            # trunk continues right
                rows = defaultdict(list)
                for b, tid in col: rows[round(_ymid(b) / 8) * 8].append((b, tid))
                vprev = T
                for ry in sorted(rows, reverse=True):           # drop DOWN the column, deduped per row
                    D = ng.nodes.new("NodeReroute"); D.location = (tap_x, ry)
                    ng.links.new(vprev.outputs[0], D.inputs[0]); vprev = D
                    for b, tid in rows[ry]: ng.links.new(D.outputs[0], sock[(b, tid)]); n_fan += 1
    return n_hv, n_fan

def route_around_nodes(ng):
    """Route a SAME-frame link up and over the row ONLY if its straight path actually
    passes through another node's body (never cross a node)."""
    members = lambda fn: [n for n in ng.nodes if fname_of(n) == fn and n.bl_idname not in ('NodeFrame', 'NodeReroute')]
    cand = []
    for l in ng.links:
        a, b = l.from_node, l.to_node
        if a.bl_idname == 'NodeReroute' or b.bl_idname == 'NodeReroute': continue
        if fname_of(a) is None or fname_of(a) != fname_of(b) or l.to_socket.is_multi_input: continue
        ax2 = a.location.x + (a.width or 140); ay = a.location.y - 22
        bx = b.location.x; by = b.location.y - 22
        if bx <= ax2 + 10: continue
        blk = []
        for N in members(fname_of(a)):
            if N is a or N is b: continue
            nx1, nx2 = N.location.x, N.location.x + (N.width or 140)
            ox1, ox2 = max(nx1, ax2), min(nx2, bx)
            if ox2 <= ox1: continue
            t = ((ox1 + ox2) / 2 - ax2) / (bx - ax2)
            wy = ay + t * (by - ay)
            if (N.location.y - est_h(N) - 4) <= wy <= (N.location.y + 4):
                blk.append(N)
        if blk:
            top = max([N.location.y for N in blk] + [a.location.y, b.location.y]) + 45
            cand.append((a, l.from_socket.identifier, b, l.to_socket.identifier, top))
    cand.sort(key=lambda c: c[0].location.x)
    for i, (a, fid, b, tid, top) in enumerate(cand):
        fs, ts = osock(a, fid), isock(b, tid)
        for l in list(ng.links):
            if l.from_socket == fs and l.to_socket == ts: ng.links.remove(l); break
        ry = top + (i % 6) * 24
        R1 = ng.nodes.new("NodeReroute"); R1.location = (a.location.x + (a.width or 140) + 22, ry)
        R2 = ng.nodes.new("NodeReroute"); R2.location = (b.location.x - 30, ry)
        ng.links.new(fs, R1.inputs[0]); ng.links.new(R1.outputs[0], R2.inputs[0]); ng.links.new(R2.outputs[0], ts)
    return len(cand)

if "--" in sys.argv:                       # run on a subset: blender ... -- GN_Spherify GN_Twist
    sel = sys.argv[sys.argv.index("--") + 1:]
    if sel: TARGETS = sel                      # route exactly the names passed (any file, not just defaults)

for fname in TARGETS:
    bpy.ops.wm.open_mainfile(filepath=os.path.join(GEO, fname + ".blend"))
    ng = bpy.data.node_groups[fname]
    obj = next(o for o in bpy.data.objects if any(m.type == 'NODES' and m.node_group == ng for m in o.modifiers))
    m = next(md for md in obj.modifiers if md.node_group == ng)
    ids = {it.name: it.identifier for it in ng.interface.items_tree if getattr(it, 'item_type', '') == 'SOCKET' and it.in_out == 'INPUT'}
    pid = ids.get("Show Deformation Preview"); pval = m.get(pid) if pid else None
    def snap(preview):
        if pid is not None: m[pid] = preview
        obj.update_tag(); bpy.context.view_layer.update()
        dg = bpy.context.evaluated_depsgraph_get(); ev = obj.evaluated_get(dg); me = ev.to_mesh()
        P = [v.co.copy() for v in me.vertices]; ev.to_mesh_clear(); return P
    base_on, base_off = snap(True), snap(False)
    diss = dissolve_reroutes(ng)
    tidy_layout(ng)                      # re-spread (B): looser vertical stacking before routing
    n_gi = localize_group_inputs(ng)
    place_output_rightmost(ng)
    placed = []; hplaced = []                    # shared vertical / horizontal lane allocators
    boxes = node_boxes(ng)                        # node bodies to route AROUND (reroutes added below)
    n_hv, n_fb = route_branches(ng, placed, hplaced, boxes)   # H-V-H singles + shared daisy-chained fans
    n_ia = route_around_nodes(ng)
    declutter_reroutes(ng)
    aft_on, aft_off = snap(True), snap(False)
    def eq(p, q): return len(p) == len(q) and all((a - b).length < 1e-6 for a, b in zip(p, q))
    def eqset(p, q):  # same geometry, order may differ (preview-on, not exported)
        k = lambda P: sorted((round(c.x, 5), round(c.y, 5), round(c.z, 5)) for c in P)
        return len(p) == len(q) and k(p) == k(q)
    ok = eq(base_off, aft_off) and eqset(base_on, aft_on)   # OFF index-strict (real output), ON same-set
    if pid is not None: m[pid] = pval
    if ok:
        bpy.ops.wm.save_mainfile()
        print(f"[OK]   {fname:14} local-GIs={n_gi} hv={n_hv} fan={n_fb} around={n_ia} (OFF strict, ON same-set) -> saved")
    else:
        print(f"[FAIL] {fname:14} on={eq(base_on,aft_on)} off={eq(base_off,aft_off)} NOT SAVED")
sys.stdout.flush(); os._exit(0)
