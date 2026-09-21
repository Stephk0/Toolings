"""Build GN_AmbientOcclusion.blend -- a Geometry Nodes MODIFIER that bakes raycast
ambient occlusion into a colour attribute (vertex colours) and/or a float attribute.

Two node groups are produced:

  GNG_AmbientOcclusion  the reusable sampling core.  Geometry in -> geometry out plus an
                        "Ambient Occlusion" float FIELD.  A Repeat Zone fires ONE raycast
                        node `Samples` times, accumulating hits into a cache attribute on
                        the geometry (a Repeat Zone cannot carry per-element field state,
                        so the geometry itself is the accumulator).  This group is what
                        other .blend files link -- GN_VertexDataComposer does exactly that.

  GN_AmbientOcclusion   the modifier wrapper: occluder inputs, shaping (auto range, gamma,
                        invert, strength), blur, and the write block that targets a colour
                        attribute, a float attribute, or both, on Point or Face Corner.

Sampling maths: sample k of N takes u = (k + 0.5) / N, cos(theta) = 1 - u*spread (uniform)
or sqrt(1 - u*spread) (cosine weighted), azimuth = k * golden angle + a per-point random
offset, so the sample set is rotated per vertex and never bands.

Run headless:
  "C:\\Program Files\\Blender Foundation\\Blender 5.0\\blender.exe" --background \
      --factory-startup --python build_gn_ambient_occlusion.py
"""
import bpy, os, sys, math as pymath

GEO  = r"D:\Stephko_Tooling\Toolings\Blender\Geonodes"
NAME = "GN_AmbientOcclusion"
HELP = "GNG_AmbientOcclusion"
PATH = os.path.join(GEO, NAME + ".blend")
CAT  = "9b90781b-f051-4cdb-9dcb-c8909914a87b"      # ST3E/Modify

A_TMP     = "__ao_tmp"                              # wrapper's scratch cache, stripped at the end
GOLDEN    = 2.39996322972865332                     # golden angle, radians
TWO_PI    = 6.283185307179586

# ----------------------------------------------------------------------------- helpers
def _pick(sockets, key):
    """Resolve a socket by index, identifier or display name -- preferring the ENABLED
    variant.  Multi-type nodes keep DISABLED same-name sockets whose links silently
    no-op at evaluation time."""
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

# ============================================================================= clean slate
for _nm in (NAME, HELP):
    while _nm in bpy.data.node_groups:
        bpy.data.node_groups.remove(bpy.data.node_groups[_nm])

# ############################################################################# HELPER GROUP
hg = bpy.data.node_groups.new(HELP, "GeometryNodeTree")
h  = Tree(hg)
hi = hg.interface

def hsock(name, in_out, stype, parent=None, default=None, mn=None, mx=None,
          subtype=None, desc=""):
    s = hi.new_socket(name, in_out=in_out, socket_type=stype, parent=parent)
    if default is not None: s.default_value = default
    if mn is not None:      s.min_value = mn
    if mx is not None:      s.max_value = mx
    if subtype:             s.subtype = subtype
    s.description = desc
    return s

hsock("Geometry", 'OUTPUT', 'NodeSocketGeometry',
      desc="The input mesh, carrying the occlusion result in the Cache Attribute.")
hsock("Ambient Occlusion", 'OUTPUT', 'NodeSocketFloat',
      desc="Openness: 1 is fully exposed, 0 is fully enclosed. Evaluate it on the Geometry "
           "this group outputs -- it reads the Cache Attribute stored there.")

hsock("Geometry", 'INPUT', 'NodeSocketGeometry',
      desc="Mesh to shade. It is also the default occluder, see Self Occlusion.")
hsock("Selection", 'INPUT', 'NodeSocketBool', default=True,
      desc="Which points are shaded. Unselected points read 1, i.e. fully open.")

hp_s = hi.new_panel("Sampling")
hsock("Occluders", 'INPUT', 'NodeSocketGeometry', parent=hp_s,
      desc="Extra geometry the rays can hit, on top of the mesh itself. Leave it empty for "
           "pure self-occlusion.")
hsock("Samples", 'INPUT', 'NodeSocketInt', parent=hp_s, default=8, mn=1, mx=256,
      desc="Rays fired per point. Cost is linear -- 8 is a good preview, 32 to 64 a clean "
           "bake. Values below 1 are clamped to 1.")
hsock("Distance", 'INPUT', 'NodeSocketFloat', parent=hp_s, default=1.0, mn=0.0,
      subtype='DISTANCE',
      desc="How far the rays travel, roughly the radius of the detail you want shaded. "
           "Anything further away never darkens the point.")
hsock("Spread", 'INPUT', 'NodeSocketFloat', parent=hp_s, default=1.0, mn=0.0, mx=1.0,
      subtype='FACTOR',
      desc="Width of the sampling cone around the normal. 1 is the full hemisphere, small "
           "values tighten the rays towards the normal and only catch head-on blockers.")
hsock("Cosine Weighted", 'INPUT', 'NodeSocketBool', parent=hp_s, default=True,
      desc="Distribute the rays by the cosine of the angle to the normal, matching how a "
           "surface actually gathers light. Off spreads them evenly over the cone.")
hsock("Distance Falloff", 'INPUT', 'NodeSocketBool', parent=hp_s, default=True,
      desc="Weight each hit by how close the blocker is, so a contact crease darkens more "
           "than a distant wall. Off counts every hit fully.")
hsock("Bias", 'INPUT', 'NodeSocketFloat', parent=hp_s, default=0.001, mn=0.0,
      subtype='DISTANCE',
      desc="How far the ray origin is lifted along the normal, so a ray cannot hit the face "
           "it started from. Raise it if a flat surface comes out speckled.")
hsock("Jitter", 'INPUT', 'NodeSocketFloat', parent=hp_s, default=1.0, mn=0.0, mx=1.0,
      subtype='FACTOR',
      desc="Randomly rotates each point's sample set around its normal. 1 trades banding for "
           "fine noise, 0 gives every point the identical ray pattern.")
hsock("Seed", 'INPUT', 'NodeSocketInt', parent=hp_s, default=0,
      desc="Drives the jitter rotation. Same seed and same mesh give the same result.")
hsock("Self Occlusion", 'INPUT', 'NodeSocketBool', parent=hp_s, default=True,
      desc="Let the mesh occlude itself. Turn it off to measure only what the Occluders "
           "input blocks.")

hp_c = hi.new_panel("Cache", default_closed=True)
hsock("Cache Attribute", 'INPUT', 'NodeSocketString', parent=hp_c, default=A_TMP,
      desc="Name of the float attribute the result is stored in on the output geometry. The "
           "Ambient Occlusion output reads this name, so the caller owns it and is "
           "responsible for removing it again.")

HGI = h.n("NodeGroupInput",  "In")
HGO = h.n("NodeGroupOutput", "Out")
def hg_(name): return (HGI, name)

# ----------------------------------------------------------------- ray target + accumulator
h.f("Ray Target")
self_geo = switch(h, 'GEOMETRY', hg_("Self Occlusion"), None, hg_("Geometry"),
                  "Self As Occluder")
target = h.n("GeometryNodeJoinGeometry", "Join Occluders")
h.link(self_geo, "Output", target, "Geometry")
h.link(HGI, "Occluders", target, "Geometry")

h.f("Reset Accumulator")
n_safe = fmath(h, 'MAXIMUM', hg_("Samples"), 1.0, "Guard Sample Count")
init = h.n("GeometryNodeStoreNamedAttribute", "Clear Cache",
           data_type='FLOAT', domain='POINT')
h.link(HGI, "Geometry", init, "Geometry")
h.link(HGI, "Cache Attribute", init, "Name")
h.set(init, "Value", 0.0)

# ------------------------------------------------------------------------------ sample loop
# A frame is one layout band, but a Repeat Zone BRACKETS its body: keep the two ends in
# their own frames, created before and after the body, or the whole loop body lays out to
# the left of its own input and every entry link reads backwards (R3).
h.f("Sample Loop Start")
ri = h.n("GeometryNodeRepeatInput",  "Sample Loop Start")
ro = h.n("GeometryNodeRepeatOutput", "Sample Loop End")   # re-parented past the body below
ri.pair_with_output(ro)

# A Repeat Zone cannot carry per-element field state, so every scalar the loop body needs
# has to enter as its own loop item; the geometry is what carries the accumulated hits.
ITEMS = [('GEOMETRY', "Geometry"), ('GEOMETRY', "Target"), ('STRING', "Cache"),
         ('FLOAT', "Sample Count"), ('FLOAT', "Distance"), ('FLOAT', "Spread"),
         ('FLOAT', "Bias"), ('FLOAT', "Jitter"), ('INT', "Seed"),
         ('BOOLEAN', "Cosine Weighted"), ('BOOLEAN', "Distance Falloff")]
ro.repeat_items[0].name = "Geometry"
for stype, nm in ITEMS[1:]:
    ro.repeat_items.new(stype, nm)

h.link(n_safe, "Value", ri, "Iterations")     # one pass per sample
h.link(init,   "Geometry", ri, "Geometry")
h.link(target, "Geometry", ri, "Target")
h.link(HGI, "Cache Attribute",  ri, "Cache")
h.link(n_safe, "Value",         ri, "Sample Count")
h.link(HGI, "Distance",         ri, "Distance")
h.link(HGI, "Spread",           ri, "Spread")
h.link(HGI, "Bias",             ri, "Bias")
h.link(HGI, "Jitter",           ri, "Jitter")
h.link(HGI, "Seed",             ri, "Seed")
h.link(HGI, "Cosine Weighted",  ri, "Cosine Weighted")
h.link(HGI, "Distance Falloff", ri, "Distance Falloff")
# every item that is not the accumulator loops straight through, or it resets each pass
for _stype, nm in ITEMS[1:]:
    h.link(ri, nm, ro, nm)

h.f("Ray Basis")
nrm = h.n("GeometryNodeInputNormal",   "Normal")
pos = h.n("GeometryNodeInputPosition", "Position")
# pick the reference axis the normal is NOT parallel to, or the cross product degenerates
ref_a = vmath(h, 'CROSS_PRODUCT', (nrm, "Normal"), (0.0, 0.0, 1.0), "Normal Cross Z")
ref_b = vmath(h, 'CROSS_PRODUCT', (nrm, "Normal"), (1.0, 0.0, 0.0), "Normal Cross X")
len_a = vmath(h, 'LENGTH', (ref_a, "Vector"), None, "Length Of Cross Z")
degen = h.n("FunctionNodeCompare", "Normal Parallel To Z",
            data_type='FLOAT', operation='LESS_THAN')
h.link(len_a, "Value", degen, "A")
isock(degen, "B").default_value = 1e-3
tan_r = switch(h, 'VECTOR', (degen, "Result"), (ref_a, "Vector"), (ref_b, "Vector"),
               "Pick Reference Axis")
tanv = vmath(h, 'NORMALIZE', (tan_r, "Output"), None, "Tangent")
bitv = vmath(h, 'CROSS_PRODUCT', (nrm, "Normal"), (tanv, "Vector"), "Bitangent")
lift = vmath(h, 'SCALE', (nrm, "Normal"), None, "Lift Along Normal")
h.link(ri, "Bias", lift, "Scale")
origin = vmath(h, 'ADD', (pos, "Position"), (lift, "Vector"), "Ray Origin")

h.f("Sample Direction")
it_f  = fmath(h, 'ADD', None, 0.0, "Iteration As Float")
h.link(ri, "Iteration", it_f, 0)
it_h  = fmath(h, 'ADD', (it_f, "Value"), 0.5, "Sample Centre")
u     = fmath(h, 'DIVIDE', (it_h, "Value"), None, "Sample Fraction")
h.link(ri, "Sample Count", u, 1)
u_s   = fmath(h, 'MULTIPLY', (u, "Value"), None, "Scaled By Spread")
h.link(ri, "Spread", u_s, 1)
c_uni = fmath(h, 'SUBTRACT', 1.0, (u_s, "Value"), "Uniform Cosine")
c_uni_p = fmath(h, 'MAXIMUM', (c_uni, "Value"), 0.0, "Guard Cosine")
c_cos = fmath(h, 'SQRT', (c_uni_p, "Value"), None, "Cosine Weighted Cosine")
cos_t = switch(h, 'FLOAT', (ri, "Cosine Weighted"), (c_uni_p, "Value"), (c_cos, "Value"),
               "Pick Distribution")
cos_2 = fmath(h, 'MULTIPLY', (cos_t, "Output"), (cos_t, "Output"), "Cosine Squared")
sin_2 = fmath(h, 'SUBTRACT', 1.0, (cos_2, "Value"), "One Minus Cosine Squared")
sin_p = fmath(h, 'MAXIMUM', (sin_2, "Value"), 0.0, "Guard Sine")
sin_t = fmath(h, 'SQRT', (sin_p, "Value"), None, "Sine Of Angle")
ga    = fmath(h, 'MULTIPLY', (it_f, "Value"), GOLDEN, "Golden Angle Step")
idx   = h.n("GeometryNodeInputIndex", "Point Index")
rphi  = h.n("FunctionNodeRandomValue", "Random Azimuth", data_type='FLOAT')
h.set(rphi, "Min_001", 0.0)
h.set(rphi, "Max_001", TWO_PI)
h.link(idx, "Index", rphi, "ID")
h.link(ri,  "Seed",  rphi, "Seed")
jit   = fmath(h, 'MULTIPLY', (rphi, "Value_001"), None, "Jittered Offset")
h.link(ri, "Jitter", jit, 1)
phi   = fmath(h, 'ADD', (ga, "Value"), (jit, "Value"), "Azimuth")
c_phi = fmath(h, 'COSINE', (phi, "Value"), None, "Cosine Of Azimuth")
s_phi = fmath(h, 'SINE',   (phi, "Value"), None, "Sine Of Azimuth")
t_w   = fmath(h, 'MULTIPLY', (sin_t, "Value"), (c_phi, "Value"), "Tangent Weight")
b_w   = fmath(h, 'MULTIPLY', (sin_t, "Value"), (s_phi, "Value"), "Bitangent Weight")
n_part = vmath(h, 'SCALE', (nrm, "Normal"), None, "Normal Part")
h.link(cos_t, "Output", n_part, "Scale")
t_part = vmath(h, 'SCALE', (tanv, "Vector"), None, "Tangent Part")
h.link(t_w, "Value", t_part, "Scale")
b_part = vmath(h, 'SCALE', (bitv, "Vector"), None, "Bitangent Part")
h.link(b_w, "Value", b_part, "Scale")
side  = vmath(h, 'ADD', (t_part, "Vector"), (b_part, "Vector"), "Side Offset")
ray_d = vmath(h, 'ADD', (n_part, "Vector"), (side, "Vector"), "Ray Direction")

h.f("Occlusion Ray")
rc = h.n("GeometryNodeRaycast", "Occlusion Ray")
h.link(ri,     "Target",  rc, "Target Geometry")
h.link(origin, "Vector",  rc, "Source Position")
h.link(ray_d,  "Vector",  rc, "Ray Direction")
h.link(ri,     "Distance", rc, "Ray Length")
hit_f = fmath(h, 'ADD', None, 0.0, "Hit As Float")
h.link(rc, "Is Hit", hit_f, 0)
d_safe = fmath(h, 'MAXIMUM', None, 1e-6, "Guard Ray Length")
h.link(ri, "Distance", d_safe, 0)
ratio = fmath(h, 'DIVIDE', (rc, "Hit Distance"), (d_safe, "Value"), "Hit Distance Ratio")
near  = fmath(h, 'SUBTRACT', 1.0, (ratio, "Value"), "Nearness")
near_c = fmath(h, 'MAXIMUM', (near, "Value"), 0.0, "Clamp Nearness")
w_fall = fmath(h, 'MULTIPLY', (hit_f, "Value"), (near_c, "Value"), "Falloff Weighted Hit")
weight = switch(h, 'FLOAT', (ri, "Distance Falloff"), (hit_f, "Value"), (w_fall, "Value"),
                "Pick Hit Weight")

h.f("Accumulate Hits")
prev = h.n("GeometryNodeInputNamedAttribute", "Read Accumulator", data_type='FLOAT')
h.link(ri, "Cache", prev, "Name")
acc = fmath(h, 'ADD', (prev, "Attribute"), (weight, "Output"), "Add Hit")
st_acc = h.n("GeometryNodeStoreNamedAttribute", "Write Accumulator",
             data_type='FLOAT', domain='POINT')
h.link(ri, "Geometry", st_acc, "Geometry")
h.link(ri, "Cache",    st_acc, "Name")
h.link(acc, "Value",   st_acc, "Value")
h.link(st_acc, "Geometry", ro, "Geometry")

# ------------------------------------------------------------------------------- normalize
fr_end = h.f("Sample Loop End")
ro.parent = fr_end

h.f("Normalize To Openness")
raw = h.n("GeometryNodeInputNamedAttribute", "Read Hit Count", data_type='FLOAT')
h.link(HGI, "Cache Attribute", raw, "Name")
occ = fmath(h, 'DIVIDE', (raw, "Attribute"), (n_safe, "Value"), "Occlusion Fraction")
occ_c = fmath(h, 'MINIMUM', (occ, "Value"), 1.0, "Clamp Fraction")
openness = fmath(h, 'SUBTRACT', 1.0, (occ_c, "Value"), "Openness")
sel_v = switch(h, 'FLOAT', hg_("Selection"), 1.0, (openness, "Value"), "Unselected Reads One")
st_fin = h.n("GeometryNodeStoreNamedAttribute", "Write Occlusion",
             data_type='FLOAT', domain='POINT')
h.link(ro,  "Geometry",        st_fin, "Geometry")
h.link(HGI, "Cache Attribute", st_fin, "Name")
h.link(sel_v, "Output",        st_fin, "Value")
out_f = h.n("GeometryNodeInputNamedAttribute", "Read Occlusion", data_type='FLOAT')
h.link(HGI, "Cache Attribute", out_f, "Name")
h.link(st_fin, "Geometry",  HGO, "Geometry")
h.link(out_f,  "Attribute", HGO, "Ambient Occlusion")
print(f"BUILD: helper {HELP}: {len(hg.nodes)} nodes, {len(hg.links)} links", flush=True)

# ############################################################################# MAIN GROUP
ng = bpy.data.node_groups.new(NAME, "GeometryNodeTree")
t  = Tree(ng)
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

sock("Geometry", 'OUTPUT', 'NodeSocketGeometry',
     desc="The mesh with the occlusion written into the chosen attributes.")
sock("Geometry", 'INPUT', 'NodeSocketGeometry', desc="Mesh to bake occlusion on.")
sock("Selection", 'INPUT', 'NodeSocketBool', default=True,
     desc="Which elements are written. Unselected elements keep whatever the target "
          "attribute already held, so you can bake one region at a time.")

# ---------------------------------------------------------------------------- occlusion
p_occ = iface.new_panel("Occlusion")
sock("Samples", 'INPUT', 'NodeSocketInt', parent=p_occ, default=16, mn=1, mx=256,
     desc="Rays fired per vertex. Cost is linear -- 8 to 16 for look development, 32 to 64 "
          "for a final bake.")
sock("Distance", 'INPUT', 'NodeSocketFloat', parent=p_occ, default=1.0, mn=0.0,
     subtype='DISTANCE',
     desc="How far the rays travel, roughly the radius of the detail you want shaded. "
          "Scale it to your model: large values shade the whole silhouette, small values "
          "only pick out creases.")
sock("Spread", 'INPUT', 'NodeSocketFloat', parent=p_occ, default=1.0, mn=0.0, mx=1.0,
     subtype='FACTOR',
     desc="Width of the sampling cone around the normal. 1 is the full hemisphere, small "
          "values tighten the rays towards the normal for a harder, more directional mask.")
sock("Cosine Weighted", 'INPUT', 'NodeSocketBool', parent=p_occ, default=True,
     desc="Distribute the rays by the cosine of the angle to the normal, matching how a "
          "surface actually gathers light. Off spreads them evenly over the cone.")
sock("Distance Falloff", 'INPUT', 'NodeSocketBool', parent=p_occ, default=True,
     desc="Weight each hit by how close the blocker is, so contact creases darken more than "
          "distant walls. Off counts every hit fully and reads flatter.")
sock("Ray Bias", 'INPUT', 'NodeSocketFloat', parent=p_occ, default=0.001, mn=0.0,
     subtype='DISTANCE',
     desc="How far the ray origin is lifted along the normal, so a ray cannot hit the face "
          "it started from. Raise it if flat surfaces come out speckled.")
sock("Jitter", 'INPUT', 'NodeSocketFloat', parent=p_occ, default=1.0, mn=0.0, mx=1.0,
     subtype='FACTOR',
     desc="Randomly rotates each vertex's sample set around its normal. 1 trades banding for "
          "fine noise that the Blur panel cleans up, 0 gives every vertex the same pattern.")
sock("Seed", 'INPUT', 'NodeSocketInt', parent=p_occ, default=0,
     desc="Drives the jitter rotation. Same seed and same mesh give the same result.")

p_src = iface.new_panel("Occluders", default_closed=True)
iface.move_to_parent(p_src, p_occ, len(p_occ.interface_items))
sock("Self Occlusion", 'INPUT', 'NodeSocketBool', parent=p_src, default=True,
     desc="Let the mesh occlude itself. Turn it off to measure only what the extra "
          "occluders below block.")
sock("Occluder Object", 'INPUT', 'NodeSocketObject', parent=p_src,
     desc="Extra object the rays can hit -- a floor plane, a wall, the body under a piece of "
          "clothing. Its own transform is respected.")
sock("Occluder Collection", 'INPUT', 'NodeSocketCollection', parent=p_src,
     desc="Extra collection of objects the rays can hit. Instances are realized before the "
          "rays are fired, so heavy collections cost real memory.")

# ------------------------------------------------------------------------------- shaping
p_shp = iface.new_panel("Shaping")
sock("Auto Range", 'INPUT', 'NodeSocketBool', parent=p_shp, default=False,
     desc="Measure the darkest and brightest value on the mesh and stretch that span to "
          "0-1, instead of using Input Min / Input Max. Guarantees full contrast, but the "
          "result then depends on the mesh as a whole.")
sock("Input Min", 'INPUT', 'NodeSocketFloat', parent=p_shp, default=0.0, mn=0.0, mx=1.0,
     subtype='FACTOR',
     desc="Occlusion value that maps to black. Raise it to crush the dark end.")
sock("Input Max", 'INPUT', 'NodeSocketFloat', parent=p_shp, default=1.0, mn=0.0, mx=1.0,
     subtype='FACTOR',
     desc="Occlusion value that maps to white. Lower it to blow out the light end.")
sock("Invert", 'INPUT', 'NodeSocketBool', parent=p_shp, default=False,
     desc="Write occlusion instead of openness -- 1 in the creases, 0 on exposed surfaces. "
          "Engines differ on which convention they expect.")
sock("Gamma", 'INPUT', 'NodeSocketFloat', parent=p_shp, default=1.0, mn=0.01, mx=10.0,
     desc="Contrast curve on the 0-1 result. 1 is linear, below 1 lifts the dark end, above "
          "1 deepens the creases.")
sock("Strength", 'INPUT', 'NodeSocketFloat', parent=p_shp, default=1.0, mn=0.0, mx=1.0,
     subtype='FACTOR',
     desc="Blend between white and the shaded result. 0 writes a flat 1, 1 writes the full "
          "effect.")

p_blr = iface.new_panel("Blur", default_closed=True)
sock("Blur Iterations", 'INPUT', 'NodeSocketInt', parent=p_blr, default=0, mn=0, mx=100,
     desc="Smooth the result across neighbouring vertices. 1 to 3 passes clean up the noise "
          "of a low sample count without costing another ray.")
sock("Blur Weight", 'INPUT', 'NodeSocketFloat', parent=p_blr, default=1.0, mn=0.0, mx=1.0,
     subtype='FACTOR',
     desc="How much of each neighbour is mixed in per blur pass.")

# -------------------------------------------------------------------------------- output
p_out = iface.new_panel("Output")
m_tgt = sock("Write To", 'INPUT', 'NodeSocketMenu', parent=p_out,
             desc="Which attribute the result is written to. Colour attributes are what "
                  "FBX carries as vertex colours; a float attribute stays inside Blender.")
m_dom = sock("Domain", 'INPUT', 'NodeSocketMenu', parent=p_out,
             desc="Which mesh domain the attribute lives on. Face Corner lets the value "
                  "break across sharp edges and is what most engines read as vertex colour.")
sock("Colour Attribute", 'INPUT', 'NodeSocketString', parent=p_out, default="AO",
     desc="Name of the colour attribute to write. The value goes into R, G and B with alpha "
          "left at 1, so it reads as a grey mask.")
sock("Float Attribute", 'INPUT', 'NodeSocketString', parent=p_out, default="ao",
     desc="Name of the float attribute to write. Keep it different from the colour "
          "attribute -- one name cannot hold both types.")

TGT_LABELS = ["Colour Attribute", "Float Attribute", "Both"]
TGT_DESCS  = ["Write a colour attribute only -- the vertex-colour route.",
              "Write a float attribute only -- a mask for other geometry nodes.",
              "Write both, under their two separate names."]
DOM_LABELS = ["Face Corner", "Point"]
DOM_DESCS  = ["One value per face corner: the value can break across sharp edges, and this "
              "is what FBX exports as a vertex colour layer.",
              "One value per vertex: smaller, always smooth across edges."]

GI = t.n("NodeGroupInput",  "In")
GO = t.n("NodeGroupOutput", "Out")
def g(name): return (GI, name)

t.f("Extra Occluders")
oi = t.n("GeometryNodeObjectInfo", "Occluder Object", transform_space='RELATIVE')
t.link(GI, "Occluder Object", oi, "Object")
ci = t.n("GeometryNodeCollectionInfo", "Occluder Collection", transform_space='RELATIVE')
t.link(GI, "Occluder Collection", ci, "Collection")
cr = t.n("GeometryNodeRealizeInstances", "Realize Occluder Collection")
t.link(ci, "Instances", cr, "Geometry")
occ_join = t.n("GeometryNodeJoinGeometry", "Join Extra Occluders")
t.link(oi, "Geometry", occ_join, "Geometry")
t.link(cr, "Geometry", occ_join, "Geometry")

t.f("Ambient Occlusion")
gn = t.n("GeometryNodeGroup", "Ambient Occlusion")
gn.node_tree = hg
t.link(GI, "Geometry",  gn, "Geometry")
t.link(occ_join, "Geometry", gn, "Occluders")
t.link(GI, "Selection", gn, "Selection")
t.link(GI, "Samples",   gn, "Samples")
t.link(GI, "Distance",  gn, "Distance")
t.link(GI, "Spread",    gn, "Spread")
t.link(GI, "Cosine Weighted",  gn, "Cosine Weighted")
t.link(GI, "Distance Falloff", gn, "Distance Falloff")
t.link(GI, "Ray Bias",  gn, "Bias")
t.link(GI, "Jitter",    gn, "Jitter")
t.link(GI, "Seed",      gn, "Seed")
t.link(GI, "Self Occlusion", gn, "Self Occlusion")
t.set(gn, "Cache Attribute", A_TMP)

t.f("Shaping")
stat = t.n("GeometryNodeAttributeStatistic", "Measure Range", data_type='FLOAT')
t.link(gn, "Geometry", stat, "Geometry")
t.link(gn, "Ambient Occlusion", stat, "Attribute")
lo = switch(t, 'FLOAT', g("Auto Range"), g("Input Min"), (stat, "Min"), "Pick Input Min")
hi = switch(t, 'FLOAT', g("Auto Range"), g("Input Max"), (stat, "Max"), "Pick Input Max")
lo_e = fmath(t, 'ADD', (lo, "Output"), 1e-5, "Minimum Span")
hi_s = fmath(t, 'MAXIMUM', (hi, "Output"), (lo_e, "Value"), "Guard Empty Range")
mr = t.n("ShaderNodeMapRange", "Remap To 0-1", data_type='FLOAT', clamp=True)
t.link(gn, "Ambient Occlusion", mr, "Value")
t.link(lo,   "Output", mr, "From Min")
t.link(hi_s, "Value",  mr, "From Max")
t.set(mr, "To Min", 0.0)
t.set(mr, "To Max", 1.0)
inv = fmath(t, 'SUBTRACT', 1.0, (mr, "Result"), "Inverted")
v1 = switch(t, 'FLOAT', g("Invert"), (mr, "Result"), (inv, "Value"), "Pick Convention")
v1p = fmath(t, 'MAXIMUM', (v1, "Output"), 0.0, "Guard Negative Base")
gam = fmath(t, 'POWER', (v1p, "Value"), g("Gamma"), "Gamma Curve")
dark = fmath(t, 'SUBTRACT', 1.0, (gam, "Value"), "Darkening")
dark_s = fmath(t, 'MULTIPLY', (dark, "Value"), g("Strength"), "Scaled Darkening")
shaped = fmath(t, 'SUBTRACT', 1.0, (dark_s, "Value"), "Shaped Occlusion")

t.f("Blur")
blur = t.n("GeometryNodeBlurAttribute", "Blur Occlusion")
t.link(shaped, "Value", blur, "Value")
t.link(GI, "Blur Iterations", blur, "Iterations")
t.link(GI, "Blur Weight",     blur, "Weight")
# Blur Attribute is a silent no-op on the face-corner domain -- it only walks point, edge
# and face neighbours. Pin the blur to the point domain and let the store interpolate it
# back out, so the slider does the same thing whichever output domain is picked.
bpt = t.n("GeometryNodeFieldOnDomain", "Blur On Vertices", data_type='FLOAT', domain='POINT')
t.link(blur, "Value", bpt, "Value")

t.f("Write Targets")
tgt = menu_items(t.n("GeometryNodeMenuSwitch", "Target To Index", data_type='INT'),
                 TGT_LABELS, TGT_DESCS)
for i, it in enumerate(tgt.enum_definition.enum_items):
    isock(tgt, f"Item_{i}").default_value = i
t.link(GI, "Write To", tgt, "Menu")
dom = menu_items(t.n("GeometryNodeMenuSwitch", "Domain To Index", data_type='INT'),
                 DOM_LABELS, DOM_DESCS)
for i, it in enumerate(dom.enum_definition.enum_items):
    isock(dom, f"Item_{i}").default_value = i
t.link(GI, "Domain", dom, "Menu")
w_col = t.n("FunctionNodeCompare", "Write Colour", data_type='INT', operation='NOT_EQUAL')
t.link(tgt, "Output", w_col, "A_INT")
isock(w_col, "B_INT").default_value = 1
w_flt = t.n("FunctionNodeCompare", "Write Float", data_type='INT', operation='NOT_EQUAL')
t.link(tgt, "Output", w_flt, "A_INT")
isock(w_flt, "B_INT").default_value = 0
on_pt = t.n("FunctionNodeCompare", "Use Point Domain", data_type='INT', operation='EQUAL')
t.link(dom, "Output", on_pt, "A_INT")
isock(on_pt, "B_INT").default_value = 1
col = t.n("FunctionNodeCombineColor", "Grey From Occlusion", mode='RGB')
for ch in ("Red", "Green", "Blue"):
    t.link(bpt, "Value", col, ch)
t.set(col, "Alpha", 1.0)

geo = (gn, "Geometry")
def write_pair(label, dtype, name_socket, value, cond):
    """Store `value` on both domains, pick one, then gate the whole write."""
    global geo
    stores = {}
    for dom_id, dom_lab in (('CORNER', "Face Corner"), ('POINT', "Point")):
        s = t.n("GeometryNodeStoreNamedAttribute", f"{label} On {dom_lab}",
                data_type=dtype, domain=dom_id)
        t.link(geo[0], geo[1], s, "Geometry")
        t.link(GI, name_socket, s, "Name")
        t.link(GI, "Selection", s, "Selection")
        t.link(value[0], value[1], s, "Value")
        stores[dom_id] = s
    pick = switch(t, 'GEOMETRY', (on_pt, "Result"),
                  (stores['CORNER'], "Geometry"), (stores['POINT'], "Geometry"),
                  f"{label} Domain")
    gate = switch(t, 'GEOMETRY', cond, geo, (pick, "Output"), f"{label} Enabled")
    geo = (gate, "Output")

write_pair("Colour", 'FLOAT_COLOR', "Colour Attribute", (col, "Color"), (w_col, "Result"))
write_pair("Float",  'FLOAT',       "Float Attribute",  (bpt, "Value"), (w_flt, "Result"))

t.f("Strip Cache")
rm = t.n("GeometryNodeRemoveAttribute", "Remove Occlusion Cache")
t.set(rm, "Name", A_TMP)
t.link(geo[0], geo[1], rm, "Geometry")
t.link(rm, "Geometry", GO, "Geometry")

# menu defaults must be the item NAME string, or the socket reads as nothing
m_tgt.default_value = TGT_LABELS[0]
m_dom.default_value = DOM_LABELS[0]
print(f"BUILD: main graph: {len(ng.nodes)} nodes, {len(ng.links)} links", flush=True)

# ============================================================================= PUBLISH
hg.asset_mark(); hg.asset_data.tags.new("ST3E")
hg.asset_data.catalog_id = CAT
hg.is_modifier = False; hg.is_tool = False
hg.asset_data.description = (
    "Raycast ambient occlusion core: fires Samples rays per vertex over the hemisphere and "
    "returns openness as a float field plus the geometry it cached it on. Link this group "
    "into any tree that needs an occlusion mask.")
ng.asset_mark()
ng.asset_data.catalog_id = CAT
ng.asset_data.tags.new("ST3E")
ng.is_modifier = True
ng.is_tool = False
ng.asset_data.description = (
    "Bakes raycast ambient occlusion into a colour attribute (vertex colours), a float "
    "attribute, or both. Samples, distance, cone spread, cosine weighting, distance falloff, "
    "bias and jitter control the sampling; auto range, gamma, invert, strength and a blur "
    "pass shape the result. Extra objects or collections can occlude on top of the mesh "
    "itself.")

# ============================================================================= DEMO
# --factory-startup hands us the startup Cube; it is not part of the asset.
for _o in [o for o in bpy.data.objects if o.type == 'MESH']:
    bpy.data.objects.remove(_o, do_unlink=True)
bpy.ops.mesh.primitive_monkey_add(size=2.0)
demo = bpy.context.object
demo.name = "GN_Demo"
sub = demo.modifiers.new("Subdivision", 'SUBSURF')
sub.levels = 2; sub.render_levels = 2
md = demo.modifiers.new(NAME, 'NODES')
md.node_group = ng

ID = {s.name: s.identifier for s in iface.items_tree if s.item_type == 'SOCKET'}
def setv(name, value):
    md[ID[name]] = value

setv("Samples", 24)
setv("Distance", 1.0)
setv("Gamma", 2.0)
setv("Blur Iterations", 1)
demo.update_tag()

bpy.ops.object.select_all(action='DESELECT')
demo.select_set(True)
bpy.context.view_layer.objects.active = demo

dg = bpy.context.evaluated_depsgraph_get()
ev = demo.evaluated_get(dg).data
vals = [0.0] * len(ev.vertices)
col = ev.color_attributes.get("AO")
print(f"BUILD: demo evaluated -- verts={len(ev.vertices)} "
      f"colors={[c.name for c in ev.color_attributes]} "
      f"attrs={[a for a in ev.attributes.keys() if not a.startswith('.')]}", flush=True)
if col is not None:
    reds = [d.color[0] for d in col.data]
    print(f"BUILD: AO range = {min(reds):.4f} .. {max(reds):.4f} "
          f"(mean {sum(reds)/len(reds):.4f})", flush=True)
leaked = [a for a in ev.attributes.keys() if a.startswith("__ao")]
print(f"BUILD: leaked internal attributes: {leaked}", flush=True)

bpy.ops.wm.save_as_mainfile(filepath=PATH)
print(f"BUILD: saved {PATH}", flush=True)
sys.stdout.flush()
os._exit(0)
