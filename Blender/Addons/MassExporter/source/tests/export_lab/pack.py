"""Pack a run folder for hosts that serve only web types (e.g. a claude.ai artifact).

    python pack.py <out_dir> <pub_dir>

Copies the page, scripts, scene.json and the preview into <pub_dir>, and stores every file in
blobs/ as base64 inside a few packs/pack-<n>.json files. manifest.json gains "packed":
{blob name: pack id}, which tells the page to read files from the packs. cases/ is left out.
"""
import base64
import json
import os
import shutil
import sys

OUT, PUB = sys.argv[1], sys.argv[2]
PACK_BYTES = 3_000_000

shutil.rmtree(PUB, ignore_errors=True)
os.makedirs(os.path.join(PUB, "packs"))
for name in os.listdir(OUT):
    if os.path.isfile(os.path.join(OUT, name)) and name != "manifest.json":
        shutil.copy2(os.path.join(OUT, name), PUB)

packed, pack, size, n = {}, {}, 0, 0


def flush():
    global pack, size, n
    if pack:
        json.dump(pack, open(os.path.join(PUB, "packs", f"pack-{n}.json"), "w"))
        n += 1
    pack, size = {}, 0


blob_dir = os.path.join(OUT, "blobs")
for name in sorted(os.listdir(blob_dir)):
    data = open(os.path.join(blob_dir, name), "rb").read()
    if size + len(data) > PACK_BYTES:
        flush()
    pack[name] = base64.b64encode(data).decode()
    packed[name] = n
    size += len(data)
flush()

manifest = json.load(open(os.path.join(OUT, "manifest.json")))
manifest["packed"] = packed
json.dump(manifest, open(os.path.join(PUB, "manifest.json"), "w"), separators=(",", ":"))
print(f"{len(packed)} files in {n} packs -> {PUB}")
