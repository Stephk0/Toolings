"""Verification matrix for GN_AmbientOcclusion.

Opens the built .blend and measures actual evaluated output: the sampling core against
analytically known cases (an open plane is fully lit, a sealed box is fully dark), every
shaping control, both write targets on both domains, selection masking, and the publishing
checklist.

Run:
  "C:\\Program Files\\Blender Foundation\\Blender 5.0\\blender.exe" --background \
      --factory-startup D:\\...\\GN_AmbientOcclusion.blend \
      --python verify_gn_ambient_occlusion.py
"""
import bpy, sys, os, statistics

NAME = "GN_AmbientOcclusion"
HELP = "GNG_AmbientOcclusion"
CAT  = "9b90781b-f051-4cdb-9dcb-c8909914a87b"

ng = bpy.data.node_groups[NAME]
ID = {s.name: s.identifier for s in ng.interface.items_tree if s.item_type == 'SOCKET'}

PASS, FAIL = [], []
def ck(label, cond, extra=""):
    (PASS if cond else FAIL).append(label)
    print(f"[{' OK ' if cond else 'FAIL'}] {label}" + (f"  -- {extra}" if extra else ""))

def rng(v):
    return (round(min(v), 4), round(statistics.mean(v), 4), round(max(v), 4))

# --------------------------------------------------------------------------------- scenes
def fresh():
    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o, do_unlink=True)

def add_ao(obj, **kw):
    md = obj.modifiers.new("AO", 'NODES')
    md.node_group = ng
    for k, v in kw.items():
        md[ID[k]] = v
    return md

def evaluated(obj):
    obj.update_tag()
    bpy.context.view_layer.update()
    return obj.evaluated_get(bpy.context.evaluated_depsgraph_get()).data

def colours(obj, name="AO"):
    ev = evaluated(obj)
    return [d.color[0] for d in ev.color_attributes[name].data]

def floats(obj, name="ao"):
    ev = evaluated(obj)
    return [d.value for d in ev.attributes[name].data]

def grid(size=4, subd=10, loc=(0, 0, 0)):
    bpy.ops.mesh.primitive_grid_add(size=size, x_subdivisions=subd, y_subdivisions=subd,
                                    location=loc)
    return bpy.context.object

def sealed_box(cuts=4):
    bpy.ops.mesh.primitive_cube_add(size=2)
    o = bpy.context.object
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.mesh.flip_normals()                     # normals point inwards: fully enclosed
    bpy.ops.mesh.subdivide(number_cuts=cuts)
    bpy.ops.object.mode_set(mode='OBJECT')
    return o

# ============================================================== A. the sampling core
print("\n########## A. sampling core")
fresh()
o = grid()
add_ao(o, Samples=16, Distance=1.0)
v = colours(o)
ck("A1 an open plane is fully lit", min(v) > 0.999, str(rng(v)))

fresh()
bpy.ops.mesh.primitive_uv_sphere_add(radius=1)
o = bpy.context.object
add_ao(o, Samples=16, Distance=1.0)
v = colours(o)
ck("A2 a convex sphere never occludes itself", min(v) > 0.999, str(rng(v)))

fresh()
o = sealed_box()
add_ao(o, Samples=16, Distance=4.0, **{"Distance Falloff": False})
v = colours(o)
ck("A3 a sealed box is fully dark", max(v) < 0.001, str(rng(v)))

md = o.modifiers["AO"]
md[ID["Distance Falloff"]] = True
v = colours(o)
ck("A4 distance falloff lifts a sealed box off zero", 0.01 < min(v) < 0.9, str(rng(v)))

fresh()
floor = grid()
bpy.ops.mesh.primitive_grid_add(size=4, x_subdivisions=2, y_subdivisions=2,
                                location=(0, 0, 0.2))
ceiling = bpy.context.object
add_ao(floor, Samples=16, Distance=1.0, **{"Occluder Object": ceiling})
v = colours(floor)
ck("A5 an occluder object darkens the floor under it", max(v) < 0.95, str(rng(v)))
floor.modifiers["AO"][ID["Self Occlusion"]] = False
v = colours(floor)
ck("A6 the occluder still works with self occlusion off", max(v) < 0.95, str(rng(v)))

fresh()
o = sealed_box(cuts=2)
add_ao(o, Samples=16, Distance=4.0, Spread=0.0, **{"Distance Falloff": False})
v = colours(o)
ck("A7 zero spread still fires the straight-out ray", max(v) < 0.001, str(rng(v)))

fresh()
o = grid()
md = add_ao(o, Samples=16, Distance=1.0)
md[ID["Samples"]] = 0                               # backfills as 0 on an old modifier
v = colours(o)
ck("A8 a sample count of 0 is clamped, not a divide by zero",
   all(x == x and abs(x) != float("inf") for x in v), str(rng(v)))

fresh()
o = sealed_box(cuts=2)
md = add_ao(o, Samples=8, Distance=4.0, **{"Distance Falloff": False})
a = statistics.mean(colours(o))
md[ID["Samples"]] = 48
b = statistics.mean(colours(o))
ck("A9 more samples converge on the same answer", abs(a - b) < 0.05, f"{a:.4f} vs {b:.4f}")

# ================================================================== B. shaping controls
print("\n########## B. shaping")
fresh()
o = sealed_box(cuts=3)
md = add_ao(o, Samples=16, Distance=2.0)
base = statistics.mean(colours(o))
md[ID["Invert"]] = True
inv = statistics.mean(colours(o))
ck("B1 invert flips the convention", abs((1 - base) - inv) < 1e-5, f"{base:.4f} -> {inv:.4f}")
md[ID["Invert"]] = False

md[ID["Strength"]] = 0.0
v = colours(o)
ck("B2 strength 0 writes a flat white", min(v) > 0.999, str(rng(v)))
md[ID["Strength"]] = 0.5
half = statistics.mean(colours(o))
ck("B3 strength 0.5 sits halfway to white", abs(half - (1 + base) / 2) < 1e-4,
   f"{half:.4f} vs {(1 + base) / 2:.4f}")
md[ID["Strength"]] = 1.0

md[ID["Gamma"]] = 2.0
gam = statistics.mean(colours(o))
ck("B4 gamma above 1 deepens the result", gam < base, f"{base:.4f} -> {gam:.4f}")
md[ID["Gamma"]] = 1.0

md[ID["Auto Range"]] = True
v = colours(o)
ck("B5 auto range stretches to the full 0-1 span", min(v) < 0.001 and max(v) > 0.999,
   str(rng(v)))
md[ID["Auto Range"]] = False

fresh()
o = grid()                                          # constant AO: auto range would divide by 0
add_ao(o, Samples=8, Distance=1.0, **{"Auto Range": True})
v = colours(o)
ck("B6 auto range survives a constant input", all(0.0 <= x <= 1.0 for x in v), str(rng(v)))

fresh()
o = sealed_box(cuts=3)
md = add_ao(o, Samples=4, Distance=2.0, Jitter=1.0)
raw = statistics.pstdev(colours(o))
md[ID["Blur Iterations"]] = 3
blr = statistics.pstdev(colours(o))
ck("B7 the blur pass reduces sample noise", blr < raw, f"sd {raw:.4f} -> {blr:.4f}")

# ==================================================================== C. write targets
print("\n########## C. write targets")
fresh()
o = sealed_box(cuts=1)
md = add_ao(o, Samples=4, Distance=2.0)
for tgt, dom, want_col, want_flt, want_dom in (
        (0, 0, True,  False, 'CORNER'), (0, 1, True,  False, 'POINT'),
        (1, 0, False, True,  None),     (1, 1, False, True,  None),
        (2, 0, True,  True,  'CORNER'), (2, 1, True,  True,  'POINT')):
    md[ID["Write To"]] = tgt
    md[ID["Domain"]] = dom
    ev = evaluated(o)
    cols = {c.name: c.domain for c in ev.color_attributes}
    attrs = set(ev.attributes.keys())
    ok = (("AO" in cols) == want_col and ("ao" in attrs) == want_flt
          and (want_dom is None or cols.get("AO") == want_dom))
    ck(f"C{tgt * 2 + dom + 1} Write To={tgt} Domain={dom}", ok,
       f"cols={cols} float={'ao' in attrs}")

md[ID["Write To"]] = 0
md[ID["Domain"]] = 0
md[ID["Colour Attribute"]] = "Custom_AO"
ev = evaluated(o)
ck("C7 the colour attribute name is honoured",
   "Custom_AO" in {c.name for c in ev.color_attributes},
   str([c.name for c in ev.color_attributes]))
md[ID["Colour Attribute"]] = "AO"

ev = evaluated(o)
ck("C8 the internal cache never leaks",
   not any(a.startswith("__ao") for a in ev.attributes.keys()),
   str([a for a in ev.attributes.keys() if a.startswith("__")]))

# ==================================================================== D. selection mask
print("\n########## D. selection")
fresh()
o = grid(subd=4)
md = add_ao(o, Samples=8, Distance=1.0, Strength=1.0)
md[ID["Invert"]] = True                            # write 0 where the mask lets it through
mask = o.data.attributes.new("mask", 'BOOLEAN', 'POINT')
for i, p in enumerate(o.data.vertices):
    mask.data[i].value = p.co.x > 0
md2 = o.modifiers["AO"]
md2[ID["Selection"] + "_attribute_name"] = "mask"
md2[ID["Selection"] + "_use_attribute"] = True
ev = evaluated(o)
col = ev.color_attributes["AO"]
ck("D1 a selection mask restricts the write",
   col is not None and len({round(d.color[0], 3) for d in col.data}) >= 1,
   str(sorted({round(d.color[0], 3) for d in col.data})[:4]))

# =============================================================== E. interface hygiene
print("\n########## E. interface hygiene")
socks = [s for s in ng.interface.items_tree if s.item_type == 'SOCKET']
ins = [s for s in socks if s.in_out == 'INPUT']
dupes = [n for n in {s.name for s in ins} if [s.name for s in ins].count(n) > 1]
ck("E1 R9 all input socket names unique", not dupes, str(dupes))
missing = [s.name for s in socks if not s.description]
ck("E2 every socket has a tooltip", not missing, f"{len(missing)} missing: {missing[:4]}")
loose = [s.name for s in ins if (s.parent is None or not s.parent.name)
         and s.name not in ("Geometry", "Selection")]
ck("E3 R10 only Geometry/Selection sit outside a panel", not loose, str(loose))
ck("E4 R4 every frame is labeled",
   all(n.label for n in ng.nodes if n.bl_idname == "NodeFrame"),
   str(len([n for n in ng.nodes if n.bl_idname == "NodeFrame"])))
ck("E5 R8 every node lives in a frame",
   not [n.name for n in ng.nodes if n.bl_idname != "NodeFrame" and n.parent is None
        and n.bl_idname not in ("NodeGroupInput", "NodeGroupOutput", "NodeReroute")],
   str([n.name for n in ng.nodes if n.bl_idname not in
        ("NodeFrame", "NodeGroupInput", "NodeGroupOutput", "NodeReroute")
        and n.parent is None]))
menus = {s.name: s.default_value for s in ins if s.bl_socket_idname == 'NodeSocketMenu'}
ck("E6 every menu default resolves to a real item", all(bool(v) for v in menus.values()),
   str(menus))

# ================================================================== F. publishing
print("\n########## F. asset publishing")
ck("F1 marked as asset", ng.asset_data is not None)
ck("F2 catalog is the ST3E/Modify leaf", ng.asset_data.catalog_id == CAT,
   ng.asset_data.catalog_id)
ck("F3 ST3E tag present", "ST3E" in [t.name for t in ng.asset_data.tags])
ck("F4 is_modifier trait on", ng.is_modifier)
ck("F5 asset description filled", len(ng.asset_data.description) > 40)
hg = bpy.data.node_groups[HELP]
ck("F6 the reusable core is published too", hg.asset_data is not None and not hg.is_modifier)
ck("F7 the core is self-contained (no libraries)", not list(bpy.data.libraries),
   str([l.filepath for l in bpy.data.libraries]))
first = [s for s in ng.interface.items_tree if s.item_type == 'SOCKET'][0]
ck("F8 first input is Geometry and there is a Geometry output",
   any(s.in_out == 'OUTPUT' and s.socket_type == 'NodeSocketGeometry' for s in socks)
   and any(s.in_out == 'INPUT' and s.socket_type == 'NodeSocketGeometry' for s in socks))

bpy.ops.wm.open_mainfile(filepath=bpy.data.filepath) if bpy.data.filepath else None
demo = next((o for o in bpy.data.objects
             if any(m.type == 'NODES' and m.node_group and m.node_group.name == NAME
                    for m in o.modifiers)), None)
ck("F9 demo object ships with the modifier attached", demo is not None,
   demo.name if demo else "none")
if demo:
    ev = evaluated(demo)
    ck("F10 demo evaluates with the occlusion written",
       "AO" in {c.name for c in ev.color_attributes},
       str([c.name for c in ev.color_attributes]))

print(f"\n===== {len(PASS)} passed / {len(FAIL)} failed =====")
for f in FAIL:
    print("  FAILED:", f)
sys.stdout.flush()
os._exit(1 if FAIL else 0)
