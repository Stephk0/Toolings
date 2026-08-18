"""Build GN_DeleteStrayGeometry.blend -- a Geometry Nodes MODIFIER that removes
stray geometry from a mesh:

  * Loose Vertices  -- verts with no connected edge (VertexNeighbors.Vertex Count == 0)
  * Loose Edges     -- edges bordering no face  (EdgeNeighbors.Face Count == 0);
                       also catches dangling wires hanging off a big island.
  * Small Islands   -- disconnected pieces (Mesh Island connected components) that are
                       "stray": too few verts, OR tiny relative to the biggest piece,
                       OR below an absolute size. This covers loose quads / small
                       fragments AND the "almost invisible next to the big shape" case.

Reference for the relative-size test is the LARGEST island's size (not a global
bounding box) so a far-away stray can never inflate the reference and wrongly
flag the main mesh -- the metric is distance-invariant.

Run headless:
  "C:\\Program Files\\Blender Foundation\\Blender 5.0\\blender.exe" --background \
      --factory-startup --python build_gn_delete_stray_geometry.py
"""
import bpy, bmesh, sys, os, math

GEO   = r"D:\Stephko_Tooling\Toolings\Blender\Geonodes"
NAME  = "GN_DeleteStrayGeometry"
PATH  = os.path.join(GEO, NAME + ".blend")
CAT   = "f9ab2fa9-3a4e-491a-abaa-558cd5c029d0"   # ST3E catalog

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

# ----------------------------------------------------------------------------- clean slate
for ng in list(bpy.data.node_groups):
    if ng.name == NAME:
        bpy.data.node_groups.remove(ng)

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

# top level
sock("Geometry", 'INPUT', 'NodeSocketGeometry',
     desc="Mesh to clean of stray geometry.")
sock("Selection", 'INPUT', 'NodeSocketBool', default=True,
     desc="Only geometry where this is on is eligible for deletion. Leave on to "
          "clean the whole mesh; drive it with an attribute/field to protect regions.")

p_loose = iface.new_panel("Loose Geometry")
sock("Delete Loose Vertices", 'INPUT', 'NodeSocketBool', parent=p_loose, default=True,
     desc="Remove vertices that are not connected to any edge (isolated points).")
sock("Delete Loose Edges", 'INPUT', 'NodeSocketBool', parent=p_loose, default=True,
     desc="Remove edges that do not border any face -- floating edges and dangling "
          "wires sticking out of a solid mesh. Vertices left orphaned are cleaned by "
          "the loose-vertex pass.")
sock("Delete Loose Faces", 'INPUT', 'NodeSocketBool', parent=p_loose, default=True,
     desc="Remove isolated faces -- a polygon (tri, quad or n-gon) that shares no edge "
          "with any other face, so it floats free of the surrounding surface. A face "
          "welded to the mesh by even one edge is kept. Note: on a single-face mesh "
          "(e.g. a bare plane) the whole face counts as loose.")
sock("Delete Loose Triangles", 'INPUT', 'NodeSocketBool', parent=p_loose, default=True,
     desc="Remove isolated TRIANGLES only -- an edge-isolated 3-gon. Use this to clear "
          "stray triangulation slivers while keeping isolated quads/n-gons "
          "(leave 'Delete Loose Faces' off for that).")

p_isl = iface.new_panel("Small Islands")
sock("Delete Small Islands", 'INPUT', 'NodeSocketBool', parent=p_isl, default=True,
     desc="Remove whole disconnected pieces judged 'stray' by any of the tests below.")
sock("Min Vertex Count", 'INPUT', 'NodeSocketInt', parent=p_isl, default=5, mn=0,
     desc="A disconnected piece with FEWER vertices than this is removed. Catches "
          "loose verts (1), loose edges (2) and lone tris/quads (3-4). Set 0 to skip "
          "this test.")
sock("Relative Size", 'INPUT', 'NodeSocketFloat', parent=p_isl, default=0.02,
     mn=0.0, mx=1.0, subtype='FACTOR',
     desc="A piece smaller than this fraction of the LARGEST piece's size is removed "
          "-- the 'almost invisible next to the big shape' test. 0.02 = pieces under "
          "2% of the main shape. Set 0 to skip. Distance-invariant (a far-away stray "
          "cannot skew the reference).")
sock("Absolute Size", 'INPUT', 'NodeSocketFloat', parent=p_isl, default=0.0, mn=0.0,
     subtype='DISTANCE',
     desc="A piece whose characteristic size (world units) is below this is removed. "
          "0 = disabled; use when you want a fixed world-space cutoff rather than a "
          "relative one.")

sock("Geometry", 'OUTPUT', 'NodeSocketGeometry', desc="Cleaned mesh.")

# grab interface identifiers for Group Input routing (all come off one Group Input node)
gin  = n.new("NodeGroupInput")
gout = n.new("NodeGroupOutput")
GEO_S, SEL_S = "Geometry", "Selection"
DLV, DLE     = "Delete Loose Vertices", "Delete Loose Edges"
DLF, DLT     = "Delete Loose Faces", "Delete Loose Triangles"
DSI, MVC     = "Delete Small Islands", "Min Vertex Count"
RSZ, ASZ     = "Relative Size", "Absolute Size"

# ============================================================================= FRAMES
def frame(label):
    f = n.new("NodeFrame"); f.label = label; f.location = (0, 0)
    f.use_custom_color = True; f.color = (0.18, 0.20, 0.26)
    return f
F_lv  = frame("Loose Vertices")
F_le  = frame("Loose Edges")
F_lf  = frame("Loose Faces / Triangles")
F_isz = frame("Island Size (RMS, per connected component)")
F_tst = frame("Small-Island Test")
F_del = frame("Delete Passes  (islands -> loose edges -> loose verts)")

def mk(idname, parent=None, loc=(0, 0), **props):
    node = n.new(idname)
    for k, v in props.items(): setattr(node, k, v)
    if parent: node.parent = parent
    node.location = loc
    return node

# convenience builders --------------------------------------------------------
def cmp(op, dtype, parent, loc):
    return mk("FunctionNodeCompare", parent, loc, data_type=dtype, operation=op)
def boolmath(op, parent, loc):
    return mk("FunctionNodeBooleanMath", parent, loc, operation=op)
def math(op, parent, loc):
    return mk("ShaderNodeMath", parent, loc, operation=op)
def vmath(op, parent, loc):
    return mk("ShaderNodeVectorMath", parent, loc, operation=op)

# ============================================================================= LOOSE VERTS
vn   = mk("GeometryNodeInputMeshVertexNeighbors", F_lv, (-1600, 400))
vcmp = cmp('EQUAL', 'INT', F_lv, (-1400, 420))
isock(vcmp, "B_INT").default_value = 0
link(vn, "Vertex Count", vcmp, "A_INT")
v_en = boolmath('AND', F_lv, (-1200, 420))          # AND enable toggle
link(gin, DLV, v_en, 0); link(vcmp, "Result", v_en, 1)
v_sel = boolmath('AND', F_lv, (-1040, 420))         # AND global Selection
link(v_en, "Boolean", v_sel, 0); link(gin, SEL_S, v_sel, 1)

# ============================================================================= LOOSE EDGES
en   = mk("GeometryNodeInputMeshEdgeNeighbors", F_le, (-1600, 100))
ecmp = cmp('EQUAL', 'INT', F_le, (-1400, 120))
isock(ecmp, "B_INT").default_value = 0
link(en, "Face Count", ecmp, "A_INT")
e_en = boolmath('AND', F_le, (-1200, 120))
link(gin, DLE, e_en, 0); link(ecmp, "Result", e_en, 1)
e_sel = boolmath('AND', F_le, (-1040, 120))
link(e_en, "Boolean", e_sel, 0); link(gin, SEL_S, e_sel, 1)

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
fn    = mk("GeometryNodeInputMeshFaceNeighbors", F_lf, (-1600, 760))
fcmp  = cmp('EQUAL', 'INT', F_lf, (-1400, 800))            # Face Count == 0  -> isolated face
isock(fcmp, "B_INT").default_value = 0
link(fn, "Face Count", fcmp, "A_INT")
tcmp  = cmp('EQUAL', 'INT', F_lf, (-1400, 660))            # Vertex Count == 3 -> triangle
isock(tcmp, "B_INT").default_value = 3
link(fn, "Vertex Count", tcmp, "A_INT")
looseTri = boolmath('AND', F_lf, (-1220, 660))            # isolated AND 3-gon (FACE bool)
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
f_en  = boolmath('AND', F_lf, (-860, 800));  link(f_own, "Boolean", f_en, 0); link(gin, DLF, f_en, 1)
t_own = boolmath('AND', F_lf, (-1020, 560)); link(tAll, "Result", t_own, 0); link(hasF, "Result", t_own, 1)
t_en  = boolmath('AND', F_lf, (-860, 560));  link(t_own, "Boolean", t_en, 0); link(gin, DLT, t_en, 1)
f_or  = boolmath('OR', F_lf, (-700, 700));   link(f_en, "Boolean", f_or, 0); link(t_en, "Boolean", f_or, 1)
f_sel = boolmath('AND', F_lf, (-540, 700));  link(f_or, "Boolean", f_sel, 0); link(gin, SEL_S, f_sel, 1)

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

# largest island size = Max of the size field over the whole (original) mesh
stat = mk("GeometryNodeAttributeStatistic", F_isz, (-60, -640), data_type='FLOAT', domain='POINT')
link(gin, GEO_S, stat, "Geometry"); link(size, "Value", stat, "Attribute")

# ============================================================================= SMALL TEST
relDenom = math('MAXIMUM', F_tst, (140, -300)); link(stat, "Max", relDenom, 0)
isock(relDenom, "Value_001").default_value = 1e-9
relSize  = math('DIVIDE',  F_tst, (300, -300)); link(size, "Value", relSize, 0); link(relDenom, "Value", relSize, 1)

tCount = cmp('LESS_THAN', 'FLOAT', F_tst, (300, -120))     # verts < Min Vertex Count
link(accN, "Total", tCount, "A"); link(gin, MVC, tCount, "B")
tRel   = cmp('LESS_THAN', 'FLOAT', F_tst, (460, -300))     # relSize < Relative Size
link(relSize, "Value", tRel, "A"); link(gin, RSZ, tRel, "B")
absOn  = cmp('GREATER_THAN', 'FLOAT', F_tst, (300, -500))  # Absolute Size > 0  (enabled)
link(gin, ASZ, absOn, "A"); isock(absOn, "B").default_value = 0.0
absSm  = cmp('LESS_THAN', 'FLOAT', F_tst, (300, -640))     # size < Absolute Size
link(size, "Value", absSm, "A"); link(gin, ASZ, absSm, "B")
tAbs   = boolmath('AND', F_tst, (460, -560)); link(absOn, "Result", tAbs, 0); link(absSm, "Result", tAbs, 1)

orA    = boolmath('OR', F_tst, (620, -200)); link(tCount, "Result", orA, 0); link(tRel, "Result", orA, 1)
isSmall = boolmath('OR', F_tst, (780, -300)); link(orA, "Boolean", isSmall, 0); link(tAbs, "Boolean", isSmall, 1)
i_en   = boolmath('AND', F_tst, (940, -300)); link(isSmall, "Boolean", i_en, 0); link(gin, DSI, i_en, 1)
i_sel  = boolmath('AND', F_tst, (1100, -300)); link(i_en, "Boolean", i_sel, 0); link(gin, SEL_S, i_sel, 1)

# ============================================================================= DELETE PASSES
d1 = mk("GeometryNodeDeleteGeometry", F_del, (1320, 40),  domain='POINT', mode='ALL')
link(gin, GEO_S, d1, "Geometry"); link(i_sel, "Boolean", d1, "Selection")
dF = mk("GeometryNodeDeleteGeometry", F_del, (1520, 40),  domain='POINT', mode='ALL')  # loose faces via their verts
link(d1, "Geometry", dF, "Geometry"); link(f_sel, "Boolean", dF, "Selection")
d2 = mk("GeometryNodeDeleteGeometry", F_del, (1720, 40),  domain='EDGE',  mode='EDGE_FACE')
link(dF, "Geometry", d2, "Geometry"); link(e_sel, "Boolean", d2, "Selection")
d3 = mk("GeometryNodeDeleteGeometry", F_del, (1920, 40),  domain='POINT', mode='ALL')
link(d2, "Geometry", d3, "Geometry"); link(v_sel, "Boolean", d3, "Selection")
link(d3, "Geometry", gout, GEO_S)

gin.location  = (-2000, 0)
gout.location = (1960, 0)

# ============================================================================= DEMO OBJECT
# a main shape plus deliberate strays so the modifier visibly cleans it.
me = bpy.data.meshes.new("GN_Demo")
bm = bmesh.new()
try:
    bmesh.ops.create_icosphere(bm, subdivisions=2, radius=2.0)
except TypeError:
    bmesh.ops.create_icosphere(bm, subdivisions=2, diameter=2.0)
bm.verts.ensure_lookup_table()

# tiny disconnected cube (~0.03 wide, ~1% of the sphere) -> "almost invisible" island
bmesh.ops.create_cube(bm, size=0.03, matrix=__import__("mathutils").Matrix.Translation((0, 6, 0)))
# lone quad island (isolated face + small island)
q = [bm.verts.new(c) for c in [(6, 0, 0), (6.3, 0, 0), (6.3, 0.3, 0), (6, 0.3, 0)]]
bm.faces.new(q)
# lone triangle island (isolated triangle -> loose triangle + loose face)
tr = [bm.verts.new(c) for c in [(6, 1, 0), (6.4, 1, 0), (6.2, 1.35, 0)]]
bm.faces.new(tr)
# loose vertex
bm.verts.new((6, 3, 0))
# floating loose edge
a = bm.verts.new((6, 4, 0)); b = bm.verts.new((6, 4.4, 0)); bm.edges.new((a, b))
# dangling wire off the sphere (loose edges attached to the BIG island)
bm.verts.ensure_lookup_table()
tip = bm.verts[0]
w1 = bm.verts.new(tip.co + __import__("mathutils").Vector((0, 0, 1.2)))
w2 = bm.verts.new(tip.co + __import__("mathutils").Vector((0, 0, 2.4)))
bm.edges.new((tip, w1)); bm.edges.new((w1, w2))

bm.to_mesh(me); bm.free()
obj = bpy.data.objects.new("GN_Demo", me)
bpy.context.scene.collection.objects.link(obj)
md = obj.modifiers.new(NAME, "NODES"); md.node_group = ng
obj.select_set(True); bpy.context.view_layer.objects.active = obj

# ============================================================================= PUBLISH
ng.asset_mark()
ng.asset_data.catalog_id = CAT
ng.asset_data.tags.new("ST3E")
ng.is_modifier = True
ng.is_tool = False

bpy.ops.wm.save_as_mainfile(filepath=PATH)
print("SAVED", PATH)
sys.stdout.flush()
os._exit(0)
