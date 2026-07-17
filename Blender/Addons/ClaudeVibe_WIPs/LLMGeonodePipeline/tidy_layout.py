import bpy, sys, os
from collections import defaultdict
GEO = r"D:\Stephko_Tooling\Toolings\Blender\Geonodes"
TARGETS = ["GN_Spherify", "GN_Twist", "GN_Taper", "GN_Wave", "GN_Bend", "GN_Stretch",
           "GN_Inflate", "GN_Smooth", "GN_RandomizePosition",
           "GN_Triangulate", "GN_Subdivide", "GN_Wireframe", "GN_RadialArray",
           "GN_Displace", "GN_MeshBoolean", "GN_Cast", "GN_Scatter",
           "GN_ConvexHull", "GN_BoundingBox", "GN_FlipFaces", "GN_SetMaterial",
           "GN_DualMesh", "GN_VoxelRemesh", "GN_AutoSmooth", "GN_PointsToSpheres",
           "GN_NormalTransfer"]

def isock(node, ident): return next(s for s in node.inputs if s.identifier == ident)
def osock(node, ident): return next(s for s in node.outputs if s.identifier == ident)
def isock_or_extend(node, ident):
    """Input socket by identifier, falling back to the node's '__extend__' socket.
    Dynamic-item sockets (Blender 5 Viewer items) self-remove when unlinked, so a
    remove-then-relink round trip must recreate them via the extension socket."""
    s = next((s for s in node.inputs if s.identifier == ident), None)
    if s is None:
        s = next((s for s in node.inputs if s.identifier == '__extend__'), None)
    return s
def fname_of(n): return n.parent.name if n.parent else None   # frame identity by NAME (bpy wrappers fail `is`)
def est_h(n):
    if n.dimensions.y > 0:                        # actual drawn size (0 when headless/pre-draw)
        return n.dimensions.y / _uiscale()
    nin = sum(1 for s in n.inputs if s.enabled and not s.hide and s.type != 'CUSTOM')
    nout = sum(1 for s in n.outputs if s.enabled and not s.hide and s.type != 'CUSTOM')
    # an unlinked vector/rotation input draws 3 extra value sliders below its row
    extra = sum(54 for s in n.inputs if s.enabled and not s.hide and not s.is_linked
                and s.type in ('VECTOR', 'ROTATION') and not s.hide_value)
    return 34 + (nin + nout) * 22 + 30 + extra

def tidy_layout(ng, col_gap=130, row_gap=55, band_gap=120, label_pad=48):
    # col_gap 85->130 (2026-07-09 user image-diff): tight columns cramped the frames;
    # wider columns also give GI param ribbons and drop lanes room to stay clear
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
        pad = label_pad if b is not None else 0.0
        for c, ns in bycol.items():
            ns.sort(key=lambda n: n.name); yy = top - pad
            for n in ns: n.location = (lcolx[c], yy); yy -= (est_h(n) + row_gap)
        # SOCKET-ANCHORED Y (user image-diff GN_Wave 2026-07-10): a feeder aligns its
        # OUTPUT to the Y of the input SOCKET it feeds, sweeping columns right-to-left.
        # Tall consumers (Index/Menu Switch: inputs span 100s of px) get staggered
        # feeder rows with short direct wires instead of one top-aligned row whose
        # wires dive across the band -- and a feeder that anchors LOW vacates the
        # straight path between its row neighbours (move the blocker, don't detour).
        outl = defaultdict(list)
        for l in ng.links:
            if l.from_node in bset and l.to_node in bset:
                outl[l.from_node.name].append(l)
        for c in range(maxld - 1, -1, -1):
            ns = bycol.get(c)
            if not ns: continue
            want = {}
            for n in ns:
                anchors = []
                for l in outl.get(n.name, ()):
                    if ldepth[l.to_node] > c:      # forward links only (later columns are final)
                        off = _socket_y(n, l.from_socket, False) - n.location.y
                        anchors.append(_socket_y(l.to_node, l.to_socket, True) - off)
                want[n.name] = (sum(anchors) / len(anchors)) if anchors else n.location.y
            ns.sort(key=lambda n: -want[n.name])
            yy = top - pad
            for n in ns:                           # greedy: keep anchor order, never overlap
                n.location.y = min(want[n.name], yy)
                yy = n.location.y - est_h(n) - row_gap
        band_h = max((top - pad) - (n.location.y - est_h(n)) for n in bn)
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
        ts = isock_or_extend(tnode, tident)
        if ts is not None: ng.links.new(rs, ts)
    return len(rr)

def localize_group_inputs(ng):
    gis = [n for n in ng.nodes if n.bl_idname == 'NodeGroupInput']; giset = set(gis)
    # key by socket IDENTIFIER, never display name -- two interface sockets may share a name
    items = [(l.from_socket.identifier, l.to_node, l.to_socket.identifier) for l in ng.links if l.from_node in giset]
    for l in list(ng.links):
        if l.from_node in giset: ng.links.remove(l)
    # panel lookup for GI labeling (socket identifier -> NAMED panel, '' if top-level)
    sock_panel = {}
    for it in ng.interface.items_tree:
        if getattr(it, 'item_type', '') == 'SOCKET':
            par = getattr(it, 'parent', None)
            sock_panel[it.identifier] = (getattr(par, 'name', '') or '').strip() if par is not None else ''
    byframe = defaultdict(list); framemap = {}
    for gid, tnode, ident in items:
        fn = fname_of(tnode); byframe[fn].append((gid, tnode, ident))
        if tnode.parent: framemap[fn] = tnode.parent
    for fn, its in byframe.items():
        # split consumers into X-CLUSTERS: a far-right consumer gets its OWN small GI
        # parked next to it, instead of one long wire from the frame's main GI
        # (user image-diff: a one-socket GI labeled by its panel right before the Mix node)
        its.sort(key=lambda t: t[1].location.x)
        clusters = [[its[0]]]
        for t in its[1:]:
            if t[1].location.x - clusters[-1][-1][1].location.x > 900:
                clusters.append([t])
            else:
                clusters[-1].append(t)
        for cl in clusters:
            nodes_in = [t for _, t, _ in cl]
            minx = min(n.location.x for n in nodes_in)
            lgi = ng.nodes.new("NodeGroupInput")
            if framemap.get(fn): lgi.parent = framemap[fn]
            if len(nodes_in) == 1:
                # single consumer: directly left of it, socket-aligned
                anchor_y = nodes_in[0].location.y
            else:
                # multi consumer: BELOW-left, so the param ribbon sweeps the clear
                # corridor under the frame's nodes as straight parallel lines
                anchor_y = min(n.location.y - est_h(n) for n in nodes_in) - 60
            lgi.location = (minx - 300, anchor_y)
            for gid, tnode, ident in cl:
                ts = isock_or_extend(tnode, ident)
                if ts is not None: ng.links.new(osock(lgi, gid), ts)
            conn = set(l.from_socket.identifier for l in ng.links if l.from_node is lgi)
            for o in lgi.outputs:
                if o.identifier and o.identifier not in conn: o.hide = True
            # label: the interface PANEL name when unambiguous, else the function frame
            panels = set(sock_panel.get(g, '') for g in conn) - {''}
            if len(panels) == 1:
                lgi.label = next(iter(panels))
            elif framemap.get(fn) and (framemap[fn].label or '').strip():
                lgi.label = f"In: {framemap[fn].label}"
            # slide the new GI to the vertical gap NEAREST its anchor among nodes sharing
            # its x-span (never a cumulative push-down: that walks it below the whole column)
            w, h = (lgi.width or 140), est_h(lgi)
            x0, x1 = lgi.location.x - 30, lgi.location.x + w + 30
            occ = [(o.location.y, o.location.y - est_h(o)) for o in ng.nodes
                   if o is not lgi and o.bl_idname not in ('NodeFrame', 'NodeReroute')
                   and o.location.x < x1 and o.location.x + (o.width or 140) > x0]
            def _clear(top):
                return all(top - h - 30 >= t or top + 30 <= b for t, b in occ)
            if not _clear(lgi.location.y):
                cands = [y for t, b in occ for y in (t + 30 + h, b - 30) if _clear(y)]
                if cands: lgi.location.y = min(cands, key=lambda y: abs(y - anchor_y))
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

ADJ_DX = 300.0   # a link no longer than this (edge to edge) is "adjacent" -- keep it a direct wire
ADJ_DY = 240.0   # ...provided the rise is small too (keep in sync with layout_audit R11)

def _seg_clear(sx, sy, tx, ty, boxes, pad=4):
    """True if the straight wire (sx,sy)->(tx,ty) crosses no node body (forward links only).
    Subway-map corollary: lines only bend for a reason -- short unobstructed runs stay direct."""
    if tx <= sx:
        return False
    for nx, ny, w, h in boxes:
        x0, y0, x1, y1 = nx, ny - h, nx + w, ny
        ox0, ox1 = max(x0, sx), min(x1, tx)
        if ox1 <= ox0:
            continue
        for xx in (ox0, (ox0 + ox1) / 2.0, ox1):
            t = (xx - sx) / (tx - sx)
            if 0.0 < t < 1.0 and (y0 - pad) <= (sy + t * (ty - sy)) <= (y1 + pad):
                return False
    return True

def _adjacent_direct(a, fs, b, ts, boxes):
    """Adjacency test shared by all routing passes: target close, small rise, clear path."""
    a_right = a.location.x + (a.width or 140)
    soy = _socket_y(a, fs, False); tyy = _socket_y(b, ts, True)
    return ((b.location.x - a_right) < ADJ_DX and abs(soy - tyy) < ADJ_DY
            and _seg_clear(a_right, soy, b.location.x, tyy, boxes))

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
    """Pick a clear horizontal-trunk Y for [xmin,xmax] (no clash with an existing trunk in
    `hplaced` or a node body). Search BOTH directions from hy0 and take the NEAREST clear
    lane, preferring `ddir` (default DOWN, western reading flow) on ties.

    Bidirectional on purpose: a down-only search gets shoved past a whole lower row of nodes
    when a short hop UP into the header gap was clear -- that produced the deep fan-out detour
    (trunk dived ~400px below the row and looped back). Nearest-clear keeps fans compact."""
    def clash(y):
        if any(abs(y - vy) < step and not (xmax < lo - pad or xmin > hi + pad) for vy, lo, hi in hplaced):
            return True
        return _hits_node_h(y, xmin, xmax, boxes)
    if not clash(hy0):
        hplaced.append((hy0, xmin, xmax)); return hy0
    for k in range(1, 400):
        for d in (ddir, -ddir):            # try ddir side first at each distance, then the other
            y = hy0 + step * k * d
            if not clash(y):
                hplaced.append((y, xmin, xmax)); return y
    hplaced.append((hy0, xmin, xmax)); return hy0   # give up: accept start

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
    soy = _socket_y(a, fs, False); diy = _socket_y(b, ts, True)  # enter/leave AT socket height
    rx = _vlane(b.location.x - 140, min(soy, diy), max(soy, diy), placed, boxes, minx=a_right + 20)
    # E = framed EXIT reroute right of the source; A = gap bend; B = framed ENTRY at target socket
    E = ng.nodes.new("NodeReroute"); E.location = (a_right + 25, soy)
    A = ng.nodes.new("NodeReroute"); A.location = (rx, soy)
    B = ng.nodes.new("NodeReroute"); B.location = (rx, diy)
    ng.links.new(fs, E.inputs[0]); ng.links.new(E.outputs[0], A.inputs[0])
    ng.links.new(A.outputs[0], B.inputs[0]); ng.links.new(B.outputs[0], ts)

def _ymid(node): return node.location.y - 22   # link y at a node's first socket (approx)

def _uiscale():
    try: return bpy.context.preferences.system.ui_scale
    except Exception: return 1.0

def _socket_y(node, sock, is_input):
    """Estimate a socket's Y (node space), headless-safe. Outputs stack from just below the
    header (socket 0 highest); inputs stack in the LOWER part of the node (socket 0 highest of
    the inputs). Used to enter/leave a node AT its socket height so taps are pure-horizontal
    and multi-socket entries stagger instead of piling on one row."""
    coll = node.inputs if is_input else node.outputs
    vis = [s for s in coll if s.enabled and not s.hide and s.type != 'CUSTOM']
    try: i = vis.index(sock)
    except ValueError: i = 0
    if not is_input:
        return node.location.y - 34 - i * 22 - 6
    n = len(vis) or 1
    h = (node.dimensions.y / _uiscale()) if node.dimensions.y else est_h(node)
    return (node.location.y - h) + (n - i) * 22 - 6

def route_into_nodes(ng, placed, hplaced, boxes):
    """Coordinate ALL cross-band wires entering the SAME node into a nested, non-crossing
    staircase (subway-map): each entry reroute sits at its target SOCKET's Y (staggered), and
    lanes nest so the TOPMOST socket turns in the lane closest to the node, lower sockets in
    lanes progressively further left. This replaces `_route_v`'s old habit of parking every
    entry reroute at node_y-35 (one horizontal row -> crossing taps). Rerouted links become
    source->reroute->reroute->target, so route_branches (which skips reroute endpoints) leaves
    them alone. Run BEFORE route_branches."""
    from collections import defaultdict
    # A source socket feeding >1 target is a FAN -> leave the whole fan to route_branches
    # (stealing one branch here fragments the fan and makes the source loop back on itself).
    src_fanout = defaultdict(int)
    for l in ng.links:
        if l.from_node.bl_idname in ('NodeReroute', 'NodeGroupInput'):
            continue
        src_fanout[(l.from_node.name, l.from_socket.identifier)] += 1

    by_target = defaultdict(list)
    for l in ng.links:
        a, b = l.from_node, l.to_node
        if a.bl_idname in ('NodeReroute', 'NodeGroupInput') or b.bl_idname == 'NodeReroute':
            continue
        if l.to_socket.is_multi_input:            # never reroute into a merge socket (reorders)
            continue
        if src_fanout[(a.name, l.from_socket.identifier)] > 1:   # fan source -> route_branches
            continue
        a_right = a.location.x + (a.width or 140)
        if b.location.x < a_right + 50:            # backward -> leave to route_back
            continue
        if fname_of(a) == fname_of(b):             # same-frame -> not a cross-band entry
            continue
        by_target[b.name].append((a, l.from_socket.identifier, l.to_socket.identifier))
    n_routed = 0
    for tname, entries in by_target.items():
        if len(entries) < 2:                       # single entry: let route_branches H-V-H it
            continue
        b = next(n for n in ng.nodes if n.name == tname)
        # resolve sockets, sort topmost-target-socket first
        rows = []
        for aname_src, fid, tid in entries:
            a = aname_src
            fs = next(s for s in a.outputs if s.identifier == fid)
            ts = next(s for s in b.inputs if s.identifier == tid)
            rows.append((a, fs, ts, _socket_y(b, ts, True)))
        rows.sort(key=lambda r: -r[3])             # highest socket Y first (topmost)
        # adjacent sources with a clear straight path keep their DIRECT wire (no staircase)
        rows = [(a, fs, ts, sy) for a, fs, ts, sy in rows
                if not _adjacent_direct(a, fs, b, ts, boxes)]
        base_x = b.location.x - 45
        for k, (a, fs, ts, sy) in enumerate(rows):
            soy = _socket_y(a, fs, False)
            want_x = base_x - k * 30               # topmost=k0=nearest node; lower sockets further left
            lane_x = _vlane(want_x, min(soy, sy), max(soy, sy), placed, boxes,
                            minx=a.location.x + (a.width or 140) + 20)
            for ll in list(ng.links):              # drop the original direct link
                if ll.from_socket == fs and ll.to_socket == ts:
                    ng.links.remove(ll); break
            # E = framed EXIT reroute just right of the source (inside source frame);
            # A = gap bend at the drop lane; B = framed ENTRY at the target socket.
            E = ng.nodes.new("NodeReroute"); E.location = (a.location.x + (a.width or 140) + 25, soy)
            A = ng.nodes.new("NodeReroute"); A.location = (lane_x, soy)
            B = ng.nodes.new("NodeReroute"); B.location = (lane_x, sy)
            ng.links.new(fs, E.inputs[0]); ng.links.new(E.outputs[0], A.inputs[0])
            ng.links.new(A.outputs[0], B.inputs[0]); ng.links.new(B.outputs[0], ts)
            n_routed += 1
    return n_routed

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
        # viewers excluded: their dynamic item sockets vanish on unlink, so keep those wires direct
        if a.bl_idname in ('NodeReroute', 'NodeGroupInput') or b.bl_idname in ('NodeReroute', 'GeometryNodeViewer'): continue
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
            if _adjacent_direct(a, fs, b, ts, boxes):
                continue                                        # adjacent + clear: direct wire reads best
            for l in list(ng.links):
                if l.from_socket == fs and l.to_socket == ts: ng.links.remove(l); break
            _route_v(ng, fs, ts, a, b, placed, boxes, hplaced); n_hv += 2
            continue
        ys = [b.location.y for b, _ in tg]; xs = [b.location.x for b, _ in tg]
        if max(ys) - min(ys) < 50 and max(xs) - min(xs) < 80:
            continue                                            # tight cluster: short direct lines read fine
        # adjacent branches with a clear straight wire stay DIRECT; only the rest get bused
        tg = [(b, tid) for b, tid in tg if not _adjacent_direct(a, fs, b, isock(b, tid), boxes)]
        if not tg:
            continue                                            # whole fan adjacent: a bus adds noise
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
            b, tid = tg[0]
            if _adjacent_direct(a, fs, b, sock[(b, tid)], boxes):
                ng.links.new(fs, sock[(b, tid)])                # adjacent + clear: restore the direct wire
            else:
                _route_v(ng, fs, sock[(b, tid)], a, b, placed, boxes, hplaced); n_hv += 2
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
            # ---- SPREAD: horizontal trunk flowing strictly RIGHT, one tap per target ----
            # MONOTONIC: each tap_x is forced >= previous tap + spacing and only ever shifts
            # RIGHT to clear a node. (The old per-column `_vlane` shifted LEFT on clash, so a
            # later tap could land left of an earlier one -> the wire looped back on itself.)
            tg.sort(key=lambda bt: bt[0].location.x)
            soy0 = _socket_y(a, fs, False)
            tx0 = a_right + 25; txmax = max(xs) + 60
            trunk_y = _hlane(soy0, tx0, txmax, hplaced, boxes)
            E = ng.nodes.new("NodeReroute"); E.location = (tx0, trunk_y); ng.links.new(fs, E.inputs[0])
            prev = E; last_x = tx0
            for b, tid in tg:
                ty = _socket_y(b, sock[(b, tid)], True)
                tap_x = max(b.location.x - 30, last_x + 28)          # never left of the previous tap
                lo, hi = min(ty, trunk_y) - 6, max(ty, trunk_y) + 6
                while _hits_node(tap_x, lo, hi, boxes) and tap_x < b.location.x + (b.width or 140):
                    tap_x += 24                                       # clear a node by shifting RIGHT
                last_x = tap_x
                T = ng.nodes.new("NodeReroute"); T.location = (tap_x, trunk_y)
                ng.links.new(prev.outputs[0], T.inputs[0]); prev = T   # trunk marches right
                D = ng.nodes.new("NodeReroute"); D.location = (tap_x, ty)
                ng.links.new(T.outputs[0], D.inputs[0]); ng.links.new(D.outputs[0], sock[(b, tid)])
                n_fan += 2
    return n_hv, n_fan

def route_around_nodes(ng):
    """Route a SAME-frame link up and over the row ONLY if its straight path actually
    passes through another node's body (never cross a node)."""
    members = lambda fn: [n for n in ng.nodes if fname_of(n) == fn and n.bl_idname not in ('NodeFrame', 'NodeReroute')]
    cand = []
    for l in ng.links:
        a, b = l.from_node, l.to_node
        # Group-Input param fans stay DIRECT straight wires, always -- lane-detouring them
        # stacked 6+ reroute rows across the frame label (user image-diff, EdgeDestruct).
        if a.bl_idname in ('NodeReroute', 'NodeGroupInput') or b.bl_idname in ('NodeReroute', 'GeometryNodeViewer'): continue
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

def frame_reroutes(ng):
    """Parent each reroute to the comment frame (function) it spatially sits inside, so a
    reroute reads as belonging to that function. A reroute in the gap BETWEEN frames stays
    unparented (it's the inter-function track). Cross-function wires therefore keep a framed
    reroute in each function they touch (exit inside source, entry inside target) plus any
    gap bends. Run LAST. Frames are at (0,0) here (tidy_layout set them), so child.location ==
    absolute and parenting a reroute needs no coordinate fix.

    Containment uses each frame's *node* bbox (excluding reroutes), so a reroute is only pulled
    in if it truly sits over that function's nodes -- it can't drag a frame open into overlap."""
    frames = [f for f in ng.nodes if f.bl_idname == 'NodeFrame']
    sc = _uiscale()

    def node_bbox(f):
        ks = [n for n in ng.nodes if n.parent is not None and n.parent.name == f.name
              and n.bl_idname not in ('NodeFrame', 'NodeReroute')]
        if not ks:
            return None
        x0 = min(k.location.x for k in ks)
        x1 = max(k.location.x + (k.width or 140) for k in ks)
        y1 = max(k.location.y for k in ks)
        y0 = min(k.location.y - ((k.dimensions.y / sc) if k.dimensions.y else est_h(k)) for k in ks)
        return (x0, y0, x1, y1)

    bb = {f.name: node_bbox(f) for f in frames}
    bb = {k: v for k, v in bb.items() if v}
    M = 60.0   # containment margin: a reroute hugging a frame's nodes belongs to that function
    n = 0
    for r in ng.nodes:
        if r.bl_idname != 'NodeReroute' or r.parent is not None:
            continue
        rx, ry = r.location.x, r.location.y
        inside = [f for f in frames
                  if f.name in bb and (bb[f.name][0] - M) <= rx <= (bb[f.name][2] + M)
                  and (bb[f.name][1] - M) <= ry <= (bb[f.name][3] + M)]
        if inside:                                 # innermost (smallest) wins -> supports nested frames
            f = min(inside, key=lambda f: (bb[f.name][2] - bb[f.name][0]) * (bb[f.name][3] - bb[f.name][1]))
            r.parent = f
            n += 1
    return n


def separate_frames(ng, margin=40):
    """R7 ENFORCEMENT (root cause found 2026-07-10): post-layout extensions -- a
    below-left localized GI, exit/gap reroutes -- poke past the band footprint the
    cascade reserved, so at a diagonal band junction two frame boxes corner-cross
    through EMPTY space. Detect partial overlap exactly like the audit (children
    bbox, nesting allowed) and shift the LOWER frame's contents straight DOWN until
    clear. Down-only on purpose: vertical lanes stay vertical under a pure Y shift,
    so the orthogonal routing survives; an x-shift would shear cross-band lanes."""
    def fbox(fname):
        kids = [n for n in ng.nodes if n.parent is not None and n.parent.name == fname]
        if not kids: return None
        x0 = y0 = x1 = y1 = None
        for k in kids:
            w, h = (10.0, 10.0) if k.bl_idname == 'NodeReroute' else ((k.width or 140.0), est_h(k))
            kx, ky = k.location.x, k.location.y
            x0 = kx if x0 is None else min(x0, kx);          y0 = ky - h if y0 is None else min(y0, ky - h)
            x1 = kx + w if x1 is None else max(x1, kx + w);  y1 = ky if y1 is None else max(y1, ky)
        return (x0, y0, x1, y1)
    def descendants(fname):
        out = []
        for n in ng.nodes:
            if n.bl_idname == 'NodeFrame': continue
            p = n.parent
            while p is not None:
                if p.name == fname: out.append(n); break
                p = p.parent
        return out
    n_shift = 0
    for _ in range(12):
        frames = [f.name for f in ng.nodes if f.bl_idname == 'NodeFrame']
        boxes = {fn: fbox(fn) for fn in frames}
        boxes = {k: v for k, v in boxes.items() if v}
        moved = False
        names = sorted(boxes, key=lambda n: -boxes[n][3])          # top-most first
        for i in range(len(names)):
            for j in range(i + 1, len(names)):
                A, B = boxes[names[i]], boxes[names[j]]            # A is the upper frame
                if A[2] <= B[0] + 4 or B[2] <= A[0] + 4 or A[3] <= B[1] + 4 or B[3] <= A[1] + 4:
                    continue                                       # no overlap
                if (A[0] <= B[0] and A[1] <= B[1] and A[2] >= B[2] and A[3] >= B[3]) or \
                   (B[0] <= A[0] and B[1] <= A[1] and B[2] >= A[2] and B[3] >= A[3]):
                    continue                                       # full nesting is deliberate
                dy = B[3] - (A[1] - margin)                        # push B's top below A's bottom
                if dy <= 0: continue
                for n in descendants(names[j]):
                    n.location.y -= dy
                boxes[names[j]] = fbox(names[j])
                n_shift += 1; moved = True
        if not moved: break
    return n_shift


# ---------------------------------------------------------------------------
#  Importable pipeline API  (used by run_pipeline.py and the __main__ CLI below)
# ---------------------------------------------------------------------------

def tidy_and_route(ng):
    """Full deterministic layout pass, mutating `ng` in place:
    dissolve reroutes -> layered tidy (frames as bands) -> localize group inputs
    -> place output rightmost -> orthogonal reroute routing -> declutter.
    No file I/O and no geometry check -- callers own those. Returns a stats dict."""
    dissolve_reroutes(ng)
    tidy_layout(ng)
    n_gi = localize_group_inputs(ng)
    place_output_rightmost(ng)
    placed = []; hplaced = []
    boxes = node_boxes(ng)
    n_ne = route_into_nodes(ng, placed, hplaced, boxes)   # nested staircase entries FIRST
    n_hv, n_fb = route_branches(ng, placed, hplaced, boxes)
    n_ia = route_around_nodes(ng)
    declutter_reroutes(ng)
    n_fr = frame_reroutes(ng)                             # parent reroutes to their function frame
    n_sep = separate_frames(ng)                           # R7: resolve band corner-crossings
    if n_sep:
        declutter_reroutes(ng)                            # shifted nodes may cover a gap bend
    return {"local_gis": n_gi, "node_entries": n_ne, "hv": n_hv, "fan": n_fb,
            "around": n_ia, "framed_reroutes": n_fr, "frame_shifts": n_sep}


def eval_positions(obj, m, pid, preview):
    """Evaluated vertex positions (optionally toggling a deform-preview socket)."""
    if pid is not None:
        m[pid] = preview
    obj.update_tag(); bpy.context.view_layer.update()
    dg = bpy.context.evaluated_depsgraph_get(); ev = obj.evaluated_get(dg); me = ev.to_mesh()
    P = [v.co.copy() for v in me.vertices]; ev.to_mesh_clear(); return P


def process_file(fname, save=True, gate=None):
    """Open <fname>.blend, snapshot geometry, run tidy_and_route, verify the mesh
    is unchanged, optionally run an extra `gate(ng) -> (ok, info)`, and save ONLY
    if BOTH the geometry check and the gate pass.

    The `gate` hook is how the two halves of the suite verify each other:
    run_pipeline passes a gate that runs `layout_audit`, so routing-correctness
    (geometry unchanged) AND readability rules (R1-R5) must both hold before the
    file is committed. Returns a stats dict."""
    bpy.ops.wm.open_mainfile(filepath=os.path.join(GEO, fname + ".blend"))
    ng = bpy.data.node_groups[fname]
    obj = next(o for o in bpy.data.objects if any(md.type == 'NODES' and md.node_group == ng for md in o.modifiers))
    m = next(md for md in obj.modifiers if md.node_group == ng)
    ids = {it.name: it.identifier for it in ng.interface.items_tree if getattr(it, 'item_type', '') == 'SOCKET' and it.in_out == 'INPUT'}
    pid = ids.get("Show Deformation Preview"); pval = m.get(pid) if pid else None

    base_on, base_off = eval_positions(obj, m, pid, True), eval_positions(obj, m, pid, False)
    stats = tidy_and_route(ng)
    aft_on, aft_off = eval_positions(obj, m, pid, True), eval_positions(obj, m, pid, False)
    if pid is not None: m[pid] = pval

    def eq(p, q): return len(p) == len(q) and all((a - b).length < 1e-6 for a, b in zip(p, q))
    def eqset(p, q):
        k = lambda P: sorted((round(c.x, 5), round(c.y, 5), round(c.z, 5)) for c in P)
        return len(p) == len(q) and k(p) == k(q)
    geom_ok = eq(base_off, aft_off) and eqset(base_on, aft_on)

    gate_ok, gate_info = True, None
    if gate is not None:
        gate_ok, gate_info = gate(ng)

    ok = geom_ok and gate_ok
    saved = False
    if ok and save:
        bpy.ops.wm.save_mainfile(); saved = True
    return {"fname": fname, "geom_ok": geom_ok, "gate_ok": gate_ok, "saved": saved,
            "stats": stats, "gate_info": gate_info}


def _cli():
    targets = TARGETS
    if "--" in sys.argv:                       # run on a subset: blender ... -- GN_Spherify GN_Twist
        sel = sys.argv[sys.argv.index("--") + 1:]
        if sel: targets = sel
    for fname in targets:
        r = process_file(fname, save=True)
        s = r["stats"]
        tag = "OK  " if r["saved"] else ("GEOMFAIL" if not r["geom_ok"] else "NOTSAVED")
        print(f"[{tag}] {fname:16} local-GIs={s['local_gis']} hv={s['hv']} fan={s['fan']} "
              f"around={s['around']} geom_ok={r['geom_ok']} -> {'saved' if r['saved'] else 'NOT saved'}")
    sys.stdout.flush(); os._exit(0)


if __name__ == "__main__":
    _cli()
