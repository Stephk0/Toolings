"""group_frames.py -- Setup step for huge graphs: collapse big function frames into GNG_*
helper groups, so the tree reads as a block diagram and every chunk is tidied on its own.

In circuit terms: a sheet with 3000 parts is split into sub-sheets. Each large labeled
frame becomes a helper group `GNG_<Tool>_<FrameName>`; its group node stays in the same
frame, labelled with the frame's name. `run_pipeline` / `polish_layout` already treat every
local helper group as its own graph (`tidy_layout.own_trees`), so after this the tidy and
polish work in chunks instead of one enormous graph.

Rules:
  - only top-level frames with at least `--min` function nodes (default 30);
  - a repeat / simulation / for-each zone is grouped only if the WHOLE zone (both ends and
    everything reachable between them) sits in the frame -- never split a zone;
  - local Group Input nodes stay outside; their links become the helper's inputs;
  - duplicate socket names on a helper get the feeding/reading node as suffix (R9);
  - geometry is checked after EVERY frame: a grouping that changes the result is ungrouped
    again (GN_Mosaic "Contour Rows" emptied the output); the main tree's interface must be
    unchanged; the file is saved only with `--save` and only if everything matches.
Reroutes are dissolved first -- the tidy re-routes afterwards anyway.

GUI Blender only (uses the node editor's Make Group operator):
  blender --factory-startup Geonodes/GN_X.blend --python group_frames.py -- GN_X [--min 30] [--save]
Then run `run_pipeline.py` (twice) and `polish_layout.py`.
"""

import bpy, sys, os, re
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import tidy_layout, polish_layout

argv = sys.argv[sys.argv.index("--") + 1:]
NAME = argv[0]
MIN = int(argv[argv.index("--min") + 1]) if "--min" in argv else 30
SAVE = "--save" in argv
ZONE_IN = ('GeometryNodeRepeatInput', 'GeometryNodeSimulationInput', 'GeometryNodeForeachGeometryElementInput')
ZONE_OUT = ('GeometryNodeRepeatOutput', 'GeometryNodeSimulationOutput', 'GeometryNodeForeachGeometryElementOutput')


def geometry(objs):
    dg = bpy.context.evaluated_depsgraph_get(); dg.update()
    out = []
    for o in objs:
        ev = o.evaluated_get(dg); me = ev.to_mesh()
        out.append(sorted((round(v.co.x, 5), round(v.co.y, 5), round(v.co.z, 5)) for v in me.vertices))
        ev.to_mesh_clear()
    return out


def descendants(ng, fr):
    out = []
    for n in ng.nodes:
        p = n.parent
        while p is not None:
            if p == fr: out.append(n); break
            p = p.parent
    return out


def zone_bodies(ng):
    """{zone input name: set of node names forward-reachable from it up to its output}."""
    out = {}
    for zi in [n for n in ng.nodes if n.bl_idname in ZONE_IN]:
        zo = zi.paired_output
        body, stack = {zi.name, zo.name}, [zi]
        while stack:
            n = stack.pop()
            for s in n.outputs:
                for l in s.links:
                    t = l.to_node
                    if t.name in body: continue
                    body.add(t.name)
                    if t != zo: stack.append(t)
        out[zi.name] = body
    return out


def editor(ng):
    polish_layout.draw_tree(ng)
    w, a = polish_layout._editor()
    return w, a, next(r for r in a.regions if r.type == 'WINDOW')


def camel(label):
    core = label.split("  (")[0].split("(")[0]
    return "".join(p[:1].upper() + p[1:] for p in re.split(r"[^A-Za-z0-9]+", core) if p)


def run():
    code = 1
    try:
        ng = bpy.data.node_groups[NAME]
        objs = [o for o in bpy.data.objects if any(m.type == 'NODES' and m.node_group == ng for m in o.modifiers)]
        iface0 = [(i.identifier, i.name) for i in ng.interface.items_tree if i.item_type == 'SOCKET']
        g0 = geometry(objs)
        n_rr = len([n for n in ng.nodes if n.bl_idname == 'NodeReroute'])
        tidy_layout.dissolve_reroutes(ng)          # the tidy re-routes afterwards anyway
        print(f"dissolved {n_rr} reroutes")
        bodies = zone_bodies(ng)
        tool = NAME[3:] if NAME.startswith("GN_") else NAME
        made = []
        for fr in [f for f in ng.nodes if f.bl_idname == 'NodeFrame' and f.parent is None]:
            work = [n for n in descendants(ng, fr)
                    if n.bl_idname not in ('NodeFrame', 'NodeReroute', 'NodeGroupInput', 'NodeGroupOutput')]
            if len(work) < MIN: continue
            names = {n.name for n in work}
            bad = []
            for zi, body in bodies.items():
                inside = body & names
                if inside and inside != body:
                    bad.append(zi)              # a zone split across this frame's edge
            if bad:
                print(f"  skip '{fr.label}': cuts through zone(s) {bad}"); continue
            w, a, r = editor(ng)
            for n in ng.nodes: n.select = False
            for n in work: n.select = True
            ng.nodes.active = work[0]
            with bpy.context.temp_override(window=w, area=a, region=r):
                res = bpy.ops.node.group_make()
            if 'FINISHED' not in res:
                print(f"  skip '{fr.label}': group_make {res}"); continue
            sp = a.spaces.active
            if sp.edit_tree != ng:
                with bpy.context.temp_override(window=w, area=a, region=r):
                    bpy.ops.node.tree_path_parent()
            gnode = next((n for n in ng.nodes if n.select and n.bl_idname == 'GeometryNodeGroup'
                          and n.node_tree and n.node_tree.name not in [g for g, _ in made]
                          and n.node_tree.name.startswith("NodeGroup")), None)
            if gnode is None:
                gnode = ng.nodes.active
            sub = gnode.node_tree
            sub.name = f"GNG_{tool}_{camel(fr.label or fr.name)}"
            gnode.label = (fr.label or fr.name).split("  (")[0]
            loc = gnode.location.copy()
            gnode.parent = fr
            # unique, specific socket names (R9): suffix the node that feeds / reads a duplicate
            for io in ('INPUT', 'OUTPUT'):
                items = [i for i in sub.interface.items_tree if i.item_type == 'SOCKET' and i.in_out == io]
                seen = {}
                for it in items: seen.setdefault(it.name, []).append(it)
                for nm, its in seen.items():
                    if len(its) < 2: continue
                    for k, it in enumerate(its):
                        sock = next((s for s in (gnode.inputs if io == 'INPUT' else gnode.outputs)
                                     if s.identifier == it.identifier), None)
                        other = None
                        if sock is not None and sock.links:
                            l = sock.links[0]
                            other = l.from_node if io == 'INPUT' else l.to_node
                        tag = (other.label or other.name) if other is not None else str(k + 1)
                        it.name = f"{nm} ({tag})"
            gnow = geometry(objs)
            if gnow != g0:
                diff = [(len(a_), len(b_)) for a_, b_ in zip(g0, gnow)]
                print(f"  '{fr.label}' CHANGED geometry {diff} -> ungrouping")
                for n in ng.nodes: n.select = False
                gnode.select = True; ng.nodes.active = gnode
                w, a, r = editor(ng)
                with bpy.context.temp_override(window=w, area=a, region=r):
                    bpy.ops.node.group_ungroup()
                bpy.data.node_groups.remove(sub)
                if geometry(objs) != g0:
                    raise RuntimeError("ungroup did not restore the geometry")
                continue
            made.append((sub.name, len(work)))
            print(f"  grouped '{fr.label}' -> {sub.name} ({len(work)} nodes)")
        iface1 = [(i.identifier, i.name) for i in ng.interface.items_tree if i.item_type == 'SOCKET']
        g1 = geometry(objs)
        ok = g1 == g0 and iface1 == iface0
        print(f"verts per object: {[len(g) for g in g0]}"); print(f"groups made: {len(made)}  geometry unchanged: {g1 == g0}  interface unchanged: {iface1 == iface0}"
              f"  nodes in main tree now: {len(ng.nodes)}")
        if ok and SAVE and made:
            bpy.ops.wm.save_mainfile(); print("=> SAVED")
        else:
            print("=> not saved")
        code = 0 if ok else 1
    except Exception:
        import traceback; traceback.print_exc()
    sys.stdout.flush(); os._exit(code)


bpy.app.timers.register(run, first_interval=1.5)
