import bpy, sys, os, math
OUT = r"C:\Users\Stephko\AppData\Local\Temp\claude\D--Stephko-Tooling-Toolings-Blender-Addons-ClaudeVibe-WIPs\f037431e-6231-45fb-bd85-0bb41b919d72\scratchpad"
obj = bpy.data.objects["GN_Demo"]; md = obj.modifiers[0]
ng = bpy.data.node_groups["GN_Mosaic"]
ID = {it.name: it.identifier for it in ng.interface.items_tree if hasattr(it, "identifier")}
def setv(n, v): md[ID[n]] = v

mat = bpy.data.materials.new("MosaicDebug"); mat.use_nodes = True
nt = mat.node_tree; nt.nodes.clear()
a = nt.nodes.new("ShaderNodeAttribute"); a.attribute_name = "tile_color"
e = nt.nodes.new("ShaderNodeEmission")
o = nt.nodes.new("ShaderNodeOutputMaterial")
nt.links.new(a.outputs["Color"], e.inputs["Color"])
nt.links.new(e.outputs["Emission"], o.inputs["Surface"])
setv("Material", mat)  # tiles are GN-generated: assign via the modifier

cam_d = bpy.data.cameras.new("C"); cam_d.type = 'ORTHO'; cam_d.ortho_scale = 8.4
cam = bpy.data.objects.new("C", cam_d); bpy.context.scene.collection.objects.link(cam)
cam.location = (0, 0, 10); cam.rotation_euler = (0, 0, 0)
sc = bpy.context.scene
sc.camera = cam
sc.render.engine = 'CYCLES'; sc.cycles.samples = 8; sc.cycles.device = 'CPU'
sc.render.resolution_x, sc.render.resolution_y = 1400, 700
sc.render.film_transparent = False
sc.view_settings.view_transform = "Standard"
sc.world.node_tree.nodes["Background"].inputs[0].default_value = (0.02, 0.02, 0.03, 1)

def shot(name, **kw):
    for k, v in kw.items(): setv(k, v)
    obj.update_tag()
    sc.render.filepath = os.path.join(OUT, name)
    bpy.ops.render.render(write_still=True)
    print("RENDERED", name)

shot("mosaic_default.png")
shot("mosaic_contour.png", **{"Contour Rows": 3, "Triangle Ratio": 0.45,
                              "Tile Size": 0.13, "Gap": 0.022, "Irregularity": 0.35})
shot("mosaic_cut.png", **{"Contour Rows": 2, "Fit Mode": 2, "Fit Tiles To Boundary": True,
                          "Triangle Ratio": 0.25, "Tile Size": 0.13, "Gap": 0.022,
                          "Irregularity": 0.2})
sys.stdout.flush(); os._exit(0)
