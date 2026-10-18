"""Render the demo media: every transform, multi-selections, several shapes.

Three steps (Blender's Python has no PIL, and there's no ffmpeg needed):

    blender -b --factory-startup --python demo_media.py -- render <addon_parent_dir> <frames_dir> [preview]
    python demo_media.py <frames_dir> <out_dir>          # captions, stills, GIF
    blender -b --factory-startup --python demo_media.py -- encode <png_dir> <out.mp4>

<addon_parent_dir> must contain the addon as `GeometryConstraint/` (as for
blender_checks.py). Each frame runs a NATIVE transform op at a fraction of its
final value through the live handler, the same way a drag frame does. Orange
is the constrained selection, the thin red ghost is what plain Blender would
do with the constraint off. `preview` renders one frame per segment.

Outputs in <out_dir>: captioned/ (1080p PNG frames), stills/ (clean and
captioned 1080p PNG at each segment's full transform) and a 960 px GIF.
"""

import json
import math
import os
import sys

FPS = 25
FORWARD, HOLD, BACK, REST = 20, 14, 14, 6
SIZE = (1920, 1080)
GIF_WIDTH = 960


# ---------------------------------------------------------------------------
# Step 2: plain Python + PIL
# ---------------------------------------------------------------------------

def assemble(frames_dir, out_dir):
    from PIL import Image, ImageDraw, ImageFont

    meta = json.load(open(os.path.join(frames_dir, "frames.json")))
    cap_dir = os.path.join(out_dir, "captioned")
    still_dir = os.path.join(out_dir, "stills")
    os.makedirs(cap_dir, exist_ok=True)
    os.makedirs(still_dir, exist_ok=True)
    k = SIZE[1] / 450.0

    def font(size, bold=False):
        for name in (("segoeuib.ttf", "arialbd.ttf", "DejaVuSans-Bold.ttf") if bold
                     else ("segoeui.ttf", "arial.ttf", "DejaVuSans.ttf")):
            try:
                return ImageFont.truetype(name, size)
            except OSError:
                pass
        return ImageFont.load_default()

    def s(v):
        return int(round(v * k))

    f_title, f_sub, f_small = font(s(26), True), font(s(18)), font(s(14))

    def caption(im, entry):
        d = ImageDraw.Draw(im)
        d.text((s(22), s(16)), entry["title"], font=f_title, fill=(235, 235, 235))
        d.text((s(22), s(50)), entry["subtitle"], font=f_sub, fill=(170, 170, 170))
        y = im.height - s(30)
        d.rectangle((s(22), y + s(4), s(34), y + s(16)), fill=(255, 140, 30))
        d.text((s(40), y), "constrained", font=f_small, fill=(200, 200, 200))
        d.rectangle((s(140), y + s(9), s(152), y + s(11)), fill=(230, 60, 60))
        d.text((s(158), y), "Blender without constraint", font=f_small, fill=(200, 200, 200))
        tag = "Geometry Constraint"
        w = d.textlength(tag, font=f_small)
        d.text((im.width - w - s(22), y), tag, font=f_small, fill=(130, 130, 130))
        return im

    gif = []
    gif_size = (GIF_WIDTH, round(GIF_WIDTH * SIZE[1] / SIZE[0]))
    for n, entry in enumerate(meta):
        clean = Image.open(os.path.join(frames_dir, entry["file"])).convert("RGB")
        im = caption(clean.copy(), entry)
        im.save(os.path.join(cap_dir, f"f{n:04d}.png"))
        if entry.get("still"):
            stem = f"{entry['segment'] + 1:02d}_{entry['slug']}"
            clean.save(os.path.join(still_dir, f"{stem}.png"))
            im.save(os.path.join(still_dir, f"{stem}_captioned.png"))
        if n % 2 == 0:        # GIF at half the frame rate keeps it small
            gif.append(im.resize(gif_size, Image.LANCZOS)
                       .quantize(colors=128, method=Image.Quantize.MEDIANCUT))
    out_gif = os.path.join(out_dir, "geometry_constraint_demo.gif")
    gif[0].save(out_gif, save_all=True, append_images=gif[1:], loop=0,
                duration=int(2000 / FPS), optimize=True, disposal=1)
    print(f"wrote {cap_dir} ({len(meta)} frames), {still_dir}, "
          f"{out_gif} ({os.path.getsize(out_gif) / 1e6:.1f} MB)")


def encode(png_dir, out_mp4):
    """PNG sequence -> H.264 MP4 through Blender's own FFmpeg."""
    import bpy

    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    files = sorted(f for f in os.listdir(png_dir) if f.endswith(".png"))
    scene.sequence_editor_create()
    strips = scene.sequence_editor.strips if hasattr(scene.sequence_editor, "strips") \
        else scene.sequence_editor.sequences
    strip = strips.new_image("frames", os.path.join(png_dir, files[0]), channel=1, frame_start=1)
    for f in files[1:]:
        strip.elements.append(f)
    r = scene.render
    r.resolution_x, r.resolution_y = SIZE
    r.resolution_percentage = 100
    r.fps = FPS
    scene.frame_start, scene.frame_end = 1, len(files)
    if hasattr(r.image_settings, "media_type"):
        r.image_settings.media_type = 'VIDEO'     # Blender 5.0: FFMPEG lives under VIDEO
    r.image_settings.file_format = 'FFMPEG'
    r.ffmpeg.format = 'MPEG4'
    r.ffmpeg.codec = 'H264'
    r.ffmpeg.constant_rate_factor = 'PERC_LOSSLESS'
    r.ffmpeg.ffmpeg_preset = 'BEST'
    r.ffmpeg.gopsize = FPS
    r.filepath = out_mp4
    bpy.ops.render.render(animation=True)
    print(f"wrote {out_mp4}: {len(files)} frames at {FPS} fps", flush=True)


# ---------------------------------------------------------------------------
# Step 1: inside Blender
# ---------------------------------------------------------------------------

def render_frames(addon_parent, frames_dir, preview=False):
    import bmesh
    import bpy
    from mathutils import Vector

    sys.path.insert(0, os.path.abspath(addon_parent))
    import GeometryConstraint
    from GeometryConstraint.blender import live

    os.makedirs(frames_dir, exist_ok=True)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    GeometryConstraint.register()
    scene = bpy.context.scene
    settings = scene.geometry_constraint

    # -- render setup --------------------------------------------------------
    scene.render.engine = 'BLENDER_WORKBENCH'
    scene.render.resolution_x, scene.render.resolution_y = SIZE
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = 'PNG'
    scene.display.render_aa = '8'
    sh = scene.display.shading
    sh.light = 'STUDIO'
    sh.color_type = 'OBJECT'
    sh.show_cavity = True
    sh.show_object_outline = True
    sh.object_outline_color = (0.02, 0.02, 0.02)
    world = bpy.data.worlds.new("Demo")
    world.color = (0.035, 0.035, 0.04)
    scene.world = world
    cam = bpy.data.objects.new("Cam", bpy.data.cameras.new("Cam"))
    cam.data.lens = 40
    cam.data.shift_y = 0.035          # leaves room for the captions on top
    scene.collection.objects.link(cam)
    scene.camera = cam

    def tube_tree(name, radius, point_radius=0.0):
        ng = bpy.data.node_groups.new(name, 'GeometryNodeTree')
        ng.interface.new_socket("Geometry", in_out='INPUT', socket_type='NodeSocketGeometry')
        ng.interface.new_socket("Geometry", in_out='OUTPUT', socket_type='NodeSocketGeometry')
        n = ng.nodes
        gi, go = n.new('NodeGroupInput'), n.new('NodeGroupOutput')
        m2c = n.new('GeometryNodeMeshToCurve')
        circ = n.new('GeometryNodeCurvePrimitiveCircle')
        circ.inputs["Resolution"].default_value = 8
        circ.inputs["Radius"].default_value = radius
        c2m = n.new('GeometryNodeCurveToMesh')
        ng.links.new(gi.outputs[0], m2c.inputs["Mesh"])
        ng.links.new(m2c.outputs[0], c2m.inputs["Curve"])
        ng.links.new(circ.outputs[0], c2m.inputs["Profile Curve"])
        out = c2m.outputs[0]
        if point_radius:
            pts = n.new('GeometryNodeMeshToPoints')
            ico = n.new('GeometryNodeMeshIcoSphere')
            ico.inputs["Radius"].default_value = point_radius
            ico.inputs["Subdivisions"].default_value = 2
            inst = n.new('GeometryNodeInstanceOnPoints')
            join = n.new('GeometryNodeJoinGeometry')
            ng.links.new(gi.outputs[0], pts.inputs["Mesh"])
            ng.links.new(pts.outputs[0], inst.inputs["Points"])
            ng.links.new(ico.outputs[0], inst.inputs["Instance"])
            ng.links.new(out, join.inputs[0])
            ng.links.new(inst.outputs[0], join.inputs[0])
            out = join.outputs[0]
        ng.links.new(out, go.inputs[0])
        return ng

    trees = {}

    def display(name, mesh, color, tree=None):
        ob = bpy.data.objects.new(name, mesh)
        ob.color = color
        scene.collection.objects.link(ob)
        if tree is not None:
            mod = ob.modifiers.new("tube", 'NODES')
            mod.node_group = tree
        return ob

    # -- shapes ------------------------------------------------------------------

    def bisect(bm, axis, values):
        for val in values:
            co, no = [0.0] * 3, [0.0] * 3
            co[axis], no[axis] = val, 1.0
            bmesh.ops.bisect_plane(bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:],
                                   plane_co=co, plane_no=no)

    def cube(cuts):
        bm = bmesh.new()
        bmesh.ops.create_cube(bm, size=2.0)
        bisect(bm, 2, cuts)
        return bm

    def skewed(cuts):
        # Sheared box: slanted side edges, so a loop sliding along them visibly
        # moves sideways too.
        bm = cube(cuts)
        for v in bm.verts:
            v.co.x += 0.45 * v.co.z
        return bm

    def frustum():
        bm = cube([0.0])
        for v in bm.verts:
            if v.co.z > 0.99:
                v.co.x *= 0.45
                v.co.y *= 0.45
        return bm

    def cylinder():
        bm = bmesh.new()
        bmesh.ops.create_cone(bm, cap_ends=True, segments=16, radius1=1.0, radius2=1.0, depth=2.0)
        bisect(bm, 2, [0.0])
        return bm

    def sphere():
        bm = bmesh.new()
        bmesh.ops.create_uvsphere(bm, u_segments=24, v_segments=12, radius=1.1)
        return bm

    def terrain():
        bm = bmesh.new()
        bmesh.ops.create_grid(bm, x_segments=14, y_segments=14, size=1.6)
        for v in bm.verts:
            x, y = v.co.x, v.co.y
            v.co.z = 0.22 * math.sin(2.6 * x) * math.cos(2.1 * y) + 0.12 * math.sin(4.0 * y + 1.0)
        return bm

    def icosphere():
        bm = bmesh.new()
        bmesh.ops.create_icosphere(bm, subdivisions=2, radius=1.0)
        return bm

    # Selections: (verts, edges) predicates on the ORIGINAL coordinates.
    def ring(z):
        return lambda co: abs(co.z - z) < 1e-4

    def front_edges(co):
        return abs(co.y + 1) < 1e-4 and abs(abs(co.z) - 0.5) < 1e-4

    def patch(co):
        return abs(co.x) < 0.5 and abs(co.y) < 0.5

    def cap(co):
        return co.z > 0.55

    def rot(axis, deg):
        return lambda t: bpy.ops.transform.rotate(value=math.radians(deg) * t, orient_axis=axis)

    def move(x, y, z):
        return lambda t: bpy.ops.transform.translate(value=(x * t, y * t, z * t))

    def scale(f, axis=None):
        """Uniform, or along one global axis ('X' / 'Y' / 'Z') like S Z."""
        def run(t):
            k = 1 + (f - 1) * t
            if axis is None:
                return bpy.ops.transform.resize(value=(k,) * 3)
            i = "XYZ".index(axis)
            value = [1.0, 1.0, 1.0]
            value[i] = k
            lock = [False, False, False]
            lock[i] = True
            return bpy.ops.transform.resize(value=value, orient_type='GLOBAL',
                                            constraint_axis=lock)
        return run

    segments = [
        # title, subtitle, shape, select, edge-mode select, mode, op, pivot, view
        ("Edge · Rotate (R)", "One loop: the rotation becomes a shear, the cube stays a cube",
         lambda: cube([0.0]), ring(0.0), False, 'EDGE', rot('Y', 35), 'MEDIAN_POINT', None),
        ("Edge · Move (G)", "The loop slides along the vertical edges and stops at the corners",
         lambda: cube([0.0]), ring(0.0), False, 'EDGE', move(0.5, 0.0, 1.2), 'MEDIAN_POINT', None),
        ("Edge · Scale Z (S Z)", "Two loops on a skewed box slide toward each other along its slanted edges",
         lambda: skewed([-0.6, 0.6]), lambda co: abs(abs(co.z) - 0.6) < 1e-4, False, 'EDGE',
         scale(0.2, 'Z'), 'MEDIAN_POINT', None),
        ("Edge · Rotate · Individual Origins", "Two loops, each tilting about its own centre",
         lambda: cube([-0.5, 0.5]), lambda co: abs(abs(co.z) - 0.5) < 1e-4, False, 'EDGE',
         rot('Y', 30), 'INDIVIDUAL_ORIGINS', None),
        ("Edge · Scale Z · two edges", "Edge select mode: the edges slide along the slanted edges joining them",
         lambda: skewed([-0.5, 0.5]), front_edges, True, 'EDGE', scale(1.8, 'Z'), 'MEDIAN_POINT', None),
        ("Edge · Rotate · two edges", "Rotating around Z slides them along the side edges",
         lambda: cube([-0.5, 0.5]), front_edges, True, 'EDGE', rot('Z', 25), 'MEDIAN_POINT', None),
        ("Edge · Scale X on a tapered box", "Scaling along X slides the loop down the slanted edges",
         frustum, ring(0.0), False, 'EDGE', scale(1.6, 'X'), 'MEDIAN_POINT', None),
        ("Edge · Rotate on a cylinder", "The loop tilts along the vertical edges, still a cylinder",
         cylinder, ring(0.0), False, 'EDGE', rot('X', 25), 'MEDIAN_POINT', None),
        ("Edge · Rotate on a sphere", "The equator slides along the meridians",
         sphere, ring(0.0), False, 'EDGE', rot('X', 25), 'MEDIAN_POINT', None),
        ("Face · Move (G)", "The patch slides over the terrain instead of leaving it",
         terrain, patch, False, 'FACE', move(0.9, 0.3, 0.0), 'MEDIAN_POINT', 'high'),
        ("Face · Rotate (R)", "Rotated in place, every vertex stays on the surface",
         terrain, patch, False, 'FACE', rot('Z', 40), 'MEDIAN_POINT', 'high'),
        ("Normal · Move (G)", "Each vertex moves only along its own normal",
         icosphere, cap, False, 'NORMAL', move(0.0, 0.0, 0.35), 'MEDIAN_POINT', None),
        ("Normal · Scale (S)", "Scaling pushes the patch out along the normals",
         icosphere, cap, False, 'NORMAL', scale(1.5), 'MEDIAN_POINT', None),
    ]

    win = bpy.context.window_manager.windows[0]
    area = next((a for a in win.screen.areas if a.type == 'VIEW_3D'), None)

    def in_view3d(fn):
        if area is None:
            return fn()
        region = next(r for r in area.regions if r.type == 'WINDOW')
        with bpy.context.temp_override(window=win, area=area, region=region):
            return fn()

    def ease(t):
        return 0.5 - 0.5 * math.cos(math.pi * t)

    timeline = ([ease(i / (FORWARD - 1)) for i in range(FORWARD)] + [1.0] * HOLD
                + [ease(1 - i / (BACK - 1)) for i in range(BACK)] + [0.0] * REST)
    still_at = FORWARD + HOLD // 2
    if preview:
        timeline, still_at = [1.0], 0

    meta = []
    frame_no = 0
    for si, (title, sub, make, pick, edge_sel, mode, op, pivot, view) in enumerate(segments):
        for ob in [o for o in scene.objects if o is not cam]:
            bpy.data.objects.remove(ob)
        bm = make()
        me = bpy.data.meshes.new(f"src{si}")
        bm.to_mesh(me)
        bm.free()
        src = bpy.data.objects.new(f"src{si}", me)
        src.hide_render = True
        scene.collection.objects.link(src)

        orig = [v.co.copy() for v in me.vertices]
        if edge_sel:
            sel_e = [e.index for e in me.edges if all(pick(orig[i]) for i in e.vertices)]
            sel_v = sorted({i for ei in sel_e for i in me.edges[ei].vertices})
        else:
            sel_v = [i for i, co in enumerate(orig) if pick(co)]
            sv = set(sel_v)
            sel_e = [e.index for e in me.edges if all(i in sv for i in e.vertices)]
        edges = [tuple(e.vertices) for e in me.edges]
        faces = [tuple(p.vertices) for p in me.polygons]

        disp = bpy.data.meshes.new(f"disp{si}")
        disp.from_pydata([tuple(c) for c in orig], edges, faces)
        remap = {v: k for k, v in enumerate(sel_v)}
        sub_edges = [(remap[edges[ei][0]], remap[edges[ei][1]]) for ei in sel_e]

        def sub_mesh(name):
            m = bpy.data.meshes.new(name)
            m.from_pydata([tuple(orig[i]) for i in sel_v], sub_edges, [])
            return m

        if not trees:
            trees["wire"] = tube_tree("wire", 0.008)
            trees["sel"] = tube_tree("sel", 0.022, point_radius=0.04)
            trees["ghost"] = tube_tree("ghost", 0.009, point_radius=0.022)
        display("solid", disp, (0.42, 0.42, 0.45, 1))
        display("wire", disp, (0.03, 0.03, 0.03, 1), trees["wire"])
        sel_ob = display("sel", sub_mesh("sel"), (1.0, 0.42, 0.05, 1), trees["sel"])
        ghost_ob = display("ghost", sub_mesh("ghost"), (0.85, 0.12, 0.12, 1), trees["ghost"])

        # camera: three-quarter view framing the shape
        lo = Vector([min(c[i] for c in orig) for i in range(3)])
        hi = Vector([max(c[i] for c in orig) for i in range(3)])
        centre = (lo + hi) / 2
        radius = (hi - lo).length / 2
        d = Vector((1.0, -1.35, 1.6 if view == 'high' else 0.75)).normalized()
        cam.location = centre + d * radius * (3.9 if view == 'high' else 4.6)
        cam.rotation_euler = (centre - cam.location).to_track_quat('-Z', 'Y').to_euler()

        # edit mode with the demo's selection
        for o in scene.objects:
            o.select_set(False)
        bpy.context.view_layer.objects.active = src
        src.select_set(True)
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_mode(type='EDGE' if edge_sel else 'VERT')
        ebm = bmesh.from_edit_mesh(me)
        ebm.verts.ensure_lookup_table()
        ebm.edges.ensure_lookup_table()
        for v in ebm.verts:
            v.select = False
        for e in ebm.edges:
            e.select = False
        for f in ebm.faces:
            f.select = False
        if edge_sel:
            for ei in sel_e:
                ebm.edges[ei].select = True
        else:
            for i in sel_v:
                ebm.verts[i].select = True
        ebm.select_flush_mode()
        bmesh.update_edit_mesh(me)
        scene.tool_settings.transform_pivot_point = pivot
        settings.mode = mode
        if mode == 'FACE':
            settings.reach = 12

        def restore():
            b = bmesh.from_edit_mesh(me)
            b.verts.ensure_lookup_table()
            for i, co in enumerate(orig):
                b.verts[i].co = co
            bmesh.update_edit_mesh(me)
            bpy.context.view_layer.update()

        def run(t, constrained):
            settings.enabled = constrained
            live.reset()
            restore()
            if t > 1e-6:
                real = live.transform_running
                live.transform_running = lambda wm: True
                try:
                    in_view3d(lambda: op(t))
                    bpy.context.view_layer.update()
                finally:
                    live.transform_running = real
                bmesh.update_edit_mesh(me)
                bpy.context.view_layer.update()
            b = bmesh.from_edit_mesh(me)
            return [v.co.copy() for v in b.verts]

        slug = "".join(ch if ch.isalnum() else "_" for ch in title.lower())
        slug = "_".join(p for p in slug.split("_") if p)
        for ti, t in enumerate(timeline):
            free = run(t, False)
            got = run(t, True)
            disp.vertices.foreach_set("co", [c for p in got for c in p])
            disp.update()
            for ob, cos in ((sel_ob, got), (ghost_ob, free)):
                ob.data.vertices.foreach_set("co", [c for i in sel_v for c in cos[i]])
                ob.data.update()
            ghost_ob.hide_render = t < 1e-6
            name = f"f{frame_no:04d}.png"
            scene.render.filepath = os.path.join(frames_dir, name)
            bpy.ops.render.render(write_still=True)
            meta.append({"file": name, "title": title, "subtitle": sub, "segment": si,
                         "slug": slug, "still": ti == still_at})
            frame_no += 1
        restore()
        bpy.ops.object.mode_set(mode='OBJECT')
        settings.reach = 4
        print(f"segment {si + 1}/{len(segments)} done: {title}", flush=True)

    json.dump(meta, open(os.path.join(frames_dir, "frames.json"), "w"), indent=0)
    print(f"rendered {frame_no} frames into {frames_dir}", flush=True)


if __name__ == "__main__":
    try:
        import bpy  # noqa: F401
    except ImportError:
        assemble(sys.argv[1], sys.argv[2])
    else:
        argv = sys.argv[sys.argv.index("--") + 1:]
        if argv[0] == "encode":
            encode(argv[1], argv[2])
        else:
            render_frames(argv[1], argv[2], preview="preview" in argv[3:])
