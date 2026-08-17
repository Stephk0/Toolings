"""Verify SH_Cavity: numeric behaviour of the factor + comparison renders.

  blender.exe --background --factory-startup SH_Cavity.blend --python verify_sh_cavity.py

Every numeric test renders the group's Factor output straight to a linear EXR
(Standard view transform, transparent film) and reads back only the pixels the
model actually covers, using alpha as the surface mask.
"""
import bpy
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


# --------------------------------------------------------------------------- #
scene = bpy.context.scene
ng = bpy.data.node_groups["SH_Cavity"]
demo = bpy.data.objects["SH_Cavity_Demo"]
flat = bpy.data.objects["SH_Cavity_Demo_Flat"]

# ---------------------------------------------------------------- interface
names_in = [i.name for i in ng.interface.items_tree
            if getattr(i, "in_out", None) == 'INPUT']
names_out = [i.name for i in ng.interface.items_tree
             if getattr(i, "in_out", None) == 'OUTPUT']
check("interface inputs", names_in == ["Base Color", "World Ridge", "World Valley",
                                       "World Distance", "Screen Ridge", "Screen Valley",
                                       "Screen Distance"], str(names_in))
check("interface outputs", names_out == ["Color", "Factor", "Concave", "Convex"],
      str(names_out))
check("every input tooltipped",
      all(i.description for i in ng.interface.items_tree
          if getattr(i, "in_out", None) in ('INPUT', 'OUTPUT')))
check("asset marked + catalogued",
      ng.asset_data is not None
      and ng.asset_data.catalog_id == "3c7d5e91-2b64-4f8a-9d13-6a0e5f2c8b47"
      and "ST3E" in [t.name for t in ng.asset_data.tags])

# ------------------------------------------------------------- probe material
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
flat.hide_render = True

scene.render.engine = 'BLENDER_EEVEE'
scene.render.resolution_x = scene.render.resolution_y = 200
scene.render.film_transparent = True
scene.render.image_settings.file_format = 'OPEN_EXR'
scene.render.image_settings.color_mode = 'RGBA'
scene.render.image_settings.color_depth = '32'
scene.view_settings.view_transform = 'Standard'
# The default 1.5px reconstruction filter mixes the transparent background into
# pixels that still report alpha 1.0 -- a constant emission of 1.0 reads back as
# 0.985 there. That is the film, not the shader, so probe with a box filter.
scene.render.filter_size = 0.01


def sample(socket_name="Factor", **inputs):
    """Render one output socket of the group and return its values on the model."""
    for link in list(nt.links):
        if link.to_node is emi:
            nt.links.remove(link)
    nt.links.new(grp.outputs[socket_name], emi.inputs['Color'])
    defaults = dict(**{"World Ridge": 0.0, "World Valley": 0.0, "Screen Ridge": 0.0,
                       "Screen Valley": 0.0, "World Distance": 0.2,
                       "Screen Distance": 0.02})
    defaults.update(inputs)
    for k, v in defaults.items():
        grp.inputs[k].default_value = v
    grp.inputs["Base Color"].default_value = (1.0, 1.0, 1.0, 1.0)

    scene.render.filepath = os.path.join(TMP, "probe")
    bpy.ops.render.render(write_still=True)
    return read_surface(scene.render.filepath + ".exr")


def read_surface(path):
    """Values on the model only.  Blender's EXR is PREMULTIPLIED, so a silhouette
    pixel at alpha 0.985 carries 0.985x the shaded value -- divide it back out or
    every test picks up a phantom ~1.5% darkening at the outline."""
    img = bpy.data.images.load(path)
    px = list(img.pixels)
    bpy.data.images.remove(img)
    return [px[i] / px[i + 3] for i in range(0, len(px), 4) if px[i + 3] > 0.5]


def rng(v):
    return "min=%.4f max=%.4f mean=%.4f n=%d" % (min(v), max(v), sum(v) / len(v), len(v))


# ------------------------------------------------------------------- identity
v = sample()
check("all sliders 0 -> factor == 1", max(abs(x - 1.0) for x in v) < 2e-3, rng(v))

# ---------------------------------------------------------------- world valley
v = sample(**{"World Valley": 1.0})
check("world valley only darkens", max(v) <= 1.0005 and min(v) < 0.95, rng(v))

# ----------------------------------------------------------------- world ridge
v = sample(**{"World Ridge": 1.0})
check("world ridge only brightens", min(v) >= 0.9995 and max(v) > 1.05, rng(v))

# --------------------------------------------------------------- screen valley
# at the shipped 0.05m radius on a 2m head this is a fine crease darkening, not a
# broad occlusion -- the magnitude test that matters is the wide-radius one below.
v = sample(**{"Screen Valley": 1.0, "Screen Distance": 0.05})
check("screen valley only darkens", max(v) <= 1.0005 and min(v) < 0.995, rng(v))
v = sample(**{"Screen Valley": 1.0, "Screen Distance": 0.5})
# the inside-probe (convex) reads systematically stronger than the outward one, so
# normal_diff is biased towards ridge -- valley needs a wider radius or a higher
# slider for the same visual weight. Documented in the README.
check("screen valley darkens hard at wide radius", min(v) < 0.85, rng(v))

# ---------------------------------------------------------------- screen ridge
v = sample(**{"Screen Ridge": 1.0, "Screen Distance": 0.05})
check("screen ridge only brightens", min(v) >= 0.9995 and max(v) > 1.02, rng(v))

# ------------------------------------------- soft clamp cap: 2*(0.25/ctrl) = 1
# ridge=1 -> ctrl=0.5 -> curvature <= 1.0 -> factor <= 2.0
v = sample(**{"Screen Ridge": 1.0, "Screen Distance": 0.5})
check("soft clamp caps ridge at 1+1.0", max(v) <= 2.0 + 1e-4, rng(v))

v = sample(**{"Screen Valley": 1.0, "Screen Distance": 0.5})
# valley=1 -> ctrl=0.7 -> curvature >= -2*(0.25/0.7) = -0.714 -> factor >= 0.2857
check("soft clamp caps valley at 1-0.714", min(v) >= 0.2857 - 1e-4, rng(v))

# ---------------------------------------------------------------- output clamp
v = sample(**{"World Ridge": 2.5, "World Valley": 2.5, "Screen Ridge": 2.5,
              "Screen Valley": 2.5, "World Distance": 0.6, "Screen Distance": 0.3})
check("factor clamped to 0..4", min(v) >= 0.0 and max(v) <= 4.0 + 1e-4, rng(v))

# ------------------------------------------------------------ distance responds
near = sample(**{"World Valley": 1.0, "World Distance": 0.02})
far = sample(**{"World Valley": 1.0, "World Distance": 0.6})
mn, mf = sum(near) / len(near), sum(far) / len(far)
check("world distance changes the result",
      mf < mn - 0.02 and min(far) < min(near) - 0.1,
      "mean 0.02m=%.4f 0.6m=%.4f | min 0.02m=%.4f 0.6m=%.4f"
      % (mn, mf, min(near), min(far)))

# --------------------------------------------------------------- mask outputs
v = sample("Concave", **{"World Distance": 0.2})
check("Concave in 0..1 and varies", 0.0 <= min(v) and max(v) <= 1.0 and max(v) - min(v) > 0.1,
      rng(v))
v = sample("Convex", **{"World Distance": 0.2})
check("Convex in 0..1 and varies", 0.0 <= min(v) and max(v) <= 1.0 and max(v) - min(v) > 0.1,
      rng(v))

# ------------------------------------------------------------ Base Color tints
for link in list(nt.links):
    if link.to_node is emi:
        nt.links.remove(link)
nt.links.new(grp.outputs["Color"], emi.inputs['Color'])
grp.inputs["Base Color"].default_value = (0.5, 0.5, 0.5, 1.0)
for k, val in (("World Ridge", 0.0), ("World Valley", 0.0),
               ("Screen Ridge", 0.0), ("Screen Valley", 0.0)):
    grp.inputs[k].default_value = val
scene.render.filepath = os.path.join(TMP, "probe")
bpy.ops.render.render(write_still=True)
vals = read_surface(scene.render.filepath + ".exr")
check("Color = Base Color at factor 1", max(abs(x - 0.5) for x in vals) < 2e-3, rng(vals))

# --------------------------------------------------------------------------- #
#  comparison renders: workbench cavity (ground truth)  vs  SH_Cavity in EEVEE
# --------------------------------------------------------------------------- #
bpy.data.objects.remove(probe, do_unlink=True)
demo.hide_render = False
flat.hide_render = False
scene.render.filter_size = 1.5
scene.render.film_transparent = False
scene.render.image_settings.file_format = 'PNG'
scene.render.image_settings.color_mode = 'RGB'
scene.render.resolution_x = 960
scene.render.resolution_y = 540

scene.render.filepath = os.path.join(SHOTS, "sh_cavity_eevee")
scene.render.engine = 'BLENDER_EEVEE'
bpy.ops.render.render(write_still=True)
log("wrote", scene.render.filepath + ".png")

# same two heads, rendered by workbench with its own cavity overlay
scene.render.engine = 'BLENDER_WORKBENCH'
sh = scene.display.shading
sh.light = 'STUDIO'
sh.color_type = 'SINGLE'
sh.single_color = (0.55, 0.42, 0.32)
sh.show_cavity = True
sh.cavity_type = 'BOTH'
sh.cavity_ridge_factor = 1.0
sh.cavity_valley_factor = 1.0
sh.curvature_ridge_factor = 1.0
sh.curvature_valley_factor = 1.0
scene.render.filepath = os.path.join(SHOTS, "sh_cavity_workbench_reference")
bpy.ops.render.render(write_still=True)
log("wrote", scene.render.filepath + ".png")
scene.render.engine = 'BLENDER_EEVEE'

log("PASS %d / FAIL %d" % (len(PASS), len(FAIL)))
if FAIL:
    log("failed:", FAIL)
sys.stdout.flush()
os._exit(1 if FAIL else 0)
