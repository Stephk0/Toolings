"""Add an 'Invert Selection' bool to every ST3E modifier that gates on a Selection.

Pattern: Selection XOR Invert Selection -> every consumer of Selection.
XOR is the correct semantics: off => passthrough (byte-identical output),
on => the complement of whatever the Selection field evaluates to.
"""
import bpy, sys, os

GEO = r"D:\Stephko_Tooling\Toolings\Blender\Geonodes"

DESC = ("Invert the Selection, so the modifier acts everywhere the Selection is "
        "NOT set. Has no effect while Selection is left at its default")

TARGETS = [
    # (file, node group, selection socket name)
    ("GN_Inflate.blend",               "GN_Inflate",              "Selection"),
    ("GN_Twist.blend",                 "GN_Twist",                "Selection"),
    ("GN_Taper.blend",                 "GN_Taper",                "Selection"),
    ("GN_Stretch.blend",               "GN_Stretch",              "Selection"),
    ("GN_Bend.blend",                  "GN_Bend",                 "Selection"),
    ("GN_Wave.blend",                  "GN_Wave",                 "Selection"),
    ("GN_Cast.blend",                  "GN_Cast",                 "Selection"),
    ("GN_Smooth.blend",                "GN_Smooth",               "Selection"),
    ("GN_Displace.blend",              "GN_Displace",             "Selection"),
    ("GN_RandomizePosition.blend",     "GN_RandomizePosition",    "Selection"),
    ("GN_RandomizeMeshElements.blend", "GN_RandomizeMeshElements","Selection"),
    ("GN_ShearGeometry.blend",         "GN_ShearGeometry",        "Selection"),
    ("GN_FlattenByBoundary.blend",     "GN_FlattenByBoundary",    "Selection"),
    ("GN_SimpleTransform.blend",       "GN_SimpleTransformMesh",  "Selection"),
    ("GN_Triangulate.blend",           "GN_Triangulate",          "Selection"),
    ("GN_PointsToSpheres.blend",       "GN_PointsToSpheres",      "Selection"),
    ("GN_Scatter.blend",               "GN_Scatter",              "Selection"),
    ("GN_Mosaic.blend",                "GN_Mosaic",               "Selection"),
    ("GN_FlipFaces.blend",             "GN_FlipFaces",            "Selection"),
    ("GN_SetMaterial.blend",           "GN_SetMaterial",          "Selection"),
    ("GN_Weld.blend",                  "GN_Weld",                 "Selection"),
    ("GN_ExtrudeSelection.blend",      "GN_ExtrudeFace",          "Selection"),
    ("GN_Mirror_Groupable.blend",      "GN_MirrorGroup",          "Selection"),
    ("GN_AmbientOcclusion.blend",      "GN_AmbientOcclusion",     "Selection"),
    ("GN_VertexDataComposer.blend",    "GN_VertexDataComposer",   "Selection"),
    ("GN_AttributeFunctions_4.5.blend","GN_AttributeTransfer",    "Selected Groups"),
]

NEW_NAME = "Invert Selection"


def demo_objects(ng):
    out = []
    for o in bpy.data.objects:
        for m in o.modifiers:
            if m.type == 'NODES' and m.node_group == ng:
                out.append((o, m))
    return out


def snapshot(obj):
    obj.update_tag(); bpy.context.view_layer.update()
    dg = bpy.context.evaluated_depsgraph_get()
    ev = obj.evaluated_get(dg)
    try:
        me = ev.to_mesh()
    except RuntimeError:
        return None
    if me is None:
        return None
    sig = (len(me.vertices), len(me.edges), len(me.polygons),
           tuple(round(c, 5) for v in me.vertices for c in v.co))
    ev.to_mesh_clear()
    return sig


def root_index(item):
    p = item.parent
    return list(p.interface_items).index(item)


def patch(fname, gname, selname, dry=False):
    path = os.path.join(GEO, fname)
    bpy.ops.wm.open_mainfile(filepath=path, load_ui=False)
    ng = bpy.data.node_groups[gname]

    names = {it.name for it in ng.interface.items_tree
             if it.item_type == 'SOCKET' and it.in_out == 'INPUT'}
    if NEW_NAME in names:
        return f"SKIP  {fname}/{gname}: already has {NEW_NAME!r}"

    sel = next((it for it in ng.interface.items_tree
                if it.item_type == 'SOCKET' and it.in_out == 'INPUT'
                and it.name == selname), None)
    if sel is None:
        return f"FAIL  {fname}/{gname}: no input socket {selname!r}"

    objs = demo_objects(ng)
    before = {o.name: snapshot(o) for o, _ in objs}

    # --- collect every consumer of the Selection output, across all Group Input nodes
    consumers, gis = [], []
    for n in ng.nodes:
        if n.bl_idname != "NodeGroupInput":
            continue
        for out in n.outputs:
            if out.name != selname:
                continue
            if out.links:
                gis.append(n)
            for l in out.links:
                consumers.append(l.to_socket)
    if not consumers:
        return f"FAIL  {fname}/{gname}: {selname!r} feeds nothing"

    # --- interface: new bool right after the Selection socket, same panel
    parent = sel.parent
    new = ng.interface.new_socket(NEW_NAME, in_out='INPUT',
                                  socket_type='NodeSocketBool', parent=parent)
    new.description = DESC
    new.default_value = False
    ng.interface.move_to_parent(new, parent, root_index(sel) + 1)
    ng.interface.active_index = 0

    # --- graph: Selection XOR Invert Selection, in its own labeled frame
    reals = [n for n in ng.nodes if n.bl_idname != "NodeFrame"]
    min_x = min(n.location.x for n in reals)
    max_y = max(n.location.y for n in reals)

    frame = ng.nodes.new("NodeFrame")
    frame.label = "Selection Gate  (Selection XOR Invert Selection)"
    frame.location = (0, 0)          # keeps child .location absolute
    frame.label_size = 20

    gi = ng.nodes.new("NodeGroupInput")
    gi.parent = frame
    gi.location = (min_x - 700, max_y + 700)
    for o in gi.outputs:
        o.hide = o.name not in (selname, NEW_NAME)

    xor = ng.nodes.new("FunctionNodeBooleanMath")
    xor.operation = 'XOR'
    xor.label = "Selection XOR Invert"
    xor.parent = frame
    xor.location = (min_x - 400, max_y + 700)

    ng.links.new(gi.outputs[selname], xor.inputs[0])
    ng.links.new(gi.outputs[NEW_NAME], xor.inputs[1])
    for ts in consumers:
        ng.links.new(xor.outputs[0], ts)

    # --- verify: default off must be byte-identical
    after = {o.name: snapshot(o) for o, _ in objs}
    changed = [k for k in before if before[k] != after[k]]
    if changed:
        return f"FAIL  {fname}/{gname}: geometry changed with Invert off: {changed}"

    # --- informational: does toggling it on actually do something?
    effect = "no demo object"
    if objs:
        o, m = objs[0]
        try:
            m[new.identifier] = True
            on = snapshot(o)
            m[new.identifier] = False
            effect = "effect" if on != after[o.name] else "NO-OP (selection default covers all)"
        except Exception as e:
            effect = f"toggle failed: {e}"

    if dry:
        return f"DRY   {fname}/{gname}: ok, {len(consumers)} consumer(s), {effect}"
    bpy.ops.wm.save_mainfile(filepath=path, compress=True)
    return f"OK    {fname}/{gname}: +{NEW_NAME}, {len(consumers)} consumer(s), {effect}"


if __name__ == "__main__":
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    dry = "--dry" in argv
    only = [a for a in argv if not a.startswith("--")]
    results = []
    for f, g, s in TARGETS:
        if only and f not in only and g not in only:
            continue
        try:
            results.append(patch(f, g, s, dry=dry))
        except Exception as e:
            import traceback; traceback.print_exc()
            results.append(f"FAIL  {f}/{g}: {e}")
    print("\n#### RESULTS ####")
    for r in results:
        print(r)
