"""Lay out a shader node group with the deterministic tidy engine, audit R1-R11, save.

The engine in LLMGeonodePipeline/tidy_layout.py only keys on generic node idnames
(NodeFrame / NodeGroupInput / NodeGroupOutput / NodeReroute), so it works on a
ShaderNodeTree unchanged.  The save is gated on the blocking rules passing.

  blender.exe --background --factory-startup <file>.blend --python tidy_shader_group.py
  blender.exe --background --factory-startup <file>.blend --python tidy_shader_group.py -- SH_Cavity

With no argument it picks the single SH_* group in the file.
"""
import bpy
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PIPE = os.path.normpath(os.path.join(
    HERE, "..", "..", "Addons", "ClaudeVibe_WIPs", "LLMGeonodePipeline"))
sys.path.insert(0, PIPE)

import tidy_layout          # noqa: E402
import layout_audit         # noqa: E402


def log(*a):
    print("TIDY:", *a)
    sys.stdout.flush()


def pick_group():
    if "--" in sys.argv:
        return bpy.data.node_groups[sys.argv[sys.argv.index("--") + 1]]
    cands = [g for g in bpy.data.node_groups
             if g.bl_idname == 'ShaderNodeTree' and g.name.startswith("SH_")]
    if len(cands) != 1:
        raise SystemExit("expected exactly one SH_* shader group, got %s"
                         % [g.name for g in cands])
    return cands[0]


ng = pick_group()
log("group:", ng.name)
log("before: %d nodes, %d frames" % (
    len([n for n in ng.nodes if n.bl_idname != 'NodeFrame']),
    len([n for n in ng.nodes if n.bl_idname == 'NodeFrame'])))

stats = tidy_layout.tidy_and_route(ng)
log("tidy stats:", stats)

rep = layout_audit.audit(ng)
layout_audit.print_report(rep)

failed_blocking = [r for r in layout_audit.BLOCKING if rep.get(r, {}).get("fail")]
if failed_blocking:
    log("BLOCKING FAILURES -> not saving:", failed_blocking)
    sys.stdout.flush()
    os._exit(1)

log("after: %d nodes, %d frames, %d reroutes" % (
    len([n for n in ng.nodes if n.bl_idname not in ('NodeFrame', 'NodeReroute')]),
    len([n for n in ng.nodes if n.bl_idname == 'NodeFrame']),
    len([n for n in ng.nodes if n.bl_idname == 'NodeReroute'])))

bpy.ops.wm.save_mainfile()
log("saved", bpy.data.filepath)
sys.stdout.flush()
os._exit(0)
