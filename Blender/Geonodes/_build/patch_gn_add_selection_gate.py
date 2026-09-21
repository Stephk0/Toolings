"""Give the remaining ST3E modifiers a Selection gate (default ON) + Invert Selection.

Selection defaults to True, so every file must evaluate byte-identically afterwards.
Two shapes:
  * WIRE  -- the operation node already exposes a free `Selection` input: feed it.
  * SPLIT -- the operation is whole-geometry (Convex Hull / Bounding Box): insert a
             Separate Geometry in front of it and drive its Selection.
"""
import bpy, os, sys

GEO = r"D:\Stephko_Tooling\Toolings\Blender\Geonodes"

SEL, INV = "Selection", "Invert Selection"
SEL_DESC = ("Limit the modifier to the selected elements. Bind a vertex group or "
            "attribute with the modifier's 'sets via attribute' toggle")
INV_DESC = ("Invert the Selection, so the modifier acts everywhere the Selection is "
            "NOT set. Has no effect while Selection is left at its default")

# (file, group, [(node name, input socket)], split_before or None)
TARGETS = [
    ("GN_AutoSmooth.blend",        "GN_AutoSmooth",        [("All Smooth", "Selection")], None),
    ("GN_NoiseDisplace.blend",     "GN_NoiseDisplace",     [("Set Position", "Selection")], None),
    ("GN_VoronoiDisplace.blend",   "GN_VoronoiDisplace",   [("Set Position", "Selection")], None),
    ("GN_Erosion.blend",           "GN_Erosion",           [("Set Position", "Selection")], None),
    ("GN_Erosion_3D.blend",        "GN_Erosion_3D",        [("Set Position", "Selection")], None),
    ("GN_Wireframe.blend",         "GN_Wireframe",         [("Edges -> Curve", "Selection")], None),
    ("GN_RandomDistribute.blend",  "GN_RandomDistribute",
     [("Distribute Points on Faces", "Selection")], None),
    ("GN_ConvexHull.blend",        "GN_ConvexHull",        [], ("Convex Hull", "Geometry")),
    ("GN_BoundingBox.blend",       "GN_BoundingBox",       [], ("Bounding Box", "Geometry")),
]


def find_node(ng, name):
    for n in ng.nodes:
        if n.name == name or n.label == name:
            return n
    return None


def sig(ng):
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
            if me is None:
                continue
            out[o.name] = (len(me.vertices), len(me.edges), len(me.polygons),
                           tuple(round(c, 5) for v in me.vertices for c in v.co))
            ev.to_mesh_clear()
    return out


def patch(fname, gname, wires, split, dry=False):
    path = os.path.join(GEO, fname)
    bpy.ops.wm.open_mainfile(filepath=path, load_ui=False)
    ng = bpy.data.node_groups[gname]

    names = {i.name for i in ng.interface.items_tree
             if i.item_type == 'SOCKET' and i.in_out == 'INPUT'}
    if SEL in names:
        return "SKIP  %s/%s: already has %r" % (fname, gname, SEL)

    before = sig(ng)

    geo = next(i for i in ng.interface.items_tree
               if i.item_type == 'SOCKET' and i.in_out == 'INPUT'
               and i.socket_type == 'NodeSocketGeometry')
    root = geo.parent
    base = list(root.interface_items).index(geo)

    s_sel = ng.interface.new_socket(SEL, in_out='INPUT', socket_type='NodeSocketBool', parent=root)
    s_sel.description, s_sel.default_value = SEL_DESC, True
    ng.interface.move_to_parent(s_sel, root, base + 1)
    s_inv = ng.interface.new_socket(INV, in_out='INPUT', socket_type='NodeSocketBool', parent=root)
    s_inv.description, s_inv.default_value = INV_DESC, False
    ng.interface.move_to_parent(s_inv, root, base + 2)
    ng.interface.active_index = 0

    # A new group input backfills EXISTING modifiers with type-zero, not the socket
    # default -- so the demo instances in this file must be set explicitly or they
    # would evaluate with Selection = False. (Same applies to any scene saved before
    # this change; that is a documented migration step, not something we can fix here.)
    for o in bpy.data.objects:
        for m in o.modifiers:
            if m.type == 'NODES' and m.node_group == ng:
                m[s_sel.identifier] = True
                m[s_inv.identifier] = False

    reals = [n for n in ng.nodes if n.bl_idname != "NodeFrame"]
    min_x = min(n.location.x for n in reals)
    max_y = max(n.location.y for n in reals)

    frame = ng.nodes.new("NodeFrame")
    frame.label = "Selection Gate  (Selection XOR Invert Selection)"
    frame.location = (0, 0)
    frame.label_size = 20

    gi = ng.nodes.new("NodeGroupInput")
    gi.parent = frame
    gi.location = (min_x - 700, max_y + 700)
    for o in gi.outputs:
        o.hide = o.name not in (SEL, INV)

    xor = ng.nodes.new("FunctionNodeBooleanMath")
    xor.operation = 'XOR'
    xor.label = "Selection XOR Invert"
    xor.parent = frame
    xor.location = (min_x - 400, max_y + 700)
    ng.links.new(gi.outputs[SEL], xor.inputs[0])
    ng.links.new(gi.outputs[INV], xor.inputs[1])

    targets = []
    for nname, sname in wires:
        n = find_node(ng, nname)
        if n is None:
            return "FAIL  %s/%s: no node %r" % (fname, gname, nname)
        if sname not in n.inputs:
            return "FAIL  %s/%s: %r has no %r input" % (fname, gname, nname, sname)
        targets.append(n.inputs[sname])

    sep_note = ""
    if split:
        nname, gsock = split
        op = find_node(ng, nname)
        if op is None:
            return "FAIL  %s/%s: no node %r" % (fname, gname, nname)
        src = op.inputs[gsock].links[0].from_socket
        sep = ng.nodes.new("GeometryNodeSeparateGeometry")
        sep.domain = 'POINT'
        sep.label = "Keep Selected"
        sep.parent = frame
        sep.location = (min_x - 200, max_y + 700)
        ng.links.new(src, sep.inputs["Geometry"])
        ng.links.new(sep.outputs["Selection"], op.inputs[gsock])
        targets.append(sep.inputs["Selection"])
        sep_note = " +SeparateGeometry"

    for ts in targets:
        ng.links.new(xor.outputs[0], ts)

    after = sig(ng)
    if before != after:
        return "FAIL  %s/%s: geometry changed with Selection at its True default" % (fname, gname)

    if dry:
        return "DRY   %s/%s: ok, %d target(s)%s" % (fname, gname, len(targets), sep_note)
    bpy.ops.wm.save_mainfile(filepath=path, compress=True)
    return "OK    %s/%s: +%s/+%s, %d target(s)%s" % (fname, gname, SEL, INV, len(targets), sep_note)


if __name__ == "__main__":
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    dry = "--dry" in argv
    only = [a for a in argv if not a.startswith("--")]
    res = []
    for f, g, w, s in TARGETS:
        if only and f not in only:
            continue
        try:
            res.append(patch(f, g, w, s, dry=dry))
        except Exception as e:
            import traceback
            traceback.print_exc()
            res.append("FAIL  %s/%s: %s" % (f, g, e))
    print("\n#### SELECTION GATE ####")
    for r in res:
        print(r)
