"""Verify SH_ScreenCavity.

  blender.exe --background --factory-startup SH_ScreenCavity.blend --python verify_sh_screencavity.py

The headline test is a direct numerical comparison against Blender itself:
Workbench rendered with Lighting=Flat, a white single colour and Cavity=Screen
Space outputs exactly `clamp(1 + curvature, 0, 4)` -- which is this group's
`Factor`. So the two images are directly correlatable, pixel for pixel.

Numeric probes render with filter_size = 0.01: at the default 1.5px
reconstruction filter EEVEE mixes the transparent background into pixels that
still report alpha 1.0, so even a constant 1.0 reads back as 0.985.
"""
import bpy
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SHOTS = os.path.normpath(os.path.join(HERE, "..", "assets"))
TMP = os.path.join(HERE, "_verify_tmp")
os.makedirs(SHOTS, exist_ok=True)
os.makedirs(TMP, exist_ok=True)

PASS, FAIL = [], []


def log(*a):
    print("VERIFY:", *a)
    sys.stdout.flush()


def check(name, ok, detail=""):
    (PASS if ok else FAIL).append(name)
    log("%-4s %-46s %s" % ("ok" if ok else "FAIL", name, detail))


scene = bpy.context.scene
ng = bpy.data.node_groups["SH_ScreenCavity"]
demo = bpy.data.objects["SH_ScreenCavity_Demo"]
flat_demo = bpy.data.objects["SH_ScreenCavity_Demo_Flat"]

# ---------------------------------------------------------------- interface
names_in = [i.name for i in ng.interface.items_tree
            if getattr(i, "in_out", None) == 'INPUT']
names_out = [i.name for i in ng.interface.items_tree
             if getattr(i, "in_out", None) == 'OUTPUT']
check("interface inputs",
      names_in == ["Base Color", "Ridge", "Valley", "Curvature Scale",
                   "Distance Scaling"], str(names_in))
check("interface outputs",
      names_out == ["Color", "Factor", "Curvature", "Normal Diff"], str(names_out))
check("every socket tooltipped",
      all(i.description for i in ng.interface.items_tree
          if getattr(i, "in_out", None) in ('INPUT', 'OUTPUT')))
check("asset marked + catalogued",
      ng.asset_data is not None
      and ng.asset_data.catalog_id == "3c7d5e91-2b64-4f8a-9d13-6a0e5f2c8b47"
      and "ST3E" in [t.name for t in ng.asset_data.tags])
check("uses no Ambient Occlusion node",
      not any(n.bl_idname == 'ShaderNodeAmbientOcclusion' for n in ng.nodes),
      "bump nodes: %d" % len([n for n in ng.nodes if n.bl_idname == 'ShaderNodeBump']))

# ------------------------------------------------------------- probe scene
probe_mat = bpy.data.materials.new("__probe")
probe_mat.use_nodes = True
nt = probe_mat.node_tree
nt.nodes.clear()
out = nt.nodes.new('ShaderNodeOutputMaterial')
emi = nt.nodes.new('ShaderNodeEmission')
grp = nt.nodes.new('ShaderNodeGroup')
grp.node_tree = ng
nt.links.new(emi.outputs[0], out.inputs['Surface'])

probe = demo.copy()
probe.data = demo.data.copy()
probe.name = "__probe"
probe.data.materials.clear()
probe.data.materials.append(probe_mat)
probe.location = (0, 0, 0)
scene.collection.objects.link(probe)
demo.hide_render = True
flat_demo.hide_render = True

# a flat plane facing the camera, and a convex sphere -- ground-truth shapes
bpy.ops.mesh.primitive_grid_add(x_subdivisions=60, y_subdivisions=60, size=3.0,
                                location=(0, 0, 0))
plane = bpy.context.object
plane.name = "__plane"
plane.rotation_euler = (math.radians(90), 0, 0)
bpy.ops.object.shade_smooth()
plane.data.materials.append(probe_mat)
plane.hide_render = True

bpy.ops.mesh.primitive_uv_sphere_add(segments=128, ring_count=64, radius=1.0,
                                     location=(0, 0, 0))
sphere = bpy.context.object
sphere.name = "__sphere"
bpy.ops.object.shade_smooth()
sphere.data.materials.append(probe_mat)
sphere.hide_render = True

scene.render.engine = 'BLENDER_EEVEE'
scene.render.resolution_x = scene.render.resolution_y = 220
scene.render.film_transparent = True
scene.render.filter_size = 0.01
scene.render.image_settings.file_format = 'OPEN_EXR'
scene.render.image_settings.color_mode = 'RGBA'
scene.render.image_settings.color_depth = '32'
scene.view_settings.view_transform = 'Standard'

cam = scene.camera
CAM_HOME = (0.0, -8.6, 0.05)
PROBE_CAM = (0.0, -4.0, 0.0)


def read_surface(path, offset=0.0):
    """Values on the model only. Blender's EXR is premultiplied, so divide by alpha."""
    return [v for _, v in read_surface_indexed(path, offset)]


def read_surface_indexed(path, offset=0.0):
    """(pixel_index, value) pairs, so two renders can be intersected on coverage --
    EEVEE and Workbench do not rasterise the silhouette identically."""
    img = bpy.data.images.load(path)
    px = list(img.pixels)
    bpy.data.images.remove(img)
    return [(i // 4, px[i] / px[i + 3] - offset)
            for i in range(0, len(px), 4) if px[i + 3] > 0.999]


def sample(socket="Factor", offset=0.0, **inputs):
    """Render one group output. `offset` is added in-shader so negative values
    survive (EEVEE clamps negative emission to black) and removed on read-back."""
    for lk in list(nt.links):
        if lk.to_node is emi:
            nt.links.remove(lk)
    src = grp.outputs[socket]
    if offset:
        add = nt.nodes.new('ShaderNodeMath')
        add.operation = 'ADD'
        add.inputs[1].default_value = offset
        nt.links.new(src, add.inputs[0])
        src = add.outputs[0]
    nt.links.new(src, emi.inputs['Color'])

    defaults = {"Ridge": 1.0, "Valley": 1.0, "Curvature Scale": 2.0,
                "Distance Scaling": 0.0}
    defaults.update(inputs)
    for k, v in defaults.items():
        grp.inputs[k].default_value = v
    grp.inputs["Base Color"].default_value = (1.0, 1.0, 1.0, 1.0)

    scene.render.filepath = os.path.join(TMP, "probe")
    bpy.ops.render.render(write_still=True)
    return read_surface(scene.render.filepath + ".exr", offset)


def rng(v):
    return "min=%.4f max=%.4f mean=%.4f n=%d" % (min(v), max(v), sum(v) / len(v), len(v))


def only(obj):
    for o in (probe, plane, sphere):
        o.hide_render = (o is not obj)


# ------------------------------------------------------- flat surface == 1.0
cam.location = PROBE_CAM
only(plane)
v = sample()
check("flat plane -> factor exactly 1", max(abs(x - 1.0) for x in v) < 1e-3, rng(v))
v = sample("Normal Diff", offset=1.0)
check("flat plane -> normal_diff exactly 0", max(abs(x) for x in v) < 1e-3, rng(v))

# --------------------------------------------------------- convex -> ridge
only(sphere)
v = sample()
check("convex sphere -> ridge (factor > 1)", min(v) > 0.999 and max(v) > 1.05, rng(v))
v = sample("Normal Diff", offset=1.0)
sphere_nd = sum(v) / len(v)
check("convex sphere -> normal_diff > 0", min(v) > -1e-3 and sphere_nd > 0.01, rng(v))

# ------------------------------------------- flipping normals must NOT flip it
mesh = sphere.data
mesh.flip_normals()
v = sample("Normal Diff", offset=1.0)
flipped_nd = sum(v) / len(v)
check("backfacing correction keeps convex = ridge",
      flipped_nd > 0.01,
      "front mean=%.4f  flipped mean=%.4f" % (sphere_nd, flipped_nd))
mesh.flip_normals()

# --------------------------------------------------------- sliders at zero
v = sample(**{"Ridge": 0.0, "Valley": 0.0})
check("ridge=valley=0 -> factor == 1", max(abs(x - 1.0) for x in v) < 2e-3, rng(v))

# ------------------------------------------------------------ ridge / valley
only(probe)
v = sample(**{"Valley": 0.0})
check("ridge only brightens", min(v) >= 0.999 and max(v) > 1.05, rng(v))
v = sample(**{"Ridge": 0.0})
check("valley only darkens", max(v) <= 1.001 and min(v) < 0.95, rng(v))

# -------------------------------------------------------- soft clamp ceilings
v = sample(**{"Valley": 0.0, "Curvature Scale": 8.0})
check("soft clamp caps ridge at 1 + 1.0", max(v) <= 2.0 + 1e-3, rng(v))
v = sample(**{"Ridge": 0.0, "Curvature Scale": 8.0})
check("soft clamp floors valley at 1 - 0.714", min(v) >= 0.2857 - 1e-3, rng(v))
v = sample(**{"Ridge": 2.5, "Valley": 2.5, "Curvature Scale": 8.0})
check("factor clamped to 0..4", min(v) >= 0.0 and max(v) <= 4.0 + 1e-3, rng(v))

# ------------------------------------------------- Curvature Scale is a gain
only(sphere)
a = sample("Normal Diff", offset=1.0, **{"Curvature Scale": 2.0})
b = sample("Normal Diff", offset=1.0, **{"Curvature Scale": 4.0})
ma, mb = sum(a) / len(a), sum(b) / len(b)
check("Curvature Scale is a linear gain", abs(mb / ma - 2.0) < 0.02,
      "2.0 -> %.5f, 4.0 -> %.5f, ratio %.3f" % (ma, mb, mb / ma))

# ----------------------------------------- zoom invariance at Distance Scaling 0
base = sample("Normal Diff", offset=1.0)
mbase = sum(base) / len(base)
cam.data.lens = 100
zoom = sample("Normal Diff", offset=1.0)
mzoom = sum(zoom) / len(zoom)
check("zoom invariant when Distance Scaling = 0", abs(mzoom / mbase - 1.0) < 0.15,
      "lens 50 -> %.5f, lens 100 -> %.5f, ratio %.3f" % (mbase, mzoom, mzoom / mbase))
cam.data.lens = 50

# ------------------------------------------------- Distance Scaling does scale
# lens scales with distance so the sphere covers the same pixels either way --
# otherwise the framing change, not the gain, moves the mean.
near = sample("Normal Diff", offset=1.0,
              **{"Distance Scaling": 1.0, "Curvature Scale": 1.0})
mnear = sum(near) / len(near)
cam.location = (0.0, -16.0, 0.0)
cam.data.lens = 200
far = sample("Normal Diff", offset=1.0,
             **{"Distance Scaling": 1.0, "Curvature Scale": 1.0})
mfar = sum(far) / len(far)
check("Distance Scaling scales with camera distance", 3.0 < mfar / mnear < 5.0,
      "d=4 -> %.5f, d=16 -> %.5f, ratio %.2f (expect ~4)"
      % (mnear, mfar, mfar / mnear))
cam.location = PROBE_CAM
cam.data.lens = 50

# --------------------------------------------------------------------------- #
#  headline: correlate against Workbench's own Screen Space cavity
# --------------------------------------------------------------------------- #
cam.location = CAM_HOME
only(probe)
probe.location = (0, 0, 0)
sample(**{"Ridge": 1.0, "Valley": 1.0, "Curvature Scale": 2.0})
eevee_ix = dict(read_surface_indexed(os.path.join(TMP, "probe.exr")))

scene.render.engine = 'BLENDER_WORKBENCH'
sh = scene.display.shading
sh.light = 'FLAT'
sh.color_type = 'SINGLE'
sh.single_color = (1.0, 1.0, 1.0)
sh.show_cavity = True
sh.cavity_type = 'SCREEN'
sh.curvature_ridge_factor = 1.0
sh.curvature_valley_factor = 1.0
scene.render.filepath = os.path.join(TMP, "gt")
bpy.ops.render.render(write_still=True)
gt_ix = dict(read_surface_indexed(scene.render.filepath + ".exr"))
scene.render.engine = 'BLENDER_EEVEE'

shared = sorted(set(gt_ix) & set(eevee_ix))
gt = [gt_ix[i] for i in shared]
eevee = [eevee_ix[i] for i in shared]

if len(shared) > 100:
    n = len(gt)
    mg, me = sum(gt) / n, sum(eevee) / n
    cov = sum((gt[i] - mg) * (eevee[i] - me) for i in range(n))
    sg = math.sqrt(sum((x - mg) ** 2 for x in gt))
    se = math.sqrt(sum((x - me) ** 2 for x in eevee))
    r = cov / (sg * se) if sg and se else 0.0
    check("correlates with Workbench Screen Space cavity", r > 0.5,
          "pearson r = %.3f  (n=%d, workbench mean=%.3f, ours mean=%.3f)"
          % (r, n, mg, me))
    check("default gain matches Workbench output level", abs(me - mg) < 0.03,
          "workbench mean=%.4f, ours mean=%.4f" % (mg, me))
else:
    check("correlates with Workbench Screen Space cavity", False,
          "only %d shared pixels" % len(shared))

# --------------------------------------------------------------------------- #
#  comparison renders
# --------------------------------------------------------------------------- #
bpy.data.objects.remove(probe, do_unlink=True)
bpy.data.objects.remove(plane, do_unlink=True)
bpy.data.objects.remove(sphere, do_unlink=True)
demo.hide_render = False
flat_demo.hide_render = False
scene.render.filter_size = 1.5
scene.render.film_transparent = False
scene.render.image_settings.file_format = 'PNG'
scene.render.image_settings.color_mode = 'RGB'
scene.render.resolution_x = 960
scene.render.resolution_y = 540
cam.location = CAM_HOME

scene.render.filepath = os.path.join(SHOTS, "sh_screencavity_eevee")
bpy.ops.render.render(write_still=True)
log("wrote", scene.render.filepath + ".png")

scene.render.engine = 'BLENDER_WORKBENCH'
sh.light = 'STUDIO'
sh.color_type = 'SINGLE'
sh.single_color = (0.55, 0.42, 0.32)
sh.show_cavity = True
sh.cavity_type = 'SCREEN'
scene.render.filepath = os.path.join(SHOTS, "sh_screencavity_workbench_reference")
bpy.ops.render.render(write_still=True)
log("wrote", scene.render.filepath + ".png")
scene.render.engine = 'BLENDER_EEVEE'

log("PASS %d / FAIL %d" % (len(PASS), len(FAIL)))
if FAIL:
    log("failed:", FAIL)
sys.stdout.flush()
os._exit(1 if FAIL else 0)
