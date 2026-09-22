"""Which ST3E modifiers still need an icon.

    blender --background --factory-startup --python coverage.py

Sweeps every .blend in Blender/Geonodes for asset-marked node groups with
`is_modifier`, and reports for each whether it has a recipe, a rendered PNG and
an embedded preview. Run it before starting a batch to pick the next targets,
and after embedding to confirm nothing was missed.

Also flags groups that are `is_modifier` but sit on the null catalog - those
are legacy or helper groups that should not get an icon (and arguably should
not carry the trait at all).
"""
import bpy
import glob
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import recipes      # noqa: E402

GEONODES = os.path.dirname(HERE)
OUT = os.path.join(HERE, "out")

CATALOGS = {
    "f9ab2fa9-3a4e-491a-abaa-558cd5c029d0": "ST3E(root)",
    "bacd112a-8e87-47c2-afbc-818a11c75c08": "Deform",
    "8872522f-45b7-4541-a557-5b69bcbfcee2": "Generate",
    "9b90781b-f051-4cdb-9dcb-c8909914a87b": "Modify",
    "25b9ecc2-4cf7-41b3-83c3-152a2eccbc77": "Scatter",
    "3c7d5e91-2b64-4f8a-9d13-6a0e5f2c8b47": "Shading",
    "5d2a7c14-9e3b-4f06-8c72-1b4e6a9d3f58": "Group",
    "00000000-0000-0000-0000-000000000000": "(none)",
}


SHADING = os.path.join(os.path.dirname(GEONODES), "Shading")


def scan():
    rows = []
    paths = sorted(glob.glob(os.path.join(GEONODES, "*.blend")))
    paths += sorted(glob.glob(os.path.join(SHADING, "*.blend")))
    for path in paths:
        # Purge EVERY group between files. Nested helpers survive a by-name
        # remove (they are still used), so the next file's copy of the same
        # group arrives as "<name>.001" and a lookup by name returns the stale
        # one from the previous file - GNG_TileableNoiseCoords was reported
        # missing that way while perfectly asset-marked.
        for ng in list(bpy.data.node_groups):
            try:
                bpy.data.node_groups.remove(ng)
            except Exception:
                pass
        try:
            with bpy.data.libraries.load(path, assets_only=True) as (src, dst):
                names = list(src.node_groups)
                dst.node_groups = list(names)
            loaded = list(dst.node_groups)   # the actual datablocks, renamed or not
        except Exception as exc:
            rows.append({"file": os.path.basename(path), "error": str(exc)})
            continue
        for name, ng in zip(names, loaded):
            if ng is None or ng.bl_idname not in ("GeometryNodeTree",
                                                  "ShaderNodeTree"):
                continue
            ad = ng.asset_data
            cat_now = CATALOGS.get(ad.catalog_id, "") if ad else ""
            # Modifiers, the GNG_*/SHG_* helper groups (Group catalog) and the
            # SH_* shader groups on the Shading catalog.
            if ng.bl_idname == "ShaderNodeTree":
                if cat_now not in ("Shading", "Group"):
                    continue
            elif not getattr(ng, "is_modifier", False) and cat_now != "Group":
                continue
            cat = CATALOGS.get(ad.catalog_id, ad.catalog_id) if ad else None
            preview = bool(ng.preview and ng.preview.image_size[0] > 0
                           and ng.preview.is_image_custom)
            rows.append({"file": os.path.basename(path), "group": name,
                         "catalog": cat, "preview": preview,
                         "kind": "group" if cat == "Group" else "modifier",
                         "inputs": sum(1 for it in ng.interface.items_tree
                                       if it.item_type == 'SOCKET'
                                       and it.in_out == 'INPUT')})
    return rows


def main():
    rows = [r for r in scan() if "error" not in r]
    done = skip = todo = 0
    print("\n=== ICON COVERAGE ===")
    print("%-5s %-6s %-28s %-11s %5s  %s"
          % ("recipe", "png", "group", "catalog", "in", "file"))
    covered = recipes.covered()
    for r in sorted(rows, key=lambda x: ((x["catalog"] or "zz"), x["group"])):
        key = covered.get((r["group"], r["file"]))
        has_recipe = key is not None
        has_png = os.path.exists(os.path.join(OUT, (key or r["group"]) + ".png"))
        if r["catalog"] in (None, "(none)"):
            mark, note = "  -  ", "legacy/helper - no icon"
            skip += 1
        elif r["catalog"] not in CATALOGS.values():
            # A catalog UUID ST3E does not define: a foreign asset carried
            # along inside a file (ash_char_base_SSS holds one). Not ours.
            mark, note = "  -  ", "foreign catalog - not an ST3E asset"
            skip += 1
        elif has_recipe and r["preview"]:
            mark, note = " ok  ", ""
            done += 1
        else:
            mark, note = " TODO", ""
            todo += 1
        print("%-5s %-6s %-28s %-11s %5d  %s%s"
              % (mark,
                 "yes" if has_png else ("emb" if r["preview"] else "-"),
                 r["group"], r["catalog"], r["inputs"], r["file"],
                 ("   <- " + note) if note else ""))
    print("=== %d done, %d to do, %d skipped (null or foreign catalog) ===\n"
          % (done, todo, skip))

    present = {(r["group"], r["file"]) for r in rows}
    orphan = [k for pair, k in covered.items() if pair not in present]
    if orphan:
        print("RECIPES WITH NO MATCHING ASSET GROUP:", orphan)

    # A rendered PNG with no recipe is unambiguous: a recipe was lost. The
    # build still reports N/N in that case, so nothing else catches it.
    lost = [r["group"] for r in rows
            if (r["group"], r["file"]) not in covered
            and r["group"] not in {recipes.group_of(k) for k in recipes.RECIPES}
            and os.path.exists(os.path.join(OUT, r["group"] + ".png"))]
    if lost:
        print("!! RENDERED ICON BUT NO RECIPE - recipe lost:", lost)

    # Custom previews that predate this pipeline; harmless, replaced when the
    # recipe is written.
    stale = [r["group"] for r in rows
             if r["preview"] and (r["group"], r["file"]) not in covered
             and r["catalog"] not in (None, "(none)")
             and r["group"] not in lost]
    if stale:
        print("note: pre-existing previews, will be replaced:", stale)
    sys.stdout.flush()


if __name__ == "__main__":
    main()
    os._exit(0)
