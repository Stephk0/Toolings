"""XOR truth-table check for every ST3E modifier that carries a Selection gate.

Discovers the pairs itself: any modifier node group with an `Invert Selection`
input, gated on the boolean input that sits immediately before it.

    A = (Sel 1, Inv 0)   and   B = (Sel 0, Inv 1)   must be IDENTICAL  (-> selected)
    C = (Sel 0, Inv 0)   and   D = (Sel 1, Inv 1)   must be IDENTICAL  (-> unselected)
    A != C proves the gate is actually live on this file's demo object.

`live:False` only means the demo scene's parameters produce no visible difference
between selected and unselected; it is not a wiring failure.

Run ONE FILE PER PROCESS -- pass the .blend basenames after `--`:

    for f in GN_*.blend; do
      blender --background --factory-startup \
        --python _build/verify_gn_invert_selection.py -- "${f%.blend}"
    done

Loading several .blend files into one Blender process corrupts this comparison:
GN_PointsToSpheres reported A != B reproducibly (its evaluated UV layer came back
differently) purely because another file had been opened first in the same process.
The same run, one process per file, passes. With no arguments every file is checked
in a single process -- fast, but treat any failure there as suspect until you have
re-run that one file on its own.
"""
import bpy, os, glob, sys

GEO = r"D:\Stephko_Tooling\Toolings\Blender\Geonodes"
INV = "Invert Selection"
SKIP = {"GN_VariousTest", "GN_EdgeDestruct", "GN_EdgeDestruct_fixed",
        "GN_treeGenerator_03", "GN_CellFrac"}


def sig(obj):
    obj.update_tag()
    bpy.context.view_layer.update()
    dg = bpy.context.evaluated_depsgraph_get()
    ev = obj.evaluated_get(dg)
    me = ev.to_mesh()
    if me is None:
        return None
    parts = [len(me.vertices), len(me.edges), len(me.polygons)]
    parts += [round(c, 5) for v in me.vertices for c in v.co]
    parts += [p.material_index for p in me.polygons]
    parts += [round(c, 4) for p in me.polygons for c in p.normal]
    for a in me.attributes:
        if a.domain not in {'POINT', 'CORNER', 'FACE'}:
            continue
        try:
            for d in a.data:
                for f in ("value", "vector", "color"):
                    v = getattr(d, f, None)
                    if v is None:
                        continue
                    parts += [round(x, 4) for x in v] if hasattr(v, "__len__") else [round(v, 4)]
        except Exception:
            pass
    ev.to_mesh_clear()
    return tuple(parts)


def stable_sig(obj, tries=4):
    """Evaluate until two consecutive reads agree.

    `to_mesh()` on realized instances is not always repeatable inside a long-lived
    process (GN_PointsToSpheres' UV layer came back differently between two reads of
    the SAME modifier settings), so a single sample can make an identical pair look
    different. Returns (signature, stable?)."""
    prev = sig(obj)
    for _ in range(tries):
        cur = sig(obj)
        if cur == prev:
            return cur, True
        prev = cur
    return prev, False


def check(ng, fname):
    ins = [i for i in ng.interface.items_tree
           if i.item_type == 'SOCKET' and i.in_out == 'INPUT']
    idx = next((k for k, i in enumerate(ins) if i.name == INV), None)
    if idx is None or idx == 0:
        return None
    gate = ins[idx - 1]
    if gate.socket_type != 'NodeSocketBool':
        return "SKIP %s/%s: socket before %r is %s" % (fname, ng.name, INV, gate.socket_type)
    si, ii = gate.identifier, ins[idx].identifier

    pair = None
    for o in bpy.data.objects:
        for m in o.modifiers:
            if m.type == 'NODES' and m.node_group == ng:
                pair = (o, m)
                break
        if pair:
            break
    if not pair:
        return "SKIP %s/%s: no demo object" % (fname, ng.name)
    o, m = pair
    bound = bool(m.get(si + "_use_attribute", 0))
    m[si + "_use_attribute"] = 0          # honour the constant for this test
    m[ii + "_use_attribute"] = 0
    m[si], m[ii] = True, False
    sig(o)                                # warm-up: settle the depsgraph first
    res, steady = {}, True
    for key, (s, i) in {"A": (True, False), "B": (False, True),
                        "C": (False, False), "D": (True, True)}.items():
        m[si], m[ii] = s, i
        res[key], ok_s = stable_sig(o)
        steady = steady and ok_s
    m[si], m[ii] = True, False
    ok = res["A"] == res["B"] and res["C"] == res["D"]
    return "%s %s %-28s gate=%-18r A==B:%s C==D:%s live:%s attr-demo:%s%s" % (
        "PASS" if ok else "FAIL", "", fname + "/" + ng.name, gate.name,
        res["A"] == res["B"], res["C"] == res["D"], res["A"] != res["C"], bound,
        "" if steady else "  [UNSTABLE eval]")


if __name__ == "__main__":
    only = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    out = []
    for path in sorted(glob.glob(os.path.join(GEO, "GN_*.blend"))):
        base = os.path.splitext(os.path.basename(path))[0]
        if base in SKIP or (only and base not in only):
            continue
        bpy.ops.wm.open_mainfile(filepath=path, load_ui=False)
        for ng in list(bpy.data.node_groups):
            if ng.library or ng.bl_idname != "GeometryNodeTree":
                continue
            if not getattr(ng, "is_modifier", False):
                continue
            r = check(ng, base)
            if r:
                out.append(r)
    print("\n#### VERIFY ####")
    for r in out:
        print(r)
    print("total %d, failures %d" % (len(out), sum(1 for r in out if r.startswith("FAIL"))))
