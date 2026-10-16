"""Verify GNG_SelectionGate on a factory-startup grid (headless).

blender --background --factory-startup --python verify_gng_selection_gate.py

Selects one vertex / face / curve point in the middle by index and checks the
element counts the gate returns for Invert and Grow / Shrink against the
expected ring counts.
"""
import bpy, os, sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(r"D:\Stephko_Tooling\Toolings\Blender\Addons\LLMGeonodePipeline")
import gng_selection_gate as gate

gng = gate.ensure(force=True)


def harness(domain, seed_index, source):
    """Geometry -> Store Named Attribute 'gate' (domain) <- gate(index == seed)."""
    ng = bpy.data.node_groups.new("T_" + domain + source, "GeometryNodeTree")
    ng.interface.new_socket("Geometry", in_out='OUTPUT', socket_type='NodeSocketGeometry')
    for name, t in (("Select All", 'NodeSocketBool'), ("Invert", 'NodeSocketBool'),
                    ("Grow", 'NodeSocketInt')):
        ng.interface.new_socket(name, in_out='INPUT', socket_type=t)
    n, l = ng.nodes, ng.links
    gi, go = n.new("NodeGroupInput"), n.new("NodeGroupOutput")
    if source == "mesh":
        geo = n.new("GeometryNodeMeshGrid")
        geo.inputs["Vertices X"].default_value = 21
        geo.inputs["Vertices Y"].default_value = 21
        smi = n.new("GeometryNodeSetMaterialIndex")
        smi.inputs["Material Index"].default_value = 1
        fidx, lt = n.new("GeometryNodeInputIndex"), n.new("FunctionNodeCompare")
        lt.data_type, lt.operation = 'INT', 'LESS_THAN'
        lt.inputs[3].default_value = 200
        l.new(fidx.outputs[0], lt.inputs[2]); l.new(lt.outputs[0], smi.inputs["Selection"])
        l.new(geo.outputs["Mesh"], smi.inputs["Geometry"])
        out = smi.outputs[0]
    else:
        geo = n.new("GeometryNodeCurvePrimitiveLine")
        res = n.new("GeometryNodeResampleCurve")
        res.inputs["Count"].default_value = 21
        l.new(geo.outputs[0], res.inputs[0])
        out = res.outputs[0]
    idx, cmp = n.new("GeometryNodeInputIndex"), n.new("FunctionNodeCompare")
    cmp.data_type, cmp.operation = 'INT', 'EQUAL'
    cmp.inputs[3].default_value = seed_index
    l.new(idx.outputs[0], cmp.inputs[2])
    orr = n.new("FunctionNodeBooleanMath"); orr.operation = 'OR'
    l.new(cmp.outputs[0], orr.inputs[0]); l.new(gi.outputs["Select All"], orr.inputs[1])
    g = n.new("GeometryNodeGroup"); g.node_tree = gng
    l.new(orr.outputs[0], g.inputs[gate.SEL])
    l.new(gi.outputs["Invert"], g.inputs[gate.INV])
    l.new(gi.outputs["Grow"], g.inputs[gate.GROW])
    g.name = "GATE"
    g.inputs[gate.MAT_ID].default_value = 1
    st = n.new("GeometryNodeStoreNamedAttribute")
    st.data_type, st.domain = 'BOOLEAN', domain
    st.inputs["Name"].default_value = "gate"
    l.new(out, st.inputs["Geometry"]); l.new(g.outputs[0], st.inputs["Value"])
    if source == "mesh":
        l.new(st.outputs[0], go.inputs[0])
    else:   # curve points -> mesh verts so the result reads back through to_mesh()
        c2m = n.new("GeometryNodeCurveToMesh")
        l.new(st.outputs[0], c2m.inputs[0]); l.new(c2m.outputs[0], go.inputs[0])
    return ng


def count(obj, ng, domain, select_all=False, invert=False, grow=0, mat=None):
    gn = ng.nodes["GATE"]
    gn.inputs[gate.USE_MAT].default_value = mat is not None
    gn.inputs[gate.MAT_MODE].default_value = mat or gate.MODES[0]
    m = obj.modifiers[0]
    m.node_group = ng
    ids = {it.name: it.identifier for it in ng.interface.items_tree
           if it.item_type == 'SOCKET' and it.in_out == 'INPUT'}
    m[ids["Select All"]], m[ids["Invert"]], m[ids["Grow"]] = select_all, invert, grow
    obj.update_tag(); bpy.context.view_layer.update()
    ev = obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
    me = ev.to_mesh()
    n = sum(1 for d in me.attributes["gate"].data if d.value)
    ev.to_mesh_clear()
    return n


fails = []


def check(label, got, want):
    ok = got == want
    print("  %-46s got %5d  want %5d  %s" % (label, got, want, "ok" if ok else "FAIL"))
    if not ok:
        fails.append(label)


bpy.ops.mesh.primitive_plane_add()
mesh_obj = bpy.context.active_object
mesh_obj.modifiers.new("T", 'NODES')

# 21x21 grid, centre vertex 220 / centre face 210 (20x20 faces).
P = harness('POINT', 220, "mesh")
print("POINT domain (21x21 verts)")
check("seed", count(mesh_obj, P, 'POINT'), 1)
check("invert", count(mesh_obj, P, 'POINT', invert=True), 440)
check("grow 1  (edge neighbours = diamond)", count(mesh_obj, P, 'POINT', grow=1), 5)
check("grow 2", count(mesh_obj, P, 'POINT', grow=2), 13)
check("grow 50 (fills, no underflow)", count(mesh_obj, P, 'POINT', grow=50), 441)
check("grow 1 then shrink is -1 of grown? (shrink 1 of seed)",
      count(mesh_obj, P, 'POINT', grow=-1), 0)
check("invert + shrink 1  (hole grows by a ring)",
      count(mesh_obj, P, 'POINT', invert=True, grow=-1), 441 - 5)
check("select all + shrink 3 (boundary never shrinks)",
      count(mesh_obj, P, 'POINT', select_all=True, grow=-3), 441)
check("select all + invert", count(mesh_obj, P, 'POINT', select_all=True, invert=True), 0)

print("POINT + Material ID 1 (lower half: 231 verts touch it; seed 220 is on its edge)")
check("Add", count(mesh_obj, P, 'POINT', mat="Add"), 231)
check("Subtract  (seed is on the material)", count(mesh_obj, P, 'POINT', mat="Subtract"), 0)
check("Intersect", count(mesh_obj, P, 'POINT', mat="Intersect"), 1)
check("Material Minus Selection", count(mesh_obj, P, 'POINT', mat="Material Minus Selection"), 230)
check("select all + Subtract", count(mesh_obj, P, 'POINT', select_all=True, mat="Subtract"), 210)
check("Add + invert  (invert after combine)", count(mesh_obj, P, 'POINT', invert=True, mat="Add"), 210)
check("Add + grow 1  (grow after combine)", count(mesh_obj, P, 'POINT', grow=1, mat="Add"), 252)

F = harness('FACE', 210, "mesh")
print("FACE domain (20x20 faces)")
check("seed", count(mesh_obj, F, 'FACE'), 1)
check("grow 1  (edge-adjacent faces)", count(mesh_obj, F, 'FACE', grow=1), 5)
check("grow 2", count(mesh_obj, F, 'FACE', grow=2), 13)
check("invert + shrink 1", count(mesh_obj, F, 'FACE', invert=True, grow=-1), 400 - 5)
check("Add  (seed face 210 is not on material)", count(mesh_obj, F, 'FACE', mat="Add"), 201)
check("Subtract", count(mesh_obj, F, 'FACE', mat="Subtract"), 1)
check("Intersect", count(mesh_obj, F, 'FACE', mat="Intersect"), 0)
check("Material Minus Selection", count(mesh_obj, F, 'FACE', mat="Material Minus Selection"), 200)

bpy.ops.curve.primitive_bezier_curve_add()
curve_obj = bpy.context.active_object
curve_obj.modifiers.new("T", 'NODES')
C = harness('POINT', 10, "curve")
print("CURVE points (21)")
check("seed", count(curve_obj, C, 'POINT'), 1)
check("grow 3", count(curve_obj, C, 'POINT', grow=3), 7)
check("invert + shrink 2", count(curve_obj, C, 'POINT', invert=True, grow=-2), 21 - 5)

print("\nRESULT:", "ALL PASS" if not fails else "FAILED: %s" % fails)

import layout_audit
blocking = layout_audit.print_report(layout_audit.audit(gng))
sys.stdout.flush()
os._exit(1 if (fails or blocking) else 0)
