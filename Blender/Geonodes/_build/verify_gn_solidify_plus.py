"""Verify GN_SolidifyPlus.blend headless.

  1. Parity: element counts, crease / bevel edge counts and vertex-crease handling
     against reference numbers recorded from the third-party "Solidify Plus (Vert
     Crease Fix)" group GN_SolidifyPlus replaces (it matched them case for case, and
     the example character's jacket, backpack, pants and zipper buckle to <= 0.2 mm,
     when it was built -- the original is not in the repo, so its numbers are baked in).
  2. Profile curve: rim layer placement for both profile modes.
  3. Selection gate truth table, Grow 0 passthrough, no NaN anywhere.

  "C:\\Program Files\\Blender Foundation\\Blender 5.0\\blender.exe" --background \
      --factory-startup --python verify_gn_solidify_plus.py
Exit code 1 on any failure.
"""
from collections import Counter
import bpy, bmesh, os, sys, math

GEO = r"D:\Stephko_Tooling\Toolings\Blender\Geonodes"
NAME = "GN_SolidifyPlus"

with bpy.data.libraries.load(os.path.join(GEO, NAME + ".blend"), link=False) as (src, dst):
    dst.node_groups = [NAME]
NG = bpy.data.node_groups[NAME]
IDS = {it.name: it.identifier for it in NG.interface.items_tree
       if it.item_type == 'SOCKET' and it.in_out == 'INPUT'}

# mesh, params, attribute bindings, (V, E, F), creased edges, bevelled edges, crease_vert kept
PARITY = {
    "default":       ('grid', {}, {}, (50, 96, 48), 0, 0, True),
    "offset_-1":     ('grid', {"Thickness": 0.2, "Offset": -1.0}, {}, (50, 96, 48), 0, 0, True),
    "negative_T":    ('grid', {"Thickness": -0.2}, {}, (50, 96, 48), 0, 0, True),
    "rim_loops_2":   ('grid', {"Rim Loops": 2}, {}, (82, 160, 80), 0, 0, True),
    "no_fill":       ('grid', {"Fill Rim": False}, {}, (50, 80, 32), 0, 0, True),
    "only_rim":      ('grid', {"Only Rim": True}, {}, (41, 72, 32), 0, 0, True),
    "crease_all":    ('grid', {"Inner Crease": 0.5, "Outer Crease": 0.6, "Rim Loop Crease": 0.7,
                               "Rim Crease": 0.8, "Rim Loops": 1}, {}, (66, 128, 64), 56, 0, True),
    "bevel_all":     ('grid', {"Inner Bevel Weight": 0.5, "Outer Bevel Weight": 0.6,
                               "Rim Loop Bevel Weight": 0.7, "Rim Bevel Weight": 0.8,
                               "Rim Loops": 1}, {}, (66, 128, 64), 0, 56, True),
    "rim_convex":    ('L', {"Rim Crease": 1.0, "Rim Crease By": 2}, {}, (30, 56, 28), 5, 0, True),
    "rim_concave":   ('L', {"Rim Crease": 1.0, "Rim Crease By": 3}, {}, (30, 56, 28), 1, 0, True),
    "rim_vcrease":   ('L', {"Rim Crease": 1.0, "Rim Crease By": 5}, {}, (30, 56, 28), 3, 0, False),
    "rim_vc_keep":   ('L', {"Rim Crease": 1.0, "Rim Crease By": 5, "Keep Vertex Crease": True},
                      {}, (30, 56, 28), 3, 0, True),
    "rim_all_loops": ('L', {"Rim Crease": 1.0, "Rim Crease By": 0, "Rim Loops": 1}, {},
                      (42, 80, 40), 24, 0, True),
    "tube_loops":    ('tube', {"Rim Loops": 3, "Rim Loop Crease": 0.5}, {}, (80, 160, 80), 48, 0, True),
    "closed_cube":   ('cube', {}, {}, (16, 24, 12), 0, 0, True),
    "selection":     ('gridsel', {}, {"Selection": "sel"}, (45, 78, 36), 0, 0, True),
    "sel_invert":    ('gridsel', {"Invert Selection": True}, {"Selection": "sel"}, (45, 78, 36), 0, 0, True),
    "weight_missing": ('grid', {}, {"Thickness Weight": "nope"}, (50, 96, 48), 0, 0, True),
    "materials":     ('grid', {"Offset": -1.0, "Shell Material Offset": 1, "Rim Material Offset": 2},
                      {}, (50, 96, 48), 0, 0, True),
}

FAILS = []
def check(cond, msg):
    print(("  ok   " if cond else "  FAIL ") + msg)
    if not cond: FAILS.append(msg)


def make_mesh(kind):
    bm = bmesh.new()
    if kind == 'grid':
        bmesh.ops.create_grid(bm, x_segments=4, y_segments=4, size=1.0)
        for v in bm.verts: v.co.z = 0.15 * v.co.x ** 2
    elif kind in ('gridsel', 'flat'):
        bmesh.ops.create_grid(bm, x_segments=4, y_segments=4, size=1.0)
    elif kind == 'L':
        bmesh.ops.create_grid(bm, x_segments=3, y_segments=3, size=1.0)
        bmesh.ops.delete(bm, geom=[f for f in bm.faces if f.calc_center_median().x > 0.2
                                   and f.calc_center_median().y > 0.2], context='FACES')
    elif kind == 'tube':
        bmesh.ops.create_cone(bm, cap_ends=False, segments=8, radius1=1, radius2=1, depth=1)
    elif kind == 'cube':
        bmesh.ops.create_cube(bm, size=2)
    me = bpy.data.meshes.new(kind); bm.to_mesh(me); bm.free()
    cv = me.attributes.new('crease_vert', 'FLOAT', 'POINT')
    for v in me.vertices:
        if abs(abs(v.co.x) - 1) < 1e-4 and abs(abs(v.co.y) - 1) < 1e-4:
            cv.data[v.index].value = 1.0
    sel = me.attributes.new('sel', 'BOOLEAN', 'FACE')
    nsel = me.attributes.new('nsel', 'BOOLEAN', 'FACE')
    for p in me.polygons:
        sel.data[p.index].value = p.center.x < 0.1
        nsel.data[p.index].value = not (p.center.x < 0.1)
    ob = bpy.data.objects.new(kind, me); bpy.context.scene.collection.objects.link(ob)
    return ob


def run(kind, params, attrs=None, extra=None):
    ob = make_mesh(kind)
    md = ob.modifiers.new(NAME, 'NODES'); md.node_group = NG
    for k, v in params.items(): md[IDS[k]] = v
    for k, v in (attrs or {}).items():
        md[IDS[k] + '_use_attribute'] = True; md[IDS[k] + '_attribute_name'] = v
    if extra: extra(md)
    dg = bpy.context.evaluated_depsgraph_get(); ob.update_tag(); dg.update()
    me = bpy.data.meshes.new_from_object(ob.evaluated_get(dg), preserve_all_data_layers=True,
                                         depsgraph=dg)
    bpy.data.objects.remove(ob)
    return me


def positive(me, name):
    at = me.attributes.get(name)
    return sum(1 for d in at.data if d.value > 1e-6) if at else 0


def no_nan(me):
    return all(all(math.isfinite(c) for c in v.co) for v in me.vertices)


print("== parity with Solidify Plus (Vert Crease Fix)")
for case, (kind, params, attrs, counts, ncr, nbw, keepvc) in PARITY.items():
    me = run(kind, params, attrs)
    got = (len(me.vertices), len(me.edges), len(me.polygons))
    check(got == counts and positive(me, 'crease_edge') == ncr
          and positive(me, 'bevel_weight_edge') == nbw
          and bool(me.attributes.get('crease_vert')) == keepvc and no_nan(me),
          f"{case}: counts {got}/{counts}, crease {positive(me, 'crease_edge')}/{ncr}, "
          f"bevel {positive(me, 'bevel_weight_edge')}/{nbw}, crease_vert kept "
          f"{bool(me.attributes.get('crease_vert'))}/{keepvc}")

print("== profile curve")
def profile(points):
    cu = bpy.data.curves.new('profile', 'CURVE'); sp = cu.splines.new('POLY')
    sp.points.add(len(points) - 1)
    for p, (x, y) in zip(sp.points, points): p.co = (x, y, 0, 1)
    ob = bpy.data.objects.new('profile', cu); bpy.context.scene.collection.objects.link(ob)
    return ob

# a tent: half the thickness out at mid-height. Flat 2x2 sheet, T 0.1: the middle rim
# loop sits 0.05 outside the border, the others 0.025.
tent = profile([(0, 0), (0.5, 0.5), (0, 1)])
me = run('flat', {"Rim Loops": 3},
         extra=lambda md: md.__setitem__(IDS["Profile Curve"], tent))
xmax = max(v.co.x for v in me.vertices)
check(abs(xmax - 1.05) < 1e-4, f"tent profile pushes the middle loop out by T/2 (max x {xmax:.4f})")
mid = [v for v in me.vertices if abs(v.co.z - 0.05) < 1e-4 and abs(v.co.y) < 0.4]
check(mid and all(abs(abs(v.co.x) - 1.05) < 1e-4 for v in mid),
      "middle loop at half thickness, offset straight out")

# Profile Sets Rim Loops: 5 points -> 3 rim loops, layer k on point k
steps = profile([(0, 0), (0.2, 0.1), (0.2, 0.5), (0.2, 0.9), (0, 1)])
me = run('flat', {"Profile Sets Rim Loops": True, "Rim Loops": 7},
         extra=lambda md: md.__setitem__(IDS["Profile Curve"], steps))
check(len(me.vertices) == 25 * 2 + 16 * 3,
      f"5-point profile sets 3 rim loops (verts {len(me.vertices)} / {25 * 2 + 16 * 3})")
zs = sorted({round(v.co.z, 4) for v in me.vertices})
check(zs == [0.0, 0.01, 0.05, 0.09, 0.1], f"rim loops on the profile points' heights {zs}")
check(abs(max(v.co.x for v in me.vertices) - 1.02) < 1e-4, "profile x scaled to thickness")

print("== selection gate")
def sig(me): return sorted((round(v.co.x, 5), round(v.co.y, 5), round(v.co.z, 5)) for v in me.vertices)
a = run('gridsel', {"Invert Selection": False}, {"Selection": "sel"})
b = run('gridsel', {"Invert Selection": True}, {"Selection": "nsel"})
c = run('gridsel', {"Invert Selection": True}, {"Selection": "sel"})
d = run('gridsel', {"Invert Selection": False}, {"Selection": "nsel"})
check(sig(a) == sig(b), "(Sel, Inv 0) == (not Sel, Inv 1)")
check(sig(c) == sig(d), "(Sel, Inv 1) == (not Sel, Inv 0)")
e = run('grid', {"Grow / Shrink Selection": 0})
f = run('grid', {})
check(sig(e) == sig(f), "Grow / Shrink 0 is a passthrough")
z = run('grid', {"Thickness": 0.0, "Rim Loops": 2, "Push": 0.1, "Even Thickness": True})
check(no_nan(z), "zero thickness: no NaN")

print("== material index")
def mats(set_mode):
    def base_mat(md):
        me = md.id_data.data
        for i in range(4): me.materials.append(bpy.data.materials.new(f"M{i}"))
        for p in me.polygons: p.material_index = 1
    me = run('grid', {"Shell Material Offset": 1, "Rim Material Offset": 2,
                      "Set Material Index": set_mode}, extra=base_mat)
    return sorted(Counter(p.material_index for p in me.polygons).items())
check(mats(False) == [(1, 16), (2, 16), (3, 16)], f"offset mode adds {mats(False)}")
check(mats(True) == [(1, 32), (2, 16)], f"Set Material Index sets {mats(True)}")

print("== sharp edges")
def n_sharp(me):
    at = me.attributes.get("sharp_edge")
    return sum(1 for d in at.data if d.value) if at else None
check(n_sharp(run('flat', {})) is None, "defaults add no sharp_edge attribute")
check(n_sharp(run('flat', {"Outer Sharp": True})) == 16, "Outer Sharp marks the 16 border edges")
check(n_sharp(run('flat', {"Rim Sharp": True, "Rim Sharp By": 0})) == 16,
      "Rim Sharp (All) marks the 16 rim edges")

# flat 2 x 2 m grid, UV = xy / 2 + 0.5 (0.5 UV per metre), shell 0.1 behind the surface
def with_uv(md):
    me = md.id_data.data
    uv = me.uv_layers.new(name="UVMap")
    for lp in me.loops:
        co = me.vertices[lp.vertex_index].co
        uv.data[lp.index].uv = (co.x * 0.5 + 0.5, co.y * 0.5 + 0.5)
SHELL = {"Thickness": 0.1, "Offset": -1.0}

def rim_corners(me):
    out = []
    uv = me.uv_layers["UVMap"].data
    for p in me.polygons:
        if abs(p.normal.z) < 0.5:
            for li in p.loop_indices:
                out.append((me.vertices[me.loops[li].vertex_index].co.copy(), uv[li].uv.copy(), p))
    return out

print("== rim UVs")
me = run('flat', dict(SHELL, **{"Rim UVs": 1}), extra=with_uv)
rc = rim_corners(me)
outside = lambda u: max(u.x - 1, -u.x, u.y - 1, -u.y, 0.0)
check(len(rc) == 64 and all(abs(outside(u) - (-co.z) * 0.5) < 1e-4 for co, u, _ in rc),
      "Expand: rim continues the island outward at its texel density (0.05 UV for 0.1 m)")
me = run('flat', dict(SHELL, **{"Rim UVs": 1, "Expand Offset": 0.02}), extra=with_uv)
check(all(abs(outside(u) - ((-co.z) * 0.5 + 0.02)) < 1e-4 for co, u, _ in rim_corners(me)),
      "Expand Offset leaves a 0.02 UV gap")
me = run('flat', dict(SHELL, **{"Rim UVs": 2}), extra=with_uv)
rc = rim_corners(me)
spans = {}
for co, u, p in rc:
    spans.setdefault(p.index, []).append(u.x)
check(all(abs(u.y - (-co.z)) < 1e-4 for co, u, _ in rc)
      and min(u.x for _, u, _ in rc) > -1e-4 and max(u.x for _, u, _ in rc) < 8 + 1e-4
      and all(abs(max(s) - min(s) - 0.5) < 1e-4 for s in spans.values()),
      "Strip: U = border length (0..8 m, 0.5 per face, closing face wrapped), V = depth")

print("== fix normals")
def shell_dev(me):
    worst = 0.0
    for p in me.polygons:
        if abs(p.normal.z) > 0.5:
            for li in p.loop_indices:
                worst = max(worst, 1 - me.corner_normals[li].vector.dot(p.normal))
    return worst
def smooth(md):
    for p in md.id_data.data.polygons: p.use_smooth = True
check(shell_dev(run('flat', SHELL, extra=smooth)) > 1e-3,
      "smooth shaded, without Fix Normals the rim bends the shell border")
me = run('flat', dict(SHELL, **{"Fix Normals": True}), extra=smooth)
rim_ok = all(abs(me.corner_normals[li].vector.z) < 1e-4
             for p in me.polygons if abs(p.normal.z) < 0.5 for li in p.loop_indices)
check(shell_dev(me) < 1e-5 and rim_ok, "Fix Normals: flat shells, rim shaded on its own")

print("== trim")
me = run('flat', {"Add Trim": True, "Trim Radius": 0.05})
base = run('flat', {})
check(len(me.polygons) > len(base.polygons) and no_nan(me), "Add Trim joins a trim")
TRIM_OUT = next(it.identifier for it in NG.interface.items_tree
                if it.item_type == 'SOCKET' and it.in_out == 'OUTPUT' and it.name == "Trim")
def trim_z(weight):
    def prep(md):
        me_ = md.id_data.data
        at = me_.attributes.new("w", 'FLOAT', 'POINT')
        for d_ in at.data: d_.value = weight
        md[TRIM_OUT + "_attribute_name"] = "trim"
    me = run('flat', dict(SHELL, **{"Add Trim": True, "Trim Radius": 0.01}),
             {"Thickness Weight": "w"}, extra=prep)
    at = me.attributes["trim"]
    vs = {v for p in me.polygons if at.data[p.index].value for v in p.vertices}
    return sum(me.vertices[v].co.z for v in vs) / len(vs)
z1, z5 = trim_z(1.0), trim_z(0.5)
check(abs(z1 + 0.05) < 2e-3 and abs(z5 + 0.025) < 2e-3,
      f"trim mid-rim follows the thickness weight (z {z1:.4f} at 1, {z5:.4f} at 0.5)")

print(f"\n{len(FAILS)} failure(s)")
sys.stdout.flush()
os._exit(1 if FAILS else 0)
