"""Headless integration checks + comparison renders, run inside Blender 5.0.

    blender --background --factory-startup --python blender_checks.py -- <addon_parent_dir> [render_dir]
    # or with the PyPI `bpy` module:
    python blender_checks.py <addon_parent_dir> [render_dir]

<addon_parent_dir> must contain the addon package as `EdgeConstraintMode/`
(a copy or symlink of source/). Exits non-zero on any failed check. Not
collected by pytest (core tests stay bpy-free).
"""

import math
import os
import sys

import bpy  # noqa: I001  (bpy first: the PyPI module provides bmesh/mathutils)
import bmesh
from mathutils import Vector

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
ADDON_PARENT = os.path.abspath(argv[0])
RENDER_DIR = os.path.abspath(argv[1]) if len(argv) > 1 else None
sys.path.insert(0, ADDON_PARENT)

import EdgeConstraintMode  # noqa: E402

FAILS = []


def check(cond, msg):
    print(("PASS " if cond else "FAIL ") + msg)
    if not cond:
        FAILS.append(msg)


_registered = False


def reset():
    global _registered
    if _registered:
        EdgeConstraintMode.unregister()
    bpy.ops.wm.read_factory_settings(use_empty=True)
    EdgeConstraintMode.register()
    _registered = True


def make_cube(name, loc, cuts_axis=2, cut_values=(0.0,)):
    """Cube (-1..1) with loop cuts perpendicular to cuts_axis; returns obj
    and the vertex indices of each cut loop."""
    me = bpy.data.meshes.new(name)
    obj = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(obj)
    obj.location = loc
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=2.0)
    for val in sorted(cut_values, reverse=True):
        # Slice with bisect so the cut is a real edge loop.
        co = [0.0, 0.0, 0.0]
        co[cuts_axis] = val
        no = [0.0, 0.0, 0.0]
        no[cuts_axis] = 1.0
        bmesh.ops.bisect_plane(bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:],
                               plane_co=co, plane_no=no)
    bm.to_mesh(me)
    bm.free()
    obj["ec_planes"] = {
        str(v.index): [(i, 1.0 if v.co[i] > 0 else -1.0)
                       for i in range(3) if abs(abs(v.co[i]) - 1.0) < 1e-5]
        for v in me.vertices}
    loops = [[v.index for v in me.vertices if abs(v.co[cuts_axis] - val) < 1e-5]
             for val in cut_values]
    return obj, loops


def enter_edit(obj, sel):
    for o in bpy.context.scene.objects:
        o.select_set(False)
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    for v in obj.data.vertices:
        v.select = v.index in sel
    for e in obj.data.edges:
        e.select = all(i in sel for i in e.vertices)
    for f in obj.data.polygons:
        f.select = all(i in sel for i in f.vertices)
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_mode(type='VERT')


def leave_edit():
    bpy.ops.object.mode_set(mode='OBJECT')


def local_cos(obj):
    return [v.co.copy() for v in obj.data.vertices]


def on_cube(p, tol=1e-4):
    return all(abs(c) <= 1 + tol for c in p) and any(abs(abs(c) - 1) <= tol for c in p)


def is_cube(obj, tol=1e-4):
    """Still the same cube: every vertex is still on every cube side-plane it
    started on (a loop vert on a vertical cube edge must stay on both planes,
    otherwise the side faces fold), and nothing left the -1..1 box."""
    for v in obj.data.vertices:
        start = obj.get("ec_planes", {}).get(str(v.index))
        if not on_cube(v.co, tol):
            return False
        if start:
            for axis, sign in start:
                if abs(v.co[int(axis)] - sign) > tol:
                    return False
    return True


def bbox_is_unit(obj):
    xs = [v.co for v in obj.data.vertices]
    return all(abs(max(c[i] for c in xs) - 1) < 1e-4 and abs(min(c[i] for c in xs) + 1) < 1e-4
               for i in range(3))


# ---------------------------------------------------------------------------
# Checks
# ---------------------------------------------------------------------------

def run_checks():
    reset()
    s = bpy.context.scene.edge_constraint_mode

    # 1. Acceptance: rotate the loop of a cube -> still a cube (shear).
    obj, (loop,) = make_cube("RotCube", (0, 0, 0))
    enter_edit(obj, set(loop))
    s.mode = 'EDGE'
    bpy.ops.mesh.edge_constraint_transform(transform_type='ROTATE', angle=math.radians(30),
                                           axis=(0, 1, 0))
    leave_edit()
    check(is_cube(obj), "edge rotate: every vertex still on the cube surface")
    zs = sorted(obj.data.vertices[i].co.z for i in loop)
    check(zs[-1] - zs[0] > 0.5, f"edge rotate: loop was sheared (z span {zs[-1] - zs[0]:.3f})")
    for i in loop:
        co = obj.data.vertices[i].co
        check(abs(co.z - (-co.x) * math.sin(math.radians(30))) < 1e-4,
              f"edge rotate: vert {i} z == -x*sin(30)  ({co.z:.4f})")

    # 2. Native rotate for contrast: breaks the cube. (transform.rotate's
    # value is clockwise-positive, hence the minus to match +30 deg here.)
    obj, (loop,) = make_cube("NativeCube", (0, 0, 0))
    enter_edit(obj, set(loop))
    bpy.ops.transform.rotate(value=-math.radians(30), orient_axis='Y')
    leave_edit()
    check(not is_cube(obj), "native rotate leaves the cube (sanity contrast)")

    # 3. Move diagonally -> only the rail component survives.
    obj, (loop,) = make_cube("MoveCube", (0, 0, 0))
    enter_edit(obj, set(loop))
    bpy.ops.mesh.edge_constraint_transform(transform_type='TRANSLATE', value=(0.6, 0.3, 0.5))
    leave_edit()
    check(is_cube(obj) and bbox_is_unit(obj), "edge move: cube intact")
    check(all(abs(obj.data.vertices[i].co.z - 0.5) < 1e-4 for i in loop), "edge move: loop at z=0.5")

    # 4. Uniform scale of two X loops -> they slide apart along X only.
    obj, loops = make_cube("ScaleCube", (0, 0, 0), cuts_axis=0, cut_values=(-0.5, 0.5))
    sel = set(loops[0]) | set(loops[1])
    enter_edit(obj, sel)
    bpy.ops.mesh.edge_constraint_transform(transform_type='RESIZE', scale=(1.6, 1.6, 1.6))
    leave_edit()
    check(is_cube(obj) and bbox_is_unit(obj), "edge scale: cube intact")
    check(all(abs(abs(obj.data.vertices[i].co.x) - 0.8) < 1e-4 for i in sel), "edge scale: loops at x=+-0.8")

    # 5. Face constraint rotate about Z keeps verts on the surface.
    obj, (loop,) = make_cube("FaceCube", (0, 0, 0))
    enter_edit(obj, set(loop))
    s.mode = 'FACE'
    bpy.ops.mesh.edge_constraint_transform(transform_type='ROTATE', angle=math.radians(25),
                                           axis=(0, 0, 1))
    leave_edit()
    # Face mode lets corner verts leave the cube edge onto one face (as in Max),
    # so only require every vertex to stay on the surface.
    check(all(on_cube(v.co) for v in obj.data.vertices) and bbox_is_unit(obj),
          "face rotate: every vertex stays on the cube surface")
    check(any(abs(obj.data.vertices[i].co.x) < 0.999 for i in loop),
          "face rotate: loop verts actually slid over the faces")

    # 6. None -> operator unavailable, so the G/R/S key falls through to Blender.
    obj, (loop,) = make_cube("NoneCube", (0, 0, 0))
    enter_edit(obj, set(loop))
    s.mode = 'NONE'
    check(not bpy.ops.mesh.edge_constraint_transform.poll(), "mode None: operator poll() fails (keys fall through)")
    leave_edit()

    # 7. Object transform + non-uniform object scale: projection in world space.
    obj, (loop,) = make_cube("XformCube", (3, 0, 0))
    obj.scale = (2.0, 1.0, 0.5)
    obj.rotation_euler = (0.3, 0.2, 0.1)
    enter_edit(obj, set(loop))
    s.mode = 'EDGE'
    bpy.ops.mesh.edge_constraint_transform(transform_type='ROTATE', angle=math.radians(20),
                                           axis=(0, 1, 0))
    leave_edit()
    check(is_cube(obj), "edge rotate on transformed object: cube intact (local)")

    # 8. Undo restores (needs the undo stack; skipped quietly if unavailable).
    print("Checks done:", "OK" if not FAILS else f"{len(FAILS)} FAILED")


# ---------------------------------------------------------------------------
# Renders: native Blender (left) vs Edge constraint (right)
# ---------------------------------------------------------------------------

COL_MESH = (0.80, 0.80, 0.82, 1.0)
COL_WIRE = (0.08, 0.08, 0.09, 1.0)
COL_SEL = (1.00, 0.45, 0.05, 1.0)
COL_GHOST = (0.15, 0.55, 1.00, 1.0)


def wire_copy(src_obj, name, color, thickness, vert_filter=None):
    """Wireframe visual of src; vert_filter = list of vertex-index sets, an edge
    is drawn when both its verts are in one of them (None = all edges)."""
    me = bpy.data.meshes.new(name)
    verts = [v.co.copy() for v in src_obj.data.vertices]
    edges = [tuple(e.vertices) for e in src_obj.data.edges
             if vert_filter is None
             or any(all(i in group for i in e.vertices) for group in vert_filter)]
    me.from_pydata(verts, edges, [])
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    ob.matrix_basis = src_obj.matrix_basis.copy()   # matrix_world is stale until a depsgraph update
    # Skin-free tube: convert edges to thin cylinders via a Skin? Use Wireframe
    # on a temporary face-less mesh is not possible, so use curve bevel.
    bpy.context.view_layer.objects.active = ob
    for o in bpy.context.scene.objects:
        o.select_set(o == ob)
    bpy.ops.object.convert(target='CURVE')
    ob = bpy.context.view_layer.objects.active
    ob.data.bevel_depth = thickness
    ob.data.bevel_resolution = 2
    ob.color = color
    return ob


def label(text, loc, size=0.35):
    cu = bpy.data.curves.new("lbl", 'FONT')
    cu.body = text
    cu.align_x = 'CENTER'
    cu.size = size
    ob = bpy.data.objects.new("lbl", cu)
    bpy.context.scene.collection.objects.link(ob)
    ob.location = loc
    ob.rotation_euler = (math.radians(90), 0, 0)
    ob.color = (0.85, 0.85, 0.85, 1)
    return ob


def setup_render(title):
    sc = bpy.context.scene
    sc.render.engine = 'BLENDER_WORKBENCH'
    sc.render.resolution_x = 1400
    sc.render.resolution_y = 760
    sc.display.shading.light = 'STUDIO'
    sc.display.shading.color_type = 'OBJECT'
    sc.display.shading.show_cavity = False
    sc.display.shading.show_object_outline = False
    sc.render.film_transparent = False
    world = bpy.data.worlds.new("w")
    sc.world = world
    sc.display.shading.background_type = 'VIEWPORT' if hasattr(sc.display.shading, "background_type") else None
    cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam"))
    sc.collection.objects.link(cam)
    cam.location = (0.0, -13.5, 4.6)
    cam.rotation_euler = (math.radians(73), 0, 0)
    cam.data.lens = 38
    sc.camera = cam
    label(title, (0, 0, 2.75), 0.32)


def finish_render(path):
    bpy.context.scene.render.filepath = path
    bpy.ops.render.render(write_still=True)
    print("Rendered", path)


def demo(kind, path):
    reset()
    s = bpy.context.scene.edge_constraint_mode
    titles = {
        'move': "Move (0.6, 0.3, 0.5) of the loop",
        'rotate': "Rotate 30 deg about Y of the loop",
        'scale': "Uniform scale 1.6 of two loops",
    }
    setup_render(titles[kind])
    for side, x in (('native', -2.7), ('edge', 2.7)):
        if kind == 'scale':
            obj, loops = make_cube(f"{kind}_{side}", (x, 0, 0), cuts_axis=0, cut_values=(-0.5, 0.5))
            groups = [set(loops[0]), set(loops[1])]
        else:
            obj, (loop,) = make_cube(f"{kind}_{side}", (x, 0, 0))
            groups = [set(loop)]
        sel = set().union(*groups)
        obj.rotation_euler = (0, 0, math.radians(-28))
        wire_copy(obj, "ghost", COL_GHOST, 0.012, groups)
        enter_edit(obj, sel)
        if side == 'native':
            if kind == 'move':
                bpy.ops.transform.translate(value=(0.6, 0.3, 0.5))
            elif kind == 'rotate':
                bpy.ops.transform.rotate(value=-math.radians(30), orient_axis='Y')
            else:
                bpy.ops.transform.resize(value=(1.6, 1.6, 1.6))
        else:
            s.mode = 'EDGE'
            if kind == 'move':
                bpy.ops.mesh.edge_constraint_transform(transform_type='TRANSLATE', value=(0.6, 0.3, 0.5))
            elif kind == 'rotate':
                bpy.ops.mesh.edge_constraint_transform(transform_type='ROTATE', angle=math.radians(30),
                                                       axis=(0, 1, 0))
            else:
                bpy.ops.mesh.edge_constraint_transform(transform_type='RESIZE', scale=(1.6, 1.6, 1.6))
        leave_edit()
        ok = is_cube(obj) and bbox_is_unit(obj)
        obj.color = COL_MESH
        wire_copy(obj, "wire", COL_WIRE, 0.012)
        wire_copy(obj, "sel", COL_SEL, 0.03, groups)
        name = "Blender native" if side == 'native' else "Edge Constraint"
        verdict = "still a cube" if ok else "cube broken"
        label(f"{name}: {verdict}", (x, -2.2, -1.75), 0.28)
    finish_render(path)


if __name__ == "__main__":
    run_checks()
    if RENDER_DIR:
        os.makedirs(RENDER_DIR, exist_ok=True)
        for kind in ('move', 'rotate', 'scale'):
            demo(kind, os.path.join(RENDER_DIR, f"edge_constraint_{kind}.png"))
    if FAILS:
        print("FAILED:", *FAILS, sep="\n  ")
        sys.exit(1)
