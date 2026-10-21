"""GNG_SelectionGate v2 rollout: Material ID selection + a Selection panel on every modifier.

Per tool that already routes its selection through GNG_SelectionGate:
  * upgrades the file's GNG_SelectionGate to gate.VERSION (adds Use Material ID /
    Material ID / Material Mode; existing links and identifiers are kept),
  * adds `Select by Material ID` (bool, off), `Selection Material ID` (int) and
    `Material ID Mode` (menu, Add) to the modifier and wires them into the gate,
  * files the whole selection block into a `Selection` panel (created right after
    Geometry when the tool has none): Selection, Invert Selection, Grow / Shrink
    Selection, Select by Material ID, Selection Material ID, Material ID Mode.
    Moving is cosmetic -- identifiers and saved overrides travel with the socket.
  * GN_ExtrudeFace: its own material select becomes `Legacy Select by Material Index` /
    `Legacy Selection Material Index` (renames keep identifiers, so old values load).

Backward compatible: Blender backfills the new bool/int with 0 and the menu with its
first item (Add), and Use Material ID off is an exact passthrough. Gated like the
earlier rollouts: identical evaluation (positions + attributes) with Invert off and on,
no blocking layout rule worse.

blender --background --factory-startup --python patch_gn_selection_gate_v2.py -- [--dry] [GN_X.blend ...]
"""
import bpy, os, sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import gng_selection_gate as gate
from patch_gn_use_selection_gate_group import (GEO, GROW_NAME, TARGETS as T1,
                                               instances, sig, blocking)

USE_NAME, ID_NAME, MODE_NAME = "Select by Material ID", "Selection Material ID", "Material ID Mode"
DESCS = {
    USE_NAME: ("Also select by material: combine the Selection with every face that uses "
               "Selection Material ID, as set by Material ID Mode"),
    ID_NAME: "Material slot index (0 = first slot) used by Select by Material ID",
    MODE_NAME: ("Add: Selection plus the material's faces. Subtract: Selection minus them. "
                "Intersect: only the selected part of the material. Material Minus "
                "Selection: the material's faces minus the Selection"),
}
PANEL = "Selection"
INV_NAME = "Invert Selection"
LEGACY = {"GN_ExtrudeFace": [("Select by Material Index", "Legacy Select by Material Index"),
                             ("Selection Material Index", "Legacy Selection Material Index")]}
LEGACY_NOTE = ("Legacy: kept so files saved before the shared selection gate still load "
               "their value. Use Select by Material ID instead. ")

TARGETS = T1 + [("GN_AttributeFunctions_4.5.blend", "GN_SetAttribute"),
                ("GN_Delete.blend", "GN_Delete"),
                ("GN_SolidifyPlus.blend", "GN_SolidifyPlus")]


def inputs(ng):
    return [i for i in ng.interface.items_tree if i.item_type == 'SOCKET' and i.in_out == 'INPUT']


def item(ng, name):
    return next((i for i in inputs(ng) if i.name == name), None)


def gate_node(ng):
    return next(n for n in ng.nodes if n.bl_idname == "GeometryNodeGroup"
                and n.node_tree and n.node_tree.name == gate.NAME)


def selection_panel(ng):
    iface = ng.interface
    geo = next(i for i in inputs(ng) if i.socket_type == 'NodeSocketGeometry')
    root = geo.parent
    for it in root.interface_items:
        if it.item_type == 'PANEL' and it.name == PANEL:
            return it, False
    p = iface.new_panel(PANEL)
    iface.move_to_parent(p, root, list(root.interface_items).index(geo) + 1)
    return p, True


def file_into(ng, panel, items):
    """Put items into panel, in this order, ahead of anything else already there."""
    iface = ng.interface
    for k, it in enumerate(items):
        iface.move_to_parent(it, panel, k)


def new_input(ng, name, stype, panel):
    it = ng.interface.new_socket(name, in_out='INPUT', socket_type=stype, parent=panel)
    it.description = DESCS[name]
    if hasattr(it, "structure_type") and stype != 'NodeSocketMenu':
        it.structure_type = 'SINGLE'
    return it


def patch(fname, gname, dry=False):
    path = os.path.join(GEO, fname)
    bpy.ops.wm.open_mainfile(filepath=path, load_ui=False)
    ng = bpy.data.node_groups[gname]
    if item(ng, USE_NAME):
        return "SKIP  %s/%s: already has %r" % (fname, gname, USE_NAME)

    inv_id = item(ng, INV_NAME).identifier

    def sig_both():
        a = sig(ng)
        old = [(m, m[inv_id]) for _, m in instances(ng)]
        for m, v in old:
            m[inv_id] = not v
        b = sig(ng)
        for m, v in old:
            m[inv_id] = v
        return a, b

    before, audit_before = sig_both(), blocking(ng)

    g = gate.ensure()                       # upgrade in place (same datablock)
    node = gate_node(ng)
    gi = node.inputs[gate.INV].links[0].from_node
    sel_src = node.inputs[gate.SEL].links[0].from_socket
    sel_item = item(ng, sel_src.name) if sel_src.node.bl_idname == "NodeGroupInput" else None

    for old, new in LEGACY.get(gname, []):
        it = item(ng, old)
        it.name = new
        if not it.description.startswith("Legacy"):
            it.description = LEGACY_NOTE + it.description

    panel, created = selection_panel(ng)
    use = new_input(ng, USE_NAME, 'NodeSocketBool', panel)
    use.default_value = False
    mid = new_input(ng, ID_NAME, 'NodeSocketInt', panel)
    mid.default_value, mid.min_value, mid.max_value = 0, 0, 32767
    mode = new_input(ng, MODE_NAME, 'NodeSocketMenu', panel)

    order = [i for i in (sel_item, item(ng, INV_NAME), item(ng, GROW_NAME)) if i is not None]
    file_into(ng, panel, order + [use, mid, mode])
    ng.interface.active_index = 0

    for name, sock in ((USE_NAME, gate.USE_MAT), (ID_NAME, gate.MAT_ID), (MODE_NAME, gate.MAT_MODE)):
        out = gi.outputs[name]
        out.hide = False
        ng.links.new(out, node.inputs[sock])
    mode.default_value = gate.MODES[0]      # after linking, so the enum resolves
    for _, m in instances(ng):
        m[use.identifier] = False
        m[mid.identifier] = 0
        m[mode.identifier] = 0              # stored -1 (no item) when the socket was added

    # The Group Input now shows three more sockets, so the gate frame grows and can clip
    # a neighbouring frame. Slide the frame's nodes clear (up first, then left) until no
    # blocking rule is worse than before.
    def worse_now():
        a = blocking(ng)
        return any(a[k] > audit_before[k] for k in a)

    moved = None
    if worse_now() and node.parent is not None:
        kids = [n for n in ng.nodes if n.parent == node.parent]
        home = {n.name: n.location.copy() for n in kids}
        steps = [(0, d) for d in range(100, 2001, 100)] + [(-d, 0) for d in range(100, 2001, 100)] \
            + [(0, -d) for d in range(100, 2001, 100)]
        for dx, dy in steps:
            for n in kids:
                n.location = (home[n.name].x + dx, home[n.name].y + dy)
            if not worse_now():
                moved = (dx, dy)
                break
        else:
            for n in kids:
                n.location = home[n.name]

    after, audit_after = sig_both(), blocking(ng)
    for tag, b, a in (("", before[0], after[0]), (" with Invert flipped", before[1], after[1])):
        if b != a:
            bad = [k for k in b if b[k] != a.get(k)]
            return "FAIL  %s/%s: result changed%s: %s" % (fname, gname, tag, bad)
    worse = {k: (audit_before[k], audit_after[k]) for k in audit_before
             if audit_after[k] > audit_before[k]}
    if worse:
        return "FAIL  %s/%s: layout regressions %s" % (fname, gname, worse)
    if mode.default_value != gate.MODES[0]:
        return "FAIL  %s/%s: menu default did not resolve (%r)" % (fname, gname, mode.default_value)
    note = "new Selection panel" if created else "existing Selection panel"
    if gname in LEGACY:
        note += ", legacy material select renamed"
    if moved:
        note += ", gate frame nudged %s" % (moved,)
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
    print("\n#### SELECTION GATE V2 ####")
    for r in res:
        print(r)
    sys.stdout.flush()
    os._exit(0)
