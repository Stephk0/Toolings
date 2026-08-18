"""Build SH_ScreenCavity.blend -- Blender's Solid-viewport "Screen Space" cavity
(curvature) reproduced in EEVEE WITHOUT the Ambient Occlusion node.

Run headless:
  blender.exe --background --factory-startup --python build_sh_screencavity.py

The viewport algorithm (workbench_curvature_lib.glsl) is:

    normal_diff = (normal_up - normal_down) + (normal_right - normal_left)
    curvature_soft_clamp(c, ctrl) = c < 0.5/ctrl ? c*(1 - c*ctrl) : 0.25/ctrl
    curvature = normal_diff < 0 ? -2*soft_clamp(-normal_diff, valley_ctrl)
                                :  2*soft_clamp( normal_diff, ridge_ctrl)
    ridge_ctrl = 0.5/max(ridge^2,1e-4)   valley_ctrl = 0.7/max(valley^2,1e-4)
    color.rgb *= clamp(1 + curvature, 0, 4)

`normal_up - normal_down` and `normal_right - normal_left` are the screen-space
derivatives of the VIEW-SPACE normal's .y and .x -- normal_diff is the
screen-space DIVERGENCE of the view normal.

The only node in Blender that exposes a screen-space derivative is **Bump**: its
GLSL builds surfgrad = dHdx*Rx + dHdy*Ry from dFdx/dFdy of its Height input.
Feeding it Height = view-normal.x and differencing the two bump directions
recovers that derivative:

    dot(Bump(h, invert=off) - Bump(h, invert=on), axis)  ~  -2*D*dHd(axis)/det

Measured behaviour (all re-checked by verify_sh_screencavity.py):
  * flat plane -> exactly 0, convex sphere -> one uniform sign
  * linear in the Bump Distance D only while D is small -- a large D tilts the
    normal far enough that Bump's normalize() saturates the reading, so the
    probe step is FIXED at 0.01 and Curvature Scale multiplies afterwards
  * invariant to zoom / camera distance / resolution, because the `det` division
    normalises the pixel footprint out. The SAMPLING FOOTPRINT is still one pixel
    (dFdx), so the effect stays as crisp as the viewport's -- only the AMPLITUDE
    is world-normalised instead of pixel-scaled. `Distance Scaling` optionally
    puts the viewport's distance dependence back.
  * the sign comes out inverted vs workbench (the leading minus above), so it is
    flipped; Bump also flips `dist` on backfaces, corrected with Backfacing.
"""

import bpy
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.normpath(os.path.join(HERE, "..", "SH_ScreenCavity.blend"))
CATALOG_SHADING = "3c7d5e91-2b64-4f8a-9d13-6a0e5f2c8b47"   # ST3E/Shading


def log(*a):
    print("BUILD:", *a)
    sys.stdout.flush()


def isock(node, ident):
    """Resolve an input by IDENTIFIER, preferring enabled sockets (inputs[key]
    looks up by display NAME, and multi-type nodes reuse names)."""
    for s in node.inputs:
        if s.identifier == ident and s.enabled:
            return s
    return next(s for s in node.inputs if s.identifier == ident)


def osock(node, ident):
    for s in node.outputs:
        if s.identifier == ident and s.enabled:
            return s
    return next(s for s in node.outputs if s.identifier == ident)


class Tree:
    def __init__(self, ng):
        self.ng = ng
        self.frame = None

    def frame_new(self, label, tint=None):
        f = self.ng.nodes.new('NodeFrame')
        f.label = label
        f.location = (0.0, 0.0)          # keeps child .location absolute
        f.label_size = 18
        if tint:
            f.use_custom_color = True
            f.color = tint
        self.frame = f
        return f

    def new(self, idname, label=None):
        n = self.ng.nodes.new(idname)
        if label:
            n.label = label
            n.name = label
        if self.frame:
            n.parent = self.frame
        return n

    def link(self, a, b):
        return self.ng.links.new(a, b)

    def math(self, op, label=None, a=None, b=None, c=None, clamp=False):
        n = self.new('ShaderNodeMath', label)
        n.operation = op
        n.use_clamp = clamp
        for i, v in enumerate((a, b, c)):
            if v is None:
                continue
            if hasattr(v, 'is_output'):
                self.link(v, n.inputs[i])
            else:
                n.inputs[i].default_value = v
        return n.outputs[0]

    def vmath(self, op, label=None, a=None, b=None):
        n = self.new('ShaderNodeVectorMath', label)
        n.operation = op
        for i, v in enumerate((a, b)):
            if v is None:
                continue
            if hasattr(v, 'is_output'):
                self.link(v, n.inputs[i])
            else:
                n.inputs[i].default_value = v
        return n

    def cam_axis(self, vec, label):
        """A camera-space basis vector expressed in world space."""
        n = self.new('ShaderNodeVectorTransform', label)
        n.vector_type = 'VECTOR'
        n.convert_from = 'CAMERA'
        n.convert_to = 'WORLD'
        n.inputs[0].default_value = vec
        return n.outputs[0]


def iface_socket(ng, name, sock_type, parent=None, default=None, smin=None,
                 smax=None, subtype=None, desc=""):
    it = ng.interface.new_socket(name=name, in_out='INPUT', socket_type=sock_type)
    if default is not None:
        it.default_value = default
    if smin is not None:
        it.min_value = smin
    if smax is not None:
        it.max_value = smax
    if subtype:
        it.subtype = subtype
    it.description = desc
    if parent is not None:
        ng.interface.move_to_parent(it, parent, len(parent.interface_items))
    return it


def build_group():
    ng = bpy.data.node_groups.new("SH_ScreenCavity", "ShaderNodeTree")
    t = Tree(ng)

    # ---------------------------------------------------------------- interface
    iface_socket(ng, "Base Color", 'NodeSocketColor', default=(1.0, 1.0, 1.0, 1.0),
                 desc="Colour the curvature factor is multiplied into. Leave white to "
                      "output the raw overlay.")

    p_curv = ng.interface.new_panel(
        "Curvature",
        description="The viewport's Cavity > Screen Space controls.")
    iface_socket(ng, "Ridge", 'NodeSocketFloat', p_curv, 1.0, 0.0, 2.5,
                 desc="Brightening on convex edges. Same response as the viewport's "
                      "Cavity > Screen Space > Ridge: 0 disables it, and the soft clamp "
                      "ceilings the brightening at +1.0 when this is 1.0.")
    iface_socket(ng, "Valley", 'NodeSocketFloat', p_curv, 1.0, 0.0, 2.5,
                 desc="Darkening in creases. Same response as the viewport's "
                      "Cavity > Screen Space > Valley: 0 disables it, and the soft clamp "
                      "floors the darkening at -0.714 when this is 1.0.")
    iface_socket(ng, "Curvature Scale", 'NodeSocketFloat', p_curv, 2.0, 0.0, 50.0,
                 desc="Linear gain on the measured curvature, before Ridge/Valley. The "
                      "viewport takes its amplitude from the pixel size; the Bump "
                      "derivative used here normalises that out, so it is set explicitly. "
                      "Raise it for large or softly curved models, lower it for small or "
                      "highly detailed ones. The 2.0 default was calibrated against "
                      "Workbench: it reproduces the viewport's own output level (mean "
                      "factor 1.192 vs 1.185) at the lowest RMSE.")
    iface_socket(ng, "Distance Scaling", 'NodeSocketFloat', p_curv, 0.0, 0.0, 1.0,
                 subtype='FACTOR',
                 desc="Puts the viewport's perspective behaviour back: at 1.0 the gain "
                      "scales with distance from the camera, so far-away surfaces get the "
                      "coarser cavity they would get in the viewport. At 0.0 (default) the "
                      "effect is camera-independent and never swims.")

    o_col = ng.interface.new_socket(name="Color", in_out='OUTPUT',
                                    socket_type='NodeSocketColor')
    o_col.description = ("Base Color multiplied by Factor. Plug into Base Color, or into "
                         "an Emission for the literal viewport look.")
    o_fac = ng.interface.new_socket(name="Factor", in_out='OUTPUT',
                                    socket_type='NodeSocketFloat')
    o_fac.description = ("clamp(1 + curvature, 0, 4) -- the multiplier workbench applies. "
                         "1.0 means untouched, below 1 a valley, above 1 a ridge.")
    o_cur = ng.interface.new_socket(name="Curvature", in_out='OUTPUT',
                                    socket_type='NodeSocketFloat')
    o_cur.description = ("The signed, soft-clamped curvature itself (workbench's "
                         "`curvature`): positive on ridges, negative in valleys, 0 on "
                         "flat surfaces.")
    o_nd = ng.interface.new_socket(name="Normal Diff", in_out='OUTPUT',
                                   socket_type='NodeSocketFloat')
    o_nd.description = ("The raw signed divergence of the view-space normal, before the "
                        "soft clamp (workbench's `normal_diff`). Useful for driving other "
                        "effects.")

    gin = ng.nodes.new('NodeGroupInput')
    gin.name = gin.label = "Group Input"
    gout = ng.nodes.new('NodeGroupOutput')
    gout.name = gout.label = "Group Output"
    IN = gin.outputs

    # ------------------------------------------- the buffer workbench samples
    t.frame_new("View-Space Normal  -  what workbench reads from normalBuffer",
                tint=(0.19, 0.24, 0.31))
    geo = t.new('ShaderNodeNewGeometry', "Geometry")
    vt = t.new('ShaderNodeVectorTransform', "World -> Camera")
    vt.vector_type = 'NORMAL'
    vt.convert_from = 'WORLD'
    vt.convert_to = 'CAMERA'
    t.link(geo.outputs['Normal'], vt.inputs[0])
    sep = t.new('ShaderNodeSeparateXYZ', "Nx  Ny")
    t.link(vt.outputs[0], sep.inputs[0])
    cam_right = t.cam_axis((1.0, 0.0, 0.0), "Camera Right")
    cam_up = t.cam_axis((0.0, 1.0, 0.0), "Camera Up")

    # ---------------------------------------------------------- sampling gain
    t.frame_new("Sampling Gain  -  Curvature Scale, optionally x camera distance",
                tint=(0.20, 0.20, 0.26))
    cam_org = t.new('ShaderNodeVectorTransform', "Camera Origin")
    cam_org.vector_type = 'POINT'
    cam_org.convert_from = 'CAMERA'
    cam_org.convert_to = 'WORLD'
    cam_org.inputs[0].default_value = (0.0, 0.0, 0.0)
    to_cam = t.vmath('SUBTRACT', "P - Camera", geo.outputs['Position'],
                     cam_org.outputs[0])
    cam_dist = t.vmath('LENGTH', "Camera Distance")
    t.link(to_cam.outputs['Vector'], cam_dist.inputs[0])
    # gain = scale * mix(1, distance, Distance Scaling) = scale * (1 + s*(d - 1))
    d_minus_1 = t.math('SUBTRACT', "distance - 1", cam_dist.outputs['Value'], 1.0)
    dist_mix = t.math('MULTIPLY_ADD', "mix(1, distance, s)", d_minus_1,
                      IN["Distance Scaling"], 1.0)
    gain = t.math('MULTIPLY', "Sampling Gain", IN["Curvature Scale"], dist_mix)

    # ------------------------------------------ the two screen-space derivatives
    # The Bump Distance is a FIXED small step, not the user gain: Bump normalises
    # its result, so a large Distance tilts the normal far enough to saturate and
    # the measurement stops being proportional to the derivative. 0.01 keeps every
    # model measured in the linear regime; the gain is applied afterwards, which
    # also matches workbench (a plain finite difference, then scaling).
    PROBE_STEP = 0.01

    def derivative(height, axis, tag, tint):
        """dot(Bump(h) - Bump(h, inverted), axis) -- the screen-space derivative of
        `height` along `axis`, as exposed by the Bump node's surfgrad."""
        t.frame_new(tag, tint=tint)
        outs = []
        for inv in (False, True):
            b = t.new('ShaderNodeBump',
                      "Bump %s" % ("(inverted)" if inv else "(direct)"))
            b.invert = inv
            b.inputs['Strength'].default_value = 1.0
            b.inputs['Distance'].default_value = PROBE_STEP
            t.link(height, b.inputs['Height'])
            outs.append(b.outputs['Normal'])
        sub = t.vmath('SUBTRACT', "bump delta", outs[0], outs[1])
        dot = t.vmath('DOT_PRODUCT', "project onto axis", sub.outputs['Vector'], axis)
        return dot.outputs['Value']

    d_x = derivative(sep.outputs['X'], cam_right,
                     "normal_right - normal_left  -  d(Nx) along screen X",
                     (0.16, 0.28, 0.22))
    d_y = derivative(sep.outputs['Y'], cam_up,
                     "normal_up - normal_down  -  d(Ny) along screen Y",
                     (0.16, 0.28, 0.22))

    # ----------------------------------------------------------- normal_diff
    t.frame_new("normal_diff  -  divergence of the view normal, sign-corrected",
                tint=(0.16, 0.28, 0.22))
    diverg = t.math('ADD', "dNx/dx + dNy/dy", d_x, d_y)
    # Bump's surfgrad enters with a leading minus, and its `dist` flips on
    # backfaces -- undo both so a convex surface always reads as a ridge.
    face_sign = t.math('MULTIPLY_ADD', "front/back sign", geo.outputs['Backfacing'],
                       -2.0, 1.0)
    flipped = t.math('MULTIPLY', "flip sign", diverg, -1.0)
    signed = t.math('MULTIPLY', "front/back corrected", flipped, face_sign)
    normal_diff = t.math('MULTIPLY', "normal_diff", signed, gain)

    # ------------------------------------------- curvature controls (Blender's)
    t.frame_new("Curvature Controls  -  0.5/ridge^2 , 0.7/valley^2",
                tint=(0.30, 0.24, 0.16))
    r_sq = t.math('MULTIPLY', "ridge^2", IN["Ridge"], IN["Ridge"])
    r_safe = t.math('MAXIMUM', "max(ridge^2, 1e-4)", r_sq, 1e-4)
    ctrl_ridge = t.math('DIVIDE', "Ridge Control", 0.5, r_safe)
    v_sq = t.math('MULTIPLY', "valley^2", IN["Valley"], IN["Valley"])
    v_safe = t.math('MAXIMUM', "max(valley^2, 1e-4)", v_sq, 1e-4)
    ctrl_valley = t.math('DIVIDE', "Valley Control", 0.7, v_safe)

    def soft_clamp(c, ctrl, tag):
        """Blender's curvature_soft_clamp(), branch and all."""
        cc = t.math('MULTIPLY', "%s c*ctrl" % tag, c, ctrl)
        inner = t.math('SUBTRACT', "%s 1 - c*ctrl" % tag, 1.0, cc)
        para = t.math('MULTIPLY', "%s c*(1 - c*ctrl)" % tag, c, inner)
        cap = t.math('DIVIDE', "%s cap 0.25/ctrl" % tag, 0.25, ctrl)
        thr = t.math('DIVIDE', "%s threshold 0.5/ctrl" % tag, 0.5, ctrl)
        below = t.math('LESS_THAN', "%s c < threshold" % tag, c, thr)
        delta = t.math('SUBTRACT', "%s para - cap" % tag, para, cap)
        return t.math('MULTIPLY_ADD', "%s soft clamp" % tag, delta, below, cap)

    # ------------------------------------------------------------- curvature
    t.frame_new("Curvature  -  signed, soft-clamped, x2",
                tint=(0.30, 0.24, 0.16))
    neg_diff = t.math('MULTIPLY', "-normal_diff", normal_diff, -1.0)
    # Blender BRANCHES and only evaluates the taken side; node trees evaluate both,
    # so clamp each side's input to its own sign -- the idle branch then computes
    # soft_clamp(0) == 0 exactly instead of reaching ~1e4 and losing precision in
    # the arithmetic select below.
    pos_diff = t.math('MAXIMUM', "max(normal_diff, 0)", normal_diff, 0.0)
    pos_neg_diff = t.math('MAXIMUM', "max(-normal_diff, 0)", neg_diff, 0.0)
    ridge_sc = soft_clamp(pos_diff, ctrl_ridge, "Ridge")
    valley_sc = soft_clamp(pos_neg_diff, ctrl_valley, "Valley")
    ridge_branch = t.math('MULTIPLY', "Ridge Branch  +2x", ridge_sc, 2.0)
    valley_branch = t.math('MULTIPLY', "Valley Branch  -2x", valley_sc, -2.0)
    is_ridge = t.math('GREATER_THAN', "normal_diff > 0", normal_diff, 0.0)
    branch_delta = t.math('SUBTRACT', "ridge - valley", ridge_branch, valley_branch)
    curvature = t.math('MULTIPLY_ADD', "curvature", branch_delta, is_ridge,
                       valley_branch)

    # ------------------------------------------------------------- composite
    t.frame_new("Composite  -  clamp( 1 + curvature , 0 , 4 )",
                tint=(0.30, 0.16, 0.20))
    one_plus = t.math('ADD', "1 + curvature", 1.0, curvature)
    clamp = t.new('ShaderNodeClamp', "Clamp 0..4")
    clamp.inputs['Min'].default_value = 0.0
    clamp.inputs['Max'].default_value = 4.0
    t.link(one_plus, clamp.inputs['Value'])
    factor = clamp.outputs['Result']

    # ---------------------------------------------------------------- output
    t.frame_new("Output  -  Base Color x Factor", tint=(0.22, 0.22, 0.22))
    mix = t.new('ShaderNodeMix', "Base Color x Factor")
    mix.data_type = 'RGBA'
    mix.blend_type = 'MULTIPLY'
    mix.clamp_result = False
    isock(mix, 'Factor_Float').default_value = 1.0
    t.link(IN["Base Color"], isock(mix, 'A_Color'))
    t.link(factor, isock(mix, 'B_Color'))

    t.frame = None
    t.link(osock(mix, 'Result_Color'), gout.inputs["Color"])
    t.link(factor, gout.inputs["Factor"])
    t.link(curvature, gout.inputs["Curvature"])
    t.link(normal_diff, gout.inputs["Normal Diff"])
    return ng


def demo_material(name, ng, flat):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()
    out = nt.nodes.new('ShaderNodeOutputMaterial')
    out.location = (620, 0)
    grp = nt.nodes.new('ShaderNodeGroup')
    grp.node_tree = ng
    grp.location = (-260, 0)
    grp.width = 260
    if flat:
        grp.inputs["Base Color"].default_value = (0.42, 0.42, 0.42, 1.0)
        emi = nt.nodes.new('ShaderNodeEmission')
        emi.location = (200, 0)
        nt.links.new(grp.outputs["Color"], emi.inputs['Color'])
        nt.links.new(emi.outputs[0], out.inputs['Surface'])
    else:
        grp.inputs["Base Color"].default_value = (0.55, 0.42, 0.32, 1.0)
        bsdf = nt.nodes.new('ShaderNodeBsdfPrincipled')
        bsdf.location = (140, 0)
        bsdf.inputs['Roughness'].default_value = 0.55
        nt.links.new(grp.outputs["Color"], bsdf.inputs['Base Color'])
        nt.links.new(bsdf.outputs[0], out.inputs['Surface'])
    return mat


def build_scene(ng):
    scene = bpy.context.scene
    scene.render.engine = 'BLENDER_EEVEE'
    scene.view_settings.view_transform = 'Standard'
    scene.render.resolution_x = 960
    scene.render.resolution_y = 540

    world = bpy.data.worlds.new("World")
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs[0].default_value = (0.05, 0.05, 0.055, 1.0)
    scene.world = world

    made = []
    for name, flat, x in (("SH_ScreenCavity_Demo", False, -1.6),
                          ("SH_ScreenCavity_Demo_Flat", True, 1.6)):
        bpy.ops.mesh.primitive_monkey_add(size=2, location=(x, 0, 0))
        ob = bpy.context.object
        ob.name = name
        ob.data.name = name
        bpy.ops.object.shade_smooth()
        sub = ob.modifiers.new("Subdivision", 'SUBSURF')
        sub.levels = 2
        sub.render_levels = 2
        ob.data.materials.append(demo_material("M_%s" % name, ng, flat))
        made.append(ob)

    cam_data = bpy.data.cameras.new("Camera")
    cam_data.lens = 50
    cam = bpy.data.objects.new("Camera", cam_data)
    scene.collection.objects.link(cam)
    cam.location = (0.0, -8.6, 0.05)
    cam.rotation_euler = (1.5708, 0.0, 0.0)
    scene.camera = cam

    light_data = bpy.data.lights.new("Key", 'AREA')
    light_data.energy = 320.0
    light_data.size = 4.0
    light = bpy.data.objects.new("Key", light_data)
    scene.collection.objects.link(light)
    light.location = (2.6, -3.4, 3.2)
    light.rotation_euler = (0.72, 0.0, 0.62)

    bpy.context.view_layer.objects.active = made[0]
    made[0].select_set(True)
    return made


def publish(ng):
    ng.asset_mark()
    ng.asset_data.catalog_id = CATALOG_SHADING
    ng.asset_data.tags.new("ST3E")
    ng.asset_data.description = (
        "The Solid-viewport 'Screen Space' cavity (curvature) in EEVEE, computed from "
        "the screen-space divergence of the view normal via the Bump node -- no Ambient "
        "Occlusion node and no ray tracing. Ridge/Valley behave like the viewport's."
    )
    for trait in ("is_modifier", "is_tool"):
        if hasattr(ng, trait):
            setattr(ng, trait, False)


def main():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    ng = build_group()
    log("group built:", ng.name,
        "| %d nodes" % len([n for n in ng.nodes if n.bl_idname != 'NodeFrame']),
        "| %d frames" % len([n for n in ng.nodes if n.bl_idname == 'NodeFrame']))
    objs = build_scene(ng)
    log("demo objects:", ", ".join(o.name for o in objs))
    publish(ng)
    log("asset:", ng.asset_data.catalog_id, [t.name for t in ng.asset_data.tags])
    bpy.ops.wm.save_as_mainfile(filepath=OUT)
    log("saved", OUT)
    sys.stdout.flush()
    os._exit(0)


main()
