"""Put the GNG_* helper groups on the ST3E/Group catalog.

    blender --background --factory-startup --python recatalog_groups.py [-- --dry-run]

GNG_* groups are asset-marked for reuse in the node editor, not as modifiers.
They belong in their own catalog rather than scattered through Deform/Generate/
Modify, and they must not carry `is_modifier` — that lists them in the Add
Modifier menu, where they are clutter at best and (with a non-Geometry first
input) broken at worst.

Asset metadata only: no graph edits. Evaluated geometry is snapshotted per file
and the save is gated on it being unchanged.
"""
import bpy
import os
import sys

GEONODES = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GROUP_CATALOG = "5d2a7c14-9e3b-4f06-8c72-1b4e6a9d3f58"

# group -> the .blend that owns it. GN_VariousTest is a scratch file and is
# deliberately excluded, so GNG_MixValues (which lives only there) is too.
HOMES = {
    "GNG_AmbientOcclusion": "GN_AmbientOcclusion.blend",
    "GNG_Mirror": "GN_Mirror_Groupable.blend",
    "GNG_MixAlpha": "GN_AttributeFunctions_4.5.blend",
    "GNG_MixRGBXYZValues": "GN_AttributeFunctions_4.5.blend",
    "GNG_SetAttributename": "GN_AttributeFunctions_4.5.blend",
    "GNG_StoreAttributeOnDomain": "GN_AttributeFunctions_4.5.blend",
    "GNG_TileableNoiseCoords": "SHG_TileableNoise.blend",
    "GNG_VertexChannel": "GN_VertexDataComposer.blend",
}


def snapshot():
    dg = bpy.context.evaluated_depsgraph_get()
    out = {}
    for obj in bpy.context.scene.objects:
        if obj.type != 'MESH':
            continue
        oe = obj.evaluated_get(dg)
        me = oe.to_mesh()
        out[obj.name] = (len(me.vertices), len(me.edges), len(me.polygons))
        oe.to_mesh_clear()
    return out


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    dry = "--dry-run" in argv

    by_file = {}
    for group, blend in HOMES.items():
        by_file.setdefault(blend, []).append(group)

    results = []
    for blend, groups in sorted(by_file.items()):
        path = os.path.join(GEONODES, blend)
        if not os.path.exists(path):
            results.append((blend, "-", False, "missing file"))
            continue
        bpy.ops.wm.open_mainfile(filepath=path)
        before = snapshot()
        dirty = False
        for group in groups:
            ng = bpy.data.node_groups.get(group)
            if ng is None:
                results.append((blend, group, False, "not in file"))
                continue
            if ng.asset_data is None:
                ng.asset_mark()
            was = ng.asset_data.catalog_id
            ng.asset_data.catalog_id = GROUP_CATALOG
            if not any(t.name == "ST3E" for t in ng.asset_data.tags):
                ng.asset_data.tags.new("ST3E")
            ng.is_modifier = False
            ng.is_tool = False
            dirty = True
            results.append((blend, group, True,
                            "catalog %s -> Group" % was[:8]))
        after = snapshot()
        if before != after:
            results.append((blend, "-", False, "ABORT: geometry changed"))
            continue
        if dirty and not dry:
            bpy.ops.wm.save_mainfile(filepath=path, compress=True)

    print("\n=== RECATALOG%s ===" % (" (DRY RUN)" if dry else ""))
    for blend, group, ok, msg in results:
        print("%s %-30s %-34s %s" % ("ok  " if ok else "FAIL", group, blend, msg))
    bad = [r for r in results if not r[2]]
    print("=== %d/%d ===" % (len(results) - len(bad), len(results)))
    sys.stdout.flush()
    return 1 if bad else 0


if __name__ == "__main__":
    code = main()
    os._exit(code)
