"""Publish GN_Mosaic to the ST3E asset library -- metadata ONLY.

This deliberately does NOT rebuild the node graph: GN_Mosaic.blend has a tidied
layout and the user's own test objects in it, and re-running build_gn_mosaic.py
would throw both away. It opens the shipped file, fixes the asset metadata and
saves in place.

What it sets:
  * asset_mark            (idempotent -- already marked, kept)
  * catalog_id            ST3E/Generate, NOT the flat ST3E root. The 2026-07-20
                          reorg (commit 8f1e6b7) split the catalog into
                          Deform / Generate / Modify / Scatter & Instancing and
                          re-pointed every modifier; GN_Mosaic was authored after
                          that and was still on the now-empty parent.
  * tags                  "ST3E"  (the Add-Modifier menu / browser filter tag)
  * is_modifier = True    without this the group is invisible in Add Modifier
  * is_tool = False
  * asset_data.description   the browser tooltip

Run headless:
  "C:\\Program Files\\Blender Foundation\\Blender 5.0\\blender.exe" --background \
      --factory-startup GN_Mosaic.blend --python publish_gn_mosaic.py
"""
import bpy, sys, os

NAME = "GN_Mosaic"
PATH = bpy.data.filepath
CAT_GENERATE = "8872522f-45b7-4541-a557-5b69bcbfcee2"   # ST3E/Generate
TAG = "ST3E"

DESC = (
    "Fill the bounded areas of a mesh with mosaic tesserae. Edge loops -- a marked "
    "Boundary Edges field and/or the mesh's own open edges -- cut the surface into "
    "regions, and every region is packed with tiles that stop at its outline, however "
    "organic. Grid mode intersects a warped square/triangle lattice with the region "
    "(fit modes, edge margin, adaptive tile sizes near walls); Shatter mode instead "
    "partitions the region's own faces by recursive edge cutting for exact coverage "
    "with 3-6 sided tiles, and can be made seamlessly tileable across a bounds box. "
    "Contour Rows lay N rows of tiles following the outline (opus vermiculatum). "
    "Outputs a unique tile_id per tile plus region_id, tile_random and a tile_color "
    "corner attribute for shading."
)

ng = bpy.data.node_groups.get(NAME)
if ng is None:
    raise SystemExit("FATAL: no node group named %s in %s" % (NAME, PATH))

before = (len(ng.nodes), len(ng.interface.items_tree), len(bpy.data.objects))

# --------------------------------------------------------------------- asset traits
if ng.asset_data is None:
    ng.asset_mark()
ad = ng.asset_data
ad.catalog_id = CAT_GENERATE
if TAG not in [t.name for t in ad.tags]:
    ad.tags.new(TAG)
for t in [t for t in ad.tags if t.name != TAG]:      # normalise stray legacy tags
    print("  dropping stray tag:", t.name)
    ad.tags.remove(t)
ad.description = DESC
ng.is_modifier = True
ng.is_tool = False

# helper groups linked into this file must NOT show up in the Add-Modifier menu
for other in bpy.data.node_groups:
    if other is ng or other.library is not None:
        continue
    if other.asset_data and other.is_modifier:
        print("  NOTE: local helper group also flagged is_modifier:", other.name)

# --------------------------------------------------------- modifier-validity contract
items = [i for i in ng.interface.items_tree if i.item_type == 'SOCKET']
ins = [i for i in items if i.in_out == 'INPUT']
outs = [i for i in items if i.in_out == 'OUTPUT']
assert ins[0].socket_type == 'NodeSocketGeometry', "first input must be Geometry"
assert any(o.socket_type == 'NodeSocketGeometry' for o in outs), "need a Geometry output"
blank = [i.name for i in items if not (i.description or "").strip()]
assert not blank, "sockets missing a tooltip: %s" % blank

assert (len(ng.nodes), len(ng.interface.items_tree), len(bpy.data.objects)) == before, \
    "publish must not change the graph or the scene"

bpy.ops.wm.save_mainfile(filepath=PATH)
print("PUBLISHED %s | catalog=%s | tags=%s | is_modifier=%s | nodes=%d (unchanged)" % (
    NAME, ad.catalog_id, [t.name for t in ad.tags], ng.is_modifier, len(ng.nodes)))
sys.stdout.flush()
os._exit(0)
