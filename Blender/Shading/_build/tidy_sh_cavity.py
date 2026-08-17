"""Lay out SH_Cavity with the deterministic tidy engine, audit R1-R11, save.

The engine in LLMGeonodePipeline/tidy_layout.py only keys on generic node idnames
(NodeFrame / NodeGroupInput / NodeGroupOutput / NodeReroute), so it works on a
ShaderNodeTree unchanged.  The save is gated on the blocking rules passing.

  blender.exe --background --factory-startup SH_Cavity.blend --python tidy_sh_cavity.py
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


ng = bpy.data.node_groups["SH_Cavity"]
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
