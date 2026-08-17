"""Build GN_VertexDataComposer.blend -- a Geometry Nodes MODIFIER that authors every
piece of vertex data an FBX mesh can carry, channel by channel.

    4 colour attributes  x RGBA   = 16 channels
    8 UV maps            x UV     = 16 channels
                                  --------------
                                    32 writable scalar channels

Each channel independently picks a SOURCE (30 of them), a vector COMPONENT, and runs a
full processing chain (remap / clamp / invert / gamma / quantize / blur / sRGB) before it
is written.  A channel with its Write toggle off is left exactly as it was, and a slot
with no channel written is never created at all -- so the modifier never litters the mesh
with empty UV maps or colour attributes.

Why these targets: verified against Blender 5.0's own FBX exporter
(scripts/addons_core/io_scene_fbx/export_fbx_bin.py) -- it writes ALL `me.color_attributes`
as LayerElementColor (line 1291) and ALL `me.uv_layers` as LayerElementUV (line 1339).
Arbitrary named attributes are NOT exported to FBX, which is why they are not a target.

Architecture
------------
* GNG_VertexChannel -- helper group holding the source selector + processing chain.
  Defined once, instanced 32 times.  It reads the cached sources by NAME, so each
  instance needs only its own parameter links, not a 30-wide source bus.
* Precompute bus -- computes the expensive sources once and caches them as internal
  `__vdc_*` attributes; they are stripped again at the end of the graph.
* Write blocks -- 4 colour (domain/type selectable) + 8 UV, each preserving the
  channels it does not write.

Run headless:
  "C:\\Program Files\\Blender Foundation\\Blender 5.0\\blender.exe" --background \
      --factory-startup --python build_gn_vertex_data_composer.py
"""
import bpy, os, sys, math as pymath

GEO  = r"D:\Stephko_Tooling\Toolings\Blender\Geonodes"
NAME = "GN_VertexDataComposer"
HELP = "GNG_VertexChannel"
PATH = os.path.join(GEO, NAME + ".blend")
CAT  = "9b90781b-f051-4cdb-9dcb-c8909914a87b"      # ST3E/Modify

# internal cached-source attribute names (stripped before output)
A_FRAND = "__vdc_face_random"
A_IIDX  = "__vdc_island_index"
A_INRM  = "__vdc_island_norm"
A_IRND  = "__vdc_island_random"
A_ICEN  = "__vdc_island_centroid"
A_ISIZ  = "__vdc_island_size"
A_CURV  = "__vdc_curvature"
A_AO    = "__vdc_ao"
A_BDIST = "__vdc_boundary_dist"
A_ODIST = "__vdc_object_dist"
CACHED  = [A_FRAND, A_IIDX, A_INRM, A_IRND, A_ICEN, A_ISIZ, A_CURV, A_AO, A_BDIST, A_ODIST]

# ----------------------------------------------------------------------------- helpers
def _pick(sockets, key):
    """Resolve a socket by index, identifier or display name -- preferring the ENABLED
    variant.  Multi-type nodes (Random Value, Compare, ...) keep DISABLED same-name
    sockets whose links silently no-op at evaluation time."""
    if isinstance(key, int):
        return sockets[key]
    for test in (lambda s: s.enabled and s.identifier == key,
                 lambda s: s.enabled and s.name == key,
                 lambda s: s.identifier == key,
                 lambda s: s.name == key):
        for s in sockets:
            if test(s):
                return s
    raise KeyError(f"{key!r} not among {[(s.identifier, s.name, s.enabled) for s in sockets]}")

def osock(node, key): return _pick(node.outputs, key)
def isock(node, key): return _pick(node.inputs,  key)

class Tree:
    """Terse node creation that also keeps every node inside the current labeled frame."""
    def __init__(self, ng):
        self.ng = ng
        self.frame = None
    def f(self, label):
        fr = self.ng.nodes.new("NodeFrame")
        fr.label = label
        fr.location = (0, 0)          # keeps child .location absolute
        self.frame = fr
        return fr
    def n(self, idname, label=None, **props):
        nd = self.ng.nodes.new(idname)
        for k, v in props.items():
            setattr(nd, k, v)
        if label:
            nd.label = label
        if self.frame:
            nd.parent = self.frame
        return nd
    def link(self, a, ai, b, bi):
        return self.ng.links.new(osock(a, ai), isock(b, bi))
    def set(self, nd, key, val):
        isock(nd, key).default_value = val
        return nd
    def plug(self, node, idx_or_key, v):
        """v may be a (node, socket) tuple or a literal."""
        if v is None:
            return
        if isinstance(v, tuple) and len(v) == 2 and hasattr(v[0], "outputs"):
            self.ng.links.new(osock(v[0], v[1]), isock(node, idx_or_key))
        else:
            isock(node, idx_or_key).default_value = v

def fmath(t, op, a=None, b=None, label=None, c=None):
    m = t.n("ShaderNodeMath", label or op.title().replace("_", " "), operation=op)
    for idx, v in ((0, a), (1, b), (2, c)):
        t.plug(m, idx, v)
    return m

def vmath(t, op, a=None, b=None, label=None):
    m = t.n("ShaderNodeVectorMath", label or op.title().replace("_", " "), operation=op)
    for idx, v in ((0, a), (1, b)):
        t.plug(m, idx, v)
    return m

def switch(t, dtype, cond, false, true, label="Switch"):
    s = t.n("GeometryNodeSwitch", label, input_type=dtype)
    t.plug(s, "Switch", cond)
    t.plug(s, "False", false)
    t.plug(s, "True", true)
    return s

def menu_items(node, labels, descs=None):
    """Rename the two stock items in place, then append.  Delete-and-recreate makes the
    internal value counter skip, and the modifier's int override then selects nothing."""
    ed = node.enum_definition
    for i, lab in enumerate(labels):
        if i < len(ed.enum_items):
            ed.enum_items[i].name = lab
        else:
            ed.enum_items.new(lab)
    while len(ed.enum_items) > len(labels):
        ed.enum_items.remove(ed.enum_items[len(labels)])
    if descs:
        for it, d in zip(ed.enum_items, descs):
            it.description = d
    return node

# ============================================================================= SOURCES
SOURCES = [
    ("Constant",                      "A fixed number typed into Constant Value. Use it to blank a channel to a known value or to write a per-object flag."),
    ("Attribute (Float)",             "A named float attribute, read by the name in Attribute."),
    ("Attribute (Integer)",           "A named integer attribute, converted to float."),
    ("Attribute (Vector)",            "A named vector attribute. This is also how you read an EXISTING UV map -- a UV reads back as (U, V, 0), so pick component X for U and Y for V."),
    ("Attribute (Color)",             "A named colour attribute, RGBA. This is how you read an EXISTING colour attribute; component W gives the alpha."),
    ("Attribute (Boolean)",           "A named boolean attribute as 0 or 1."),
    ("Selection Mask",                "The modifier's own Selection field as 0 or 1. Handy for baking the mask you are already using into a channel."),
    ("Position (Local)",              "Vertex position in object space."),
    ("Position (World)",              "Vertex position in world space, i.e. after the object's own transform."),
    ("Position (Bounds 0-1)",         "Vertex position normalized into the mesh bounding box, so each axis runs 0 to 1. This is the usual height gradient -- pick component Z for a bottom-to-top ramp."),
    ("Normal",                        "Surface normal. Pack all three components into RGB for an object-space normal, or one component for a slope mask."),
    ("Random (Per Point)",            "A random 0-1 value per vertex, driven by Seed."),
    ("Random (Per Face)",             "A random 0-1 value per face, driven by Seed. Exact on a face-corner channel; on a vertex channel it averages over the faces meeting there."),
    ("Random (Per Island)",           "A random 0-1 value per connected mesh island, driven by Seed. The standard per-leaf, per-plank, per-brick variation source."),
    ("Random (Per Object)",           "One random 0-1 value for the whole object, derived from its origin so copies placed elsewhere get different values."),
    ("Island Index",                  "The raw index of the connected island this element belongs to."),
    ("Island Index (Normalized)",     "The island index divided by the island count, so it runs 0 to 1."),
    ("Island Size",                   "The island's RMS radius -- how big the piece is. Useful to scale wind or damage by leaf size."),
    ("Island Centroid",               "The island's centre of mass, in object space."),
    ("Island Centroid (Bounds 0-1)",  "The island's centre of mass normalized into the mesh bounding box."),
    ("Offset From Island Centroid",   "Vertex position minus its island's centroid. Packed into a UV pair this is the classic pivot-relative offset for wind and cloth shaders."),
    ("Direction To Island Centroid",  "Unit vector from the vertex towards its island's centroid."),
    ("Material Index",                "The face's material slot index."),
    ("Element Index (Normalized)",    "The vertex index divided by the vertex count, 0 to 1. Mostly a debug or ordering source."),
    ("Face Area",                     "Area of the face. On a vertex channel it averages the adjacent faces."),
    ("Curvature",                     "Average signed edge angle at the vertex: positive on convex ridges, negative in concave creases, zero on flat ground. Turn Auto Range on to normalize it."),
    ("Ambient Occlusion",             "Cheap five-ray self-occlusion, 1 = open, 0 = fully enclosed. Requires Compute Ambient Occlusion in the Sources panel, otherwise it reads 1."),
    ("Distance To Boundary",          "Distance to the nearest boundary edge, in object units -- the leaf-tip and stiffness gradient. Requires Compute Boundary Distance in the Sources panel."),
    ("Distance To Object",            "Distance to the surface of Source Object, in object units. Requires Compute Object Distance in the Sources panel."),
    ("Radial Distance",               "Distance from Source Object's origin, or from this object's own origin when no Source Object is set."),
]
SRC_LABELS = [s[0] for s in SOURCES]
SRC_DESCS  = [s[1] for s in SOURCES]
SRC = {lab: i for i, lab in enumerate(SRC_LABELS)}

COMPONENTS = ["X / Red / U", "Y / Green / V", "Z / Blue", "W / Alpha"]
COMP_DESCS = ["First component: X of a vector, Red of a colour, U of a UV pair.",
              "Second component: Y of a vector, Green of a colour, V of a UV pair.",
              "Third component: Z of a vector, Blue of a colour. Zero for a UV pair.",
              "Fourth component: Alpha of a colour. Zero for anything else."]

# ============================================================================= clean slate
for _nm in (NAME, HELP):
    while _nm in bpy.data.node_groups:
        bpy.data.node_groups.remove(bpy.data.node_groups[_nm])

# ############################################################################# HELPER GROUP
hg = bpy.data.node_groups.new(HELP, "GeometryNodeTree")
h = Tree(hg)
hi = hg.interface

def hsock(name, in_out, stype, default=None, mn=None, mx=None, subtype=None, desc=""):
    s = hi.new_socket(name, in_out=in_out, socket_type=stype)
    if default is not None: s.default_value = default
    if mn is not None:      s.min_value = mn
    if mx is not None:      s.max_value = mx
    if subtype:             s.subtype = subtype
    s.description = desc
    return s

hsock("Value", 'OUTPUT', 'NodeSocketFloat', desc="Processed channel value.")
hsock("Geometry",        'INPUT', 'NodeSocketGeometry', desc="Geometry, used only for the Auto Range statistic.")
hsock("Selection Mask",  'INPUT', 'NodeSocketBool', default=True, desc="Selection field, exposed as the Selection Mask source.")
hsock("Bounds Min",      'INPUT', 'NodeSocketVector', desc="Mesh bounding box minimum.")
hsock("Bounds Max",      'INPUT', 'NodeSocketVector', desc="Mesh bounding box maximum.")
hsock("Center Position", 'INPUT', 'NodeSocketVector', desc="Origin used by Radial Distance.")
hsock("Point Count",     'INPUT', 'NodeSocketInt', default=1, desc="Vertex count, used by Element Index (Normalized).")
hsock("Seed",            'INPUT', 'NodeSocketInt', default=0, desc="Random seed.")
h_src  = hsock("Source",          'INPUT', 'NodeSocketMenu', desc="Which piece of mesh data feeds this channel.")
hsock("Attribute",       'INPUT', 'NodeSocketString', default="", desc="Attribute name for the Attribute (...) sources.")
h_comp = hsock("Component",       'INPUT', 'NodeSocketMenu', desc="Which component of a vector or colour source to take.")
hsock("Constant Value",  'INPUT', 'NodeSocketFloat', default=0.0, desc="Value used by the Constant source.")
hsock("Auto Range",      'INPUT', 'NodeSocketBool', default=False, desc="Measure the source's own min and max over the mesh instead of using From Min / From Max.")
hsock("From Min",        'INPUT', 'NodeSocketFloat', default=0.0, desc="Input value that maps to To Min.")
hsock("From Max",        'INPUT', 'NodeSocketFloat', default=1.0, desc="Input value that maps to To Max.")
hsock("To Min",          'INPUT', 'NodeSocketFloat', default=0.0, desc="Output value at the bottom of the range.")
hsock("To Max",          'INPUT', 'NodeSocketFloat', default=1.0, desc="Output value at the top of the range.")
hsock("Clamp",           'INPUT', 'NodeSocketBool', default=True, desc="Hold the result inside To Min .. To Max.")
hsock("Invert",          'INPUT', 'NodeSocketBool', default=False, desc="Flip the normalized value before the output range is applied.")
hsock("Gamma",           'INPUT', 'NodeSocketFloat', default=1.0, mn=0.01, mx=10.0, desc="Contrast curve. 1 is linear.")
hsock("Quantize Steps",  'INPUT', 'NodeSocketInt', default=0, mn=0, mx=256, desc="Snap to this many evenly spaced levels. 0 or 1 disables it.")
hsock("Blur Iterations", 'INPUT', 'NodeSocketInt', default=0, mn=0, mx=100, desc="Smooth the result across neighbouring elements. 0 disables it.")
hsock("Encode sRGB",     'INPUT', 'NodeSocketBool', default=False, desc="Convert the value from linear to sRGB.")

hgi = hg.nodes.new("NodeGroupInput")
hgo = hg.nodes.new("NodeGroupOutput")
def gi(key): return (hgi, key)

# ------------------------------------------------------------------ menus -> int
h.f("Menus")
m_src = h.n("GeometryNodeMenuSwitch", "Source -> Index", data_type='INT')
menu_items(m_src, SRC_LABELS, SRC_DESCS)
for i in range(len(SRC_LABELS)):
    isock(m_src, f"Item_{i}").default_value = i
h.link(hgi, "Source", m_src, "Menu")

m_cmp = h.n("GeometryNodeMenuSwitch", "Component -> Index", data_type='INT')
menu_items(m_cmp, COMPONENTS, COMP_DESCS)
for i in range(len(COMPONENTS)):
    isock(m_cmp, f"Item_{i}").default_value = i
h.link(hgi, "Component", m_cmp, "Menu")

# ------------------------------------------------------------------ cheap sources
h.f("Cheap Sources")
n_pos  = h.n("GeometryNodeInputPosition", "Position")
n_nrm  = h.n("GeometryNodeInputNormal", "Normal")
n_idx  = h.n("GeometryNodeInputIndex", "Index")
n_mat  = h.n("GeometryNodeInputMaterialIndex", "Material Index")
n_area = h.n("GeometryNodeInputMeshFaceArea", "Face Area")
n_self = h.n("GeometryNodeSelfObject", "Self Object")
n_oinf = h.n("GeometryNodeObjectInfo", "Self Object Info")
h.link(n_self, "Self Object", n_oinf, "Object")
n_world = h.n("FunctionNodeTransformPoint", "Position -> World")
h.link(n_pos, "Position", n_world, "Vector")
h.link(n_oinf, "Transform", n_world, "Transform")

h.f("Bounds Normalize")
bspan = vmath(h, 'SUBTRACT', gi("Bounds Max"), gi("Bounds Min"), "Bounds Span")
bsafe = vmath(h, 'MAXIMUM', (bspan, "Vector"), (1e-9, 1e-9, 1e-9), "Guard Zero Span")
def bounds_norm(node, sock_, label):
    d = vmath(h, 'SUBTRACT', (node, sock_), gi("Bounds Min"), label + " - Min")
    return vmath(h, 'DIVIDE', (d, "Vector"), (bsafe, "Vector"), label + " / Span")
n_posn = bounds_norm(n_pos, "Position", "Position")

h.f("Named Attribute Reads")
def named(dtype, label, fixed=None):
    nd = h.n("GeometryNodeInputNamedAttribute", label, data_type=dtype)
    if fixed is not None:
        isock(nd, "Name").default_value = fixed
    else:
        h.link(hgi, "Attribute", nd, "Name")
    return nd
na_f = named('FLOAT',        "User Attribute (Float)")
na_i = named('INT',          "User Attribute (Int)")
na_v = named('FLOAT_VECTOR', "User Attribute (Vector)")
na_c = named('FLOAT_COLOR',  "User Attribute (Color)")
na_b = named('BOOLEAN',      "User Attribute (Bool)")
sep_c = h.n("FunctionNodeSeparateColor", "Split User Color")
h.link(na_c, "Attribute", sep_c, "Color")

h.f("Cached Source Reads")
ca_frnd = named('FLOAT',        "Face Random",       fixed=A_FRAND)
ca_iidx = named('FLOAT',        "Island Index",      fixed=A_IIDX)
ca_inrm = named('FLOAT',        "Island Normalized", fixed=A_INRM)
ca_irnd = named('FLOAT',        "Island Random",     fixed=A_IRND)
ca_icen = named('FLOAT_VECTOR', "Island Centroid",   fixed=A_ICEN)
ca_isiz = named('FLOAT',        "Island Size",       fixed=A_ISIZ)
ca_curv = named('FLOAT',        "Curvature",         fixed=A_CURV)
ca_ao   = named('FLOAT',        "Ambient Occlusion", fixed=A_AO)
ca_bd   = named('FLOAT',        "Boundary Distance", fixed=A_BDIST)
ca_od   = named('FLOAT',        "Object Distance",   fixed=A_ODIST)

h.f("Island Derived")
icen_n = bounds_norm(ca_icen, "Attribute", "Island Centroid")
ioff   = vmath(h, 'SUBTRACT', (n_pos, "Position"), (ca_icen, "Attribute"), "Offset From Centroid")
idir_r = vmath(h, 'SUBTRACT', (ca_icen, "Attribute"), (n_pos, "Position"), "Towards Centroid")
idir   = vmath(h, 'NORMALIZE', (idir_r, "Vector"), None, "Normalize Direction")

h.f("Randoms")
rnd_pt = h.n("FunctionNodeRandomValue", "Random Per Point", data_type='FLOAT')
h.link(n_idx, "Index", rnd_pt, "ID")
h.link(hgi, "Seed", rnd_pt, "Seed")
obj_noise = h.n("ShaderNodeTexWhiteNoise", "Random Per Object", noise_dimensions='4D')
h.link(n_oinf, "Location", obj_noise, "Vector")
seed_f = fmath(h, 'ADD', gi("Seed"), 0.5, "Seed As Float")
h.link(seed_f, "Value", obj_noise, "W")

h.f("Scalar Derived")
pc_sub = fmath(h, 'SUBTRACT', None, 1.0, "Count - 1")
h.link(hgi, "Point Count", pc_sub, 0)
pc_m1  = fmath(h, 'MAXIMUM', (pc_sub, "Value"), 1.0, "Guard Count")
elem_n = fmath(h, 'DIVIDE', None, (pc_m1, "Value"), "Element Index / Count")
h.link(n_idx, "Index", elem_n, 0)
radial = vmath(h, 'DISTANCE', (n_pos, "Position"), gi("Center Position"), "Radial Distance")

# ------------------------------------------------------------------ source select
h.f("Source Select")
def vec3(node, sock_, label):
    """Broadcast a scalar into a vector so any component returns it."""
    c = h.n("ShaderNodeCombineXYZ", label)
    for s in ("X", "Y", "Z"):
        h.link(node, sock_, c, s)
    return c

sel_f = fmath(h, 'ADD', None, 0.0, "Selection As Float")
h.link(hgi, "Selection Mask", sel_f, 0)

SRC_VEC = {
    "Constant":                     vec3(hgi, "Constant Value", "Constant"),
    "Attribute (Float)":            vec3(na_f, "Attribute", "Attr Float"),
    "Attribute (Integer)":          vec3(na_i, "Attribute", "Attr Int"),
    "Attribute (Vector)":           (na_v, "Attribute"),
    "Attribute (Color)":            (na_c, "Attribute"),
    "Attribute (Boolean)":          vec3(na_b, "Attribute", "Attr Bool"),
    "Selection Mask":               vec3(sel_f, "Value", "Selection"),
    "Position (Local)":             (n_pos, "Position"),
    "Position (World)":             (n_world, "Vector"),
    "Position (Bounds 0-1)":        (n_posn, "Vector"),
    "Normal":                       (n_nrm, "Normal"),
    "Random (Per Point)":           vec3(rnd_pt, "Value_001", "Rand Point"),
    "Random (Per Face)":            vec3(ca_frnd, "Attribute", "Rand Face"),
    "Random (Per Island)":          vec3(ca_irnd, "Attribute", "Rand Island"),
    "Random (Per Object)":          vec3(obj_noise, "Value", "Rand Object"),
    "Island Index":                 vec3(ca_iidx, "Attribute", "Island Idx"),
    "Island Index (Normalized)":    vec3(ca_inrm, "Attribute", "Island Norm"),
    "Island Size":                  vec3(ca_isiz, "Attribute", "Island Size"),
    "Island Centroid":              (ca_icen, "Attribute"),
    "Island Centroid (Bounds 0-1)": (icen_n, "Vector"),
    "Offset From Island Centroid":  (ioff, "Vector"),
    "Direction To Island Centroid": (idir, "Vector"),
    "Material Index":               vec3(n_mat, "Material Index", "Material Idx"),
    "Element Index (Normalized)":   vec3(elem_n, "Value", "Element Norm"),
    "Face Area":                    vec3(n_area, "Area", "Face Area"),
    "Curvature":                    vec3(ca_curv, "Attribute", "Curvature"),
    "Ambient Occlusion":            vec3(ca_ao, "Attribute", "AO"),
    "Distance To Boundary":         vec3(ca_bd, "Attribute", "Boundary Dist"),
    "Distance To Object":           vec3(ca_od, "Attribute", "Object Dist"),
    "Radial Distance":              vec3(radial, "Value", "Radial"),
}
assert set(SRC_VEC) == set(SRC_LABELS), set(SRC_LABELS) ^ set(SRC_VEC)

ix_src = h.n("GeometryNodeIndexSwitch", "Selected Source", data_type='VECTOR')
while len(ix_src.index_switch_items) < len(SRC_LABELS):
    ix_src.index_switch_items.new()
h.link(m_src, "Output", ix_src, "Index")
for i, lab in enumerate(SRC_LABELS):
    v = SRC_VEC[lab]
    node, sock_ = v if isinstance(v, tuple) else (v, "Vector")
    h.link(node, sock_, ix_src, f"Item_{i}")
sep_src = h.n("ShaderNodeSeparateXYZ", "Split Source")
h.link(ix_src, "Output", sep_src, "Vector")

h.f("Alpha Component")
is_col = h.n("FunctionNodeCompare", "Is Color Source", data_type='INT', operation='EQUAL')
h.link(m_src, "Output", is_col, "A_INT")
isock(is_col, "B_INT").default_value = SRC["Attribute (Color)"]
is_const = h.n("FunctionNodeCompare", "Is Constant Source", data_type='INT', operation='EQUAL')
h.link(m_src, "Output", is_const, "A_INT")
isock(is_const, "B_INT").default_value = SRC["Constant"]
w_const = switch(h, 'FLOAT', (is_const, "Result"), 0.0, gi("Constant Value"), "W = Constant")
w_val   = switch(h, 'FLOAT', (is_col, "Result"), (w_const, "Output"), (sep_c, "Alpha"), "W = Alpha")

ix_cmp = h.n("GeometryNodeIndexSwitch", "Selected Component", data_type='FLOAT')
while len(ix_cmp.index_switch_items) < 4:
    ix_cmp.index_switch_items.new()
h.link(m_cmp, "Output", ix_cmp, "Index")
h.link(sep_src, "X", ix_cmp, "Item_0")
h.link(sep_src, "Y", ix_cmp, "Item_1")
h.link(sep_src, "Z", ix_cmp, "Item_2")
h.link(w_val,  "Output", ix_cmp, "Item_3")

# ------------------------------------------------------------------ auto range
# Switch(GEOMETRY) is lazy, so feeding the statistic EMPTY geometry when Auto Range is off
# means the statistic costs nothing on the channels that do not use it.
h.f("Auto Range")
geo_gate = switch(h, 'GEOMETRY', gi("Auto Range"), None, gi("Geometry"), "Gate Statistic Geometry")
stat = h.n("GeometryNodeAttributeStatistic", "Source Statistic", data_type='FLOAT', domain='POINT')
h.link(geo_gate, "Output", stat, "Geometry")
h.link(ix_cmp, "Output", stat, "Attribute")
f_min = switch(h, 'FLOAT', gi("Auto Range"), gi("From Min"), (stat, "Min"), "Effective From Min")
f_max = switch(h, 'FLOAT', gi("Auto Range"), gi("From Max"), (stat, "Max"), "Effective From Max")

# ------------------------------------------------------------------ processing chain
h.f("Normalize")
span   = fmath(h, 'SUBTRACT', (f_max, "Output"), (f_min, "Output"), "Input Span")
sp_abs = fmath(h, 'ABSOLUTE', (span, "Value"), None, "Abs Span")
sp_deg = h.n("FunctionNodeCompare", "Span Is Zero", data_type='FLOAT', operation='LESS_THAN')
h.link(sp_abs, "Value", sp_deg, "A")
isock(sp_deg, "B").default_value = 1e-9
sp_safe = switch(h, 'FLOAT', (sp_deg, "Result"), (span, "Value"), 1.0, "Guard Zero Span")
shifted = fmath(h, 'SUBTRACT', (ix_cmp, "Output"), (f_min, "Output"), "Value - From Min")
norm    = fmath(h, 'DIVIDE', (shifted, "Value"), (sp_safe, "Output"), "Normalized 0-1")

h.f("Clamp")
clamped = h.n("ShaderNodeClamp", "Clamp 0-1")
h.link(norm, "Value", clamped, "Value")
h.set(clamped, "Min", 0.0); h.set(clamped, "Max", 1.0)
n_clamp = switch(h, 'FLOAT', gi("Clamp"), (norm, "Value"), (clamped, "Result"), "Apply Clamp")

h.f("Invert")
inv_v = fmath(h, 'SUBTRACT', 1.0, (n_clamp, "Output"), "1 - Value")
n_inv = switch(h, 'FLOAT', gi("Invert"), (n_clamp, "Output"), (inv_v, "Value"), "Apply Invert")

h.f("Gamma")
# pow() of a negative base is NaN, so the base is floored at 0 first.
g_base = fmath(h, 'MAXIMUM', (n_inv, "Output"), 0.0, "Guard Negative Base")
g_pow  = fmath(h, 'POWER', (g_base, "Value"), gi("Gamma"), "Value ^ Gamma")
g_is1  = h.n("FunctionNodeCompare", "Gamma Is One", data_type='FLOAT', operation='EQUAL')
h.link(hgi, "Gamma", g_is1, "A")
isock(g_is1, "B").default_value = 1.0
isock(g_is1, "Epsilon").default_value = 1e-4
n_gam  = switch(h, 'FLOAT', (g_is1, "Result"), (g_pow, "Value"), (n_inv, "Output"), "Apply Gamma")

h.f("Quantize")
q_sub = fmath(h, 'SUBTRACT', None, 1.0, "Steps - 1")
h.link(hgi, "Quantize Steps", q_sub, 0)
q_lv  = fmath(h, 'MAXIMUM', (q_sub, "Value"), 1.0, "Guard Levels")
q_mul = fmath(h, 'MULTIPLY', (n_gam, "Output"), (q_lv, "Value"), "Scale To Levels")
q_rnd = fmath(h, 'ROUND', (q_mul, "Value"), None, "Snap To Level")
q_div = fmath(h, 'DIVIDE', (q_rnd, "Value"), (q_lv, "Value"), "Back To 0-1")
q_on  = h.n("FunctionNodeCompare", "Quantize Enabled", data_type='INT', operation='GREATER_THAN')
h.link(hgi, "Quantize Steps", q_on, "A_INT")
isock(q_on, "B_INT").default_value = 1
n_q   = switch(h, 'FLOAT', (q_on, "Result"), (n_gam, "Output"), (q_div, "Value"), "Apply Quantize")

h.f("sRGB Encode")
# linear -> sRGB:  c <= 0.0031308 ? 12.92c : 1.055*c^(1/2.4) - 0.055
s_lo   = fmath(h, 'MULTIPLY', (n_q, "Output"), 12.92, "Low Segment")
s_base = fmath(h, 'MAXIMUM', (n_q, "Output"), 0.0, "Guard Negative")
s_pow  = fmath(h, 'POWER', (s_base, "Value"), 1.0 / 2.4, "c ^ (1/2.4)")
s_mul  = fmath(h, 'MULTIPLY', (s_pow, "Value"), 1.055, "Times 1.055")
s_hi   = fmath(h, 'SUBTRACT', (s_mul, "Value"), 0.055, "Minus 0.055")
s_cmp  = h.n("FunctionNodeCompare", "Below Knee", data_type='FLOAT', operation='LESS_THAN')
h.link(n_q, "Output", s_cmp, "A")
isock(s_cmp, "B").default_value = 0.0031308
s_pick = switch(h, 'FLOAT', (s_cmp, "Result"), (s_hi, "Value"), (s_lo, "Value"), "Pick Segment")
n_srgb = switch(h, 'FLOAT', gi("Encode sRGB"), (n_q, "Output"), (s_pick, "Output"), "Apply sRGB")

h.f("Output Range")
o_span = fmath(h, 'SUBTRACT', gi("To Max"), gi("To Min"), "Output Span")
o_mul  = fmath(h, 'MULTIPLY', (n_srgb, "Output"), (o_span, "Value"), "Scale To Output")
o_add  = fmath(h, 'ADD', (o_mul, "Value"), gi("To Min"), "Offset To Output")

h.f("Blur")
blur = h.n("GeometryNodeBlurAttribute", "Blur Channel", data_type='FLOAT')
h.link(o_add, "Value", blur, "Value")
h.link(hgi, "Blur Iterations", blur, "Iterations")
h.link(blur, "Value", hgo, "Value")

# menu defaults must be the item NAME string, or the socket reads as nothing
h_src.default_value  = SRC_LABELS[0]
h_comp.default_value = COMPONENTS[0]
print(f"BUILD: helper {HELP}: {len(hg.nodes)} nodes, {len(hg.links)} links", flush=True)

# ############################################################################# MAIN GROUP
ng = bpy.data.node_groups.new(NAME, "GeometryNodeTree")
t = Tree(ng)
iface = ng.interface

def sock(name, in_out, stype, parent=None, default=None, mn=None, mx=None,
         subtype=None, desc=""):
    s = iface.new_socket(name, in_out=in_out, socket_type=stype, parent=parent)
    if default is not None: s.default_value = default
    if mn is not None:      s.min_value = mn
    if mx is not None:      s.max_value = mx
    if subtype:             s.subtype = subtype
    s.description = desc
    return s

def subpanel(name, parent, closed=True):
    p = iface.new_panel(name, default_closed=closed)
    iface.move_to_parent(p, parent, len(parent.interface_items))
    return p

sock("Geometry", 'OUTPUT', 'NodeSocketGeometry', desc="Mesh with the authored channels.")
sock("Geometry", 'INPUT', 'NodeSocketGeometry', desc="Mesh whose vertex data is authored.")
sock("Selection", 'INPUT', 'NodeSocketBool', default=True,
     desc="Which elements are written. Unselected elements keep whatever the channel "
          "already held, so you can author one region at a time.")

p_src = iface.new_panel("Sources")
sock("Source Object", 'INPUT', 'NodeSocketObject', parent=p_src,
     desc="Reference object for the Distance To Object and Radial Distance sources. "
          "Radial Distance falls back to this object's own origin when it is empty.")
sock("Seed", 'INPUT', 'NodeSocketInt', parent=p_src, default=0,
     desc="Drives every Random source. Same seed and same mesh give the same result.")
sock("Compute Ambient Occlusion", 'INPUT', 'NodeSocketBool', parent=p_src, default=False,
     desc="Enable the five-ray self-occlusion pass. It raycasts the mesh against itself, "
          "so leave it off unless a channel actually reads Ambient Occlusion.")
sock("Occlusion Distance", 'INPUT', 'NodeSocketFloat', parent=p_src, default=1.0, mn=0.0,
     subtype='DISTANCE',
     desc="How far the occlusion rays travel -- roughly the radius of the detail you want "
          "shaded. Larger values darken more.")
sock("Occlusion Spread", 'INPUT', 'NodeSocketFloat', parent=p_src, default=0.7,
     mn=0.0, mx=1.0, subtype='FACTOR',
     desc="How far the four side rays tilt away from the normal. 0 fires every ray "
          "straight out, 1 fires them nearly along the surface.")
sock("Compute Boundary Distance", 'INPUT', 'NodeSocketBool', parent=p_src, default=False,
     desc="Enable the distance-to-boundary pass used by the Distance To Boundary source.")
sock("Boundary From Open Edges", 'INPUT', 'NodeSocketBool', parent=p_src, default=True,
     desc="Treat the mesh's own open edges as boundary. Turn it off to use only the "
          "Boundary Edges field.")
sock("Boundary Edges", 'INPUT', 'NodeSocketBool', parent=p_src, default=False,
     desc="Extra edges to treat as boundary. Bind it to an edge attribute to mark your own "
          "seams, hem lines or leaf stems.")
sock("Compute Object Distance", 'INPUT', 'NodeSocketBool', parent=p_src, default=False,
     desc="Enable the distance-to-Source-Object pass used by the Distance To Object source.")

CHAN_PARAMS = [
    ("Write",           'NodeSocketBool',   False, None, None,
     "Write this channel. Off leaves it untouched -- and a slot with no channel written is "
     "never created on the mesh at all."),
    ("Source",          'NodeSocketMenu',   None, None, None,
     "Which piece of mesh data feeds this channel."),
    ("Attribute",       'NodeSocketString', "",   None, None,
     "Name of the attribute to read, for the Attribute (...) sources. An existing UV map is "
     "read with Attribute (Vector); an existing colour attribute with Attribute (Color)."),
    ("Component",       'NodeSocketMenu',   None, None, None,
     "Which component of a vector or colour source to take. Ignored by scalar sources."),
    ("Constant Value",  'NodeSocketFloat',  0.0,  None, None,
     "The value written when Source is Constant."),
    ("Auto Range",      'NodeSocketBool',   False, None, None,
     "Measure the source's own minimum and maximum across the mesh and use those as the "
     "input range instead of From Min / From Max. Measured on the vertex domain."),
    ("From Min",        'NodeSocketFloat',  0.0,  None, None, "Source value that maps to To Min."),
    ("From Max",        'NodeSocketFloat',  1.0,  None, None, "Source value that maps to To Max."),
    ("To Min",          'NodeSocketFloat',  0.0,  None, None, "Value written at the bottom of the range."),
    ("To Max",          'NodeSocketFloat',  1.0,  None, None, "Value written at the top of the range."),
    ("Clamp",           'NodeSocketBool',   True, None, None,
     "Keep the result inside To Min .. To Max. Leave it on for colour, which is clipped to "
     "0-1 on export anyway."),
    ("Invert",          'NodeSocketBool',   False, None, None, "Flip the value inside its range."),
    ("Gamma",           'NodeSocketFloat',  1.0,  0.01, 10.0,
     "Contrast curve applied to the normalized value. 1 is linear, below 1 lifts the dark "
     "end, above 1 crushes it."),
    ("Quantize Steps",  'NodeSocketInt',    0,    0,   256,
     "Snap to this many evenly spaced levels. 0 or 1 disables it. Set it to the number of "
     "distinct values you need when packing an index into an 8-bit colour channel."),
    ("Blur Iterations", 'NodeSocketInt',    0,    0,   100,
     "Smooth the finished value across neighbouring elements. 0 disables it."),
]
SRGB_PARAM = ("Encode sRGB", 'NodeSocketBool', False, None, None,
              "Convert this channel from linear to sRGB. Only use it when your exporter "
              "writes raw colour -- Blender's FBX exporter has its own Color Space option "
              "and doing both converts twice.")

COLOR_SLOTS = [
    ("Col 1", "Col",  "The main colour attribute -- the one Unreal's FBX importer reads."),
    ("Col 2", "Col2", "Second colour attribute. Unity can read it; Unreal imports only the first."),
    ("Col 3", "Col3", "Third colour attribute."),
    ("Col 4", "Col4", "Fourth colour attribute."),
]
UV_SLOTS = [
    ("UV0", "UVMap", "The main texture UV. Usually leave this alone and pack data into UV1 and up."),
    ("UV1", "UV1", "Second UV set. In Unreal this slot is normally taken by the lightmap."),
    ("UV2", "UV2", "Third UV set."),  ("UV3", "UV3", "Fourth UV set."),
    ("UV4", "UV4", "Fifth UV set."),  ("UV5", "UV5", "Sixth UV set."),
    ("UV6", "UV6", "Seventh UV set."),("UV7", "UV7", "Eighth UV set."),
]

CHANNELS = []
def channel_iface(prefix, letter, parent, is_color):
    p = subpanel(letter, parent)
    entries = list(CHAN_PARAMS) + ([SRGB_PARAM] if is_color else [])
    socks = {}
    for pname, stype, dflt, mn, mx, desc in entries:
        socks[pname] = sock(f"{prefix} {pname}", 'INPUT', stype, parent=p,
                            default=dflt, mn=mn, mx=mx, desc=desc)
    CHANNELS.append((prefix, socks, is_color))
    return socks

COLOR_IFACE = []
for slot_key, dflt_name, slot_desc in COLOR_SLOTS:
    pp = iface.new_panel(f"Color Attribute {slot_key[-1]}", default_closed=True)
    nm = sock(f"{slot_key} Name", 'INPUT', 'NodeSocketString', parent=pp, default=dflt_name,
              desc=slot_desc + " This is the attribute name on the mesh and the layer name "
                               "in the exported file.")
    dm = sock(f"{slot_key} Domain", 'INPUT', 'NodeSocketMenu', parent=pp,
              desc="Vertex stores one colour per vertex (smaller, always continuous); Face "
                   "Corner stores one per corner, which is what you need for a hard colour "
                   "split across an edge. FBX writes both out per corner.")
    dt = sock(f"{slot_key} Data Type", 'INPUT', 'NodeSocketMenu', parent=pp,
              desc="Byte is 8 bits per channel and is what game engines actually keep. Float "
                   "is full precision inside Blender but is still narrowed by most importers. "
                   "Pick Byte unless you stay in Blender.")
    chans = [channel_iface(f"{slot_key} {c}", c, pp, True) for c in ("R", "G", "B", "A")]
    COLOR_IFACE.append((slot_key, nm, dm, dt, chans))

UV_IFACE = []
for slot_key, dflt_name, slot_desc in UV_SLOTS:
    pp = iface.new_panel(f"UV Map {slot_key}", default_closed=True)
    nm = sock(f"{slot_key} Name", 'INPUT', 'NodeSocketString', parent=pp, default=dflt_name,
              desc=slot_desc + " This is the UV map name on the mesh and the layer name in "
                               "the exported file.")
    chans = [channel_iface(f"{slot_key} {c}", c, pp, False) for c in ("U", "V")]
    UV_IFACE.append((slot_key, nm, chans))

n_sock = len([i for i in iface.items_tree if i.item_type == 'SOCKET'])
n_pan  = len([i for i in iface.items_tree if i.item_type == 'PANEL'])
print(f"BUILD: interface: {n_sock} sockets, {n_pan} panels", flush=True)

# ============================================================================= GRAPH
GI = ng.nodes.new("NodeGroupInput")
GO = ng.nodes.new("NodeGroupOutput")
def g(key): return (GI, key)

t.f("Slot Domain & Type")
DOMAIN_ITEMS = ["Vertex", "Face Corner"]
TYPE_ITEMS   = ["Byte Color (8-bit)", "Float Color"]
dom_switches, typ_switches = [], []
for slot_key, nm, dm, dt, chans in COLOR_IFACE:
    ms = t.n("GeometryNodeMenuSwitch", f"{slot_key} Domain -> Index", data_type='INT')
    menu_items(ms, DOMAIN_ITEMS, ["One colour per vertex.", "One colour per face corner."])
    for i in range(2):
        isock(ms, f"Item_{i}").default_value = i
    t.link(GI, dm.name, ms, "Menu")
    dm.default_value = DOMAIN_ITEMS[1]
    dom_switches.append(ms)
    mt = t.n("GeometryNodeMenuSwitch", f"{slot_key} Type -> Index", data_type='INT')
    menu_items(mt, TYPE_ITEMS, ["8 bits per channel, matching what engines keep.",
                                "Full float precision, for staying inside Blender."])
    for i in range(2):
        isock(mt, f"Item_{i}").default_value = i
    t.link(GI, dt.name, mt, "Menu")
    dt.default_value = TYPE_ITEMS[0]
    typ_switches.append(mt)

t.f("Mesh Facts")
bbox = t.n("GeometryNodeBoundBox", "Bounding Box")
t.link(GI, "Geometry", bbox, "Geometry")
dsize = t.n("GeometryNodeAttributeDomainSize", "Domain Size", component='MESH')
t.link(GI, "Geometry", dsize, "Geometry")
obji = t.n("GeometryNodeObjectInfo", "Source Object Info", transform_space='RELATIVE')
t.link(GI, "Source Object", obji, "Object")

t.f("Face Random")
f_idx    = t.n("GeometryNodeInputIndex", "Face Index")
f_seed   = fmath(t, 'ADD', g("Seed"), 11, "Seed + 11")
f_seed_i = t.n("FunctionNodeFloatToInt", "Seed To Int", rounding_mode='FLOOR')
t.link(f_seed, "Value", f_seed_i, "Float")
f_rnd = t.n("FunctionNodeRandomValue", "Random Per Face", data_type='FLOAT')
t.link(f_idx, "Index", f_rnd, "ID")
t.link(f_seed_i, "Integer", f_rnd, "Seed")
st_frnd = t.n("GeometryNodeStoreNamedAttribute", "Cache Face Random",
              data_type='FLOAT', domain='FACE')
t.set(st_frnd, "Name", A_FRAND)
t.link(GI, "Geometry", st_frnd, "Geometry")
t.link(f_rnd, "Value_001", st_frnd, "Value")

t.f("Island Data")
isl  = t.n("GeometryNodeInputMeshIsland", "Mesh Island")
pos0 = t.n("GeometryNodeInputPosition", "Position")
acc_cnt = t.n("GeometryNodeAccumulateField", "Island Point Count", data_type='FLOAT')
t.set(acc_cnt, "Value", 1.0)
t.link(isl, "Island Index", acc_cnt, "Group Index")
acc_pos = t.n("GeometryNodeAccumulateField", "Island Position Sum", data_type='FLOAT_VECTOR')
t.link(pos0, "Position", acc_pos, "Value")
t.link(isl, "Island Index", acc_pos, "Group Index")
cnt_safe = fmath(t, 'MAXIMUM', (acc_cnt, "Total"), 1.0, "Guard Count")
centroid = vmath(t, 'DIVIDE', (acc_pos, "Total"), None, "Island Centroid")
t.link(cnt_safe, "Value", centroid, 1)          # float -> vector broadcast
p_dot = vmath(t, 'DOT_PRODUCT', (pos0, "Position"), (pos0, "Position"), "Squared Length")
acc_d = t.n("GeometryNodeAccumulateField", "Island Squared Sum", data_type='FLOAT')
t.link(p_dot, "Value", acc_d, "Value")
t.link(isl, "Island Index", acc_d, "Group Index")
mean_d = fmath(t, 'DIVIDE', (acc_d, "Total"), (cnt_safe, "Value"), "Mean Squared Length")
c_dot  = vmath(t, 'DOT_PRODUCT', (centroid, "Vector"), (centroid, "Vector"), "Squared Centroid")
var    = fmath(t, 'SUBTRACT', (mean_d, "Value"), (c_dot, "Value"), "Variance")
var_p  = fmath(t, 'MAXIMUM', (var, "Value"), 0.0, "Guard Negative")
rms    = fmath(t, 'SQRT', (var_p, "Value"), None, "Island RMS Size")
isl_f  = fmath(t, 'ADD', None, 0.0, "Island Index As Float")
t.link(isl, "Island Index", isl_f, 0)
icnt_sub = fmath(t, 'SUBTRACT', None, 1.0, "Island Count - 1")
t.link(isl, "Island Count", icnt_sub, 0)
icnt_m1 = fmath(t, 'MAXIMUM', (icnt_sub, "Value"), 1.0, "Guard Island Count")
isl_n   = fmath(t, 'DIVIDE', (isl_f, "Value"), (icnt_m1, "Value"), "Island Index Normalized")
i_seed  = fmath(t, 'ADD', g("Seed"), 23, "Seed + 23")
i_seed_i = t.n("FunctionNodeFloatToInt", "Island Seed To Int", rounding_mode='FLOOR')
t.link(i_seed, "Value", i_seed_i, "Float")
i_rnd = t.n("FunctionNodeRandomValue", "Random Per Island", data_type='FLOAT')
t.link(isl, "Island Index", i_rnd, "ID")
t.link(i_seed_i, "Integer", i_rnd, "Seed")

def store(prev, name, value_node, value_sock, dtype='FLOAT', domain='POINT'):
    s = t.n("GeometryNodeStoreNamedAttribute", f"Cache {name}", data_type=dtype, domain=domain)
    t.set(s, "Name", name)
    t.link(prev[0], prev[1], s, "Geometry")
    t.link(value_node, value_sock, s, "Value")
    return (s, "Geometry")

cur = (st_frnd, "Geometry")
cur = store(cur, A_IIDX, isl_f,    "Value")
cur = store(cur, A_INRM, isl_n,    "Value")
cur = store(cur, A_IRND, i_rnd,    "Value_001")
cur = store(cur, A_ICEN, centroid, "Vector", dtype='FLOAT_VECTOR')
cur = store(cur, A_ISIZ, rms,      "Value")

t.f("Curvature")
eang = t.n("GeometryNodeInputMeshEdgeAngle", "Edge Angle")
curv = t.n("GeometryNodeFieldOnDomain", "Average Onto Vertices", data_type='FLOAT', domain='POINT')
t.link(eang, "Signed Angle", curv, "Value")
cur = store(cur, A_CURV, curv, "Value")

t.f("Ambient Occlusion")
ao_geo = switch(t, 'GEOMETRY', g("Compute Ambient Occlusion"), None, cur, "Gate AO Geometry")
nrm1 = t.n("GeometryNodeInputNormal", "Normal")
pos1 = t.n("GeometryNodeInputPosition", "Position")
# tangent basis: pick the reference axis the normal is NOT parallel to, or the cross degenerates
ref_a = vmath(t, 'CROSS_PRODUCT', (nrm1, "Normal"), (0.0, 0.0, 1.0), "Normal Cross Z")
ref_b = vmath(t, 'CROSS_PRODUCT', (nrm1, "Normal"), (1.0, 0.0, 0.0), "Normal Cross X")
len_a = vmath(t, 'LENGTH', (ref_a, "Vector"), None, "Length Of Cross Z")
degen = t.n("FunctionNodeCompare", "Normal Parallel To Z", data_type='FLOAT', operation='LESS_THAN')
t.link(len_a, "Value", degen, "A")
isock(degen, "B").default_value = 1e-3
tan_r = switch(t, 'VECTOR', (degen, "Result"), (ref_a, "Vector"), (ref_b, "Vector"), "Pick Reference")
tanv  = vmath(t, 'NORMALIZE', (tan_r, "Output"), None, "Tangent")
bitv  = vmath(t, 'CROSS_PRODUCT', (nrm1, "Normal"), (tanv, "Vector"), "Bitangent")
eps   = fmath(t, 'MULTIPLY', g("Occlusion Distance"), 1e-4, "Ray Bias")
lift  = vmath(t, 'SCALE', (nrm1, "Normal"), None, "Lift Along Normal")
t.link(eps, "Value", lift, "Scale")
origin = vmath(t, 'ADD', (pos1, "Position"), (lift, "Vector"), "Ray Origin")
spread_a = fmath(t, 'MULTIPLY', g("Occlusion Spread"), pymath.pi * 0.5 * 0.9, "Spread Angle")
sp_sin = fmath(t, 'SINE', (spread_a, "Value"), None, "Sine Of Spread")
sp_cos = fmath(t, 'COSINE', (spread_a, "Value"), None, "Cosine Of Spread")
n_part = vmath(t, 'SCALE', (nrm1, "Normal"), None, "Normal Part")
t.link(sp_cos, "Value", n_part, "Scale")

ray_dirs = []
for k, (ca, sa) in enumerate([(1, 0), (0, 1), (-1, 0), (0, -1)]):
    tm = fmath(t, 'MULTIPLY', (sp_sin, "Value"), float(ca), f"Tangent Weight {k}")
    tp = vmath(t, 'SCALE', (tanv, "Vector"), None, f"Tangent Part {k}")
    t.link(tm, "Value", tp, "Scale")
    bm = fmath(t, 'MULTIPLY', (sp_sin, "Value"), float(sa), f"Bitangent Weight {k}")
    bp = vmath(t, 'SCALE', (bitv, "Vector"), None, f"Bitangent Part {k}")
    t.link(bm, "Value", bp, "Scale")
    side = vmath(t, 'ADD', (tp, "Vector"), (bp, "Vector"), f"Side Offset {k}")
    ray_dirs.append(vmath(t, 'ADD', (n_part, "Vector"), (side, "Vector"), f"Ray Direction {k}"))
ray_dirs.append(n_part)                                   # the straight-out ray

hits = []
for k, d in enumerate(ray_dirs):
    rc = t.n("GeometryNodeRaycast", f"Occlusion Ray {k}")
    t.link(ao_geo, "Output", rc, "Target Geometry")
    t.link(origin, "Vector", rc, "Source Position")
    t.link(d, "Vector", rc, "Ray Direction")
    t.link(GI, "Occlusion Distance", rc, "Ray Length")
    hv = fmath(t, 'ADD', None, 0.0, f"Hit {k} As Float")
    t.link(rc, "Is Hit", hv, 0)
    hits.append(hv)
hs = hits[0]
for k in range(1, len(hits)):
    hs = fmath(t, 'ADD', (hs, "Value"), (hits[k], "Value"), f"Sum Hits {k}")
occ  = fmath(t, 'DIVIDE', (hs, "Value"), float(len(hits)), "Occlusion Fraction")
ao_v = fmath(t, 'SUBTRACT', 1.0, (occ, "Value"), "Ambient Occlusion")
ao_final = switch(t, 'FLOAT', g("Compute Ambient Occlusion"), 1.0, (ao_v, "Value"), "AO Or One")
cur = store(cur, A_AO, ao_final, "Output")

t.f("Boundary Distance")
en = t.n("GeometryNodeInputMeshEdgeNeighbors", "Edge Face Count")
open_e = t.n("FunctionNodeCompare", "Is Open Edge", data_type='INT', operation='LESS_THAN')
t.link(en, "Face Count", open_e, "A_INT")
isock(open_e, "B_INT").default_value = 2
open_g = t.n("FunctionNodeBooleanMath", "Open Edges Enabled", operation='AND')
t.link(open_e, "Result", open_g, 0)
t.link(GI, "Boundary From Open Edges", open_g, 1)
bsel = t.n("FunctionNodeBooleanMath", "Boundary Selection", operation='OR')
t.link(open_g, "Boolean", bsel, 0)
t.link(GI, "Boundary Edges", bsel, 1)
bd_geo = switch(t, 'GEOMETRY', g("Compute Boundary Distance"), None, cur, "Gate Boundary Geometry")
bsep = t.n("GeometryNodeSeparateGeometry", "Isolate Boundary Edges", domain='EDGE')
t.link(bd_geo, "Output", bsep, "Geometry")
t.link(bsel, "Boolean", bsep, "Selection")
bprox = t.n("GeometryNodeProximity", "Distance To Boundary")
try:
    bprox.target_element = 'EDGES'
except Exception as e:
    print("BUILD: proximity target_element not settable:", e, flush=True)
t.link(bsep, "Selection", bprox, "Target")
pos2 = t.n("GeometryNodeInputPosition", "Position")
t.link(pos2, "Position", bprox, "Source Position")
bd_final = switch(t, 'FLOAT', g("Compute Boundary Distance"), 0.0, (bprox, "Distance"),
                  "Boundary Distance Or Zero")
cur = store(cur, A_BDIST, bd_final, "Output")

t.f("Object Distance")
od_geo = switch(t, 'GEOMETRY', g("Compute Object Distance"), None, (obji, "Geometry"),
                "Gate Object Geometry")
oprox = t.n("GeometryNodeProximity", "Distance To Object")
try:
    oprox.target_element = 'FACES'
except Exception:
    pass
t.link(od_geo, "Output", oprox, "Target")
pos3 = t.n("GeometryNodeInputPosition", "Position")
t.link(pos3, "Position", oprox, "Source Position")
od_final = switch(t, 'FLOAT', g("Compute Object Distance"), 0.0, (oprox, "Distance"),
                  "Object Distance Or Zero")
cur = store(cur, A_ODIST, od_final, "Output")
BUS = cur

t.f("Channels")
chan_out = {}
for prefix, socks, is_color in CHANNELS:
    gnode = t.n("GeometryNodeGroup", prefix)
    gnode.node_tree = hg
    t.link(BUS[0], BUS[1], gnode, "Geometry")
    t.link(GI, "Selection", gnode, "Selection Mask")
    t.link(bbox, "Min", gnode, "Bounds Min")
    t.link(bbox, "Max", gnode, "Bounds Max")
    t.link(obji, "Location", gnode, "Center Position")
    t.link(dsize, "Point Count", gnode, "Point Count")
    t.link(GI, "Seed", gnode, "Seed")
    for pname, s in socks.items():
        if pname == "Write":
            continue
        t.link(GI, s.name, gnode, pname)
    chan_out[prefix] = gnode
    socks["Source"].default_value    = SRC_LABELS[0]
    socks["Component"].default_value = COMPONENTS[0]

def any_write(names, label):
    node = t.n("FunctionNodeBooleanMath", label, operation='OR')
    t.link(GI, names[0], node, 0)
    t.link(GI, names[1], node, 1)
    for nm_ in names[2:]:
        nxt = t.n("FunctionNodeBooleanMath", label, operation='OR')
        t.link(node, "Boolean", nxt, 0)
        t.link(GI, nm_, nxt, 1)
        node = nxt
    return node

geo = BUS
for si, (slot_key, nm, dm, dt, chans) in enumerate(COLOR_IFACE):
    t.f(f"Write {slot_key}")
    ex = t.n("GeometryNodeInputNamedAttribute", f"{slot_key} Existing", data_type='FLOAT_COLOR')
    t.link(GI, nm.name, ex, "Name")
    sep = t.n("FunctionNodeSeparateColor", f"{slot_key} Split Existing")
    t.link(ex, "Attribute", sep, "Color")
    comb = t.n("FunctionNodeCombineColor", f"{slot_key} Combine")
    for cname, sockname in zip("RGBA", ("Red", "Green", "Blue", "Alpha")):
        prefix = f"{slot_key} {cname}"
        # a colour attribute that does not exist yet starts at opaque black
        base = switch(t, 'FLOAT', (ex, "Exists"), 1.0 if cname == "A" else 0.0,
                      (sep, sockname), f"{prefix} Existing Or Default")
        pick = switch(t, 'FLOAT', g(f"{prefix} Write"), (base, "Output"),
                      (chan_out[prefix], "Value"), f"{prefix} Write Or Keep")
        t.link(pick, "Output", comb, sockname)
    anyw = any_write([f"{slot_key} {c} Write" for c in "RGBA"], f"{slot_key} Any Write")
    idx = fmath(t, 'MULTIPLY_ADD', None, 2.0, f"{slot_key} Variant Index")
    t.link(dom_switches[si], "Output", idx, 0)
    t.link(typ_switches[si], "Output", idx, 2)
    idx_i = t.n("FunctionNodeFloatToInt", f"{slot_key} Variant Int", rounding_mode='ROUND')
    t.link(idx, "Value", idx_i, "Float")
    ixg = t.n("GeometryNodeIndexSwitch", f"{slot_key} Domain And Type", data_type='GEOMETRY')
    while len(ixg.index_switch_items) < 4:
        ixg.index_switch_items.new()
    t.link(idx_i, "Integer", ixg, "Index")
    for vi, (dom, dty) in enumerate([('POINT', 'BYTE_COLOR'), ('POINT', 'FLOAT_COLOR'),
                                     ('CORNER', 'BYTE_COLOR'), ('CORNER', 'FLOAT_COLOR')]):
        s = t.n("GeometryNodeStoreNamedAttribute",
                f"{slot_key} Store {dom.title()} {dty.split('_')[0].title()}",
                data_type=dty, domain=dom)
        t.link(geo[0], geo[1], s, "Geometry")
        t.link(GI, nm.name, s, "Name")
        t.link(GI, "Selection", s, "Selection")
        t.link(comb, "Color", s, "Value")
        t.link(s, "Geometry", ixg, f"Item_{vi}")
    sw = switch(t, 'GEOMETRY', (anyw, "Boolean"), geo, (ixg, "Output"), f"{slot_key} Enabled")
    geo = (sw, "Output")

for slot_key, nm, chans in UV_IFACE:
    t.f(f"Write {slot_key}")
    ex = t.n("GeometryNodeInputNamedAttribute", f"{slot_key} Existing", data_type='FLOAT_VECTOR')
    t.link(GI, nm.name, ex, "Name")
    sep = t.n("ShaderNodeSeparateXYZ", f"{slot_key} Split Existing")
    t.link(ex, "Attribute", sep, "Vector")
    comb = t.n("ShaderNodeCombineXYZ", f"{slot_key} Combine")
    for cname, axis in (("U", "X"), ("V", "Y")):
        prefix = f"{slot_key} {cname}"
        base = switch(t, 'FLOAT', (ex, "Exists"), 0.0, (sep, axis), f"{prefix} Existing Or Default")
        pick = switch(t, 'FLOAT', g(f"{prefix} Write"), (base, "Output"),
                      (chan_out[prefix], "Value"), f"{prefix} Write Or Keep")
        t.link(pick, "Output", comb, axis)
    anyw = any_write([f"{slot_key} {c} Write" for c in ("U", "V")], f"{slot_key} Any Write")
    s = t.n("GeometryNodeStoreNamedAttribute", f"{slot_key} Store UV",
            data_type='FLOAT2', domain='CORNER')
    t.link(geo[0], geo[1], s, "Geometry")
    t.link(GI, nm.name, s, "Name")
    t.link(GI, "Selection", s, "Selection")
    t.link(comb, "Vector", s, "Value")
    sw = switch(t, 'GEOMETRY', (anyw, "Boolean"), geo, (s, "Geometry"), f"{slot_key} Enabled")
    geo = (sw, "Output")

t.f("Strip Cached Sources")
for a in CACHED:
    r = t.n("GeometryNodeRemoveAttribute", f"Remove {a.replace('__vdc_', '')}")
    t.set(r, "Name", a)
    t.link(geo[0], geo[1], r, "Geometry")
    geo = (r, "Geometry")
ng.links.new(osock(geo[0], geo[1]), isock(GO, "Geometry"))
print(f"BUILD: main graph: {len(ng.nodes)} nodes, {len(ng.links)} links", flush=True)

# ============================================================================= PUBLISH
hg.asset_mark(); hg.asset_data.tags.new("ST3E")
hg.is_modifier = False; hg.is_tool = False
hg.asset_data.description = ("Helper for GN_VertexDataComposer: selects one mesh data source "
                             "and runs the per-channel processing chain.")
ng.asset_mark()
ng.asset_data.catalog_id = CAT
ng.asset_data.tags.new("ST3E")
ng.is_modifier = True
ng.is_tool = False
ng.asset_data.description = (
    "Authors every piece of vertex data an FBX mesh can carry: 4 colour attributes (RGBA) "
    "and 8 UV maps (U/V), 32 independently writable channels. Each channel picks one of 30 "
    "mesh data sources -- position, normal, curvature, ambient occlusion, per-island randoms "
    "and pivots, distance fields -- then remaps, clamps, inverts, gamma-corrects, quantizes "
    "and blurs it before writing. Channels left off are untouched, and unused slots are "
    "never created.")

# ============================================================================= DEMO
bpy.ops.mesh.primitive_monkey_add(size=2.0)          # Suzanne: body + 2 eye islands
demo = bpy.context.object
demo.name = "GN_Demo"
md = demo.modifiers.new(NAME, 'NODES')
md.node_group = ng

ID = {s.name: s.identifier for s in iface.items_tree if s.item_type == 'SOCKET'}
def setv(name, value):
    md[ID[name]] = value

setv("Compute Ambient Occlusion", True)
setv("Occlusion Distance", 0.6)
setv("Col 1 R Write", True); setv("Col 1 R Source", SRC["Ambient Occlusion"])
setv("Col 1 R Auto Range", True)
setv("Col 1 G Write", True); setv("Col 1 G Source", SRC["Curvature"])
setv("Col 1 G Auto Range", True)
setv("Col 1 B Write", True); setv("Col 1 B Source", SRC["Random (Per Island)"])
setv("UV1 U Write", True);  setv("UV1 U Source", SRC["Offset From Island Centroid"])
setv("UV1 U Component", 0); setv("UV1 U From Min", -1.0); setv("UV1 U From Max", 1.0)
setv("UV1 U To Min", -1.0); setv("UV1 U To Max", 1.0)
setv("UV1 V Write", True);  setv("UV1 V Source", SRC["Offset From Island Centroid"])
setv("UV1 V Component", 2); setv("UV1 V From Min", -1.0); setv("UV1 V From Max", 1.0)
setv("UV1 V To Min", -1.0); setv("UV1 V To Max", 1.0)
demo.update_tag()

bpy.ops.object.select_all(action='DESELECT')
demo.select_set(True)
bpy.context.view_layer.objects.active = demo

dg = bpy.context.evaluated_depsgraph_get()
ev = demo.evaluated_get(dg).data
print(f"BUILD: demo evaluated -- verts={len(ev.vertices)} "
      f"colors={[c.name for c in ev.color_attributes]} uvs={[u.name for u in ev.uv_layers]}",
      flush=True)
leaked = [a for a in ev.attributes.keys() if a.startswith("__vdc")]
print(f"BUILD: leaked internal attributes: {leaked}", flush=True)

bpy.ops.wm.save_as_mainfile(filepath=PATH)
print(f"BUILD: saved {PATH}", flush=True)
sys.stdout.flush()
os._exit(0)
