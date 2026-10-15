"""Drive a REAL Blender UI with simulated input to test Live mode end to end.

    Xvfb :99 -screen 0 1600x1000x24 &
    DISPLAY=:99 blender --factory-startup --enable-event-simulate \
        --python gui_drive.py -- <addon_parent_dir> <out_dir>

Native operators only: the R key, the Move-tool gizmo, the S key, Ctrl+Z /
Ctrl+Shift+Z. Each step checks the mesh and grabs the X display (needs
`xwd` + ImageMagick `convert`), so the screenshots are the actual viewport.
Prints PASS/FAIL lines and exits 1 on failure.
"""

import math
import os
import subprocess
import sys

import bmesh
import bpy
from bpy_extras.view3d_utils import location_3d_to_region_2d
from mathutils import Euler, Vector

argv = sys.argv[sys.argv.index("--") + 1:]
sys.path.insert(0, os.path.abspath(argv[0]))
OUT = os.path.abspath(argv[1])
os.makedirs(OUT, exist_ok=True)

import EdgeConstraintMode  # noqa: E402

FAILS = []


def ops_log(tag):
    print(f"OPS {tag}:", [o.bl_idname for o in bpy.context.window_manager.operators][-4:], flush=True)


def check(cond, msg):
    print(("PASS " if cond else "FAIL ") + msg, flush=True)
    if not cond:
        FAILS.append(msg)


def win():
    return bpy.context.window_manager.windows[0]


def view3d():
    for area in win().screen.areas:
        if area.type == 'VIEW_3D':
            region = next(r for r in area.regions if r.type == 'WINDOW')
            return area, region, area.spaces.active.region_3d
    raise RuntimeError("no 3D view")


def capture(name):
    area, _region, _rv3d = view3d()
    full = os.path.join(OUT, f"_{name}_full.png")
    dst = os.path.join(OUT, f"{name}.png")
    disp = os.environ.get("DISPLAY", ":99")
    subprocess.run(["sh", "-c", f"xwd -root -display {disp} | convert xwd:- png:{full}"], check=True)
    # X origin is top-left, Blender's window origin bottom-left.
    top = win().height - (area.y + area.height)
    subprocess.run(["convert", full, "-crop", f"{area.width}x{area.height}+{area.x}+{top}",
                    "+repage", dst], check=True)
    os.remove(full)
    print("SHOT", dst, flush=True)


def to_win(p2d):
    _area, region, _rv3d = view3d()
    return int(region.x + p2d.x), int(region.y + p2d.y)


def screen_of(world_pt):
    _area, region, rv3d = view3d()
    return location_3d_to_region_2d(region, rv3d, Vector(world_pt))


def ev(type, value='NOTHING', **kw):
    win().event_simulate(type=type, value=value, **kw)


_cursor = [0, 0]


def mouse(x, y):
    _cursor[:] = [x, y]
    ev('MOUSEMOVE', x=x, y=y)


def key(k, ctrl=False, shift=False):
    # Key events need the cursor position too, or they land at window (0, 0)
    # (the timeline), not in the 3D view. Modifiers are real key presses:
    # passing ctrl=True as a flag leaves Ctrl logically held afterwards
    # (later drags then snap in 1 m increments).
    x, y = _cursor
    mods = [m for m, on in (('LEFT_CTRL', ctrl), ('LEFT_SHIFT', shift)) if on]
    for m in mods:
        ev(m, 'PRESS', x=x, y=y, ctrl=ctrl, shift=shift)
    ev(k, 'PRESS', x=x, y=y, ctrl=ctrl, shift=shift)
    ev(k, 'RELEASE', x=x, y=y, ctrl=ctrl, shift=shift)
    for m in reversed(mods):
        ev(m, 'RELEASE', x=x, y=y)       # flags cleared -> modifiers up again


def sel_world(obj):
    bm = bmesh.from_edit_mesh(obj.data)
    return {v.index: obj.matrix_world @ v.co for v in bm.verts if v.select}


def all_world(obj):
    bm = bmesh.from_edit_mesh(obj.data)
    return [obj.matrix_world @ v.co for v in bm.verts]


def on_cube_edges(obj, loop):
    """Loop verts still on the 4 vertical cube edges, every vert inside the box."""
    ok = all(all(abs(c) <= 1 + 1e-4 for c in p) for p in all_world(obj))
    for p in sel_world(obj).values():
        ok &= abs(abs(p.x) - 1) < 1e-4 and abs(abs(p.y) - 1) < 1e-4
    return ok


# ---------------------------------------------------------------------------

STATE = {}


def make_loop_cube():
    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o)
    me = bpy.data.meshes.new("LoopCube")
    obj = bpy.data.objects.new("LoopCube", me)
    bpy.context.scene.collection.objects.link(obj)
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=2.0)
    bmesh.ops.bisect_plane(bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:],
                           plane_co=(0, 0, 0), plane_no=(0, 0, 1))
    for v in bm.verts:
        v.select = abs(v.co.z) < 1e-5
    bm.select_flush(True)
    bm.to_mesh(me)
    bm.free()
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    return obj


def make_frustum_loop():
    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o)
    me = bpy.data.meshes.new("Frustum")
    obj = bpy.data.objects.new("Frustum", me)
    bpy.context.scene.collection.objects.link(obj)
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, segments=16, radius1=1.6, radius2=0.7, depth=2.4)
    bmesh.ops.bisect_plane(bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:],
                           plane_co=(0, 0, 0.3), plane_no=(0, 0, 1))
    for v in bm.verts:
        v.select = abs(v.co.z - 0.3) < 1e-5
    bm.select_flush(True)
    bm.to_mesh(me)
    bm.free()
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    return obj


def frame_view(rot_deg=(62, 0, 38), dist=8.0, loc=(0, 0, 0)):
    _area, _region, rv3d = view3d()
    rv3d.view_perspective = 'PERSP'
    rv3d.view_rotation = Euler([math.radians(a) for a in rot_deg]).to_quaternion()
    rv3d.view_distance = dist
    rv3d.view_location = loc


def new_object(name, build):
    """Fresh single-object scene; build(bm) makes geometry + selection."""
    if bpy.context.object is not None and bpy.context.object.mode != 'OBJECT':
        bpy.ops.object.mode_set(mode='OBJECT')
    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o)
    me = bpy.data.meshes.new(name)
    obj = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(obj)
    bm = bmesh.new()
    build(bm)
    bm.select_flush(True)
    bm.to_mesh(me)
    bm.free()
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.ed.undo_push(message="test setup")
    return obj


def key_drag(k, center, start_off, path):
    """Press key k with the cursor at center+start_off, then follow path."""
    mouse(*to_win(center + Vector(start_off)))
    yield 0.4
    key(k)
    yield 0.4
    for off in path:
        mouse(*to_win(center + Vector(off)))
        yield 0.12
    yield 0.6


def confirm():
    ev('LEFTMOUSE', 'PRESS', x=_cursor[0], y=_cursor[1])
    ev('LEFTMOUSE', 'RELEASE', x=_cursor[0], y=_cursor[1])


def arc(radius, deg_to, step=3):
    return [(radius * math.cos(math.radians(a)), radius * math.sin(math.radians(a)))
            for a in range(step, deg_to + 1, step)]


def same_azimuth(p, q):
    d = math.atan2(p.y, p.x) - math.atan2(q.y, q.x)
    return abs((d + math.pi) % (2 * math.pi) - math.pi) < 1e-4


def more_objects(s):
    from mathutils.bvhtree import BVHTree

    # ---- 6. Cylinder: R on a loop (Edge) ---------------------------------
    def cyl(bm):
        bmesh.ops.create_cone(bm, cap_ends=True, segments=24, radius1=1.0, radius2=1.0, depth=3.0)
        bmesh.ops.bisect_plane(bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:],
                               plane_co=(0, 0, 0.3), plane_no=(0, 0, 1))
        for v in bm.verts:
            v.select = abs(v.co.z - 0.3) < 1e-5
    obj = new_object("Cylinder", cyl)
    s.mode, s.enabled = 'EDGE', True
    frame_view((68, 0, 25), 10.0, (0, 0, 0.2))
    yield 1.0
    capture("gui_10a_cylinder_before")
    before = sel_world(obj)
    c = screen_of(sum(before.values(), Vector()) / len(before))
    yield from key_drag('R', c, (200, 0), arc(200, 27))
    after = sel_world(obj)
    ok = all(abs(math.hypot(p.x, p.y) - 1.0) < 1e-4 and
             same_azimuth(p, before[i])
             for i, p in after.items())
    zs = [p.z for p in after.values()]
    check(ok and max(zs) - min(zs) > 0.3,
          f"cylinder R (Edge): loop tilts along the vertical edges, still a cylinder (z span {max(zs) - min(zs):.2f})")
    capture("gui_10_cylinder_rotate")
    confirm()
    yield 0.8

    # ---- 7. UV sphere: R on the equator (Edge) ---------------------------
    def sph(bm):
        bmesh.ops.create_uvsphere(bm, u_segments=24, v_segments=16, radius=1.4)
        for v in bm.verts:
            v.select = abs(v.co.z) < 1e-4
    obj = new_object("Sphere", sph)
    frame_view((70, 0, 25), 9.5)
    yield 1.0
    capture("gui_11a_sphere_before")
    before = sel_world(obj)
    c = screen_of(Vector())
    yield from key_drag('R', c, (200, 0), arc(200, 30))
    after = sel_world(obj)
    ok = all(same_azimuth(p, before[i])
             and p.length <= 1.4 + 1e-4 for i, p in after.items())
    zs = [p.z for p in after.values()]
    check(ok and max(zs) - min(zs) > 0.4,
          f"sphere R (Edge): equator slides along the meridians (z span {max(zs) - min(zs):.2f})")
    capture("gui_11_sphere_rotate")
    confirm()
    yield 0.8

    # ---- 8. Terrain: G on a patch (Face) ---------------------------------
    def height(x, y):
        return 0.35 * math.sin(1.7 * x) * math.cos(1.7 * y)

    def terrain(bm):
        bmesh.ops.create_grid(bm, x_segments=28, y_segments=28, size=3.0)
        for v in bm.verts:
            v.co.z = height(v.co.x, v.co.y)
            v.select = abs(v.co.x + 1.0) < 0.5 and abs(v.co.y) < 0.5
    obj = new_object("Terrain", terrain)
    bpy.ops.mesh.select_mode(type='FACE')
    s.mode, s.reach = 'FACE', 12
    frame_view((42, 0, 8), 9.0)
    yield 1.0
    capture("gui_12a_terrain_before")
    bm = bmesh.from_edit_mesh(obj.data)
    tree = BVHTree.FromBMesh(bm)          # the untouched surface
    before = sel_world(obj)
    c = screen_of(sum(before.values(), Vector()) / len(before))
    yield from key_drag('G', c, (0, 0), [(8 * k, 2 * k) for k in range(1, 16)])
    after = sel_world(obj)
    dist = max(tree.find_nearest(p)[3] for p in after.values())
    shifts = [after[i].x - before[i].x for i in before]
    check(dist < 1e-3 and min(shifts) > 0.3,
          f"terrain G (Face): whole patch slides over the bumps (off-surface {dist:.1e}, "
          f"X shift {min(shifts):.2f}..{max(shifts):.2f})")
    capture("gui_12_terrain_face_move")
    confirm()
    yield 0.8
    s.reach = 4

    # ---- 9. Icosphere: G on a cap (Normal) --------------------------------
    def ico(bm):
        bmesh.ops.create_icosphere(bm, subdivisions=3, radius=1.4)
        for v in bm.verts:
            v.select = v.co.z > 0.9
    obj = new_object("Icosphere", ico)
    s.mode = 'NORMAL'
    frame_view((72, 0, 20), 9.0)
    yield 1.0
    capture("gui_13a_icosphere_before")
    bm = bmesh.from_edit_mesh(obj.data)
    normals = {v.index: v.normal.copy() for v in bm.verts if v.select}
    before = sel_world(obj)
    c = screen_of(sum(before.values(), Vector()) / len(before))
    yield from key_drag('G', c, (0, 0), [(0, 7 * k) for k in range(1, 14)])
    after = sel_world(obj)
    par = max((after[i] - before[i]).cross(normals[i]).length for i in before)
    moved = max((after[i] - before[i]).length for i in before)
    check(par < 1e-4 and moved > 0.1,
          f"icosphere G (Normal): every vert moves along its own normal (off-normal {par:.1e}, max {moved:.2f})")
    capture("gui_13_icosphere_normal_move")
    confirm()
    yield 0.8

    # ---- 10. Extrude (E) is NOT constrained ------------------------------
    def top_face(bm):
        bmesh.ops.create_cube(bm, size=2.0)
        for f in bm.faces:
            f.select = f.normal.z > 0.9
    obj = new_object("ExtrudeCube", top_face)
    bpy.ops.mesh.select_mode(type='FACE')
    s.mode, s.enabled = 'EDGE', True
    frame_view((65, 0, 30), 10.0)
    yield 1.0
    nverts = len(all_world(obj))
    c = screen_of(Vector((0, 0, 1)))
    yield from key_drag('E', c, (0, 0), [(0, 6 * k) for k in range(1, 12)])
    confirm()
    yield 0.8
    zs = [p.z for p in sel_world(obj).values()]
    check(len(all_world(obj)) == nverts + 4 and min(zs) > 1.2,
          f"extrude E with Edge on: extrusion is free, not constrained (top at z={min(zs):.2f})")
    capture("gui_14_extrude_unconstrained")

    # ---- 11. Pivot = 3D cursor: R drag rotates about the cursor -----------
    ts = bpy.context.scene.tool_settings

    def loop_cube(cuts, select_z):
        # Select while building (before Edit mode): a selection changed by a
        # script inside Edit mode isn't a registered operator, which the
        # pre-4.2 fallback detection would read as the start of a drag.
        def build(bm):
            bmesh.ops.create_cube(bm, size=2.0)
            for z in sorted(cuts, reverse=True):
                bmesh.ops.bisect_plane(bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:],
                                       plane_co=(0, 0, z), plane_no=(0, 0, 1))
            for v in bm.verts:
                v.select = any(abs(v.co.z - z) < 1e-5 for z in select_z)
        return build

    bpy.ops.object.mode_set(mode='OBJECT')
    obj = new_object("CursorPivot", loop_cube([0.0], [0.0]))
    bpy.ops.mesh.select_mode(type='VERT')
    ts.transform_pivot_point = 'CURSOR'
    bpy.context.scene.cursor.location = (2.6, 0.0, 0.0)
    s.mode, s.enabled = 'EDGE', True
    frame_view((75, 0, 0), 11.0, (1.0, 0, 0))
    yield 1.0
    capture("gui_15a_cursor_pivot_before")
    cur = screen_of(bpy.context.scene.cursor.location)
    yield from key_drag('R', cur, (-230, 0), [(-230 * math.cos(math.radians(a)), -230 * math.sin(math.radians(a)))
                                             for a in range(2, 21, 2)])
    sel = sel_world(obj)
    on_rails = all(abs(abs(p.x) - 1) < 1e-4 and abs(abs(p.y) - 1) < 1e-4 for p in sel.values())
    mean_z = sum(p.z for p in sel.values()) / len(sel)
    zs = [p.z for p in sel.values()]
    check(on_rails and abs(mean_z) > 0.3,
          f"pivot 3D cursor, R drag: loop swings about the cursor along the edges "
          f"(mean z {mean_z:+.2f}, span {max(zs) - min(zs):.2f})")
    capture("gui_15_cursor_pivot_rotate")
    confirm()
    yield 0.8

    # ---- 12. Pivot = Individual Origins: each loop about its own centre ---
    obj = new_object("IndividualPivot", loop_cube([-0.6, 0.0, 0.6], [-0.6, 0.6]))
    ts.transform_pivot_point = 'INDIVIDUAL_ORIGINS'
    bpy.context.scene.cursor.location = (0, 0, 0)
    frame_view((75, 0, 0), 9.0)
    yield 1.0
    capture("gui_16a_individual_before")
    c = screen_of(Vector((0, 0, 0)))
    yield from key_drag('R', c, (200, 0), arc(200, 15))
    sel = sel_world(obj)
    lower = [p for p in sel.values() if p.z < 0]
    upper = [p for p in sel.values() if p.z > 0]
    on_rails = all(abs(abs(p.x) - 1) < 1e-4 and abs(abs(p.y) - 1) < 1e-4 for p in sel.values())
    ml = sum(p.z for p in lower) / max(len(lower), 1)
    mu = sum(p.z for p in upper) / max(len(upper), 1)
    span = max(p.z for p in upper) - min(p.z for p in upper)
    check(on_rails and len(lower) == len(upper) == 4 and abs(ml + 0.6) < 1e-3 and abs(mu - 0.6) < 1e-3
          and span > 0.25,
          f"pivot individual origins, R drag: each loop tilts about its own centre "
          f"(centres z {ml:+.3f} / {mu:+.3f}, tilt span {span:.2f})")
    capture("gui_16_individual_rotate")
    confirm()
    yield 0.8
    ts.transform_pivot_point = 'MEDIAN_POINT'


def steps():
    """Generator of (delay, label); each yield lets Blender process + redraw."""
    s = bpy.context.scene.edge_constraint_mode
    print("STEP setup", flush=True)
    # Close the splash screen; it would swallow the first key presses.
    _a, region, _r = view3d()
    mouse(region.x + 40, region.y + 40)
    key('ESC')
    yield 1.0

    # ---- 1. R key on a cube loop ---------------------------------------
    obj = make_loop_cube()
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.ed.undo_push(message="test setup")   # scripted setup isn't an undo step
    frame_view()
    s.mode = 'EDGE'
    s.enabled = True
    yield 1.0
    capture("gui_00_cube_loop_selected")
    piv = Vector((0, 0, 0))
    c = screen_of(piv)
    start = c + Vector((180, 0))
    mouse(*to_win(start))
    yield 0.4
    key('R')
    yield 0.4
    for a in range(1, 31, 3):
        r = math.radians(a)
        mouse(*to_win(c + Vector((180 * math.cos(r), 180 * math.sin(r)))))
        yield 0.15
    yield 0.6
    check(on_cube_edges(obj, None), "R drag (live, before confirm): loop verts stay on the cube's vertical edges")
    zs = [p.z for p in sel_world(obj).values()]
    check(max(zs) - min(zs) > 0.3, f"R drag: loop is being sheared (z span {max(zs) - min(zs):.3f})")
    capture("gui_01_rotate_dragging")
    x, y = to_win(c + Vector((180 * math.cos(math.radians(30)), 180 * math.sin(math.radians(30)))))
    ev('LEFTMOUSE', 'PRESS', x=x, y=y)
    ev('LEFTMOUSE', 'RELEASE', x=x, y=y)
    yield 0.8
    check(on_cube_edges(obj, None), "R confirmed: cube is still a cube")
    rotated = {i: p.copy() for i, p in sel_world(obj).items()}
    capture("gui_02_rotate_confirmed")

    # ---- 2. Undo / redo keep the constrained result ---------------------
    key('Z', ctrl=True)
    yield 0.8
    check(all(abs(p.z) < 1e-4 for p in sel_world(obj).values()), "Ctrl+Z: loop back to flat")
    key('Z', ctrl=True, shift=True)
    yield 0.8
    redo = sel_world(obj)
    check(all((redo[i] - rotated[i]).length < 1e-4 for i in rotated),
          "Ctrl+Shift+Z: redo restores the CONSTRAINED result (undo step stored it)")

    # ---- 3. Move-tool gizmo: drag the centre circle diagonally ----------
    with bpy.context.temp_override(window=win(), area=view3d()[0]):
        bpy.ops.wm.tool_set_by_id(name="builtin.move")
    yield 0.8
    before = {i: p.copy() for i, p in sel_world(obj).items()}
    med = sum(before.values(), Vector()) / len(before)
    c = screen_of(med)
    x0, y0 = to_win(c)
    mouse(x0, y0)
    yield 0.4
    capture("gui_03_move_gizmo")
    ev('LEFTMOUSE', 'PRESS', x=x0, y=y0)
    yield 0.3
    # The first moves only cross the drag threshold; keep going after that.
    for k in range(1, 4):              # open the drag (tweak threshold)
        mouse(x0 + 10 * k, y0 + 10 * k)
        yield 0.12
    for k in range(1, 9):
        mouse(x0 + 30 + 3 * k, y0 + 30 + 3 * k)
        yield 0.12
    yield 0.6
    after = sel_world(obj)
    check(on_cube_edges(obj, None), "Move gizmo drag (live): verts slid only along the vertical edges")
    moved = max((after[i] - before[i]).length for i in before)
    check(moved > 0.05, f"Move gizmo drag: selection actually moved ({moved:.3f})")
    capture("gui_04_move_gizmo_dragging")
    ev("LEFTMOUSE", "RELEASE", x=x0 + 54, y=y0 + 54)
    yield 0.8
    check(on_cube_edges(obj, None), "Move gizmo released: cube is still a cube")
    capture("gui_05_move_gizmo_done")

    # ---- 4. S key on a frustum loop --------------------------------------
    with bpy.context.temp_override(window=win(), area=view3d()[0]):
        bpy.ops.wm.tool_set_by_id(name="builtin.select_box")
    yield 0.4
    bpy.ops.object.mode_set(mode='OBJECT')
    obj = make_frustum_loop()
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.ed.undo_push(message="test setup")
    frame_view((70, 0, 30), 9.0, (0, 0, 0))
    yield 1.0
    capture("gui_06_frustum_loop_selected")
    piv = sum(sel_world(obj).values(), Vector()) / len(sel_world(obj))
    c = screen_of(piv)
    mouse(*to_win(c + Vector((120, 0))))
    yield 0.4
    key('S')
    yield 0.4
    for k in range(1, 9):
        mouse(*to_win(c + Vector((120 + 10 * k, 0))))
        yield 0.12
    yield 0.6
    ops_log("after S drag")
    sel = sel_world(obj)
    # slant radius r(z) = 1.15 - 0.375 z  (radius 1.6 at z=-1.2, 0.7 at z=1.2)
    on_slant = all(abs(math.hypot(p.x, p.y) - (1.15 - 0.375 * p.z)) < 1e-3 for p in sel.values())
    check(on_slant, "S drag (live): loop verts stay on the frustum's slanted edges")
    check(all(p.z < 0.29 for p in sel.values()), "S drag: scaling up slid the loop down the slope")
    capture("gui_07_scale_dragging")
    x, y = to_win(c + Vector((200, 0)))
    ev('LEFTMOUSE', 'PRESS', x=x, y=y)
    ev('LEFTMOUSE', 'RELEASE', x=x, y=y)
    yield 0.8
    capture("gui_08_scale_confirmed")

    # ---- 5. Toggle off: native behaviour is untouched --------------------
    s.enabled = False
    yield 0.4
    before = {i: p.copy() for i, p in sel_world(obj).items()}
    mouse(*to_win(c + Vector((120, 0))))
    yield 0.3
    key('S')
    yield 0.3
    for k in range(1, 6):
        mouse(*to_win(c + Vector((120 + 10 * k, 0))))
        yield 0.12
    ev('LEFTMOUSE', 'PRESS', x=x, y=y)
    ev('LEFTMOUSE', 'RELEASE', x=x, y=y)
    yield 0.8
    after = sel_world(obj)
    check(all(abs(after[i].z - before[i].z) < 1e-4 for i in before) and
          any((after[i] - before[i]).length > 0.05 for i in before),
          "Toggle off: S is Blender's plain scale again (no slide)")
    yield 0.2
    yield from more_objects(s)


_gen = None


def tick():
    global _gen
    try:
        if _gen is None:
            print("STEP register", flush=True)
            EdgeConstraintMode.register()
            _gen = steps()
        return next(_gen)
    except StopIteration:
        print("GUI DRIVE DONE:", "OK" if not FAILS else f"{len(FAILS)} FAILED", flush=True)
        os._exit(1 if FAILS else 0)
    except Exception:
        import traceback
        traceback.print_exc()
        os._exit(2)


bpy.app.timers.register(tick, first_interval=2.0)
