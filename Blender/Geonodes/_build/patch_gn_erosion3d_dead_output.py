"""Remove the dead duplicate `Geometry` OUTPUT on GN_Erosion_3D (R9)."""
import bpy, os

GEO = r"D:\Stephko_Tooling\Toolings\Blender\Geonodes"
path = os.path.join(GEO, "GN_Erosion_3D.blend")
bpy.ops.wm.open_mainfile(filepath=path, load_ui=False)
ng = bpy.data.node_groups["GN_Erosion_3D"]


def sig():
    out = {}
    for o in bpy.data.objects:
        for m in o.modifiers:
            if m.type == 'NODES' and m.node_group == ng:
                o.update_tag()
                bpy.context.view_layer.update()
                dg = bpy.context.evaluated_depsgraph_get()
                ev = o.evaluated_get(dg)
                me = ev.to_mesh()
                out[o.name] = (len(me.vertices), len(me.polygons),
                               tuple(round(c, 5) for v in me.vertices for c in v.co))
                ev.to_mesh_clear()
    return out


before = sig()
it = next(i for i in ng.interface.items_tree
          if i.item_type == 'SOCKET' and i.in_out == 'OUTPUT' and i.identifier == "Socket_24")
linked = any(s.identifier == "Socket_24" and s.links
             for n in ng.nodes if n.bl_idname == "NodeGroupOutput" for s in n.inputs)
print("removing %r [%s], linked=%s" % (it.name, it.identifier, linked))
assert not linked, "socket is wired -- not removing"
ng.interface.remove(it)

after = sig()
print("geometry unchanged:", before == after)
if before == after:
    bpy.ops.wm.save_mainfile(filepath=path, compress=True)
    print("SAVED GN_Erosion_3D.blend")
else:
    print("NOT SAVED -- geometry changed")
