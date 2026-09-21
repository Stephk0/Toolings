"""Verify GN_Delete evaluated behaviour -- both the original selection-delete and
the folded-in Stray Geometry stage. Also proves the stage is inert when off.

  blender --background --factory-startup --python verify_gn_delete.py
"""
import bpy, bmesh, sys, os
from mathutils import Matrix, Vector

PATH = r"D:\Stephko_Tooling\Toolings\Blender\Geonodes\GN_Delete.blend"
NAME = "GN_Delete"
bpy.ops.wm.open_mainfile(filepath=PATH)
ng = bpy.data.node_groups[NAME]
ids = {it.name: it.identifier for it in ng.interface.items_tree
       if getattr(it, 'item_type', '') == 'SOCKET' and it.in_out == 'INPUT'}

# ------------------------------------------------------------------ test mesh
# sphere (42v) + tiny cube island (8v) + lone quad (4v) + lone tri (3v)
# + loose vert (1v) + floating edge (2v) + 2-segment dangling wire (2v) = 62v
me = bpy.data.meshes.new("StrayTest")
bm = bmesh.new()
bmesh.ops.create_icosphere(bm, subdivisions=2, radius=2.0)
bm.verts.ensure_lookup_table()
bmesh.ops.create_cube(bm, size=0.03, matrix=Matrix.Translation((0, 6, 0)))
bm.faces.new([bm.verts.new(c) for c in [(6, 0, 0), (6.3, 0, 0), (6.3, .3, 0), (6, .3, 0)]])
bm.faces.new([bm.verts.new(c) for c in [(6, 1, 0), (6.4, 1, 0), (6.2, 1.35, 0)]])
bm.verts.new((6, 3, 0))
a = bm.verts.new((6, 4, 0)); b = bm.verts.new((6, 4.4, 0)); bm.edges.new((a, b))
bm.verts.ensure_lookup_table()
tip = bm.verts[0]
w1 = bm.verts.new(tip.co + Vector((0, 0, 1.2)))
w2 = bm.verts.new(tip.co + Vector((0, 0, 2.4)))
bm.edges.new((tip, w1)); bm.edges.new((w1, w2))
bm.to_mesh(me); bm.free()

obj = bpy.data.objects.new("StrayTest", me)
bpy.context.scene.collection.objects.link(obj)
md = obj.modifiers.new(NAME, "NODES"); md.node_group = ng

PASSES = ["Loose Vertices", "Loose Edges", "Loose Faces",
          "Loose Triangles", "Small Islands"]

def setp(**kw):
    for k, v in kw.items(): md[ids[k]] = v
    obj.update_tag()

def counts():
    dg = bpy.context.evaluated_depsgraph_get()
    m = obj.evaluated_get(dg).data
    return len(m.vertices), len(m.edges), len(m.polygons)

def stray(*on, **extra):
    kw = {p: (p in on) for p in PASSES}
    kw.update(extra)
    setp(**kw)

# main delete disabled so the stray stage is measured in isolation
setp(**{"Selection Group": False,
        "Min Vertex Count": 5, "Relative Size": 0.02,
        "Absolute Size": 0.0})

stray()                                              ; raw    = counts()
stray(*PASSES)                                       ; full   = counts()
stray("Loose Faces")                                 ; lf     = counts()
stray("Loose Triangles")                             ; lt     = counts()
stray("Loose Faces", "Loose Triangles")              ; lft    = counts()
stray("Small Islands",
      **{"Min Vertex Count": 0, "Relative Size": 0.0}); si_off = counts()
stray()                                              ; off    = counts()

# regression: the original selection delete still deletes everything selected
setp(**{"Selection Group": True})                    ; delall = counts()
setp(**{"Selection Group": True, "Invert Selection": True}); inv = counts()

print("RESULT every pass off (identity)    V/E/F:", raw)
print("RESULT stray full clean             V/E/F:", full)
print("RESULT loose faces only             V/E/F:", lf)
print("RESULT loose triangles only         V/E/F:", lt)
print("RESULT loose faces + triangles      V/E/F:", lft)
print("RESULT islands, min0/rel0           V/E/F:", si_off)
print("RESULT passes toggled back off      V/E/F:", off)
print("RESULT selection delete all (point) V/E/F:", delall)
print("RESULT selection delete inverted    V/E/F:", inv)

fails = []
def chk(label, got, want):
    if got != want: fails.append(f"{label}: got {got} want {want}")
chk("raw verts", raw[0], 62)
chk("all passes off is identity", raw, (62, 142, 88))
chk("passes toggled back off is identity", off, raw)
chk("full clean = sphere only", full[0], 42)
chk("loose faces only removes quad+tri", lf[0], 55)
chk("loose tris only removes tri", lt[0], 59)
chk("loose faces+tris removes quad+tri", lft[0], 55)
chk("selection delete all", delall[0], 0)
chk("inverted selection keeps all", inv, raw)
print("VERDICT:", "PASS" if not fails else "FAIL -> " + " | ".join(fails))
sys.stdout.flush(); os._exit(1 if fails else 0)
