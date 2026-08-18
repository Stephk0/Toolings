"""Build SH_Cavity.blend  --  a shader node group that reproduces Blender's
Solid-viewport "Cavity" overlay inside EEVEE / Material Preview.

Run headless:
  blender.exe --background --factory-startup --python build_sh_cavity.py

Blender's workbench composites the overlay as (workbench_composite.bsl.hh):

    color.rgb *= clamp((1 - cavity) * (1 + edges) * (1 + curvature), 0, 4)

  cavity / edges  come from an Alchemy SSAO over the depth+normal buffer,
                  scaled by cavity_valley_factor / cavity_ridge_factor  ("World")
  curvature       comes from the screen-space derivative of the normal buffer,
                  split by sign and soft-clamped                        ("Screen Space")

    curvature_soft_clamp(c, ctrl) = c < 0.5/ctrl ? c * (1 - c * ctrl) : 0.25/ctrl
    curvature = normal_diff < 0 ? -2 * soft_clamp(-normal_diff, valley_ctrl)
                                :  2 * soft_clamp( normal_diff, ridge_ctrl)
    ridge_ctrl = 0.5 / max(ridge^2, 1e-4)   valley_ctrl = 0.7 / max(valley^2, 1e-4)

Shader nodes cannot read the depth or normal buffer, so the two curvature
*sources* are replaced by an Ambient Occlusion probe pair (outward = concave,
inside = convex) at two different radii.  Every piece of maths downstream of the
probes is Blender's own, verbatim -- so the Ridge / Valley sliders respond
exactly like the viewport ones.
"""

import bpy
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.normpath(os.path.join(HERE, "..", "SH_Cavity.blend"))
CATALOG_SHADING = "3c7d5e91-2b64-4f8a-9d13-6a0e5f2c8b47"   # ST3E/Shading

AO_SAMPLES = 16          # matches Blender's default matcap_ssao_samples


def log(*a):
    print("BUILD:", *a)
    sys.stdout.flush()


# --------------------------------------------------------------------------- #
#  small node helpers
# --------------------------------------------------------------------------- #
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

    def new(self, idname, label=None, frame=True):
        n = self.ng.nodes.new(idname)
        if label:
            n.label = label
            n.name = label
        if frame and self.frame:
            n.parent = self.frame
        return n

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

    def link(self, from_socket, to_socket):
        return self.ng.links.new(from_socket, to_socket)


def isock(node, ident):
    """Resolve an input by IDENTIFIER, preferring enabled sockets.

    node.inputs[key] looks up by *display name*, and multi-type nodes reuse names
    (Mix has three sockets called "A") while keeping a disabled socket per variant --
    linking one of those silently no-ops at evaluation time.
    """
    for s in node.inputs:
        if s.identifier == ident and s.enabled:
            return s
    return next(s for s in node.inputs if s.identifier == ident)


def osock(node, ident):
    for s in node.outputs:
        if s.identifier == ident and s.enabled:
            return s
    return next(s for s in node.outputs if s.identifier == ident)


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


# --------------------------------------------------------------------------- #
#  the node group
# --------------------------------------------------------------------------- #
def build_group():
    ng = bpy.data.node_groups.new("SH_Cavity", "ShaderNodeTree")
    t = Tree(ng)

    # ---------------------------------------------------------------- interface
    iface_socket(ng, "Base Color", 'NodeSocketColor', default=(1.0, 1.0, 1.0, 1.0),
                 desc="Colour the cavity factor is multiplied into. Leave white to "
                      "output the raw overlay.")

    p_world = ng.interface.new_panel(
        "Cavity (World)",
        description="Broad ambient-occlusion cavity - the viewport's 'World' cavity type.")
    iface_socket(ng, "World Ridge", 'NodeSocketFloat', p_world, 1.0, 0.0, 2.5,
                 desc="Brightening on convex, outward-facing areas. Viewport equivalent: "
                      "Cavity > World > Ridge. 0 disables.")
    iface_socket(ng, "World Valley", 'NodeSocketFloat', p_world, 1.0, 0.0, 2.5,
                 desc="Darkening inside concave areas. Viewport equivalent: "
                      "Cavity > World > Valley. 0 disables.")
    iface_socket(ng, "World Distance", 'NodeSocketFloat', p_world, 0.2, 0.0, 100.0,
                 subtype='DISTANCE',
                 desc="Radius the broad cavity is gathered over, in scene units. Matches "
                      "Render Properties > Color Management... > SSAO Distance (default 0.2m). "
                      "Scale this with your model.")

    p_screen = ng.interface.new_panel(
        "Curvature (Screen)",
        description="Tight curvature that picks out edges - the viewport's 'Screen Space' "
                    "cavity type.")
    iface_socket(ng, "Screen Ridge", 'NodeSocketFloat', p_screen, 1.0, 0.0, 2.5,
                 desc="Brightening on sharp convex edges. Viewport equivalent: "
                      "Cavity > Screen Space > Ridge. 0 disables.")
    iface_socket(ng, "Screen Valley", 'NodeSocketFloat', p_screen, 1.0, 0.0, 2.5,
                 desc="Darkening in sharp creases. Viewport equivalent: "
                      "Cavity > Screen Space > Valley. 0 disables.")
    iface_socket(ng, "Screen Distance", 'NodeSocketFloat', p_screen, 0.05, 0.0, 100.0,
                 subtype='DISTANCE',
                 desc="Radius of the tight curvature probe, in scene units. The viewport "
                      "samples one pixel; here it is a world-space radius, so keep it small "
                      "(a few percent of the model) to read as an edge highlight. Unlike the "
                      "viewport it does not change with zoom.")

    o_col = ng.interface.new_socket(name="Color", in_out='OUTPUT', socket_type='NodeSocketColor')
    o_col.description = "Base Color multiplied by Factor. Plug into Base Color, or into an " \
                        "Emission for the literal viewport look."
    o_fac = ng.interface.new_socket(name="Factor", in_out='OUTPUT', socket_type='NodeSocketFloat')
    o_fac.description = "The raw cavity multiplier, 0..4. 1.0 means untouched, below 1 is a " \
                        "valley, above 1 a ridge."
    o_cav = ng.interface.new_socket(name="Concave", in_out='OUTPUT', socket_type='NodeSocketFloat')
    o_cav.description = "Valley mask from the broad probe, 0..1. Useful as a dirt/wear mask."
    o_edg = ng.interface.new_socket(name="Convex", in_out='OUTPUT', socket_type='NodeSocketFloat')
    o_edg.description = "Ridge mask from the broad probe, 0..1. Useful as an edge-wear mask."

    gin = ng.nodes.new('NodeGroupInput')
    gin.name = gin.label = "Group Input"
    gout = ng.nodes.new('NodeGroupOutput')
    gout.name = gout.label = "Group Output"
    IN = gin.outputs

    # ------------------------------------------------- probes: broad ("world")
    t.frame_new("World Probe  -  AO pair at World Distance",
                tint=(0.19, 0.24, 0.31))
    ao_wc = t.new('ShaderNodeAmbientOcclusion', "AO World Outward")
    ao_wc.inside = False
    ao_wc.only_local = False
    ao_wc.samples = AO_SAMPLES
    t.link(IN["World Distance"], ao_wc.inputs['Distance'])
    ao_wv = t.new('ShaderNodeAmbientOcclusion', "AO World Inside")
    ao_wv.inside = True
    ao_wv.only_local = False
    ao_wv.samples = AO_SAMPLES
    t.link(IN["World Distance"], ao_wv.inputs['Distance'])
    # 1 - AO : outward probe -> concavity, inside probe -> convexity
    w_concave = t.math('SUBTRACT', "World Concave", 1.0, ao_wc.outputs['AO'], clamp=True)
    w_convex = t.math('SUBTRACT', "World Convex", 1.0, ao_wv.outputs['AO'], clamp=True)

    # ------------------------------------------------ probes: tight ("screen")
    t.frame_new("Screen Probe  -  AO pair at Screen Distance",
                tint=(0.19, 0.24, 0.31))
    ao_sc = t.new('ShaderNodeAmbientOcclusion', "AO Screen Outward")
    ao_sc.inside = False
    ao_sc.only_local = False
    ao_sc.samples = AO_SAMPLES
    t.link(IN["Screen Distance"], ao_sc.inputs['Distance'])
    ao_sv = t.new('ShaderNodeAmbientOcclusion', "AO Screen Inside")
    ao_sv.inside = True
    ao_sv.only_local = False
    ao_sv.samples = AO_SAMPLES
    t.link(IN["Screen Distance"], ao_sv.inputs['Distance'])
    s_concave = t.math('SUBTRACT', "Screen Concave", 1.0, ao_sc.outputs['AO'], clamp=True)
    s_convex = t.math('SUBTRACT', "Screen Convex", 1.0, ao_sv.outputs['AO'], clamp=True)

    # --------------------------------------- world term: (1 - cavity)(1 + edges)
    t.frame_new("World Cavity  -  (1 - cavity) * (1 + edges)",
                tint=(0.16, 0.28, 0.22))
    cavity = t.math('MULTIPLY', "cavity", w_concave, IN["World Valley"])
    edges = t.math('MULTIPLY', "edges", w_convex, IN["World Ridge"])
    one_minus_cavity = t.math('SUBTRACT', "1 - cavity", 1.0, cavity)
    one_plus_edges = t.math('ADD', "1 + edges", 1.0, edges)
    world_term = t.math('MULTIPLY', "World Term", one_minus_cavity, one_plus_edges)

    # ------------------------------------------- curvature controls (Blender's)
    t.frame_new("Curvature Controls  -  0.5/ridge^2 , 0.7/valley^2",
                tint=(0.30, 0.24, 0.16))
    r_sq = t.math('MULTIPLY', "ridge^2", IN["Screen Ridge"], IN["Screen Ridge"])
    r_safe = t.math('MAXIMUM', "max(ridge^2, 1e-4)", r_sq, 1e-4)
    ctrl_ridge = t.math('DIVIDE', "Ridge Control", 0.5, r_safe)
    v_sq = t.math('MULTIPLY', "valley^2", IN["Screen Valley"], IN["Screen Valley"])
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

    # ------------------------------------------------------- curvature (screen)
    t.frame_new("Curvature  -  signed, soft-clamped, x2",
                tint=(0.30, 0.24, 0.16))
    normal_diff = t.math('SUBTRACT', "normal_diff", s_convex, s_concave)
    neg_diff = t.math('MULTIPLY', "-normal_diff", normal_diff, -1.0)
    # Blender BRANCHES here and only ever evaluates the taken side. Node trees have
    # to evaluate both, so clamp each side's input to its own sign: the branch that
    # is not selected then computes soft_clamp(0) == 0 exactly. Without this the idle
    # branch reaches ~1e4 (c * (1 - c*ctrl) with ctrl = 0.7/1e-4 at Valley 0) and the
    # float32 cancellation in the select below eats ~1.5% of the factor.
    pos_diff = t.math('MAXIMUM', "max(normal_diff, 0)", normal_diff, 0.0)
    pos_neg_diff = t.math('MAXIMUM', "max(-normal_diff, 0)", neg_diff, 0.0)
    ridge_sc = soft_clamp(pos_diff, ctrl_ridge, "Ridge")
    valley_sc = soft_clamp(pos_neg_diff, ctrl_valley, "Valley")
    ridge_branch = t.math('MULTIPLY', "Ridge Branch  +2x", ridge_sc, 2.0)
    valley_branch = t.math('MULTIPLY', "Valley Branch  -2x", valley_sc, -2.0)
    is_ridge = t.math('GREATER_THAN', "normal_diff > 0", normal_diff, 0.0)
    branch_delta = t.math('SUBTRACT', "ridge - valley", ridge_branch, valley_branch)
    curvature = t.math('MULTIPLY_ADD', "curvature", branch_delta, is_ridge, valley_branch)
    one_plus_curv = t.math('ADD', "1 + curvature", 1.0, curvature)

    # ------------------------------------------------------------- composite
    t.frame_new("Composite  -  clamp( world * curvature , 0 , 4 )",
                tint=(0.30, 0.16, 0.20))
    product = t.math('MULTIPLY', "world * curvature", world_term, one_plus_curv)
    clamp = t.new('ShaderNodeClamp', "Clamp 0..4")
    clamp.inputs['Min'].default_value = 0.0
    clamp.inputs['Max'].default_value = 4.0
    t.link(product, clamp.inputs['Value'])
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
    t.link(w_concave, gout.inputs["Concave"])
    t.link(w_convex, gout.inputs["Convex"])

    return ng


# --------------------------------------------------------------------------- #
#  demo scene
# --------------------------------------------------------------------------- #
def demo_material(name, ng, flat):
    """flat=True -> Emission(Factor) = the literal viewport overlay.
       flat=False -> the overlay multiplied into a Principled base colour."""
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
        # kept dark enough that a ridge (factor up to ~2) still lands under 1.0
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
    world.node_tree.nodes["Background"].inputs[1].default_value = 1.0
    scene.world = world

    made = []
    for i, (name, flat, x) in enumerate((("SH_Cavity_Demo", False, -1.6),
                                         ("SH_Cavity_Demo_Flat", True, 1.6))):
        bpy.ops.mesh.primitive_monkey_add(size=2, location=(x, 0, 0))
        ob = bpy.context.object
        ob.name = name
        ob.data.name = name
        bpy.ops.object.shade_smooth()
        sub = ob.modifiers.new("Subdivision", 'SUBSURF')
        sub.levels = 2
        sub.render_levels = 2
        mat = demo_material("M_%s" % name, ng, flat)
        ob.data.materials.append(mat)
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


# --------------------------------------------------------------------------- #
def publish(ng):
    ng.asset_mark()
    ng.asset_data.catalog_id = CATALOG_SHADING
    ng.asset_data.tags.new("ST3E")
    ng.asset_data.description = (
        "Reproduces the Solid-viewport Cavity overlay (World + Screen Space) inside "
        "EEVEE and Material Preview. Ridge/Valley sliders behave like the viewport's; "
        "the curvature source is an Ambient Occlusion probe pair instead of the depth "
        "and normal buffers."
    )
    # is_modifier / is_tool are GeometryNodeTree traits; a ShaderNodeTree has neither.
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
