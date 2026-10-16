"""Route every ST3E modifier's selection through the shared GNG_SelectionGate group.

Replaces the per-tool `Selection XOR Invert Selection` node (frame
"Selection Gate  (Selection XOR Invert Selection)", added by
patch_gn_add_invert_selection.py / patch_gn_add_selection_gate.py) with a
GNG_SelectionGate group node, and exposes the group's Grow / Shrink as a new
`Grow / Shrink Selection` int directly beneath `Invert Selection`.

Backward compatible: the new int defaults to 0 and Blender backfills existing
modifiers with 0, and the gate at 0 is an exact passthrough -- every demo object
must evaluate byte-identically, or the file is not saved.

blender --background --factory-startup --python patch_gn_use_selection_gate_group.py -- [--dry] [GN_X.blend ...]
"""
import bpy, os, sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(r"D:\Stephko_Tooling\Toolings\Blender\Addons\LLMGeonodePipeline")
import gng_selection_gate as gate
import layout_audit

GEO = r"D:\Stephko_Tooling\Toolings\Blender\Geonodes"
OLD_FRAME = "Selection Gate  (Selection XOR Invert Selection)"
NEW_FRAME = "Selection Gate  (GNG_SelectionGate)"
GROW_NAME = "Grow / Shrink Selection"
GROW_DESC = ("Grow the selection by this many rings of neighbouring elements; negative "
             "values shrink it. 0 leaves the selection unchanged")
# Tools that already ship their own grow control keep it; they still get the shared
# gate (Invert), just without a second, competing Grow / Shrink input.
OWN_GROW = {"GN_ExtrudeFace"}   # 'Selection Expand / Contract' (To Edge / To Face)

TARGETS = [
    ("GN_AmbientOcclusion.blend", "GN_AmbientOcclusion"),
    ("GN_AttributeFunctions_4.5.blend", "GN_AttributeTransfer"),
    ("GN_AutoSmooth.blend", "GN_AutoSmooth"),
    ("GN_Bend.blend", "GN_Bend"),
    ("GN_BoundingBox.blend", "GN_BoundingBox"),
    ("GN_Cast.blend", "GN_Cast"),
    ("GN_ConvexHull.blend", "GN_ConvexHull"),
    ("GN_CurveFromSurface.blend", "GN_CurveFromSurface"),
    ("GN_Displace.blend", "GN_Displace"),
    ("GN_DistributeObjectOnSurface.blend", "GN_DistributeObjectOnSurface"),
    ("GN_Erosion.blend", "GN_Erosion"),
    ("GN_Erosion_3D.blend", "GN_Erosion_3D"),
    ("GN_ExtrudeSelection.blend", "GN_ExtrudeFace"),
    ("GN_FlattenByBoundary.blend", "GN_FlattenByBoundary"),
    ("GN_FlipFaces.blend", "GN_FlipFaces"),
    ("GN_Inflate.blend", "GN_Inflate"),
    ("GN_Mirror_Groupable.blend", "GN_MirrorGroup"),
    ("GN_Mosaic.blend", "GN_Mosaic"),
    ("GN_NoiseDisplace.blend", "GN_NoiseDisplace"),
    ("GN_PointsToSpheres.blend", "GN_PointsToSpheres"),
    ("GN_QuadCap.blend", "GN_QuadCap"),
    ("GN_RandomDistribute.blend", "GN_RandomDistribute"),
    ("GN_RandomizeMeshElements.blend", "GN_RandomizeMeshElements"),
    ("GN_RandomizePosition.blend", "GN_RandomizePosition"),
    ("GN_Scatter.blend", "GN_Scatter"),
    ("GN_SetMaterial.blend", "GN_SetMaterial"),
    ("GN_ShearGeometry.blend", "GN_ShearGeometry"),
    ("GN_SimpleTransform.blend", "GN_SimpleTransformMesh"),
    ("GN_Smooth.blend", "GN_Smooth"),
    ("GN_Stretch.blend", "GN_Stretch"),
    ("GN_Taper.blend", "GN_Taper"),
    ("GN_Triangulate.blend", "GN_Triangulate"),
    ("GN_Twist.blend", "GN_Twist"),
    ("GN_VertexDataComposer.blend", "GN_VertexDataComposer"),
    ("GN_VoronoiDisplace.blend", "GN_VoronoiDisplace"),
    ("GN_Wave.blend", "GN_Wave"),
    ("GN_Weld.blend", "GN_Weld"),
    ("GN_Wireframe.blend", "GN_Wireframe"),
]


def instances(ng):
    return [(o, m) for o in bpy.data.objects for m in o.modifiers
            if m.type == 'NODES' and m.node_group == ng]


def sig(ng):
    out = {}
    for o, _ in instances(ng):
        o.update_tag()
        bpy.context.view_layer.update()
        ev = o.evaluated_get(bpy.context.evaluated_depsgraph_get())
        try:
            me = ev.to_mesh()
        except RuntimeError:
            me = None
        if me is None:
            out[o.name] = None
            continue
        attrs = []
        for a in sorted(me.attributes, key=lambda a: (a.name, a.domain)):
            if a.name.startswith("."):
                continue
            prop = next((p for p in ("value", "vector", "color") if len(a.data) and hasattr(a.data[0], p)), None)
            vals = tuple(round(float(x), 5) if isinstance(x, float) else x
                         for d in a.data for x in (lambda v: v if hasattr(v, "__len__") and not isinstance(v, str) else (v,))(getattr(d, prop))) if prop else ()
            attrs.append((a.name, a.domain, a.data_type, vals))
        out[o.name] = (len(me.vertices), len(me.edges), len(me.polygons),
                       tuple(round(c, 5) for v in me.vertices for c in v.co), tuple(attrs))
        ev.to_mesh_clear()
    return out


def blocking(ng):
    rep = layout_audit.audit(ng)
    return {k: rep[k].get("count", len(rep[k].get("overlaps", rep[k].get("inside", []))))
            for k in layout_audit.BLOCKING}


def patch(fname, gname, dry=False):
    path = os.path.join(GEO, fname)
    bpy.ops.wm.open_mainfile(filepath=path, load_ui=False)
    ng = bpy.data.node_groups[gname]

    xor = next((n for n in ng.nodes if n.bl_idname == "FunctionNodeBooleanMath"
                and n.operation == 'XOR' and n.parent and n.parent.label == OLD_FRAME), None)
    if xor is None:
        if any(n.bl_idname == "GeometryNodeGroup" and n.node_tree
               and n.node_tree.name == gate.NAME for n in ng.nodes):
            return "SKIP  %s/%s: already on %s" % (fname, gname, gate.NAME)
        return "FAIL  %s/%s: no XOR gate in %r" % (fname, gname, OLD_FRAME)

    sel_link, inv_link = xor.inputs[0].links[0], xor.inputs[1].links[0]
    gi = sel_link.from_node
    if gi.bl_idname != "NodeGroupInput" or inv_link.from_node != gi:
        return "FAIL  %s/%s: gate inputs are not one Group Input" % (fname, gname)
    sel_name, inv_name = sel_link.from_socket.name, inv_link.from_socket.name
    consumers = [l.to_socket for l in xor.outputs[0].links]

    before = sig(ng)
    audit_before = blocking(ng)

    # --- interface: Grow / Shrink Selection right under Invert Selection --------
    grow_item = None
    if gname not in OWN_GROW:
        inv_item = next(i for i in ng.interface.items_tree if i.item_type == 'SOCKET'
                        and i.in_out == 'INPUT' and i.name == inv_name)
        parent = inv_item.parent
        grow_item = ng.interface.new_socket(GROW_NAME, in_out='INPUT',
                                            socket_type='NodeSocketInt', parent=parent)
        grow_item.default_value = 0
        grow_item.min_value, grow_item.max_value = -10000, 10000
        grow_item.description = GROW_DESC
        if hasattr(grow_item, "structure_type"):
            grow_item.structure_type = 'SINGLE'
        ng.interface.move_to_parent(grow_item, parent,
                                    list(parent.interface_items).index(inv_item) + 1)
        ng.interface.active_index = 0
        for _, m in instances(ng):      # explicit, not relying on the zero backfill
            m[grow_item.identifier] = 0

    # --- graph: group node in place of the XOR -----------------------------------
    g = gate.ensure()
    node = ng.nodes.new("GeometryNodeGroup")
    node.node_tree = g
    node.name = node.label = "Selection Gate"
    node.parent = xor.parent
    node.location = xor.location.copy()
    node.width = xor.width
    xor.parent.label = NEW_FRAME

    ng.links.new(gi.outputs[sel_name], node.inputs[gate.SEL])
    ng.links.new(gi.outputs[inv_name], node.inputs[gate.INV])
    if grow_item is not None:
        out = gi.outputs[GROW_NAME]
        out.hide = False
        ng.links.new(out, node.inputs[gate.GROW])
    for ts in consumers:
        ng.links.new(node.outputs[0], ts)
    ng.nodes.remove(xor)

    after = sig(ng)
    if before != after:
        bad = [k for k in before if before[k] != after.get(k)]
        return "FAIL  %s/%s: geometry changed at Grow 0: %s" % (fname, gname, bad)

    audit_after = blocking(ng)
    worse = {k: (audit_before[k], audit_after[k]) for k in audit_before
             if audit_after[k] > audit_before[k]}
    note = " layout regressions %s" % worse if worse else ""

    # informational: does Grow do anything on the demo? (default Selection=True
    # selects all, so usually not -- the unit test covers the behaviour)
    if dry:
        return "DRY   %s/%s: ok, %d consumer(s)%s%s" % (
            fname, gname, len(consumers), "" if grow_item else " (no Grow: own control)", note)
    if worse:
        return "FAIL  %s/%s: not saved,%s" % (fname, gname, note)
    bpy.ops.wm.save_mainfile(filepath=path, compress=True)
    return "OK    %s/%s: gate group, %d consumer(s)%s" % (
        fname, gname, len(consumers), "" if grow_item else " (no Grow: own control)")


if __name__ == "__main__":
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    dry = "--dry" in argv
    only = [a for a in argv if not a.startswith("--")]
    res = []
    for f, g in TARGETS:
        if only and f not in only and g not in only:
            continue
        try:
            res.append(patch(f, g, dry=dry))
        except Exception as e:
            import traceback
            traceback.print_exc()
            res.append("FAIL  %s/%s: %s" % (f, g, e))
    print("\n#### SELECTION GATE GROUP ####")
    for r in res:
        print(r)
    sys.stdout.flush()
    os._exit(0)
