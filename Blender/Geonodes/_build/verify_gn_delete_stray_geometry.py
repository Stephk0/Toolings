"""Verify GN_DeleteStrayGeometry evaluated behaviour under several settings."""
import bpy, sys, os
PATH = r"D:\Stephko_Tooling\Toolings\Blender\Geonodes\GN_DeleteStrayGeometry.blend"
bpy.ops.wm.open_mainfile(filepath=PATH)
NAME = "GN_DeleteStrayGeometry"
ng  = bpy.data.node_groups[NAME]
obj = next(o for o in bpy.data.objects if any(m.type=='NODES' and m.node_group==ng for m in o.modifiers))
md  = next(m for m in obj.modifiers if m.node_group==ng)
ids = {it.name: it.identifier for it in ng.interface.items_tree
       if getattr(it,'item_type','')=='SOCKET' and it.in_out=='INPUT'}

ALL_PASSES = ["Delete Loose Vertices","Delete Loose Edges","Delete Loose Faces",
              "Delete Loose Triangles","Delete Small Islands"]
def setp(**kw):
    for k,v in kw.items(): md[ids[k]] = v
    obj.update_tag()
def only(*on, **extra):
    kw = {p:(p in on) for p in ALL_PASSES}; kw.update(extra); setp(**kw)
def counts():
    dg = bpy.context.evaluated_depsgraph_get()
    m  = obj.evaluated_get(dg).data
    return len(m.vertices), len(m.edges), len(m.polygons)

setp(Selection=True, **{"Min Vertex Count":5,"Relative Size":0.02,"Absolute Size":0.0})

only()                                             ; base = counts()
only(*ALL_PASSES)                                  ; full = counts()
only("Delete Loose Faces")                         ; lf   = counts()
only("Delete Loose Triangles")                     ; lt   = counts()
only("Delete Loose Faces","Delete Loose Triangles"); lft  = counts()
only("Delete Small Islands", **{"Min Vertex Count":0,"Relative Size":0.0}); si_off = counts()
only(*ALL_PASSES); setp(Selection=False)           ; sel0 = counts()

print("RESULT base(all off)        V/E/F:", base)
print("RESULT full clean           V/E/F:", full)
print("RESULT loose faces only     V/E/F:", lf)
print("RESULT loose triangles only V/E/F:", lt)
print("RESULT loose faces+tris     V/E/F:", lft)
print("RESULT islands off(min0rel0)V/E/F:", si_off)
print("RESULT selection=off        V/E/F:", sel0)
print("EXPECT base=62 (42 sphere +8 cube +4 quad +3 tri +1 lv +2 le +2 wire)")
print("EXPECT full=42 (sphere only); selection off == base")
print("EXPECT loose faces only removes quad(4)+tri(3)=7 -> 55 ; keeps closed cube")
print("EXPECT loose triangles only removes tri(3) only -> 59")
sys.stdout.flush(); os._exit(0)
