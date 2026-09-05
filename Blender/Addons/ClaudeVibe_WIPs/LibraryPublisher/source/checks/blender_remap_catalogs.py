"""Rewrite asset catalog ids in STAGED .blend copies.

When the publisher remaps catalog UUIDs, the new ids only exist in the published
`blender_assets.cats.txt`. Assets key on the UUID, so every published .blend has
to carry the new id or its assets land in no catalog at all.

This runs once, headless, over the staging tree. It must never be pointed at the
repo: the batch file lists staged paths, and the publisher copies (rather than
hardlinks) any file this will touch, so the source is physically untouchable
from here.

    blender --background --factory-startup --python blender_remap_catalogs.py -- <batch.json>

batch.json: {"files": ["<staged .blend>", ...], "id_map": {"<old>": "<new>", ...}}
"""

import json
import os
import sys
import traceback

import bpy

JSON_BEGIN = "<<<ST3E_REMAP_JSON>>>"
JSON_END = "<<<ST3E_REMAP_END>>>"

ASSET_COLLECTIONS = (
    "node_groups",
    "objects",
    "materials",
    "collections",
    "worlds",
    "images",
    "actions",
    "brushes",
    "scenes",
)


def remap_open_file(id_map):
    """Rewrite catalog_id on every LOCAL asset. Returns (changed, untouched)."""
    changed = []
    untouched = []
    for coll_name in ASSET_COLLECTIONS:
        coll = getattr(bpy.data, coll_name, None)
        if coll is None:
            continue
        for datablock in coll:
            asset_data = getattr(datablock, "asset_data", None)
            if asset_data is None:
                continue
            # Linked datablocks belong to another file; rewriting them would
            # both fail to persist and misrepresent someone else's catalogs.
            if getattr(datablock, "library", None) is not None:
                continue
            old = (getattr(asset_data, "catalog_id", "") or "").strip()
            new = id_map.get(old)
            if not new:
                # Unassigned, or a catalog outside the published set. Leaving it
                # alone is correct: we only own the ids we published.
                untouched.append("%s/%s" % (coll_name, datablock.name))
                continue
            try:
                asset_data.catalog_id = new
                changed.append("%s/%s" % (coll_name, datablock.name))
            except Exception as exc:
                untouched.append("%s/%s (write failed: %s)" % (coll_name, datablock.name, exc))
    return changed, untouched


def main():
    argv = sys.argv
    if "--" not in argv:
        _emit({"results": [], "error": "no batch file argument"})
        return
    with open(argv[argv.index("--") + 1], "r", encoding="utf-8") as fh:
        batch = json.load(fh)

    id_map = batch.get("id_map") or {}
    results = []

    for path in batch.get("files") or []:
        entry = {"path": path}
        if not os.path.isfile(path):
            entry["error"] = "staged file missing"
            results.append(entry)
            continue
        try:
            bpy.ops.wm.open_mainfile(filepath=path, load_ui=False)
        except Exception as exc:
            entry["error"] = "open failed: %s" % exc
            results.append(entry)
            continue

        try:
            changed, untouched = remap_open_file(id_map)
            entry["changed"] = changed
            entry["untouched"] = untouched
            if changed:
                # Preserve the source file's compression: a plain save would
                # rewrite a zstd .blend uncompressed and inflate the drive.
                compress = _was_compressed(path)
                bpy.ops.wm.save_mainfile(filepath=path, compress=compress)
                entry["saved"] = True
                entry["compressed"] = compress
            else:
                entry["saved"] = False
        except Exception:
            entry["error"] = "remap failed: %s" % traceback.format_exc(limit=3)
        results.append(entry)

    _emit({"results": results, "id_map_size": len(id_map)})


def _was_compressed(path):
    """zstd-framed .blend files start with the zstd magic; plain ones say BLENDER."""
    try:
        with open(path, "rb") as fh:
            head = fh.read(4)
    except OSError:
        return True
    return head == b"\x28\xb5\x2f\xfd"


def _emit(payload):
    sys.stdout.write("\n" + JSON_BEGIN + "\n")
    sys.stdout.write(json.dumps(payload))
    sys.stdout.write("\n" + JSON_END + "\n")
    sys.stdout.flush()


if __name__ == "__main__":
    try:
        main()
    except Exception:
        _emit({"results": [], "error": traceback.format_exc(limit=5)})
    sys.stdout.flush()
    sys.stderr.flush()
    os._exit(0)
