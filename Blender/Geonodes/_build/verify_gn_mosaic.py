"""Headless verification matrix for GN_Mosaic.blend.

  "C:\\Program Files\\Blender Foundation\\Blender 5.0\\blender.exe" --background \
      --factory-startup D:\\...\\GN_Mosaic.blend --python verify_gn_mosaic.py
"""
import bpy, sys, os, math
from mathutils import Vector

NAME = "GN_Mosaic"
obj = bpy.data.objects["GN_Demo"]
md  = obj.modifiers[0]
ng  = bpy.data.node_groups[NAME]
ID  = {it.name: it.identifier for it in ng.interface.items_tree if hasattr(it, "identifier")}

def setv(name, value):
    md[ID[name]] = value

def ev():
    obj.update_tag()
    dg = bpy.context.evaluated_depsgraph_get()
    dg.update()
    return obj.evaluated_get(dg).data

def stats(me):
    d = {"verts": len(me.vertices), "faces": len(me.polygons), "attrs": {}}
    for a in me.attributes:
        d["attrs"][a.name] = (a.domain, a.data_type)
    return d

def face_sides(me):
    h = {}
    for p in me.polygons:
        h[len(p.vertices)] = h.get(len(p.vertices), 0) + 1
    return h

def attr_vals(me, name):
    a = me.attributes.get(name)
    if a is None: return None
    key = "value" if a.data_type in ("INT", "FLOAT", "BOOLEAN") else "color"
    return [getattr(x, key) for x in a.data]

def has_nan(me):
    for v in me.vertices:
        for c in v.co:
            if not math.isfinite(c): return True
    return False

FAIL = []
def check(cond, msg):
    print(("  OK   " if cond else "  FAIL ") + msg)
    if not cond: FAIL.append(msg)

print("=" * 78)
print("1) DEFAULTS")
me = ev(); s = stats(me)
print("   ", s["verts"], "verts /", s["faces"], "faces | sides", face_sides(me))
print("    attrs:", {k: v for k, v in s["attrs"].items() if not k.startswith(".")})
check(s["faces"] > 100, "default settings generate a decent tile field")
check(not has_nan(me), "no NaN in tile positions")
for a in ("tile_id", "region_id", "tile_random", "tile_color"):
    check(a in s["attrs"], f"attribute '{a}' present")
check(s["attrs"].get("tile_id") == ("FACE", "INT"), "tile_id is FACE/INT")
check(s["attrs"].get("tile_color") == ("CORNER", "FLOAT_COLOR"), "tile_color is CORNER/COLOR (the domain shaders can read)")
for a in ("__mos_tri", "__mos_diag", "__mos_tile", "__mos_tangent"):
    check(a not in s["attrs"], f"internal attribute '{a}' cleaned from the output")

tid = attr_vals(me, "tile_id")
check(len(set(tid)) == len(tid) == s["faces"], "tile_id unique for every tile")
reg = set(attr_vals(me, "region_id"))
print("    region ids:", sorted(reg))
check(len(reg) == 2, "two separate shapes -> two region ids")
rnd = attr_vals(me, "tile_random")
check(all(0.0 <= r <= 1.0 for r in rnd) and len(set(rnd)) > s["faces"] * 0.9,
      "tile_random is 0..1 and varies per tile")

# every tile must sit inside the demo shape: its centre is farther than the hole
# radius (0.52) from the hole centre, and inside the outer contour.
def blobA_R(t): return 1.55 + 0.30 * math.sin(3 * t) + 0.12 * math.sin(7 * t + 1.1)
def blobB_R(t): return 1.15 + 0.34 * math.sin(5 * t)
bad = 0
for p in me.polygons:
    c = p.center
    dA = Vector((c.x + 1.9, c.y)).length
    dB = Vector((c.x - 2.35, c.y)).length
    tA = math.atan2(c.y, c.x + 1.9); tB = math.atan2(c.y, c.x - 2.35)
    inA = 0.52 - 0.12 < dA < blobA_R(tA) + 0.12
    inB = dB < blobB_R(tB) + 0.12
    if not (inA or inB): bad += 1
check(bad == 0, f"all {s['faces']} tiles land inside a bounded shape (outliers: {bad})")
base_faces = s["faces"]

print("\n2) TRIANGLE RATIO   (contour tiles are rectangular by design -> rows off)")
setv("Contour Rows", 0)
setv("Triangle Ratio", 0.0); me = ev(); sq = face_sides(me)
print("    ratio 0.0 ->", sq)
check(set(sq) == {4}, "ratio 0 = only square tiles")
setv("Triangle Ratio", 1.0); me = ev(); tr = face_sides(me)
print("    ratio 1.0 ->", tr)
check(set(tr) == {3}, "ratio 1 = only triangular tiles")
setv("Triangle Ratio", 0.5); me = ev(); mx = face_sides(me)
print("    ratio 0.5 ->", mx)
check(3 in mx and 4 in mx, "ratio 0.5 mixes squares and triangles")
setv("Triangle Ratio", 0.25)
setv("Contour Rows", 1); me = ev()
check(4 in face_sides(me), "contour rows stay rectangular even at a high triangle ratio")

print("\n3) FIT MODE  (0 centre / 1 fully inside / 2 any overlap)")
# graded with the contour band OFF -- with rows >= 1 the reserved band already
# guarantees a whole tile fits, so all three modes legitimately agree.
# Adaptive sizing is off too: it fills the near-wall strip with hundreds of tiny
# tiles, so raw tile counts would say nothing about the fit rule being tested.
setv("Adaptive Levels", 0)
setv("Contour Rows", 0)
counts = []
for m in (0, 1, 2):
    setv("Fit Mode", m); me = ev(); counts.append(len(me.polygons))
    print(f"    rows=0 mode {m}: {counts[-1]} tiles")
check(counts[1] < counts[0] <= counts[2], "fully-inside < centre-inside <= any-overlap")
setv("Contour Rows", 1)
conv = []
for m in (0, 1, 2):
    setv("Fit Mode", m); me = ev(); conv.append(len(me.polygons))
print(f"    rows=1 modes -> {conv}")
check(len(set(conv)) == 1,
      "with a contour band reserved the three fit modes converge (no half-tiles left)")
check(conv[1] > counts[1],
      f"contour rows fill the strip Fully Inside leaves along the walls "
      f"({counts[1]} -> {conv[1]} tiles)")
setv("Fit Mode", 0); setv("Adaptive Levels", 2)

print("\n4) EDGE MARGIN")
setv("Edge Margin", 0.25); me = ev(); marg = len(me.polygons)
print("    margin 0.25 ->", marg, "tiles (was", base_faces, ")")
check(marg < base_faces, "edge margin pulls tiles away from the outline")
setv("Edge Margin", 0.0)

print("\n5) CONTOUR ROWS")
setv("Contour Rows", 0); me = ev(); r0 = len(me.polygons)
setv("Contour Rows", 1); me = ev(); r1 = len(me.polygons)
setv("Contour Rows", 3); me = ev(); r3 = len(me.polygons)
print(f"    rows 0/1/3 -> {r0} / {r1} / {r3} tiles")
check(r0 != r1 and r1 != r3, "contour rows change the tile field")
setv("Contour Rows", 3); me = ev()
sides3 = face_sides(me)
print("    rows 3 sides:", sides3)
setv("Contour Rows", 1)

print("\n6) TILE SIZE / GAP")
setv("Tile Size", 0.2); me = ev(); big = len(me.polygons)
setv("Tile Size", 0.05); me = ev(); small = len(me.polygons)
print(f"    tile 0.2 -> {big} tiles | tile 0.05 -> {small} tiles")
check(small > big * 3, "smaller tiles -> many more of them")
setv("Tile Size", 0.1)
def mean_area(me): return sum(p.area for p in me.polygons) / max(len(me.polygons), 1)
# Gap widens the grout, i.e. the PITCH -- the tiles keep the size the user asked for,
# so the count must drop while the mean tile area stays put.
setv("Gap", 0.0); me = ev(); g0, c0 = mean_area(me), len(me.polygons)
setv("Gap", 0.05); me = ev(); g1, c1 = mean_area(me), len(me.polygons)
print(f"    gap 0.0 -> {c0} tiles, mean area {g0:.6f} | gap 0.05 -> {c1} tiles, {g1:.6f}")
check(c1 < c0 * 0.8, "a wider gap spaces the tiles further apart (fewer fit)")
check(abs(g1 - g0) < g0 * 0.25, "a wider gap does NOT change the tile size itself")
setv("Gap", 0.015)

print("\n7) LAYOUT PARAMS")
def bbox(me):
    xs = [v.co.x for v in me.vertices]; ys = [v.co.y for v in me.vertices]
    return (min(xs), max(xs), min(ys), max(ys))
setv("Irregularity", 0.0); me = ev(); a0 = sorted(p.area for p in me.polygons)
setv("Irregularity", 0.8); me = ev(); a1 = sorted(p.area for p in me.polygons)
print(f"    irregularity 0 area spread {a0[-1]-a0[0]:.5f} | 0.8 -> {a1[-1]-a1[0]:.5f}")
check(a1[-1] - a1[0] > a0[-1] - a0[0], "irregularity varies the cell shapes")
setv("Irregularity", 0.15)
def coords(me): return sorted(tuple(round(c, 5) for c in v.co) for v in me.vertices)
setv("Grid Rotation", 0.0); me = ev(); b0 = coords(me)
setv("Grid Rotation", 0.6); me = ev(); b1 = coords(me)
check(b0 != b1, "grid rotation turns the courses of tiles")
setv("Grid Rotation", 0.0)
setv("Rotation Jitter", 0.0); me = ev(); n0 = [tuple(v.co) for v in me.vertices][:50]
setv("Rotation Jitter", 0.3); me = ev(); n1 = [tuple(v.co) for v in me.vertices][:50]
check(n0 != n1, "rotation jitter turns individual tiles")
setv("Rotation Jitter", 0.06)
setv("Region Rotation", 0.4); me = ev()
check(len(me.polygons) > 0, "region rotation evaluates")
setv("Region Rotation", 0.0)

print("\n8) SEED")
setv("Seed", 0); me = ev(); s0 = [tuple(v.co) for v in me.vertices][:80]
setv("Seed", 7); me = ev(); s7 = [tuple(v.co) for v in me.vertices][:80]
check(s0 != s7, "seed reshuffles the mosaic")
setv("Seed", 0)

print("\n9) CUT TILES AT BOUNDARY")
setv("Fit Mode", 2)
setv("Fit Tiles To Boundary", False); me = ev(); cut0 = [tuple(v.co) for v in me.vertices]
setv("Fit Tiles To Boundary", True);  me = ev(); cut1 = [tuple(v.co) for v in me.vertices]
moved = sum(1 for a, b in zip(cut0, cut1) if a != b)
print(f"    {moved} of {len(cut0)} vertices snapped onto the boundary")
check(moved > 0, "cut pulls overhanging corners onto the outline")
check(not has_nan(me), "no NaN after cutting")
setv("Fit Tiles To Boundary", False); setv("Fit Mode", 0)

print("\n10) THICKNESS / KEEP SOURCE")
setv("Thickness", 0.0); me = ev(); f0 = len(me.polygons)
setv("Thickness", 0.05); me = ev(); f1 = len(me.polygons)
print(f"    flat {f0} faces -> extruded {f1} faces")
check(f1 > f0 * 2, "thickness turns tiles into slabs")
setv("Thickness", 0.0)
setv("Keep Source Mesh", True); me = ev(); k1 = len(me.polygons)
print(f"    keep source -> {k1} faces (tiles {f0} + source {len(obj.data.polygons)})")
check(k1 == f0 + len(obj.data.polygons), "source mesh joined underneath")
setv("Keep Source Mesh", False)

print("\n11) PROJECTION AXIS + CONFORM")
for m, nm in ((0, "Auto"), (3, "Z")):
    setv("Projection Axis", m); me = ev()
    print(f"    axis {nm}: {len(me.polygons)} tiles")
    check(len(me.polygons) > 100, f"axis {nm} tiles the flat demo")
setv("Projection Axis", 1); me = ev()   # X -- grid seen edge-on, must not explode
print("    axis X (degenerate for a flat XY plane):", len(me.polygons), "tiles")
check(not has_nan(me), "degenerate projection axis produces no NaN")
setv("Projection Axis", 0)
setv("Conform To Surface", False); me = ev()
check(len(me.polygons) > 100 and not has_nan(me), "conform off still tiles")
setv("Conform To Surface", True)
setv("Surface Offset", 0.1); me = ev()
check(abs(me.vertices[0].co.z - 0.1) < 1e-4, "surface offset lifts the tiles")
setv("Surface Offset", 0.0)

print("\n12) SELECTION / BOUNDARY TOGGLES")
setv("Use Open Edges", False); me = ev()
print("    open edges off ->", len(me.polygons), "tiles")
check(len(me.polygons) > 1000, "with no walls at all the surface still fills with tiles")
check(not has_nan(me), "no NaN with an empty boundary")
setv("Use Open Edges", True)
# a face selection border must act as a wall on its own
half = ng.interface.items_tree["Selection"].identifier
md[half + "_use_attribute"] = True
md[half + "_attribute_name"] = "half"
mesh = obj.data
if "half" not in mesh.attributes:
    a = mesh.attributes.new("half", 'BOOLEAN', 'FACE')
    for i, p in enumerate(mesh.polygons):
        a.data[i].value = p.center.x < 0.0
me = ev()
print("    Selection = left half ->", len(me.polygons), "tiles")
check(0 < len(me.polygons) < base_faces, "face Selection restricts the mosaic to part of the mesh")
xs = [p.center.x for p in me.polygons]
check(max(xs) < 0.4, "no tiles generated outside the selected faces")
md[half + "_use_attribute"] = False

print("\n13) ADAPTIVE TILE SIZE")
def wall_dist(c):
    """approx distance from a tile centre to the nearest demo wall"""
    dA = Vector((c.x + 1.9, c.y)).length
    dB = Vector((c.x - 2.35, c.y)).length
    tA = math.atan2(c.y, c.x + 1.9); tB = math.atan2(c.y, c.x - 2.35)
    if dB < blobB_R(tB) + 0.2:
        return abs(blobB_R(tB) - dB)
    return min(abs(blobA_R(tA) - dA), abs(dA - 0.52))
setv("Contour Rows", 0); setv("Triangle Ratio", 0.0)
setv("Adaptive Levels", 0); me = ev()
n0, sp0 = len(me.polygons), max(p.area for p in me.polygons) / min(p.area for p in me.polygons)
setv("Adaptive Levels", 2); me = ev()
n2, sp2 = len(me.polygons), max(p.area for p in me.polygons) / min(p.area for p in me.polygons)
print(f"    levels 0 -> {n0} tiles, area max/min {sp0:.1f} | levels 2 -> {n2} tiles, {sp2:.1f}")
check(n2 > n0, "adaptive levels produce more, smaller tiles where space is tight")
check(sp2 > sp0 * 3, "adaptive levels give a genuinely mixed range of tile sizes")
# the refined band is about one cell wide, so bin by actual distance rather than by
# quantile -- a quantile bucket is far wider than the band and dilutes the effect
CELL = 0.115                                    # Tile Size 0.1 + Gap 0.015
prof = [(lo, [p.area for p in me.polygons
              if lo * CELL <= wall_dist(p.center) < hi * CELL])
        for lo, hi in ((0, 1), (1, 2), (2, 3), (3, 99))]
for lo, xs in prof:
    if xs: print(f"    {lo}-{lo+1} cells from a wall: {len(xs):4d} tiles, mean area {sum(xs)/len(xs):.5f}")
near = sum(prof[0][1]) / max(len(prof[0][1]), 1)
far = sum(prof[3][1]) / max(len(prof[3][1]), 1)
check(near < far * 0.5,
      f"tiles crowding a wall really are smaller ({near:.5f} vs {far:.5f} in open ground)")
setv("Adaptive Levels", 0); setv("Triangle Ratio", 0.25); setv("Contour Rows", 1)

print("\n14) CONTOUR SIZE / WIDTH / SPACING / TRIANGLES")
setv("Adaptive Levels", 0); setv("Contour Rows", 1)
me = ev(); base_c = len(me.polygons)
setv("Contour Spacing", 2.0); me = ev(); sp = len(me.polygons)
print(f"    spacing 1.0 -> {base_c} tiles | 2.0 -> {sp}")
check(sp < base_c, "contour spacing thins the row out")
setv("Contour Spacing", 1.0)
setv("Contour Length", 0.3); me = ev()
lens = [max((me.vertices[p.vertices[(i + 1) % len(p.vertices)]].co
             - me.vertices[p.vertices[i]].co).length for i in range(len(p.vertices)))
        for p in me.polygons]
print(f"    contour length 0.3 -> longest tile edge {max(lens):.3f}")
check(max(lens) > 0.25, "Contour Length makes long brick-shaped contour tesserae")
setv("Contour Length", 0.0)
setv("Contour Width", 0.04); me = ev(); narrow = len(me.polygons)
print(f"    contour width 0.04 -> {narrow} tiles (was {base_c})")
check(narrow != base_c, "Contour Width changes the border row")
setv("Contour Width", 0.0)
setv("Contour Rows", 2); setv("Contour Triangle Ratio", 0.0); me = ev()
q0 = face_sides(me).get(3, 0)
setv("Contour Triangle Ratio", 1.0); me = ev()
q1 = face_sides(me).get(3, 0)
print(f"    contour triangles 0.0 -> {q0} tris | 1.0 -> {q1} tris")
check(q1 > q0, "Contour Triangle Ratio splits contour tiles into triangles")
setv("Contour Triangle Ratio", 0.0); setv("Contour Rows", 1)

print("\n15) BOUNDARY GAP + FIT TO BOUNDARY")
def min_wall_gap(me):
    return min(wall_dist(Vector(v.co)) if False else wall_dist(v.co) for v in me.vertices)
setv("Boundary Gap", 0.0); me = ev(); g0 = len(me.polygons)
setv("Boundary Gap", 0.12); me = ev(); g1 = len(me.polygons)
print(f"    boundary gap 0.0 -> {g0} tiles | 0.12 -> {g1}")
check(g1 < g0, "Boundary Gap holds the mosaic back from the walls")
setv("Fit Mode", 2); setv("Fit Tiles To Boundary", True); me = ev()
check(not has_nan(me), "no NaN when fitting tiles to the boundary")
outs = sum(1 for p in me.polygons
           if wall_dist(p.center) < 0.02 and len(p.vertices) >= 3)
print(f"    fitted with a 0.12 gap: {len(me.polygons)} tiles, {outs} sitting on the wall")
check(len(me.polygons) > 0, "fit-to-boundary evaluates with a gap")
setv("Boundary Gap", 0.0); me = ev()
check(not has_nan(me), "no NaN fitting with a zero gap")
setv("Fit Tiles To Boundary", False); setv("Fit Mode", 0)

print("\n16) SHATTER TILING MODE")
SRC_AREA = sum(p.area for p in obj.data.polygons)
SRC_FACES = len(obj.data.polygons)
print(f"    source region: {SRC_FACES} faces, area {SRC_AREA:.4f}")
setv("Contour Rows", 0); setv("Adaptive Levels", 0); setv("Fit Mode", 0)
setv("Tiling Mode", 1); setv("Tile Size", 0.25); setv("Shatter Levels", 6)
setv("Split Chance", 1.0); setv("Scale Variation", 0.3)
setv("Gap", 0.0); me = ev()
cov = sum(p.area for p in me.polygons) / SRC_AREA
print(f"    gap 0: {len(me.polygons)} tiles covering {100*cov:.2f}% of the region")
check(abs(cov - 1.0) < 0.005,
      "shatter tiles PARTITION the region exactly (100% coverage at zero grout)")
setv("Max Corners", 3); me = ev()
check(set(face_sides(me)) == {3}, "Max Corners 3 gives the all-triangle break-up")
check(not has_nan(me), "no NaN in shatter mode")
tid = attr_vals(me, "tile_id")
check(len(set(tid)) == len(tid), "every shatter tile still gets a unique tile_id")
check(len(set(attr_vals(me, "region_id"))) == 2, "shatter keeps the two regions apart")
# nothing may escape the shape or fall into the hole
bad = 0
for p in me.polygons:
    c = p.center
    dA = Vector((c.x + 1.9, c.y)).length; dB = Vector((c.x - 2.35, c.y)).length
    tA = math.atan2(c.y, c.x + 1.9); tB = math.atan2(c.y, c.x - 2.35)
    if not ((0.52 - 0.02 < dA < blobA_R(tA) + 0.02) or (dB < blobB_R(tB) + 0.02)): bad += 1
check(bad == 0, f"no shatter tile escapes the outline or falls into the hole ({bad})")

setv("Shatter Levels", 0); me = ev()
print(f"    levels 0 -> {len(me.polygons)} tiles (source triangulates to >= {SRC_FACES})")
check(len(me.polygons) >= SRC_FACES,
      "level 0 returns the seed triangulation itself, one tile per region face")
setv("Shatter Levels", 6)
setv("Gap", 0.02); me = ev(); ga = sum(p.area for p in me.polygons) / SRC_AREA
print(f"    gap 0.02 -> {100*ga:.1f}% coverage (grout eats the rest)")
check(ga < 0.99, "grout opens a real joint between shatter tiles")
def biggest(me):
    """99th-percentile tile area -- how large the surviving slabs actually are.
    (A max/min spread says nothing here: this demo's own topology already spans a
    huge size range, which swamps the effect being measured.)"""
    ar = sorted(p.area for p in me.polygons)
    return ar[int(len(ar) * 0.99)] if ar else 0.0
# Shatter can only subdivide, never merge, so the seed's own face size is a floor --
# this demo's faces are already ~0.1 across. Ask for something smaller than that or
# nothing splits at all and the parameters look inert.
setv("Tile Size", 0.04); setv("Gap", 0.004)
setv("Split Chance", 1.0); me = ev(); n_even = len(me.polygons)
spread_even = biggest(me)
setv("Split Chance", 0.45); me = ev(); n_chunk = len(me.polygons)
spread_chunk = biggest(me)
print(f"    chance 1.0 -> {n_even} tiles, biggest {spread_even:.5f} | "
      f"0.45 -> {n_chunk} tiles, biggest {spread_chunk:.5f}")
check(n_chunk < n_even, "a lower split chance leaves bigger pieces")
check(spread_chunk > spread_even * 1.2,
      "a lower split chance leaves genuinely larger slabs among the small fragments")
setv("Split Chance", 0.75)
setv("Split Chance", 1.0); setv("Gap", 0.004)
setv("Tile Size", 0.6); me = ev(); coarse = len(me.polygons)
setv("Tile Size", 0.03); me = ev(); fine = len(me.polygons)
print(f"    tile 0.6 (coarser than the seed) -> {coarse} tiles | 0.03 -> {fine}")
# not "exactly the seed": the sliver rule still squares up the demo's elongated
# radial cells, which is wanted. What matters is that a coarse target barely subdivides.
check(coarse < fine / 5,
      "a target coarser than the input faces barely subdivides (shatter cannot merge)")
check(fine > coarse * 2, "a target finer than the input faces drives real subdivision")
print("    -- corner counts and the boundary gap --")
setv("Gap", 0.0); setv("Tile Size", 0.25); setv("Shatter Levels", 6)
setv("Split Chance", 1.0)
shapes = {}
for mc in (3, 4, 5, 6):
    setv("Max Corners", mc); me = ev()
    sides = face_sides(me); shapes[mc] = sides
    cov = sum(p.area for p in me.polygons) / SRC_AREA
    print(f"    max corners {mc}: {len(me.polygons)} tiles, sides {sides}, cover {100*cov:.2f}%")
    check(abs(cov - 1.0) < 0.005, f"Max Corners {mc} still partitions the region exactly")
    check(max(sides) <= mc, f"Max Corners {mc} is respected (no tile has more sides)")
check(4 in shapes[4], "Max Corners 4 produces quads")
check(5 in shapes[5], "Max Corners 5 produces pentagons")
check(6 in shapes[6], "Max Corners 6 produces hexagons")
# a boundary gap that is a sensible fraction of the tile size is held exactly
setv("Max Corners", 4); setv("Boundary Gap", 0.03); me = ev()
worst = 9.9
for p in me.polygons:
    for i in p.vertices:
        c = me.vertices[i].co
        dA = Vector((c.x + 1.9, c.y)).length; dB = Vector((c.x - 2.35, c.y)).length
        tA = math.atan2(c.y, c.x + 1.9); tB = math.atan2(c.y, c.x - 2.35)
        if dB < blobB_R(tB) + 0.3: worst = min(worst, abs(blobB_R(tB) - dB))
        else: worst = min(worst, min(abs(blobA_R(tA) - dA), abs(dA - 0.52)))
print(f"    boundary gap 0.03 -> closest tile vertex sits {worst:.4f} from a wall")
check(worst > 0.02, "Shatter holds the tiles off the walls by the Boundary Gap")
setv("Boundary Gap", 0.0); setv("Max Corners", 4)
setv("Tile Size", 0.1); setv("Gap", 0.015); setv("Shatter Levels", 7)
setv("Scale Variation", 0.12); setv("Tiling Mode", 0)
setv("Adaptive Levels", 2); setv("Contour Rows", 1)
me = ev()
check(len(me.polygons) == base_faces, "switching back to Grid restores the original result")

print("\n17) TILEABLE SEAMS  (own 2x2 plane filling the bounds box)")
import bmesh
H, N = 1.0, 8
_bm = bmesh.new()
_g = [[_bm.verts.new((-H + 2 * H * i / N, -H + 2 * H * j / N, 0.0))
       for j in range(N + 1)] for i in range(N + 1)]
for i in range(N):
    for j in range(N):
        _bm.faces.new((_g[i][j], _g[i + 1][j], _g[i + 1][j + 1], _g[i][j + 1]))
bmesh.ops.recalc_face_normals(_bm, faces=_bm.faces[:])
if sum(f.normal.z for f in _bm.faces) < 0:
    bmesh.ops.reverse_faces(_bm, faces=_bm.faces[:])
_me = bpy.data.meshes.new("TilePlane"); _bm.to_mesh(_me); _bm.free()
_ob = bpy.data.objects.new("TilePlane", _me)
bpy.context.scene.collection.objects.link(_ob)
_md = _ob.modifiers.new("GN_Mosaic", "NODES"); _md.node_group = ng
def tset(n, v): _md[ID[n]] = v
def tev():
    _ob.update_tag(); dg = bpy.context.evaluated_depsgraph_get(); dg.update()
    return _ob.evaluated_get(dg).data
for k, v in (("Tiling Mode", 1), ("Contour Rows", 0), ("Tile Size", 0.42),
             ("Gap", 0.05), ("Boundary Gap", 0.22), ("Shatter Levels", 7),
             ("Max Corners", 4), ("Split Chance", 1.0), ("Adaptive Threshold", 0.0),
             ("Tile Bounds", (2.0, 2.0, 2.0))):
    tset(k, v)
def _inset():
    m = tev()
    return min(min(H - abs(v.co[0]), H - abs(v.co[1])) for v in m.vertices), len(m.polygons)
tset("Tileable", False); i_off, n_off = _inset()
tset("Tileable", True);  i_on, n_on = _inset()
print(f"    tileable off: inset {i_off:.4f} -> seam joint {2*i_off:.4f} ({n_off} tiles)")
print(f"    tileable on : inset {i_on:.4f} -> seam joint {2*i_on:.4f} ({n_on} tiles), "
      f"interior Gap 0.0500")
check(abs(2 * i_on - 0.05) < 1e-3,
      "a seam joint between two copies equals the interior Gap exactly")
check(2 * i_off > 0.05 * 2,
      "without Tileable the seam would show the Boundary Gap twice over")
check(i_on > 0.0,
      "no tile crosses the bounds box, so copies never overlap")
# the cuts along opposite faces must agree, and keep agreeing once jitter is applied
def _face_cuts(m, axis, sign, other):
    return set(round(v.co[other], 4) for v in m.vertices
               if abs(abs(v.co[axis]) - H) < 0.03 and v.co[axis] * sign > 0)
tset("Gap", 0.0)
for jit in (0.0, 0.5, 1.0):
    tset("Split Jitter", jit)
    tset("Tileable", True); m = tev()
    bad = len(_face_cuts(m, 0, -1, 1) ^ _face_cuts(m, 0, +1, 1))         + len(_face_cuts(m, 1, -1, 0) ^ _face_cuts(m, 1, +1, 0))
    print(f"    jitter {jit:.2f}: {bad} cut(s) on a face without a partner opposite")
    check(bad == 0, f"opposite faces are divided identically at Split Jitter {jit}")
tset("Split Jitter", 0.5); tset("Gap", 0.05); tset("Boundary Gap", 0.22)
tset("Tileable", False)

print("\n18) SHATTER PER-TILE VARIATION  (same wobble the grid tiles get)")
# every shattered tile is one face, and the variation runs after the cull, so face and
# vertex order are stable across these settings -- tile i can be compared to tile i
for k, v in (("Tileable", False), ("Boundary Gap", 0.0), ("Gap", 0.05),
             ("Split Jitter", 0.5), ("Shatter Position Jitter", 0.0),
             ("Shatter Rotation Jitter", 0.0), ("Shatter Scale Jitter", 0.0)):
    tset(k, v)
def _tiles():
    m = tev()
    return ([p.area for p in m.polygons], [tuple(p.center) for p in m.polygons],
            [tuple(v.co) for v in m.vertices])
def _maxd(a, b):
    return max((Vector(p) - Vector(q)).length for p, q in zip(a, b)) if a else 0.0
a0, c0, v0 = _tiles()
print(f"    baseline: {len(a0)} tiles, total area {sum(a0):.4f}")

tset("Shatter Position Jitter", 0.8); a1, c1, v1 = _tiles()
cap = 0.5 * 0.05 * 0.8 * math.sqrt(2.0)
dA = max(abs(x - y) for x, y in zip(a0, a1)) if a0 else 0.0
print(f"    position jitter 0.8: tiles move up to {_maxd(c0, c1):.4f} "
      f"(cap {cap:.4f}), worst area change {dA:.2e}")
check(len(a1) == len(a0), "position jitter moves tiles without adding or losing any")
check(_maxd(c0, c1) > 1e-4, "position jitter actually shifts the tiles")
check(_maxd(c0, c1) <= cap * 1.02, "the shift stays inside the grout it was scaled by")
check(dA < 1e-6, "the tiles slide rigidly -- no tile changes area")

tset("Shatter Position Jitter", 0.0); tset("Shatter Rotation Jitter", 0.08)
a2, c2, v2 = _tiles()
dA2 = max(abs(x - y) for x, y in zip(a0, a2)) if a0 else 0.0
print(f"    rotation jitter 0.08: centroids move {_maxd(c0, c2):.2e}, "
      f"vertices move up to {_maxd(v0, v2):.4f}, worst area change {dA2:.2e}")
check(_maxd(v0, v2) > 1e-4, "rotation jitter actually turns the tiles")
check(_maxd(c0, c2) < 1e-5, "each tile turns about its OWN centroid, which stays put")
check(dA2 < 1e-6, "rotation is rigid -- no tile changes area")

tset("Shatter Rotation Jitter", 0.0); tset("Shatter Scale Jitter", 0.3)
a3, c3, v3 = _tiles()
print(f"    scale jitter 0.3: total area {sum(a3):.4f} vs {sum(a0):.4f}")
check(sum(a3) < sum(a0) * 0.995, "scale jitter opens the grout up by shrinking tiles")
check(all(x <= y + 1e-9 for x, y in zip(a3, a0)), "it only ever shrinks, never grows")
check(_maxd(c0, c3) < 1e-5, "tiles shrink about their own centroid")

# Rotation must deliver the angle it was ASKED for -- no silent per-tile ceiling. An
# earlier build limited it to what each tile's grout could absorb, which made the control
# stop responding on coarse break-ups and do nothing whatsoever at Gap 0.
tset("Shatter Scale Jitter", 0.0); tset("Shatter Position Jitter", 0.0)
tset("Tile Size", 0.9); tset("Shatter Levels", 3)          # deliberately big tiles
tset("Shatter Rotation Jitter", 0.0)
_, _, vb = _tiles()
_mb = tev()
_e0 = [(_mb.vertices[p.vertices[1]].co - _mb.vertices[p.vertices[0]].co).copy()
       for p in _mb.polygons]
for _ask in (0.05, 0.30):
    tset("Shatter Rotation Jitter", _ask)
    _m1 = tev()
    _e1 = [(_m1.vertices[p.vertices[1]].co - _m1.vertices[p.vertices[0]].co).copy()
           for p in _m1.polygons]
    _got = 0.0
    for _a, _b in zip(_e0, _e1):
        if _a.length > 1e-9 and _b.length > 1e-9:
            _got = max(_got, math.degrees(math.acos(
                max(-1.0, min(1.0, _a.normalized().dot(_b.normalized()))))))
    print(f"    big tiles, asked {math.degrees(_ask):5.1f} deg -> largest turn "
          f"{_got:5.2f} deg")
    check(_got > math.degrees(_ask) * 0.9,
          f"rotation jitter delivers the {math.degrees(_ask):.0f} deg it was asked for")
tset("Tile Size", 0.42); tset("Shatter Levels", 7); tset("Shatter Rotation Jitter", 0.0)

# position jitter IS grout-scaled, so it stays inert at Gap 0 -- that is what keeps the
# exact-coverage partition intact at the defaults
tset("Gap", 0.0)
_, _, vz = _tiles()
tset("Shatter Position Jitter", 1.0)
_, _, vj = _tiles()
print(f"    at Gap 0: worst vertex move with position jitter at maximum {_maxd(vz, vj):.2e}")
check(_maxd(vz, vj) < 1e-6,
      "at Gap 0 position jitter does nothing, so the partition stays exact")

# a seam cannot be dragged out of register: the tile on the far face is a different
# shape, so tiles touching one sit the variation out entirely
tset("Gap", 0.05); tset("Shatter Position Jitter", 0.0); tset("Tileable", True)
tset("Shatter Position Jitter", 0.0); tset("Shatter Rotation Jitter", 0.0)
_, _, vt0 = _tiles()
tset("Shatter Position Jitter", 0.8); tset("Shatter Rotation Jitter", 0.08)
_, _, vt1 = _tiles()
_seam = [i for i, c in enumerate(vt0) if min(H - abs(c[0]), H - abs(c[1])) < 0.03]
_rest = [i for i in range(len(vt0)) if i not in set(_seam)]
_ds = max((Vector(vt1[i]) - Vector(vt0[i])).length for i in _seam) if _seam else 0.0
_dr = max((Vector(vt1[i]) - Vector(vt0[i])).length for i in _rest) if _rest else 0.0
print(f"    tileable on: {len(_seam)} seam vertices move {_ds:.2e}, "
      f"{len(_rest)} interior vertices move up to {_dr:.4f}")
check(len(_seam) > 0, "the test plane really does have tiles on the seam")
check(_ds < 1e-6, "seam vertices are pinned, so two copies still mate exactly")
check(_dr > 1e-4, "the tiles away from the seam still get their wobble")

for k, v in (("Tileable", False), ("Shatter Position Jitter", 0.0),
             ("Shatter Rotation Jitter", 0.0), ("Shatter Scale Jitter", 0.0),
             ("Boundary Gap", 0.22)):
    tset(k, v)

print("\n19) SIZE AND GROUT RANGES  (Tile Size Max / Gap Max / Boundary Gap Max)")
# Joint width between two shattered tiles. Every tile owns its vertices outright, so the
# two sides of a joint are two separate edges: take each edge midpoint and find the
# nearest midpoint belonging to a DIFFERENT tile. Bucketed on a grid coarser than the
# joint, or the two sides land in different buckets and nothing is ever found.
def _joint_widths(m, cell, hi):
    mids = []
    for fi, p in enumerate(m.polygons):
        n = len(p.vertices)
        for k in range(n):
            a = m.vertices[p.vertices[k]].co
            b = m.vertices[p.vertices[(k + 1) % n]].co
            mids.append((((a + b) * 0.5).copy(), fi))
    grid = {}
    for i, (c, fi) in enumerate(mids):
        grid.setdefault((int(c[0] // cell), int(c[1] // cell)), []).append(i)
    out = []
    for i, (c, fi) in enumerate(mids):
        best = None
        gx, gy = int(c[0] // cell), int(c[1] // cell)
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                for j in grid.get((gx + dx, gy + dy), ()):
                    if mids[j][1] == fi:
                        continue
                    d = (mids[j][0] - c).length
                    if best is None or d < best:
                        best = d
        if best is not None and best < hi:
            out.append(best)
    return out

for k, v in (("Tiling Mode", 1), ("Tileable", False), ("Contour Rows", 0),
             ("Boundary Gap", 0.0), ("Tile Size", 0.42), ("Shatter Levels", 7),
             ("Gap", 0.02), ("Gap Max", 0.0), ("Tile Size Max", 0.0),
             ("Boundary Gap Max", 0.0), ("Split Jitter", 0.5)):
    tset(k, v)
# Read the MEDIAN and quartiles, not min/max: an edge whose neighbour was dropped as
# all-grout has no partner, so its "nearest midpoint on another tile" is a tile away and
# contaminates the extremes. The bulk of the distribution is what carries the answer.
def _quart(v):
    s = sorted(v)
    return (s[len(s) // 4], s[len(s) // 2], s[(3 * len(s)) // 4])
w0 = _joint_widths(tev(), 0.25, 0.12)
q0 = _quart(w0)
print(f"    Gap 0.02, Gap Max off : {len(w0)} joints, "
      f"quartiles {q0[0]:.4f} / {q0[1]:.4f} / {q0[2]:.4f}, min {min(w0):.4f}")
check(len(w0) > 50, "the joint measurement finds joints at all")
check(q0[2] - q0[0] < 2e-3, "with Gap Max off every joint is the same width")
check(abs(q0[1] - 0.02) < 2e-3, "...and that width is the Gap asked for")
check(min(w0) > 0.02 - 2e-3, "no joint is tighter than the Gap")
tset("Gap Max", 0.08)
w1 = _joint_widths(tev(), 0.25, 0.12)
q1 = _quart(w1)
print(f"    Gap 0.02, Gap Max 0.08: {len(w1)} joints, "
      f"quartiles {q1[0]:.4f} / {q1[1]:.4f} / {q1[2]:.4f}, min {min(w1):.4f}")
check(q1[2] - q1[0] > 0.02, "Gap Max spreads the joints over a range")
check(0.02 - 2e-3 < q1[1] < 0.08 + 2e-3, "the typical joint sits inside Gap .. Gap Max")
check(min(w1) > 0.02 - 2e-3, "and none is tighter than the base Gap")
# A joint is measured edge-to-edge across two SEPARATE tiles, so if the two disagreed
# about its width the pair would not sit at a single clean value -- the tight quartile
# spread in the Gap-Max-off case is what proves they agree.
tset("Gap Max", 0.0)

# Tile Size Max changes the break-up ITSELF in Shatter -- each piece is split down to
# its own target, so the range shows up as a genuinely mixed mosaic rather than as a
# uniform field that has been scaled afterwards
def _size_stats():
    a = sorted(p.area for p in tev().polygons)
    return len(a), sum(a) / len(a), a[int(len(a) * 0.9)] / max(a[int(len(a) * 0.1)], 1e-9)
tset("Tile Size", 0.25); tset("Tile Size Max", 0.0)
n_u, mean_u, ratio_u = _size_stats()
tset("Tile Size Max", 0.9)
n_r, mean_r, ratio_r = _size_stats()
print(f"    Tile Size 0.25 alone : {n_u} tiles, mean area {mean_u:.4f}, p90/p10 {ratio_u:.1f}")
print(f"    ...with Max 0.9      : {n_r} tiles, mean area {mean_r:.4f}, p90/p10 {ratio_r:.1f}")
check(mean_r > mean_u * 2.0, "a tile SIZE range lets pieces target sizes well above Tile Size")
check(ratio_r > ratio_u * 1.2, "...and widens the spread between the big and small tiles")
check(n_r < n_u, "bigger targets mean fewer, coarser pieces")
tset("Tile Size Max", 0.0); tset("Tile Size", 0.42)

# Boundary Gap Max: the setback from the wall stops being one flat line
tset("Boundary Gap", 0.03); tset("Boundary Gap Max", 0.0)
def _wall_setback():
    m = tev()
    return [d for d in (min(H - abs(v.co[0]), H - abs(v.co[1])) for v in m.vertices)
            if d < 0.25]
# the tiles actually touching the wall are the lowest setbacks; with one flat Boundary
# Gap they all sit at exactly that value, with a range they fan out
s0 = sorted(_wall_setback())[:24]
tset("Boundary Gap Max", 0.12)
s1 = sorted(_wall_setback())[:24]
print(f"    24 closest verts to a wall: flat {s0[0]:.4f}..{s0[-1]:.4f} | "
      f"ranged {s1[0]:.4f}..{s1[-1]:.4f}")
check(s0[-1] - s0[0] < 1e-3, "with Boundary Gap Max off the wall setback is one flat line")
check(s1[-1] - s1[0] > 3e-3,
      "Boundary Gap Max makes the wall setback ragged instead of a flat line")
check(s1[0] > 0.03 - 1e-3, "no tile comes closer than the base Boundary Gap")
tset("Boundary Gap Max", 0.0); tset("Boundary Gap", 0.22)
tset("Tile Size", 0.42); tset("Gap", 0.05)

bpy.data.objects.remove(_ob, do_unlink=True)

# --- the same two ranges in GRID mode, on the demo -----------------------------------
# every other source of variation off, so any spread in tile area is the range under test
for k, v in (("Tiling Mode", 0), ("Contour Rows", 0), ("Adaptive Levels", 0),
             ("Position Jitter", 0.0), ("Rotation Jitter", 0.0), ("Irregularity", 0.0),
             ("Scale Variation", 0.0), ("Region Rotation", 0.0), ("Triangle Ratio", 0.0),
             ("Tile Size", 0.1), ("Gap", 0.015), ("Gap Max", 0.0),
             ("Tile Size Max", 0.0), ("Boundary Gap", 0.0)):
    setv(k, v)
def _grid_areas():
    a = sorted(p.area for p in ev().polygons)
    return len(a), a[0], a[-1], sum(a) / len(a)
n0, lo0, hi0, mean0 = _grid_areas()
print(f"    grid, no ranges  : {n0} tiles, area {lo0:.5f}..{hi0:.5f}")
check(hi0 - lo0 < 1e-6, "with everything off the grid tiles are all identical")

setv("Gap Max", 0.05)
n1, lo1, hi1, mean1 = _grid_areas()
print(f"    grid, Gap Max .05: {n1} tiles, area {lo1:.5f}..{hi1:.5f}, mean {mean1:.5f}")
check(hi1 - lo1 > 1e-5, "Gap Max varies the grout per tile in Grid mode too")
check(mean1 < mean0, "...and more grout on average means less tile")
check(hi1 <= hi0 + 1e-6, "no tile grows past its cell, so tiles still cannot collide")
setv("Gap Max", 0.0)

setv("Tile Size Max", 0.25)
n2, lo2, hi2, mean2 = _grid_areas()
print(f"    grid, Size Max .25: {n2} tiles, area {lo2:.5f}..{hi2:.5f}")
check(n2 < n0, "a bigger size range spaces the lattice wider, so fewer tiles fit")
check(hi2 - lo2 > (hi0 - lo0) + 1e-5, "Tile Size Max mixes tile sizes in Grid mode")
check(hi2 > hi0, "...including tiles larger than plain Tile Size would give")
setv("Tile Size Max", 0.0)

print("\n20) RANGES OFF == OLD BEHAVIOUR  (the defaults must not have moved)")
for k, v in (("Tiling Mode", 0), ("Tile Size", 0.1), ("Gap", 0.015),
             ("Contour Rows", 1), ("Adaptive Levels", 2), ("Fit Mode", 0),
             ("Triangle Ratio", 0.25), ("Irregularity", 0.15),
             ("Position Jitter", 0.4), ("Rotation Jitter", 0.06),
             ("Region Rotation", 0.0), ("Edge Margin", 0.0), ("Grid Rotation", 0.0),
             ("Scale Variation", 0.12), ("Boundary Gap", 0.0), ("Seed", 0),
             ("Tile Size Max", 0.0), ("Gap Max", 0.0), ("Boundary Gap Max", 0.0)):
    setv(k, v)
me = ev()
print(f"    grid defaults -> {len(me.polygons)} tiles (baseline was {base_faces})")
check(len(me.polygons) == base_faces,
      "with every Max at 0 the grid generator reproduces its original output exactly")

print("\n" + "=" * 78)
print("FAILURES:", len(FAIL))
for f in FAIL: print("   -", f)
sys.stdout.flush()
os._exit(1 if FAIL else 0)
