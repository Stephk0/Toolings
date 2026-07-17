# Geonode Publishing-Criteria Audit

Headless scan of all 52 `GN_*.blend` in `D:\Stephko_Tooling\Toolings\Blender\Geonodes`
against `GEONODE_CRITERIA.md` ## Publishing (Blender 5.0, `--factory-startup`).
Checks: asset-marked, catalog `f9ab2fa9…`, `ST3E` tag, `is_modifier=True`,
demo object attached, self-contained.

**Result: 32 pass, 20 fail.**

## Hard failures — absolute-path / third-party library links

| File | Main tree | Missing | External libs |
|---|---|---|---|
| GN_CellFrac.blend | GN_CellFrac | asset mark, catalog, tag, libs | Character_Bakematerials, geometry_nodes_essentials |
| GN_CollectionInstancer.blend | GN_CollectionInstancerModel | libs | geometry_nodes_essentials |
| GN_DisplaceByImage.blend | (foreign tree: GN_CollectionInstancerModel) | libs | geometry_nodes_essentials, //GN_CollectionInstancer |
| GN_EdgeDestruct.blend | (foreign tree: GN_CellFrac) | asset mark, catalog, tag, libs | Character_Bakematerials, essentials, bradley preset |
| GN_EdgeDestruct_fixed.blend | (foreign tree: GN_CellFrac) | asset mark, catalog, tag, libs | same as GN_EdgeDestruct |
| GN_MeshFromImage.blend | (foreign tree: GN_InsetFaces) | catalog, tag, libs | Higgsas Geo Node Groups v10 |
| GN_Solidify2.blend | GN_Solidfy2 (typo) | catalog, tag, libs | bradley preset (4.5) |
| GN_VariousTest.blend | GN_AttributeTransferLegacy | catalog, tag, libs | Higgsas, bradley preset |

## Metadata-only failures (self-contained)

| File | Main tree | Missing |
|---|---|---|
| GN_Erosion_3D.blend | GN_Erosion_3D | asset mark, catalog, tag |
| GN_Mirror_Groupable.blend | GN_Mirror | asset mark, catalog, tag, is_modifier, demo object |
| GN_treeGenerator_03.blend | TreeGen_Simple.002 | asset mark, catalog, tag, is_modifier |

(GN_Mirror_Groupable and GN_treeGenerator_03 may be intentionally non-modifier /
WIP; confirm before "fixing".)

## Soft failures — relative sibling links only (`//GN_*.blend`, `//SHG_TileableNoise.blend`)

Criteria bans *absolute-path* libraries; these link relatively within the library
folder. Decide whether to localize or accept:

- GN_AttributeFunctions_4.5.blend → //GN_GrowSelection, //SHG_TileableNoise
- GN_ExtrudeSelection.blend → //GN_Delete, //GN_GrowSelection
- GN_FillBorder.blend → //GN_Delete (also missing asset mark, catalog, tag)
- GN_GrowSelection.blend → //GN_InsetFace (also missing catalog, tag)
- GN_InsetFace.blend → //GN_Delete, //GN_SplitByAttribute (also missing catalog, tag)
- GN_NoiseDisplace.blend → //SHG_TileableNoise
- GN_RandomDistribute.blend → //SHG_TileableNoise
- GN_SplitByAttribute.blend → //GN_InsetFace
- GN_VoronoiDisplace.blend → //SHG_TileableNoise

## Notes

- "(foreign tree)" = no `GN_`-named tree of its own file name was found; the file's
  first geometry tree is a linked/imported one — likely needs its real tree renamed
  or the file rebuilt.
- Script: `%LOCALAPPDATA%\Temp\gn_publish_audit.py`; raw JSON lines in Git-Bash `/tmp/gn_audit_out.txt`.
