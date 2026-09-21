"""Generate the PNG frame overlays for the ST3E geonode icons.

One 256x256 RGBA frame per asset catalog: a chamfered-square ring (45 degree
straight corners, top-left left square) flush with the image border, plus a
filled top bar carrying "ST3E / <Category>" in monospace, a black vignette
with a soft circular hole, and a shadow cast inward by the frame edge.

Rendered rather than drawn pixel by pixel so the bar text is a real font.
An orthographic camera with ortho_scale 1.0 over a 256px frame makes one
Blender unit exactly 256 pixels, so every dimension below is stated in pixels
and converted once.

Run:  blender --background --factory-startup --python make_frames.py
"""
import bpy
import os
import sys

SIZE = 256
CHAMFER = 17.0       # px cut off each corner at 45 degrees
SQUARE_CORNERS = ("tl",)   # corners left square instead of chamfered
                           # (the bar's own corner, so it reads as a tab)
STROKE = 3.0         # px ring thickness
BAR_H = 29.4         # px height of the top bar (70% of the original 42)
TEXT_PAD = 11.0      # px clear space left of the bar text and right of the tile
TEXT_CAP = 12.075   # px target cap height, 70% of the original 17.25
TEXT_COLOUR = (0.97, 0.97, 0.97, 1.0)
SHADOW_PX = 1.0      # px dark line just inside the ring, so the frame reads
SHADOW_ALPHA = 0.5   # on any background
TEXT_SHADOW_PX = 2.0     # px DISTANCE of the bar text's drop shadow
VIGNETTE_PX = 128.0      # px width of the soft falloff band, measured
                         # inward from the corners toward the clear centre
VIGNETTE_ALPHA = 0.30    # peak opacity of the black vignette
SCRIM_PX = 88.0          # px height of the dark band behind the name label
SCRIM_ALPHA = 0.55       # its opacity at the bottom edge
INNER_SHADOW_PX = 18.0   # px depth of the shadow cast inward by the frame
INNER_SHADOW_ALPHA = 0.10

PX = 1.0 / SIZE
ROOT2 = 2.0 ** 0.5

MONO_CANDIDATES = (
    r"C:\Windows\Fonts\consola.ttf",
    r"C:\Windows\Fonts\cour.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
)

# Catalog tints (sRGB hex). Keys match the `catalog` field in recipes.py.
CATALOGS = {
    "Deform":   ("E8833A", "ST3E / Deform"),
    "Generate": ("4FA3D1", "ST3E / Generate"),
    "Modify":   ("7CB342", "ST3E / Modify"),
    "Scatter":  ("A46BD8", "ST3E / Scatter"),
    "Shading":  ("E0B93C", "ST3E / Shading"),
    "Group":    ("5E7C8A", "ST3E / Group"),
    "Neutral":  ("9AA0A6", "ST3E"),
}


def srgb_to_linear(c):
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def hex_to_linear(h):
    return tuple(srgb_to_linear(int(h[i:i + 2], 16) / 255.0) for i in (0, 2, 4))


def frame_shape(half, chamfer, square=()):
    """Corner points of a chamfered square, counter-clockwise from bottom-left.

    Corners named in `square` keep their right angle instead of being cut at
    45 degrees. Inner and outer shapes must be built with the same `square`
    set so the two point lists stay the same length for ring_object().
    """
    h, c = half, chamfer
    pts = []
    pts.append((-h, -h) if "bl" in square else (-h + c, -h))
    if "br" in square:
        pts.append((h, -h))
    else:
        pts.extend([(h - c, -h), (h, -h + c)])
    if "tr" in square:
        pts.append((h, h))
    else:
        pts.extend([(h, h - c), (h - c, h)])
    if "tl" in square:
        pts.append((-h, h))
    else:
        pts.extend([(-h + c, h), (-h, h - c)])
    if "bl" not in square:
        pts.append((-h, -h + c))
    return pts


def emission_material(name, colour):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()
    em = nt.nodes.new("ShaderNodeEmission")
    em.inputs["Color"].default_value = (colour[0], colour[1], colour[2], 1.0)
    em.inputs["Strength"].default_value = 1.0
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    nt.links.new(em.outputs[0], out.inputs["Surface"])
    return mat


def shadow_material(name, alpha):
    """Half-transparent black - EEVEE needs BLENDED or it dithers at 256px."""
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    if hasattr(mat, "surface_render_method"):
        mat.surface_render_method = 'BLENDED'
    nt = mat.node_tree
    nt.nodes.clear()
    em = nt.nodes.new("ShaderNodeEmission")
    em.inputs["Color"].default_value = (0.0, 0.0, 0.0, 1.0)
    trans = nt.nodes.new("ShaderNodeBsdfTransparent")
    mix = nt.nodes.new("ShaderNodeMixShader")
    mix.inputs["Fac"].default_value = alpha
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    nt.links.new(trans.outputs[0], mix.inputs[1])
    nt.links.new(em.outputs[0], mix.inputs[2])
    nt.links.new(mix.outputs[0], out.inputs["Surface"])
    return mat


def poly_object(name, points, mat, z=0.0, location=None):
    """Build a flat n-gon from 2D points."""
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata([(x, y, z) for x, y in points], [], [list(range(len(points)))])
    mesh.update()
    mesh.materials.append(mat)
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.scene.collection.objects.link(obj)
    if location is not None:
        obj.location = location
    return obj


def vignette_material(name, half_x, half_y, feather, alpha):
    """Black overlay with a soft circular hole in the middle.

    Alpha is a single smoothstep on the RADIUS from the centre, so the clear
    area is one round hole. Multiplying separate per-axis falloffs instead
    gives four discrete corner blobs, which is not a vignette.

    The band runs from the corner radius inward by `feather`; the mesh carries
    its geometry at z=0 with the depth offset on the object, so the object
    coordinates this reads are purely 2D.
    """
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()
    coord = nt.nodes.new("ShaderNodeTexCoord")
    length = nt.nodes.new("ShaderNodeVectorMath")
    length.operation = 'LENGTH'
    nt.links.new(coord.outputs["Object"], length.inputs[0])

    outer = (half_x * half_x + half_y * half_y) ** 0.5
    ramp = nt.nodes.new("ShaderNodeMapRange")
    ramp.interpolation_type = 'SMOOTHSTEP'
    ramp.clamp = True
    ramp.inputs["From Min"].default_value = max(outer - feather, 0.0)
    ramp.inputs["From Max"].default_value = outer
    ramp.inputs["To Min"].default_value = 0.0
    ramp.inputs["To Max"].default_value = alpha
    nt.links.new(length.outputs["Value"], ramp.inputs["Value"])

    black = nt.nodes.new("ShaderNodeEmission")
    black.inputs["Color"].default_value = (0.0, 0.0, 0.0, 1.0)
    trans = nt.nodes.new("ShaderNodeBsdfTransparent")
    mix = nt.nodes.new("ShaderNodeMixShader")
    nt.links.new(ramp.outputs["Result"], mix.inputs["Fac"])
    nt.links.new(trans.outputs[0], mix.inputs[1])
    nt.links.new(black.outputs[0], mix.inputs[2])
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    nt.links.new(mix.outputs[0], out.inputs["Surface"])
    return mat


def scrim_material(name, half_y, height, alpha):
    """Dark band rising from the bottom edge, so the white name label reads.

    The radial vignette is weakest exactly where the label sits - horizontally
    centred, near the bottom - so the label needs its own gradient rather than
    a stronger vignette.
    """
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()
    coord = nt.nodes.new("ShaderNodeTexCoord")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    nt.links.new(coord.outputs["Object"], sep.inputs["Vector"])
    up = nt.nodes.new("ShaderNodeMath")
    up.operation = 'ADD'
    up.inputs[1].default_value = half_y
    nt.links.new(sep.outputs["Y"], up.inputs[0])

    ramp = nt.nodes.new("ShaderNodeMapRange")
    ramp.interpolation_type = 'SMOOTHSTEP'
    ramp.clamp = True
    ramp.inputs["From Min"].default_value = 0.0
    ramp.inputs["From Max"].default_value = height
    ramp.inputs["To Min"].default_value = alpha
    ramp.inputs["To Max"].default_value = 0.0
    nt.links.new(up.outputs[0], ramp.inputs["Value"])

    black = nt.nodes.new("ShaderNodeEmission")
    black.inputs["Color"].default_value = (0.0, 0.0, 0.0, 1.0)
    trans = nt.nodes.new("ShaderNodeBsdfTransparent")
    mix = nt.nodes.new("ShaderNodeMixShader")
    nt.links.new(ramp.outputs["Result"], mix.inputs["Fac"])
    nt.links.new(trans.outputs[0], mix.inputs[1])
    nt.links.new(black.outputs[0], mix.inputs[2])
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    nt.links.new(mix.outputs[0], out.inputs["Surface"])
    return mat


def inner_shadow_material(name, half_x, half_y, chamfer_offset, depth, alpha):
    """Shadow cast inward by the frame edge, following the frame's outline.

    Alpha is driven by the distance to the nearest EDGE of the content polygon,
    taken as the minimum over its half-planes. Using only the two axis-aligned
    pairs gives a box-cornered shadow that ignores the 45 degree chamfers, so
    the bottom chamfer half-plane is folded in as a third term. It is shared by
    both bottom corners: mirrored about x, the two lines reduce to the same
    expression in |x|.
    """
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()
    coord = nt.nodes.new("ShaderNodeTexCoord")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    nt.links.new(coord.outputs["Object"], sep.inputs["Vector"])

    def math(op, a=None, b=None):
        n = nt.nodes.new("ShaderNodeMath")
        n.operation = op
        for slot, v in ((0, a), (1, b)):
            if v is None:
                continue
            if isinstance(v, (int, float)):
                n.inputs[slot].default_value = v
            else:
                nt.links.new(v, n.inputs[slot])
        return n.outputs[0]

    abs_x = math('ABSOLUTE', sep.outputs["X"])
    abs_y = math('ABSOLUTE', sep.outputs["Y"])
    d_x = math('SUBTRACT', half_x, abs_x)
    d_y = math('SUBTRACT', half_y, abs_y)
    # (chamfer_offset - |x| + y) / sqrt(2)
    d_c = math('MULTIPLY',
               math('ADD', math('SUBTRACT', chamfer_offset, abs_x),
                    sep.outputs["Y"]),
               1.0 / (2.0 ** 0.5))
    nearest = math('MINIMUM', math('MINIMUM', d_x, d_y), d_c)

    ramp = nt.nodes.new("ShaderNodeMapRange")
    ramp.interpolation_type = 'SMOOTHSTEP'
    ramp.clamp = True
    ramp.inputs["From Min"].default_value = 0.0
    ramp.inputs["From Max"].default_value = depth
    ramp.inputs["To Min"].default_value = alpha
    ramp.inputs["To Max"].default_value = 0.0
    nt.links.new(nearest, ramp.inputs["Value"])

    black = nt.nodes.new("ShaderNodeEmission")
    black.inputs["Color"].default_value = (0.0, 0.0, 0.0, 1.0)
    trans = nt.nodes.new("ShaderNodeBsdfTransparent")
    mix = nt.nodes.new("ShaderNodeMixShader")
    nt.links.new(ramp.outputs["Result"], mix.inputs["Fac"])
    nt.links.new(trans.outputs[0], mix.inputs[1])
    nt.links.new(black.outputs[0], mix.inputs[2])
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    nt.links.new(mix.outputs[0], out.inputs["Surface"])
    return mat


def ring_object(name, outer, inner, mat, z=0.0):
    """Build the ring between two matching-length convex polygons."""
    n = len(outer)
    verts = [(x, y, z) for x, y in outer] + [(x, y, z) for x, y in inner]
    faces = [[i, (i + 1) % n, n + (i + 1) % n, n + i] for i in range(n)]
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(verts, [], faces)
    mesh.update()
    mesh.materials.append(mat)
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.scene.collection.objects.link(obj)
    return obj


def load_mono_font():
    for path in MONO_CANDIDATES:
        if os.path.exists(path):
            return bpy.data.fonts.load(path)
    return bpy.data.fonts.load("<builtin>")


def cap_ratio(font):
    """Rendered height of a capital at em size 1.0.

    Sizing by the label's own bounding box instead would scale it by whatever
    ascenders and descenders the string happens to contain, so "ST3E / Modify"
    (descender on the y) would come out smaller than "ST3E / Generate".
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


def text_object(body, font, mat, left_x, max_width, centre_y, z=0.01,
                offset=(0.0, 0.0)):
    curve = bpy.data.curves.new("BarText", type='FONT')
    curve.body = body
    curve.font = font
    curve.align_x = 'LEFT'
    curve.align_y = 'CENTER'
    curve.size = TEXT_CAP * PX / cap_ratio(font)
    curve.materials.append(mat)
    obj = bpy.data.objects.new("BarText", curve)
    bpy.context.scene.collection.objects.link(obj)
    obj.location = (left_x + offset[0], centre_y + offset[1], z)
    bpy.context.view_layer.update()
    if obj.dimensions.x > max_width:
        obj.scale = [max_width / obj.dimensions.x] * 3
    return obj


def build_scene():
    for coll in (bpy.data.objects, bpy.data.meshes, bpy.data.materials,
                 bpy.data.curves, bpy.data.cameras):
        for item in list(coll):
            try:
                coll.remove(item)
            except Exception:
                pass
    sc = bpy.context.scene
    # Cycles, not EEVEE: EEVEE segfaults rendering a lightless scene in
    # --background, and everything in this scene is flat emission anyway.
    sc.render.engine = 'CYCLES'
    sc.cycles.device = 'CPU'
    # The overlays stack four transparent layers (vignette, scrim, inner
    # shadow, ring), and each one is a Mix Shader against a Transparent BSDF.
    # At low sample counts that stack dithers visibly across the gradients.
    sc.cycles.samples = 512
    sc.cycles.use_denoising = False
    sc.cycles.transparent_max_bounces = 16
    sc.render.resolution_x = sc.render.resolution_y = SIZE
    sc.render.resolution_percentage = 100
    sc.render.film_transparent = True
    sc.render.image_settings.file_format = 'PNG'
    sc.render.image_settings.color_mode = 'RGBA'
    sc.view_settings.view_transform = 'Standard'
    sc.view_settings.look = 'None'
    # A black world, not None: EEVEE crashes rendering a worldless scene in
    # background mode. Everything here is emission anyway.
    world = bpy.data.worlds.new("FrameWorld")
    world.use_nodes = True
    bg = next(n for n in world.node_tree.nodes if n.type == 'BACKGROUND')
    bg.inputs["Strength"].default_value = 0.0
    sc.world = world

    cam_data = bpy.data.cameras.new("FrameCam")
    cam_data.type = 'ORTHO'
    cam_data.ortho_scale = 1.0
    cam = bpy.data.objects.new("FrameCam", cam_data)
    sc.collection.objects.link(cam)
    cam.location = (0.0, 0.0, 5.0)
    cam.rotation_euler = (0.0, 0.0, 0.0)
    sc.camera = cam
    return cam


def build_frame(name, tint_hex, label, font, out_dir):
    for obj in list(bpy.data.objects):
        if obj.type != 'CAMERA':
            bpy.data.objects.remove(obj, do_unlink=True)

    colour = hex_to_linear(tint_hex)
    tint_mat = emission_material("Tint_" + name, colour)
    text_mat = emission_material("Text_" + name, TEXT_COLOUR[:3])

    sq = SQUARE_CORNERS
    half_o, cham_o = 0.5, CHAMFER * PX
    d = STROKE * PX
    half_i = half_o - d
    # Inset of a 45 degree edge by d moves its endpoints by d * (sqrt2 - 2)
    # relative to the shrunken bounding box.
    cham_i = cham_o + d * ROOT2 - 2.0 * d

    ring_object("Ring", frame_shape(half_o, cham_o, sq),
                frame_shape(half_i, cham_i, sq), tint_mat)

    # Drop shadow: a 1px dark line immediately inside the coloured ring, so the
    # frame edge stays readable against a light icon or a light UI background.
    sd = SHADOW_PX * PX
    half_s = half_i - sd
    cham_s = cham_i + sd * ROOT2 - 2.0 * sd
    ring_object("Shadow", frame_shape(half_i, cham_i, sq),
                frame_shape(half_s, cham_s, sq),
                shadow_material("Shadow_" + name, SHADOW_ALPHA), z=-0.005)

    # The bar is the inner shape clipped to everything above bar_bottom.
    bar_bottom = half_i - BAR_H * PX
    bar = [(-half_i, bar_bottom), (half_i, bar_bottom)]
    if "tr" in sq:
        bar.append((half_i, half_i))
    else:
        bar.extend([(half_i, half_i - cham_i), (half_i - cham_i, half_i)])
    if "tl" in sq:
        bar.append((-half_i, half_i))
    else:
        bar.extend([(-half_i + cham_i, half_i), (-half_i, half_i - cham_i)])
    poly_object("Bar", bar, tint_mat, z=-0.01)

    # Corner vignette over the content area only (inside the ring, below the
    # bar), so all four of ITS corners darken - anchoring it to the raw tile
    # would hide the top two behind the bar.
    content = [(-half_i + cham_i, -half_i), (half_i - cham_i, -half_i),
               (half_i, -half_i + cham_i), (half_i, bar_bottom),
               (-half_i, bar_bottom), (-half_i, -half_i + cham_i)]
    cy = (bar_bottom - half_i) * 0.5
    half_y = (bar_bottom + half_i) * 0.5
    centred = [(x, y - cy) for x, y in content]
    poly_object("Vignette", centred,
                vignette_material("Vignette_" + name, half_i, half_y,
                                  VIGNETTE_PX * PX, VIGNETTE_ALPHA),
                z=0.0, location=(0.0, cy, -0.02))
    poly_object("Scrim", centred,
                scrim_material("Scrim_" + name, half_y, SCRIM_PX * PX,
                               SCRIM_ALPHA),
                z=0.0, location=(0.0, cy, -0.018))
    poly_object("InnerShadow", centred,
                inner_shadow_material("InnerShadow_" + name, half_i, half_y,
                                      2.0 * half_i - cham_i + cy,
                                      INNER_SHADOW_PX * PX,
                                      INNER_SHADOW_ALPHA),
                z=0.0, location=(0.0, cy, -0.015))

    left_x = -half_i + TEXT_PAD * PX
    max_w = (half_i - TEXT_PAD * PX) - left_x
    centre_y = (half_i + bar_bottom) * 0.5
    # Drop shadow first, down-right and behind the text itself. It is a fully
    # opaque black emission copy rather than an alpha-mixed one, so it stays a
    # hard-edged duplicate of the glyphs - an embossed offset, not a blur.
    # Split across both axes so the diagonal distance is the stated one;
    # offsetting by the full amount on each axis is sqrt(2) too far.
    ts = TEXT_SHADOW_PX * PX / ROOT2
    text_object(label, font,
                emission_material("TextShadow_" + name, (0.0, 0.0, 0.0)),
                left_x=left_x, max_width=max_w, centre_y=centre_y,
                z=0.005, offset=(ts, -ts))
    text_object(label, font, text_mat, left_x=left_x, max_width=max_w,
                centre_y=centre_y)

    path = os.path.join(out_dir, "frame_%s.png" % name.lower())
    bpy.context.scene.render.filepath = path
    bpy.ops.render.render(write_still=True)
    print("FRAME", path)


def main():
    out_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "frames")
    os.makedirs(out_dir, exist_ok=True)
    build_scene()
    font = load_mono_font()
    print("FONT", font.filepath or font.name)
    for name, (tint, label) in CATALOGS.items():
        build_frame(name, tint, label, font, out_dir)
    sys.stdout.flush()


if __name__ == "__main__":
    main()
    os._exit(0)
