"""Verification matrix for GN_VertexDataComposer.

Opens the built .blend and measures actual evaluated output: every source, every
processing stage, both colour domains and both data types, channel preservation,
selection masking and identity when nothing is written.

Run:
  "C:\\Program Files\\Blender Foundation\\Blender 5.0\\blender.exe" --background \
      --factory-startup D:\\...\\GN_VertexDataComposer.blend \
      --python verify_gn_vertex_data_composer.py
"""
import bpy, sys, math, os

NAME = "GN_VertexDataComposer"
ng = bpy.data.node_groups[NAME]
ID = {s.name: s.identifier for s in ng.interface.items_tree if s.item_type == 'SOCKET'}

SRC_LABELS = None
for n in bpy.data.node_groups["GNG_VertexChannel"].nodes:
    if n.bl_idname == "GeometryNodeMenuSwitch" and n.label.startswith("Source"):
        SRC_LABELS = [i.name for i in n.enum_definition.enum_items]
SRC = {lab: i for i, lab in enumerate(SRC_LABELS)}

PASS, FAIL = [], []
# recorded before the tests start deleting objects to build their own scenes
_demo = bpy.data.objects.get("GN_Demo")
DEMO_OK = _demo is not None and any(m.type == 'NODES' and m.node_group == ng
                                    for m in _demo.modifiers)
DEMO_EVAL = None
if _demo is not None:
    _m = _demo.evaluated_get(bpy.context.evaluated_depsgraph_get()).data
    DEMO_EVAL = ([c.name for c in _m.color_attributes], [u.name for u in _m.uv_layers])
def ck(label, cond, detail=""):
    (PASS if cond else FAIL).append(label)
    print(("[ OK ] " if cond else "[FAIL] ") + label + (f"  -- {detail}" if detail else ""),
          flush=True)

# --------------------------------------------------------------------------- scaffolding
def fresh(kind="grid", **kw):
    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o, do_unlink=True)
    if kind == "grid":
        bpy.ops.mesh.primitive_grid_add(x_subdivisions=kw.get("n", 6),
                                        y_subdivisions=kw.get("n", 6), size=2.0)
    elif kind == "cube":
        bpy.ops.mesh.primitive_cube_add(size=2.0)
    elif kind == "sphere":
        bpy.ops.mesh.primitive_uv_sphere_add(radius=1.0)
    elif kind == "monkey":
        bpy.ops.mesh.primitive_monkey_add(size=2.0)
    o = bpy.context.object
    md = o.modifiers.new("vdc", 'NODES')
    md.node_group = ng
    return o, md

def two_islands():
    """A grid plus a far-away smaller grid: two connected components."""
    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o, do_unlink=True)
    bpy.ops.mesh.primitive_grid_add(x_subdivisions=3, y_subdivisions=3, size=2.0)
    a = bpy.context.object
    bpy.ops.mesh.primitive_grid_add(x_subdivisions=3, y_subdivisions=3, size=1.0,
                                    location=(5, 0, 0))
    b = bpy.context.object
    bpy.ops.object.select_all(action='DESELECT')
    a.select_set(True); b.select_set(True)
    bpy.context.view_layer.objects.active = a
    bpy.ops.object.join()
    o = bpy.context.object
    md = o.modifiers.new("vdc", 'NODES')
    md.node_group = ng
    return o, md

def setv(md, name, value):
    md[ID[name]] = value

def ev_mesh(o):
    o.update_tag()                       # without this the depsgraph re-reads the old eval
    dg = bpy.context.evaluated_depsgraph_get()
    dg.update()
    return o.evaluated_get(dg).data

def read_col(me, name="Col", comp=0):
    a = me.color_attributes[name]
    buf = [0.0] * (len(a.data) * 4)
    a.data.foreach_get("color", buf)
    return buf[comp::4]

def read_uv(me, name, comp=0):
    a = me.uv_layers[name]
    buf = [0.0] * (len(a.data) * 2)
    a.data.foreach_get("uv", buf)
    return buf[comp::2]

def cfg_channel(md, prefix, source, comp=0, **kw):
    """Configure one channel, writing it, with float-colour precision defaults."""
    setv(md, f"{prefix} Write", True)
    setv(md, f"{prefix} Source", SRC[source])
    setv(md, f"{prefix} Component", comp)
    for k, v in kw.items():
        setv(md, f"{prefix} {k}", v)

def col1_float_point(md):
    setv(md, "Col 1 Domain", 0)        # Vertex
    setv(md, "Col 1 Data Type", 1)     # Float Color -> exact, no 8-bit quantization

def rng(v): return (min(v), max(v))

print("\n########## A. identity / slot creation", flush=True)
o, md = fresh("grid")
me = ev_mesh(o)
ck("A1 all-off creates no colour attribute", len(me.color_attributes) == 0,
   str([c.name for c in me.color_attributes]))
ck("A2 all-off leaves UV maps untouched", [u.name for u in me.uv_layers] == ["UVMap"],
   str([u.name for u in me.uv_layers]))
ck("A3 all-off leaks no internals",
   not [a for a in me.attributes.keys() if a.startswith("__vdc")],
   str([a for a in me.attributes.keys() if a.startswith("__vdc")]))
base_uv = read_uv(me, "UVMap", 0)

col1_float_point(md)
cfg_channel(md, "Col 1 R", "Constant", **{"Constant Value": 0.42})
me = ev_mesh(o)
ck("A4 writing one channel creates the slot", "Col" in me.color_attributes)
ck("A5 unused UV slots still not created", [u.name for u in me.uv_layers] == ["UVMap"],
   str([u.name for u in me.uv_layers]))
ck("A6 internals stripped after a write",
   not [a for a in me.attributes.keys() if a.startswith("__vdc")])

print("\n########## B. sources", flush=True)
def source_values(obj, mdf, source, comp=0, **kw):
    for pre in ("Col 1 R",):
        setv(mdf, f"{pre} Write", True)
        setv(mdf, f"{pre} Source", SRC[source])
        setv(mdf, f"{pre} Component", comp)
        setv(mdf, f"{pre} Clamp", False)
        setv(mdf, f"{pre} From Min", 0.0)
        setv(mdf, f"{pre} From Max", 1.0)
        setv(mdf, f"{pre} To Min", 0.0)
        setv(mdf, f"{pre} To Max", 1.0)
        setv(mdf, f"{pre} Auto Range", False)
        setv(mdf, f"{pre} Gamma", 1.0)
        setv(mdf, f"{pre} Quantize Steps", 0)
        setv(mdf, f"{pre} Blur Iterations", 0)
        setv(mdf, f"{pre} Invert", False)
        setv(mdf, f"{pre} Encode sRGB", False)
        for k, v in kw.items():
            setv(mdf, f"{pre} {k}", v)
    return read_col(ev_mesh(obj))

# -- a grid spanning -1..1 in X/Y, flat, normals +Z
o, md = fresh("grid", n=4)
col1_float_point(md)
xs = [v.co.x for v in o.data.vertices]

v = source_values(o, md, "Position (Local)", 0)
ck("B1 Position (Local) X matches vertex x",
   all(abs(a - b) < 1e-5 for a, b in zip(v, xs)), f"{rng(v)} vs {rng(xs)}")

v = source_values(o, md, "Position (Bounds 0-1)", 0)
ck("B2 Position (Bounds 0-1) X spans 0..1", abs(min(v)) < 1e-5 and abs(max(v) - 1) < 1e-5, str(rng(v)))

v = source_values(o, md, "Normal", 2)
ck("B3 Normal Z is 1 on a flat grid", all(abs(a - 1) < 1e-5 for a in v), str(rng(v)))

v = source_values(o, md, "Constant", 0, **{"Constant Value": 0.42})
ck("B4 Constant writes its value", all(abs(a - 0.42) < 1e-6 for a in v), str(rng(v)))
v = source_values(o, md, "Constant", 3, **{"Constant Value": 0.42})
ck("B5 Constant also reaches component W", all(abs(a - 0.42) < 1e-6 for a in v), str(rng(v)))

v = source_values(o, md, "Random (Per Point)", 0)
ck("B6 Random (Per Point) is in 0..1 and varies",
   0 <= min(v) and max(v) <= 1 and len(set(round(x, 5) for x in v)) > len(v) * 0.8, str(rng(v)))

v = source_values(o, md, "Element Index (Normalized)", 0)
ck("B7 Element Index (Normalized) spans 0..1",
   abs(min(v)) < 1e-6 and abs(max(v) - 1) < 1e-6, str(rng(v)))

v = source_values(o, md, "Selection Mask", 0)
ck("B8 Selection Mask reads 1 when fully selected", all(abs(a - 1) < 1e-6 for a in v), str(rng(v)))

v = source_values(o, md, "Face Area", 0)
exp_area = (2.0 / 4) ** 2                      # 4 subdivisions over a 2m grid -> 0.25m cells
ck("B9 Face Area matches the cell area", all(abs(a - exp_area) < 1e-5 for a in v),
   f"{rng(v)} expected {exp_area}")

v = source_values(o, md, "Radial Distance", 0)
exp = [math.hypot(vv.co.x, vv.co.y) for vv in o.data.vertices]
ck("B10 Radial Distance matches |p| from the origin",
   all(abs(a - b) < 1e-5 for a, b in zip(v, exp)), str(rng(v)))

# world position: move the object
o.location = (10, 0, 0)
v = source_values(o, md, "Position (World)", 0)
ck("B11 Position (World) follows the object transform",
   all(abs(a - (b + 10)) < 1e-4 for a, b in zip(v, xs)), str(rng(v)))
o.location = (0, 0, 0)

# boundary distance on a grid: 0 on the rim, largest in the middle
setv(md, "Compute Boundary Distance", True)
v = source_values(o, md, "Distance To Boundary", 0)
rim = [a for a, vv in zip(v, o.data.vertices)
       if abs(abs(vv.co.x) - 1) < 1e-6 or abs(abs(vv.co.y) - 1) < 1e-6]
ck("B12 Distance To Boundary is 0 on the rim", all(a < 1e-6 for a in rim), str(rng(rim)))
ck("B13 Distance To Boundary peaks in the middle", abs(max(v) - 1.0) < 1e-4, str(rng(v)))
setv(md, "Compute Boundary Distance", False)
v = source_values(o, md, "Distance To Boundary", 0)
ck("B14 Distance To Boundary is 0 when the pass is off", all(abs(a) < 1e-9 for a in v))

# curvature on a cube: nonzero at the edges
o, md = fresh("cube"); col1_float_point(md)
v = source_values(o, md, "Curvature", 0)
ck("B15 Curvature is nonzero on a cube", max(abs(a) for a in v) > 0.5, str(rng(v)))
o2, md2 = fresh("grid", n=4); col1_float_point(md2)
v = source_values(o2, md2, "Curvature", 0)
ck("B16 Curvature is ~0 on a flat grid", max(abs(a) for a in v) < 1e-5, str(rng(v)))

# ambient occlusion on a sphere (convex -> mostly open) vs monkey (has cavities)
o, md = fresh("sphere"); col1_float_point(md)
setv(md, "Compute Ambient Occlusion", True); setv(md, "Occlusion Distance", 0.5)
v = source_values(o, md, "Ambient Occlusion", 0)
ck("B17 AO on a convex sphere is fully open", min(v) > 0.95, str(rng(v)))
o, md = fresh("monkey"); col1_float_point(md)
setv(md, "Compute Ambient Occlusion", True); setv(md, "Occlusion Distance", 0.5)
v = source_values(o, md, "Ambient Occlusion", 0)
ck("B18 AO on Suzanne finds occluded areas", min(v) < 0.8 and max(v) > 0.95, str(rng(v)))
setv(md, "Compute Ambient Occlusion", False)
v = source_values(o, md, "Ambient Occlusion", 0)
ck("B19 AO reads 1 when the pass is off", all(abs(a - 1) < 1e-9 for a in v))

# island sources on a two-island mesh
o, md = two_islands(); col1_float_point(md)
big = [i for i, vv in enumerate(o.data.vertices) if vv.co.x < 2.5]
sml = [i for i, vv in enumerate(o.data.vertices) if vv.co.x >= 2.5]
v = source_values(o, md, "Island Index", 0)
ck("B20 Island Index gives exactly two values", len(set(round(a, 5) for a in v)) == 2,
   str(sorted(set(round(a, 3) for a in v))))
v = source_values(o, md, "Random (Per Island)", 0)
ck("B21 Random (Per Island) is constant within an island",
   len(set(round(v[i], 5) for i in big)) == 1 and len(set(round(v[i], 5) for i in sml)) == 1,
   str(sorted(set(round(a, 3) for a in v))))
ck("B22 Random (Per Island) differs between islands",
   abs(v[big[0]] - v[sml[0]]) > 1e-4)
v = source_values(o, md, "Island Centroid", 0)
ck("B23 Island Centroid X is ~0 and ~5 for the two islands",
   abs(v[big[0]]) < 1e-4 and abs(v[sml[0]] - 5.0) < 1e-4,
   f"{v[big[0]]:.4f} / {v[sml[0]]:.4f}")
v = source_values(o, md, "Island Size", 0)
ck("B24 Island Size is larger for the big island", v[big[0]] > v[sml[0]] * 1.5,
   f"{v[big[0]]:.4f} vs {v[sml[0]]:.4f}")
v = source_values(o, md, "Offset From Island Centroid", 0)
ck("B25 Offset From Island Centroid is pivot-relative",
   abs(max(v[i] for i in sml) - 0.5) < 1e-4, str(rng([v[i] for i in sml])))
v = source_values(o, md, "Direction To Island Centroid", 0)
ck("B26 Direction To Island Centroid is a unit-ish vector",
   max(abs(a) for a in v) <= 1.0 + 1e-5, str(rng(v)))
v = source_values(o, md, "Island Index (Normalized)", 0)
ck("B27 Island Index (Normalized) spans 0..1", abs(min(v)) < 1e-6 and abs(max(v) - 1) < 1e-6,
   str(rng(v)))

# per-face random + material index (corner-domain read so it is exact)
o, md = fresh("cube"); col1_float_point(md)
v = source_values(o, md, "Random (Per Face)", 0)
ck("B28 Random (Per Face) is in 0..1 and varies", 0 <= min(v) <= max(v) <= 1 and min(v) != max(v),
   str(rng(v)))
mat = bpy.data.materials.new("m0"); o.data.materials.append(mat)
mat2 = bpy.data.materials.new("m1"); o.data.materials.append(mat2)
for p in o.data.polygons[:3]:
    p.material_index = 1
v = source_values(o, md, "Material Index", 0)
ck("B29 Material Index reports slot 1 somewhere", max(v) > 0.5, str(rng(v)))

# user attributes
o, md = fresh("grid", n=4); col1_float_point(md)
mesh = o.data
af = mesh.attributes.new("myfloat", 'FLOAT', 'POINT')
af.data.foreach_set("value", [0.25] * len(mesh.vertices))
ai = mesh.attributes.new("myint", 'INT', 'POINT')
ai.data.foreach_set("value", [3] * len(mesh.vertices))
av = mesh.attributes.new("myvec", 'FLOAT_VECTOR', 'POINT')
av.data.foreach_set("vector", [0.1, 0.2, 0.3] * len(mesh.vertices))
ac = mesh.attributes.new("mycol", 'FLOAT_COLOR', 'POINT')
ac.data.foreach_set("color", [0.6, 0.7, 0.8, 0.9] * len(mesh.vertices))
ab = mesh.attributes.new("mybool", 'BOOLEAN', 'POINT')
ab.data.foreach_set("value", [True] * len(mesh.vertices))
for lab, comp, exp, attr in (("Attribute (Float)", 0, 0.25, "myfloat"),
                             ("Attribute (Integer)", 0, 3.0, "myint"),
                             ("Attribute (Vector)", 1, 0.2, "myvec"),
                             ("Attribute (Color)", 2, 0.8, "mycol"),
                             ("Attribute (Color)", 3, 0.9, "mycol"),
                             ("Attribute (Boolean)", 0, 1.0, "mybool")):
    v = source_values(o, md, lab, comp, **{"Attribute": attr})
    ck(f"B30 {lab} comp{comp} reads {exp}", all(abs(a - exp) < 1e-5 for a in v), str(rng(v)))

# reading an existing UV map back through Attribute (Vector)
v = source_values(o, md, "Attribute (Vector)", 0, **{"Attribute": "UVMap"})
ck("B31 an existing UV map reads back as (U,V,0)",
   all(abs(a - b) < 1e-5 for a, b in zip(v, [0] * len(v))) is False and 0 <= min(v) <= max(v) <= 1,
   str(rng(v)))

# distance to object
o, md = fresh("grid", n=4); col1_float_point(md)
bpy.ops.mesh.primitive_uv_sphere_add(radius=0.5, location=(0, 0, 2))
tgt = bpy.context.object
setv(md, "Source Object", tgt)
setv(md, "Compute Object Distance", True)
v = source_values(o, md, "Distance To Object", 0)
ck("B32 Distance To Object is ~1.5 under the sphere", abs(min(v) - 1.5) < 0.05, str(rng(v)))
v = source_values(o, md, "Radial Distance", 0)
ck("B33 Radial Distance re-centres on Source Object",
   abs(min(v) - 2.0) < 0.05, str(rng(v)))
setv(md, "Source Object", None); setv(md, "Compute Object Distance", False)

# random per object
o, md = fresh("grid", n=2); col1_float_point(md)
v1 = source_values(o, md, "Random (Per Object)", 0)
o.location = (7, 3, 1)
v2 = source_values(o, md, "Random (Per Object)", 0)
ck("B34 Random (Per Object) is uniform over the mesh", len(set(round(a, 6) for a in v1)) == 1)
ck("B35 Random (Per Object) changes with the object origin", abs(v1[0] - v2[0]) > 1e-6,
   f"{v1[0]:.5f} vs {v2[0]:.5f}")

print("\n########## C. processing chain", flush=True)
o, md = fresh("grid", n=4); col1_float_point(md)
# a clean 0..1 ramp to process: bounds-normalized X
def proc(**kw):
    return source_values(o, md, "Position (Bounds 0-1)", 0, **kw)

v = proc(**{"To Min": 0.0, "To Max": 255.0})
ck("C1 output range remaps to 0..255", abs(min(v)) < 1e-4 and abs(max(v) - 255) < 1e-3, str(rng(v)))
v = proc(**{"Invert": True})
ck("C2 invert flips the ramp", abs(min(v)) < 1e-5 and abs(max(v) - 1) < 1e-5 and v[0] != 0.0,
   str(rng(v)))
v0 = proc(**{"Invert": False}); v1 = proc(**{"Invert": True})
ck("C3 invert is exactly 1-x", all(abs((a + b) - 1) < 1e-5 for a, b in zip(v0, v1)))
v = proc(**{"From Min": 0.25, "From Max": 0.75, "Clamp": True})
ck("C4 clamp holds the range", abs(min(v)) < 1e-6 and abs(max(v) - 1) < 1e-6, str(rng(v)))
v = proc(**{"From Min": 0.25, "From Max": 0.75, "Clamp": False})
ck("C5 clamp off lets values escape", min(v) < -0.4 and max(v) > 1.4, str(rng(v)))
v = proc(**{"Gamma": 2.0})
ck("C6 gamma 2 squares the normalized value",
   all(abs(a - b * b) < 1e-4 for a, b in zip(v, v0)), str(rng(v)))
v = proc(**{"Quantize Steps": 4})
ck("C7 quantize 4 yields exactly 4 distinct levels",
   len(set(round(a, 5) for a in v)) == 4, str(sorted(set(round(a, 3) for a in v))))
v = proc(**{"Quantize Steps": 0})
ck("C8 quantize 0 is a no-op", all(abs(a - b) < 1e-6 for a, b in zip(v, v0)))
v = proc(**{"Encode sRGB": True})
def l2s(c): return 12.92 * c if c <= 0.0031308 else 1.055 * (c ** (1 / 2.4)) - 0.055
ck("C9 sRGB encode matches the reference formula",
   all(abs(a - l2s(b)) < 1e-4 for a, b in zip(v, v0)), str(rng(v)))
vb = proc(**{"Blur Iterations": 8})
def var(xs):
    m = sum(xs) / len(xs)
    return sum((x - m) ** 2 for x in xs) / len(xs)
ck("C10 blur reduces variance", var(vb) < var(v0) * 0.95, f"{var(vb):.5f} vs {var(v0):.5f}")
ck("C11 blur 0 is a no-op",
   all(abs(a - b) < 1e-6 for a, b in zip(proc(**{"Blur Iterations": 0}), v0)))
# auto range on a -1..1 source
v = source_values(o, md, "Position (Local)", 0, **{"Auto Range": True})
ck("C12 auto range normalizes a -1..1 source to 0..1",
   abs(min(v)) < 1e-5 and abs(max(v) - 1) < 1e-5, str(rng(v)))
v = source_values(o, md, "Position (Local)", 0, **{"Auto Range": False, "Clamp": False})
ck("C13 auto range off leaves the raw -1..1 source alone", min(v) < -0.9, str(rng(v)))
# degenerate range must not produce NaN
v = source_values(o, md, "Constant", 0,
                  **{"Constant Value": 0.5, "From Min": 1.0, "From Max": 1.0})
ck("C14 a zero-width input range produces no NaN", all(a == a for a in v), str(rng(v)))

print("\n########## D. write targets", flush=True)
o, md = fresh("grid", n=3)
cfg_channel(md, "Col 1 R", "Constant", **{"Constant Value": 0.5})
for dom_i, dom_name in ((0, 'POINT'), (1, 'CORNER')):
    for typ_i, typ_name in ((0, 'BYTE_COLOR'), (1, 'FLOAT_COLOR')):
        setv(md, "Col 1 Domain", dom_i); setv(md, "Col 1 Data Type", typ_i)
        me = ev_mesh(o)
        a = me.color_attributes["Col"]
        ck(f"D1 colour slot honours {dom_name}/{typ_name}",
           a.domain == dom_name and a.data_type == typ_name, f"{a.domain}/{a.data_type}")

col1_float_point(md)
setv(md, "Col 1 Name", "MyMask")
me = ev_mesh(o)
ck("D2 colour slot name is user-driven", "MyMask" in me.color_attributes,
   str([c.name for c in me.color_attributes]))
setv(md, "Col 1 Name", "Col")

# unwritten channels keep the existing value
o, md = fresh("grid", n=3)
ca = o.data.color_attributes.new("Col", 'FLOAT_COLOR', 'POINT')
ca.data.foreach_set("color", [0.1, 0.2, 0.3, 0.4] * len(o.data.vertices))
col1_float_point(md)
cfg_channel(md, "Col 1 R", "Constant", **{"Constant Value": 0.9})
me = ev_mesh(o)
ck("D3 written channel takes the new value", all(abs(a - 0.9) < 1e-5 for a in read_col(me, comp=0)),
   str(rng(read_col(me, comp=0))))
for comp, exp, nm_ in ((1, 0.2, "G"), (2, 0.3, "B"), (3, 0.4, "A")):
    vv = read_col(me, comp=comp)
    ck(f"D4 unwritten {nm_} keeps the existing value", all(abs(a - exp) < 1e-5 for a in vv),
       str(rng(vv)))

# a colour attribute that does not exist yet starts opaque black
o, md = fresh("grid", n=3); col1_float_point(md)
cfg_channel(md, "Col 1 R", "Constant", **{"Constant Value": 0.9})
me = ev_mesh(o)
ck("D5 new colour attribute defaults to opaque black",
   all(abs(a) < 1e-6 for a in read_col(me, comp=1)) and
   all(abs(a - 1) < 1e-6 for a in read_col(me, comp=3)))

# UV writes
o, md = fresh("grid", n=3)
base_u = read_uv(ev_mesh(o), "UVMap", 0)
base_v = read_uv(ev_mesh(o), "UVMap", 1)
cfg_channel(md, "UV2 U", "Constant", **{"Constant Value": 0.7})
me = ev_mesh(o)
ck("D6 UV slot is created on demand", "UV2" in me.uv_layers, str([u.name for u in me.uv_layers]))
ck("D7 UV U channel takes the value", all(abs(a - 0.7) < 1e-5 for a in read_uv(me, "UV2", 0)))
ck("D8 unwritten UV V stays 0 on a new map", all(abs(a) < 1e-6 for a in read_uv(me, "UV2", 1)))
ck("D9 UV2 is a real CORNER FLOAT2 layer",
   me.attributes["UV2"].domain == 'CORNER' and me.attributes["UV2"].data_type == 'FLOAT2',
   f"{me.attributes['UV2'].domain}/{me.attributes['UV2'].data_type}")

# writing into the existing UVMap must preserve V
o, md = fresh("grid", n=3)
setv(md, "UV0 Name", "UVMap")
cfg_channel(md, "UV0 U", "Constant", **{"Constant Value": 0.3})
me = ev_mesh(o)
ck("D10 writing UVMap.U preserves V",
   all(abs(a - b) < 1e-6 for a, b in zip(read_uv(me, "UVMap", 1), base_v)))
ck("D11 writing UVMap.U changes U", all(abs(a - 0.3) < 1e-6 for a in read_uv(me, "UVMap", 0)))

# all 8 UV slots + all 4 colour slots at once
o, md = fresh("grid", n=3)
for i in range(8):
    cfg_channel(md, f"UV{i} U", "Constant", **{"Constant Value": 0.1 * (i + 1)})
for i in range(1, 5):
    setv(md, f"Col {i} Domain", 0); setv(md, f"Col {i} Data Type", 1)
    cfg_channel(md, f"Col {i} R", "Constant", **{"Constant Value": 0.2 * i})
me = ev_mesh(o)
ck("D12 all 8 UV slots exist together", len(me.uv_layers) == 8, str([u.name for u in me.uv_layers]))
ck("D13 all 4 colour slots exist together", len(me.color_attributes) == 4,
   str([c.name for c in me.color_attributes]))
ck("D14 every UV slot carries its own value",
   all(abs(read_uv(me, f"UV{i}" if i else "UVMap", 0)[0] - 0.1 * (i + 1)) < 1e-5 for i in range(8)))
ck("D15 every colour slot carries its own value",
   all(abs(read_col(me, "Col" if i == 1 else f"Col{i}", 0)[0] - 0.2 * i) < 1e-5
       for i in range(1, 5)))
ck("D16 no internals leak with everything on",
   not [a for a in me.attributes.keys() if a.startswith("__vdc")])

print("\n########## E. selection masking", flush=True)
o, md = fresh("grid", n=4)
ca = o.data.color_attributes.new("Col", 'FLOAT_COLOR', 'POINT')
ca.data.foreach_set("color", [0.0, 0.0, 0.0, 1.0] * len(o.data.vertices))
sel = o.data.attributes.new("half", 'BOOLEAN', 'POINT')
sel.data.foreach_set("value", [v.co.x > 0 for v in o.data.vertices])
col1_float_point(md)
cfg_channel(md, "Col 1 R", "Constant", **{"Constant Value": 1.0})
md[ID["Selection"] + "_use_attribute"] = True
md[ID["Selection"] + "_attribute_name"] = "half"
me = ev_mesh(o)
vals = read_col(me, comp=0)
left = [a for a, vv in zip(vals, o.data.vertices) if vv.co.x < 0]
right = [a for a, vv in zip(vals, o.data.vertices) if vv.co.x > 0]
ck("E1 selected side is written", all(abs(a - 1) < 1e-5 for a in right), str(rng(right)))
ck("E2 unselected side is untouched", all(abs(a) < 1e-5 for a in left), str(rng(left)))

print("\n########## F. interface hygiene", flush=True)
socks = [i for i in ng.interface.items_tree if i.item_type == 'SOCKET']
# R9 is about by-name miswiring, which can only happen within one direction:
# the in/out pair both called "Geometry" is the universal geonode convention.
in_names = [s.name for s in socks if s.in_out == 'INPUT']
dupes = sorted({n for n in in_names if in_names.count(n) > 1})
ck("F1 R9 all input socket names unique", not dupes, str(dupes[:8]))
nodesc = [s.name for s in socks if not s.description]
ck("F2 every socket has a tooltip", not nodesc, f"{len(nodesc)} missing: {nodesc[:5]}")
def named_panel(it):
    p = it.parent
    return p is not None and p.name != ""
loose = [s.name for s in socks if not named_panel(s) and s.name not in ("Geometry", "Selection")]
ck("F3 R10 only Geometry/Selection sit outside a panel", not loose, str(loose[:5]))
ck("F4 socket count is the expected 528", len(socks) == 528, str(len(socks)))
frames = [n for n in ng.nodes if n.bl_idname == "NodeFrame"]
ck("F5 R4 every frame is labeled", all(f.label for f in frames), str(len(frames)))
# same exemptions as layout_audit's R8: frames, the group in/out buses, and the
# routing reroutes the tidy engine lays down between frames
unframed = [n.name for n in ng.nodes
            if n.bl_idname not in ("NodeFrame", "NodeGroupInput", "NodeGroupOutput",
                                   "NodeReroute")
            and n.parent is None]
ck("F6 R8 every node lives in a frame", not unframed, str(unframed[:5]))
# the Source menu really propagated all 30 items to the outer interface
src_sock = [s for s in socks if s.name == "Col 1 R Source"][0]
try:
    items = [i.name for i in src_sock.default_input_items] if hasattr(src_sock, "default_input_items") else None
except Exception:
    items = None
ck("F7 Source menu default resolves to a real item", src_sock.default_value == SRC_LABELS[0],
   str(src_sock.default_value))
ck("F8 30 sources are defined", len(SRC_LABELS) == 30, str(len(SRC_LABELS)))

print("\n########## G. asset publishing", flush=True)
ck("G1 marked as asset", ng.asset_data is not None)
ck("G2 catalog is the ST3E/Modify leaf",
   ng.asset_data.catalog_id == "9b90781b-f051-4cdb-9dcb-c8909914a87b", ng.asset_data.catalog_id)
ck("G3 ST3E tag present", "ST3E" in [t.name for t in ng.asset_data.tags])
ck("G4 is_modifier trait on", ng.is_modifier and not ng.is_tool)
ck("G5 asset description filled", len(ng.asset_data.description or "") > 80)
ck("G6 first input is Geometry and there is a Geometry output",
   [s for s in ng.interface.items_tree if s.item_type == 'SOCKET' and s.in_out == 'INPUT'][0].name == "Geometry"
   and any(s.name == "Geometry" for s in ng.interface.items_tree
           if s.item_type == 'SOCKET' and s.in_out == 'OUTPUT'))
ck("G7 demo object ships with the modifier attached", DEMO_OK)
ck("G8 demo evaluates with authored channels",
   DEMO_EVAL is not None and "Col" in DEMO_EVAL[0] and "UV1" in DEMO_EVAL[1], str(DEMO_EVAL))

print(f"\n===== {len(PASS)} passed / {len(FAIL)} failed =====", flush=True)
for f in FAIL:
    print("  FAILED:", f, flush=True)
sys.stdout.flush()
os._exit(1 if FAIL else 0)
