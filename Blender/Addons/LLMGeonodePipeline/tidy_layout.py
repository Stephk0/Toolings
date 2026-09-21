import bpy, sys, os
from collections import defaultdict
GEO = r"D:\Stephko_Tooling\Toolings\Blender\Geonodes"
TARGETS = ["GN_Twist", "GN_Taper", "GN_Wave", "GN_Bend", "GN_Stretch",
           "GN_Inflate", "GN_Smooth", "GN_RandomizePosition",
           "GN_Triangulate", "GN_Subdivide", "GN_Wireframe", "GN_RadialArray",
           "GN_Displace", "GN_MeshBoolean", "GN_Cast", "GN_Scatter",
           "GN_ConvexHull", "GN_BoundingBox", "GN_FlipFaces", "GN_SetMaterial",
           "GN_DualMesh", "GN_VoxelRemesh", "GN_AutoSmooth", "GN_PointsToSpheres",
           "GN_NormalTransfer", "GN_Delete",
           "GN_Erosion", "GN_NoiseDisplace", "GN_VoronoiDisplace", "GN_ShearGeometry",
           "GN_Mosaic", "GN_RandomizeMeshElements", "GN_VertexDataComposer"]

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
    # Escape rows are REMEMBERED. The old code sent every reroute escaping a given node to the
    # same `ny + M + 10`, so two different trunks squeezing past one node landed on an identical
    # Y -- a 0.0px collinear pair manufactured AFTER the lane allocator had already placed them
    # clear (this was the last surviving R12 failure on GN_Erosion / GN_VertexDataComposer).
    taken = []

    def free(y, x):
        return not any(abs(y - ty) < LANE_MIN * 2 and abs(x - tx) < 400 for ty, tx in taken)

    for _ in range(3):
        for r in rr:
            for nx, ny, w, h in boxes:
                if nx - M <= r.location.x <= nx + w + M and ny - h - M <= r.location.y <= ny + M:
                    up, down = ny + M + 10, ny - h - M - 10
                    cands = [up, down] if abs(up - r.location.y) <= abs(down - r.location.y)                         else [down, up]
                    y = None
                    for base in cands:                     # step off an already-used escape row
                        for k in range(0, 12):
                            for d in ((1, -1) if base == up else (-1, 1)):
                                cy = base + k * LANE_MIN * 2 * d
                                if free(cy, r.location.x):
                                    y = cy; break
                            if y is not None: break
                        if y is not None: break
                    r.location.y = y if y is not None else cands[0]
                    taken.append((r.location.y, r.location.x))
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

# ---------------------------------------------------------------------------
#  Lane allocator -- the ONE ledger every drawn wire segment goes through
# ---------------------------------------------------------------------------
NODE_CLEAR = 30.0   # px of gutter a wire lane keeps from any node body (not a hairline)
LANE_STEP  = 28.0   # px between parallel lanes searched by the allocator
LANE_MIN   = 11.0   # hard floor: two lanes are NEVER closer than this (jog fallback)
GUTTER_MAX = 420.0  # corridors wider than this aren't centred (centring would drag the lane away)
MIN_TILT_RUN = 120.0  # a row may only be nudged if its stubs are at least this long...
MAX_ROW_TILT = 44.0   # ...and never by more than this, so the stub stays a gentle diagonal


class Lanes:
    """The single reservation ledger for wire corridors. Every pass that draws a segment
    ALLOCATES it here, and every segment a pass has no freedom over (socket stubs, trunk
    hops) is still RECORDED here -- so later allocations can see it. No pass may place a
    lane any other way.

    Replaces the old bare `placed`/`hplaced` lists, which only `_vlane`/`_hlane` fed while
    `route_branches`' spread-fan path derived `tap_x` straight from the target's own X and
    never consulted or recorded anything. Measured consequence on SH_ScreenCavity: three
    different signals (normal_diff / Ridge Control / Valley Control) landed on x=6970 and
    again on x=7142, drawing 10 EXACTLY-collinear wire pairs with up to 3453px of shared
    extent -- three wires rendering as one line.

    Three code paths also "gave up and accepted a known clash" when their bounded search ran
    out: `_vlane`'s `minx` snap, the tap escape loop's `tap_x < target_right` guard, and
    `_hlane`'s accept-start fallback. That is what painted 13 buses 2px off a node border.
    Neither failure mode is reachable here: the search is bidirectional, and the last resort
    is a JOG that maximises separation -- worst case a visibly parallel wire, never a hidden
    one."""

    def __init__(self, boxes):
        self.boxes = list(boxes)     # (x, y, w, h) real node bodies -- reroutes/frames excluded
        self.v = []                  # reserved vertical runs   (x, ymin, ymax)
        self.h = []                  # reserved horizontal runs (y, xmin, xmax)
        # The lane search probes hundreds of candidate positions per link; on a 2800-node
        # graph a full box scan per probe dominates the runtime. Sort once and window in.
        self._bx = sorted(self.boxes, key=lambda b: b[0])
        self._xs = [b[0] for b in self._bx]
        self._maxw = max([b[2] for b in self.boxes] or [140.0])
        self._by = sorted(self.boxes, key=lambda b: b[1])
        self._ys = [b[1] for b in self._by]
        self._maxh = max([b[3] for b in self.boxes] or [200.0])

    def _hit_v(self, x, ymin, ymax, pad):
        """_hits_node over the x-window that can possibly reach x."""
        import bisect
        lo = bisect.bisect_left(self._xs, x - pad - self._maxw)
        hi = bisect.bisect_right(self._xs, x + pad)
        for nx, ny, w, h in self._bx[lo:hi]:
            if nx - pad <= x <= nx + w + pad and not (ymax < ny - h - pad or ymin > ny + pad):
                return True
        return False

    def _hit_h(self, y, xmin, xmax, pad):
        import bisect
        lo = bisect.bisect_left(self._ys, y - pad)
        hi = bisect.bisect_right(self._ys, y + pad + self._maxh)
        for nx, ny, w, h in self._by[lo:hi]:
            if ny - h - pad <= y <= ny + pad and not (xmax < nx - pad or xmin > nx + w + pad):
                return True
        return False

    # -- recording -----------------------------------------------------------
    def add_v(self, x, ymin, ymax):
        self.v.append((x, min(ymin, ymax), max(ymin, ymax))); return x

    def add_h(self, y, xmin, xmax):
        self.h.append((y, min(xmin, xmax), max(xmin, xmax))); return y

    def seg(self, p0, p1):
        """Record a segment the caller had no freedom over (exit/entry stubs, trunk hops).
        Diagonals are deliberate DIRECT wires, not lanes -- they aren't recorded."""
        (x0, y0), (x1, y1) = p0, p1
        if abs(x1 - x0) < 6 and abs(y1 - y0) > 20:
            self.add_v((x0 + x1) / 2.0, y0, y1)
        elif abs(y1 - y0) < 6 and abs(x1 - x0) > 20:
            self.add_h((y0 + y1) / 2.0, x0, x1)

    # -- corridors -----------------------------------------------------------
    def _occupied_x(self, ymin, ymax):
        """Merged x-intervals blocked by node bodies over [ymin,ymax], padded by NODE_CLEAR."""
        iv = sorted((nx - NODE_CLEAR, nx + w + NODE_CLEAR) for nx, ny, w, h in self.boxes
                    if not (ymax < ny - h or ymin > ny))
        out = []
        for a, b in iv:
            if out and a <= out[-1][1]:
                out[-1][1] = max(out[-1][1], b)
            else:
                out.append([a, b])
        return out

    @staticmethod
    def _centre(lo, hi, want_x):
        if hi - lo <= 0:
            return want_x
        if hi - lo > GUTTER_MAX:                  # wide-open space: stay near where we wanted
            return min(max(want_x, lo + NODE_CLEAR), hi - NODE_CLEAR)
        return (lo + hi) / 2.0

    def gutter(self, want_x, ymin, ymax):
        """Snap want_x to the CENTRE of the free corridor it falls in. A lane that merely
        clears a node by the pad still reads as part of that node's outline (the 2px-off-the-
        border buses); centring it in the gap is what makes a bus legible as its own line."""
        occ = self._occupied_x(ymin, ymax)
        prev = None
        for a, b in occ:
            if want_x < a:
                return self._centre(prev if prev is not None else want_x - GUTTER_MAX, a, want_x)
            if a <= want_x <= b:                  # inside a node: take the nearer free corridor
                nxt = next((c for c, _ in occ if c > b), b + GUTTER_MAX)
                if prev is not None and (want_x - prev) < (nxt - want_x):
                    return self._centre(prev, a, want_x)
                return self._centre(b, nxt, want_x)
            prev = b
        return self._centre(prev if prev is not None else want_x - GUTTER_MAX,
                            want_x + GUTTER_MAX, want_x)

    # -- allocation ----------------------------------------------------------
    def _v_clash(self, x, ymin, ymax):
        if any(abs(x - vx) < LANE_STEP and not (ymax < lo - 14 or ymin > hi + 14)
               for vx, lo, hi in self.v):
            return True
        return self._hit_v(x, ymin, ymax, NODE_CLEAR)

    def h_run_clash(self, y, xmin, xmax):
        """Clash against other recorded RUNS only. The full `_h_clash` also rejects node
        bodies, which a leg leaving a socket always touches -- useless for deciding whether
        a fixed-Y exit leg needs to drop to an allocated lane."""
        return any(abs(y - vy) < LANE_STEP and not (xmax < lo - 14 or xmin > hi + 14)
                   for vy, lo, hi in self.h)

    def _h_clash(self, y, xmin, xmax):
        if any(abs(y - vy) < LANE_STEP and not (xmax < lo - 14 or xmin > hi + 14)
               for vy, lo, hi in self.h):
            return True
        return self._hit_h(y, xmin, xmax, NODE_CLEAR)

    def vlane(self, want_x, ymin, ymax, minx=None, maxx=None):
        """A clear vertical-bus X for [ymin,ymax], searched BOTH ways from the corridor centre
        and always recorded. `minx`/`maxx` bound the window; an impossible window degrades to
        a jog, never to a silent overlap."""
        if minx is not None and maxx is not None and maxx < minx + 4:
            maxx = None                            # impossible window -> unbounded on the right
        base = self.gutter(want_x, ymin, ymax)
        if minx is not None: base = max(base, minx)
        if maxx is not None: base = min(base, maxx)

        def ok(x):
            if minx is not None and x < minx: return False
            if maxx is not None and x > maxx: return False
            return not self._v_clash(x, ymin, ymax)

        if ok(base):
            return self.add_v(base, ymin, ymax)
        for k in range(1, 260):                    # nearest clear lane, left side first
            for d in (-1, 1):
                x = base + LANE_STEP * k * d
                if ok(x):
                    return self.add_v(x, ymin, ymax)
        return self.add_v(self._jog(base, ymin, ymax, minx, maxx, vertical=True), ymin, ymax)

    def hlane(self, want_y, xmin, xmax, ddir=-1):
        """A clear horizontal-trunk Y for [xmin,xmax]. Bidirectional (a down-only search gets
        shoved past a whole lower row when a short hop up into the header gap was clear)."""
        if not self._h_clash(want_y, xmin, xmax):
            return self.add_h(want_y, xmin, xmax)
        for k in range(1, 260):
            for d in (ddir, -ddir):
                y = want_y + LANE_STEP * k * d
                if not self._h_clash(y, xmin, xmax):
                    return self.add_h(y, xmin, xmax)
        return self.add_h(self._jog(want_y, xmin, xmax, None, None, vertical=False), xmin, xmax)

    def _jog(self, base, lo_span, hi_span, lim_lo, lim_hi, vertical):
        """Last resort. NEVER snap onto an occupied lane -- that snap IS the bug this replaces.
        Scan a window at LANE_MIN granularity and take the position with the greatest clearance
        from every conflicting run, so the worst case is a visibly parallel wire."""
        runs = self.v if vertical else self.h
        conf = [c for c, lo, hi in runs if not (hi_span < lo - 14 or lo_span > hi + 14)]
        if vertical:
            hit = lambda p: self._hit_v(p, lo_span, hi_span, 8)
        else:
            hit = lambda p: self._hit_h(p, lo_span, hi_span, 8)
        best, best_d = base, -1e18
        for i in range(-180, 181):
            p = base + i * LANE_MIN
            if lim_lo is not None and p < lim_lo: continue
            if lim_hi is not None and p > lim_hi: continue
            d = min([abs(p - c) for c in conf] or [1e9])
            if hit(p): d -= 1e6                    # still prefer not to sit on a node
            d -= abs(i) * 0.01                     # tie-break: stay near where we wanted
            if d > best_d:
                best, best_d = p, d
        return best


def _route_back(ng, fs, ts, a, b, L):
    """Target sits LEFT of (or under) its source -> can't flow rightward. Route exit-right, drop to
    a clear horizontal lane BELOW, run left to just-left-of-target, rise into it. 4 reroutes, fully
    orthogonal, approaches the target from the left so the wire never overshoots/self-crosses."""
    a_right = a.location.x + (a.width or 140)
    ay, by = _ymid(a), _ymid(b)
    xlo, xhi = min(b.location.x - 35, a_right + 25), max(b.location.x - 35, a_right + 25)
    lane_y = L.hlane(min(ay, by) - 70, xlo, xhi, ddir=-1)
    rx_out = L.vlane(a_right + 25, min(lane_y, ay), max(lane_y, ay), minx=a_right + 20)
    rx_in = L.vlane(b.location.x - 35, min(lane_y, by), max(lane_y, by), maxx=b.location.x - 20)
    P0 = ng.nodes.new("NodeReroute"); P0.location = (rx_out, ay)
    P1 = ng.nodes.new("NodeReroute"); P1.location = (rx_out, lane_y)
    P2 = ng.nodes.new("NodeReroute"); P2.location = (rx_in, lane_y)
    P3 = ng.nodes.new("NodeReroute"); P3.location = (rx_in, by)
    ng.links.new(fs, P0.inputs[0]); ng.links.new(P0.outputs[0], P1.inputs[0])
    ng.links.new(P1.outputs[0], P2.inputs[0]); ng.links.new(P2.outputs[0], P3.inputs[0])
    ng.links.new(P3.outputs[0], ts)
    L.seg((a_right, ay), (rx_out, ay))                 # exit stub
    L.seg((rx_in, by), (b.location.x, by))             # entry stub


def _route_v(ng, fs, ts, a, b, L):
    a_right = a.location.x + (a.width or 140)
    if b.location.x < a_right + 50:                 # backward / overshoot risk -> over-under route
        _route_back(ng, fs, ts, a, b, L); return
    soy = _socket_y(a, fs, False); diy = _socket_y(b, ts, True)  # enter/leave AT socket height
    rx = L.vlane(b.location.x - 140, min(soy, diy), max(soy, diy),
                 minx=a_right + 25 + LANE_STEP, maxx=b.location.x - 20)
    # E = framed EXIT reroute right of the source; A = gap bend; B = framed ENTRY at target socket
    ex = a_right + 25
    E = ng.nodes.new("NodeReroute"); E.location = (ex, soy)
    ng.links.new(fs, E.inputs[0])
    L.seg((a_right, soy), (ex, soy))                   # short exit stub, no freedom
    if L.h_run_clash(soy, ex, rx):
        # The leg from the source socket across to the turn lane is a LANE, not a stub, and
        # its Y is pinned to the socket. When something already occupies that line, drop to
        # an allocated one instead of sharing it (SH_ScreenCavity: this leg ran 115px along a
        # direct wire whose nodes sit 7px off the same row).
        ly = L.hlane(soy, ex, rx)
        C = ng.nodes.new("NodeReroute"); C.location = (ex, ly)
        ng.links.new(E.outputs[0], C.inputs[0]); E = C
        L.add_v(ex, min(soy, ly), max(soy, ly))
        soy = ly
    else:
        L.add_h(soy, ex, rx)                           # allocate the leg we are about to draw
    A = ng.nodes.new("NodeReroute"); A.location = (rx, soy)
    B = ng.nodes.new("NodeReroute"); B.location = (rx, diy)
    ng.links.new(E.outputs[0], A.inputs[0])
    ng.links.new(A.outputs[0], B.inputs[0]); ng.links.new(B.outputs[0], ts)
    L.seg((rx, diy), (b.location.x, diy))              # entry stub

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

def route_into_nodes(ng, L):
    """Coordinate ALL cross-band wires entering the SAME node into a nested, non-crossing
    staircase (subway-map): each entry reroute sits at its target SOCKET's Y (staggered), and
    lanes nest so the TOPMOST socket turns in the lane closest to the node, lower sockets in
    lanes progressively further left. This replaces `_route_v`'s old habit of parking every
    entry reroute at node_y-35 (one horizontal row -> crossing taps). Rerouted links become
    source->reroute->reroute->target, so route_branches (which skips reroute endpoints) leaves
    them alone. Run BEFORE route_branches."""
    from collections import defaultdict
    boxes = L.boxes
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
            a_right = a.location.x + (a.width or 140)
            want_x = base_x - k * LANE_STEP        # topmost=k0=nearest node; lower sockets further left
            lane_x = L.vlane(want_x, min(soy, sy), max(soy, sy),
                             minx=a_right + 25 + LANE_STEP, maxx=b.location.x - 20)
            for ll in list(ng.links):              # drop the original direct link
                if ll.from_socket == fs and ll.to_socket == ts:
                    ng.links.remove(ll); break
            # E = framed EXIT reroute just right of the source (inside source frame);
            # A = gap bend at the drop lane; B = framed ENTRY at the target socket.
            E = ng.nodes.new("NodeReroute"); E.location = (a_right + 25, soy)
            A = ng.nodes.new("NodeReroute"); A.location = (lane_x, soy)
            B = ng.nodes.new("NodeReroute"); B.location = (lane_x, sy)
            ng.links.new(fs, E.inputs[0]); ng.links.new(E.outputs[0], A.inputs[0])
            ng.links.new(A.outputs[0], B.inputs[0]); ng.links.new(B.outputs[0], ts)
            L.seg((a_right, soy), (lane_x, soy))   # exit stub
            L.seg((lane_x, sy), (b.location.x, sy))  # entry stub
            n_routed += 1
    return n_routed


def route_branches(ng, L):
    """Group EVERY real link by its SOURCE socket, then route each source ONCE:
      - 1 target, cross-frame -> orthogonal H-V-H (2 reroutes in a clear lane).
      - 1 target, same-frame  -> leave direct (route_around handles any node crossing).
      - >=2 targets           -> ONE SHARED daisy-chained branch off the source (never duplicate
        reroutes on the same line): STACKED targets -> a vertical bus; SPREAD targets -> a horizontal
        trunk at source height that splits off a tap per column then continues right. Targets sharing
        a row/column reuse the SAME reroute (deduped) so no two reroutes ever land on one spot.

    Every lane here -- including the spread fan's per-target drop legs -- is allocated through
    `L`. The drop legs used to be derived from the target's own X with no ledger at all, which
    is why two fans feeding one column drew on top of each other (SH_ScreenCavity)."""
    boxes = L.boxes
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
            _route_v(ng, fs, ts, a, b, L); n_hv += 2
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
            _route_back(ng, fs, sock[(b, tid)], a, b, L); n_fan += 1
        tg = [(b, tid) for b, tid in tg if b.location.x >= a_right + 50]
        if not tg: continue
        if len(tg) == 1:                                        # one forward target left -> simple H-V-H
            b, tid = tg[0]
            if _adjacent_direct(a, fs, b, sock[(b, tid)], boxes):
                ng.links.new(fs, sock[(b, tid)])                # adjacent + clear: restore the direct wire
            else:
                _route_v(ng, fs, sock[(b, tid)], a, b, L); n_hv += 2
            continue
        ys = [b.location.y for b, _ in tg]; xs = [b.location.x for b, _ in tg]
        if max(xs) - min(xs) <= 200:
            # ---- STACKED: one vertical bus, reroutes deduped per ROW ----
            ymin = min(ys + [a.location.y]) - 35; ymax = max(ys + [a.location.y])
            soy0 = _socket_y(a, fs, False)
            bus_x = L.vlane(min(xs) - 45, min(ymin, soy0), max(ymax, soy0),
                            minx=a_right + 25 + LANE_STEP, maxx=min(xs) - 20)
            rows = defaultdict(list)
            for b, tid in tg: rows[round(_ymid(b) / 8) * 8].append((b, tid))
            # The run from the source across to the bus can be thousands of px long -- that is a
            # LANE, not a stub, so it goes through the ledger like any other. Parking R0 at the
            # source's socket Y instead put two buses whose sources happened to share a socket
            # row on one line for 3220px (SH_ScreenCavity: Camera Right vs Nx/Ny, both at y=-88).
            ex = a_right + 25
            trunk_y = L.hlane(soy0, ex, bus_x)
            if abs(trunk_y - soy0) < 2.0:                       # already clear: no bend needed
                R0 = ng.nodes.new("NodeReroute"); R0.location = (bus_x, soy0)
                ng.links.new(fs, R0.inputs[0])
            else:
                E = ng.nodes.new("NodeReroute"); E.location = (ex, soy0)
                C = ng.nodes.new("NodeReroute"); C.location = (ex, trunk_y)
                R0 = ng.nodes.new("NodeReroute"); R0.location = (bus_x, trunk_y)
                ng.links.new(fs, E.inputs[0]); ng.links.new(E.outputs[0], C.inputs[0])
                ng.links.new(C.outputs[0], R0.inputs[0])
                L.seg((a_right, soy0), (ex, soy0))              # short exit stub
                L.add_v(ex, min(soy0, trunk_y), max(soy0, trunk_y))
            # Chain monotonically AWAY from R0 in each direction, splitting at R0 when it
            # sits between its rows. Always chaining to the TOPMOST row first made the bus
            # climb past every row and descend back down through its own line whenever the
            # source sat below its targets -- GN_Erosion_3D drew a 936px retrace on one X
            # that no amount of lane separation could fix, because it was one wire crossing
            # itself. A reroute output may fan, so the split costs nothing.
            r0y = R0.location.y
            up = sorted([ry for ry in rows if ry > r0y])                  # away, ascending
            down = sorted([ry for ry in rows if ry <= r0y], reverse=True)  # away, descending
            for seq in (down, up):
                prev = R0
                for ry in seq:
                    R = ng.nodes.new("NodeReroute"); R.location = (bus_x, ry)
                    ng.links.new(prev.outputs[0], R.inputs[0]); prev = R
                    for b, tid in rows[ry]:
                        ng.links.new(R.outputs[0], sock[(b, tid)]); n_fan += 1
        else:
            # ---- SPREAD: horizontal trunk flowing strictly RIGHT, one tap per target ----
            # MONOTONIC: each drop lane is bounded below by the previous tap, so the trunk only
            # ever marches right and never loops back. The lane itself comes from the ledger,
            # which is what keeps two fans over the same column off one another's line.
            tg.sort(key=lambda bt: bt[0].location.x)
            soy0 = _socket_y(a, fs, False)
            tx0 = a_right + 25; txmax = max(xs) + 60
            trunk_y = L.hlane(soy0, tx0, txmax)
            E = ng.nodes.new("NodeReroute"); E.location = (tx0, trunk_y); ng.links.new(fs, E.inputs[0])
            L.seg((a_right, soy0), (tx0, trunk_y))              # exit stub, AS DRAWN
            prev = E; last_x = tx0
            for b, tid in tg:
                ty = _socket_y(b, sock[(b, tid)], True)
                lo, hi = min(ty, trunk_y) - 6, max(ty, trunk_y) + 6
                tap_x = L.vlane(b.location.x - 45, lo, hi,
                                minx=last_x + LANE_STEP, maxx=b.location.x - 20)
                last_x = tap_x
                T = ng.nodes.new("NodeReroute"); T.location = (tap_x, trunk_y)
                ng.links.new(prev.outputs[0], T.inputs[0]); prev = T   # trunk marches right
                D = ng.nodes.new("NodeReroute"); D.location = (tap_x, ty)
                ng.links.new(T.outputs[0], D.inputs[0]); ng.links.new(D.outputs[0], sock[(b, tid)])
                L.seg((tap_x, ty), (b.location.x, ty))          # entry stub
                n_fan += 2
    return n_hv, n_fan


def route_around_nodes(ng, L):
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
    for a, fid, b, tid, top in cand:
        fs, ts = osock(a, fid), isock(b, tid)
        for l in list(ng.links):
            if l.from_socket == fs and l.to_socket == ts: ng.links.remove(l); break
        x1 = a.location.x + (a.width or 140) + 22
        x2 = b.location.x - 30
        # `top + (i % 6) * 24` guaranteed a collision on the 7th over-the-row detour and
        # reserved nothing; the ledger picks the nearest genuinely free trunk instead.
        ry = L.hlane(top, min(x1, x2), max(x1, x2), ddir=1)
        R1 = ng.nodes.new("NodeReroute"); R1.location = (x1, ry)
        R2 = ng.nodes.new("NodeReroute"); R2.location = (x2, ry)
        ng.links.new(fs, R1.inputs[0]); ng.links.new(R1.outputs[0], R2.inputs[0]); ng.links.new(R2.outputs[0], ts)
        L.seg((a.location.x + (a.width or 140), _ymid(a)), (x1, _ymid(a)))
        L.seg((x2, _ymid(b)), (b.location.x, _ymid(b)))
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



def _lane_groups(ng, axis):
    """Connected groups of reroutes sharing a column (axis 'V') or a row (axis 'H') -- the unit
    that can be slid sideways/up without bending anything, since every run inside the group
    moves with it."""
    same = (lambda A, B: abs(A.location.x - B.location.x) < 3) if axis == 'V' else \
           (lambda A, B: abs(A.location.y - B.location.y) < 3)
    rr = [n for n in ng.nodes if n.bl_idname == 'NodeReroute']
    idx = {n.name: i for i, n in enumerate(rr)}
    par = list(range(len(rr)))

    def find(i):
        while par[i] != i:
            par[i] = par[par[i]]; i = par[i]
        return i

    for l in ng.links:
        A, B = l.from_node, l.to_node
        if A.name in idx and B.name in idx and same(A, B):
            ra, rb = find(idx[A.name]), find(idx[B.name])
            if ra != rb: par[ra] = rb
    grp = defaultdict(list)
    for n in rr:
        grp[find(idx[n.name])].append(n)
    return list(grp.values())


def separate_wire_lanes(ng, iters=8):
    """R12/R13 SAFETY NET -- runs LAST, on the graph as actually drawn.

    Allocation happens before `declutter_reroutes` nudges reroutes and before `separate_frames`
    shifts whole bands, so a lane that was clear when it was reserved can still end up on
    another lane, or on a node's border, by the time the file is saved. This re-measures the
    real reroute-to-reroute runs and slides whole same-column / same-row groups apart until no
    two wires are collinear (R12) and no vertical run is painted on a node outline (R13).

    Immovable obstacles matter as much as movable lanes: a trunk laid 7px off a DIRECT
    node-to-node wire is exactly as unreadable as two trunks on one line, and that wire can
    never move, so it enters the ledger with a zero travel budget.

    A group's travel budget follows from what a shift would bend. The stubs joining it to real
    node sockets run horizontally, so sliding a COLUMN sideways only lengthens them -- free,
    unless a stub is itself vertical. Sliding a ROW up/down tilts every stub, so it is allowed
    only over stubs long enough (MIN_TILT_RUN) to absorb the rise as a gentle diagonal, and
    never by more than MAX_ROW_TILT."""
    boxes = node_boxes(ng)
    links = list(ng.links)
    # link index by node name -- rebuilt per pass, not per group (this pass runs on graphs with
    # thousands of links; the naive per-group scan was O(groups x links) x iters x axes)
    touch = defaultdict(list)
    for l in links:
        touch[l.from_node.name].append(l)
        touch[l.to_node.name].append(l)
    moved = 0
    for axis in ('V', 'H'):
        vertical = axis == 'V'
        # Groups move as a unit and never merge or split, so membership is computed ONCE.
        groups = _lane_groups(ng, axis)
        def obstacle(x0, y0, x1, y1, owners):
            """An axis-aligned wire the repair cannot move but must not ignore."""
            if vertical and abs(x1 - x0) < 6 and abs(y1 - y0) > 20:
                return [None, (x0 + x1) / 2.0, min(y0, y1), max(y0, y1), (0.0, 0.0), owners]
            if not vertical and abs(y1 - y0) < 6 and abs(x1 - x0) > 20:
                return [None, (y0 + y1) / 2.0, min(x0, x1), max(x0, x1), (0.0, 0.0), owners]
            return None

        node_wires = []                         # direct node-to-node: fixed forever
        for l in links:
            A, B = l.from_node, l.to_node
            if A.bl_idname == 'NodeReroute' or B.bl_idname == 'NodeReroute':
                continue
            o = obstacle(A.location.x + (A.width or 140), _socket_y(A, l.from_socket, False),
                         B.location.x, _socket_y(B, l.to_socket, True), frozenset())
            if o: node_wires.append(o)
        for _ in range(iters):
            spans = list(node_wires)
            # Reroute-to-node stubs move WITH their group, so they are rebuilt every pass and
            # tagged with their owner -- a group must not flee its own stub. Without them the
            # repair was blind to a trunk laid 3.5px off an entry stub (GN_Erosion_3D).
            for l in links:
                A, B = l.from_node, l.to_node
                ar, br = A.bl_idname == 'NodeReroute', B.bl_idname == 'NodeReroute'
                if ar == br:
                    continue
                if ar:
                    o = obstacle(A.location.x, A.location.y,
                                 B.location.x, _socket_y(B, l.to_socket, True), frozenset([A.name]))
                else:
                    o = obstacle(A.location.x + (A.width or 140), _socket_y(A, l.from_socket, False),
                                 B.location.x, B.location.y, frozenset([B.name]))
                if o: spans.append(o)
            for g in groups:
                names = set(n.name for n in g)
                seen = set(); runs = []
                for nm in names:
                    for l in touch[nm]:
                        if l.from_node.name in names and l.to_node.name in names \
                                and id(l) not in seen:
                            seen.add(id(l)); runs.append((l.from_node, l.to_node))
                key = (lambda n: n.location.y) if vertical else (lambda n: n.location.x)
                perp = (lambda n: n.location.x) if vertical else (lambda n: n.location.y)
                runs = [r for r in runs if abs(key(r[0]) - key(r[1])) > 20]
                if not runs:
                    continue
                vals = [key(n) for pr in runs for n in pr]
                # Travel window [dlo, dhi]. Two separate constraints bound it.
                stubs = []                      # (a) stubs into fixed real-node sockets
                dlo, dhi = -1e9, 1e9            # (b) ORDER of the runs attached to this group
                for nm in names:
                    for l in touch[nm]:
                        for R, O in ((l.from_node, l.to_node), (l.to_node, l.from_node)):
                            if R.name not in names:
                                continue
                            if O.bl_idname != 'NodeReroute':
                                ox = O.location.x + ((O.width or 140) if O is l.from_node else 0.0)
                                stubs.append(abs(R.location.x - ox))
                                continue
                            if O.name in names:
                                continue
                            # A perpendicular neighbour run: sliding this group changes that
                            # run's LENGTH, and pushing past the neighbour REVERSES it. This
                            # repair pass itself reversed a trunk hop that way -- GN_Erosion's
                            # trunk ran 1715 -> 1996 -> 1804 -> 2040, a 192px backtrack that
                            # then read as two wires on one line.
                            if vertical:
                                if abs(R.location.y - O.location.y) > 6:
                                    continue
                                d = R.location.x - O.location.x
                            else:
                                if abs(R.location.x - O.location.x) > 6:
                                    continue
                                d = R.location.y - O.location.y
                            # Only the SIGN must survive -- keep the neighbour run at least
                            # LANE_MIN long. Requiring a full LANE_STEP pinned trunks that had
                            # genuine room and re-broke SH_ScreenCavity.
                            if d > 0:
                                dlo = max(dlo, LANE_MIN - d)
                            elif d < 0:
                                dhi = min(dhi, -LANE_MIN - d)
                            else:
                                dlo, dhi = 0.0, 0.0
                if vertical:
                    if not all(s >= 12.0 for s in stubs):
                        dlo = dhi = 0.0         # a vertical stub would bend
                else:
                    if stubs and min(stubs) < MIN_TILT_RUN:
                        dlo = dhi = 0.0         # stubs too short to absorb a tilt
                    else:
                        dlo = max(dlo, -MAX_ROW_TILT); dhi = min(dhi, MAX_ROW_TILT)
                spans.append([g, perp(g[0]), min(vals), max(vals), (dlo, dhi), frozenset(names)])
            if not spans:
                break

            def bad(c, lo, hi, self_i):
                mine = spans[self_i][5]
                for k in range(len(spans)):
                    if k == self_i or (spans[k][5] & mine):
                        continue                # itself, or a stub that travels with it
                    _g2, c2, lo2, hi2, _b, _o = spans[k]
                    if abs(c - c2) < LANE_MIN * 2 and not (hi < lo2 - 15 or lo > hi2 + 15):
                        return True             # R12: another wire on this line
                if not vertical:
                    return False                # R13 is about vertical runs vs node borders
                for nx, ny, w, h in boxes:
                    if hi < ny - h - 4 or lo > ny + 4:
                        continue
                    if nx - 22 <= c <= nx + w + 22:
                        return True             # R13: on (or hugging) a node border
                return False

            changed = False
            for i in range(len(spans)):
                g, c, lo, hi, win, _own = spans[i]
                dlo, dhi = win
                if dhi - dlo < LANE_MIN or not bad(c, lo, hi, i):
                    continue
                for k in range(1, 60):          # nearest clear line, both directions
                    if k * LANE_MIN > max(dhi, -dlo):
                        break
                    for dd in (-1, 1):
                        nc = c + k * LANE_MIN * dd
                        if not (dlo <= nc - c <= dhi):
                            continue
                        if not bad(nc, lo, hi, i):
                            for n in g:
                                if vertical: n.location.x += nc - c
                                else:         n.location.y += nc - c
                            spans[i][1] = nc
                            moved += 1; changed = True
                            break
                    else:
                        continue
                    break
            if not changed:
                break
    return moved


# ---------------------------------------------------------------------------
#  Importable pipeline API  (used by run_pipeline.py and the __main__ CLI below)
# ---------------------------------------------------------------------------

def seed_direct_wires(ng, L):
    """Record the links the routers will deliberately LEAVE direct.

    They were the last category of drawn segment invisible to the ledger. A direct wire
    occupies its line exactly like a routed lane does, so a trunk could be allocated 7px
    from one and read as sharing it (SH_ScreenCavity: `Ridge Branch +2x -> ridge - valley`
    against a reroute trunk, 115px of co-extent). `_adjacent_direct` is the same predicate
    the routers use to skip a link, so seeding on it cannot drift from their decisions.
    Node positions are fixed by the time this runs, so the answer is already final."""
    fanout = defaultdict(int)
    for l in ng.links:
        if l.from_node.bl_idname not in ('NodeReroute', 'NodeGroupInput'):
            fanout[(l.from_node.name, l.from_socket.identifier)] += 1
    n = 0
    for l in ng.links:
        a, b = l.from_node, l.to_node
        if a.bl_idname in ('NodeReroute', 'NodeGroupInput') or b.bl_idname == 'NodeReroute':
            continue
        # Mirror BOTH of route_branches' skip conditions -- an adjacent clear link, and a
        # same-frame single-target link, which is left direct at ANY length (that second one
        # is the 420px wire the first seeding attempt missed).
        same_frame_single = (fanout[(a.name, l.from_socket.identifier)] == 1
                             and fname_of(a) is not None and fname_of(a) == fname_of(b))
        if not (same_frame_single or _adjacent_direct(a, l.from_socket, b, l.to_socket, L.boxes)):
            continue
        L.seg((a.location.x + (a.width or 140), _socket_y(a, l.from_socket, False)),
              (b.location.x, _socket_y(b, l.to_socket, True)))
        n += 1
    return n


def tidy_and_route(ng):
    """Full deterministic layout pass, mutating `ng` in place:
    dissolve reroutes -> layered tidy (frames as bands) -> localize group inputs
    -> place output rightmost -> orthogonal reroute routing -> declutter.
    No file I/O and no geometry check -- callers own those. Returns a stats dict."""
    dissolve_reroutes(ng)
    tidy_layout(ng)
    n_gi = localize_group_inputs(ng)
    place_output_rightmost(ng)
    L = Lanes(node_boxes(ng))                             # THE ledger -- every lane goes through it
    seed_direct_wires(ng, L)                              # ...including the wires nobody routes
    n_ne = route_into_nodes(ng, L)                        # nested staircase entries FIRST
    n_hv, n_fb = route_branches(ng, L)
    n_ia = route_around_nodes(ng, L)
    declutter_reroutes(ng)
    n_fr = frame_reroutes(ng)                             # parent reroutes to their function frame
    n_sep = separate_frames(ng)                           # R7: resolve band corner-crossings
    if n_sep:
        declutter_reroutes(ng)                            # shifted nodes may cover a gap bend
    n_lane = separate_wire_lanes(ng)                      # R12/R13: re-measure AS DRAWN and fix
    return {"local_gis": n_gi, "node_entries": n_ne, "hv": n_hv, "fan": n_fb,
            "around": n_ia, "framed_reroutes": n_fr, "frame_shifts": n_sep,
            "lane_shifts": n_lane}


def eval_positions(obj, m, pid, preview):
    """Evaluated vertex positions (optionally toggling a deform-preview socket)."""
    if pid is not None:
        m[pid] = preview
    obj.update_tag(); bpy.context.view_layer.update()
    dg = bpy.context.evaluated_depsgraph_get(); ev = obj.evaluated_get(dg); me = ev.to_mesh()
    P = [v.co.copy() for v in me.vertices]; ev.to_mesh_clear(); return P


def own_trees(ng):
    """`ng` plus every LOCAL geometry group it instances, transitively, outermost first.

    A tool is not tidy while its helper groups are a pile at the origin -- a group the
    user can open is a graph the user reads, so it is held to the same R1-R13 bar as the
    tree that instances it. LINKED groups are skipped on purpose: they are owned (and
    tidied, and audited) by the .blend they live in, and a linked datablock cannot be
    edited from here anyway. Groups sitting in the file but not reachable from `ng` are
    somebody else's datablocks -- left alone."""
    seen, order, stack = {ng.name}, [ng], [ng]
    while stack:
        cur = stack.pop()
        for n in cur.nodes:
            sub = getattr(n, "node_tree", None)
            if sub is None or sub.library is not None:
                continue
            if sub.bl_idname != "GeometryNodeTree" or sub.name in seen:
                continue
            seen.add(sub.name)
            order.append(sub)
            stack.append(sub)
    return order


def process_file(fname, save=True, gate=None):
    """Open <fname>.blend, snapshot geometry, run tidy_and_route, verify the mesh
    is unchanged, optionally run an extra `gate(ng) -> (ok, info)`, and save ONLY
    if BOTH the geometry check and the gate pass.

    EVERY local group the tool owns is tidied, not just the tree named after the file --
    see `own_trees`. The geometry snapshot covers them all at once, since the helpers are
    only reachable through the modifier being evaluated.

    The `gate` hook is how the two halves of the suite verify each other:
    run_pipeline passes a gate that runs `layout_audit` on EACH tidied tree, so
    routing-correctness (geometry unchanged) AND readability rules (R1-R13) must both
    hold before the file is committed. `gate(trees) -> (ok, info)`. Returns a stats
    dict."""
    bpy.ops.wm.open_mainfile(filepath=os.path.join(GEO, fname + ".blend"))
    ng = bpy.data.node_groups[fname]
    obj = next(o for o in bpy.data.objects if any(md.type == 'NODES' and md.node_group == ng for md in o.modifiers))
    m = next(md for md in obj.modifiers if md.type == 'NODES' and md.node_group == ng)
    ids = {it.name: it.identifier for it in ng.interface.items_tree if getattr(it, 'item_type', '') == 'SOCKET' and it.in_out == 'INPUT'}
    pid = ids.get("Show Deformation Preview"); pval = m.get(pid) if pid else None

    trees = own_trees(ng)
    base_on, base_off = eval_positions(obj, m, pid, True), eval_positions(obj, m, pid, False)
    stats = tidy_and_route(ng)
    sub_stats = {sub.name: tidy_and_route(sub) for sub in trees[1:]}
    aft_on, aft_off = eval_positions(obj, m, pid, True), eval_positions(obj, m, pid, False)
    if pid is not None: m[pid] = pval

    def eq(p, q): return len(p) == len(q) and all((a - b).length < 1e-6 for a, b in zip(p, q))
    def eqset(p, q):
        k = lambda P: sorted((round(c.x, 5), round(c.y, 5), round(c.z, 5)) for c in P)
        return len(p) == len(q) and k(p) == k(q)
    geom_ok = eq(base_off, aft_off) and eqset(base_on, aft_on)

    gate_ok, gate_info = True, None
    if gate is not None:
        gate_ok, gate_info = gate(trees)

    ok = geom_ok and gate_ok
    saved = False
    if ok and save:
        bpy.ops.wm.save_mainfile(); saved = True
    return {"fname": fname, "geom_ok": geom_ok, "gate_ok": gate_ok, "saved": saved,
            "stats": stats, "sub_stats": sub_stats, "trees": [t.name for t in trees],
            "gate_info": gate_info}


def _cli():
    targets = TARGETS
    if "--" in sys.argv:                       # run on a subset: blender ... -- GN_Twist GN_Taper
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
