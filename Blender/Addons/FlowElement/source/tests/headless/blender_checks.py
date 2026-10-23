"""Headless Blender checks for the Flow Element operator.

blender --background --factory-startup --python tests/headless/blender_checks.py
Exits 1 on any failure.
"""

import math
import os
import sys
import traceback

import bmesh
import bpy
from mathutils import Vector

SOURCE = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.dirname(SOURCE))
addon = __import__(os.path.basename(SOURCE))
addon.register()

failures = []


def check(label, cond, detail=""):
    print(("PASS " if cond else "FAIL ") + label + (f"  ({detail})" if detail else ""))
    if not cond:
        failures.append(label)


def fresh(add_primitive, **kw):
    if bpy.context.object and bpy.context.object.mode != 'OBJECT':
        bpy.ops.object.mode_set(mode='OBJECT')
    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o)
    add_primitive(**kw)
    obj = bpy.context.object
    bpy.ops.object.mode_set(mode='EDIT')
    return obj


def ringed_cylinder(segments=16, cuts=5):
    obj = fresh(bpy.ops.mesh.primitive_cylinder_add, vertices=segments, depth=2.0,
                end_fill_type='TRIFAN')
    bm = bmesh.from_edit_mesh(obj.data)
    vertical = [e for e in bm.edges
                if abs(e.verts[0].co.z - e.verts[1].co.z) > 1.0 and
                all(abs(math.hypot(v.co.x, v.co.y) - 1.0) < 1e-4 for v in e.verts)]
    bmesh.ops.subdivide_edges(bm, edges=vertical, cuts=cuts, use_grid_fill=True)
    bmesh.update_edit_mesh(obj.data)
    return obj


def select_only(bm, verts=(), edges=(), faces=()):
    for seq in (bm.verts, bm.edges, bm.faces):
        for e in seq:
            e.select = False
    for e in (*verts, *edges, *faces):
        e.select = True
    bm.select_flush_mode()


def middle_ring(bm):
    zs = sorted({round(v.co.z, 4) for v in bm.verts})
    z = zs[len(zs) // 2]
    verts = [v for v in bm.verts if abs(v.co.z - z) < 1e-4 and math.hypot(v.co.x, v.co.y) > 0.5]
    vs = set(verts)
    edges = [e for e in bm.edges if e.verts[0] in vs and e.verts[1] in vs]
    return verts, edges


def run(label, fn):
    try:
        fn()
    except Exception:
        traceback.print_exc()
        check(label + " raised", False)


def edge_flow_cylinder():
    obj = ringed_cylinder()
    bm = bmesh.from_edit_mesh(obj.data)
    verts, edges = middle_ring(bm)
    for v in verts:  # squash in X: flattened ring
        v.co.x *= 0.4
    select_only(bm, edges=edges)
    bpy.context.tool_settings.mesh_select_mode = (False, True, False)
    bmesh.update_edit_mesh(obj.data)

    res = bpy.ops.mesh.st3e_flow_element()
    bm = bmesh.from_edit_mesh(obj.data)
    radii = [math.hypot(v.co.x, v.co.y) for v in bm.verts if v.select]
    err = max(abs(r - 1.0) for r in radii)
    check("edge flow restores flattened cylinder ring", res == {'FINISHED'} and err < 1e-4,
          f"{len(radii)} verts, max radius error {err:.2e}")


def mix_half():
    obj = ringed_cylinder()
    bm = bmesh.from_edit_mesh(obj.data)
    verts, edges = middle_ring(bm)
    for v in verts:
        v.co.x *= 0.4
        v.co.y *= 0.4
    select_only(bm, edges=edges)
    bmesh.update_edit_mesh(obj.data)
    bpy.ops.mesh.st3e_flow_element(mode='EDGE', mix=0.5)
    bm = bmesh.from_edit_mesh(obj.data)
    radii = [math.hypot(v.co.x, v.co.y) for v in bm.verts if v.select]
    check("mix 0.5 lands halfway", all(abs(r - 0.7) < 1e-4 for r in radii),
          f"{min(radii):.4f}..{max(radii):.4f}")


def vertex_flow_sphere():
    obj = fresh(bpy.ops.mesh.primitive_uv_sphere_add, segments=32, ring_count=16)
    bm = bmesh.from_edit_mesh(obj.data)
    v = min((v for v in bm.verts if abs(v.co.z) < 0.3), key=lambda v: v.co.z ** 2)
    v.co *= 0.75
    select_only(bm, verts=[v])
    bpy.context.tool_settings.mesh_select_mode = (True, False, False)
    bmesh.update_edit_mesh(obj.data)
    bpy.ops.mesh.st3e_flow_element()
    bm = bmesh.from_edit_mesh(obj.data)
    r = next(x for x in bm.verts if x.select).co.length
    check("vertex flow pops a dent back onto the sphere", abs(r - 1.0) < 2e-3, f"r={r:.5f}")


def face_flow_sphere():
    obj = fresh(bpy.ops.mesh.primitive_uv_sphere_add, segments=48, ring_count=24)
    bm = bmesh.from_edit_mesh(obj.data)
    centre = Vector((0.0, -1.0, 0.0))  # around the -Y equator
    faces = [f for f in bm.faces
             if (f.calc_center_median() - centre).length < 0.45]
    verts = {v for f in faces for v in f.verts}
    for v in verts:  # flatten onto the plane y = -0.92
        v.co.y = max(v.co.y, -0.92)
    select_only(bm, faces=faces)
    bpy.context.tool_settings.mesh_select_mode = (False, False, True)
    bmesh.update_edit_mesh(obj.data)
    before = max(abs(v.co.length - 1.0) for v in verts)
    bpy.ops.mesh.st3e_flow_element()
    bm = bmesh.from_edit_mesh(obj.data)
    after = max(abs(v.co.length - 1.0) for v in bm.verts if v.select)
    check("face flow rebuilds a flattened sphere patch", before > 0.02 and after < 1e-3,
          f"{len(faces)} faces, error {before:.4f} -> {after:.2e}")


def irregular_smoke():
    obj = fresh(bpy.ops.mesh.primitive_monkey_add)
    bm = bmesh.from_edit_mesh(obj.data)
    select_only(bm, faces=list(bm.faces)[::7])
    bmesh.update_edit_mesh(obj.data)
    ok = all(bpy.ops.mesh.st3e_flow_element(mode=m) in ({'FINISHED'}, {'CANCELLED'})
             for m in ('VERTEX', 'EDGE', 'FACE'))
    check("Suzanne (poles, triangles, borders) runs in every mode", ok)


def nothing_selected():
    obj = ringed_cylinder()
    bm = bmesh.from_edit_mesh(obj.data)
    select_only(bm)
    bmesh.update_edit_mesh(obj.data)
    check("empty selection cancels", bpy.ops.mesh.st3e_flow_element() == {'CANCELLED'})


for name, fn in list(globals().items()):
    if name in ("edge_flow_cylinder", "mix_half", "vertex_flow_sphere", "face_flow_sphere",
                "irregular_smoke", "nothing_selected"):
        run(name, fn)

addon.unregister()
print(f"\n{len(failures)} failure(s)")
sys.exit(1 if failures else 0)
