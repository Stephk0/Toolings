"""Cold-verify every embedded preview.

    blender --background --factory-startup --python verify_embed.py

Reopens each CLOSED .blend with libraries.load(assets_only=True) and checks the
preview is 256x256, is_image_custom, still asset-marked and non-empty. Run this
after embed_icons.py - it is the only step that proves the previews actually
landed in the files rather than just in memory.

The group list comes from recipes.py, so it cannot drift.
"""
import bpy, sys, os

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
import recipes  # noqa: E402

ROOT = os.path.dirname(HERE)
GROUPS = sorted(recipes.RECIPES)
bad = 0
for g in GROUPS:
    rec = recipes.RECIPES[g]
    path = os.path.join(ROOT, rec.get("file", recipes.source_file(g)))
    # Cold read of the closed file, asset metadata only.
    with bpy.data.libraries.load(path, assets_only=True) as (df, dt):
        dt.node_groups = [n for n in df.node_groups if n == g]
    ng = bpy.data.node_groups.get(g)
    if ng is None:
        print("FAIL %-24s not an asset in the file" % g)
        bad += 1
        continue
    pv = ng.preview
    size = tuple(pv.image_size) if pv else (0, 0)
    px = list(pv.image_pixels_float[:4096]) if pv else []
    nonzero = sum(1 for v in px if v > 0.0)
    asset = ng.asset_data is not None
    ok = (size == (256, 256) and pv.is_image_custom and nonzero > 0 and asset)
    print("%s %-24s size=%s custom=%s asset=%s nonzero=%d" %
          ("ok  " if ok else "FAIL", g, size,
           pv.is_image_custom if pv else None, asset, nonzero))
    if not ok:
        bad += 1
    bpy.data.node_groups.remove(ng)
print("=== %d/%d previews verified cold ===" % (len(GROUPS) - bad, len(GROUPS)))
sys.stdout.flush()
os._exit(1 if bad else 0)
