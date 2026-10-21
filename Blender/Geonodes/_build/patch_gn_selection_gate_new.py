"""Put GNG_SelectionGate on the modifiers that were still without it.

  * GN_InsetFaces -- its bare `Selection` (consumed on the FACE domain) now goes through
    the gate; adds Invert Selection, Grow / Shrink Selection and the Material ID trio.
  * GN_NormalTransfer -- keeps its float mask (Masking Mode / Mask Attribute / Invert
    Mask: a Mix factor, 0 = take the source normal, 1 = keep the own normal). The gate is
    added BESIDE it as a new boolean `Selection` (default on): unselected corners keep
    their own normal, selected ones use the mask as before. The gate is evaluated on the
    POINT domain (like the deformers), so Grow counts vertex rings; Set Mesh Normal
    reads it per corner.

Both get a `Selection` panel right after Geometry, and their remaining top-level inputs
go into panels (InsetFaces: Inset; NormalTransfer: Source, Mask) -- moving an input is
cosmetic, identifiers and saved values travel with it.

Gated like the earlier rollouts: identical evaluation (positions + attributes) at the
defaults, no blocking layout rule worse; the new nodes sit in their own labeled frame,
slid clear of the existing graph.

blender --background --factory-startup --python patch_gn_selection_gate_new.py -- [--dry] [GN_X ...]
"""
import bpy, os, sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import gng_selection_gate as gate
from patch_gn_use_selection_gate_group import GEO, NEW_FRAME, GROW_NAME, GROW_DESC, instances, sig, blocking
from patch_gn_selection_gate_v2 import (USE_NAME, ID_NAME, MODE_NAME, DESCS, INV_NAME,
                                        inputs, item, selection_panel, file_into, new_input)

SEL_DESC = {
    "GN_NormalTransfer": ("Corners that take the source normal (through the mask below). "
                          "Unselected corners keep their own normal"),
}
INV_DESC = "Invert the selection (applied after Select by Material ID, before Grow / Shrink)"
PANELS = {
    "GN_InsetFaces": [("Inset", ["Offset"])],
    "GN_NormalTransfer": [("Source", ["Source Object"]),
                          ("Mask", ["Masking Mode", "Mask Attribute", "Invert Mask"])],
}
TARGETS = [("GN_InsetFace.blend", "GN_InsetFaces"),
           ("GN_NormalTransfer.blend", "GN_NormalTransfer")]


def panel_after(ng, name, prev):
    """Panel `name` at root level, right after `prev` (an interface item)."""
    iface = ng.interface
    root = prev.parent
    p = next((i for i in root.interface_items if i.item_type == 'PANEL' and i.name == name), None)
    if p is None:
        p = iface.new_panel(name)
    iface.move_to_parent(p, root, list(root.interface_items).index(prev) + 1)
    return p


def build_interface(ng, gname):
    """Selection panel with the full gate block; returns the six items in gate order."""
    panel, _ = selection_panel(ng)
    sel = item(ng, "Selection")
    if sel is None:
        sel = ng.interface.new_socket("Selection", in_out='INPUT', socket_type='NodeSocketBool',
                                      parent=panel)
        sel.default_value = True
        sel.hide_value = False
    if gname in SEL_DESC:
        sel.description = SEL_DESC[gname]
    inv = ng.interface.new_socket(INV_NAME, in_out='INPUT', socket_type='NodeSocketBool', parent=panel)
    inv.default_value, inv.description = False, INV_DESC
    grow = ng.interface.new_socket(GROW_NAME, in_out='INPUT', socket_type='NodeSocketInt', parent=panel)
    grow.default_value, grow.min_value, grow.max_value = 0, -10000, 10000
    grow.description = GROW_DESC
    if hasattr(grow, "structure_type"):
        grow.structure_type = 'SINGLE'
    use = new_input(ng, USE_NAME, 'NodeSocketBool', panel)
    use.default_value = False
    mid = new_input(ng, ID_NAME, 'NodeSocketInt', panel)
    mid.default_value, mid.min_value, mid.max_value = 0, 0, 32767
    mode = new_input(ng, MODE_NAME, 'NodeSocketMenu', panel)
    items = [sel, inv, grow, use, mid, mode]
    file_into(ng, panel, items)

    prev = panel
    for pname, names in PANELS.get(gname, []):
        p = panel_after(ng, pname, prev)
        file_into(ng, p, [item(ng, n) for n in names])
        prev = p
    ng.interface.active_index = 0
    return items


def build_gate(ng, items, anchor):
    """Frame + Group Input (gate sockets only) + gate node, left of / below `anchor`."""
    frame = ng.nodes.new("NodeFrame")
    frame.label = NEW_FRAME
    frame.location = (0, 0)
    gi = ng.nodes.new("NodeGroupInput")
    gi.parent = frame
    names = [i.name for i in items]
    for s in gi.outputs:
        if s.name and s.name not in names:
            s.hide = True
    node = ng.nodes.new("GeometryNodeGroup")
    node.node_tree = gate.ensure()
    node.name = node.label = "Selection Gate"
    node.parent = frame
    node.width = 180
    for it, sock in zip(items, (gate.SEL, gate.INV, gate.GROW, gate.USE_MAT, gate.MAT_ID, gate.MAT_MODE)):
        ng.links.new(gi.outputs[it.name], node.inputs[sock])
    items[-1].default_value = gate.MODES[0]     # after linking, so the enum resolves
    ax, ay = anchor.location.x, anchor.location.y
    gi.location = (ax - 560, ay - 350)
    node.location = (ax - 300, ay - 350)
    return frame, gi, node


def slide_clear(ng, frame, audit_before):
    """Move the new frame's nodes until no blocking layout rule is worse than before."""
    def worse_now():
        a = blocking(ng)
        return any(a[k] > audit_before[k] for k in a)
    if not worse_now():
        return (0, 0)
    kids = [n for n in ng.nodes if n.parent == frame]
    home = {n.name: n.location.copy() for n in kids}
    steps = [(0, -d) for d in range(100, 3001, 100)] + [(-d, 0) for d in range(100, 3001, 100)] \
        + [(-d, -d) for d in range(100, 3001, 100)]
    for dx, dy in steps:
        for n in kids:
            n.location = (home[n.name].x + dx, home[n.name].y + dy)
        if not worse_now():
            return (dx, dy)
    for n in kids:
        n.location = home[n.name]
    return None


def wire_inset(ng, node):
    """Gate replaces the bare Selection everywhere it was read."""
    links = [l for l in ng.links if l.from_node.bl_idname == "NodeGroupInput"
             and l.from_socket.name == "Selection" and l.to_node != node]
    anchor = links[0].to_node
    for l in links:
        ts = l.to_socket
        ng.links.remove(l)
        ng.links.new(node.outputs[0], ts)
    return anchor


def wire_normal(ng, node, frame):
    """Mix factor = Selection ? mask : 1 (keep own normal)."""
    mix = next(n for n in ng.nodes if n.bl_idname == "ShaderNodeMix")
    fac = mix.inputs["Factor"]
    src = fac.links[0].from_socket
    dom = ng.nodes.new("GeometryNodeFieldOnDomain")
    dom.domain, dom.data_type = 'POINT', 'BOOLEAN'
    dom.name = dom.label = "Selection on Points"
    dom.parent = frame
    sw = ng.nodes.new("GeometryNodeSwitch")
    sw.input_type = 'FLOAT'
    sw.name = sw.label = "Selected ? Mask : Keep Own Normal"
    sw.parent = frame
    sw.inputs["False"].default_value = 1.0
    ng.links.new(node.outputs[0], dom.inputs["Value"])
    ng.links.new(dom.outputs["Value"], sw.inputs["Switch"])
    ng.links.new(src, sw.inputs["True"])
    ng.links.new(sw.outputs["Output"], fac)
    dom.location = (node.location.x + 230, node.location.y)
    sw.location = (node.location.x + 430, node.location.y)
    return mix


def patch(fname, gname, dry=False):
    path = os.path.join(GEO, fname)
    bpy.ops.wm.open_mainfile(filepath=path, load_ui=False)
    ng = bpy.data.node_groups[gname]
    if item(ng, USE_NAME):
        return "SKIP  %s/%s: already has %r" % (fname, gname, USE_NAME)
    before, audit_before = sig(ng), blocking(ng)

    had = {m.name: set(m.keys()) for _, m in instances(ng)}
    items = build_interface(ng, gname)
    gi_anchor = next(n for n in ng.nodes if n.bl_idname == "NodeGroupOutput")
    frame, gi, node = build_gate(ng, items, gi_anchor)
    if gname == "GN_InsetFaces":
        anchor = wire_inset(ng, node)
    else:
        anchor = wire_normal(ng, node, frame)
    # re-place next to the real consumer, then slide clear of the existing graph
    dx = anchor.location.x - gi_anchor.location.x
    dy = anchor.location.y - gi_anchor.location.y
    for n in ng.nodes:
        if n.parent == frame:
            n.location = (n.location.x + dx - (700 if gname == "GN_NormalTransfer" else 0),
                          n.location.y + dy)
    moved = slide_clear(ng, frame, audit_before)
    # Explicit values, not the zero backfill -- a NEW Selection must come up True. Set
    # after the graph is built: the modifier re-syncs its inputs on interface change.
    bpy.context.view_layer.update()
    for _, m in instances(ng):
        for it, v in zip(items[:5], (True, False, 0, False, 0)):
            if it.identifier not in had[m.name]:
                m[it.identifier] = v
        m[items[-1].identifier] = 0         # menu stored -1 (no item) when the socket was added

    after, audit_after = sig(ng), blocking(ng)
    if before != after:
        bad = [k for k in before if before[k] != after.get(k)]
        return "FAIL  %s/%s: result changed at defaults: %s" % (fname, gname, bad)
    worse = {k: (audit_before[k], audit_after[k]) for k in audit_before
             if audit_after[k] > audit_before[k]}
    if worse:
        return "FAIL  %s/%s: layout regressions %s" % (fname, gname, worse)
    if items[-1].default_value != gate.MODES[0]:
        return "FAIL  %s/%s: menu default did not resolve" % (fname, gname)
    note = "gate frame slid %s" % (moved,)
    if dry:
        return "DRY   %s/%s: ok, %s" % (fname, gname, note)
    bpy.ops.wm.save_mainfile(filepath=path, compress=True)
    return "OK    %s/%s: %s" % (fname, gname, note)


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
    print("\n#### SELECTION GATE NEW ####")
    for r in res:
        print(r)
    sys.stdout.flush()
    os._exit(0)
