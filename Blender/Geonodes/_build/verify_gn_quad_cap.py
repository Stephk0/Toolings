"""Verify GN_QuadCap.blend: caps close every loop, only quads (+1 tri per odd loop),
winding consistent with the surrounding faces, filters + options behave.

  blender.exe --background --factory-startup <GN_QuadCap.blend> --python verify_gn_quad_cap.py
"""
import bpy, bmesh, sys, os, math
from collections import Counter
from mathutils import Matrix

NAME = "GN_QuadCap"
ng = bpy.data.node_groups[NAME]
obj = bpy.data.objects["GN_Demo"]
md = obj.modifiers[NAME]
ids = {it.name: it.identifier for it in ng.interface.items_tree
       if it.item_type == 'SOCKET' and it.in_out == 'INPUT'}
cap_out = next(it.identifier for it in ng.interface.items_tree
               if it.item_type == 'SOCKET' and it.in_out == 'OUTPUT' and it.name == "Cap")
md[cap_out + "_attribute_name"] = "cap"
DEFAULTS = {k: md[v] for k, v in ids.items() if v in md.keys()}

fails = []
def check(label, ok, info=""):
    print(("PASS " if ok else "FAIL ") + label + ("  " + str(info) if info else ""))
    if not ok: fails.append(label)

def evaluate(o=obj, **over):
    m = o.modifiers[NAME]
    for k, v in DEFAULTS.items(): m[ids[k]] = v
    for k, v in over.items(): m[ids[k]] = v
    o.update_tag(); bpy.context.view_layer.update()
    ev = o.evaluated_get(bpy.context.evaluated_depsgraph_get())
    me = ev.to_mesh()
    bm = bmesh.new(); bm.from_mesh(me)
    capl = bm.faces.layers.bool.get("cap")
    ev.to_mesh_clear()
    return bm, capl

src = obj.data
src_faces = len(src.polygons)

# ---- 1. defaults: every loop capped, all-quad except 1 tri per odd loop ----------
bm, capl = evaluate()
border = [e for e in bm.edges if len(e.link_faces) < 2]
check("no open border left", len(border) == 0, len(border))
check("all edges manifold", all(len(e.link_faces) == 2 for e in bm.edges))
check("winding consistent (every edge contiguous)", all(e.is_contiguous for e in bm.edges),
      sum(not e.is_contiguous for e in bm.edges))
check("cap attribute present", capl is not None)
caps = [f for f in bm.faces if f[capl]]
hist = Counter(len(f.verts) for f in caps)
# tube16: 2 x (4x4) ; tube13: 2 x (3x4, one tri) ; sphere hole 24: 6x6
check("cap face count", len(caps) == 2 * 16 + 2 * 12 + 36, (len(caps), dict(hist)))
check("caps are quads + exactly 2 tris (two odd loops)", hist.get(3, 0) == 2
      and set(hist) <= {3, 4}, dict(hist))
check("original faces kept", len(bm.faces) - len(caps) == src_faces)
nan = any(any(math.isnan(c) for c in v.co) for v in bm.verts)
check("no NaN", not nan)
# normals point away from each island's centre (outward)
def outward_ratio(bm, faces):
    good = 0
    for f in faces:
        ctr = f.calc_center_median()
        # island centre: tubes at x=-2.2/0, sphere at 2.2
        ic = min((-2.2, 0.0, 2.2), key=lambda x: abs(x - ctr.x))
        good += f.normal.dot(ctr - type(ctr)((ic, 0, 0))) > 0
    return good / max(1, len(faces))
check("caps face outward", outward_ratio(bm, caps) == 1.0, outward_ratio(bm, caps))
bm.free()

# ---- 2. selection off / inverted -> identity -------------------------------------
bm, _ = evaluate(**{"Selection": False})
check("Selection off = untouched", len(bm.faces) == src_faces and len(bm.verts) == len(src.vertices))
bm.free()
bm, _ = evaluate(**{"Invert Selection": True})
check("Invert Selection (all selected) = untouched", len(bm.faces) == src_faces)
bm.free()

# ---- 3. size filter ----------------------------------------------------------------
bm, capl = evaluate(**{"Max Border Vertices": 16})
nc = sum(1 for f in bm.faces if f[capl])
check("Max Border Vertices 16 skips the 24-loop", nc == 2 * 16 + 2 * 12, nc)
bm.free()

# ---- 4. side balance / corner offset ---------------------------------------------------
bm, capl = evaluate(**{"Side Balance": 1})
nc = sum(1 for f in bm.faces if f[capl])
# tube16 5x3 =15 ; tube13 (N'14) 4x3 = 12 ; sphere 7x5 = 35
check("Side Balance +1 reshapes grids", nc == 2 * 15 + 2 * 12 + 35, nc)
check("Side Balance keeps it closed + consistent",
      all(len(e.link_faces) == 2 and e.is_contiguous for e in bm.edges))
bm.free()
bm, capl = evaluate(**{"Corner Offset": 3})
check("Corner Offset keeps it closed + consistent",
      all(len(e.link_faces) == 2 and e.is_contiguous for e in bm.edges))
bm.free()

# ---- 5. relax + dome ------------------------------------------------------------------
bm, capl = evaluate(**{"Relax Iterations": 10, "Dome": 1.0})
check("relax+dome closed + consistent",
      all(len(e.link_faces) == 2 and e.is_contiguous for e in bm.edges))
check("relax+dome no NaN", not any(any(math.isnan(c) for c in v.co) for v in bm.verts))
top = max(v.co.z for v in bm.verts if abs(v.co.x + 2.2) < 1.0)
check("dome bulges tube end outward", top > 0.8 + 0.3, round(top, 3))
bm.free()
bm, capl = evaluate(**{"Dome": 1.0})
ring = sorted(v.co.z for v in bm.verts if abs(v.co.x + 2.2) < 1.0 and v.co.z > 0.8001)
# 4x4 grid: 9 interior verts all lifted, and the 8 around the centre by > 30% of the peak
check("dome lifts every interior vert (not a spike)", len(ring) == 9
      and ring[0] - 0.8 > 0.3 * (ring[-1] - 0.8), [round(z, 3) for z in ring])
bm.free()
bm, capl = evaluate(**{"Dome": 0.0})
top0 = max(v.co.z for v in bm.verts if abs(v.co.x + 2.2) < 1.0)
check("dome 0 = flat cap", abs(top0 - 0.8) < 1e-5, top0)
bm.free()

# ---- 6. merge off / flip ------------------------------------------------------------------
bm, capl = evaluate(**{"Merge With Mesh": False})
check("merge off leaves caps separate", len([e for e in bm.edges if len(e.link_faces) < 2]) > 0)
bm.free()
bm, capl = evaluate(**{"Flip Cap Normals": True})
caps = [f for f in bm.faces if f[capl]]
check("flip reverses caps", outward_ratio(bm, caps) == 0.0)
bm.free()

# ---- 7. loose edge loop ------------------------------------------------------------------
me = bpy.data.meshes.new("_loose"); b2 = bmesh.new()
bmesh.ops.create_circle(b2, cap_ends=False, segments=12, radius=1.0)
b2.to_mesh(me); b2.free()
lo = bpy.data.objects.new("_loose", me); bpy.context.scene.collection.objects.link(lo)
lm = lo.modifiers.new(NAME, "NODES"); lm.node_group = ng; lm[cap_out + "_attribute_name"] = "cap"
bm, capl = evaluate(lo)
check("loose 12-loop capped with 3x3 quads", len(bm.faces) == 9
      and all(len(f.verts) == 4 for f in bm.faces), len(bm.faces))
bm.free()
bm, capl = evaluate(lo, **{"Cap Loose Edge Loops": False})
check("loose loops off", len(bm.faces) == 0)
bm.free()

# ---- 8. plane with a square hole: outer rim + hole, filter keeps the rim open -------------
me = bpy.data.meshes.new("_holed"); b3 = bmesh.new()
bmesh.ops.create_grid(b3, x_segments=6, y_segments=6, size=1.0)
mid = [f for f in b3.faces if abs(f.calc_center_median().x) < 0.4 and abs(f.calc_center_median().y) < 0.4]
bmesh.ops.delete(b3, geom=mid, context='FACES')
b3.to_mesh(me); b3.free()
ho = bpy.data.objects.new("_holed", me); bpy.context.scene.collection.objects.link(ho)
hm = ho.modifiers.new(NAME, "NODES"); hm.node_group = ng; hm[cap_out + "_attribute_name"] = "cap"
bm, capl = evaluate(ho, **{"Max Border Vertices": 12})
nc = sum(1 for f in bm.faces if f[capl])
check("hole in plane capped (8-loop -> 2x2), rim open", nc == 4, nc)
check("hole cap welded (1 new vert, only the 24-rim open)", len(bm.verts) == 49
      and sum(1 for e in bm.edges if len(e.link_faces) < 2) == 24, len(bm.verts))
check("hole cap contiguous", all(e.is_contiguous for e in bm.edges if len(e.link_faces) == 2))
cn = [f.normal.z for f in bm.faces if f[capl]]
check("hole cap faces same way as plane", all(z > 0.99 for z in cn), cn)
bm.free()

bpy.data.objects.remove(lo); bpy.data.objects.remove(ho)
print("\nRESULT:", "ALL PASS" if not fails else f"{len(fails)} FAIL: {fails}")
sys.stdout.flush()
os._exit(0 if not fails else 1)
