"""Upgrade GNG_SelectionGate in every Geonodes .blend that holds it.

Run after changing gng_selection_gate.py (bump VERSION there). Each file's group is
rebuilt in place by gate.ensure() -- same datablock, socket identifiers matched by name --
and the file is saved only when every modifier using the gate evaluates identically
(positions + attributes) before and after. Adding a NEW gate input still needs a
rollout that exposes and wires it on each modifier (see patch_gn_selection_gate_v2.py).

blender --background --factory-startup --python upgrade_gng_selection_gate.py -- [--dry]
"""
import bpy, glob, os, sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import gng_selection_gate as gate
from patch_gn_use_selection_gate_group import GEO, sig


def users(g):
    return [ng for ng in bpy.data.node_groups if ng != g and any(
        n.bl_idname == "GeometryNodeGroup" and n.node_tree == g for n in ng.nodes)]


def upgrade(path, dry):
    bpy.ops.wm.open_mainfile(filepath=path, load_ui=False)
    g = bpy.data.node_groups.get(gate.NAME)
    f = os.path.basename(path)
    if g is None or g.library is not None:
        return None
    old = g.get(gate.VERSION_KEY, 0)
    if old >= gate.VERSION:
        return "SKIP  %s: already v%d" % (f, old)
    trees = users(g)
    before = {t.name: sig(t) for t in trees}
    gate.ensure()
    after = {t.name: sig(t) for t in trees}
    if before != after:
        return "FAIL  %s: evaluation changed in %s" % (
            f, [t for t in before if before[t] != after[t]])
    if dry:
        return "DRY   %s: v%d -> v%d (%s)" % (f, old, gate.VERSION, ", ".join(before))
    bpy.ops.wm.save_mainfile(filepath=path, compress=True)
    return "OK    %s: v%d -> v%d (%s)" % (f, old, gate.VERSION, ", ".join(before))


if __name__ == "__main__":
    dry = "--dry" in sys.argv
    res = []
    for path in sorted(glob.glob(os.path.join(GEO, "*.blend"))):
        try:
            r = upgrade(path, dry)
        except Exception as e:
            import traceback
            traceback.print_exc()
            r = "FAIL  %s: %s" % (os.path.basename(path), e)
        if r:
            res.append(r)
    print("\n#### GATE UPGRADE ####")
    for r in res:
        print(r)
    sys.stdout.flush()
    os._exit(0)
