"""Fix typo'd / duplicate / placeholder interface socket names across the ST3E library.

Display names only -- socket IDENTIFIERS are untouched, so existing modifier
overrides keep working (R9: duplicates silently miswire by-name scripting).
"""
import bpy, os, sys, collections

GEO = r"D:\Stephko_Tooling\Toolings\Blender\Geonodes"

# file -> group -> {socket identifier (or __by_name__ map): new display name}
RENAMES = {
    "GN_ExtrudeSelection.blend": {
        "GN_ExtrudeFace": {
            "__by_name__": {
                "Select bv Material Index": "Select by Material Index",
                "Seperate Extrusion": "Separate Extrusion",
                "Extruded Face Material ID ": "Extruded Face Material ID",
                "Extruded Face Face Group Attribute ": "Extruded Face Face Group Attribute",
                "Outer Face Material ID ": "Outer Face Material ID",
                "Outer Face Face Group Attribute ": "Outer Face Face Group Attribute",
            }},
        "Inset Face": {"__by_name__": {"Reletive Offset": "Relative Offset"}},
    },
    "GN_AttributeFunctions_4.5.blend": {
        "GN_SetAttribute": {
            "__by_name__": {
                "XYZ/RGB Adjust Base ": "XYZ/RGB Adjust Base",
                "Expand / Shrink ": "Expand / Shrink",
                "Alpha Value to Set": "Alpha Value To Set",
            },
            "Socket_92": "Invert Noise Selection",
            "Socket_68": "Use Object",
            "Socket_107": "Alpha Blur Iterations",
            "Socket_108": "Alpha Blur Weight",
        },
        "GNG_StoreAttributeOnDomain": {"__by_name__": {"MixToAlpha": "Mix To Alpha"}},
    },
    "GN_RandomizePosition.blend": {
        "Fix Pivot": {"__by_name__": {"Primitiv": "Primitive"}},
    },
    "GN_SplitByAttribute.blend": {
        "GNG_Boundary": {"__by_name_out__": {"Boundry Edges": "Boundary Edges"}},
    },
    "GN_CollectionInstancer.blend": {
        "GN_CollectionInstancerModel": {"Socket_25": "Scale Uniform", "Socket_28": "Scale Per Axis"},
        "Randomize Transforms": {"Socket_8": "Scale Uniform", "Socket_4": "Scale Per Axis"},
    },
    "GN_Mirror_Groupable.blend": {
        "GN_MirrorGroup": {
            "Socket_39": "Flip Delete Axis X", "Socket_37": "Delete Center Threshold X",
            "Socket_16": "U Scale X", "Socket_17": "V Scale X",
            "Socket_4": "U Shift X", "Socket_5": "V Shift X",
            "Socket_40": "Flip Delete Axis Y", "Socket_38": "Delete Center Threshold Y",
            "Socket_26": "U Scale Y", "Socket_27": "V Scale Y",
            "Socket_29": "U Shift Y", "Socket_28": "V Shift Y",
            "Socket_44": "Flip Delete Axis Z", "Socket_45": "Delete Center Threshold Z",
            "Socket_46": "U Scale Z", "Socket_47": "V Scale Z",
            "Socket_48": "U Shift Z", "Socket_49": "V Shift Z",
        },
    },
}

# dead placeholder sockets to remove (unconnected, name forbidden by the criteria)
REMOVE = {"GN_Solidify2.blend": {"GN_Solidfy2": ["Socket_13"]}}
# node-group datablock renames
GROUP_RENAMES = {"GN_Solidify2.blend": {"GN_Solidfy2": "GN_Solidify2"}}


def eval_sig(ng):
    out = {}
    for o in bpy.data.objects:
        for m in o.modifiers:
            if m.type != 'NODES' or m.node_group != ng:
                continue
            o.update_tag()
            bpy.context.view_layer.update()
            dg = bpy.context.evaluated_depsgraph_get()
            ev = o.evaluated_get(dg)
            me = ev.to_mesh()
            if me is not None:
                out[o.name] = (len(me.vertices), len(me.polygons),
                               tuple(round(c, 5) for v in me.vertices for c in v.co))
                ev.to_mesh_clear()
    return out


def run(dry=False):
    files = sorted(set(RENAMES) | set(REMOVE) | set(GROUP_RENAMES))
    log = []
    for fname in files:
        bpy.ops.wm.open_mainfile(filepath=os.path.join(GEO, fname), load_ui=False)
        touched = set(RENAMES.get(fname, {})) | set(REMOVE.get(fname, {})) | set(GROUP_RENAMES.get(fname, {}))
        before = {g: eval_sig(bpy.data.node_groups[g]) for g in touched}

        for gname, spec in RENAMES.get(fname, {}).items():
            ng = bpy.data.node_groups[gname]
            items = [i for i in ng.interface.items_tree if i.item_type == 'SOCKET']
            for key, new in spec.items():
                if key in ("__by_name__", "__by_name_out__"):
                    want = 'INPUT' if key == "__by_name__" else 'OUTPUT'
                    for old, nn in new.items():
                        hit = [i for i in items if i.in_out == want and i.name == old]
                        if not hit:
                            log.append("  MISS %s/%s: %s %r" % (fname, gname, want, old))
                            continue
                        for h in hit:
                            log.append("  ren  %s: %r -> %r" % (gname, old, nn))
                            h.name = nn
                else:
                    hit = [i for i in items if i.identifier == key and i.in_out == 'INPUT']
                    if not hit:
                        log.append("  MISS %s/%s: id %s" % (fname, gname, key))
                        continue
                    log.append("  ren  %s: %r [%s] -> %r" % (gname, hit[0].name, key, new))
                    hit[0].name = new

        for gname, ids in REMOVE.get(fname, {}).items():
            ng = bpy.data.node_groups[gname]
            for sid in ids:
                it = next((i for i in ng.interface.items_tree
                           if i.item_type == 'SOCKET' and i.identifier == sid), None)
                if it is None:
                    log.append("  MISS %s/%s: remove %s" % (fname, gname, sid))
                    continue
                used = any(o.identifier == sid and o.links
                           for n in ng.nodes if n.bl_idname == "NodeGroupInput"
                           for o in n.outputs)
                if used:
                    log.append("  KEPT %s/%s: %s is wired" % (fname, gname, sid))
                    continue
                log.append("  del  %s: dead socket %r [%s]" % (gname, it.name, sid))
                ng.interface.remove(it)

        for gname, new in GROUP_RENAMES.get(fname, {}).items():
            bpy.data.node_groups[gname].name = new
            log.append("  ren  group %r -> %r" % (gname, new))

        ok = True
        for g, sig in before.items():
            cur = bpy.data.node_groups[GROUP_RENAMES.get(fname, {}).get(g, g)]
            if eval_sig(cur) != sig:
                ok = False
                log.append("  FAIL %s/%s: geometry changed" % (fname, g))

        for g in touched:
            cur = bpy.data.node_groups[GROUP_RENAMES.get(fname, {}).get(g, g)]
            cnt = collections.Counter(i.name for i in cur.interface.items_tree
                                      if i.item_type == 'SOCKET' and i.in_out == 'INPUT')
            rest = {k: v for k, v in cnt.items() if v > 1}
            if rest:
                log.append("  R9   %s/%s: still duplicated %s" % (fname, cur.name, rest))

        if ok and not dry:
            bpy.ops.wm.save_mainfile()
            log.append("SAVED %s" % fname)
        else:
            log.append("%s %s" % ("DRY" if dry else "NOT-SAVED", fname))
    return log


if __name__ == "__main__":
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    out = run(dry="--dry" in argv)
    print("\n#### NAME FIXES ####")
    for l in out:
        print(l)
