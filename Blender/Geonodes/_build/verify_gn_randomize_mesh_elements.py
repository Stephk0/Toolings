"""Verify GN_RandomizeMeshElements.blend headlessly.

  "C:\\Program Files\\Blender Foundation\\Blender 5.0\\blender.exe" --background \
      --factory-startup --python verify_gn_randomize_mesh_elements.py

Checks: neutral identity, per-element rigidity (a cube's verts stay equidistant from
its own centre under rotate/uniform-scale/mirror), grouping modes, affect chance,
seed response, mirror winding repair, pivot modes and NaN-freedom.
"""
import bpy, sys, os, math
from mathutils import Vector

PATH = r"D:\Stephko_Tooling\Toolings\Blender\Geonodes\GN_RandomizeMeshElements.blend"

bpy.ops.wm.open_mainfile(filepath=PATH)
obj = bpy.data.objects["GN_Demo"]
md  = obj.modifiers[0]
ng  = md.node_group
ID  = {it.name: it.identifier for it in ng.interface.items_tree
       if getattr(it, "item_type", "") == 'SOCKET' and it.in_out == 'INPUT'}

SRC = [v.co.copy() for v in obj.data.vertices]

DEFAULTS = {
    "Group By": 0, "Group Attribute": "group_id", "Seed": 0, "Affect Chance": 1.0,
    "Position Amount": [0.1, 0.1, 0.1],
    "Rotation Amount": [0.0, 0.0, math.radians(15.0)],
    "Uniform Scale": True, "Scale Min": 0.9, "Scale Max": 1.1,
    "Flip X Chance": 0.0, "Flip Y Chance": 0.0, "Flip Z Chance": 0.0,
    "Flip Faces On Mirror": True, "Pivot Point": 0,
}

def apply(**over):
    p = dict(DEFAULTS); p.update(over)
    for k, v in p.items():
        md[ID[k]] = v
    obj.update_tag()
    dg = bpy.context.evaluated_depsgraph_get(); dg.update()
    ev = obj.evaluated_get(dg)
    m = ev.to_mesh()
    verts = [v.co.copy() for v in m.vertices]
    edges = [tuple(e.vertices) for e in m.edges]
    polys = [(list(p.vertices), p.normal.copy(), p.center.copy()) for p in m.polygons]
    ev.to_mesh_clear()
    return verts, edges, polys

def islands(nv, edges):
    par = list(range(nv))
    def find(a):
        while par[a] != a: par[a] = par[par[a]]; a = par[a]
        return a
    for a, b in edges:
        ra, rb = find(a), find(b)
        if ra != rb: par[ra] = rb
    groups = {}
    for i in range(nv): groups.setdefault(find(i), []).append(i)
    return list(groups.values())

def has_nan(vs):
    return any(math.isnan(c) or math.isinf(c) for v in vs for c in v)

RES = []
def check(name, ok, info=""):
    RES.append((name, bool(ok), info))
    print(("  PASS  " if ok else "  FAIL  ") + name + ("   " + info if info else ""))

print("== interface ==")
print("   inputs:", len(ID), "| nodes:", len(ng.nodes))

# --------------------------------------------------------------- 1. neutral identity
v, e, p = apply(**{"Position Amount": [0, 0, 0], "Rotation Amount": [0, 0, 0],
                   "Scale Min": 1.0, "Scale Max": 1.0})
check("neutral: vertex count unchanged", len(v) == len(SRC), f"{len(v)} vs {len(SRC)}")
dmax = max((a - b).length for a, b in zip(v, SRC)) if len(v) == len(SRC) else 9e9
check("neutral: positions identical", dmax < 1e-6, f"max delta {dmax:.3e}")

# --------------------------------------------------------------- 2. defaults / rigidity
v, e, p = apply()
isl = islands(len(v), e)
check("default: 16 islands (cubes stay whole)", len(isl) == 16, f"{len(isl)}")
check("default: no NaN", not has_nan(v))
moved = max((a - b).length for a, b in zip(v, SRC))
check("default: geometry actually randomized", moved > 1e-3, f"max move {moved:.4f}")

def rigidity(verts, isl):
    """A cube's 8 corners are equidistant from its centre; rotation, uniform scale and
    mirroring all preserve that. Worst-case spread over all islands."""
    worst = 0.0
    for g in isl:
        c = sum((verts[i] for i in g), Vector()) / len(g)
        ds = [(verts[i] - c).length for i in g]
        worst = max(worst, (max(ds) - min(ds)) / max(max(ds), 1e-9))
        globals()['_last_r'] = None
    return worst
r = rigidity(v, isl)
check("default: each element rigid (uniform scale + rotation)", r < 1e-5, f"spread {r:.2e}")

cent = [sum((v[i] for i in g), Vector()) / len(g) for g in isl]
src_isl = islands(len(SRC), [tuple(ed.vertices) for ed in obj.data.edges])
src_cent = [sum((SRC[i] for i in g), Vector()) / len(g) for g in src_isl]
# pair each source element with its nearest evaluated element (elements move well
# under half the 1.0 grid spacing, so the pairing is unambiguous)
off = [min((c - s for c in cent), key=lambda d: d.length) for s in src_cent]
check("default: offsets within Position Amount",
      all(abs(o.x) <= 0.1001 and abs(o.y) <= 0.1001 and abs(o.z) <= 0.1001 for o in off),
      f"max |offset| {max(max(abs(o.x),abs(o.y),abs(o.z)) for o in off):.4f}")
check("default: elements offset differently (not one rigid block)",
      max((off[0] - o).length for o in off) > 1e-3)

# --------------------------------------------------------------- 3. seed response
v2, _, _ = apply(Seed=7)
diff = max((a - b).length for a, b in zip(v, v2))
check("seed change gives a different pattern", diff > 1e-3, f"max delta {diff:.4f}")

# --------------------------------------------------------------- 4. affect chance
v0, _, _ = apply(**{"Affect Chance": 0.0})
d0 = max((a - b).length for a, b in zip(v0, SRC))
check("Affect Chance 0 = identity", d0 < 1e-6, f"max delta {d0:.3e}")

vh, eh, _ = apply(**{"Affect Chance": 0.5})
ih = islands(len(vh), eh)
untouched = sum(1 for g in ih
                if max((vh[i] - SRC[i]).length for i in g) < 1e-6)
check("Affect Chance 0.5 leaves some elements untouched",
      0 < untouched < 16, f"{untouched}/16 untouched")

# --------------------------------------------------------------- 5. grouping = Face
v, e, p = apply(**{"Group By": 1})
isl = islands(len(v), e)
check("Group By Face: every face separated", len(isl) == 96 and len(v) == 96 * 4,
      f"{len(isl)} islands / {len(v)} verts")
check("Group By Face: no NaN", not has_nan(v))
r = rigidity(v, isl)
check("Group By Face: faces stay square (rigid)", r < 1e-5, f"spread {r:.2e}")

# --------------------------------------------------------------- 6. grouping = Material
me2 = obj.data
for i, mat in enumerate(("MatA", "MatB")):
    m = bpy.data.materials.get(mat) or bpy.data.materials.new(mat)
    me2.materials.append(m)
for i, poly in enumerate(me2.polygons):
    poly.material_index = i % 2
v, e, p = apply(**{"Group By": 2})
isl = islands(len(v), e)
check("Group By Material: mesh split into material groups",
      len(v) > len(SRC) and not has_nan(v), f"{len(v)} verts / {len(isl)} islands")

# --------------------------------------------------------------- 7. grouping = Attribute
at = me2.attributes.new(name="group_id", type='INT', domain='FACE')
for i in range(len(me2.polygons)):
    at.data[i].value = i // 24          # 4 groups of 6 faces (per row of cubes)
v, e, p = apply(**{"Group By": 3})
isl = islands(len(v), e)
check("Group By Attribute: groups move as one",
      len(isl) >= 4 and not has_nan(v), f"{len(isl)} islands")
grp_off = {}
for g in isl:
    c = sum((v[i] for i in g), Vector()) / len(g)
    grp_off[round(c.z, 4)] = grp_off.get(round(c.z, 4), 0) + 1
check("Group By Attribute: fewer groups than faces", len(isl) < 96, f"{len(isl)} < 96")
me2.attributes.remove(me2.attributes["group_id"])
me2.materials.clear()

# --------------------------------------------------------------- 8. mirroring / winding
def outwardness(verts, edges, polys):
    isl = islands(len(verts), edges)
    owner = {}
    for k, g in enumerate(isl):
        for i in g: owner[i] = k
    cents = [sum((verts[i] for i in g), Vector()) / len(g) for g in isl]
    dots = []
    for pv, nrm, ctr in polys:
        c = cents[owner[pv[0]]]
        dots.append(nrm.dot((ctr - c).normalized()))
    return min(dots)

v, e, p = apply(**{"Flip X Chance": 1.0, "Position Amount": [0, 0, 0],
                   "Rotation Amount": [0, 0, 0], "Scale Min": 1.0, "Scale Max": 1.0})
check("mirror + Flip Faces On Mirror: normals stay outward",
      outwardness(v, e, p) > 0.99, f"min dot {outwardness(v, e, p):.3f}")
v, e, p = apply(**{"Flip X Chance": 1.0, "Flip Faces On Mirror": False,
                   "Position Amount": [0, 0, 0], "Rotation Amount": [0, 0, 0],
                   "Scale Min": 1.0, "Scale Max": 1.0})
check("mirror without the repair: normals inverted",
      outwardness(v, e, p) < -0.99, f"min dot {outwardness(v, e, p):.3f}")
v, e, p = apply(**{"Flip Y Chance": 0.5, "Flip Z Chance": 0.5})
check("partial flips: no NaN, still 16 elements",
      not has_nan(v) and len(islands(len(v), e)) == 16)

# --------------------------------------------------------------- 9. pivot = Object Origin
v, e, p = apply(**{"Pivot Point": 1, "Position Amount": [0, 0, 0],
                   "Scale Min": 1.0, "Scale Max": 1.0,
                   "Rotation Amount": [0, 0, math.radians(30)]})
isl = islands(len(v), e)
cent = sorted([sum((v[i] for i in g), Vector()) / len(g) for g in isl],
              key=lambda c: round(c.length, 4))
src_c = sorted(src_cent, key=lambda c: round(c.length, 4))
dr = max(abs(a.length - b.length) for a, b in zip(cent, src_c))
check("Pivot Object Origin: elements orbit the origin (radius kept)", dr < 1e-4,
      f"max radius delta {dr:.2e}")
swing = max((a - b).length for a, b in zip(cent, src_c))
check("Pivot Object Origin: elements actually swung", swing > 1e-3, f"{swing:.4f}")

# --------------------------------------------------------------- 10. non-uniform scale
v, e, p = apply(**{"Uniform Scale": False, "Scale Min": 0.5, "Scale Max": 1.5,
                   "Rotation Amount": [0, 0, 0]})
isl = islands(len(v), e)
ratios = []
for g in isl:
    xs = [v[i].x for i in g]; ys = [v[i].y for i in g]; zs = [v[i].z for i in g]
    ratios.append((max(xs) - min(xs)) / max(max(ys) - min(ys), 1e-9))
check("non-uniform scale stretches elements per axis",
      max(ratios) - min(ratios) > 0.1 and not has_nan(v),
      f"aspect spread {max(ratios) - min(ratios):.3f}")

# --------------------------------------------------------------- 11. selection field off
v, e, p = apply(**{})
check("no NaN anywhere in the matrix", not has_nan(v))

# --------------------------------------------------------------- 12. asset metadata
ad = ng.asset_data
check("asset: marked + ST3E tag + modifier trait",
      ad is not None and "ST3E" in [t.name for t in ad.tags] and ng.is_modifier
      and not ng.is_tool)
check("asset: catalog = ST3E/Deform",
      ad.catalog_id == "bacd112a-8e87-47c2-afbc-818a11c75c08", ad.catalog_id)
missing = [it.name for it in ng.interface.items_tree
           if getattr(it, "item_type", "") == 'SOCKET' and not it.description]
check("asset: every socket documented", not missing, str(missing))
ins  = [it.name for it in ng.interface.items_tree
        if getattr(it, "item_type", "") == 'SOCKET' and it.in_out == 'INPUT']
outs = [it.name for it in ng.interface.items_tree
        if getattr(it, "item_type", "") == 'SOCKET' and it.in_out == 'OUTPUT']
check("interface: unique socket names per side (R9)",
      len(ins) == len(set(ins)) and len(outs) == len(set(outs)))
unframed = [n.name for n in ng.nodes
            if n.bl_idname not in ("NodeFrame", "NodeGroupInput", "NodeGroupOutput",
                                   "NodeReroute")
            and n.parent is None]
check("graph: every node inside a labeled frame (R8)", not unframed, str(unframed[:5]))

# --------------------------------------------------------------- summary
bad = [r for r in RES if not r[1]]
print(f"\n== {len(RES) - len(bad)}/{len(RES)} checks passed ==")
if bad:
    for nme, _, info in bad: print("   FAILED:", nme, info)
sys.stdout.flush()
os._exit(1 if bad else 0)
