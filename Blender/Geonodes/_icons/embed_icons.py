"""Stage B - write the rendered icons into each .blend as the asset preview.

    blender --background --factory-startup --python embed_icons.py -- [GROUP ...]
    blender --background --factory-startup --python embed_icons.py -- --dry-run

One Blender launch for the whole batch: the files are reopened in-process with
wm.open_mainfile, which is far cheaper than relaunching per file.

THIS WRITES TO THE SOURCE .blend FILES. It only touches ID previews - no node,
object or scene data is modified - but it does call save_mainfile, so the files
are rewritten by Blender 5. Run stage A first and eyeball out/*.png.
"""
import bpy
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import recipes      # noqa: E402

GEONODES = os.path.dirname(HERE)
OUT = os.path.join(HERE, "out")


def groups_by_file(wanted):
    """Bundle the requested groups per source .blend so each file opens once."""
    buckets = {}
    for key in wanted:
        if key not in recipes.RECIPES:
            continue
        png = os.path.join(OUT, key + ".png")
        if not os.path.exists(png):
            print("skip %s - no rendered icon at %s" % (key, png))
            continue
        for blend in recipes.files_of(key):
            buckets.setdefault(blend, []).append(
                (recipes.group_of(key), png, key))
    return buckets


def embed(blend_name, jobs, dry_run):
    path = os.path.join(GEONODES, blend_name)
    if not os.path.exists(path):
        return [{"file": blend_name, "ok": False, "msg": "missing file"}]
    bpy.ops.wm.open_mainfile(filepath=path)
    results = []
    dirty = False
    for group, png, key in jobs:
        ng = bpy.data.node_groups.get(group)
        if ng is None:
            results.append({"file": blend_name, "group": group, "ok": False,
                            "msg": "group not in file"})
            continue
        if ng.asset_data is None:
            results.append({"file": blend_name, "group": group, "ok": False,
                            "msg": "not marked as an asset"})
            continue
        with bpy.context.temp_override(id=ng):
            bpy.ops.ed.lib_id_load_custom_preview(filepath=png)
        size = tuple(ng.preview.image_size)
        ok = size[0] > 0 and ng.preview.is_image_custom
        dirty = dirty or ok
        results.append({"file": blend_name, "group": group, "ok": ok,
                        "msg": "preview %dx%d custom=%s"
                               % (size[0], size[1], ng.preview.is_image_custom)})
    if dirty and not dry_run:
        bpy.ops.wm.save_mainfile(filepath=path, compress=True)
    return results


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    dry_run = "--dry-run" in argv
    wanted = [a for a in argv if not a.startswith("--")] or sorted(recipes.RECIPES)

    results = []
    for blend_name, jobs in sorted(groups_by_file(wanted).items()):
        results.extend(embed(blend_name, jobs, dry_run))

    print("\n=== ICON EMBED%s ===" % (" (DRY RUN)" if dry_run else ""))
    for r in results:
        print("%s %-26s %-34s %s" % ("ok  " if r["ok"] else "FAIL",
                                     r.get("group", "-"), r["file"], r["msg"]))
    bad = [r for r in results if not r["ok"]]
    print("=== %d/%d embedded ===" % (len(results) - len(bad), len(results)))
    sys.stdout.flush()
    return 1 if bad else 0


if __name__ == "__main__":
    code = main()
    os._exit(code)
