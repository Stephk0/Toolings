"""Build GN_SolidifyPlus.blend -- a Geometry Nodes MODIFIER that solidifies a surface like
Blender's Solidify modifier, with the extras a production character mesh needs:

  * rim loops (edge loops around the rim) and a rim shape (Push bulge, or a profile
    curve that can also set the number of rim loops)
  * crease and bevel weight per edge group: inner border, outer border, rim loops and
    rim edges, where the rim edges can be picked by corner type, by angle, or by the
    input's VERTEX CREASE (a creased border vertex creases its rim edge -- the
    "vertex crease fix": the vertex creases are consumed, so they don't pinch the
    subdivided result, unless Keep Vertex Crease is on)
  * face selection (unselected faces pass through untouched), thickness weight (vertex
    group) with zero-weight factor, inset of the outer border, material offsets,
    custom thickness direction.

A clean-room ST3E build: written against the behaviour of the third-party "Solidify
Plus (Vert Crease Fix)" group the example character used, not copied from it.

How it is built
---------------
Topology first, positions last. The selected part S is copied twice (inner + outer
shell); the rim is extruded off the inner shell's border edges (one Extrude Mesh per
rim segment, zero offset), and its last ring is welded onto the outer shell's border
by source-vertex index (GNG_SolidifyPlus_IndexWeld -- exact, never merges unrelated
vertices the way a distance merge would). Every vertex carries its source data
(position, inner/outer offset, rim direction, layer k) as attributes, and ONE Set
Position computes the final shape from them. Edge kinds (inner border / outer border /
rim loop / rim edge) are tagged while building, so crease and bevel weight are a
lookup (GNG_SolidifyPlus_EdgeWeight, used twice).

Run headless:
  "C:\\Program Files\\Blender Foundation\\Blender 5.0\\blender.exe" --background \
      --factory-startup --python build_gn_solidify_plus.py
"""
import bpy, bmesh, sys, os, math
from mathutils import Matrix

GEO  = r"D:\Stephko_Tooling\Toolings\Blender\Geonodes"
NAME = "GN_SolidifyPlus"
PATH = os.path.join(GEO, NAME + ".blend")
CAT  = "8872522f-45b7-4541-a557-5b69bcbfcee2"   # ST3E/Generate (adds geometry)

sys.path.append(os.path.join(GEO, "_build"))
import gng_selection_gate as gate

W_NAME = "GNG_SolidifyPlus_IndexWeld"
E_NAME = "GNG_SolidifyPlus_EdgeWeight"
D_NAME = "GNG_SolidifyPlus_SourceData"
R_NAME = "GNG_SolidifyPlus_Rim"
P_NAME = "GNG_SolidifyPlus_Shape"

RIM_MODES = ["All", "Convex & Concave", "Convex", "Concave", "Angle Threshold",
             "Vertex Crease"]
MODE_VERTEX_CREASE = 5

# private attributes (removed before output)
A_P, A_LO, A_HI = "__sp_p", "__sp_lo", "__sp_hi"
A_RD, A_MIT, A_TURN, A_NB = "__sp_rd", "__sp_mit", "__sp_turn", "__sp_nb"
A_BND, A_SRC, A_K = "__sp_bnd", "__sp_src", "__sp_k"
A_EK, A_FRONT, A_PART = "__sp_ek", "__sp_front", "__sp_part"
# edge kinds (A_EK) and face parts (A_PART)
EK_INNER, EK_OUTER, EK_LOOP, EK_RIM = 1, 2, 3, 4
PART_INNER, PART_OUTER, PART_RIM = 1, 2, 3


# ----------------------------------------------------------------------------- helpers
def _pick(sockets, key):
    """Resolve a socket by index, identifier or display name -- preferring the
    ENABLED variant (multi-type nodes keep disabled same-name sockets that no-op)."""
    if isinstance(key, int):
        return sockets[key]
    for test in (lambda s: s.enabled and s.identifier == key,
                 lambda s: s.enabled and s.name == key,
                 lambda s: s.identifier == key,
                 lambda s: s.name == key):
        for s in sockets:
            if test(s):
                return s
    raise KeyError(key)
def osock(node, key): return _pick(node.outputs, key)
def isock(node, key): return _pick(node.inputs,  key)


class Graph:
    """Small node-authoring kit bound to one node group."""

    def __init__(self, ng):
        self.ng, self.n, self.links = ng, ng.nodes, ng.links
        self._cursor = {}

    # -- structure -------------------------------------------------------------
    def frame(self, label):
        f = self.n.new("NodeFrame"); f.label = label; f.location = (0, 0)
        f.use_custom_color = True; f.color = (0.18, 0.20, 0.26)
        return f

    def mk(self, idname, parent=None, name=None, label=None, **props):
        node = self.n.new(idname)
        for k, v in props.items(): setattr(node, k, v)
        if parent: node.parent = parent
        x, y = self._cursor.get(parent, (0, 0))      # rough; the tidy engine lays out
        node.location = (x, y); self._cursor[parent] = (x + 220, y)
        if name: node.name = name
        if label: node.label = label
        return node

    def link(self, a, ai, b, bi): self.links.new(osock(a, ai), isock(b, bi))

    def feed(self, node, key, src):
        """src: constant, or (node, socket) tuple."""
        if isinstance(src, tuple): self.link(src[0], src[1], node, key)
        else: isock(node, key).default_value = src

    def gi(self, parent, *names):
        """Per-function Group Input (criterion 2): only the listed sockets shown."""
        g = self.mk("NodeGroupInput", parent)
        for s in g.outputs:
            if s.name and s.name not in names: s.hide = True
        return g

    # -- math ------------------------------------------------------------------
    def fmath(self, op, a, b=None, p=None, c=None, label=None):
        nd = self.mk("ShaderNodeMath", p, operation=op, label=label)
        self.feed(nd, "Value", a)
        if b is not None: self.feed(nd, "Value_001", b)
        if c is not None: self.feed(nd, "Value_002", c)
        return (nd, "Value")

    def imath(self, op, a, b=None, p=None, label=None):
        nd = self.mk("FunctionNodeIntegerMath", p, operation=op, label=label)
        self.feed(nd, "Value", a)
        if b is not None: self.feed(nd, "Value_001", b)
        return (nd, "Value")

    def vmath(self, op, a, b=None, p=None, label=None):
        nd = self.mk("ShaderNodeVectorMath", p, operation=op, label=label)
        self.feed(nd, "Vector", a)
        if b is not None:
            self.feed(nd, "Scale" if op == 'SCALE' else "Vector_001", b)
        out = "Value" if op in ('DOT_PRODUCT', 'LENGTH', 'DISTANCE') else "Vector"
        return (nd, out)

    def cmp(self, dtype, op, a, b, p=None, label=None):
        nd = self.mk("FunctionNodeCompare", p, data_type=dtype, operation=op, label=label)
        if dtype == 'INT':
            self.feed(nd, "A_INT", a); self.feed(nd, "B_INT", b)
        else:
            self.feed(nd, "A", a); self.feed(nd, "B", b)
        return (nd, "Result")

    def bmath(self, op, a, b=None, p=None, label=None):
        nd = self.mk("FunctionNodeBooleanMath", p, operation=op, label=label)
        self.feed(nd, 0, a)
        if b is not None: self.feed(nd, 1, b)
        return (nd, "Boolean")

    def switch(self, itype, sw, f, t, p=None, label=None):
        nd = self.mk("GeometryNodeSwitch", p, input_type=itype, label=label)
        self.feed(nd, "Switch", sw); self.feed(nd, "False", f); self.feed(nd, "True", t)
        return (nd, "Output")

    def named(self, dtype, name, p=None):
        nd = self.mk("GeometryNodeInputNamedAttribute", p, data_type=dtype)
        isock(nd, "Name").default_value = name
        return (nd, "Attribute")

    def store(self, geo, dtype, domain, name, value, p=None, sel=None, label=None):
        nd = self.mk("GeometryNodeStoreNamedAttribute", p, data_type=dtype,
                     domain=domain, label=label)
        self.feed(nd, "Geometry", geo); isock(nd, "Name").default_value = name
        self.feed(nd, "Value", value)
        if sel is not None: self.feed(nd, "Selection", sel)
        return (nd, "Geometry")

    def on_domain(self, domain, dtype, value, p=None, label=None):
        nd = self.mk("GeometryNodeFieldOnDomain", p, domain=domain, data_type=dtype,
                     label=label)
        self.feed(nd, "Value", value)
        return (nd, "Value")

    def at_index(self, domain, dtype, value, index, p=None, label=None):
        nd = self.mk("GeometryNodeFieldAtIndex", p, domain=domain, data_type=dtype,
                     label=label)
        self.feed(nd, "Value", value); self.feed(nd, "Index", index)
        return (nd, "Value")

    def sample_index(self, geo, dtype, value, index, p=None, label=None):
        nd = self.mk("GeometryNodeSampleIndex", p, data_type=dtype, domain='POINT',
                     label=label)
        self.feed(nd, "Geometry", geo); self.feed(nd, "Value", value)
        self.feed(nd, "Index", index)
        return (nd, "Value")

    def sep(self, v, p=None):
        nd = self.mk("ShaderNodeSeparateXYZ", p); self.feed(nd, "Vector", v)
        return (nd, "X"), (nd, "Y"), (nd, "Z")


def iface_sock(iface, name, in_out, stype, parent=None, default=None, mn=None, mx=None,
               subtype=None, desc="", single=False):
    s = iface.new_socket(name, in_out=in_out, socket_type=stype,
                         parent=parent if parent else None)
    if default is not None: s.default_value = default
    if mn is not None:      s.min_value = mn
    if mx is not None:      s.max_value = mx
    if subtype:             s.subtype = subtype
    s.description = desc
    if single and hasattr(s, "structure_type"):
        s.structure_type = 'SINGLE'
    return s


def fresh_group(name):
    old = bpy.data.node_groups.get(name)
    if old is not None:
        bpy.data.node_groups.remove(old)
    return bpy.data.node_groups.new(name, "GeometryNodeTree")


# ============================================================================= HELPER: INDEX WELD
def build_index_weld():
    """Weld selected vertices that share the same integer Key -- and only those.

    Each selected vertex is parked on a lattice point picked by its key
    (key mod 4096, key div 4096) -- exact in float32 -- and merged with distance 0.25,
    so equal keys meet and different keys are >= 1 apart. Positions are restored
    afterwards (the merged vertex keeps one of the pair's, which share a position
    by construction anyway)."""
    ng = fresh_group(W_NAME)
    ng.description = ("Merge selected vertices that share the same Key, and nothing else. "
                      "Exact replacement for a distance merge when the pairs are known")
    it = ng.interface
    iface_sock(it, "Geometry", 'INPUT', 'NodeSocketGeometry', desc="Mesh to weld")
    s = iface_sock(it, "Selection", 'INPUT', 'NodeSocketBool', default=True,
                   desc="Vertices that may be welded")
    s.hide_value = True
    iface_sock(it, "Key", 'INPUT', 'NodeSocketInt', default=0,
               desc="Selected vertices with the same key become one vertex")
    iface_sock(it, "Geometry", 'OUTPUT', 'NodeSocketGeometry', desc="Welded mesh")
    G = Graph(ng)
    F_park = G.frame("Park On Key Lattice  (key mod 4096, key div 4096)")
    F_mrg = G.frame("Merge Equal Keys  (distance 0.25)")
    F_rst = G.frame("Restore Positions")

    g = G.gi(F_park, "Geometry", "Selection", "Key")
    keep = G.store((g, "Geometry"), 'FLOAT_VECTOR', 'POINT', "__iw_p",
                   (G.mk("GeometryNodeInputPosition", F_park), "Position"), F_park,
                   label="Keep Position")
    kx = G.imath('MODULO', (g, "Key"), 4096, F_park, label="Key mod 4096")
    ky = G.imath('DIVIDE_FLOOR', (g, "Key"), 4096, F_park, label="Key div 4096")
    lat = G.mk("ShaderNodeCombineXYZ", F_park, label="Lattice Point")
    G.feed(lat, "X", kx); G.feed(lat, "Y", ky)
    park = G.mk("GeometryNodeSetPosition", F_park, label="Park Selected")
    G.feed(park, "Geometry", keep); G.feed(park, "Selection", (g, "Selection"))
    G.feed(park, "Position", (lat, "Vector"))

    g2 = G.gi(F_mrg, "Selection")
    mrg = G.mk("GeometryNodeMergeByDistance", F_mrg, label="Merge Equal Keys")
    G.feed(mrg, "Geometry", (park, "Geometry")); G.feed(mrg, "Selection", (g2, "Selection"))
    isock(mrg, "Mode").default_value = "All"
    isock(mrg, "Distance").default_value = 0.25

    rst = G.mk("GeometryNodeSetPosition", F_rst, label="Restore Position")
    G.feed(rst, "Geometry", (mrg, "Geometry"))
    G.feed(rst, "Position", G.named('FLOAT_VECTOR', "__iw_p", F_rst))
    rm = G.mk("GeometryNodeRemoveAttribute", F_rst)
    G.feed(rm, "Geometry", (rst, "Geometry")); isock(rm, "Name").default_value = "__iw_p"
    go = G.mk("NodeGroupOutput", F_rst)
    G.link(rm, "Geometry", go, "Geometry")
    return ng


# ============================================================================= HELPER: EDGE WEIGHT
def build_edge_weight():
    """Write one edge weight attribute (crease_edge or bevel_weight_edge) from the edge
    kinds GN_SolidifyPlus tagged: inner border, outer border, rim loop, rim edge --
    rim edges filtered by the Rim Mode."""
    ng = fresh_group(E_NAME)
    ng.description = ("GN_SolidifyPlus: write an edge weight (crease / bevel weight) on the "
                      "inner border, outer border, rim loop and rim edges")
    it = ng.interface
    iface_sock(it, "Geometry", 'INPUT', 'NodeSocketGeometry', desc="Solidified mesh")
    iface_sock(it, "Attribute Name", 'INPUT', 'NodeSocketString', default="crease_edge",
               desc="Edge attribute to write, e.g. crease_edge or bevel_weight_edge")
    for nm, d in (("Inner Border", "Weight of the inner shell's border edges"),
                  ("Outer Border", "Weight of the outer shell's border edges"),
                  ("Rim Loops", "Weight of the loops running around the rim"),
                  ("Rim Edges", "Weight of the edges running across the rim, picked by "
                                "Rim Mode")):
        iface_sock(it, nm, 'INPUT', 'NodeSocketFloat', default=0.0, mn=0.0, mx=1.0,
                   subtype='FACTOR', desc=d)
    iface_sock(it, "Rim Mode", 'INPUT', 'NodeSocketInt', default=4, mn=0, mx=5,
               desc="0 All, 1 Convex & Concave, 2 Convex, 3 Concave, 4 Angle Threshold, "
                    "5 Vertex Crease", single=True)
    iface_sock(it, "Rim Angle", 'INPUT', 'NodeSocketFloat', default=math.radians(95),
               mn=0.0, mx=math.pi, subtype='ANGLE',
               desc="Angle Threshold mode: rim edges at border corners sharper than this")
    iface_sock(it, "Geometry", 'OUTPUT', 'NodeSocketGeometry', desc="Mesh with the weights")
    G = Graph(ng)
    F_mode = G.frame("Rim Edge Filter  (by Rim Mode)")
    F_val = G.frame("Weight Per Edge Kind")
    F_st = G.frame("Store Edge Weight")

    # ---- rim edge filter: per-vertex source data, same on both ends of a rim edge
    g = G.gi(F_mode, "Rim Mode", "Rim Angle")
    nb = G.named('INT', A_NB, F_mode)
    turn = G.named('FLOAT', A_TURN, F_mode)
    vc = G.named('FLOAT', "crease_vert", F_mode)
    sw = G.mk("GeometryNodeIndexSwitch", F_mode, data_type='BOOLEAN', label="Rim Mode")
    while len([s for s in sw.inputs if s.name.isdigit()]) < len(RIM_MODES):
        sw.index_switch_items.new()
    G.feed(sw, "Index", (g, "Rim Mode"))
    G.feed(sw, "0", True)
    G.feed(sw, "1", G.cmp('INT', 'NOT_EQUAL', nb, 3, F_mode, label="Corner  (edges != 3)"))
    G.feed(sw, "2", G.cmp('INT', 'LESS_THAN', nb, 3, F_mode, label="Convex  (edges < 3)"))
    G.feed(sw, "3", G.cmp('INT', 'GREATER_THAN', nb, 3, F_mode, label="Concave  (edges > 3)"))
    inner_ang = G.fmath('SUBTRACT', math.pi, turn, F_mode, label="Corner Angle  (pi - turn)")
    G.feed(sw, "4", G.cmp('FLOAT', 'LESS_THAN', inner_ang, (g, "Rim Angle"), F_mode,
                          label="Sharper Than Threshold"))
    G.feed(sw, "5", G.cmp('FLOAT', 'GREATER_THAN', vc, 0.0, F_mode,
                          label="Vertex Creased  (crease_vert > 0)"))

    # ---- value per kind
    g2 = G.gi(F_val, "Inner Border", "Outer Border", "Rim Loops", "Rim Edges")
    kind = G.named('INT', A_EK, F_val)
    val = G.mk("GeometryNodeIndexSwitch", F_val, data_type='FLOAT', label="Weight By Kind")
    while len([s for s in val.inputs if s.name.isdigit()]) < 5:
        val.index_switch_items.new()
    G.feed(val, "Index", kind)
    G.feed(val, "0", 0.0)
    G.feed(val, "1", (g2, "Inner Border")); G.feed(val, "2", (g2, "Outer Border"))
    G.feed(val, "3", (g2, "Rim Loops")); G.feed(val, "4", (g2, "Rim Edges"))

    is_border_or_loop = G.bmath('AND', G.cmp('INT', 'GREATER_EQUAL', kind, EK_INNER, F_val),
                                G.cmp('INT', 'LESS_EQUAL', kind, EK_LOOP, F_val), F_val,
                                label="Border Or Loop")
    is_rim = G.bmath('AND', G.cmp('INT', 'EQUAL', kind, EK_RIM, F_val, label="Rim Edge"),
                     (sw, "Output"), F_val, label="Rim Edge In Mode")
    sel = G.bmath('OR', is_border_or_loop, is_rim, F_val, label="Edges To Write")

    g3 = G.gi(F_st, "Geometry", "Attribute Name")
    st = G.mk("GeometryNodeStoreNamedAttribute", F_st, data_type='FLOAT', domain='EDGE',
              label="Store Edge Weight")
    G.feed(st, "Geometry", (g3, "Geometry")); G.feed(st, "Name", (g3, "Attribute Name"))
    G.feed(st, "Selection", sel); G.feed(st, "Value", (val, "Output"))
    go = G.mk("NodeGroupOutput", F_st)
    G.link(st, "Geometry", go, "Geometry")
    return ng


# ============================================================================= HELPER: SOURCE DATA
def build_source_data():
    """Everything the shells and rim need, measured once on the selected faces and
    stored per source vertex / edge (copies made later inherit it): thickness
    direction, weighted inner/outer offsets, rim direction, mitre, corner turn,
    border flags and the source index."""
    ng = fresh_group(D_NAME)
    ng.description = ("GN_SolidifyPlus: measure the source surface once -- thickness "
                      "direction and offsets, rim direction, mitre, corner turn -- and store "
                      "it on the vertices and edges")
    it = ng.interface
    iface_sock(it, "Geometry", 'INPUT', 'NodeSocketGeometry', desc="Selected faces to solidify")
    p = it.new_panel("Thickness")
    iface_sock(it, "Thickness", 'INPUT', 'NodeSocketFloat', p, default=0.1,
               subtype='DISTANCE', desc="Shell thickness")
    iface_sock(it, "Offset", 'INPUT', 'NodeSocketFloat', p, default=1.0, mn=-1.0, mx=1.0,
               subtype='FACTOR', desc="-1 behind, 0 centred, 1 in front of the surface")
    iface_sock(it, "Even Thickness", 'INPUT', 'NodeSocketBool', p, default=False,
               desc="Push corner vertices out so the shell stays evenly thick")
    p = it.new_panel("Thickness Weight")
    iface_sock(it, "Weight", 'INPUT', 'NodeSocketFloat', p, default=1.0, mn=0.0, mx=1.0,
               subtype='FACTOR', desc="Per-vertex thickness weight, 0-1")
    iface_sock(it, "Zero Weight Factor", 'INPUT', 'NodeSocketFloat', p, default=0.0,
               mn=0.0, mx=1.0, subtype='FACTOR', desc="Thickness factor at weight 0")
    iface_sock(it, "Invert Weight", 'INPUT', 'NodeSocketBool', p, default=False,
               desc="Use 1 - weight")
    p = it.new_panel("Direction")
    iface_sock(it, "Use Custom Direction", 'INPUT', 'NodeSocketBool', p, default=False,
               desc="One fixed direction instead of the vertex normals")
    iface_sock(it, "Custom Direction Rotation", 'INPUT', 'NodeSocketRotation', p,
               desc="Rotates object +Z into the custom direction")
    iface_sock(it, "Geometry", 'OUTPUT', 'NodeSocketGeometry',
               desc="The same faces, with the source data stored")
    G = Graph(ng)
    link, feed, mk, gi = G.link, G.feed, G.mk, G.gi
    F_dir = G.frame("Thickness Direction  (normal or custom, even thickness)")
    F_w = G.frame("Thickness Weight  (vertex group, zero weight factor)")
    F_off = G.frame("Shell Offsets  (inner = T(o-1)/2, outer = T(o+1)/2)")
    F_rdir = G.frame("Rim Direction  (rim face normals, mitre, corner turn)")
    F_data = G.frame("Store Source Vertex Data")

    # ---- thickness direction
    g = gi(F_dir, "Use Custom Direction", "Custom Direction Rotation", "Even Thickness")
    nrm = (mk("GeometryNodeInputNormal", F_dir), "Normal")
    rotv = mk("FunctionNodeRotateVector", F_dir, label="Custom Direction")
    isock(rotv, "Vector").default_value = (0.0, 0.0, 1.0)
    link(g, "Custom Direction Rotation", rotv, "Rotation")
    dirv = G.switch('VECTOR', (g, "Use Custom Direction"), nrm, (rotv, "Vector"), F_dir,
                    label="Direction")
    fnrm = G.on_domain('FACE', 'FLOAT_VECTOR', nrm, F_dir, label="Mean Face Normal")
    cosang = G.vmath('DOT_PRODUCT', dirv, fnrm, F_dir, label="Cos  (direction, faces)")
    cosc = G.fmath('MAXIMUM', cosang, 0.25, F_dir, label="Clamp  (max 4x)")
    even = G.fmath('DIVIDE', 1.0, cosc, F_dir, label="Even Factor")
    evenk = G.switch('FLOAT', (g, "Even Thickness"), 1.0, even, F_dir,
                     label="Even Thickness?")

    # ---- thickness weight: an all-zero weight (missing group) counts as no weight
    g = gi(F_w, "Geometry", "Weight", "Zero Weight Factor", "Invert Weight")
    stat = mk("GeometryNodeAttributeStatistic", F_w, data_type='FLOAT', domain='POINT',
              label="Weight Range")
    link(g, "Geometry", stat, "Geometry"); link(g, "Weight", stat, "Attribute")
    has_w = G.cmp('FLOAT', 'GREATER_THAN', (stat, "Max"), 0.0, F_w, label="Any Weight?")
    w_inv = G.fmath('SUBTRACT', 1.0, (g, "Weight"), F_w, label="1 - Weight")
    w_use = G.switch('FLOAT', (g, "Invert Weight"), (g, "Weight"), w_inv, F_w,
                     label="Invert Weight?")
    mixw = mk("ShaderNodeMix", F_w, data_type='FLOAT', label="Weight -> Factor",
              clamp_factor=True)
    feed(mixw, "Factor_Float", (g, "Zero Weight Factor"))
    feed(mixw, "A_Float", w_use); feed(mixw, "B_Float", 1.0)
    wfac = G.switch('FLOAT', has_w, 1.0, (mixw, "Result_Float"), F_w, label="Weight Factor")

    # ---- shell offsets
    g = gi(F_off, "Thickness", "Offset")
    t_loc = G.fmath('MULTIPLY', G.fmath('MULTIPLY', (g, "Thickness"), wfac, F_off),
                    evenk, F_off, label="Local Thickness")
    o_lo = G.fmath('MULTIPLY', G.fmath('SUBTRACT', (g, "Offset"), 1.0, F_off), 0.5, F_off,
                   label="(o - 1) / 2")
    o_hi = G.fmath('MULTIPLY', G.fmath('ADD', (g, "Offset"), 1.0, F_off), 0.5, F_off,
                   label="(o + 1) / 2")
    lo_v = G.vmath('SCALE', dirv, G.fmath('MULTIPLY', t_loc, o_lo, F_off), F_off,
                   label="Inner Offset")
    hi_v = G.vmath('SCALE', dirv, G.fmath('MULTIPLY', t_loc, o_hi, F_off), F_off,
                   label="Outer Offset")

    # ---- rim direction
    ev = mk("GeometryNodeInputMeshEdgeVertices", F_rdir)
    mid = G.vmath('SCALE', G.vmath('ADD', (ev, "Position 1"), (ev, "Position 2"), F_rdir),
                  0.5, F_rdir, label="Edge Middle")
    evec = G.vmath('SUBTRACT', (ev, "Position 2"), (ev, "Position 1"), F_rdir,
                   label="Edge Vector")
    fctr = G.on_domain('FACE', 'FLOAT_VECTOR',
                       (mk("GeometryNodeInputPosition", F_rdir), "Position"), F_rdir,
                       label="Face Centre  (on edge)")
    away = G.vmath('SUBTRACT', mid, fctr, F_rdir, label="Face -> Edge")
    perp = G.vmath('SUBTRACT', away, G.vmath('PROJECT', away, evec, F_rdir), F_rdir,
                   label="Perpendicular To Edge")
    enb = mk("GeometryNodeInputMeshEdgeNeighbors", F_rdir)
    is_b = G.cmp('INT', 'EQUAL', (enb, "Face Count"), 1, F_rdir, label="Border Edge")
    # the rim face's normal: across the edge AND the thickness direction (dir on an
    # edge = mean of its two vertices), pointed away from the face it borders
    rimn = G.vmath('NORMALIZE', G.vmath('CROSS_PRODUCT', evec, dirv, F_rdir), None, F_rdir,
                   label="Rim Face Normal")
    side = G.fmath('SIGN', G.vmath('DOT_PRODUCT', rimn, perp, F_rdir), None, F_rdir,
                   label="Away From Face")
    eout = G.vmath('SCALE', G.vmath('SCALE', rimn, side, F_rdir), is_b, F_rdir,
                   label="Outward  (border edges only)")
    vnb = mk("GeometryNodeInputMeshVertexNeighbors", F_rdir)
    vsum = G.vmath('SCALE', G.on_domain('EDGE', 'FLOAT_VECTOR', eout, F_rdir,
                                        label="Mean Outward"),
                   (vnb, "Vertex Count"), F_rdir, label="Sum Outward")
    nbord = G.fmath('MULTIPLY', G.on_domain('EDGE', 'FLOAT', is_b, F_rdir,
                                            label="Mean Border"),
                    (vnb, "Vertex Count"), F_rdir, label="Border Edges At Vertex")
    vlen = G.vmath('LENGTH', vsum, None, F_rdir, label="Sum Length")
    mitre = G.fmath('MINIMUM', G.fmath('DIVIDE', nbord, G.fmath('MAXIMUM', vlen, 1e-6, F_rdir),
                                       F_rdir), 4.0, F_rdir, label="Mitre  (1 / cos(turn/2))")
    turn = G.fmath('MULTIPLY', G.fmath('ARCCOSINE',
                   G.fmath('DIVIDE', vlen, G.fmath('MAXIMUM', nbord, 1.0, F_rdir), F_rdir,
                           label="cos(turn/2)"), None, F_rdir), 2.0, F_rdir,
                   label="Corner Turn")
    rdir = G.vmath('NORMALIZE', vsum, None, F_rdir, label="Rim Direction")
    on_b = G.cmp('FLOAT', 'GREATER_THAN', nbord, 0.5, F_rdir, label="Border Vertex")

    # ---- store
    g = gi(F_data, "Geometry")
    pos = (mk("GeometryNodeInputPosition", F_data), "Position")
    idx = (mk("GeometryNodeInputIndex", F_data), "Index")
    x = (g, "Geometry")
    for dt, dom, nm, val in (('FLOAT_VECTOR', 'POINT', A_P, pos),
                             ('FLOAT_VECTOR', 'POINT', A_LO, lo_v),
                             ('FLOAT_VECTOR', 'POINT', A_HI, hi_v),
                             ('FLOAT_VECTOR', 'POINT', A_RD, rdir),
                             ('FLOAT', 'POINT', A_MIT, mitre),
                             ('FLOAT', 'POINT', A_TURN, turn),
                             ('INT', 'POINT', A_NB, (vnb, "Vertex Count")),
                             ('BOOLEAN', 'POINT', A_BND, on_b),
                             ('INT', 'POINT', A_SRC, idx),
                             ('INT', 'EDGE', A_EK, G.switch('INT', is_b, 0, EK_INNER, F_data)),
                             ('BOOLEAN', 'EDGE', A_FRONT, is_b)):
        x = G.store(x, dt, dom, nm, val, F_data, label=nm.replace("__sp_", "Store "))
    go = mk("NodeGroupOutput", F_data)
    feed(go, "Geometry", x)
    return ng


# ============================================================================= HELPER: RIM
def build_rim():
    """Grow the rim off the inner shell's border: one zero-length edge extrusion per
    rim segment, tagging each new layer (vertex layer k, loop / outer-border edges,
    rim faces). Positions are placed later from the stored source data."""
    ng = fresh_group(R_NAME)
    ng.description = ("GN_SolidifyPlus: grow the rim off the inner shell's border, one "
                      "tagged edge extrusion per rim segment")
    it = ng.interface
    iface_sock(it, "Geometry", 'INPUT', 'NodeSocketGeometry',
               desc="Inner shell with the source data stored")
    p = it.new_panel("Rim")
    iface_sock(it, "Segments", 'INPUT', 'NodeSocketInt', p, default=1, mn=1,
               desc="Rim segments from shell to shell (Rim Loops + 1)", single=True)
    iface_sock(it, "Extrusions", 'INPUT', 'NodeSocketInt', p, default=1, mn=0,
               desc="Segments to grow: Segments, or 0 for no rim", single=True)
    iface_sock(it, "Geometry", 'OUTPUT', 'NodeSocketGeometry',
               desc="Inner shell plus the rim layers")
    G = Graph(ng)
    link, feed, mk, gi = G.link, G.feed, G.mk, G.gi
    F_rin = G.frame("Rim Loop In")
    F_body = G.frame("Extrude One Rim Segment  (tag layer, edges, faces)")
    F_rout = G.frame("Rim Loop Out")

    g = gi(F_rin, "Geometry", "Extrusions")
    r_in = mk("GeometryNodeRepeatInput", F_rin, name="Rim Loop In")
    r_out = mk("GeometryNodeRepeatOutput", F_rout, name="Rim Loop Out")
    r_in.pair_with_output(r_out)
    r_out.repeat_items.new('INT', "Layer")
    link(g, "Extrusions", r_in, "Iterations")
    link(g, "Geometry", r_in, "Geometry")
    isock(r_in, "Layer").default_value = 0

    b = F_body
    gsize = mk("GeometryNodeAttributeDomainSize", b, component='MESH', label="Vertices Before")
    link(r_in, "Geometry", gsize, "Geometry")
    ext = mk("GeometryNodeExtrudeMesh", b, mode='EDGES', label="Extrude Rim Front")
    link(r_in, "Geometry", ext, "Mesh")
    feed(ext, "Selection", G.named('BOOLEAN', A_FRONT, b))
    isock(ext, "Offset Scale").default_value = 0.0
    layer = G.imath('ADD', (r_in, "Layer"), 1, b, label="Layer + 1")
    is_new = G.cmp('INT', 'GREATER_EQUAL', (mk("GeometryNodeInputIndex", b), "Index"),
                   (gsize, "Point Count"), b, label="New Vertex")
    gseg = gi(b, "Segments")
    last = G.cmp('INT', 'EQUAL', layer, (gseg, "Segments"), b, label="Last Layer")
    x = G.store((ext, "Mesh"), 'INT', 'POINT', A_K, layer, b, sel=is_new, label="Tag Layer")
    x = G.store(x, 'BOOLEAN', 'EDGE', A_FRONT, (ext, "Top"), b, label="Advance Front")
    # the last ring's edges coincide with the outer border after the weld: same kind
    x = G.store(x, 'INT', 'EDGE', A_EK, G.switch('INT', last, EK_LOOP, EK_OUTER, b),
                b, sel=(ext, "Top"), label="Tag Loop Edges")
    x = G.store(x, 'INT', 'FACE', A_PART, PART_RIM, b, sel=(ext, "Side"),
                label="Tag Rim Faces")
    feed(r_out, "Geometry", x)
    link(layer[0], "Value", r_out, "Layer")
    go = mk("NodeGroupOutput", F_rout)
    link(r_out, "Geometry", go, "Geometry")
    return ng


# ============================================================================= HELPER: SHAPE
def build_shape():
    """Place every vertex from its stored source data: inner -> outer offset by the rim
    parameter u, outer border inset, rim pushed out along the rim direction by the
    Push bulge and the profile curve."""
    ng = fresh_group(P_NAME)
    ng.description = ("GN_SolidifyPlus: place every vertex -- shell offsets, inset, push "
                      "and profile curve -- from the stored source data")
    it = ng.interface
    iface_sock(it, "Geometry", 'INPUT', 'NodeSocketGeometry',
               desc="Welded shells and rim, positions not yet placed")
    p = it.new_panel("Profile")
    iface_sock(it, "Profile", 'INPUT', 'NodeSocketGeometry', p,
               desc="Profile curve geometry, in its own local space")
    iface_sock(it, "Segments", 'INPUT', 'NodeSocketInt', p, default=1, mn=1,
               desc="Rim segments from shell to shell", single=True)
    iface_sock(it, "Profile Sets Rim Loops", 'INPUT', 'NodeSocketBool', p, default=False,
               desc="Rim layer k sits on profile point k instead of at k / Segments")
    p = it.new_panel("Rim Shape")
    iface_sock(it, "Inset", 'INPUT', 'NodeSocketFloat', p, default=0.0, subtype='DISTANCE',
               desc="Pull the outer border inward", single=True)
    iface_sock(it, "Push", 'INPUT', 'NodeSocketFloat', p, default=0.0, subtype='DISTANCE',
               desc="Bulge the rim out at its middle", single=True)
    iface_sock(it, "Even Rim Offset", 'INPUT', 'NodeSocketBool', p, default=True,
               desc="Mitre push and profile at border corners")
    iface_sock(it, "Geometry", 'OUTPUT', 'NodeSocketGeometry', desc="Placed mesh")
    G = Graph(ng)
    link, feed, mk, gi = G.link, G.feed, G.mk, G.gi
    F_pts = G.frame("Profile Points  (evaluated)")
    F_prof = G.frame("Profile Curve  (u along thickness, v outward)")
    F_pos = G.frame("Final Position  (shell offsets, inset, push, profile)")

    # ---- profile points
    g = gi(F_pts, "Profile", "Profile Sets Rim Loops")
    c2p = mk("GeometryNodeCurveToPoints", F_pts, mode='EVALUATED', label="Profile Points")
    link(g, "Profile", c2p, "Curve")
    psize = mk("GeometryNodeAttributeDomainSize", F_pts, component='POINTCLOUD')
    link(c2p, "Points", psize, "Geometry")
    pcount = (psize, "Point Count")
    has_prof = G.cmp('INT', 'GREATER_EQUAL', pcount, 2, F_pts, label="Has Profile")
    use_pts = G.bmath('AND', (g, "Profile Sets Rim Loops"), has_prof, F_pts,
                      label="Layer On Point")

    # ---- profile sample per vertex
    g = gi(F_prof, "Profile", "Segments")
    kf = G.named('INT', A_K, F_prof)
    tpar = G.fmath('DIVIDE', kf, (g, "Segments"), F_prof, label="t = layer / segments")
    ppos = lambda: (mk("GeometryNodeInputPosition", F_prof), "Position")
    p_first = G.sample_index((c2p, "Points"), 'FLOAT_VECTOR', ppos(), 0, F_prof,
                             label="First Point")
    p_last = G.sample_index((c2p, "Points"), 'FLOAT_VECTOR', ppos(),
                            G.imath('SUBTRACT', pcount, 1, F_prof), F_prof, label="Last Point")
    p_at_pt = G.sample_index((c2p, "Points"), 'FLOAT_VECTOR', ppos(), kf, F_prof,
                             label="Profile Point k")
    scurve = mk("GeometryNodeSampleCurve", F_prof, mode='FACTOR', data_type='FLOAT_VECTOR',
                use_all_curves=False, label="Profile At t")
    link(g, "Profile", scurve, "Curves"); feed(scurve, "Factor", tpar)
    p_at_t = G.switch('VECTOR', use_pts, (scurve, "Position"), p_at_pt, F_prof,
                      label="Profile Sample")
    axis = G.vmath('SUBTRACT', p_last, p_first, F_prof, label="Profile Axis")
    rel = G.vmath('SUBTRACT', p_at_t, p_first, F_prof, label="From First Point")
    alen2 = G.fmath('MAXIMUM', G.vmath('DOT_PRODUCT', axis, axis, F_prof), 1e-12, F_prof,
                    label="Axis Length^2")
    u_prof = G.fmath('DIVIDE', G.vmath('DOT_PRODUCT', rel, axis, F_prof), alen2, F_prof,
                     label="u  (along axis)")
    ax, ay, _ = G.sep(axis, F_prof)
    rx, ry, _ = G.sep(rel, F_prof)
    cross2 = G.fmath('SUBTRACT', G.fmath('MULTIPLY', ay, rx, F_prof),
                     G.fmath('MULTIPLY', ax, ry, F_prof), F_prof,
                     label="Signed Distance x |axis|")
    v_prof = G.fmath('DIVIDE', cross2, alen2, F_prof, label="v  (outward, / height)")
    u = G.switch('FLOAT', has_prof, tpar, u_prof, F_prof, label="u")
    v = G.switch('FLOAT', has_prof, 0.0, v_prof, F_prof, label="v")

    # ---- final position
    g = gi(F_pos, "Geometry", "Inset", "Push", "Even Rim Offset")
    P = G.named('FLOAT_VECTOR', A_P, F_pos)
    LO = G.named('FLOAT_VECTOR', A_LO, F_pos)
    HI = G.named('FLOAT_VECTOR', A_HI, F_pos)
    RD = G.named('FLOAT_VECTOR', A_RD, F_pos)
    MIT = G.named('FLOAT', A_MIT, F_pos)
    BND = G.named('BOOLEAN', A_BND, F_pos)
    inset = G.vmath('SCALE', RD, G.fmath('MULTIPLY', G.fmath('MULTIPLY', MIT, (g, "Inset"),
                    F_pos), G.fmath('MULTIPLY', BND, -1.0, F_pos), F_pos), F_pos,
                    label="Inset  (border only, mitred)")
    hi_in = G.vmath('ADD', HI, inset, F_pos, label="Outer + Inset")
    across = G.vmath('SCALE', G.vmath('SUBTRACT', hi_in, LO, F_pos), u, F_pos,
                     label="Inner -> Outer  (u)")
    thick = G.vmath('LENGTH', G.vmath('SUBTRACT', HI, LO, F_pos), None, F_pos,
                    label="Local Thickness")
    bulge = G.fmath('MULTIPLY', G.fmath('MULTIPLY', 4.0, u, F_pos),
                    G.fmath('SUBTRACT', 1.0, u, F_pos), F_pos, label="4u(1-u)")
    out_amt = G.fmath('MULTIPLY_ADD', v, thick, F_pos,
                      c=G.fmath('MULTIPLY', (g, "Push"), bulge, F_pos),
                      label="Profile + Push")
    rd_e = G.vmath('SCALE', RD, G.switch('FLOAT', (g, "Even Rim Offset"), 1.0, MIT, F_pos),
                   F_pos, label="Rim Direction  (even?)")
    shape = G.vmath('SCALE', rd_e, G.fmath('MULTIPLY', out_amt, BND, F_pos), F_pos,
                    label="Rim Shape Offset")
    final = G.vmath('ADD', G.vmath('ADD', P, LO, F_pos),
                    G.vmath('ADD', across, shape, F_pos), F_pos, label="Final Position")
    setp = mk("GeometryNodeSetPosition", F_pos, label="Place Every Vertex")
    link(g, "Geometry", setp, "Geometry"); feed(setp, "Position", final)
    go = mk("NodeGroupOutput", F_pos)
    link(setp, "Geometry", go, "Geometry")
    return ng


# ============================================================================= MAIN GROUP
def build_main(weld_ng, weight_ng, data_ng, rim_ng, shape_ng):
    ng = fresh_group(NAME)
    iface = ng.interface
    S = lambda *a, **k: iface_sock(iface, *a, **k)

    S("Geometry", 'INPUT', 'NodeSocketGeometry', desc="Mesh to solidify.")
    S("Selection", 'INPUT', 'NodeSocketBool', default=True,
      desc="Faces to solidify. Unselected faces pass through unchanged (not connected "
           "to the solidified part).")
    S("Invert Selection", 'INPUT', 'NodeSocketBool', default=False,
      desc="Solidify every face EXCEPT the selected ones.")
    grow = S("Grow / Shrink Selection", 'INPUT', 'NodeSocketInt', default=0,
             mn=-10000, mx=10000, single=True,
             desc="Grow the selection by this many rings of neighbouring faces; negative "
                  "values shrink it. 0 leaves the selection unchanged.")

    p_sol = iface.new_panel("Solidify")
    S("Thickness", 'INPUT', 'NodeSocketFloat', p_sol, default=0.1, subtype='DISTANCE',
      single=True,
      desc="Shell thickness. Negative values solidify to the other side.")
    S("Offset", 'INPUT', 'NodeSocketFloat', p_sol, default=1.0, mn=-1.0, mx=1.0,
      subtype='FACTOR', single=True,
      desc="Where the shell sits relative to the surface: 1 = in front (along the normal), "
           "-1 = behind, 0 = centred. Same as the Solidify modifier's Offset.")
    S("Even Thickness", 'INPUT', 'NodeSocketBool', p_sol, default=False,
      desc="Keep the shell evenly thick at sharp corners by pushing corner vertices "
           "further out.")
    S("Rim Loops", 'INPUT', 'NodeSocketInt', p_sol, default=0, mn=0, mx=64, single=True,
      desc="Extra edge loops around the rim. Give the rim support loops for subdivision, "
           "or room for Push and the Profile Curve.")
    S("Fill Rim", 'INPUT', 'NodeSocketBool', p_sol, default=True,
      desc="Close the gap between the two shells with a rim. Off leaves two separate "
           "shells.")
    S("Only Rim", 'INPUT', 'NodeSocketBool', p_sol, default=False,
      desc="Drop the inner shell (the flipped one, at Offset -1) and keep the outer shell "
           "plus the rim. With Offset -1 that is the original surface with a rim grown "
           "behind it. Needs Fill Rim.")
    S("Inset", 'INPUT', 'NodeSocketFloat', p_sol, default=0.0, subtype='DISTANCE',
      single=True,
      desc="Pull the outer shell's border inward along the surface, so the rim leans in. "
           "Corners are mitred, so the border stays parallel.")

    p_w = iface.new_panel("Thickness Weight", default_closed=True)
    tw = S("Thickness Weight", 'INPUT', 'NodeSocketFloat', p_w, default=1.0, mn=0.0, mx=1.0,
           subtype='FACTOR',
           desc="Per-vertex thickness, 0-1. Bind a vertex group here with the attribute "
                "toggle. A weight that is 0 everywhere (e.g. a group name that does not "
                "exist) counts as no weight at all.")
    tw.default_attribute_name = ""
    S("Zero Weight Factor", 'INPUT', 'NodeSocketFloat', p_w, default=0.0, mn=0.0, mx=1.0,
      subtype='FACTOR', single=True,
      desc="Thickness factor for vertices with zero weight (the Solidify modifier's "
           "Factor). 1 = weight has no effect.")
    S("Invert Weight", 'INPUT', 'NodeSocketBool', p_w, default=False,
      desc="Use 1 - weight.")

    def weight_panel(title, word):
        p = iface.new_panel(title, default_closed=True)
        S(f"Inner {word}", 'INPUT', 'NodeSocketFloat', p, default=0.0, mn=0.0, mx=1.0,
          subtype='FACTOR', single=True,
          desc=f"{word} on the border edges of the inner shell (the one at Offset -1).")
        S(f"Outer {word}", 'INPUT', 'NodeSocketFloat', p, default=0.0, mn=0.0, mx=1.0,
          subtype='FACTOR', single=True,
          desc=f"{word} on the border edges of the outer shell (the one at Offset 1).")
        S(f"Rim Loop {word}", 'INPUT', 'NodeSocketFloat', p, default=0.0, mn=0.0, mx=1.0,
          subtype='FACTOR', single=True,
          desc=f"{word} on the loops running around the rim (see Rim Loops).")
        S(f"Rim {word}", 'INPUT', 'NodeSocketFloat', p, default=0.0, mn=0.0, mx=1.0,
          subtype='FACTOR', single=True,
          desc=f"{word} on the edges running across the rim, from shell to shell. Which "
               f"ones is picked by Rim {word} By.")
        m = S(f"Rim {word} By", 'INPUT', 'NodeSocketMenu', p,
              desc="Which rim edges get the weight. Convex / Concave go by topology: a "
                   "border vertex with 2 edges is a convex corner, with 4 or more a "
                   "concave one. Angle Threshold picks corners sharper than the angle "
                   "below. Vertex Crease picks border vertices with a vertex crease.")
        S(f"Rim {word} Angle", 'INPUT', 'NodeSocketFloat', p, default=math.radians(95),
          mn=0.0, mx=math.pi, subtype='ANGLE', single=True,
          desc="Angle Threshold mode: rim edges at border corners sharper than this angle. "
               "180 degrees picks every corner.")
        return p, m

    p_cr, m_cr = weight_panel("Crease", "Crease")
    S("Keep Vertex Crease", 'INPUT', 'NodeSocketBool', p_cr, default=False,
      desc="A Rim ... By set to Vertex Crease consumes the input's vertex creases (they "
           "become rim edge creases, and are removed so they don't pinch the subdivided "
           "result). Enable to keep them.")
    p_bw, m_bw = weight_panel("Bevel Weight", "Bevel Weight")

    p_shape = iface.new_panel("Rim Shape", default_closed=True)
    S("Push", 'INPUT', 'NodeSocketFloat', p_shape, default=0.0, subtype='DISTANCE',
      single=True,
      desc="Bulge the rim outward (negative: inward) at its middle, falling off "
           "smoothly to both shells. Needs Rim Loops.")
    S("Profile Curve", 'INPUT', 'NodeSocketObject', p_shape,
      desc="Curve object giving the rim's cross-section. Draw it in the curve's local XY "
           "from the inner shell (first point) to the outer shell (last point); +X is "
           "outward. Its size does not matter -- it is scaled to the thickness.")
    S("Profile Sets Rim Loops", 'INPUT', 'NodeSocketBool', p_shape, default=False,
      desc="Put one rim loop on every (evaluated) point of the profile curve, so the rim "
           "follows it exactly. Overrides Rim Loops.")
    S("Even Rim Offset", 'INPUT', 'NodeSocketBool', p_shape, default=True,
      desc="Mitre Push and the profile at border corners so the rim stays evenly wide.")

    p_mat = iface.new_panel("Materials", default_closed=True)
    S("Shell Material Offset", 'INPUT', 'NodeSocketInt', p_mat, default=0, single=True,
      desc="Added to the material index of the inner shell (the flipped one, at "
           "Offset -1).")
    S("Rim Material Offset", 'INPUT', 'NodeSocketInt', p_mat, default=0, single=True,
      desc="Added to the material index of the rim faces (they start with the material "
           "of the face they grow from).")

    p_dir = iface.new_panel("Direction", default_closed=True)
    S("Use Custom Direction", 'INPUT', 'NodeSocketBool', p_dir, default=False,
      desc="Solidify along one fixed direction instead of the vertex normals.")
    S("Custom Direction Rotation", 'INPUT', 'NodeSocketRotation', p_dir,
      desc="Rotates the custom direction, which points along object +Z by default.")

    S("Geometry", 'OUTPUT', 'NodeSocketGeometry', desc="The solidified mesh.")
    for nm, d in (("Rim", "True on the rim faces."),
                  ("Inner Shell", "True on the faces of the inner shell (at Offset -1)."),
                  ("Outer Shell", "True on the faces of the outer shell (at Offset 1).")):
        o = S(nm, 'OUTPUT', 'NodeSocketBool',
              desc=d + " Name it in the modifier's Output Attributes to use it.")
        o.attribute_domain = 'FACE'

    G = Graph(ng)
    link, feed, mk, gi = G.link, G.feed, G.mk, G.gi

    # ---- frames, created in signal order (one frame = one layout band) -----------
    F_sel = G.frame("Selection Gate  (GNG_SelectionGate)")
    F_split = G.frame("Split Selected Faces  (unselected pass through)")
    F_data = G.frame("Source Data  (direction, offsets, rim direction)")
    F_seg = G.frame("Rim Segments  (Rim Loops + 1, or profile points - 1)")
    F_inner = G.frame("Inner Shell + Rim")
    F_outer = G.frame("Outer Shell")
    F_weld = G.frame("Weld Rim To Outer Shell  (by source vertex)")
    F_only = G.frame("Only Rim  (drop the inner shell)")
    F_pos = G.frame("Place Vertices  (offsets, inset, push, profile)")
    F_kind = G.frame("Rim Edges  (edges across rim layers)")
    F_wt = G.frame("Crease & Bevel Weight")
    F_mat = G.frame("Material Offsets")
    F_vc = G.frame("Vertex Crease Consumed  (unless kept)")
    F_out = G.frame("Output  (face parts, cleanup, join unselected)")

    def group(ng_, parent, label):
        nd = mk("GeometryNodeGroup", parent, name=label, label=label)
        nd.node_tree = ng_
        return nd

    # ============================================================ 1. SELECTION GATE
    g = gi(F_sel, "Selection", "Invert Selection", "Grow / Shrink Selection")
    gnode = group(gate.ensure(), F_sel, "Selection Gate")
    link(g, "Selection", gnode, gate.SEL)
    link(g, "Invert Selection", gnode, gate.INV)
    link(g, "Grow / Shrink Selection", gnode, gate.GROW)

    # ============================================================ 2. SPLIT
    g = gi(F_split, "Geometry")
    split = mk("GeometryNodeSeparateGeometry", F_split, domain='FACE',
               label="Split Selected Faces")
    link(g, "Geometry", split, "Geometry"); link(gnode, gate.SEL, split, "Selection")

    # ============================================================ 3. SOURCE DATA
    g = gi(F_data, "Thickness", "Offset", "Even Thickness", "Thickness Weight",
           "Zero Weight Factor", "Invert Weight", "Use Custom Direction",
           "Custom Direction Rotation")
    src = group(data_ng, F_data, "Source Data")
    link(split, "Selection", src, "Geometry")
    for a, b in (("Thickness", "Thickness"), ("Offset", "Offset"),
                 ("Even Thickness", "Even Thickness"), ("Thickness Weight", "Weight"),
                 ("Zero Weight Factor", "Zero Weight Factor"),
                 ("Invert Weight", "Invert Weight"),
                 ("Use Custom Direction", "Use Custom Direction"),
                 ("Custom Direction Rotation", "Custom Direction Rotation")):
        link(g, a, src, b)

    # ============================================================ 4. RIM SEGMENTS
    g = gi(F_seg, "Rim Loops", "Profile Curve", "Profile Sets Rim Loops", "Fill Rim")
    oinfo = mk("GeometryNodeObjectInfo", F_seg, transform_space='ORIGINAL',
               label="Profile Curve")
    link(g, "Profile Curve", oinfo, "Object")
    c2p = mk("GeometryNodeCurveToPoints", F_seg, mode='EVALUATED', label="Profile Points")
    link(oinfo, "Geometry", c2p, "Curve")
    psize = mk("GeometryNodeAttributeDomainSize", F_seg, component='POINTCLOUD')
    link(c2p, "Points", psize, "Geometry")
    pcount = (psize, "Point Count")
    use_pts = G.bmath('AND', (g, "Profile Sets Rim Loops"),
                      G.cmp('INT', 'GREATER_EQUAL', pcount, 2, F_seg, label="Has Profile"),
                      F_seg, label="Loops From Profile")
    nseg = G.switch('INT', use_pts, G.imath('ADD', (g, "Rim Loops"), 1, F_seg),
                    G.imath('SUBTRACT', pcount, 1, F_seg), F_seg, label="Rim Segments")
    iters = G.switch('INT', (g, "Fill Rim"), 0, nseg, F_seg, label="Extrusions")

    # ============================================================ 5. INNER SHELL + RIM
    g = gi(F_inner, "Thickness")
    t_pos = G.cmp('FLOAT', 'GREATER_THAN', (g, "Thickness"), 0.0, F_inner,
                  label="Thickness > 0")
    inner = G.store((src, "Geometry"), 'INT', 'FACE', A_PART, PART_INNER, F_inner,
                    label="Tag Inner Faces")
    # the inner shell faces away from the solid when it lies below the outer one;
    # flipped BEFORE the rim grows off it, so the rim inherits a matching winding
    iflip = mk("GeometryNodeFlipFaces", F_inner, label="Flip Inner  (T > 0)")
    feed(iflip, "Mesh", inner); feed(iflip, "Selection", t_pos)
    rim = group(rim_ng, F_inner, "Grow Rim")
    link(iflip, "Mesh", rim, "Geometry")
    feed(rim, "Segments", nseg); feed(rim, "Extrusions", iters)

    # ============================================================ 6. OUTER SHELL
    g = gi(F_outer, "Thickness")
    t_neg = G.cmp('FLOAT', 'LESS_THAN', (g, "Thickness"), 0.0, F_outer,
                  label="Thickness < 0")
    x = G.store((src, "Geometry"), 'INT', 'FACE', A_PART, PART_OUTER, F_outer,
                label="Tag Outer Faces")
    x = G.store(x, 'INT', 'POINT', A_K, nseg, F_outer, label="Layer = Last")
    x = G.store(x, 'INT', 'EDGE', A_EK, EK_OUTER, F_outer,
                sel=G.cmp('INT', 'EQUAL', G.named('INT', A_EK, F_outer), EK_INNER, F_outer),
                label="Tag Outer Border")
    oflip = mk("GeometryNodeFlipFaces", F_outer, label="Flip Outer  (T < 0)")
    feed(oflip, "Mesh", x); feed(oflip, "Selection", t_neg)

    # ============================================================ 7. WELD
    join = mk("GeometryNodeJoinGeometry", F_weld, label="Shells + Rim")
    link(oflip, "Mesh", join, "Geometry")
    link(rim, "Geometry", join, "Geometry")
    top_ring = G.bmath('AND', G.named('BOOLEAN', A_BND, F_weld),
                       G.cmp('INT', 'EQUAL', G.named('INT', A_K, F_weld), nseg, F_weld,
                             label="Last Layer"),
                       F_weld, label="Outer Border + Last Rim Ring")
    weld = group(weld_ng, F_weld, "Index Weld")
    link(join, "Geometry", weld, "Geometry")
    feed(weld, "Selection", top_ring)
    feed(weld, "Key", G.named('INT', A_SRC, F_weld))

    # ============================================================ 8. ONLY RIM
    g = gi(F_only, "Only Rim", "Fill Rim")
    only = G.bmath('AND', (g, "Only Rim"), (g, "Fill Rim"), F_only, label="Only Rim + Fill")
    is_drop = G.bmath('AND', only,
                      G.cmp('INT', 'EQUAL', G.named('INT', A_PART, F_only), PART_INNER, F_only,
                            label="Inner Face"),
                      F_only, label="Drop These Faces")
    dele = mk("GeometryNodeDeleteGeometry", F_only, domain='FACE', mode='ALL',
              label="Drop Inner Shell")
    link(weld, "Geometry", dele, "Geometry"); feed(dele, "Selection", is_drop)

    # ============================================================ 9. PLACE VERTICES
    g = gi(F_pos, "Profile Sets Rim Loops", "Inset", "Push", "Even Rim Offset")
    shp = group(shape_ng, F_pos, "Place Vertices")
    link(dele, "Geometry", shp, "Geometry")
    link(oinfo, "Geometry", shp, "Profile")
    feed(shp, "Segments", nseg)
    for nm in ("Profile Sets Rim Loops", "Inset", "Push", "Even Rim Offset"):
        link(g, nm, shp, nm)

    # ============================================================ 10. RIM EDGES
    ev2 = mk("GeometryNodeInputMeshEdgeVertices", F_kind)
    kk = G.named('INT', A_K, F_kind)
    k1 = G.at_index('POINT', 'INT', kk, (ev2, "Vertex Index 1"), F_kind, label="Layer 1")
    k2 = G.at_index('POINT', 'INT', kk, (ev2, "Vertex Index 2"), F_kind, label="Layer 2")
    xrim = G.cmp('INT', 'NOT_EQUAL', k1, k2, F_kind, label="Crosses Layers")
    kinds = G.store((shp, "Geometry"), 'INT', 'EDGE', A_EK, EK_RIM, F_kind, sel=xrim,
                    label="Tag Rim Edges")

    # ============================================================ 11. CREASE / BEVEL
    def mode_index(menu_name, parent):
        gm = gi(parent, menu_name)
        ms = mk("GeometryNodeMenuSwitch", parent, data_type='INT',
                label=f"{menu_name}  (menu -> index)")
        # rename the two default items instead of clearing them: item identifiers are
        # handed out in creation order and a modifier stores the identifier, so ids
        # 0..5 keep saved Solidify Plus values meaning the same mode
        ms.enum_items[0].name, ms.enum_items[1].name = RIM_MODES[0], RIM_MODES[1]
        for it in RIM_MODES[2:]:
            ms.enum_items.new(it)
        for i, it in enumerate(RIM_MODES):
            isock(ms, it).default_value = i
        link(gm, menu_name, ms, "Menu")
        return (ms, "Output")

    cr_idx = mode_index("Rim Crease By", F_wt)
    bw_idx = mode_index("Rim Bevel Weight By", F_wt)
    x = kinds
    for word, attr, midx in (("Crease", "crease_edge", cr_idx),
                             ("Bevel Weight", "bevel_weight_edge", bw_idx)):
        gw = gi(F_wt, f"Inner {word}", f"Outer {word}", f"Rim Loop {word}", f"Rim {word}",
                f"Rim {word} Angle")
        wn = mk("GeometryNodeGroup", F_wt, label=f"Write {word}")
        wn.node_tree = weight_ng
        feed(wn, "Geometry", x)
        isock(wn, "Attribute Name").default_value = attr
        link(gw, f"Inner {word}", wn, "Inner Border")
        link(gw, f"Outer {word}", wn, "Outer Border")
        link(gw, f"Rim Loop {word}", wn, "Rim Loops")
        link(gw, f"Rim {word}", wn, "Rim Edges")
        link(gw, f"Rim {word} Angle", wn, "Rim Angle")
        feed(wn, "Rim Mode", midx)
        x = (wn, "Geometry")

    # ============================================================ 12. MATERIALS
    g = gi(F_mat, "Shell Material Offset", "Rim Material Offset")
    part = G.named('INT', A_PART, F_mat)
    is_inner = G.cmp('INT', 'EQUAL', part, PART_INNER, F_mat, label="Inner Face")
    is_rimf = G.cmp('INT', 'EQUAL', part, PART_RIM, F_mat, label="Rim Face")
    add = G.switch('INT', is_rimf, G.switch('INT', is_inner, 0,
                   (g, "Shell Material Offset"), F_mat), (g, "Rim Material Offset"), F_mat,
                   label="Offset Per Face")
    midx = (mk("GeometryNodeInputMaterialIndex", F_mat), "Material Index")
    newm = G.imath('MAXIMUM', G.imath('ADD', midx, add, F_mat), 0, F_mat,
                   label="Index + Offset  (>= 0)")
    smi = mk("GeometryNodeSetMaterialIndex", F_mat, label="Offset Materials")
    feed(smi, "Geometry", x); feed(smi, "Material Index", newm)

    # ============================================================ 13. VERTEX CREASE
    g = gi(F_vc, "Keep Vertex Crease")
    uses_vc = G.bmath('OR', G.cmp('INT', 'EQUAL', cr_idx, MODE_VERTEX_CREASE, F_vc),
                      G.cmp('INT', 'EQUAL', bw_idx, MODE_VERTEX_CREASE, F_vc), F_vc,
                      label="A Rim Mode Is Vertex Crease")
    consume = G.bmath('NIMPLY', uses_vc, (g, "Keep Vertex Crease"), F_vc,
                      label="Consume  (and not kept)")
    rmvc = mk("GeometryNodeRemoveAttribute", F_vc, label="Remove crease_vert")
    link(smi, "Geometry", rmvc, "Geometry"); isock(rmvc, "Name").default_value = "crease_vert"
    vcsw = G.switch('GEOMETRY', consume, (smi, "Geometry"), (rmvc, "Geometry"), F_vc,
                    label="Consume?")

    # ============================================================ 14. OUTPUT
    cap = mk("GeometryNodeCaptureAttribute", F_out, domain='FACE', label="Face Parts")
    cap.capture_items.new('INT', "Part")
    feed(cap, "Geometry", vcsw); feed(cap, "Part", G.named('INT', A_PART, F_out))
    rm = mk("GeometryNodeRemoveAttribute", F_out, label="Drop Temp Attributes")
    link(cap, "Geometry", rm, "Geometry")
    isock(rm, "Pattern Mode").default_value = "Wildcard"
    isock(rm, "Name").default_value = "__sp_*"
    jout = mk("GeometryNodeJoinGeometry", F_out, label="+ Unselected Faces")
    link(split, "Inverted", jout, "Geometry")
    link(rm, "Geometry", jout, "Geometry")
    go = mk("NodeGroupOutput", F_out)
    link(jout, "Geometry", go, "Geometry")
    for nm, pid in (("Rim", PART_RIM), ("Inner Shell", PART_INNER),
                    ("Outer Shell", PART_OUTER)):
        feed(go, nm, G.cmp('INT', 'EQUAL', (cap, "Part"), pid, F_out, label=f"Is {nm}"))

    # menu defaults are only valid once their Menu Switch has defined the items
    m_cr.default_value = "Angle Threshold"
    m_bw.default_value = "Angle Threshold"
    return ng


# ============================================================================= RUN
def main():
    weld_ng = build_index_weld()
    weight_ng = build_edge_weight()
    data_ng, rim_ng, shape_ng = build_source_data(), build_rim(), build_shape()
    ng = build_main(weld_ng, weight_ng, data_ng, rim_ng, shape_ng)
    for helper in (weld_ng, weight_ng, data_ng, rim_ng, shape_ng):
        helper.use_fake_user = True
        if hasattr(helper, "color_tag"):
            helper.color_tag = 'GEOMETRY'

    # ---- demo object: a curved open sheet with an L-shaped notch, vertex creases on
    # its outer corners, and a rim with loops, push and creases
    for _o in list(bpy.data.objects):
        bpy.data.objects.remove(_o, do_unlink=True)
    me = bpy.data.meshes.new("GN_Demo")
    bm = bmesh.new()
    bmesh.ops.create_grid(bm, x_segments=6, y_segments=6, size=1.0)
    notch = [f for f in bm.faces if f.calc_center_median().x > 0.3
             and f.calc_center_median().y > 0.3]
    bmesh.ops.delete(bm, geom=notch, context='FACES')
    for vtx in bm.verts:
        vtx.co.z = 0.25 * vtx.co.x * vtx.co.x
    bm.to_mesh(me); bm.free()
    cv = me.attributes.new("crease_vert", 'FLOAT', 'POINT')
    for vtx in me.vertices:
        if abs(abs(vtx.co.x) - 1) < 1e-4 and abs(abs(vtx.co.y) - 1) < 1e-4:
            cv.data[vtx.index].value = 1.0
    obj = bpy.data.objects.new("GN_Demo", me)
    bpy.context.scene.collection.objects.link(obj)
    md = obj.modifiers.new(NAME, "NODES"); md.node_group = ng
    ids = {it.name: it.identifier for it in ng.interface.items_tree
           if it.item_type == 'SOCKET' and it.in_out == 'INPUT'}
    md[ids["Rim Loops"]] = 2
    md[ids["Push"]] = 0.03
    md[ids["Outer Crease"]] = 1.0
    md[ids["Inner Crease"]] = 1.0
    md[ids["Rim Crease"]] = 1.0
    sub = obj.modifiers.new("Subdivision", "SUBSURF"); sub.levels = 2
    obj.select_set(True); bpy.context.view_layer.objects.active = obj

    # ---- publish
    ng.asset_mark()
    ng.asset_data.catalog_id = CAT
    ng.asset_data.tags.new("ST3E")
    ng.asset_data.description = (
        "Solidify with rim loops, rim shape (push / profile curve), crease and bevel "
        "weight per edge group (rim edges by corner, angle or vertex crease), face "
        "selection, thickness weight, inset and material offsets.")
    ng.is_modifier = True
    ng.is_tool = False

    bpy.ops.wm.save_as_mainfile(filepath=PATH)
    print("SAVED", PATH, "nodes:", len(ng.nodes))


if __name__ == "__main__":
    main()
    sys.stdout.flush()
    os._exit(0)
