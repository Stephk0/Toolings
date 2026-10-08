"""polish_layout.py -- the optional second pass: re-verify a tidied graph AS DRAWN and fix
the wire kinks the tidy engine can't see.

Why a separate pass
-------------------
`tidy_layout` runs headless, so it never knows where a socket really is: `_socket_y`
estimates the height from socket counts, and that estimate misses vector sliders,
dropdown buttons (Math, Compare, Switch types), group-node panels and multi-input
sockets. The router parks the entry reroute at the ESTIMATED socket Y, so the last hop
into the socket is a short diagonal -- the kink "before the connection goes into the
node". `route_around_nodes` / `_route_back` draw their stubs at a fixed `_ymid` guess and
kink the same way on exit and entry.

Blender draws every socket at a known position; Python just has no API for it. This
module reads it from the socket's runtime data (`bNodeSocket.runtime->location`):

  * the offset of `runtime` inside `bNodeSocket` comes from the file's own SDNA (exact,
    follows Blender's struct layout on every version), and
  * the offset of `location` inside the runtime struct is CALIBRATED on the tree's own
    reroutes, whose socket location is by definition the reroute's location.

If either step fails (headless, tree not drawn yet, a Blender that moved the field),
`SocketLocator` raises `NotDrawn` and nothing is changed -- the pass never guesses.

What it checks and fixes
------------------------
P1 orthogonal wires: every link that touches a reroute must be purely horizontal or
purely vertical as drawn (tolerance `TOL`). A reroute->socket link is an ENTRY, a
socket->reroute link an EXIT, reroute->reroute a LANE.

Fix, per horizontal run of reroutes (reroutes chained by H links, plus the real sockets
they touch):
  - every socket agrees -> the whole run slides onto that Y (only Y moves, so every V leg
    stays vertical).
  - sockets disagree -> slide only within `SNAP_MAX`, output sockets first (the source
    defines the line), and JOG the rest: a new reroute at the member's X and the socket's
    Y, so the stub leaves/enters horizontally and the step sits on a vertical line. A jog
    that would hug the node pulls the run end out to `JOG_CLEAR`, stepping by `JOG_STEP`
    when that X is another lane.
Vertical runs that drifted apart in X are re-aligned to their majority X.

Gate, per run: a change is kept only if the P1 kink count drops and no BLOCKING
`layout_audit` rule gets worse; otherwise that run is reverted and the next plan tried.
The logical links are compared once at the end (a mismatch reverts everything). The CLI
also checks evaluated geometry and saves only with `--save`.

Usage
-----
Needs a DRAWN node editor, so it runs in a GUI Blender, never `--background`:

  # scripted: opens a window, polishes every tree the tool owns, quits
  blender --factory-startup <Geonodes/GN_X.blend> --python polish_layout.py -- GN_X [--save] [--check]

  # live session (after prepare_capture.prepare(tree=...)):
  import polish_layout; polish_layout.print_result(polish_layout.polish_live(ng))

`--check` only measures and reports (no changes). Run it after `run_pipeline.py`; it is
not part of the default pipeline.
"""

import bpy, sys, os, ctypes, struct, tempfile
from collections import defaultdict

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import layout_audit
import tidy_layout

TOL = 1.0          # px (node space): a link off-axis by more than this in BOTH x and y is a kink
SNAP_MAX = 30.0    # with DISAGREEING sockets, only slide a run this far (never drag it across)
MIN_JOG_DX = 18.0  # never jog when the reroute sits closer than this to the socket (no room)
JOG_CLEAR = 36.0   # a jog's vertical leg keeps this far off the node (> layout_audit.BORDER_CLEAR)
JOG_STEP = 28.0    # ...and steps out by a lane (tidy_layout.LANE_STEP) when that X is taken (R12)
JOG_TRIES = 4
RR = "NodeReroute"


class NotDrawn(RuntimeError):
    """Socket positions are unavailable: headless, not drawn yet, or layout unknown."""


# ---------------------------------------------------------------- socket positions

_RUNTIME_OFF = {}   # bpy.app.version -> offset of bNodeSocket.runtime


def _sdna_member_offset(struct_name, member):
    """Byte offset of `member` in DNA struct `struct_name`, read from an uncompressed copy
    of the current main file's SDNA block (pointer size 8)."""
    tmp = os.path.join(tempfile.gettempdir(), "polish_layout_sdna.blend")
    bpy.ops.wm.save_as_mainfile(filepath=tmp, copy=True, compress=False)
    try:
        data = open(tmp, "rb").read()
    finally:
        try: os.remove(tmp)
        except OSError: pass
    i = data.find(b"SDNANAME")
    if i < 0: return None
    base = i                                  # padding is 4-aligned relative to the block,
    i += 8                                    # not to the file (bit us on half the library)
    al = lambda k: base + ((k - base + 3) & ~3)

    def strings(i, tag=None):
        if tag:
            i = al(i)
            if data[i:i + 4] != tag: raise ValueError(tag)
            i += 4
        n = struct.unpack_from("<i", data, i)[0]; i += 4
        out = []
        for _ in range(n):
            j = data.index(b"\0", i); out.append(data[i:j].decode("latin-1")); i = j + 1
        return out, i
    names, i = strings(i)
    types, i = strings(i, b"TYPE")
    i = al(i)
    if data[i:i + 4] != b"TLEN": return None
    i += 4
    tlen = struct.unpack_from(f"<{len(types)}h", data, i); i += 2 * len(types)
    i = al(i)
    if data[i:i + 4] != b"STRC": return None
    i += 4
    ns = struct.unpack_from("<i", data, i)[0]; i += 4
    for _ in range(ns):
        t, nm = struct.unpack_from("<hh", data, i); i += 4
        mem = []
        for _ in range(nm):
            mt, mn = struct.unpack_from("<hh", data, i); i += 4
            mem.append((mt, names[mn]))
        if types[t] != struct_name: continue
        off = 0
        for mt, nme in mem:
            cnt = 1
            for d in nme.split("[")[1:]: cnt *= int(d.rstrip("]"))
            sz = 8 if nme.startswith(("*", "(*")) else tlen[mt]
            if nme.split("[")[0].lstrip("*") == member: return off
            off += sz * cnt
    return None


class SocketLocator:
    """Drawn socket positions in NODE space (same space as `layout_audit._absloc`)."""

    def __init__(self, ng):
        self.us = bpy.context.preferences.system.ui_scale
        ver = tuple(bpy.app.version)
        if ver not in _RUNTIME_OFF:
            _RUNTIME_OFF[ver] = _sdna_member_offset("bNodeSocket", "runtime")
        self.rt_off = _RUNTIME_OFF[ver]
        if self.rt_off is None:
            raise NotDrawn("bNodeSocket.runtime not found in SDNA")
        self.loc_off = self._calibrate(ng)

    def _floats(self, sock, n=64):
        rt = ctypes.c_void_p.from_address(sock.as_pointer() + self.rt_off).value
        if not rt: raise NotDrawn("socket has no runtime")
        return (ctypes.c_float * n).from_address(rt)

    def _calibrate(self, ng):
        rr = [n for n in ng.nodes if n.bl_idname == RR]
        if not rr:
            raise NotDrawn(f"'{ng.name}' has no reroutes to calibrate on (nothing to polish)")
        cand = None
        for r in rr[:12]:
            ax, ay = layout_audit._absloc(r)
            f = self._floats(r.inputs[0])
            ks = {k for k in range(0, 62) if abs(f[k] - ax * self.us) < 0.6 and abs(f[k + 1] - ay * self.us) < 0.6}
            cand = ks if cand is None else cand & ks
            if not cand: break
        if not cand:
            raise NotDrawn(f"'{ng.name}' is not drawn (socket runtime locations don't match reroutes)")
        return min(cand) * 4

    def pos(self, sock):
        rt = ctypes.c_void_p.from_address(sock.as_pointer() + self.rt_off).value
        x, y = (ctypes.c_float * 2).from_address(rt + self.loc_off)
        return x / self.us, y / self.us


# ---------------------------------------------------------------- measure

def _link_ends(l, P):
    a, b = l.from_node, l.to_node
    p0 = layout_audit._absloc(a) if a.bl_idname == RR else P(l.from_socket)
    p1 = layout_audit._absloc(b) if b.bl_idname == RR else P(l.to_socket)
    return p0, p1


def measure(ng, P):
    """P1: links touching a reroute that are neither horizontal nor vertical as drawn."""
    out = []
    for l in ng.links:
        if not l.is_valid or l.is_muted or l.is_hidden: continue
        a, b = l.from_node, l.to_node
        ra, rb = a.bl_idname == RR, b.bl_idname == RR
        if not (ra or rb): continue
        (x0, y0), (x1, y1) = _link_ends(l, P)
        dx, dy = abs(x1 - x0), abs(y1 - y0)
        if dx > TOL and dy > TOL:
            kind = "lane" if ra and rb else ("entry" if ra else "exit")
            out.append({"kind": kind, "link": f"{a.name}->{b.name}.{l.to_socket.name}",
                        "off": round(min(dx, dy), 1)})
    return out


# ---------------------------------------------------------------- fix

def _set_abs(n, x, y):
    cx, cy = layout_audit._absloc(n)
    n.location = (n.location.x + (x - cx), n.location.y + (y - cy))


def _groups(ng, horizontal):
    """Union reroutes joined by H (or V) reroute->reroute links."""
    parent = {}
    def find(k):
        while parent.setdefault(k, k) != k:
            parent[k] = parent[parent[k]]; k = parent[k]
        return k
    for n in ng.nodes:
        if n.bl_idname == RR: find(n.name)
    for l in ng.links:
        if l.from_node.bl_idname != RR or l.to_node.bl_idname != RR: continue
        (x0, y0), (x1, y1) = layout_audit._absloc(l.from_node), layout_audit._absloc(l.to_node)
        if (abs(y1 - y0) <= abs(x1 - x0)) == horizontal:
            parent[find(l.from_node.name)] = find(l.to_node.name)
    g = defaultdict(list)
    for k in list(parent): g[find(k)].append(k)
    return list(g.values())


class _Journal:
    """Every change the fix makes, so a failed gate can put the graph back exactly."""
    def __init__(self, ng):
        self.ng, self.moves, self.jogs = ng, {}, []

    def move(self, n, x, y):
        self.moves.setdefault(n.name, layout_audit._absloc(n))
        _set_abs(n, x, y)

    def revert(self):
        ng = self.ng
        for jog, fs_node, fs_id, ts_node, ts_id in reversed(self.jogs):
            ng.nodes.remove(ng.nodes[jog])
            fn, tn = ng.nodes[fs_node], ng.nodes[ts_node]
            fs = next(s for s in fn.outputs if s.identifier == fs_id)
            ts = next(s for s in tn.inputs if s.identifier == ts_id)
            ng.links.new(fs, ts)
        for nm, (x, y) in self.moves.items():
            _set_abs(ng.nodes[nm], x, y)


def _jog(ng, J, link, at_x, at_y, parent):
    """Replace `link` with link.from -> NEW reroute at (at_x, at_y) -> link.to."""
    key = _key(link)
    ng.links.remove(link)
    # re-resolve both sockets from their nodes: a socket wrapper taken off the removed link
    # can refuse `links.new` (Blender 5.0 returned None into a reroute input)
    fs = next(s for s in ng.nodes[key[0]].outputs if s.identifier == key[1])
    ts = next(s for s in ng.nodes[key[2]].inputs if s.identifier == key[3])
    N = ng.nodes.new(RR)
    N.parent = parent
    _set_abs(N, at_x, at_y)
    J.jogs.append((N.name,) + key)
    if ng.links.new(fs, N.inputs[0]) is None or ng.links.new(N.outputs[0], ts) is None:
        raise RuntimeError(f"jog relink failed for {key}")
    return N


def _has_v_leg(ng, m):
    """Does reroute `m` link to another reroute vertically (same X)?"""
    mx, my = layout_audit._absloc(m)
    for l in list(m.inputs[0].links) + list(m.outputs[0].links):
        o = l.from_node if l.to_node == m else l.to_node
        if o.bl_idname != RR: continue
        ox, oy = layout_audit._absloc(o)
        if abs(oy - my) > abs(ox - mx): return True
    return False


def _key(l):
    return (l.from_node.name, l.from_socket.identifier, l.to_node.name, l.to_socket.identifier)


def _incident(ng, names):
    """Links touching the named reroutes (missing names skipped), without scanning the tree."""
    out = {}
    for nm in names:
        n = ng.nodes.get(nm)
        if n is None or n.bl_idname != RR: continue
        for l in list(n.inputs[0].links) + list(n.outputs[0].links):
            out[_key(l)] = l
    return out


def _find_link(ng, key):
    """Links are looked up fresh by names/identifiers -- a wrapper held across a jog and
    its revert points at a removed link. Searched on the reroute end (cheap)."""
    rr = key[2] if ng.nodes[key[2]].bl_idname == RR else key[0]
    return _incident(ng, [rr]).get(key)


def _pins(ng, mset, P):
    """Real sockets a reroute run touches: (link key, member name, is_output_pin, x, y)."""
    pins = []
    for key, l in _incident(ng, mset).items():
        if not l.is_valid or l.is_muted: continue
        if l.to_node.name in mset and l.from_node.bl_idname != RR:
            x, y = P(l.from_socket); pins.append((key, l.to_node.name, True, x, y))
        elif l.from_node.name in mset and l.to_node.bl_idname != RR:
            x, y = P(l.to_socket); pins.append((key, l.from_node.name, False, x, y))
    return pins


def _apply_run(ng, J, members, pins, target, clear=JOG_CLEAR):
    """Move the run to `target` Y (None = stay) and jog every socket it then misses.
    Returns True if a jog was pulled out to `clear` (a wider `clear` is worth retrying)."""
    pulled = False
    if target is not None:
        for m in members:
            J.move(m, layout_audit._absloc(m)[0], target)
    run_y = layout_audit._absloc(members[0])[1]
    for key, mname, is_out, sx, sy in pins:
        if abs(sy - run_y) <= TOL: continue
        m, l = ng.nodes[mname], _find_link(ng, key)
        if l is None: continue
        mx, my = layout_audit._absloc(m)
        room = (mx - sx) if is_out else (sx - mx)
        if room < MIN_JOG_DX or (not is_out and l.to_socket.is_multi_input): continue
        if room < clear and not _has_v_leg(ng, m):
            # the jog's vertical leg would hug the node (R13): pull the run end out first --
            # safe only when the member has no vertical leg of its own to keep aligned
            mx = sx + clear if is_out else sx - clear
            J.move(m, mx, my); pulled = True
        # exit: socket -> jog (H) -> member (V);  entry: member (V) -> jog -> socket (H)
        _jog(ng, J, l, mx, sy, m.parent)
    return pulled


def _plans(members, pins):
    """Candidate fixes for one run, best first; None = keep the run and jog."""
    run_y = sum(layout_audit._absloc(m)[1] for m in members) / len(members)
    ys = sorted({round(p[4], 2) for p in pins}, key=lambda y: abs(y - run_y))
    if len(ys) == 1:
        plans = [ys[0]]                  # every socket agrees: the run belongs on that line
    else:
        # the source defines the line; a far slide past disagreeing sockets would drag the
        # run through whatever it was routed around, so only near slides are tried
        outs = [round(p[4], 2) for p in pins if p[2]]
        plans = [y for y in outs + ys if abs(y - run_y) <= SNAP_MAX]
    return list(dict.fromkeys(plans)) + [None]


def fix(ng, P, gate):
    """Per run: try each plan, keep the first one `gate` (a `LocalGate`) accepts, revert
    the others.
    Returns (journals kept, stats)."""
    kept, stats = [], {"slid": 0, "jogs": 0, "realigned": 0, "rejected": 0}
    for grp in _groups(ng, horizontal=True):
        members = [ng.nodes[nm] for nm in grp]
        pins = _pins(ng, set(grp), P)
        run_y = layout_audit._absloc(members[0])[1]
        if not pins or all(abs(p[4] - run_y) <= TOL for p in pins): continue
        done, tried, why = False, False, None
        for target in _plans(members, pins):
            for k in range(JOG_TRIES):
                pre = gate.score(grp)
                J = _Journal(ng)
                pulled = _apply_run(ng, J, members, pins, target, JOG_CLEAR + k * JOG_STEP)
                if not J.moves and not J.jogs: break
                tried = True
                if gate(pre, list(grp) + [j[0] for j in J.jogs]):
                    kept.append(J)
                    stats["slid"] += 1 if target is not None else 0
                    stats["jogs"] += len(J.jogs)
                    done = True; break
                J.revert()
                why = gate.why
                if not pulled: break                      # a wider clearance changes nothing
            if done: break
        if tried and not done:
            stats["rejected"] += 1
            stats.setdefault("why", []).append((grp[0], "all plans", why))
    for grp in _groups(ng, horizontal=False):
        if len(grp) < 2: continue
        xs = [round(layout_audit._absloc(ng.nodes[nm])[0], 1) for nm in grp]
        if max(xs) - min(xs) <= TOL: continue
        best = max(set(xs), key=xs.count)
        pre = gate.score(grp)
        J = _Journal(ng)
        for nm in grp:
            n = ng.nodes[nm]
            if abs(layout_audit._absloc(n)[0] - best) > TOL:
                J.move(n, best, layout_audit._absloc(n)[1])
        if gate(pre, grp): kept.append(J); stats["realigned"] += 1
        else: J.revert(); stats["rejected"] += 1
    return kept, stats


# ---------------------------------------------------------------- pass + gate

def _blocking_score(rep):
    """Per blocking rule: (failed?, size) -- 'got worse' compares these."""
    out = {}
    for k in layout_audit.BLOCKING:
        r = rep[k]
        size = next((len(v) for v in r.values() if isinstance(v, list)), r.get("count", 0))
        out[k] = (r["status"] == "FAIL", size)
    return out


class LocalGate:
    """Blocking-rule check restricted to what one fix touches.

    Re-auditing the whole tree per attempt made the pass O(runs x tree): GN_Mosaic (1206
    kinks) ran past 30 minutes. A fix only moves reroutes and adds jog reroutes, so real
    nodes (R1) never change and every other blocking rule can be scored on the links
    incident to the touched reroutes, against a cache of all other wire segments and
    frame boxes:
      R2  touched reroutes inside a node body
      R7  frames holding a touched reroute vs every other frame
      R12 touched lanes collinear with any lane
      R13 touched vertical lanes along a node border
      P1  kinks on the touched links
    Same measurement and thresholds as `layout_audit` (its `_box` / `_sock_y` / `_lanes`),
    so the full audit the CLI runs at the end agrees -- and that audit stays the authority."""

    def __init__(self, ng, P):
        self.ng, self.P, self.why = ng, P, None
        self.sc = bpy.context.preferences.system.ui_scale
        real = [n for n in ng.nodes if n.bl_idname not in ('NodeFrame', RR)]
        self.boxes = {n.name: layout_audit._box(n, self.sc) for n in real}
        self.segs = {_key(l): self._seg(l) for l in ng.links}
        self.kids = defaultdict(set)
        for n in ng.nodes:
            if n.parent is not None: self.kids[n.parent.name].add(n.name)
        self.fbox = {f.name: self._frame_box(f.name) for f in ng.nodes if f.bl_idname == 'NodeFrame'}

    def _seg(self, l):
        a, b, sc = l.from_node, l.to_node, self.sc
        ax = layout_audit._absloc(a)[0] + (0.0 if a.bl_idname == RR else
                                           ((a.dimensions.x / sc) if a.dimensions.x else (a.width or 140.0)))
        return (ax, layout_audit._sock_y(a, l.from_socket, False, sc),
                layout_audit._absloc(b)[0], layout_audit._sock_y(b, l.to_socket, True, sc), a.name, b.name)

    def _frame_box(self, fname):
        """Like layout_audit's frame_box: bbox of the direct children (reroutes 10x10)."""
        box = None
        for nm in self.kids.get(fname, ()):
            n = self.ng.nodes.get(nm)
            if n is None: continue
            x, y = layout_audit._absloc(n)
            if n.bl_idname == RR:
                w = h = 10.0
            else:
                w = (n.dimensions.x / self.sc) if n.dimensions.x else (n.width or 140.0)
                h = (n.dimensions.y / self.sc) if n.dimensions.y else layout_audit._est_h(n)
            bb = (x, y - h, x + w, y)
            box = bb if box is None else (min(box[0], bb[0]), min(box[1], bb[1]),
                                          max(box[2], bb[2]), max(box[3], bb[3]))
        return box

    def _frames_of(self, names):
        out = set()
        for nm in names:
            n = self.ng.nodes.get(nm)
            if n is not None and n.parent is not None: out.add(n.parent.name)
        return out

    def score(self, names):
        ng = self.ng
        links = _incident(ng, names)
        keys = set(links)
        mine = [self._seg(l) for l in links.values()]
        rest = [sg for k, sg in self.segs.items() if k not in keys]
        r12 = 0
        for vertical in (True, False):
            A, B = layout_audit._lanes(mine, vertical), layout_audit._lanes(rest, vertical)
            for i, (c1, lo1, hi1, a1, b1) in enumerate(A):
                for c2, lo2, hi2, a2, b2 in A[i + 1:] + B:
                    if {a1, b1} & {a2, b2}: continue
                    if min(hi1, hi2) - max(lo1, lo2) >= layout_audit.COLLINEAR_OV \
                            and abs(c1 - c2) < layout_audit.COLLINEAR_DX:
                        r12 += 1
        r13 = 0
        for cx, lo, hi, an, bn in layout_audit._lanes(mine, True):
            for nm, (x0, y0, x1, y1) in self.boxes.items():
                if nm in (an, bn) or hi < y0 - 4 or lo > y1 + 4: continue
                if min(abs(cx - x0), abs(cx - x1)) < layout_audit.BORDER_CLEAR or x0 < cx < x1:
                    r13 += 1
        r2 = 0
        for nm in names:
            n = ng.nodes.get(nm)
            if n is None: continue
            rx, ry = layout_audit._absloc(n)
            r2 += sum(1 for x0, y0, x1, y1 in self.boxes.values()
                      if x0 - 6 <= rx <= x1 + 6 and y0 - 6 <= ry <= y1 + 6)
        r7 = 0
        mine_f = self._frames_of(names)
        fb = dict(self.fbox)
        for f in mine_f: fb[f] = self._frame_box(f)
        for f in sorted(mine_f):
            A = fb.get(f)
            if A is None: continue
            for g, B in fb.items():
                if g == f or B is None or (g in mine_f and g < f): continue
                if layout_audit._intersect(A, B, pad=4):
                    nested = (A[0] <= B[0] and A[1] <= B[1] and A[2] >= B[2] and A[3] >= B[3]) or \
                             (B[0] <= A[0] and B[1] <= A[1] and B[2] >= A[2] and B[3] >= A[3])
                    r7 += not nested
        kinks = 0
        for l in links.values():
            if not l.is_valid or l.is_muted or l.is_hidden: continue
            (x0, y0), (x1, y1) = _link_ends(l, self.P)
            kinks += abs(x1 - x0) > TOL and abs(y1 - y0) > TOL
        return {"R2": r2, "R7": r7, "R12": r12, "R13": r13, "kinks": kinks, "_keys": keys}

    def __call__(self, pre, names):
        """Accept the change just applied to `names` (and commit it to the cache) or say why not."""
        post = self.score(names)
        worse = [f"{k} {pre[k]}->{post[k]}" for k in ("R2", "R7", "R12", "R13") if post[k] > pre[k]]
        if worse or post["kinks"] >= pre["kinks"]:
            self.why = worse or [f"kinks {pre['kinks']}->{post['kinks']}"]
            return False
        for k in pre["_keys"]: self.segs.pop(k, None)
        for k, l in _incident(self.ng, names).items(): self.segs[k] = self._seg(l)
        for nm in names:
            n = self.ng.nodes.get(nm)
            if n is not None and n.parent is not None: self.kids[n.parent.name].add(nm)
        for f in self._frames_of(names): self.fbox[f] = self._frame_box(f)
        return True


def polish(ng, P, apply=True):
    """Measure P1 on `ng` with socket positions `P`, then fix run by run. Each change is
    kept only if its kinks drop and no BLOCKING rule gets worse where it touched the graph
    (`LocalGate`); the logical links are checked once at the end (a mismatch reverts
    everything)."""
    before = measure(ng, P)
    res = {"tree": ng.name, "before": len(before), "kinks_before": before[:12],
           "after": len(before), "kept": False, "stats": {}}
    if not apply or not before:
        return res
    links0 = tidy_layout.logical_links(ng)
    kept, stats = fix(ng, P, LocalGate(ng, P))
    ok = tidy_layout.logical_links(ng) == links0
    if not ok:
        for J in reversed(kept): J.revert()
    after = measure(ng, P)
    res.update(after=len(after), kinks_after=after[:12], kept=ok and bool(kept), stats=stats,
               reverted_because=None if ok else "logical links changed")
    return res


def print_result(res):
    tag = "KEPT" if res["kept"] else ("reverted" if res.get("reverted_because") else "unchanged")
    st = {k: v for k, v in res["stats"].items() if k != "why"}
    print(f"  [polish] {res['tree']}: P1 kinks {res['before']} -> {res['after']} ({tag}) {st}")
    if res.get("reverted_because"):
        print(f"           reverted: {res['reverted_because']}")
    for run, plan, why in res["stats"].get("why", [])[:6]:
        print(f"           rejected {plan:5s} on {run}: {why}")
    for k in res.get("kinks_after", res.get("kinks_before", []))[:8]:
        print(f"           {k['kind']:5s} {k['off']:6.1f}px  {k['link']}")


# ---------------------------------------------------------------- editor plumbing

def _editor():
    for w in bpy.context.window_manager.windows:
        for a in w.screen.areas:
            if a.type == 'NODE_EDITOR':
                return w, a
    for w in bpy.context.window_manager.windows:
        for a in w.screen.areas:
            if a.type == 'VIEW_3D':
                a.type = 'NODE_EDITOR'
                return w, a
    raise NotDrawn("no NODE_EDITOR (or VIEW_3D to repurpose) area")


def draw_tree(ng):
    """Show `ng` in a node editor and force a redraw so socket runtime locations are current."""
    w, a = _editor()
    sp = a.spaces.active
    sp.tree_type = 'GeometryNodeTree'
    sp.pin = True
    sp.node_tree = ng
    region = next(r for r in a.regions if r.type == 'WINDOW')
    with bpy.context.temp_override(window=w, area=a, region=region):
        bpy.ops.node.view_all()
        bpy.ops.wm.redraw_timer(type='DRAW_WIN_SWAP', iterations=1)


def polish_live(ng, apply=True):
    """Draw `ng`, then polish it. Raises NotDrawn when positions can't be read."""
    draw_tree(ng)
    return polish(ng, SocketLocator(ng).pos, apply=apply)


# ---------------------------------------------------------------- CLI (GUI Blender)

def _geometry(obj):
    dg = bpy.context.evaluated_depsgraph_get(); dg.update()
    ev = obj.evaluated_get(dg); me = ev.to_mesh()
    out = sorted((round(v.co.x, 5), round(v.co.y, 5), round(v.co.z, 5)) for v in me.vertices)
    ev.to_mesh_clear()
    return out


def _tool_trees(name):
    """The tree named after the file plus its local groups; for a file without one, every
    local tree a modifier uses (the same roster `run_pipeline` would miss)."""
    ng = bpy.data.node_groups.get(name)
    roots = [ng] if ng else list(dict.fromkeys(
        m.node_group for o in bpy.data.objects for m in o.modifiers
        if m.type == 'NODES' and m.node_group and m.node_group.library is None))
    trees = []
    for r in roots:
        trees += [t for t in tidy_layout.own_trees(r) if t not in trees]
    return trees


def _cli_run(name, save, check):
    code = 1
    try:
        trees = _tool_trees(name)
        objs = [o for o in bpy.data.objects
                if any(m.type == 'NODES' and m.node_group in trees for m in o.modifiers)]
        g0 = [_geometry(o) for o in objs]
        print(f"\n########## Polish: {name} ##########")
        if not trees:
            print("  [polish] no local geometry-node tree in this file")
        results, before = [], {}
        for t in trees:
            try:
                draw_tree(t)
                before[t.name] = _blocking_score(layout_audit.audit(t))
                r = polish(t, SocketLocator(t).pos, apply=not check)
            except NotDrawn as ex:
                print(f"  [polish] {t.name}: skipped -- {ex}")
                continue
            print_result(r); results.append(r)
        geom_ok = [_geometry(o) for o in objs] == g0
        # the gate is "no worse than before": a blocking failure the tidy left behind is
        # reported, but it is not a reason to throw the straightened wires away
        worse = []
        for t in trees:
            if t.name not in before: continue
            draw_tree(t)
            rep = layout_audit.audit(t)
            if layout_audit.print_report(rep):
                sc = _blocking_score(rep)
                worse += [f"{k} [{t.name}]" for k in sc
                          if (sc[k][0] and not before[t.name][k][0]) or sc[k][1] > before[t.name][k][1]]
        print(f"  geometry unchanged: {'PASS' if geom_ok else 'FAIL'}   "
              f"blocking rules worse than before: {worse or 'none'}")
        changed = any(r["kept"] for r in results)
        if save and changed and geom_ok and not worse:
            bpy.ops.wm.save_mainfile()
            print("  => SAVED")
        else:
            print("  => not saved" + ("" if save else " (no --save)") + ("" if changed else " (nothing changed)"))
        code = 0 if geom_ok and not worse else 1
    except Exception:
        import traceback; traceback.print_exc()
    sys.stdout.flush()
    os._exit(code)


def _cli():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    names = [a for a in argv if not a.startswith("--")]
    if bpy.app.background or len(names) != 1:
        print("usage (GUI, not --background): blender --factory-startup <GN_X.blend> "
              "--python polish_layout.py -- GN_X [--save] [--check]")
        sys.stdout.flush(); os._exit(2)
    save, check = "--save" in argv, "--check" in argv
    # the window has to exist and draw once before the editor can be driven
    bpy.app.timers.register(lambda: _cli_run(names[0], save, check), first_interval=1.5)


if __name__ == "__main__":
    _cli()
