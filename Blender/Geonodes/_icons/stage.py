"""Studio staging scene, base meshes and mesh-prep steps for ST3E geonode icons.

Imported by build_icons.py, which runs inside Blender. Nothing here touches the
source .blend files - node groups are appended as copies into this throwaway
scene, so mutating them (menu defaults etc.) is safe.
"""
import bpy
import hashlib
import math
import os
from array import array
from mathutils import Vector

SIZE = 256
CLAY = (0.62, 0.63, 0.66, 1.0)

# X is elevation (90 deg = eye level, smaller looks down more steeply),
# Z is azimuth, Y would be ROLL - keep it at zero.
CAM_ROT = (math.radians(70.0), 0.0, math.radians(35.0))
MARGIN = 1.06            # bbox padding so nothing clips the frame
CAGE_MARGIN = 1.10       # extra padding when a cage is drawn, so it is
                         # not sliced off at the tile border
# Vertical space the frame claims at each end. The subject is fitted into what
# is left and centred in THAT band, rather than in the raw square.
BAR_SAFE = 41.0 / SIZE     # top bar (29.4px) plus clearance
LABEL_SAFE = 62.0 / SIZE   # bottom scrim and the name label
BAND_CENTRE = (LABEL_SAFE - BAR_SAFE) * 0.5   # where the subject should sit
CAGE_THICKNESS = 0.0032  # cage tube radius as a fraction of the subject size
CAGE_RESOLUTION = 6      # default cage density
WIRE_THICKNESS = 0.0028  # ghost-wire tube radius, same fraction
WIRE_COLOUR = (0.015, 0.015, 0.02)   # near-black: thin emissive tubes
                                     # wash out badly under antialiasing

# Per-icon name label, burned into the render (it cannot live in the frame
# overlay - that is shared by every icon in a catalog).
LABEL_CAP_PX = 19.25     # 2px taller than the frame's bar text
LABEL_BOTTOM_PX = 30.0   # centre height above the bottom edge
LABEL_SHADOW_PX = 2.0    # drop-shadow DISTANCE, down-right
LABEL_OUTLINE_PX = 1.3   # black halo radius: a drop shadow alone leaves
                         # white text unreadable over a white subject
LABEL_PAD_PX = 16.0      # clear space either side before the text shrinks
MONO_CANDIDATES = (
    r"C:\Windows\Fonts\consola.ttf",
    r"C:\Windows\Fonts\cour.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
)
# Vendored next to the scripts rather than relied on from the system font
# directory, so the build does not depend on what happens to be installed.
# Familjen Grotesk is SIL OFL; the licence ships beside it.
#
# The STATIC instance, deliberately: Blender fills the capital A of the
# variable build (FamiljenGrotesk[wght].ttf) as a solid triangle - the leg
# aperture closes and the counter collapses to a sliver. Every other glyph is
# fine, and the static builds are correct, so this is a variable-outline
# problem in Blender's font-to-curve conversion, not a sizing one.
LABEL_FONT = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                          "fonts", "FamiljenGrotesk-Medium.ttf")

# Catalog tints, matching make_frames.CATALOGS - the deformation cage is drawn
# in its catalog colour so it ties back to the frame.
TINTS = {
    "Deform":   (0.91, 0.51, 0.23),
    "Generate": (0.31, 0.64, 0.82),
    "Modify":   (0.49, 0.70, 0.26),
    "Scatter":  (0.64, 0.42, 0.85),
    "Shading":  (0.88, 0.72, 0.24),
    "Group":    (0.37, 0.49, 0.54),
    "Neutral":  (0.60, 0.63, 0.65),
}
LIGHT_ENERGY = 140.0     # watts at ortho_scale == 1; scaled per subject

# Three-point rig. Positions are in RIG space, which is centred on the SUBJECT
# and oriented like the camera: +X right, +Y up, +Z toward the viewer. Anchor
# it to the subject, not the camera - the camera sits 4x the framing away, so
# a light at camera-local -Z is still in front of the subject and produces a
# frontal hotspot instead of a rim.
#   name, local position, energy multiplier, area size, colour
LIGHT_SPECS = (
    # Subtle colour separation: warm key, cool fill, faintly cyan rim.
    ("Key",  (1.55, 1.15, 1.25), 0.60, 1.40, (1.00, 0.955, 0.880)),
    ("Fill", (-1.40, -1.00, 1.70), 0.22, 2.20, (0.815, 0.880, 1.000)),
    # Harsh rim: LEFT, low and well behind the subject, small and hot so it
    # lays a crisp line down the left silhouette instead of a soft wash. The
    # key sits on the opposite side so that edge is otherwise in shadow.
    ("Rim",  (-2.20, 0.60, -3.00), 5.00, 0.22, (0.900, 0.965, 1.000)),
)


# The label has to composite ON TOP of the frame overlay (the bottom gradient
# would otherwise wash over it), while the subject has to composite UNDER it.
# One render, two view layers: subject -> over frame -> over label.
SUBJECT_LAYER = "Subject"
LABEL_LAYER = "Label"
SCENE_COLL = "IconScene"
LABEL_COLL = "IconLabel"


# --------------------------------------------------------------------------
# scene
# --------------------------------------------------------------------------

def wipe():
    for coll in (bpy.data.objects, bpy.data.meshes, bpy.data.materials,
                 bpy.data.lights, bpy.data.cameras, bpy.data.node_groups,
                 bpy.data.curves, bpy.data.collections):
        for item in list(coll):
            try:
                coll.remove(item)
            except Exception:
                pass


def link_scene(obj):
    bpy.data.collections[SCENE_COLL].objects.link(obj)
    return obj


def link_label(obj):
    bpy.data.collections[LABEL_COLL].objects.link(obj)
    return obj


def _build_layers(sc):
    """Two collections, two view layers, each seeing only one of them."""
    while len(sc.view_layers) > 1:
        sc.view_layers.remove(sc.view_layers[-1])
    subject_vl = sc.view_layers[0]
    subject_vl.name = SUBJECT_LAYER
    for name in (SCENE_COLL, LABEL_COLL):
        coll = bpy.data.collections.new(name)
        sc.collection.children.link(coll)
    label_vl = sc.view_layers.new(LABEL_LAYER)
    # Only the children are touched here. Writing .exclude on the MASTER layer
    # collection cascade-resets the whole view layer.
    subject_vl.layer_collection.children[LABEL_COLL].exclude = True
    label_vl.layer_collection.children[SCENE_COLL].exclude = True
    label_vl.use = False          # nothing to render until a label exists
    bpy.context.window.view_layer = subject_vl if bpy.context.window else None
    bpy.context.view_layer.active_layer_collection = (
        subject_vl.layer_collection.children[SCENE_COLL])
    return subject_vl, label_vl


def build_scene():
    """Create the world, camera and the three subject-anchored area lights."""
    sc = bpy.context.scene
    _build_layers(sc)
    # Cycles on CPU, not EEVEE: headless EEVEE goes through the GPU driver
    # (nvoglv64) and segfaults unpredictably in --background, and it cannot
    # render a lightless scene there at all. Cycles CPU is driver-independent
    # and a 256px icon still costs well under a second.
    sc.render.engine = 'CYCLES'
    sc.cycles.device = 'CPU'
    sc.cycles.samples = 128
    sc.cycles.use_denoising = True
    sc.cycles.transparent_max_bounces = 8
    sc.render.resolution_x = sc.render.resolution_y = SIZE
    sc.render.resolution_percentage = 100
    sc.render.film_transparent = True
    sc.render.image_settings.file_format = 'PNG'
    sc.render.image_settings.color_mode = 'RGBA'
    sc.render.image_settings.color_depth = '8'
    sc.view_settings.view_transform = 'Standard'
    sc.view_settings.look = 'None'

    world = bpy.data.worlds.new("IconWorld")
    world.use_nodes = True
    sc.world = world
    bg = next(n for n in world.node_tree.nodes if n.type == 'BACKGROUND')
    bg.inputs["Color"].default_value = (0.05, 0.05, 0.055, 1.0)
    bg.inputs["Strength"].default_value = 0.6

    cam_data = bpy.data.cameras.new("IconCam")
    cam_data.type = 'ORTHO'
    cam_data.clip_start = 0.01
    cam_data.clip_end = 1000.0
    cam = bpy.data.objects.new("IconCam", cam_data)
    sc.collection.objects.link(cam)     # master: visible to both view layers
    cam.rotation_euler = CAM_ROT
    sc.camera = cam

    # The rig is an empty placed on the subject and rotated like the camera;
    # refit_lights() positions it per icon.
    rig = link_scene(bpy.data.objects.new("LightRig", None))
    rig.rotation_euler = CAM_ROT
    for name, loc, mult, size, colour in LIGHT_SPECS:
        light = bpy.data.lights.new("L" + name, 'AREA')
        light.color = colour
        light["energy_mult"] = mult
        light["size_mult"] = size
        obj = link_scene(bpy.data.objects.new("L" + name, light))
        obj.parent = rig
        obj["base_loc"] = loc
        obj.location = loc
        con = obj.constraints.new('TRACK_TO')
        con.target = rig
        con.track_axis = 'TRACK_NEGATIVE_Z'
        con.up_axis = 'UP_Y'
    return cam


def refit_lights(scale, centre):
    """Sit the rig on the subject and keep irradiance constant.

    Distance, area size and energy have to move together: scaling energy with
    the square of the framing while the lights sit still makes a large subject
    read brighter than a small one. Pushing the rig out by `scale` too keeps
    irradiance flat.
    """
    rig = bpy.data.objects.get("LightRig")
    if rig is not None:
        rig.location = centre
        rig.rotation_euler = CAM_ROT
    for obj in bpy.data.objects:
        if obj.type != 'LIGHT':
            continue
        base = obj.get("base_loc", (0.0, 0.0, 0.0))
        obj.location = tuple(c * scale for c in base)
        obj.scale = (1.0, 1.0, 1.0)
        obj.data.size = obj.data["size_mult"] * scale
        obj.data.energy = LIGHT_ENERGY * obj.data["energy_mult"] * scale * scale


def add_interior_light(centre, scale, mult=0.012):
    """A point light inside the subject, for hollow renders.

    A culled shell is a closed cavity: every rig light is outside it, so the
    interior reads as a flat silhouette no matter how much emission it carries.
    Lighting it from within is what gives the hollow its depth.

    `mult` is tiny compared with the rig because the light sits roughly one
    radius from the shell rather than several: at the rig's own levels the
    cavity saturates to pure white.
    """
    light = bpy.data.lights.new("LInterior", 'POINT')
    light.energy = LIGHT_ENERGY * mult * scale * scale
    light.shadow_soft_size = 0.25 * scale
    obj = link_scene(bpy.data.objects.new("LInterior", light))
    obj.location = centre
    return obj


# --------------------------------------------------------------------------
# materials
# --------------------------------------------------------------------------

def _principled(mat):
    mat.use_nodes = True
    return next(n for n in mat.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')


def clay_material(name="IconClay", colour=CLAY):
    mat = bpy.data.materials.new(name)
    bsdf = _principled(mat)
    bsdf.inputs["Base Color"].default_value = colour
    bsdf.inputs["Roughness"].default_value = 0.45
    bsdf.inputs["Metallic"].default_value = 0.0
    return mat


def accent_material(colour):
    """Flat emissive accent, used for the deformation cage."""
    mat = bpy.data.materials.new("IconAccent")
    mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()
    em = nt.nodes.new("ShaderNodeEmission")
    em.inputs["Color"].default_value = (colour[0], colour[1], colour[2], 1.0)
    em.inputs["Strength"].default_value = 1.0
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    nt.links.new(em.outputs[0], out.inputs["Surface"])
    return mat


BACKFACE = (0.86, 0.33, 0.22, 1.0)


def hollow_clay_material(name="IconHollow", colour=CLAY):
    """Cull the camera-facing surface so the shell reads as hollow.

    Cycles flips the shading normal toward the viewer for opaque BSDFs, so a
    flipped face renders EXACTLY like an unflipped one - plain clay gives no
    icon at all. Culling by Backfacing shows the far shell's interior instead,
    but that cavity is enclosed and lit from outside only, so on its own it
    comes out a black silhouette. A little emission lifts it into view.
    """
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()
    geo = nt.nodes.new("ShaderNodeNewGeometry")
    bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
    bsdf.inputs["Base Color"].default_value = colour
    bsdf.inputs["Roughness"].default_value = 0.6
    glow = nt.nodes.new("ShaderNodeEmission")
    glow.inputs["Color"].default_value = colour
    glow.inputs["Strength"].default_value = 0.0
    lit = nt.nodes.new("ShaderNodeAddShader")
    nt.links.new(bsdf.outputs[0], lit.inputs[0])
    nt.links.new(glow.outputs[0], lit.inputs[1])
    trans = nt.nodes.new("ShaderNodeBsdfTransparent")
    mix = nt.nodes.new("ShaderNodeMixShader")
    nt.links.new(geo.outputs["Backfacing"], mix.inputs["Fac"])
    nt.links.new(lit.outputs[0], mix.inputs[1])
    nt.links.new(trans.outputs[0], mix.inputs[2])
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    nt.links.new(mix.outputs[0], out.inputs["Surface"])
    return mat


def two_sided_clay_material(name="IconTwoSided", front=CLAY, back=BACKFACE):
    """Clay in front, a warning tint behind.

    A flipped face renders identically to an unflipped one, so GN_FlipFaces has
    no icon without this. Culling the backfaces instead just leaves a black
    silhouette - unlit inward normals - which reads as a broken render rather
    than a flip. Note `use_backface_culling` is an EEVEE property and does
    nothing under Cycles, so the split has to be built in the shader.
    """
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()
    geo = nt.nodes.new("ShaderNodeNewGeometry")
    mix = nt.nodes.new("ShaderNodeMixShader")
    for slot, colour in ((1, front), (2, back)):
        bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
        bsdf.inputs["Base Color"].default_value = colour
        bsdf.inputs["Roughness"].default_value = 0.45
        nt.links.new(bsdf.outputs[0], mix.inputs[slot])
    nt.links.new(geo.outputs["Backfacing"], mix.inputs["Fac"])
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    nt.links.new(mix.outputs[0], out.inputs["Surface"])
    return mat


def transfer_split_material(attr_name, hue_shift=0.45, name="IconXfer"):
    """One attribute, two colourings, split on a screen-space diagonal.

    The left half shows the attribute as authored, the right the same pattern
    hue-shifted - the same data arriving somewhere else. The diagonal is cut in
    Window coordinates so it is a clean screen-space line regardless of the
    subject's shape.
    """
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()
    attr = nt.nodes.new("ShaderNodeAttribute")
    attr.attribute_type = 'GEOMETRY'
    attr.attribute_name = attr_name

    shifted = nt.nodes.new("ShaderNodeHueSaturation")
    shifted.inputs["Hue"].default_value = 0.5 + hue_shift
    shifted.inputs["Saturation"].default_value = 1.4
    nt.links.new(attr.outputs["Color"], shifted.inputs["Color"])

    coord = nt.nodes.new("ShaderNodeTexCoord")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    nt.links.new(coord.outputs["Window"], sep.inputs["Vector"])
    diag = nt.nodes.new("ShaderNodeMath")
    diag.operation = 'ADD'
    nt.links.new(sep.outputs["X"], diag.inputs[0])
    nt.links.new(sep.outputs["Y"], diag.inputs[1])
    side = nt.nodes.new("ShaderNodeMath")
    side.operation = 'GREATER_THAN'
    side.inputs[1].default_value = 1.0
    nt.links.new(diag.outputs[0], side.inputs[0])

    mix = nt.nodes.new("ShaderNodeMix")
    mix.data_type = 'RGBA'
    nt.links.new(side.outputs[0], mix.inputs["Factor"])
    nt.links.new(attr.outputs["Color"], mix.inputs[6])
    nt.links.new(shifted.outputs["Color"], mix.inputs[7])

    em = nt.nodes.new("ShaderNodeEmission")
    nt.links.new(mix.outputs[2], em.inputs["Color"])
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    nt.links.new(em.outputs[0], out.inputs["Surface"])
    return mat


def attribute_material(attr_name, channel="color", shade="emission"):
    """Show a geometry attribute the modifier wrote.

    `shade="emission"` is unlit, so the attribute is reproduced exactly - the
    honest choice for modifiers whose whole output IS the attribute (AO, Set
    Attribute, Vertex Data Composer). `shade="clay"` feeds it into a lit
    Principled instead, for when the attribute only tints the surface.
    """
    mat = bpy.data.materials.new("IconAttr_" + attr_name)
    mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()
    attr = nt.nodes.new("ShaderNodeAttribute")
    attr.attribute_type = 'GEOMETRY'
    attr.attribute_name = attr_name
    src = attr.outputs["Color"] if channel == "color" else attr.outputs["Fac"]
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    if shade == "emission":
        shader = nt.nodes.new("ShaderNodeEmission")
        shader.inputs["Strength"].default_value = 1.0
        nt.links.new(src, shader.inputs["Color"])
    else:
        shader = nt.nodes.new("ShaderNodeBsdfPrincipled")
        shader.inputs["Roughness"].default_value = 0.6
        nt.links.new(src, shader.inputs["Base Color"])
    nt.links.new(shader.outputs[0], out.inputs["Surface"])
    return mat


PALETTE = ((0.85, 0.34, 0.24, 1.0), (0.30, 0.55, 0.82, 1.0),
           (0.45, 0.72, 0.36, 1.0), (0.88, 0.72, 0.28, 1.0),
           (0.62, 0.42, 0.78, 1.0))


# --------------------------------------------------------------------------
# base meshes
# --------------------------------------------------------------------------

def base_suzanne():
    bpy.ops.mesh.primitive_monkey_add(size=2.0, location=(0, 0, 0))
    return bpy.context.object


def base_grid(x=24, y=24, size=2.0):
    bpy.ops.mesh.primitive_grid_add(x_subdivisions=x, y_subdivisions=y,
                                    size=size, location=(0, 0, 0))
    return bpy.context.object


def base_plane(size=2.0):
    bpy.ops.mesh.primitive_plane_add(size=size, location=(0, 0, 0))
    return bpy.context.object


def base_cylinder(verts=24, r=0.7, depth=2.0):
    bpy.ops.mesh.primitive_cylinder_add(vertices=verts, radius=r, depth=depth,
                                        location=(0, 0, 0))
    return bpy.context.object


def base_nodegraph(spacing=0.95, box=0.30, wire=0.055):
    """Three linked boxes - the emblem for a reusable node GROUP.

    GNG_* helpers mostly cannot be attached as modifiers at all (their first
    input is a Bool, Colour, Vector or Menu, so Blender has no geometry to
    bind), which means there is no "effect on Suzanne" to photograph. They get
    a shared emblem instead, distinguished by the name in the label.
    """
    import bmesh
    from mathutils import Matrix
    centres = [(-spacing, 0.0, 0.42), (0.0, 0.0, -0.18), (spacing, 0.0, 0.42)]
    bm = bmesh.new()
    for cx, cy, cz in centres:
        bmesh.ops.create_cube(bm, size=1.0,
                              matrix=Matrix.Translation((cx, cy, cz))
                              @ Matrix.Diagonal((box * 2, box * 1.3, box * 1.6, 1.0)))
    for a, b in ((0, 1), (1, 2)):
        ax, ay, az = centres[a]
        bx, by, bz = centres[b]
        mid = ((ax + bx) / 2, (ay + by) / 2, (az + bz) / 2)
        dx, dz = bx - ax, bz - az
        length = (dx * dx + dz * dz) ** 0.5
        rot = Matrix.Rotation(-__import__("math").atan2(dz, dx), 4, 'Y')
        bmesh.ops.create_cube(bm, size=1.0,
                              matrix=Matrix.Translation(mid) @ rot
                              @ Matrix.Diagonal((length, wire, wire, 1.0)))
    mesh = bpy.data.meshes.new("NodeGraph")
    bm.to_mesh(mesh)
    bm.free()
    obj = bpy.data.objects.new("NodeGraph", mesh)
    link_scene(obj)
    bpy.context.view_layer.objects.active = obj
    return obj


def base_icosphere(subdiv=3, r=1.0):
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=subdiv, radius=r,
                                          location=(0, 0, 0))
    return bpy.context.object


BASES = {
    "suzanne": base_suzanne,
    "grid": base_grid,
    "plane": base_plane,
    "cylinder": base_cylinder,
    "icosphere": base_icosphere,
    "nodegraph": base_nodegraph,
}


# --------------------------------------------------------------------------
# prep steps - the answer to "this modifier shows nothing without setup"
# --------------------------------------------------------------------------

def prep_shade_smooth(obj):
    for poly in obj.data.polygons:
        poly.use_smooth = True


def prep_subsurf(obj, levels=1):
    """Bake a Catmull-Clark pass into the base mesh (before the GN modifier)."""
    mod = obj.modifiers.new("PrepSubsurf", 'SUBSURF')
    mod.levels = mod.render_levels = levels
    with bpy.context.temp_override(object=obj):
        bpy.ops.object.modifier_apply(modifier=mod.name)


def prep_material_slots(obj, count=3, tint=False):
    """Give the object `count` distinct material slots (index 0..count-1).

    The slots exist so that material_index-driven modifiers have something to
    bite on; by default they are all the same clay so the icon still reads as
    part of the family. Pass tint=True when the material split itself is the
    thing the icon has to show (GN_SetMaterial, GN_MaterialOverride).
    """
    obj.data.materials.clear()
    for i in range(count):
        colour = PALETTE[i % len(PALETTE)] if tint else CLAY
        obj.data.materials.append(clay_material("IconSlot%d" % i, colour))


def prep_material_index_by(obj, mode="noise", count=None, freq=2.5, axis="z"):
    """Scatter material_index over the faces so index-driven modifiers bite."""
    slots = count or max(len(obj.data.materials), 1)
    for poly in obj.data.polygons:
        c = poly.center
        if mode == "noise":
            key = "%.3f%.3f%.3f" % (c.x, c.y, c.z)
            poly.material_index = int(
                hashlib.md5(key.encode()).hexdigest()[:8], 16) % slots
        elif mode == "stripes":
            poly.material_index = int((getattr(c, axis) + 2.0) * freq) % slots
        elif mode == "half":
            poly.material_index = 1 if c.x > 0.0 else 0
        elif mode == "region":
            # Everything past `freq` along `axis` gets index 1 - used to pick a
            # contiguous patch (the top of the skull) rather than a scatter.
            poly.material_index = 1 if getattr(c, axis) > freq else 0
        else:
            raise ValueError("unknown material_index mode %r" % mode)


def prep_attribute(obj, name, domain='POINT', data_type='FLOAT', expr="x"):
    """Write a named attribute so attribute-driven modifiers have an input."""
    attr = obj.data.attributes.new(name, data_type, domain)
    src = {'POINT': obj.data.vertices, 'FACE': obj.data.polygons,
           'EDGE': obj.data.edges}[domain]
    for i, elem in enumerate(src):
        co = getattr(elem, "co", None)
        if co is None:
            co = getattr(elem, "center", None)
        val = {"x": co.x, "y": co.y, "z": co.z, "index": float(i)}[expr]
        attr.data[i].value = val


def prep_convexity_colour(obj, name="src", base=(0.05, 0.05, 0.06),
                          ridge=(0.88, 0.28, 0.18), threshold=0.12):
    """Write a convexity map into a FLOAT_COLOR attribute.

    Discrete convexity per vertex: the mean of dot(normal, direction to each
    neighbour). On a convex ridge the neighbours fall away below the tangent
    plane, so that mean goes negative. Gives the same read as GN_SetAttribute's
    Convex selection without needing the node to produce it.
    """
    import bmesh
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bm.verts.ensure_lookup_table()
    conv = []
    for v in bm.verts:
        links = [e.other_vert(v) for e in v.link_edges]
        if not links:
            conv.append(0.0)
            continue
        total = 0.0
        for other in links:
            d = other.co - v.co
            if d.length > 1e-9:
                total += v.normal.dot(d.normalized())
        conv.append(-total / len(links))
    bm.free()

    attr = obj.data.attributes.new(name, 'FLOAT_COLOR', 'POINT')
    for i, c in enumerate(conv):
        hot = 1.0 if c > threshold else 0.0
        col = ridge if hot else base
        attr.data[i].color = (col[0], col[1], col[2], 1.0)


def prep_bool_attribute(obj, name, domain='EDGE', mode="bands", bands=4,
                        axis="z"):
    """Write a BOOLEAN attribute for attribute-bound selection sockets.

    `mode="bands"` marks evenly spaced rings along `axis`, which gives a
    boundary-selection modifier several distinct regions to work on instead of
    one. `mode="noise"` scatters it.
    """
    attr = obj.data.attributes.new(name, 'BOOLEAN', domain)
    src = {'POINT': obj.data.vertices, 'FACE': obj.data.polygons,
           'EDGE': obj.data.edges}[domain]
    verts = obj.data.vertices
    for i, elem in enumerate(src):
        if domain == 'EDGE':
            a, b = elem.vertices
            co = (verts[a].co + verts[b].co) * 0.5
        elif domain == 'FACE':
            co = elem.center
        else:
            co = elem.co
        v = getattr(co, axis)
        if mode == "bands":
            attr.data[i].value = (int((v + 2.0) * bands) % 2) == 0
        elif mode == "noise":
            key = "%.3f%.3f%.3f" % (co.x, co.y, co.z)
            attr.data[i].value = (int(hashlib.md5(key.encode())
                                      .hexdigest()[:8], 16) % 3) == 0
        else:
            raise ValueError("unknown bool attribute mode %r" % mode)


def prep_mark_open_boundary(obj, axis='z', threshold=0.0):
    """Delete faces on one side so the mesh gets a real open boundary."""
    import bmesh
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    doomed = [f for f in bm.faces
              if getattr(f.calc_center_median(), axis) > threshold]
    bmesh.ops.delete(bm, geom=doomed, context='FACES')
    bm.to_mesh(obj.data)
    bm.free()


def prep_add_loose(obj, verts=10, edges=5, islands=6, radius=1.45):
    """Add stray verts, edges and small islands for the cleanup modifiers.

    Islands are what actually read in an icon - a bare loose edge is a hairline
    that looks like a render artefact, whereas a little floating triangle is
    recognisably junk.
    """
    import bmesh
    bm = bmesh.new()
    bm.from_mesh(obj.data)

    def ring(i, n, r, lift):
        a = i * (6.2831853 / max(n, 1)) + 0.4
        return (math.cos(a) * r, math.sin(a) * r, lift)

    for i in range(verts):
        bm.verts.new(ring(i, verts, radius, (i % 5) * 0.32 - 0.64))
    bm.verts.ensure_lookup_table()
    for i in range(edges):
        bm.edges.new((bm.verts[-1 - i], bm.verts[-2 - i]))

    for i in range(islands):
        cx, cy, cz = ring(i, islands, radius * 1.05, (i % 4) * 0.42 - 0.63)
        size = 0.13 + 0.05 * (i % 3)
        tri = [bm.verts.new((cx, cy, cz + size)),
               bm.verts.new((cx + size, cy + size * 0.6, cz - size * 0.6)),
               bm.verts.new((cx - size, cy - size * 0.6, cz - size * 0.6))]
        bm.faces.new(tri)

    bm.to_mesh(obj.data)
    bm.free()


PREPS = {
    "shade_smooth": prep_shade_smooth,
    "subsurf": prep_subsurf,
    "material_slots": prep_material_slots,
    "material_index_by": prep_material_index_by,
    "attribute": prep_attribute,
    "bool_attribute": prep_bool_attribute,
    "convexity_colour": prep_convexity_colour,
    "mark_open_boundary": prep_mark_open_boundary,
    "add_loose": prep_add_loose,
}


def run_preps(obj, steps):
    for step in steps:
        if isinstance(step, str):
            name, args, kwargs = step, (), {}
        else:
            name, rest = step[0], list(step[1:])
            kwargs = rest.pop() if rest and isinstance(rest[-1], dict) else {}
            args = tuple(rest)
        PREPS[name](obj, *args, **kwargs)


# --------------------------------------------------------------------------
# node group loading + parameter binding
# --------------------------------------------------------------------------

def append_group(blend_path, group_name):
    with bpy.data.libraries.load(blend_path, link=False) as (src, dst):
        if group_name not in src.node_groups:
            raise KeyError("%r not in %s" % (group_name,
                                             os.path.basename(blend_path)))
        dst.node_groups = [group_name]
    ng = bpy.data.node_groups.get(group_name)
    if ng is None:
        raise KeyError("append of %r produced nothing" % group_name)
    return ng


def _sockets(ng):
    """Input sockets addressable three ways, plus the ambiguous bare names.

    Some groups expose several inputs with the SAME name - GN_MirrorGroup has
    six, GN_CellFrac has three "Seed"s. A bare name then binds whichever comes
    first, which is worse than failing, so those names are rejected. Two
    unambiguous forms are accepted instead:

        "U Scale#2"   the 2nd socket called "U Scale", 1-based
        "Socket_17"   the raw interface identifier
    """
    out, seen, dupes = {}, {}, set()
    for it in ng.interface.items_tree:
        if it.item_type != 'SOCKET' or it.in_out != 'INPUT':
            continue
        n = seen.get(it.name, 0) + 1
        seen[it.name] = n
        if n > 1:
            dupes.add(it.name)
        out.setdefault(it.name, it)
        out["%s#%d" % (it.name, n)] = it
        out[it.identifier] = it
    return out, dupes


def set_params(md, ng, params):
    """Bind params by socket NAME, resolving to identifiers.

    Menu sockets are set as a STRING on the appended group's interface default
    and the modifier override is dropped - the numeric value id a modifier
    stores for a menu is not exposed through the RNA, and this copy of the
    group is throwaway anyway.
    """
    lookup, dupes = _sockets(ng)
    unknown = [k for k in params if k not in lookup]
    if unknown:
        raise KeyError("%s: no such input socket(s) %s" % (ng.name, unknown))
    ambiguous = sorted(set(params) & dupes)
    if ambiguous:
        raise KeyError("%s: input socket name(s) %s are not unique - bind by "
                       "identifier or rename the socket" % (ng.name, ambiguous))
    for name, value in params.items():
        it = lookup[name]
        if isinstance(value, tuple) and value and value[0] == "attr":
            # Bind the socket to a mesh attribute, the way the modifier UI's
            # little spreadsheet toggle does. A plain value cannot express a
            # per-element field, which is what selection sockets want.
            md[it.identifier + "_use_attribute"] = True
            md[it.identifier + "_attribute_name"] = value[1]
            continue
        if it.socket_type == 'NodeSocketMenu':
            if not isinstance(value, str):
                raise TypeError("%s.%s is a Menu; pass the item name"
                                % (ng.name, name))
            it.default_value = value
            try:
                del md[it.identifier]
            except (KeyError, TypeError):
                pass
        else:
            # Vector/colour sockets are array IDProperties: the length has to
            # match exactly, and the error Blender raises names only the
            # identifier, so say which socket it was.
            try:
                md[it.identifier] = value
            except TypeError as exc:
                raise TypeError("%s.%s (%s): %s"
                                % (ng.name, name, it.socket_type, exc))


def edges_to_tubes(name, mesh, matrix, colour, radius):
    """Convert an edge-only mesh into beveled curves so a renderer draws it."""
    obj = link_scene(bpy.data.objects.new(name, mesh))
    obj.matrix_world = matrix.copy()
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    with bpy.context.temp_override(object=obj, active_object=obj,
                                   selected_editable_objects=[obj]):
        bpy.ops.object.convert(target='CURVE')
    obj.data.bevel_depth = radius
    obj.data.bevel_resolution = 1
    obj.data.materials.append(accent_material(colour))
    return obj


def build_ghost_wire(subject, colour=WIRE_COLOUR, mode="removed",
                     thickness=WIRE_THICKNESS):
    """Draw a wireframe over the subject.

    Three modes, for three things a solid render cannot show on its own:

    - "removed": only the ORIGINAL edges whose vertices are absent from the
      result, so the wire appears exactly over the hole a delete-type modifier
      left and nowhere else - no z-fighting against the surviving surface.
      Deletion does not move vertices, so matching them by rounded position is
      exact. Meaningless for a deformer.
    - "all": the whole original mesh, for modifiers that refine it (the coarse
      cage over a Subdivide result).
    - "result": the evaluated mesh's own edges, for topology operators whose
      output is a smooth surface that looks unchanged until you see its new
      edge flow (Triangulate, Dual Mesh, Voxel Remesh).
    """
    import bmesh

    def key(co):
        return (round(co.x, 5), round(co.y, 5), round(co.z, 5))

    dg = bpy.context.evaluated_depsgraph_get()
    oe = subject.evaluated_get(dg)
    result = oe.to_mesh()

    bm = bmesh.new()
    if mode == "result":
        bm.from_mesh(result)
        survivors = set()
    else:
        survivors = {key(v.co) for v in result.vertices}
        bm.from_mesh(subject.data)
    oe.to_mesh_clear()

    # FACES_ONLY drops the faces but keeps their verts and edges, unlike the
    # FACES used for the cage.
    bmesh.ops.delete(bm, geom=list(bm.faces), context='FACES_ONLY')
    if mode == "removed":
        drop = [e for e in bm.edges
                if key(e.verts[0].co) in survivors
                or key(e.verts[1].co) in survivors]
        bmesh.ops.delete(bm, geom=drop, context='EDGES')
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_edges],
                     context='VERTS')
    edge_count = len(bm.edges)
    mesh = bpy.data.meshes.new("GhostWireMesh")
    bm.to_mesh(mesh)
    bm.free()
    if edge_count == 0:
        bpy.data.meshes.remove(mesh)
        return None
    return edges_to_tubes("GhostWire", mesh, subject.matrix_world, colour,
                          max(subject.dimensions) * thickness)


def build_cage(subject, md, ng, colour, resolution=CAGE_RESOLUTION):
    """Turn the modifier's deformation preview into renderable geometry.

    The preview the ST3E deformers emit is loose EDGES joined into the output,
    which a renderer does not draw. Extract those edges, convert them to a
    curve and bevel them into tubes, then switch the preview back off so the
    subject itself renders clean.
    """
    import bmesh
    ids = {it.name: it.identifier for it in ng.interface.items_tree
           if hasattr(it, "identifier")}
    if "Show Deformation Preview" not in ids:
        return None
    md[ids["Show Deformation Preview"]] = True
    if "Preview Resolution" in ids:
        md[ids["Preview Resolution"]] = resolution
    subject.update_tag()
    bpy.context.view_layer.update()

    dg = bpy.context.evaluated_depsgraph_get()
    oe = subject.evaluated_get(dg)
    src = oe.to_mesh()
    bm = bmesh.new()
    bm.from_mesh(src)
    oe.to_mesh_clear()
    # context='FACES' drops the faces and any vert/edge only they used, which
    # leaves exactly the loose preview edges behind.
    bmesh.ops.delete(bm, geom=list(bm.faces), context='FACES')
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_edges],
                     context='VERTS')
    edge_count = len(bm.edges)
    mesh = bpy.data.meshes.new("CageMesh")
    bm.to_mesh(mesh)
    bm.free()

    md[ids["Show Deformation Preview"]] = False
    subject.update_tag()
    bpy.context.view_layer.update()

    if edge_count == 0:
        bpy.data.meshes.remove(mesh)
        return None

    return edges_to_tubes("Cage", mesh, subject.matrix_world, colour,
                          max(subject.dimensions) * CAGE_THICKNESS)


# --------------------------------------------------------------------------
# effect verification - catches "this icon is a lie"
# --------------------------------------------------------------------------

def signature(obj):
    dg = bpy.context.evaluated_depsgraph_get()
    # Instances are NOT part of to_mesh(), so an instancing modifier looks like
    # it produced nothing - or worse, like it destroyed the mesh.
    instances = sum(1 for i in dg.object_instances if i.is_instance)
    oe = obj.evaluated_get(dg)
    me = oe.to_mesh()
    nv, npoly = len(me.vertices), len(me.polygons)
    co = array('f', [0.0]) * (nv * 3)
    if nv:
        me.vertices.foreach_get("co", co)
    digest = hashlib.md5(co.tobytes()).hexdigest()[:12]
    attrs = sorted(a.name for a in me.attributes)
    mats = [m.name if m else None for m in me.materials]
    # Winding and smooth flags, so modifiers that only touch shading (Flip
    # Faces, Auto Smooth) are still measurable - nothing else in this snapshot
    # moves for them.
    shading = array('f', [0.0]) * (npoly * 3)
    smooth = array('b', [0]) * npoly
    if npoly:
        me.polygons.foreach_get("normal", shading)
        me.polygons.foreach_get("use_smooth", smooth)
    corner = b""
    if hasattr(me, "corner_normals") and len(me.corner_normals):
        cbuf = array('f', [0.0]) * (len(me.corner_normals) * 3)
        me.corner_normals.foreach_get("vector", cbuf)
        corner = cbuf.tobytes()
    shade_hash = hashlib.md5(shading.tobytes() + smooth.tobytes()
                             + corner).hexdigest()[:12]
    oe.to_mesh_clear()
    return {"verts": nv, "polys": npoly, "hash": digest, "attrs": attrs,
            "mats": mats, "instances": instances, "shading": shade_hash}


def _attr_varies(obj, name):
    dg = bpy.context.evaluated_depsgraph_get()
    oe = obj.evaluated_get(dg)
    me = oe.to_mesh()
    a = me.attributes.get(name)
    if a is None:
        have = sorted(x.name for x in me.attributes)
        oe.to_mesh_clear()
        return False, "attribute %r missing (have %s)" % (name, have)
    n = len(a.data)
    is_col = a.data_type in ('FLOAT_COLOR', 'BYTE_COLOR')
    width, field = (4, "color") if is_col else (1, "value")
    buf = array('f', [0.0]) * (n * width)
    a.data.foreach_get(field, buf)
    oe.to_mesh_clear()
    lo, hi = min(buf), max(buf)
    return (hi - lo) > 1e-4, "%s: range %.4f..%.4f over %d elems" % (name, lo, hi, n)


def check_effect(obj, before, after, expect):
    """Return (ok, message). `expect` is the recipe's declared effect kind."""
    if expect.startswith("attribute_added:"):
        # For nodes whose output an icon cannot show directly: assert only that
        # the modifier created the attribute it targets.
        want = expect.split(":", 1)[1]
        return (want in after.get("attrs", []) and want not in before.get("attrs", []),
                "attribute %r added: %s" % (want, want in after.get("attrs", [])))
    if expect.startswith("attribute:"):
        return _attr_varies(obj, expect.split(":", 1)[1])
    if expect == "instances_up":
        # For scatter/instancer modifiers the mesh often goes to zero while the
        # real output appears as instances; count those instead.
        return (after.get("instances", 0) > before.get("instances", 0),
                "instances %d -> %d" % (before.get("instances", 0),
                                        after.get("instances", 0)))
    if expect == "shading":
        return (before.get("shading") != after.get("shading"),
                "shading %s -> %s" % (before.get("shading"),
                                      after.get("shading")))
    if expect == "material":
        # Assigning a material changes no geometry at all, so the position
        # hash cannot see it; compare the evaluated slots instead.
        return (before.get("mats") != after.get("mats"),
                "materials %s -> %s" % (before.get("mats"), after.get("mats")))
    same = (before["hash"] == after["hash"]
            and before["verts"] == after["verts"]
            and before["polys"] == after["polys"])
    delta = ("verts %d->%d, polys %d->%d, hash %s"
             % (before["verts"], after["verts"], before["polys"],
                after["polys"], "same" if before["hash"] == after["hash"]
                else "changed"))
    if expect == "deform":
        if before["verts"] != after["verts"]:
            return False, "expected pure deform but vert count changed: " + delta
        return (not same), delta
    if expect == "verts_up":
        return after["verts"] > before["verts"], delta
    if expect == "verts_down":
        return after["verts"] < before["verts"], delta
    if expect in ("topology", "any"):
        return (not same), delta
    raise ValueError("unknown expect kind %r" % expect)


def load_mono_font():
    for path in MONO_CANDIDATES:
        if os.path.exists(path):
            return bpy.data.fonts.load(path, check_existing=True)
    return bpy.data.fonts.load("<builtin>", check_existing=True)


def load_label_font():
    if os.path.exists(LABEL_FONT):
        return bpy.data.fonts.load(LABEL_FONT, check_existing=True)
    print("WARNING: %s missing, falling back to the mono font" % LABEL_FONT)
    return load_mono_font()


def _cap_ratio(font):
    """Rendered height of a capital at em size 1.0.

    Normalising a label by its own bounding box instead would size it by
    whatever ascenders and descenders the string happens to contain, so
    "Spherify" (descender) would come out smaller than "Subdivide" (none).
    """
    curve = bpy.data.curves.new("CapProbe", type='FONT')
    curve.body = "H"
    curve.font = font
    curve.size = 1.0
    probe = bpy.data.objects.new("CapProbe", curve)
    bpy.context.scene.collection.objects.link(probe)
    bpy.context.view_layer.update()
    ratio = probe.dimensions.y
    bpy.data.objects.remove(probe, do_unlink=True)
    bpy.data.curves.remove(curve)
    return ratio or 0.7


def build_label(cam, text, scale):
    """Burn the modifier's short name over the lower part of the tile.

    Parented to the camera at a fixed local offset, so under an ortho camera
    it lands on the same pixels whatever the subject's size or position.
    """
    if not text:
        return []
    bpy.context.scene.view_layers[LABEL_LAYER].use = True
    font = load_label_font()
    px = scale / SIZE                      # world units per rendered pixel
    size = LABEL_CAP_PX * px / _cap_ratio(font)
    centre_y = -(0.5 - LABEL_BOTTOM_PX / SIZE) * scale
    max_width = scale - 2.0 * LABEL_PAD_PX * px
    # Split across both axes so the diagonal distance is the stated one;
    # offsetting by the full amount on each axis is sqrt(2) too far.
    shadow = LABEL_SHADOW_PX * px / (2.0 ** 0.5)

    # Draw order, furthest from the camera first: a black halo in eight
    # directions, then the offset drop shadow, then the white text on top.
    halo = LABEL_OUTLINE_PX * px
    passes = []
    for i in range(8):
        a = i * math.pi / 4.0
        passes.append(((math.cos(a) * halo, math.sin(a) * halo),
                       (0.0, 0.0, 0.0), -0.503))
    passes.append(((shadow, -shadow), (0.0, 0.0, 0.0), -0.502))
    passes.append(((0.0, 0.0), (1.0, 1.0, 1.0), -0.500))

    made = []
    for offset, colour, depth in passes:
        curve = bpy.data.curves.new("Label", type='FONT')
        curve.body = text
        curve.font = font
        curve.align_x = 'CENTER'
        curve.align_y = 'CENTER'
        curve.size = size
        curve.materials.append(accent_material(colour))
        obj = link_label(bpy.data.objects.new("Label", curve))
        obj.parent = cam
        obj.location = (offset[0], centre_y + offset[1], depth * scale)
        bpy.context.view_layer.update()
        if obj.dimensions.x > max_width:
            obj.scale = [max_width / obj.dimensions.x] * 3
        made.append(obj)
    return made


# --------------------------------------------------------------------------
# framing + render
# --------------------------------------------------------------------------

def world_points(obj):
    """World-space vertices of an object's UNEVALUATED mesh."""
    mw = obj.matrix_world
    return [mw @ v.co for v in obj.data.vertices]


def frame_camera(cam, objs, extra_points=(), margin=MARGIN):
    """Fit the ortho camera to the objects, plus any extra world-space points.

    `extra_points` carries the pre-modifier bounds. Framing on the result alone
    makes a modifier that REMOVES geometry look like a zoom-in rather than a
    deletion, and makes every icon a different scale; including the original
    bounds keeps the subject the same size before and after.
    """
    dg = bpy.context.evaluated_depsgraph_get()
    rot = cam.matrix_world.to_3x3()
    inv = rot.inverted()
    pts = [inv @ p for p in extra_points]
    for obj in objs:
        oe = obj.evaluated_get(dg)
        me = oe.to_mesh()
        mw = oe.matrix_world
        pts.extend(inv @ (mw @ v.co) for v in me.vertices)
        oe.to_mesh_clear()
    if not pts:
        raise RuntimeError("nothing to frame - evaluated geometry is empty")
    lo = Vector([min(p[i] for p in pts) for i in range(3)])
    hi = Vector([max(p[i] for p in pts) for i in range(3)])
    mid = (lo + hi) * 0.5
    # Fit into the band between the top bar and the bottom label, then centre
    # the subject in that band.
    avail = 1.0 - BAR_SAFE - LABEL_SAFE
    scale = max(hi.x - lo.x, (hi.y - lo.y) / avail, 1e-4) * margin
    cam.data.ortho_scale = scale
    cam.location = rot @ Vector((mid.x, mid.y - BAND_CENTRE * scale,
                                 hi.z + scale * 4.0))
    return scale, rot @ mid


def _alpha_centroid(path):
    """Alpha-weighted centroid of a rendered PNG, in NDC (0,0 = tile centre)."""
    img = bpy.data.images.load(path)
    w, h = img.size
    buf = array('f', [0.0]) * (w * h * 4)
    img.pixels.foreach_get(buf)
    bpy.data.images.remove(img)
    total = sx = sy = 0.0
    for j in range(h):
        base = j * w * 4
        fy = (j + 0.5) / h - 0.5
        for i in range(w):
            a = buf[base + i * 4 + 3]
            if a <= 0.0:
                continue
            total += a
            sx += a * ((i + 0.5) / w - 0.5)
            sy += a * fy
    if total <= 0.0:
        return None
    return sx / total, sy / total


def recentre_camera(cam, scale, tmp_dir):
    """Slide the camera so the rendered PIXELS are centred, not the bbox.

    Suzanne's mass is nowhere near the middle of her bounding box - the ears
    and snout push the box out much further than they push the visible weight -
    so a bbox fit lands her consistently off to one side. Rendering once with
    no frame overlay and measuring the alpha centroid is the only reliable way
    to find the optical centre; the label is not built yet, so it cannot skew
    the measurement.
    """
    sc = bpy.context.scene
    keep = sc.compositing_node_group
    sc.compositing_node_group = None
    probe = os.path.join(tmp_dir, "_centre_probe")
    render_to(probe)
    sc.compositing_node_group = keep

    found = _alpha_centroid(probe + ".png")
    try:
        os.remove(probe + ".png")
    except OSError:
        pass
    if found is None:
        return
    cx, cy = found
    rot = cam.matrix_world.to_3x3()
    cam.location = cam.location + rot @ Vector(
        (cx * scale, (cy - BAND_CENTRE) * scale, 0.0))


def setup_compositor(frame_path):
    """Alpha-over the catalog frame on the render.

    Blender 5 dropped Scene.node_tree and the Composite node: the compositor is
    a CompositorNodeTree assigned to scene.compositing_node_group, terminated
    by a Group Output.
    """
    sc = bpy.context.scene
    nt = bpy.data.node_groups.new("IconComp", "CompositorNodeTree")
    nt.interface.new_socket("Image", in_out='OUTPUT',
                            socket_type='NodeSocketColor')
    subject = nt.nodes.new("CompositorNodeRLayers")
    subject.scene = sc
    subject.layer = SUBJECT_LAYER
    img = nt.nodes.new("CompositorNodeImage")
    image = bpy.data.images.load(frame_path, check_existing=True)
    image.alpha_mode = 'STRAIGHT'
    img.image = image

    framed = nt.nodes.new("CompositorNodeAlphaOver")
    framed.inputs["Straight Alpha"].default_value = True
    nt.links.new(subject.outputs["Image"], framed.inputs["Background"])
    nt.links.new(img.outputs["Image"], framed.inputs["Foreground"])
    result = framed.outputs["Image"]

    # The name label rides above the frame, so the bottom gradient sits behind
    # it rather than washing over it.
    if sc.view_layers[LABEL_LAYER].use:
        label = nt.nodes.new("CompositorNodeRLayers")
        label.scene = sc
        label.layer = LABEL_LAYER
        topped = nt.nodes.new("CompositorNodeAlphaOver")
        topped.inputs["Straight Alpha"].default_value = True
        nt.links.new(result, topped.inputs["Background"])
        nt.links.new(label.outputs["Image"], topped.inputs["Foreground"])
        result = topped.outputs["Image"]

    out = nt.nodes.new("NodeGroupOutput")
    nt.links.new(result, out.inputs["Image"])
    sc.compositing_node_group = nt


def render_to(path):
    sc = bpy.context.scene
    sc.render.filepath = path
    bpy.ops.render.render(write_still=True)
