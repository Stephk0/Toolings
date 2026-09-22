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
JOBS = [(key, recipes.group_of(key), f)
        for key in sorted(recipes.RECIPES) for f in recipes.files_of(key)]
bad = 0
for key, g, f in JOBS:
    path = os.path.join(ROOT, f)
    # Purge every group first and use the datablock the load RETURNS. Looking
    # the group up by name finds a stale same-named copy left behind by an
    # earlier file (nested helpers survive a by-name remove), which reported
    # GN_GrowSelection as not-an-asset while it plainly was one.
    for old_ng in list(bpy.data.node_groups):
        try:
            bpy.data.node_groups.remove(old_ng)
        except Exception:
            pass
    # Cold read of the closed file, asset metadata only.
    with bpy.data.libraries.load(path, assets_only=True) as (df, dt):
        dt.node_groups = [n for n in df.node_groups if n == g]
    loaded = list(dt.node_groups)
    ng = loaded[0] if loaded else None
    if ng is None:
        print("FAIL %-30s not an asset in the file" % ("%s @ %s" % (g, os.path.basename(f))))
        bad += 1
        continue
    pv = ng.preview
    size = tuple(pv.image_size) if pv else (0, 0)
    px = list(pv.image_pixels_float[:4096]) if pv else []
    nonzero = sum(1 for v in px if v > 0.0)
    asset = ng.asset_data is not None
    ok = (size == (256, 256) and pv.is_image_custom and nonzero > 0 and asset)
    print("%s %-30s size=%s custom=%s asset=%s nonzero=%d" %
          ("ok  " if ok else "FAIL", "%s @ %s" % (g, os.path.basename(f)), size,
           pv.is_image_custom if pv else None, asset, nonzero))
    if not ok:
        bad += 1
print("=== %d/%d previews verified cold ===" % (len(JOBS) - bad, len(JOBS)))
sys.stdout.flush()
os._exit(1 if bad else 0)
