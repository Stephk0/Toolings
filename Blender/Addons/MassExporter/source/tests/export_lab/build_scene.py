"""Build the Export Lab scene: a stone, a plant and a tree set up for Mass Collection Exporter.

    blender --background --factory-startup --python build_scene.py -- <addon __init__.py> <out.blend> [preview.png]

Collections follow the exporter's conventions:

    Nature                      (exported parent collection)
      Stone                     SM_Stone, SM_Stone_COL            loose meshes, suffix pair
      Plant                     SM_Plant (empty) > Pot > Soil, Pot > Stem > Leaves, SM_Plant_COL
      Tree                      SM_Tree (empty) > Trunk > Canopy, SM_Tree_COL
      Extras                    SM_Pebble, collection hidden in the viewport
    Stage                       floor, camera, light rig (never exported)

Every asset sits away from the world origin, so Move to Center / Center Each Empty are visible
in the files. Each stack carries one viewport-disabled modifier to exercise Only Visible
Modifiers. Lighting is the geonode icon rig (Blender/Geonodes/_icons/stage.py): same three
area lights, colours, energy formula and camera angle, anchored on the line-up.
"""
import bpy
import bmesh
import importlib.util
import math
import os
import sys
from mathutils import Vector, Matrix

argv = sys.argv[sys.argv.index("--") + 1:]
ADDON, OUT_BLEND = argv[0], argv[1]
PREVIEW = argv[2] if len(argv) > 2 else None

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, *[".."] * 6))
sys.path.insert(0, os.path.join(REPO, "Blender", "Geonodes", "_icons"))
import stage  # noqa: E402  icon lighting constants

spec = importlib.util.spec_from_file_location("mass_collection_exporter", ADDON)
mx = importlib.util.module_from_spec(spec)
sys.modules["mass_collection_exporter"] = mx
spec.loader.exec_module(mx)
mx.register()


# --------------------------------------------------------------------------- helpers

def wipe():
    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o, do_unlink=True)
    for blocks in (bpy.data.meshes, bpy.data.materials, bpy.data.lights, bpy.data.cameras,
                   bpy.data.textures, bpy.data.collections, bpy.data.worlds):
        for b in list(blocks):
            blocks.remove(b)


def coll(name, parent=None):
    c = bpy.data.collections.new(name)
    (parent or bpy.context.scene.collection).children.link(c)
    return c


def mesh_obj(name, c, bm, mat=None, smooth=True):
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    if smooth:
        for p in me.polygons:
            p.use_smooth = True
    if mat:
        me.materials.append(mat)
    o = bpy.data.objects.new(name, me)
    c.objects.link(o)
    return o


def empty_obj(name, c, loc, rot_z=0.0, kind='PLAIN_AXES', size=0.3):
    o = bpy.data.objects.new(name, None)
    o.empty_display_type = kind
    o.empty_display_size = size
    o.location = loc
    o.rotation_euler.z = math.radians(rot_z)
    c.objects.link(o)
    return o


def parent_keep(child, par, local=(0, 0, 0)):
    """Parent with an identity inverse, so `local` is the position in the parent's space."""
    child.parent = par
    child.matrix_parent_inverse = Matrix.Identity(4)
    child.location = local


def hide_modifier(m):
    """Switched off in the viewport (and render, so renders match): Only Visible Modifiers must skip it."""
    m.show_viewport = False
    m.show_render = False


def collision(o):
    """Collision proxies: wireframe in the viewport, never rendered."""
    o.display_type = 'WIRE'
    o.hide_render = True


def cone(segments, r_bottom, r_top, depth, z0=0.0, cap=True):
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=cap, segments=segments, radius1=r_bottom,
                          radius2=r_top, depth=depth)
    bmesh.ops.translate(bm, verts=bm.verts, vec=(0, 0, z0 + depth / 2))
    return bm


def ico(subdiv, radius, centre=(0, 0, 0), scale=(1, 1, 1), bm=None):
    bm = bm or bmesh.new()
    new = bmesh.ops.create_icosphere(bm, subdivisions=subdiv, radius=radius)["verts"]
    bmesh.ops.scale(bm, verts=new, vec=scale)
    bmesh.ops.translate(bm, verts=new, vec=centre)
    return bm


def displace(o, name, tex, strength, mid=0.5, visible=True):
    m = o.modifiers.new(name, 'DISPLACE')
    m.texture = tex
    m.texture_coords = 'LOCAL'
    m.strength = strength
    m.mid_level = mid
    m.show_viewport = visible
    return m


def noise_tex(name, kind, size, depth=2):
    t = bpy.data.textures.new(name, kind)
    t.noise_scale = size
    if hasattr(t, "noise_depth"):
        t.noise_depth = depth
    return t


def material(name, colour, rough=0.6, bump=0.0, bump_scale=8.0, sheen=0.0):
    """Principled material. Base colour stays a plain value so FBX / OBJ / glTF carry it;
    the procedural bump only feeds Normal, which the exporters drop."""
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    bsdf = next(n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED')
    bsdf.inputs["Base Color"].default_value = colour + (1.0,)
    bsdf.inputs["Roughness"].default_value = rough
    m.diffuse_color = colour + (1.0,)
    if sheen and "Sheen Weight" in bsdf.inputs:
        bsdf.inputs["Sheen Weight"].default_value = sheen
    if bump:
        noise = nt.nodes.new('ShaderNodeTexNoise')
        noise.inputs["Scale"].default_value = bump_scale
        noise.inputs["Detail"].default_value = 6.0
        bmp = nt.nodes.new('ShaderNodeBump')
        bmp.inputs["Strength"].default_value = bump
        nt.links.new(noise.outputs["Fac"], bmp.inputs["Height"])
        nt.links.new(bmp.outputs["Normal"], bsdf.inputs["Normal"])
        noise.location = (-560, -260)
        bmp.location = (-300, -260)
    return m


# --------------------------------------------------------------------------- assets

def build_stone(c, mats):
    bm = ico(3, 0.42, scale=(1.25, 1.0, 0.72))
    stone = mesh_obj("SM_Stone", c, bm, mats["Stone_Rock"])
    stone.location = (-2.0, 0.15, 0.24)
    stone.rotation_euler.z = math.radians(20)
    displace(stone, "Displace Shape", noise_tex("TX_StoneShape", 'CLOUDS', 0.32), 0.42)
    displace(stone, "Displace Chips", noise_tex("TX_StoneChips", 'VORONOI', 0.12), 0.09)
    dec = stone.modifiers.new("Decimate (hidden)", 'DECIMATE')
    dec.ratio = 0.3
    hide_modifier(dec)

    col = mesh_obj("SM_Stone_COL", c, ico(1, 0.47, scale=(1.25, 1.0, 0.72)), smooth=False)
    col.location = stone.location
    col.rotation_euler = stone.rotation_euler
    collision(col)
    return stone


def leaf_blades(count=11, base_z=0.235, seed=3, scale=1.0):
    """One mesh of arching blades fanned around the stem."""
    import random
    rnd = random.Random(seed)
    bm = bmesh.new()
    segs = 8
    for i in range(count):
        a = (i / count) * math.tau + rnd.uniform(-0.25, 0.25)
        length = rnd.uniform(0.26, 0.38) * scale
        rise = rnd.uniform(0.95, 1.25)
        width = rnd.uniform(0.045, 0.06) * scale
        d = Vector((math.cos(a), math.sin(a), 0))
        side = Vector((-math.sin(a), math.cos(a), 0))
        rows = []
        for s in range(segs + 1):
            t = s / segs
            r = length * t
            h = length * rise * (0.95 * t - 0.85 * t * t)
            w = width * math.sin(math.pi * min(1.0, t ** 0.7 + 0.02))
            centre = d * r + Vector((0, 0, base_z * scale + h))
            rows.append([bm.verts.new(centre - side * w),
                         bm.verts.new(centre + Vector((0, 0, 0.006 * scale * (1 - t)))),
                         bm.verts.new(centre + side * w)])
        for s in range(segs):
            for k in range(2):
                bm.faces.new((rows[s][k], rows[s][k + 1], rows[s + 1][k + 1], rows[s + 1][k]))
    return bm


def build_plant(c, mats):
    root = empty_obj("SM_Plant", c, (-0.35, -0.1, 0.0), kind='PLAIN_AXES', size=0.25)
    k = 1.6     # plant scale, baked into the meshes so every transform stays clean

    bm = cone(20, 0.13 * k, 0.18 * k, 0.26 * k)
    top = max(bm.faces, key=lambda f: f.calc_center_median().z)
    bmesh.ops.delete(bm, geom=[top], context='FACES_ONLY')
    pot = mesh_obj("Pot", c, bm, mats["Plant_Pot"])
    parent_keep(pot, root)
    sol = pot.modifiers.new("Solidify", 'SOLIDIFY')
    sol.thickness = 0.014 * k
    bev = pot.modifiers.new("Bevel", 'BEVEL')
    bev.width = 0.004
    bev.segments = 2
    wn = pot.modifiers.new("Weighted Normal (hidden)", 'WEIGHTED_NORMAL')
    hide_modifier(wn)

    bm = bmesh.new()
    bmesh.ops.create_circle(bm, cap_ends=True, segments=20, radius=0.165 * k)
    bmesh.ops.translate(bm, verts=bm.verts, vec=(0, 0, 0.225 * k))
    soil = mesh_obj("Soil", c, bm, mats["Plant_Soil"], smooth=False)
    parent_keep(soil, pot)

    stem = mesh_obj("Stem", c, cone(6, 0.014 * k, 0.007 * k, 0.12 * k, z0=0.22 * k), mats["Plant_Leaf"])
    parent_keep(stem, pot)

    leaves = mesh_obj("Leaves", c, leaf_blades(scale=k), mats["Plant_Leaf"])
    parent_keep(leaves, stem)
    sub = leaves.modifiers.new("Subdivision", 'SUBSURF')
    sub.levels = sub.render_levels = 1
    sol = leaves.modifiers.new("Solidify", 'SOLIDIFY')
    sol.thickness = 0.003

    col = mesh_obj("SM_Plant_COL", c, cone(8, 0.2 * k, 0.24 * k, 0.52 * k), smooth=False)
    parent_keep(col, root)
    collision(col)
    return root


def build_tree(c, mats):
    root = empty_obj("SM_Tree", c, (1.7, 0.3, 0.0), rot_z=15, kind='ARROWS', size=0.4)

    bm = cone(12, 0.12, 0.055, 1.25)
    for v in bm.verts:              # flare the root ring, lean the top
        if v.co.z < 0.01:
            v.co.x *= 1.35
            v.co.y *= 1.35
        v.co.x += 0.06 * (v.co.z / 1.25) ** 2
    trunk = mesh_obj("Trunk", c, bm, mats["Tree_Bark"])
    parent_keep(trunk, root)
    sub = trunk.modifiers.new("Subdivision (hidden)", 'SUBSURF')
    sub.levels = 1
    hide_modifier(sub)

    bm = ico(2, 0.55, centre=(0.05, 0, 1.55))
    ico(2, 0.42, centre=(0.42, 0.12, 1.32), bm=bm)
    ico(2, 0.44, centre=(-0.32, -0.14, 1.36), bm=bm)
    ico(2, 0.36, centre=(0.0, 0.3, 1.9), bm=bm)
    canopy = mesh_obj("Canopy", c, bm, mats["Tree_Leaves"])
    parent_keep(canopy, trunk)
    displace(canopy, "Displace Clumps", noise_tex("TX_CanopyClumps", 'CLOUDS', 0.22), 0.38)

    bm = cone(8, 0.14, 0.1, 1.0)
    ico(1, 0.78, centre=(0.05, 0, 1.55), bm=bm)
    col = mesh_obj("SM_Tree_COL", c, bm, smooth=False)
    parent_keep(col, root)
    collision(col)
    return root


def build_extras(c, mats):
    peb = mesh_obj("SM_Pebble", c, ico(2, 0.09, scale=(1.3, 1.0, 0.6)), mats["Stone_Rock"])
    peb.location = (-1.35, 0.55, 0.05)
    displace(peb, "Displace Shape", bpy.data.textures["TX_StoneShape"], 0.04)
    return peb


# --------------------------------------------------------------------------- stage

def build_stage(c, centre, scale):
    sc = bpy.context.scene
    floor_mat = material("Stage_Floor", (0.30, 0.31, 0.33), rough=0.9)
    bm = bmesh.new()
    bmesh.ops.create_circle(bm, cap_ends=True, segments=64, radius=9.0)
    floor = mesh_obj("Stage_Floor", c, bm, floor_mat, smooth=False)
    floor.hide_select = True

    world = bpy.data.worlds.new("ExportLabWorld")
    world.use_nodes = True
    sc.world = world
    bg = next(n for n in world.node_tree.nodes if n.type == 'BACKGROUND')
    bg.inputs["Color"].default_value = (0.05, 0.05, 0.055, 1.0)
    bg.inputs["Strength"].default_value = 0.6

    # The icon rig, anchored on the line-up and rotated like the camera (stage.refit_lights)
    rig = bpy.data.objects.new("LightRig", None)
    c.objects.link(rig)
    rig.location = centre
    rig.rotation_euler = stage.CAM_ROT
    for name, loc, mult, size, colour in stage.LIGHT_SPECS:
        light = bpy.data.lights.new("L" + name, 'AREA')
        light.color = colour
        light.size = size * scale
        light.energy = stage.LIGHT_ENERGY * mult * scale * scale
        obj = bpy.data.objects.new("L" + name, light)
        c.objects.link(obj)
        obj.parent = rig
        obj.location = tuple(v * scale for v in loc)
        con = obj.constraints.new('TRACK_TO')
        con.target = rig
        con.track_axis = 'TRACK_NEGATIVE_Z'
        con.up_axis = 'UP_Y'

    cam_data = bpy.data.cameras.new("LabCam")
    cam_data.lens = 50
    cam = bpy.data.objects.new("LabCam", cam_data)
    c.objects.link(cam)
    cam.rotation_euler = stage.CAM_ROT
    back = cam.rotation_euler.to_matrix() @ Vector((0, 0, 1))
    cam.location = Vector(centre) + back * 8.4
    sc.camera = cam

    sc.view_settings.view_transform = 'Standard'
    sc.view_settings.look = 'None'
    sc.render.resolution_x, sc.render.resolution_y = 1920, 1080
    for engine in ('BLENDER_EEVEE', 'BLENDER_EEVEE_NEXT'):
        try:
            sc.render.engine = engine
            break
        except TypeError:
            continue
    return cam


# --------------------------------------------------------------------------- exporter setup

def configure_exporter(nature, assets, export_root):
    """The house setup: one row per asset, each into its own folder, grouped by suffix so the
    collision proxy ships in the same file. The parent `Nature` row is added but switched off."""
    p = bpy.context.scene.mass_exporter_props
    p.collection_items.clear()
    p.suffix_items.clear()
    for suffix, desc, on in (("_COL", "Collision", True), ("_LOD1", "LOD Level 1", True)):
        s = p.suffix_items.add()
        s.suffix, s.description, s.enabled = suffix, desc, on
    p.export_format = 'FBX'
    p.apply_modifiers = True
    p.apply_only_visible_modifiers = True
    row = p.collection_items.add()
    row.collection = nature
    row.export_path = os.path.join(export_root, "Nature") + os.sep
    row.export_enabled = False
    row.export_subcollections_as_single = True
    for c in assets:
        row = p.collection_items.add()
        row.collection = c
        row.export_enabled = True
        row.use_suffix_grouping = True
        row.export_path = os.path.join(export_root, c.name) + os.sep


# --------------------------------------------------------------------------- main

wipe()
sc = bpy.context.scene
sc.name = "ExportLab"
mats = {
    "Stone_Rock": material("Stone_Rock", (0.36, 0.33, 0.30), rough=0.85, bump=0.35, bump_scale=14),
    "Plant_Pot": material("Plant_Pot", (0.62, 0.30, 0.18), rough=0.7, bump=0.08, bump_scale=40),
    "Plant_Soil": material("Plant_Soil", (0.12, 0.08, 0.05), rough=1.0, bump=0.5, bump_scale=60),
    "Plant_Leaf": material("Plant_Leaf", (0.16, 0.42, 0.13), rough=0.45, sheen=0.3),
    "Tree_Bark": material("Tree_Bark", (0.24, 0.16, 0.10), rough=0.9, bump=0.6, bump_scale=22),
    "Tree_Leaves": material("Tree_Leaves", (0.20, 0.45, 0.15), rough=0.6, bump=0.3, bump_scale=9),
}
nature = coll("Nature")
c_stone, c_plant, c_tree = coll("Stone", nature), coll("Plant", nature), coll("Tree", nature)
c_extras = coll("Extras", nature)
c_stage = coll("Stage")

build_stone(c_stone, mats)
build_plant(c_plant, mats)
build_tree(c_tree, mats)
build_extras(c_extras, mats)
build_stage(c_stage, centre=(0.0, 0.15, 0.85), scale=4.0)

lc = bpy.context.view_layer.layer_collection.children["Nature"].children["Extras"]
lc.hide_viewport = True     # outliner eye off: the hidden-collection test case

blend_dir = os.path.dirname(os.path.abspath(OUT_BLEND))
configure_exporter(nature, (c_stone, c_plant, c_tree), os.path.join(blend_dir, "Exports"))
bpy.context.view_layer.update()

os.makedirs(blend_dir, exist_ok=True)
bpy.ops.wm.save_as_mainfile(filepath=os.path.abspath(OUT_BLEND), compress=True)
print("saved", OUT_BLEND)

if PREVIEW:
    # Cycles CPU, as the icon builder does: headless EEVEE is unreliable on this driver
    sc.render.engine = 'CYCLES'
    sc.cycles.device = 'CPU'
    sc.cycles.samples = 64
    sc.cycles.use_denoising = True
    sc.render.resolution_percentage = 50
    sc.render.filepath = os.path.abspath(PREVIEW)
    bpy.ops.render.render(write_still=True)
    print("preview", PREVIEW)
