"""Put the Selection panel at the top of every modifier (right under Geometry).

Blender draws a level's loose sockets BEFORE its panels, whatever the interface order
says (`move` / `move_to_parent` to index 1 is silently ignored). So a modifier with
top-level parameters showed them above the Selection panel. The only fix is to file
those parameters into a panel of their own, placed right after Selection -- which is
also criterion R10 (only Geometry stays top-level). The new panel is open by default.

Moving an input is cosmetic: identifiers and saved modifier values travel with it.
Gated on identical evaluation (positions + attributes) and no worse blocking layout rule.

blender --background --factory-startup --python patch_gn_selection_panel_first.py -- [--dry] [GN_X ...]
"""
import bpy, os, sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from patch_gn_use_selection_gate_group import GEO, sig, blocking

PANEL = "Selection"
# (file, group, name of the panel that takes the loose top-level inputs)
TARGETS = [
    ("GN_AttributeFunctions_4.5.blend", "GN_SetAttribute", "Set All"),
    ("GN_AutoSmooth.blend", "GN_AutoSmooth", "Auto Smooth"),
    ("GN_Displace.blend", "GN_Displace", "Displace"),
    ("GN_Erosion_3D.blend", "GN_Erosion_3D", "Erosion"),
    ("GN_FlattenByBoundary.blend", "GN_FlattenByBoundary", "Flatten"),
    ("GN_PointsToSpheres.blend", "GN_PointsToSpheres", "Spheres"),
    ("GN_RandomizePosition.blend", "GN_RandomizePosition", "Randomize"),
    ("GN_Scatter.blend", "GN_Scatter", "Scatter"),
    ("GN_SetMaterial.blend", "GN_SetMaterial", "Set Material"),
    ("GN_SimpleTransform.blend", "GN_SimpleTransformMesh", "Transform"),
    ("GN_Weld.blend", "GN_Weld", "Weld"),
    ("GN_Wireframe.blend", "GN_Wireframe", "Wireframe"),
]


def root_items(ng):
    return [i for i in ng.interface.items_tree if i.parent.name == ""
            and not (i.item_type == 'SOCKET' and i.in_out == 'OUTPUT')]


def drawn_order(ng):
    """Root inputs as the modifier panel draws them: sockets first, then panels."""
    items = root_items(ng)
    return [i for i in items if i.item_type == 'SOCKET'] + [i for i in items if i.item_type == 'PANEL']


def selection_first(ng):
    names = [i.name for i in drawn_order(ng)]
    return names[:2] == ["Geometry", PANEL]


def patch(fname, gname, pname, dry=False):
    path = os.path.join(GEO, fname)
    bpy.ops.wm.open_mainfile(filepath=path, load_ui=False)
    ng = bpy.data.node_groups[gname]
    if selection_first(ng):
        return "SKIP  %s/%s: Selection already on top" % (fname, gname)
    iface = ng.interface
    if any(i.item_type == 'PANEL' and i.name == pname for i in root_items(ng)):
        return "FAIL  %s/%s: a panel %r already exists" % (fname, gname, pname)
    before, audit_before = sig(ng), blocking(ng)

    loose = [i for i in root_items(ng) if i.item_type == 'SOCKET'
             and i.socket_type != 'NodeSocketGeometry']
    sel = next(i for i in root_items(ng) if i.item_type == 'PANEL' and i.name == PANEL)
    p = iface.new_panel(pname)
    p.default_closed = False
    for k, it in enumerate(loose):
        iface.move_to_parent(it, p, k)
    root = sel.parent
    iface.move_to_parent(p, root, list(root.interface_items).index(sel) + 1)
    iface.active_index = 0

    after, audit_after = sig(ng), blocking(ng)
    if before != after:
        return "FAIL  %s/%s: evaluation changed" % (fname, gname)
    worse = {k: (audit_before[k], audit_after[k]) for k in audit_before
             if audit_after[k] > audit_before[k]}
    if worse:
        return "FAIL  %s/%s: layout regressions %s" % (fname, gname, worse)
    if not selection_first(ng):
        return "FAIL  %s/%s: Selection still not first: %s" % (
            fname, gname, [i.name for i in drawn_order(ng)][:4])
    order = [("[%s]" % i.name) if i.item_type == 'PANEL' else i.name for i in drawn_order(ng)]
    note = "%d input(s) -> %r; %s" % (len(loose), pname, order[:4])
    if dry:
        return "DRY   %s/%s: %s" % (fname, gname, note)
    bpy.ops.wm.save_mainfile(filepath=path, compress=True)
    return "OK    %s/%s: %s" % (fname, gname, note)


if __name__ == "__main__":
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    dry = "--dry" in argv
    only = [a for a in argv if not a.startswith("--")]
    res = []
    for f, g, p in TARGETS:
        if only and f not in only and g not in only:
            continue
        try:
            res.append(patch(f, g, p, dry=dry))
        except Exception as e:
            import traceback
            traceback.print_exc()
            res.append("FAIL  %s/%s: %s" % (f, g, e))
    print("\n#### SELECTION PANEL FIRST ####")
    for r in res:
        print(r)
    sys.stdout.flush()
    os._exit(0)
