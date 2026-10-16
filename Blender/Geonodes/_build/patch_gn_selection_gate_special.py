"""Second rollout of GNG_SelectionGate: the modifiers whose selection was not a plain XOR.

  * GN_ExtrudeFace  -- already on the gate (Invert only). Adds Grow / Shrink Selection and
                       renames its own 'Selection Expand / Contract' to
                       'Legacy Selection Expand / Contract' (rename keeps the identifier, so
                       older files keep their value).
  * GN_SetAttribute -- invert was Switch(Selection, NOT Selection); replaced by the gate.
                       Its 'Expand / Shrink' (grows the COMBINED noise/topology/axis result,
                       later in the graph) stays.
  * GN_Delete       -- invert was Switch(src, NOT src) after the Selection Group / Material ID
                       menu; the gate takes that menu result as its Selection.

Same gates as patch_gn_use_selection_gate_group.py: every demo object must evaluate
identically (positions AND attributes) at Grow 0, and no blocking layout rule may get worse.

blender --background --factory-startup --python patch_gn_selection_gate_special.py -- [--dry]
"""
import bpy, os, sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import gng_selection_gate as gate
from patch_gn_use_selection_gate_group import (GEO, NEW_FRAME, GROW_NAME, GROW_DESC,
                                               instances, sig, blocking)

LEGACY_OLD = "Selection Expand / Contract"
LEGACY_NEW = "Legacy Selection Expand / Contract"
LEGACY_DESC = ("Legacy: kept so files saved before the shared selection gate still load "
               "their value. Use Grow / Shrink Selection instead. ")


def item(ng, name):
    return next((i for i in ng.interface.items_tree if i.item_type == 'SOCKET'
                 and i.in_out == 'INPUT' and i.name == name), None)


def add_grow(ng, after_name):
    after = item(ng, after_name)
    parent = after.parent
    g = ng.interface.new_socket(GROW_NAME, in_out='INPUT', socket_type='NodeSocketInt',
                                parent=parent)
    g.default_value = 0
    g.min_value, g.max_value = -10000, 10000
    g.description = GROW_DESC
    if hasattr(g, "structure_type"):
        g.structure_type = 'SINGLE'
    ng.interface.move_to_parent(g, parent, list(parent.interface_items).index(after) + 1)
    ng.interface.active_index = 0
    for _, m in instances(ng):
        m[g.identifier] = 0
    return g


def gi_out(gi, name):
    out = gi.outputs[name]
    out.hide = False
    return out


def replace_switch_invert(ng, switch, sel_src, inv_src, gi):
    """Switch(inv, False=sel, True=NOT sel) -> GNG_SelectionGate(sel, inv, grow)."""
    consumers = [l.to_socket for l in switch.outputs[0].links]
    nots = [l.from_node for l in switch.inputs[2].links
            if l.from_node.bl_idname == "FunctionNodeBooleanMath" and l.from_node.operation == 'NOT']
    node = ng.nodes.new("GeometryNodeGroup")
    node.node_tree = gate.ensure()
    node.name = node.label = "Selection Gate"
    node.parent = switch.parent
    node.location = switch.location.copy()
    ng.links.new(sel_src, node.inputs[gate.SEL])
    ng.links.new(inv_src, node.inputs[gate.INV])
    ng.links.new(gi_out(gi, GROW_NAME), node.inputs[gate.GROW])
    for ts in consumers:
        ng.links.new(node.outputs[0], ts)
    ng.nodes.remove(switch)
    for n in nots:
        if not any(o.is_linked for o in n.outputs):
            ng.nodes.remove(n)
    return node


def invert_switch(ng, inv_name):
    """The BOOLEAN Switch whose Switch input is the Invert socket; returns (switch, gi)."""
    for n in ng.nodes:
        if n.bl_idname == "NodeGroupInput" and inv_name in n.outputs:
            for l in n.outputs[inv_name].links:
                s = l.to_node
                if s.bl_idname == "GeometryNodeSwitch" and s.input_type == 'BOOLEAN' \
                        and l.to_socket == s.inputs[0]:
                    return s, n
    return None, None


def extrude_face(ng):
    if item(ng, GROW_NAME):
        return "already has %s" % GROW_NAME
    legacy = item(ng, LEGACY_OLD)
    legacy.name = LEGACY_NEW
    if not legacy.description.startswith("Legacy"):
        legacy.description = LEGACY_DESC + legacy.description
    add_grow(ng, "Invert Selection")
    node = next(n for n in ng.nodes if n.bl_idname == "GeometryNodeGroup"
                and n.node_tree and n.node_tree.name == gate.NAME)
    gi = node.inputs[gate.SEL].links[0].from_node
    ng.links.new(gi_out(gi, GROW_NAME), node.inputs[gate.GROW])
    return "Grow wired, %r -> %r" % (LEGACY_OLD, LEGACY_NEW)


def set_attribute(ng):
    if item(ng, GROW_NAME):
        return "already has %s" % GROW_NAME
    sw, gi = invert_switch(ng, "Invert Selection")
    if sw is None:
        raise RuntimeError("no Invert Selection switch")
    sel_src = sw.inputs[1].links[0].from_socket          # False = Selection
    inv_src = sw.inputs[0].links[0].from_socket
    add_grow(ng, "Invert Selection")
    replace_switch_invert(ng, sw, sel_src, inv_src, gi)
    return "Switch(NOT) -> gate"


def delete(ng):
    if item(ng, GROW_NAME):
        return "already has %s" % GROW_NAME
    sw, gi = invert_switch(ng, "Invert Selection")
    if sw is None:
        raise RuntimeError("no Invert Selection switch")
    sel_src = sw.inputs[1].links[0].from_socket          # Index Switch (source menu)
    inv_src = sw.inputs[0].links[0].from_socket
    frame = sw.parent
    add_grow(ng, "Invert Selection")
    replace_switch_invert(ng, sw, sel_src, inv_src, gi)
    if frame is not None:
        frame.label = NEW_FRAME
    return "Switch(NOT) -> gate"


TARGETS = [
    ("GN_ExtrudeSelection.blend", "GN_ExtrudeFace", extrude_face),
    ("GN_AttributeFunctions_4.5.blend", "GN_SetAttribute", set_attribute),
    ("GN_Delete.blend", "GN_Delete", delete),
]


def run(fname, gname, fn, dry):
    path = os.path.join(GEO, fname)
    bpy.ops.wm.open_mainfile(filepath=path, load_ui=False)
    ng = bpy.data.node_groups[gname]
    inv_id = item(ng, "Invert Selection").identifier

    def sig_inverted():
        old = [(m, m[inv_id]) for _, m in instances(ng)]
        for m, _ in old:
            m[inv_id] = not m[inv_id]
        s = sig(ng)
        for m, v in old:
            m[inv_id] = v
        return s

    before, before_inv, audit_before = sig(ng), sig_inverted(), blocking(ng)
    msg = fn(ng)
    if msg.startswith("already"):
        return "SKIP  %s/%s: %s" % (fname, gname, msg)
    after, after_inv, audit_after = sig(ng), sig_inverted(), blocking(ng)
    for tag, b, a in (("", before, after), (" with Invert flipped", before_inv, after_inv)):
        if b != a:
            bad = [k for k in b if b[k] != a.get(k)]
            return "FAIL  %s/%s: result changed at Grow 0%s: %s" % (fname, gname, tag, bad)
    worse = {k: (audit_before[k], audit_after[k]) for k in audit_before
             if audit_after[k] > audit_before[k]}
    if worse:
        return "FAIL  %s/%s: layout regressions %s" % (fname, gname, worse)
    if dry:
        return "DRY   %s/%s: ok, %s, %d demo(s)" % (fname, gname, msg, len(instances(ng)))
    bpy.ops.wm.save_mainfile(filepath=path, compress=True)
    return "OK    %s/%s: %s, %d demo(s)" % (fname, gname, msg, len(instances(ng)))


if __name__ == "__main__":
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    dry = "--dry" in argv
    res = []
    for f, g, fn in TARGETS:
        try:
            res.append(run(f, g, fn, dry))
        except Exception as e:
            import traceback
            traceback.print_exc()
            res.append("FAIL  %s/%s: %s" % (f, g, e))
    print("\n#### SELECTION GATE SPECIAL ####")
    for r in res:
        print(r)
    sys.stdout.flush()
    os._exit(0)
