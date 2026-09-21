"""Patch GN_Delete.blend -- fold GN_DeleteStrayGeometry's cleanup passes into
GN_Delete as an optional post-stage, so one modifier covers every delete case.

GN_Delete keeps its existing job (delete a selection, by group / material ID /
axis side, on a chosen domain). This patch appends a "Stray Geometry" stage
AFTER that delete. There is no master on/off socket -- the five pass toggles ARE
the control, and an OR of them drives a lazy Switch(GEOMETRY) so the stage costs
nothing while every pass is off:

  Geometry -> [selection delete] --+--> (bypass) ---------------------+
                                   |                                 |
                                   +--> islands -> loose faces ------+--> Switch -> Output
                                        -> loose edges -> loose verts

  * Loose Vertices  -- verts with no connected edge (VertexNeighbors.Vertex Count == 0)
  * Loose Edges     -- edges bordering no face (EdgeNeighbors.Face Count == 0); also
                       catches dangling wires hanging off a big island.
  * Loose Faces     -- a polygon sharing no edge with any other face; deleted via its
                       verts on the POINT domain (a FACE-domain delete strips ALL
                       face-less verts/edges regardless of selection, which would
                       couple this pass to the loose-vert/edge toggles).
  * Loose Triangles -- the same test restricted to 3-gons.
  * Small Islands   -- whole connected components that are stray: too few verts, OR
                       tiny relative to the LARGEST island (distance-invariant, so a
                       far-away stray can never inflate the reference), OR below an
                       absolute world-space size.

New interface sockets backfill existing modifiers with type-zero -- every pass
toggle reads False there -- so every GN_Delete modifier already in the wild keeps
its exact geometry (see memory feedback_gn_new_socket_backfills_zero).

The patch also normalizes the WHOLE interface (see NORMALIZE below) and frames
GN_Delete's previously unframed legacy nodes (R8). Renames keep socket
identifiers, so values stored on existing modifiers survive; panels are only
re-parented, which modifier overrides do not depend on.

Run headless:
  "C:\\Program Files\\Blender Foundation\\Blender 5.0\\blender.exe" --background \
      --factory-startup GN_Delete.blend --python patch_gn_delete_add_stray.py
Then tidy + gate:
  blender --background --factory-startup --python run_pipeline.py -- GN_Delete
"""
import bpy, sys, os

GEO  = r"D:\Stephko_Tooling\Toolings\Blender\Geonodes"
NAME = "GN_Delete"
PATH = os.path.join(GEO, NAME + ".blend")

ng = bpy.data.node_groups[NAME]
n, links = ng.nodes, ng.links

# ----------------------------------------------------------------------------- helpers
def _pick(sockets, key):
    """Resolve a socket by index, identifier or display name -- preferring the
    ENABLED variant (multi-type nodes keep disabled same-name sockets that no-op)."""
    if isinstance(key, int):
        return sockets[key]
    for want_enabled in (True, False):
        for s in sockets:
            if s.enabled == want_enabled and s.identifier == key:
                return s
    for want_enabled in (True, False):
        for s in sockets:
            if s.enabled == want_enabled and s.name == key:
                return s
    raise KeyError(key)
def osock(node, key): return _pick(node.outputs, key)
def isock(node, key): return _pick(node.inputs,  key)
def link(a, ai, b, bi): return links.new(osock(a, ai), isock(b, bi))

# ============================================================================= INTERFACE
iface = ng.interface

def panel(name, parent=None, closed=False):
    try:
        p = iface.new_panel(name, default_closed=closed)
    except TypeError:                     # older API without default_closed
        p = iface.new_panel(name)
        p.default_closed = closed
    if parent is not None:                # new_panel has no parent kwarg
        iface.move_to_parent(p, parent, len(parent.interface_items))
    return p

def sock(name, stype, parent, default=None, mn=None, mx=None, subtype=None, desc=""):
    s = iface.new_socket(name, in_out='INPUT', socket_type=stype, parent=parent)
    if default is not None: s.default_value = default
    if mn is not None:      s.min_value = mn
    if mx is not None:      s.max_value = mx
    if subtype:             s.subtype = subtype
    s.description = desc
    return s

P_STRAY = "Stray Geometry"
if any(getattr(i, "name", "") == P_STRAY for i in iface.items_tree):
    raise SystemExit("GN_Delete already carries the Stray Geometry stage -- aborting.")

def find(name, kind='SOCKET'):
    """Look an interface item up by name AND type -- items_tree[name] returns the
    PANEL when a panel and a socket share a name (which they do here)."""
    for it in iface.items_tree:
        if it.item_type == kind and it.name == name:
            return it
    raise KeyError((kind, name))

# ----------------------------------------------------------------- NORMALIZE
# Panel order follows the evaluation order the user reads top-down:
#   Selection (what)  ->  Delete (which domain)  ->  Axis Filter (narrow it)
#   ->  Stray Geometry (the cleanup post-stage)
# Renames drop words the enclosing panel already says, and no panel shares a name
# with one of its sockets.

# 1. "Selection Mode" panel shared its name with its own menu socket. Rename the
#    panel, then flatten the two one-socket sub-panels into it and drop them.
p_sel = find("Selection Mode", 'PANEL'); p_sel.name = "Selection"
# ... and its default was True, so a freshly added GN_Delete wiped the whole mesh
# until you drove it. False = added-and-inert; existing modifiers store their own
# value, so nothing already in a scene changes.
find("Selection Group").default_value = False
iface.move_to_parent(find("Selection Group"), p_sel, 1)
iface.move_to_parent(find("Material ID"),     p_sel, 2)
iface.move_to_parent(find("Invert Selection"), p_sel, 3)   # enable-flags last
for dead in ("Selection by Group", "Selection by Material ID"):
    iface.remove(find(dead, 'PANEL'))

# 2. "Deletion" holding a socket called "On Domain" -> "Delete" / "Domain",
#    matching the Delete Geometry node's own wording.
find("Deletion", 'PANEL').name = "Delete"
find("On Domain").name = "Domain"

# 3. Axis Filter: the panel already says "Axis"/"Filter", so the sockets stop
#    repeating it. "Use ..." is the ST3E enable-flag convention.
p_axis = find("Axis Filter", 'PANEL'); p_axis.default_closed = True
find("Filter by Axis").name = "Use Axis Filter"
find("Filter Axis").name = "Axis"

# ----------------------------------------------------------------- STRAY PANEL
# One flat panel: sub-panels would leave "Stray Geometry" an empty wrapper, and
# each pass toggle reads fine on its own line. Loose passes first (cheap, local),
# then the island test with its three thresholds directly under its toggle.
p_stray = panel(P_STRAY, closed=True)
S_DLV = "Loose Vertices"
S_DLE = "Loose Edges"
S_DLF = "Loose Faces"
S_DLT = "Loose Triangles"
S_DSI = "Small Islands"
S_MVC = "Min Vertex Count"
S_RSZ = "Relative Size"
S_ASZ = "Absolute Size"
sock(S_DLV, 'NodeSocketBool', p_stray, default=True,
     desc="Remove vertices that are not connected to any edge (isolated points).")
sock(S_DLE, 'NodeSocketBool', p_stray, default=True,
     desc="Remove edges that do not border any face -- floating edges and dangling "
          "wires sticking out of a solid mesh. Vertices left orphaned are cleaned by "
          "the loose-vertex pass.")
sock(S_DLF, 'NodeSocketBool', p_stray, default=True,
     desc="Remove isolated faces -- a polygon (tri, quad or n-gon) that shares no edge "
          "with any other face, so it floats free of the surrounding surface. A face "
          "welded to the mesh by even one edge is kept. Note: on a single-face mesh "
          "(e.g. a bare plane) the whole face counts as loose.")
sock(S_DLT, 'NodeSocketBool', p_stray, default=True,
     desc="Remove isolated TRIANGLES only -- an edge-isolated 3-gon. Use this to clear "
          "stray triangulation slivers while keeping isolated quads/n-gons "
          "(leave 'Loose Faces' off for that).")
sock(S_DSI, 'NodeSocketBool', p_stray, default=True,
     desc="Remove whole disconnected pieces judged 'stray' by any of the three tests "
          "below.")
sock(S_MVC, 'NodeSocketInt', p_stray, default=5, mn=0,
     desc="Small Islands: a disconnected piece with FEWER vertices than this is "
          "removed. Catches loose verts (1), loose edges (2) and lone tris/quads (3-4). "
          "Set 0 to skip this test.")
sock(S_RSZ, 'NodeSocketFloat', p_stray, default=0.02, mn=0.0, mx=1.0, subtype='FACTOR',
     desc="Small Islands: a piece smaller than this fraction of the LARGEST piece's "
          "size is removed -- the 'almost invisible next to the big shape' test. "
          "0.02 = pieces under 2% of the main shape. Set 0 to skip. Distance-invariant "
          "(a far-away stray cannot skew the reference).")
sock(S_ASZ, 'NodeSocketFloat', p_stray, default=0.0, mn=0.0, subtype='DISTANCE',
     desc="Small Islands: a piece whose characteristic size (world units) is below this "
          "is removed. 0 = disabled; use when you want a fixed world-space cutoff "
          "rather than a relative one.")

# ============================================================================= FRAMES
OX, OY = 6100, 0                      # park the new stage right of the existing graph

def frame(label):
    f = n.new("NodeFrame"); f.label = label; f.location = (0, 0)
    f.use_custom_color = True; f.color = (0.18, 0.20, 0.26)
    return f
F_lv  = frame("Stray: Loose Vertices")
F_le  = frame("Stray: Loose Edges")
F_lf  = frame("Stray: Loose Faces / Triangles")
F_isz = frame("Stray: Island Size (RMS, per connected component)")
F_tst = frame("Stray: Small-Island Test")
F_del = frame("Stray: Delete Passes  (islands -> faces -> edges -> verts)")
F_gate = frame("Stray: Bypass Gate")

def mk(idname, parent=None, loc=(0, 0), **props):
    node = n.new(idname)
    for k, v in props.items(): setattr(node, k, v)
    if parent: node.parent = parent
    node.location = (loc[0] + OX, loc[1] + OY)
    return node

def cmp(op, dtype, parent, loc):
    return mk("FunctionNodeCompare", parent, loc, data_type=dtype, operation=op)
def boolmath(op, parent, loc):
    return mk("FunctionNodeBooleanMath", parent, loc, operation=op)
def math(op, parent, loc):
    return mk("ShaderNodeMath", parent, loc, operation=op)
def vmath(op, parent, loc):
    return mk("ShaderNodeVectorMath", parent, loc, operation=op)
def groupinput(parent, loc, label):
    g = mk("NodeGroupInput", parent, loc); g.label = label
    return g

# ============================================================================= LOOSE VERTS
gi_lv = groupinput(F_lv, (-2000, 300), "In: Stray Geometry")
vn   = mk("GeometryNodeInputMeshVertexNeighbors", F_lv, (-1600, 400))
vcmp = cmp('EQUAL', 'INT', F_lv, (-1400, 420))
isock(vcmp, "B_INT").default_value = 0
link(vn, "Vertex Count", vcmp, "A_INT")
v_sel = boolmath('AND', F_lv, (-1200, 420))
link(vcmp, "Result", v_sel, 0); link(gi_lv, S_DLV, v_sel, 1)

# ============================================================================= LOOSE EDGES
gi_le = groupinput(F_le, (-2000, 40), "In: Stray Geometry")
en   = mk("GeometryNodeInputMeshEdgeNeighbors", F_le, (-1600, 100))
ecmp = cmp('EQUAL', 'INT', F_le, (-1400, 120))
isock(ecmp, "B_INT").default_value = 0
link(en, "Face Count", ecmp, "A_INT")
e_sel = boolmath('AND', F_le, (-1200, 120))
link(ecmp, "Result", e_sel, 0); link(gi_le, S_DLE, e_sel, 1)

# ============================================================================= LOOSE FACES / TRIS
# A face is "loose" when it shares no edge with any other face (Face Count == 0).
# Loose Triangles = loose faces that are also 3-gons (Vertex Count == 3).
# NOTE: a DeleteGeometry on the FACE domain STRIPS all loose (face-less) verts/edges
# regardless of its selection -- that would couple this pass to the loose-vert/edge
# toggles and break the all-off identity. So we delete on the strip-safe POINT domain
# instead: a face-domain boolean read in a POINT context averages over a vertex's
# adjacent faces, so "all adjacent faces loose" == that average > 0.999. Requiring the
# vertex to also own >=1 face excludes standalone loose verts and never tears a solid
# face sharing only a corner (its avg < 1). Deleting any vertex of a loose face removes
# that face, so the isolated polygon disappears.
gi_lf = groupinput(F_lf, (-2000, 640), "In: Stray Geometry")
fn    = mk("GeometryNodeInputMeshFaceNeighbors", F_lf, (-1600, 760))
fcmp  = cmp('EQUAL', 'INT', F_lf, (-1400, 800))            # Face Count == 0  -> isolated face
isock(fcmp, "B_INT").default_value = 0
link(fn, "Face Count", fcmp, "A_INT")
tcmp  = cmp('EQUAL', 'INT', F_lf, (-1400, 660))            # Vertex Count == 3 -> triangle
isock(tcmp, "B_INT").default_value = 3
link(fn, "Vertex Count", tcmp, "A_INT")
looseTri = boolmath('AND', F_lf, (-1220, 660))             # isolated AND 3-gon (FACE bool)
link(fcmp, "Result", looseTri, 0); link(tcmp, "Result", looseTri, 1)

vnf   = mk("GeometryNodeInputMeshVertexNeighbors", F_lf, (-1600, 500))
hasF  = cmp('GREATER_THAN', 'INT', F_lf, (-1400, 520))     # vertex owns >=1 face
link(vnf, "Face Count", hasF, "A_INT"); isock(hasF, "B_INT").default_value = 0

# FACE bool -> POINT: average over adjacent faces; == 1 means ALL adjacent faces loose
fAll  = cmp('GREATER_THAN', 'FLOAT', F_lf, (-1200, 820)); isock(fAll, "B").default_value = 0.999
link(fcmp, "Result", fAll, "A")
tAll  = cmp('GREATER_THAN', 'FLOAT', F_lf, (-1200, 560)); isock(tAll, "B").default_value = 0.999
link(looseTri, "Boolean", tAll, "A")

f_own = boolmath('AND', F_lf, (-1020, 800)); link(fAll, "Result", f_own, 0); link(hasF, "Result", f_own, 1)
f_en  = boolmath('AND', F_lf, (-860, 800));  link(f_own, "Boolean", f_en, 0); link(gi_lf, S_DLF, f_en, 1)
t_own = boolmath('AND', F_lf, (-1020, 560)); link(tAll, "Result", t_own, 0); link(hasF, "Result", t_own, 1)
t_en  = boolmath('AND', F_lf, (-860, 560));  link(t_own, "Boolean", t_en, 0); link(gi_lf, S_DLT, t_en, 1)
f_sel = boolmath('OR', F_lf, (-700, 700));   link(f_en, "Boolean", f_sel, 0); link(t_en, "Boolean", f_sel, 1)

# ============================================================================= ISLAND SIZE
# per-island RMS size = sqrt( sum_over_axes Var(pos) ),  Var = E[p^2] - E[p]^2 ,
# both expectations built from Accumulate-Field sums grouped by Island Index.
isl  = mk("GeometryNodeInputMeshIsland", F_isz, (-1600, -260))
pos  = mk("GeometryNodeInputPosition",   F_isz, (-1600, -420))
possq = vmath('MULTIPLY', F_isz, (-1420, -440)); link(pos, "Position", possq, 0); link(pos, "Position", possq, 1)

accN = mk("GeometryNodeAccumulateField", F_isz, (-1240, -220), data_type='FLOAT', domain='POINT')
isock(accN, "Value").default_value = 1.0
link(isl, "Island Index", accN, "Group Index")
accP = mk("GeometryNodeAccumulateField", F_isz, (-1240, -360), data_type='FLOAT_VECTOR', domain='POINT')
link(pos, "Position", accP, "Value"); link(isl, "Island Index", accP, "Group Index")
accP2 = mk("GeometryNodeAccumulateField", F_isz, (-1240, -520), data_type='FLOAT_VECTOR', domain='POINT')
link(possq, "Vector", accP2, "Value"); link(isl, "Island Index", accP2, "Group Index")

countVec = mk("ShaderNodeCombineXYZ", F_isz, (-1040, -240))
link(accN, "Total", countVec, 0); link(accN, "Total", countVec, 1); link(accN, "Total", countVec, 2)
mean   = vmath('DIVIDE', F_isz, (-880, -360)); link(accP, "Total", mean, 0);  link(countVec, "Vector", mean, 1)
avgSq  = vmath('DIVIDE', F_isz, (-880, -520)); link(accP2, "Total", avgSq, 0); link(countVec, "Vector", avgSq, 1)
meanSq = vmath('MULTIPLY', F_isz, (-700, -360)); link(mean, "Vector", meanSq, 0); link(mean, "Vector", meanSq, 1)
var    = vmath('SUBTRACT', F_isz, (-540, -440)); link(avgSq, "Vector", var, 0); link(meanSq, "Vector", var, 1)
varpos = vmath('MAXIMUM', F_isz, (-380, -440)); link(var, "Vector", varpos, 0)   # clamp float noise >= 0
isock(varpos, "Vector_001").default_value = (0, 0, 0)
varsum = vmath('DOT_PRODUCT', F_isz, (-220, -440)); link(varpos, "Vector", varsum, 0)
isock(varsum, "Vector_001").default_value = (1, 1, 1)
size   = math('SQRT', F_isz, (-60, -440)); link(varsum, "Value", size, 0)         # per-island size

# largest island size = Max of the size field over the stage's INPUT geometry
stat = mk("GeometryNodeAttributeStatistic", F_isz, (-60, -640), data_type='FLOAT', domain='POINT')
link(size, "Value", stat, "Attribute")

# ============================================================================= SMALL TEST
gi_tst = groupinput(F_tst, (140, -820), "In: Stray Geometry")
relDenom = math('MAXIMUM', F_tst, (140, -300)); link(stat, "Max", relDenom, 0)
isock(relDenom, "Value_001").default_value = 1e-9
relSize  = math('DIVIDE',  F_tst, (300, -300)); link(size, "Value", relSize, 0); link(relDenom, "Value", relSize, 1)

tCount = cmp('LESS_THAN', 'FLOAT', F_tst, (300, -120))     # verts < Min Island Vertex Count
link(accN, "Total", tCount, "A"); link(gi_tst, S_MVC, tCount, "B")
tRel   = cmp('LESS_THAN', 'FLOAT', F_tst, (460, -300))     # relSize < Island Relative Size
link(relSize, "Value", tRel, "A"); link(gi_tst, S_RSZ, tRel, "B")
absOn  = cmp('GREATER_THAN', 'FLOAT', F_tst, (300, -500))  # Island Absolute Size > 0 (enabled)
link(gi_tst, S_ASZ, absOn, "A"); isock(absOn, "B").default_value = 0.0
absSm  = cmp('LESS_THAN', 'FLOAT', F_tst, (300, -640))     # size < Island Absolute Size
link(size, "Value", absSm, "A"); link(gi_tst, S_ASZ, absSm, "B")
tAbs   = boolmath('AND', F_tst, (460, -560)); link(absOn, "Result", tAbs, 0); link(absSm, "Result", tAbs, 1)

orA     = boolmath('OR', F_tst, (620, -200)); link(tCount, "Result", orA, 0); link(tRel, "Result", orA, 1)
isSmall = boolmath('OR', F_tst, (780, -300)); link(orA, "Boolean", isSmall, 0); link(tAbs, "Boolean", isSmall, 1)
i_sel   = boolmath('AND', F_tst, (940, -300)); link(isSmall, "Boolean", i_sel, 0); link(gi_tst, S_DSI, i_sel, 1)

# ============================================================================= DELETE PASSES
d1 = mk("GeometryNodeDeleteGeometry", F_del, (1320, 40),  domain='POINT', mode='ALL')
link(i_sel, "Boolean", d1, "Selection")
dF = mk("GeometryNodeDeleteGeometry", F_del, (1520, 40),  domain='POINT', mode='ALL')  # loose faces via their verts
link(d1, "Geometry", dF, "Geometry"); link(f_sel, "Boolean", dF, "Selection")
d2 = mk("GeometryNodeDeleteGeometry", F_del, (1720, 40),  domain='EDGE',  mode='EDGE_FACE')
link(dF, "Geometry", d2, "Geometry"); link(e_sel, "Boolean", d2, "Selection")
d3 = mk("GeometryNodeDeleteGeometry", F_del, (1920, 40),  domain='POINT', mode='ALL')
link(d2, "Geometry", d3, "Geometry"); link(v_sel, "Boolean", d3, "Selection")

# ============================================================================= BYPASS GATE
# Lazy Switch(GEOMETRY) driven by "is ANY pass on" -- with all five toggles off the
# whole stage above is never evaluated, so an untouched GN_Delete modifier pays
# nothing for it. This is deliberately NOT a user-facing master toggle: the pass
# toggles are the only control the user needs.
gi_gate = groupinput(F_gate, (1980, -300), "In: Stray Geometry")
orV = boolmath('OR', F_gate, (2160, -120))   # loose verts OR loose edges
link(gi_gate, S_DLV, orV, 0); link(gi_gate, S_DLE, orV, 1)
orF = boolmath('OR', F_gate, (2160, -280))   # loose faces OR loose triangles
link(gi_gate, S_DLF, orF, 0); link(gi_gate, S_DLT, orF, 1)
orL = boolmath('OR', F_gate, (2320, -200))   # any loose-geometry pass
link(orV, "Boolean", orL, 0); link(orF, "Boolean", orL, 1)
anyOn = boolmath('OR', F_gate, (2480, -120)) # ... or the small-island pass
link(orL, "Boolean", anyOn, 0); link(gi_gate, S_DSI, anyOn, 1)

gate = mk("GeometryNodeSwitch", F_gate, (2660, 40), input_type='GEOMETRY')
link(anyOn, "Boolean", gate, "Switch")
link(d3, "Geometry", gate, "True")

# ============================================================================= SPLICE IN
gout = next(nd for nd in n if nd.bl_idname == "NodeGroupOutput")
geo_in = isock(gout, "Geometry")
src_link = next(l for l in links if l.to_socket == geo_in)
src_sock = src_link.from_socket
links.remove(src_link)

links.new(src_sock, isock(d1,   "Geometry"))      # stray chain head
links.new(src_sock, isock(stat, "Geometry"))      # largest-island reference
links.new(src_sock, isock(gate, "False"))         # bypass
link(gate, "Output", gout, "Geometry")
gout.location = (gate.location[0] + 400, gout.location[1])

# ============================================================================= FRAME LEGACY
# GN_Delete predates the "every node lives in a labeled frame" criterion (R8).
LEGACY = {
    "Selection Source  (Selection Group / Material ID)":
        ["Menu Switch.001", "Index Switch.001", "Material Index", "Compare"],
    "Invert Selection":
        ["Boolean Math", "Switch"],
    "Delete by Domain":
        ["Menu Switch", "Index Switch", "Delete Geometry", "Delete Geometry.001",
         "Delete Geometry.002", "Delete Geometry.003", "Delete Geometry.004"],
}
for label, names in LEGACY.items():
    f = n.new("NodeFrame"); f.label = label; f.location = (0, 0)
    f.use_custom_color = True; f.color = (0.20, 0.18, 0.22)
    for nm in names:
        nd = n[nm]
        assert nd.parent is None, f"{nm} already framed"
        nd.parent = f                      # frame at (0,0) -> child loc stays absolute
# the original monolithic Group Input joins whichever frame consumes it after the
# tidy pass re-localizes group inputs; park it with the selection source for now.
for nd in n:
    if nd.bl_idname == "NodeGroupInput" and nd.parent is None:
        nd.parent = next(f for f in n if f.bl_idname == "NodeFrame"
                         and f.label.startswith("Selection Source"))

bpy.ops.wm.save_as_mainfile(filepath=PATH)
print("PATCHED", PATH)
sys.stdout.flush()
os._exit(0)
