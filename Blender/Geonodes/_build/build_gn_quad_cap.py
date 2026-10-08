"""Build GN_QuadCap.blend -- a Geometry Nodes MODIFIER that closes open borders
(holes) with a proper cap instead of one n-gon.

Cap Type picks the topology: a quad GRID (the default), a single N-GON face, or a
CENTER VERTEX star of triangles. Inset Rings lays quad rings in from the border
first, so the cap keeps the border's edge flow. Caps can be given planar UVs and
their own material / material index.

Every selected, closed border loop of N vertices is filled with an a x b quad grid
(2a + 2b = N, rounded up to even). The grid rim is mapped onto the loop points and
the interior is placed with a Coons patch (bilinear blend of the four rim sides), so
any loop shape gets an evenly spaced quad fill. A loop with an ODD vertex count gets
one extra rim slot that duplicates a corner vertex; welding collapses that corner quad
into the single triangle an odd loop cannot avoid.

Cap winding is derived from the faces next to the hole (the cap runs every border
edge opposite to its neighbour face), so the caps come out with consistent normals.
Loose edge loops (no adjacent face) can be capped too; their facing is arbitrary.

Run headless:
  "C:\\Program Files\\Blender Foundation\\Blender 5.0\\blender.exe" --background \
      --factory-startup --python build_gn_quad_cap.py
"""
import bpy, bmesh, sys, os, math
from mathutils import Matrix

GEO  = r"D:\Stephko_Tooling\Toolings\Blender\Geonodes"
NAME = "GN_QuadCap"
PATH = os.path.join(GEO, NAME + ".blend")
CAT  = "8872522f-45b7-4541-a557-5b69bcbfcee2"   # ST3E/Generate (adds geometry)

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

for _ng in list(bpy.data.node_groups):
    if _ng.name == NAME:
        bpy.data.node_groups.remove(_ng)

ng = bpy.data.node_groups.new(NAME, "GeometryNodeTree")
n, links = ng.nodes, ng.links
def link(a, ai, b, bi): links.new(osock(a, ai), isock(b, bi))

# ============================================================================= INTERFACE
iface = ng.interface
def sock(name, in_out, stype, parent=None, default=None, mn=None, mx=None,
         subtype=None, desc=""):
    s = iface.new_socket(name, in_out=in_out, socket_type=stype,
                         parent=parent if parent else None)
    if default is not None: s.default_value = default
    if mn is not None:      s.min_value = mn
    if mx is not None:      s.max_value = mx
    if subtype:             s.subtype = subtype
    s.description = desc
    return s

sock("Geometry", 'INPUT', 'NodeSocketGeometry',
     desc="Mesh whose open borders (holes) get capped.")
sock("Selection", 'INPUT', 'NodeSocketBool', default=True,
     desc="Border vertices that may be capped. A border loop is capped only when ALL "
          "of its vertices are selected, so a vertex group around one hole caps just "
          "that hole.")
sock("Invert Selection", 'INPUT', 'NodeSocketBool', default=False,
     desc="Flip the selection: cap every border loop EXCEPT the selected ones.")

p_cap = iface.new_panel("Quad Cap")
sock("Corner Offset", 'INPUT', 'NodeSocketInt', parent=p_cap, default=0,
     desc="Rotates the grid around the loop by this many border vertices. Moves the "
          "four grid corners (and the triangle of an odd loop) to other border "
          "vertices -- use it to line the grid up with the surrounding edge flow.")
sock("Side Balance", 'INPUT', 'NodeSocketInt', parent=p_cap, default=0,
     desc="Shifts border vertices between the grid's two side pairs. 0 = as square as "
          "possible (a 16-vertex loop becomes 4 x 4). +1 makes it 5 x 3, -1 makes it "
          "3 x 5. Use it for long, narrow holes. Clamped so every side keeps at least "
          "one segment.")
sock("Max Border Vertices", 'INPUT', 'NodeSocketInt', parent=p_cap, default=0, mn=0,
     desc="Skip border loops with more vertices than this. 0 = no limit. Handy to cap "
          "the small holes of a mesh while leaving its big outer rim open.")
sock("Cap Loose Edge Loops", 'INPUT', 'NodeSocketBool', parent=p_cap, default=True,
     desc="Also fill closed loops of loose edges (edges without any face, e.g. a "
          "circle primitive). There is no neighbour face to take the winding from, so "
          "their facing is arbitrary -- use Flip Cap Normals if needed.")

p_shp = iface.new_panel("Shape")
sock("Relax Iterations", 'INPUT', 'NodeSocketInt', parent=p_shp, default=0, mn=0, mx=200,
     desc="Smooths the cap interior with the border held fixed. Evens out the grid on "
          "concave or irregular loops; 0 keeps the pure Coons patch.")
sock("Dome", 'INPUT', 'NodeSocketFloat', parent=p_shp, default=0.0, mn=-4.0, mx=4.0,
     desc="Bulges the cap into a round dome along the cap normal: height at the centre "
          "as a fraction of the loop's "
          "average radius. Positive = outward (away from the mesh), negative = inward. "
          "About 0.5-1.0 rounds a cylinder end.")

p_out = iface.new_panel("Output")
sock("Merge With Mesh", 'INPUT', 'NodeSocketBool', parent=p_out, default=True,
     desc="Weld the cap rims onto the border vertices so cap and mesh are one "
          "connected surface. Off keeps the caps as separate pieces sitting in the "
          "holes (odd loops then keep a zero-area corner instead of a triangle).")
sock("Merge Distance", 'INPUT', 'NodeSocketFloat', parent=p_out, default=0.0001,
     mn=0.0, subtype='DISTANCE',
     desc="Weld distance for the cap rims. Rim vertices sit exactly on the border "
          "vertices, so the default tiny value is enough.")
sock("Flip Cap Normals", 'INPUT', 'NodeSocketBool', parent=p_out, default=False,
     desc="Reverse the facing of all caps.")

sock("Geometry", 'OUTPUT', 'NodeSocketGeometry',
     desc="The mesh with its selected holes closed by quad caps.")
s_cap = sock("Cap", 'OUTPUT', 'NodeSocketBool',
     desc="True on the faces that were added as caps. Name it in the modifier's "
          "Output Attributes to use it for materials or selections.")
s_cap.attribute_domain = 'FACE'

# --- everything below is declared AFTER the outputs on purpose ----------------
# Socket identifiers are handed out in creation order and a modifier stores its
# values per identifier, so inserting a socket mid-panel would silently re-point
# every value below it on modifiers already living in scenes. New sockets are
# declared last and only MOVED into their panel afterwards -- the move is
# cosmetic, the identifier travels with the socket.
p_cap.name = "Cap"
sk_ctype = sock("Cap Type", 'INPUT', 'NodeSocketMenu',
     desc="How each border loop is filled. Quad Grid = an a x b grid of quads (plus one "
          "triangle on an odd loop). N-gon = a single face, no new topology, like a "
          "plain fill. Center Vertex = a star of triangles meeting at one new vertex in "
          "the middle of the hole.")

p_ins = iface.new_panel("Inset")
sock("Inset Rings", 'INPUT', 'NodeSocketInt', parent=p_ins, default=0, mn=0, mx=32,
     desc="Quad rings laid inside the border before the cap itself, each one stepping "
          "Inset Amount further in. Keeps the border's edge flow around the hole and "
          "gives the cap a clean support loop. 0 = cap straight off the border.")
sock("Inset Amount", 'INPUT', 'NodeSocketFloat', parent=p_ins, default=0.05, mn=0.0,
     subtype='DISTANCE',
     desc="How far each inset ring steps toward the centre of the hole. Vertices stop "
          "short of collapsing, so an oversized amount piles them up near the centre "
          "instead of turning the cap inside out.")
sock("Inset Relative", 'INPUT', 'NodeSocketBool', parent=p_ins, default=False,
     desc="Read Inset Amount as a fraction of the loop's average radius instead of a "
          "distance, so holes of different sizes get proportional insets.")

p_uv = iface.new_panel("UVs")
sock("Create UVs", 'INPUT', 'NodeSocketBool', parent=p_uv, default=False,
     desc="Give the cap faces UVs, projected flat onto the plane of the hole. Off "
          "leaves the mesh's UV maps exactly as they are.")
sock("UV Map", 'INPUT', 'NodeSocketString', parent=p_uv, default="UVMap",
     desc="Name of the UV map the cap UVs are written to. Use the mesh's existing map "
          "name to extend it, or a new name to keep the caps in their own map.")
sk_uvmode = sock("UV Mode", 'INPUT', 'NodeSocketMenu', parent=p_uv,
     desc="Fit Loop scales each cap so its hole fills the 0-1 square, whatever its size. "
          "World Units keeps the cap at object scale, so the texture density matches the "
          "rest of the mesh (set UV Scale to your usual units-per-tile).")
sock("UV Scale", 'INPUT', 'NodeSocketFloat', parent=p_uv, default=1.0,
     desc="Multiplies the cap UVs about the centre of the hole.")
sock("UV Rotation", 'INPUT', 'NodeSocketFloat', parent=p_uv, default=0.0, subtype='ANGLE',
     desc="Turns the UV projection around the cap normal.")

p_mat = iface.new_panel("Material")
sk_matidx = sock("Cap Material Index", 'INPUT', 'NodeSocketInt', parent=p_mat, mn=-1,
     desc="Material slot -- the 3ds Max 'material ID' -- given to the cap faces. 0 is the "
          "object's first slot. Set it to -1 to leave the caps alone, which parks them on "
          "an empty slot of their own, the way freshly generated geometry always starts.")
sk_matidx.default_value = 0
sock("Use Cap Material", 'INPUT', 'NodeSocketBool', parent=p_mat, default=False,
     desc="Assign the Cap Material below to the cap faces. Off leaves them with whatever "
          "the Cap Material Index selects.")
sock("Cap Material", 'INPUT', 'NodeSocketMaterial', parent=p_mat,
     desc="Material assigned to the cap faces when Use Cap Material is on. It is added "
          "to the object's material slots if it is not there yet.")

# file the newcomers where they belong in the UI -- panel order reads as the
# evaluation order: Cap -> Inset -> Shape -> UVs -> Material -> Output
iface.move_to_parent(sk_ctype, p_cap, 0)
iface.move(p_ins, 6)
iface.move(p_uv, 8)
iface.move(p_mat, 9)

gout = n.new("NodeGroupOutput")

# ============================================================================= FRAMES
def frame(label, parent=None):
    f = n.new("NodeFrame"); f.label = label; f.location = (0, 0)
    f.use_custom_color = True; f.color = (0.18, 0.20, 0.26)
    if parent: f.parent = parent
    return f

F_sel = frame("Selection Gate  (Selection XOR Invert Selection)")
F_brd = frame("Open Borders  (edges with <= 1 face, selected)")
F_wnd = frame("Border Winding  (next vertex along the neighbour face)")
F_crv = frame("Border Loops -> Curves  (closed loops only, size filter)")
F_fei = frame("For Each Border Loop  (input)")
F_ori = frame("Loop Orientation  (reverse to oppose the neighbour faces)")
F_ctr = frame("Loop Centre, Radius & Inset Distance")
F_sid = frame("Grid Sides  (even N' = 2a + 2b)")
F_grd = frame("Cap Grid  (a x b quads, i / j from position)")
F_map = frame("Rim Index Map  (grid rim -> loop point)")
F_cns = frame("Coons Patch  (blend of the four rim sides) + rim flag")
F_ngn = frame("N-gon Cap  (one face on the loop)")
F_fan = frame("Center Vertex Cap  (triangle star)")
F_typ = frame("Cap Type  (Quad Grid / N-gon / Center Vertex)")
F_rpi = frame("Relax  (input)")
F_rlx = frame("Relax Interior  (rim pinned)")
F_rpo = frame("Relax  (output)")
F_dom = frame("Dome  (bulge along cap normal)")
F_bnd = frame("Inset Rings  (quad band from the border inward)")
F_uv  = frame("Cap UVs  (planar in the plane of the hole)")
F_feo = frame("For Each Border Loop  (output)")
F_cpo = frame("Cap Output  (Cap field, flip)")
F_mat = frame("Cap Material & Material Index")
F_wld = frame("Weld Caps To Mesh")
F_cln = frame("Cleanup  (drop temp attributes)")

_cursor = {}
def mk(idname, parent=None, loc=None, **props):
    node = n.new(idname)
    for k, v in props.items(): setattr(node, k, v)
    if parent: node.parent = parent
    if loc is None:                       # rough placement; the tidy engine lays out
        x, y = _cursor.get(parent, (0, 0))
        loc = (x, y); _cursor[parent] = (x + 220, y)
    node.location = loc
    return node

def feed(node, key, src):
    """src: constant, or (node, socket) tuple."""
    if isinstance(src, tuple): link(src[0], src[1], node, key)
    else: isock(node, key).default_value = src

def imath(op, a, b=None, parent=None):
    nd = mk("FunctionNodeIntegerMath", parent, operation=op)
    feed(nd, "Value", a)
    if b is not None: feed(nd, "Value_001", b)
    return (nd, "Value")
def fmath(op, a, b=None, parent=None, c=None):
    nd = mk("ShaderNodeMath", parent, operation=op)
    feed(nd, "Value", a)
    if b is not None: feed(nd, "Value_001", b)
    if c is not None: feed(nd, "Value_002", c)
    return (nd, "Value")
def vmath(op, a, b=None, parent=None, out="Vector"):
    nd = mk("ShaderNodeVectorMath", parent, operation=op)
    feed(nd, "Vector", a)
    if b is not None:
        if op == 'SCALE': feed(nd, "Scale", b)
        else:             feed(nd, "Vector_001", b)
    return (nd, out)
def icmp(op, a, b, parent=None):
    nd = mk("FunctionNodeCompare", parent, data_type='INT', operation=op)
    feed(nd, "A_INT", a); feed(nd, "B_INT", b)
    return (nd, "Result")
def bmath(op, a, b=None, parent=None):
    nd = mk("FunctionNodeBooleanMath", parent, operation=op)
    feed(nd, 0, a)
    if b is not None: feed(nd, 1, b)
    return (nd, "Boolean")
def mixv(fac, a, b, parent=None):
    nd = mk("ShaderNodeMix", parent, data_type='VECTOR')
    feed(nd, "Factor_Float", fac); feed(nd, "A_Vector", a); feed(nd, "B_Vector", b)
    return (nd, "Result_Vector")
def gi(parent, *names):
    """Per-function Group Input (criterion 2)."""
    g = mk("NodeGroupInput", parent)
    for s in g.outputs:
        if s.name and s.name not in names: s.hide = True
    return g
def named(dtype, name, parent):
    nd = mk("GeometryNodeInputNamedAttribute", parent, data_type=dtype)
    isock(nd, "Name").default_value = name
    return (nd, "Attribute")

A_VID, A_NEXT, A_RIM = "__qc_vid", "__qc_next", "__qc_rim"

# ============================================================================= 1. SELECTION GATE
g = gi(F_sel, "Selection", "Invert Selection")
sel = bmath('XOR', (g, "Selection"), (g, "Invert Selection"), F_sel)

# ============================================================================= 2. OPEN BORDERS
g = gi(F_brd, "Cap Loose Edge Loops")
enb = mk("GeometryNodeInputMeshEdgeNeighbors", F_brd)
is_border = icmp('EQUAL', (enb, "Face Count"), 1, F_brd)
is_loose  = icmp('EQUAL', (enb, "Face Count"), 0, F_brd)
loose_ok  = bmath('AND', is_loose, (g, "Cap Loose Edge Loops"), F_brd)
cand      = bmath('OR', is_border, loose_ok, F_brd)
edge_sel  = bmath('AND', cand, sel, F_brd)          # point selection -> edge (AND)

# ============================================================================= 3. BORDER WINDING
# For every border vertex v find the face corner whose NEXT edge is a border edge:
# the neighbour face runs that edge v -> next(v). The cap must run it the other way.
idx_w = mk("GeometryNodeInputIndex", F_wnd)
eoc   = mk("GeometryNodeEdgesOfCorner", F_wnd)
link(idx_w, "Index", eoc, "Corner Index")
fae   = mk("GeometryNodeFieldAtIndex", F_wnd, domain='EDGE', data_type='INT')
link(enb, "Face Count", fae, "Value"); link(eoc, "Next Edge Index", fae, "Index")
nb    = icmp('EQUAL', (fae, "Value"), 1, F_wnd)
w     = fmath('SUBTRACT', 1.0, nb, F_wnd)           # 0 = corner leads onto the border
cov   = mk("GeometryNodeCornersOfVertex", F_wnd)
link(idx_w, "Index", cov, "Vertex Index"); feed(cov, "Weights", w)
isock(cov, "Sort Index").default_value = 0
wat   = mk("GeometryNodeFieldAtIndex", F_wnd, domain='CORNER', data_type='FLOAT')
feed(wat, "Value", w); link(cov, "Corner Index", wat, "Index")
w_ok  = mk("FunctionNodeCompare", F_wnd, data_type='FLOAT', operation='LESS_THAN')
link(wat, "Value", w_ok, "A"); isock(w_ok, "B").default_value = 0.5
has_c = icmp('GREATER_THAN', (cov, "Total"), 0, F_wnd)
valid = bmath('AND', (w_ok, "Result"), has_c, F_wnd)
ocf   = mk("GeometryNodeOffsetCornerInFace", F_wnd)
link(cov, "Corner Index", ocf, "Corner Index"); isock(ocf, "Offset").default_value = 1
voc   = mk("GeometryNodeVertexOfCorner", F_wnd)
link(ocf, "Corner Index", voc, "Corner Index")
nxt   = mk("GeometryNodeSwitch", F_wnd, input_type='INT')
feed(nxt, "Switch", valid); isock(nxt, "False").default_value = -1
link(voc, "Vertex Index", nxt, "True")

# ============================================================================= 4. LOOPS -> CURVES
g_geo = gi(F_crv, "Geometry")
st_vid = mk("GeometryNodeStoreNamedAttribute", F_crv, data_type='INT', domain='POINT')
link(g_geo, "Geometry", st_vid, "Geometry"); isock(st_vid, "Name").default_value = A_VID
link(idx_w, "Index", st_vid, "Value")
st_nxt = mk("GeometryNodeStoreNamedAttribute", F_crv, data_type='INT', domain='POINT')
link(st_vid, "Geometry", st_nxt, "Geometry"); isock(st_nxt, "Name").default_value = A_NEXT
link(nxt, "Output", st_nxt, "Value")
m2c = mk("GeometryNodeMeshToCurve", F_crv)
link(st_nxt, "Geometry", m2c, "Mesh"); feed(m2c, "Selection", edge_sel)

g = gi(F_crv, "Max Border Vertices")
cyc  = mk("GeometryNodeInputSplineCyclic", F_crv)
slen = mk("GeometryNodeSplineLength", F_crv)
big3 = icmp('GREATER_EQUAL', (slen, "Point Count"), 3, F_crv)
nolim = icmp('EQUAL', (g, "Max Border Vertices"), 0, F_crv)
under = icmp('LESS_EQUAL', (slen, "Point Count"), (g, "Max Border Vertices"), F_crv)
size_ok = bmath('OR', nolim, under, F_crv)
loop_ok = bmath('AND', bmath('AND', (cyc, "Cyclic"), big3, F_crv), size_ok, F_crv)

# ============================================================================= 5. FOR EACH LOOP
fe_in  = mk("GeometryNodeForeachGeometryElementInput",  F_fei)
fe_out = mk("GeometryNodeForeachGeometryElementOutput", F_feo)
fe_in.pair_with_output(fe_out)
fe_out.domain = 'CURVE'
link(m2c, "Curve", fe_in, "Geometry"); feed(fe_in, "Selection", loop_ok)
E = (fe_in, "Element")

# --- 5a. orientation --------------------------------------------------------
def sample(geo, dtype, value, index, parent):
    nd = mk("GeometryNodeSampleIndex", parent, data_type=dtype, domain='POINT')
    feed(nd, "Geometry", geo); feed(nd, "Value", value); feed(nd, "Index", index)
    return (nd, "Value")
nx0  = sample(E, 'INT', named('INT', A_NEXT, F_ori), 0, F_ori)
vid1 = sample(E, 'INT', named('INT', A_VID,  F_ori), 1, F_ori)
same = icmp('EQUAL', nx0, vid1, F_ori)
rev  = mk("GeometryNodeReverseCurve", F_ori)
feed(rev, "Curve", E); feed(rev, "Selection", same)
C = (rev, "Curve")

# --- 5b0. loop centre, radius and inset distance ------------------------------
g = gi(F_ctr, "Inset Rings", "Inset Amount", "Inset Relative")
lpos = mk("GeometryNodeInputPosition", F_ctr)
cst  = mk("GeometryNodeAttributeStatistic", F_ctr, data_type='FLOAT_VECTOR', domain='POINT')
feed(cst, "Geometry", C); link(lpos, "Position", cst, "Attribute")
CEN  = (cst, "Mean")                                   # centre of the hole
rad_f = vmath('DISTANCE', (lpos, "Position"), CEN, F_ctr, out="Value")
rst  = mk("GeometryNodeAttributeStatistic", F_ctr, data_type='FLOAT', domain='POINT')
feed(rst, "Geometry", C); feed(rst, "Attribute", rad_f)
RAD  = (rst, "Mean")                                   # average radius of the loop
amt_sw = mk("GeometryNodeSwitch", F_ctr, input_type='FLOAT')
feed(amt_sw, "Switch", (g, "Inset Relative"))
feed(amt_sw, "False", (g, "Inset Amount"))
feed(amt_sw, "True", fmath('MULTIPLY', (g, "Inset Amount"), RAD, F_ctr))
AMT   = (amt_sw, "Output")                             # inset step per ring
RINGS = imath('MAXIMUM', (g, "Inset Rings"), 0, F_ctr)
INSET = fmath('MULTIPLY', AMT, RINGS, F_ctr)           # total inset of the cap itself
RAD_IN = fmath('MAXIMUM', fmath('SUBTRACT', RAD, INSET, F_ctr), 1e-4, F_ctr)

# --- 5b. grid sides ---------------------------------------------------------
g = gi(F_sid, "Side Balance")
dsz = mk("GeometryNodeAttributeDomainSize", F_sid, component='CURVE')
feed(dsz, "Geometry", C)
N    = (dsz, "Point Count")
odd  = imath('FLOORED_MODULO', N, 2, F_sid)
Np   = imath('ADD', N, odd, F_sid)                       # even rim slot count
half = imath('DIVIDE_FLOOR', Np, 2, F_sid)
a0   = imath('DIVIDE_FLOOR', Np, 4, F_sid)
a1   = imath('ADD', a0, (g, "Side Balance"), F_sid)
hm1  = imath('SUBTRACT', half, 1, F_sid)
a    = imath('MINIMUM', imath('MAXIMUM', a1, 1, F_sid), hm1, F_sid)
b    = imath('SUBTRACT', half, a, F_sid)

# --- 5c. grid ---------------------------------------------------------------
grid = mk("GeometryNodeMeshGrid", F_grd)
feed(grid, "Size X", a); feed(grid, "Size Y", b)
feed(grid, "Vertices X", imath('ADD', a, 1, F_grd))
feed(grid, "Vertices Y", imath('ADD', b, 1, F_grd))
gpos = mk("GeometryNodeInputPosition", F_grd)
gsep = mk("ShaderNodeSeparateXYZ", F_grd); link(gpos, "Position", gsep, "Vector")
# grid spans -a/2..a/2 with unit spacing, so i = round(x + a/2)
i_f  = fmath('ROUND', fmath('MULTIPLY_ADD', a, 0.5, F_grd, c=(gsep, "X")), None, F_grd)
j_f  = fmath('ROUND', fmath('MULTIPLY_ADD', b, 0.5, F_grd, c=(gsep, "Y")), None, F_grd)
u_f  = fmath('DIVIDE', i_f, a, F_grd)
v_f  = fmath('DIVIDE', j_f, b, F_grd)
cap_uv = mk("GeometryNodeCaptureAttribute", F_grd, domain='POINT')
for nm in ("i", "j", "u", "v"):
    cap_uv.capture_items.new('FLOAT', nm)
link(grid, "Mesh", cap_uv, "Geometry")
feed(cap_uv, "i", i_f); feed(cap_uv, "j", j_f); feed(cap_uv, "u", u_f); feed(cap_uv, "v", v_f)
I, J = (cap_uv, "i"), (cap_uv, "j")
U, V = (cap_uv, "u"), (cap_uv, "v")

# --- 5d. rim index map --------------------------------------------------------
# GNG_QuadCapRimPoint: rim slot k -> position of the loop point it lands on.
HELPER = "GNG_QuadCapRimPoint"
def build_rim_helper():
    global n, links
    for _h in list(bpy.data.node_groups):
        if _h.name == HELPER: bpy.data.node_groups.remove(_h)
    hg = bpy.data.node_groups.new(HELPER, "GeometryNodeTree")
    main_n, main_links = n, links
    n, links = hg.nodes, hg.links
    hi = hg.interface
    s = hi.new_socket("Loop Curve", in_out='INPUT', socket_type='NodeSocketGeometry')
    s.description = "One closed border loop as a curve (its points in loop order)."
    hp = hi.new_panel("Rim Slot")
    s = hi.new_socket("Rim Slot", in_out='INPUT', socket_type='NodeSocketInt', parent=hp)
    s.description = ("Index into the grid rim, counted around it (0 .. N'-1, wraps). "
                     "N' is the loop size rounded up to even.")
    s = hi.new_socket("Corner Offset", in_out='INPUT', socket_type='NodeSocketInt', parent=hp)
    s.description = "Rotates the rim around the loop by this many points."
    hp2 = hi.new_panel("Inset")
    s = hi.new_socket("Centre", in_out='INPUT', socket_type='NodeSocketVector', parent=hp2)
    s.description = "Centre of the loop; the point the inset pulls toward."
    s = hi.new_socket("Inset", in_out='INPUT', socket_type='NodeSocketFloat', parent=hp2)
    s.description = ("Distance to pull the sampled point toward Centre. Clamped so a "
                     "point keeps at least 2% of its distance and can never cross over.")
    s = hi.new_socket("Position", in_out='OUTPUT', socket_type='NodeSocketVector')
    s.description = "Position of the loop point that this rim slot maps to."
    hF_sz = frame("Loop Size  (N points, even N')")
    hF_ix = frame("Slot -> Point Index  (odd loops: last slot = point 0)")
    hF_sm = frame("Sample Loop Position")
    g1 = gi(hF_sz, "Loop Curve")
    dsz = mk("GeometryNodeAttributeDomainSize", hF_sz, component='CURVE')
    link(g1, "Loop Curve", dsz, "Geometry")
    hN  = (dsz, "Point Count")
    hNp = imath('ADD', hN, imath('FLOORED_MODULO', hN, 2, hF_sz), hF_sz)
    g2 = gi(hF_ix, "Rim Slot", "Corner Offset")
    k = imath('FLOORED_MODULO', (g2, "Rim Slot"), hNp, hF_ix)
    k = imath('FLOORED_MODULO', k, hN, hF_ix)
    k = imath('ADD', k, (g2, "Corner Offset"), hF_ix)
    k = imath('FLOORED_MODULO', k, hN, hF_ix)
    g3 = gi(hF_sm, "Loop Curve")
    hp_ = mk("GeometryNodeInputPosition", hF_sm)
    smp = sample((g3, "Loop Curve"), 'FLOAT_VECTOR', (hp_, "Position"), k, hF_sm)
    hF_in = frame("Inset  (pull toward the centre of the loop)")
    g4 = gi(hF_in, "Centre", "Inset")
    d  = vmath('SUBTRACT', smp, (g4, "Centre"), hF_in)
    L  = vmath('LENGTH', d, None, hF_in, out="Value")
    f  = fmath('MAXIMUM',
               fmath('SUBTRACT', 1.0,
                     fmath('DIVIDE', (g4, "Inset"), fmath('MAXIMUM', L, 1e-6, hF_in), hF_in),
                     hF_in),
               0.02, hF_in)
    out = vmath('ADD', (g4, "Centre"), vmath('SCALE', d, f, hF_in), hF_in)
    ho = mk("NodeGroupOutput", None, (2400, 0))
    link(out[0], "Vector", ho, "Position")
    n, links = main_n, main_links
    return hg
rim_hg = build_rim_helper()

_off_gis = {}
def src_pos(k, parent=None, inset=None):
    """Rim slot -> the (inset) loop position it lands on. One local Group Input per
    frame carries Corner Offset, so no fan crosses the graph."""
    parent = parent or F_map
    if parent not in _off_gis: _off_gis[parent] = gi(parent, "Corner Offset")
    nd = mk("GeometryNodeGroup", parent); nd.node_tree = rim_hg
    feed(nd, "Loop Curve", C); feed(nd, "Rim Slot", k)
    feed(nd, "Corner Offset", (_off_gis[parent], "Corner Offset"))
    feed(nd, "Centre", CEN); feed(nd, "Inset", INSET if inset is None else inset)
    return (nd, "Position")
two_a = imath('MULTIPLY', a, 2, F_map)
k_B = I                                                   # bottom  (j = 0)
k_R = imath('ADD', a, J, F_map)                           # right   (i = a)
k_T = imath('SUBTRACT', imath('ADD', two_a, b, F_map), I, F_map)   # top (j = b)
k_L = imath('SUBTRACT', Np, J, F_map)                     # left    (i = 0)
P_B, P_R, P_T, P_L = src_pos(k_B), src_pos(k_R), src_pos(k_T), src_pos(k_L)
P00 = src_pos(0)
P10 = src_pos(a)
P11 = src_pos(imath('ADD', a, b, F_map))
P01 = src_pos(imath('ADD', two_a, b, F_map))

# --- 5e. Quad Grid cap: Coons patch -------------------------------------------
def store_rim(src, value, parent):
    """Flag the vertices sitting on the border: the weld candidates, and the points
    relax / dome must leave alone."""
    nd = mk("GeometryNodeStoreNamedAttribute", parent, data_type='BOOLEAN', domain='POINT')
    link(src, "Geometry", nd, "Geometry"); isock(nd, "Name").default_value = A_RIM
    feed(nd, "Value", value)
    return nd

S1  = mixv(V, P_B, P_T, F_cns)
S2  = mixv(U, P_L, P_R, F_cns)
S3  = mixv(V, mixv(U, P00, P10, F_cns), mixv(U, P01, P11, F_cns), F_cns)
Pc  = vmath('SUBTRACT', vmath('ADD', S1, S2, F_cns), S3, F_cns)
spc = mk("GeometryNodeSetPosition", F_cns)
link(cap_uv, "Geometry", spc, "Geometry"); feed(spc, "Position", Pc)
# rim = grid border: i in {0, a} or j in {0, b} (exact integer tests)
rim_grid = bmath('OR',
    bmath('OR', icmp('EQUAL', I, 0, F_cns), icmp('EQUAL', I, a, F_cns), F_cns),
    bmath('OR', icmp('EQUAL', J, 0, F_cns), icmp('EQUAL', J, b, F_cns), F_cns), F_cns)
cap_grid = store_rim(spc, rim_grid, F_cns)

# --- 5e2. N-gon cap: one face, no new topology --------------------------------
# Mesh Circle runs its rim counter-clockwise under a +Z normal, the same way round
# as the grid rim, so the orientation logic above covers these caps too.
ngi = mk("GeometryNodeInputIndex", F_ngn)
cir_n = mk("GeometryNodeMeshCircle", F_ngn, fill_type='NGON')
feed(cir_n, "Vertices", N)
sp_n = mk("GeometryNodeSetPosition", F_ngn)
link(cir_n, "Mesh", sp_n, "Geometry")
feed(sp_n, "Position", src_pos((ngi, "Index"), F_ngn))
cap_ngon = store_rim(sp_n, True, F_ngn)            # every vertex is on the border

# --- 5e3. Center Vertex cap: a star of triangles ------------------------------
fai = mk("GeometryNodeInputIndex", F_fan)
cir_f = mk("GeometryNodeMeshCircle", F_fan, fill_type='TRIANGLE_FAN')
feed(cir_f, "Vertices", N)
is_ctr = icmp('EQUAL', (fai, "Index"), N, F_fan)   # the fan centre is the LAST vertex
pos_f = mk("GeometryNodeSwitch", F_fan, input_type='VECTOR')
feed(pos_f, "Switch", is_ctr)
feed(pos_f, "False", src_pos((fai, "Index"), F_fan))
feed(pos_f, "True", CEN)
sp_f = mk("GeometryNodeSetPosition", F_fan)
link(cir_f, "Mesh", sp_f, "Geometry"); link(pos_f, "Output", sp_f, "Position")
cap_fan = store_rim(sp_f, bmath('NOT', is_ctr, None, F_fan), F_fan)

# --- 5e4. Cap Type -> geometry ------------------------------------------------
g = gi(F_typ, "Cap Type")
tmenu = mk("GeometryNodeMenuSwitch", F_typ, data_type='INT')
_ti = tmenu.enum_definition.enum_items
_ti[0].name = "Quad Grid"; _ti[1].name = "N-gon"; _ti.new("Center Vertex")
for _i in range(3): isock(tmenu, "Item_%d" % _i).default_value = _i
link(g, "Cap Type", tmenu, "Menu")
tpick = mk("GeometryNodeIndexSwitch", F_typ, data_type='GEOMETRY')
tpick.index_switch_items.new()                     # 2 stock + 1 = 3 items
link(tmenu, "Output", tpick, "Index")
link(cap_grid, "Geometry", tpick, "Item_0")
link(cap_ngon, "Geometry", tpick, "Item_1")
link(cap_fan,  "Geometry", tpick, "Item_2")

# --- 5f. relax (repeat zone) --------------------------------------------------
g = gi(F_rpi, "Relax Iterations")
rp_in  = mk("GeometryNodeRepeatInput",  F_rpi)
rp_out = mk("GeometryNodeRepeatOutput", F_rpo)
rp_in.pair_with_output(rp_out)
link(g, "Relax Iterations", rp_in, "Iterations")
link(tpick, "Output", rp_in, "Geometry")
rpos = mk("GeometryNodeInputPosition", F_rlx)
blur = mk("GeometryNodeBlurAttribute", F_rlx, data_type='FLOAT_VECTOR')
link(rpos, "Position", blur, "Value"); isock(blur, "Iterations").default_value = 1
inner = bmath('NOT', named('BOOLEAN', A_RIM, F_rlx), None, F_rlx)
srl = mk("GeometryNodeSetPosition", F_rlx)
link(rp_in, "Geometry", srl, "Geometry"); feed(srl, "Selection", inner)
link(blur, "Value", srl, "Position")
link(srl, "Geometry", rp_out, "Geometry")

# --- 5g. dome -----------------------------------------------------------------
g = gi(F_dom, "Dome")
fn  = mk("GeometryNodeInputNormal", F_dom)
nst = mk("GeometryNodeAttributeStatistic", F_dom, data_type='FLOAT_VECTOR', domain='FACE')
link(rp_out, "Geometry", nst, "Geometry"); link(fn, "Normal", nst, "Attribute")
nrm = vmath('NORMALIZE', (nst, "Mean"), None, F_dom)
# radial paraboloid in the plane of the hole: 1 at its centre, 0 at its radius
dpos = mk("GeometryNodeInputPosition", F_dom)
dv   = vmath('SUBTRACT', (dpos, "Position"), CEN, F_dom)
along = vmath('DOT_PRODUCT', dv, nrm, F_dom, out="Value")
perp = vmath('SUBTRACT', dv, vmath('SCALE', nrm, along, F_dom), F_dom)
dist = vmath('LENGTH', perp, None, F_dom, out="Value")
rel  = fmath('DIVIDE', dist, RAD_IN, F_dom)
prof = fmath('SUBTRACT', 1.0, fmath('MULTIPLY', rel, rel, F_dom), F_dom)
prof[0].use_clamp = True
amt = fmath('MULTIPLY', fmath('MULTIPLY', (g, "Dome"), RAD_IN, F_dom), prof, F_dom)
doff = vmath('SCALE', nrm, amt, F_dom)
sdm = mk("GeometryNodeSetPosition", F_dom)
link(rp_out, "Geometry", sdm, "Geometry"); feed(sdm, "Offset", doff)
feed(sdm, "Selection", bmath('NOT', named('BOOLEAN', A_RIM, F_dom), None, F_dom))

# --- 5h. inset rings ----------------------------------------------------------
# A grid N+1 columns wide (the extra column repeats slot 0 and welding closes that
# seam) with one row per ring: column -> rim slot, row -> how far that ring steps in.
g = gi(F_bnd, "Inset Rings")
band = mk("GeometryNodeMeshGrid", F_bnd)
feed(band, "Size X", N); feed(band, "Size Y", RINGS)
feed(band, "Vertices X", imath('ADD', N, 1, F_bnd))
feed(band, "Vertices Y", imath('ADD', RINGS, 1, F_bnd))
bpos = mk("GeometryNodeInputPosition", F_bnd)
bsep = mk("ShaderNodeSeparateXYZ", F_bnd); link(bpos, "Position", bsep, "Vector")
col = fmath('ROUND', fmath('MULTIPLY_ADD', N, 0.5, F_bnd, c=(bsep, "X")), None, F_bnd)
row = fmath('ROUND', fmath('MULTIPLY_ADD', RINGS, 0.5, F_bnd, c=(bsep, "Y")), None, F_bnd)
sp_b = mk("GeometryNodeSetPosition", F_bnd)
link(band, "Mesh", sp_b, "Geometry")
feed(sp_b, "Position", src_pos(col, F_bnd, inset=fmath('MULTIPLY', AMT, row, F_bnd)))
band_rim = store_rim(sp_b, True, F_bnd)       # seam and both ring edges may weld
bsw = mk("GeometryNodeSwitch", F_bnd, input_type='GEOMETRY')   # no rings, no band
feed(bsw, "Switch", icmp('GREATER_THAN', RINGS, 0, F_bnd))
link(band_rim, "Geometry", bsw, "True")
jn_b = mk("GeometryNodeJoinGeometry", F_bnd)
link(sdm, "Geometry", jn_b, "Geometry"); link(bsw, "Output", jn_b, "Geometry")

# --- 5i. cap UVs --------------------------------------------------------------
# Flat projection in the plane of the hole: rim slot 0 sets the U direction, the cap
# normal is the axis it rotates about.
g = gi(F_uv, "Create UVs", "UV Map", "UV Mode", "UV Scale", "UV Rotation")
t0 = vmath('SUBTRACT', src_pos(0, F_uv, inset=0.0), CEN, F_uv)
t_fl = vmath('SUBTRACT', t0,
             vmath('SCALE', nrm, vmath('DOT_PRODUCT', t0, nrm, F_uv, out="Value"), F_uv), F_uv)
t_rot = mk("ShaderNodeVectorRotate", F_uv, rotation_type='AXIS_ANGLE')
feed(t_rot, "Vector", vmath('NORMALIZE', t_fl, None, F_uv))
feed(t_rot, "Axis", nrm); link(g, "UV Rotation", t_rot, "Angle")
TAN = (t_rot, "Vector")
BIT = vmath('CROSS_PRODUCT', nrm, TAN, F_uv)
uvp = mk("GeometryNodeInputPosition", F_uv)
duv = vmath('SUBTRACT', (uvp, "Position"), CEN, F_uv)
uu  = vmath('DOT_PRODUCT', duv, TAN, F_uv, out="Value")
vv  = vmath('DOT_PRODUCT', duv, BIT, F_uv, out="Value")
umenu = mk("GeometryNodeMenuSwitch", F_uv, data_type='INT')
_ui = umenu.enum_definition.enum_items
_ui[0].name = "Fit Loop"; _ui[1].name = "World Units"
for _i in range(2): isock(umenu, "Item_%d" % _i).default_value = _i
link(g, "UV Mode", umenu, "Menu")
kpick = mk("GeometryNodeIndexSwitch", F_uv, data_type='FLOAT')
link(umenu, "Output", kpick, "Index")
feed(kpick, "Item_0", fmath('DIVIDE', 0.5, RAD, F_uv))      # hole diameter -> 0..1
feed(kpick, "Item_1", 1.0)                                  # object units
opick = mk("GeometryNodeIndexSwitch", F_uv, data_type='FLOAT')
link(umenu, "Output", opick, "Index")
feed(opick, "Item_0", 0.5); feed(opick, "Item_1", 0.0)
ks  = fmath('MULTIPLY', (kpick, "Output"), (g, "UV Scale"), F_uv)
u_o = fmath('MULTIPLY_ADD', uu, ks, F_uv, c=(opick, "Output"))
v_o = fmath('MULTIPLY_ADD', vv, ks, F_uv, c=(opick, "Output"))
uvv = mk("ShaderNodeCombineXYZ", F_uv)
feed(uvv, "X", u_o); feed(uvv, "Y", v_o)
st_uv = mk("GeometryNodeStoreNamedAttribute", F_uv, data_type='FLOAT2', domain='CORNER')
link(jn_b, "Geometry", st_uv, "Geometry")
link(g, "UV Map", st_uv, "Name"); link(uvv, "Vector", st_uv, "Value")
uvsw = mk("GeometryNodeSwitch", F_uv, input_type='GEOMETRY')   # off = no UV map touched
link(g, "Create UVs", uvsw, "Switch")
link(jn_b, "Geometry", uvsw, "False"); link(st_uv, "Geometry", uvsw, "True")
link(uvsw, "Output", fe_out, "Generation_0")

# ============================================================================= 6. CAP OUTPUT
g = gi(F_cpo, "Flip Cap Normals")
cap_f = mk("GeometryNodeCaptureAttribute", F_cpo, domain='FACE')
cap_f.capture_items.new('BOOLEAN', "Cap")
link(fe_out, "Generation_0", cap_f, "Geometry")
isock(cap_f, "Cap").default_value = True
flip = mk("GeometryNodeFlipFaces", F_cpo)
link(cap_f, "Geometry", flip, "Mesh"); link(g, "Flip Cap Normals", flip, "Selection")

# ============================================================================= 7. WELD
g = gi(F_wld, "Geometry", "Merge With Mesh", "Merge Distance")
# border verts of the ORIGINAL mesh: any selected border edge touches them
# evaluate ON edges; the point-domain store then averages it onto the vertices
e2p = mk("GeometryNodeFieldOnDomain", F_wld, domain='EDGE', data_type='FLOAT')
feed(e2p, "Value", edge_sel)
on_b = mk("FunctionNodeCompare", F_wld, data_type='FLOAT', operation='GREATER_THAN')
link(e2p, "Value", on_b, "A"); isock(on_b, "B").default_value = 0.0
st_ob = mk("GeometryNodeStoreNamedAttribute", F_wld, data_type='BOOLEAN', domain='POINT')
link(g, "Geometry", st_ob, "Geometry"); isock(st_ob, "Name").default_value = A_RIM
link(on_b, "Result", st_ob, "Value")
join = mk("GeometryNodeJoinGeometry", F_wld)
link(flip, "Mesh", join, "Geometry"); link(st_ob, "Geometry", join, "Geometry")
merge = mk("GeometryNodeMergeByDistance", F_wld)
link(join, "Geometry", merge, "Geometry")
feed(merge, "Selection", named('BOOLEAN', A_RIM, F_wld))
isock(merge, "Mode").default_value = "All"
link(g, "Merge Distance", merge, "Distance")
msw = mk("GeometryNodeSwitch", F_wld, input_type='GEOMETRY')
link(g, "Merge With Mesh", msw, "Switch")
link(join, "Geometry", msw, "False"); link(merge, "Geometry", msw, "True")

# ============================================================================= 7b. MATERIAL
# This runs AFTER the join on purpose: a material index is a slot number of the mesh
# it sits on, and on the cap geometry alone that list is empty -- Join Geometry then
# remaps the caps onto an appended empty slot. Downstream of the join the numbers are
# the object's own slots, which is what a "material ID" means to the user.
g = gi(F_mat, "Use Cap Material", "Cap Material", "Cap Material Index")
is_cap = (cap_f, "Cap")
# index first, material second: an explicitly assigned Cap Material wins over the slot
# number (the other way round the index node just overwrites the assignment again).
smi = mk("GeometryNodeSetMaterialIndex", F_mat)
link(msw, "Output", smi, "Geometry")
feed(smi, "Selection", bmath('AND', is_cap,
     icmp('GREATER_EQUAL', (g, "Cap Material Index"), 0, F_mat), F_mat))
link(g, "Cap Material Index", smi, "Material Index")
setm = mk("GeometryNodeSetMaterial", F_mat)
link(smi, "Geometry", setm, "Geometry")
link(g, "Cap Material", setm, "Material")
feed(setm, "Selection", bmath('AND', is_cap, (g, "Use Cap Material"), F_mat))

# ============================================================================= 8. CLEANUP
rm = mk("GeometryNodeRemoveAttribute", F_cln)
link(setm, "Geometry", rm, "Geometry")
isock(rm, "Pattern Mode").default_value = "Wildcard"
isock(rm, "Name").default_value = "__qc_*"
link(rm, "Geometry", gout, "Geometry")
link(cap_f, "Cap", gout, "Cap")

# menu defaults are only valid once their Menu Switch has defined the items
sk_ctype.default_value = "Quad Grid"
sk_uvmode.default_value = "Fit Loop"

gout.location = (4000, 0)

# ============================================================================= DEMO OBJECT
for _o in list(bpy.data.objects):
    bpy.data.objects.remove(_o, do_unlink=True)
me = bpy.data.meshes.new("GN_Demo")
bm = bmesh.new()
# 16-segment open tube (even loops -> 4 x 4 grids)
bmesh.ops.create_cone(bm, cap_ends=False, segments=16, radius1=0.8, radius2=0.8,
                      depth=1.6, matrix=Matrix.Translation((-2.2, 0, 0)))
# 13-segment open tube (odd loops -> quads + one triangle each)
bmesh.ops.create_cone(bm, cap_ends=False, segments=13, radius1=0.7, radius2=0.7,
                      depth=1.6, matrix=Matrix.Translation((0.0, 0, 0)))
# UV sphere with its top pole fan removed (24-vertex hole)
res = bmesh.ops.create_uvsphere(bm, u_segments=24, v_segments=12, radius=0.8,
                                matrix=Matrix.Translation((2.2, 0, 0)))
top = max(res["verts"], key=lambda v: v.co.z)
bmesh.ops.delete(bm, geom=[top], context='VERTS')
bm.to_mesh(me); bm.free()
obj = bpy.data.objects.new("GN_Demo", me)
bpy.context.scene.collection.objects.link(obj)
md = obj.modifiers.new(NAME, "NODES"); md.node_group = ng
obj.select_set(True); bpy.context.view_layer.objects.active = obj

# ============================================================================= PUBLISH
ng.asset_mark()
ng.asset_data.catalog_id = CAT
ng.asset_data.tags.new("ST3E")
ng.asset_data.description = (
    "Closes open borders with an all-quad cap instead of an n-gon: each border loop "
    "gets an evenly spaced quad grid (Coons patch), odd loops get exactly one "
    "triangle. Winding follows the surrounding faces; optional relax and dome.")
ng.is_modifier = True
ng.is_tool = False

bpy.ops.wm.save_as_mainfile(filepath=PATH)
print("SAVED", PATH, "nodes:", len(ng.nodes))
sys.stdout.flush()
os._exit(0)
