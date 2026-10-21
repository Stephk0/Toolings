"""Repair `Material ID Mode` on the Geonodes .blend files: socket default and saved modifiers.

Socket default: the tools patched while the gate was v2 stored their default as the v2
identifier of `Add` (2). v3 renumbered the items (Add = 0), so that 2 now reads as
`Intersect` and every freshly added modifier started in Intersect. Reset to `Add`.

Saved modifiers:

A Menu socket added to a group that already has modifiers gives each modifier the menu
property while the socket has no enum items yet (it is linked to the Menu Switch only
afterwards), and the modifier stores -1 -- no item. Select by Material ID then does
nothing until the menu is picked again by hand. This sets every -1 to 0 (`Add`, item
identifier 0 in GNG_SelectionGate v3) and saves only when evaluation is unchanged
(Select by Material ID is off on every demo, so the mode is not read).

blender --background --factory-startup --python fix_gn_material_mode_backfill.py -- [--dry]
"""
import bpy, glob, os, sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from patch_gn_use_selection_gate_group import GEO, instances, sig
from gng_selection_gate import MODES

MODE_NAME = "Material ID Mode"


def fix(path, dry):
    bpy.ops.wm.open_mainfile(filepath=path, load_ui=False)
    f = os.path.basename(path)
    out = []
    for ng in bpy.data.node_groups:
        if ng.library:
            continue
        it = next((i for i in ng.interface.items_tree if i.item_type == 'SOCKET'
                   and i.in_out == 'INPUT' and i.name == MODE_NAME), None)
        if it is None:
            continue
        notes = []
        if it.default_value != MODES[0]:
            notes.append("default %s -> %s" % (it.default_value, MODES[0]))
            it.default_value = MODES[0]
        bad = [m for _, m in instances(ng) if m.get(it.identifier) == -1]
        if bad:
            before = sig(ng)
            for m in bad:
                m[it.identifier] = 0
            if sig(ng) != before:
                return "FAIL  %s/%s: evaluation changed" % (f, ng.name)
            notes.append("%d modifier(s) -1 -> 0" % len(bad))
        if notes:
            out.append("%s (%s)" % (ng.name, ", ".join(notes)))
    if not out:
        return None
    if dry:
        return "DRY   %s: %s" % (f, ", ".join(out))
    bpy.ops.wm.save_mainfile(filepath=path, compress=True)
    return "OK    %s: %s" % (f, ", ".join(out))


if __name__ == "__main__":
    dry = "--dry" in sys.argv
    res = []
    for path in sorted(glob.glob(os.path.join(GEO, "*.blend"))):
        try:
            r = fix(path, dry)
        except Exception as e:
            import traceback
            traceback.print_exc()
            r = "FAIL  %s: %s" % (os.path.basename(path), e)
        if r:
            res.append(r)
    print("\n#### MATERIAL ID MODE REPAIR ####")
    for r in res:
        print(r)
    sys.stdout.flush()
    os._exit(0)
