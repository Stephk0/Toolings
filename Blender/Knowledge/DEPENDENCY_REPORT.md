# Geonodes External Dependency Report

> Reference audit of every `.blend` in `Blender/Geonodes/` for external dependencies
> (linked libraries, images/textures, fonts, sounds, cache files).
>
> **Scan date:** 2026-07-17
> **Method:** Headless Blender 5.0 (`--background --factory-startup`), opened each file and
> inspected `bpy.data.libraries`, `bpy.data.images`, etc.
> **Files scanned:** 59

---

## 1. Clean — fully self-contained (no external dependencies)

GN_AutoSmooth, GN_Bend, GN_BoundingBox, GN_Cast, GN_ConvexHull, GN_Delete, GN_Displace,
GN_DualMesh, GN_Erosion, GN_Erosion_3D, GN_FlattenByBoundary, GN_FlipFaces, GN_Inflate,
GN_MeshBoolean, GN_Mirror_Groupable, GN_NormalTransfer, GN_PointsToSpheres, GN_RadialArray,
GN_RandomizePosition, GN_Scatter, GN_SetMaterial, GN_ShearGeometry, GN_SimpleTransform,
GN_Smooth, GN_Spherify, GN_Stretch, GN_Subdivide, GN_Taper, GN_Triangulate, GN_Twist,
GN_VoxelRemesh, GN_Wave, GN_Weld, GN_Wireframe, SHG_TileableNoise, GN_treeGenerator_03,
TreeGenDocu/GN_treeGenerator_02, TreeGenDocu/GN_treeGenerator_03

## 2. Internal cross-links only

Relative `//` links to sibling files in the same Geonodes folder. Portable as long as the
folder moves as a whole.

| File | Links to (same folder) |
|---|---|
| GN_AttributeFunctions_4.5 | GN_GrowSelection, SHG_TileableNoise |
| GN_ExtrudeSelection | GN_Delete, GN_GrowSelection |
| GN_FillBorder | GN_Delete |
| GN_GrowSelection | GN_InsetFace |
| GN_InsetFace | GN_Delete, GN_SplitByAttribute |
| GN_SplitByAttribute | GN_InsetFace |
| GN_NoiseDisplace | SHG_TileableNoise |
| GN_VoronoiDisplace | SHG_TileableNoise |
| GN_RandomDistribute | SHG_TileableNoise |

⚠️ Circular link chain: GN_GrowSelection ↔ GN_InsetFace ↔ GN_SplitByAttribute.

## 3. Truly external dependencies (machine-specific absolute paths)

### GN_EdgeDestruct / GN_EdgeDestruct_fixed
- `Character_Bakematerials.blend` — Dropbox\BlenderStartup\...\Character_BakeMaterials
- `preset.blend` — **bradley_geo_nodes_presets** extension (AppData, Blender 5.0 path)
- `geometry_nodes_essentials.blend` — Blender bundled assets (version-path specific)
- Internal: GN_CollectionInstancer, GN_SimpleTransform

### GN_CellFrac
- `Character_Bakematerials.blend` — Dropbox
- `geometry_nodes_essentials.blend` — Blender bundled (linked ×2)
- Internal: GN_EdgeDestruct_fixed

### GN_CollectionInstancer
- `geometry_nodes_essentials.blend` — Blender bundled

### GN_DisplaceByImage
- `geometry_nodes_essentials.blend` — Blender bundled (×3)
- Internal: GN_CollectionInstancer
- ❌ **4 MISSING textures** from `Work_DistrictGames\Project Ares`:
  - Black_Sand_Normal.tif
  - Cliff_Mossy_A_Normal.tif
  - Pebbles_C_Normal.tif
  - Rock_Normal.tif

### GN_MeshFromImage
- `Blender 4.3Higgsas Geo Node Groups v10.blend` — Dropbox asset library
- Image `bpk-env-nature-default-trees.png` — WMH backpatcher Unity repo (exists, but outside this repo)
- One packed image (fine)
- Internal: GN_Delete

### GN_Solidify2
- `preset.blend` — bradley_geo_nodes_presets extension (AppData, Blender **4.5** path)

### GN_VariousTest
- `Blender 4.3Higgsas Geo Node Groups v10.blend` — Dropbox
- `preset.blend` — bradley_geo_nodes_presets extension (4.5 path)

### TreeGenDocu/GN_treeGenerator_04 & _05
- `Blender 4.3Higgsas Geo Node Groups v10.blend` — Dropbox

### TreeGenDocu/GN_treeGenerator_06 (heaviest offender)
- `Blender 4.3Higgsas Geo Node Groups v10.blend` — Dropbox
- `bend_modifier.blend` — Dropbox\BlenderStartup\...\Bend Mod
- `nd_asset_library.blend` — ND extension, AppData 4.5 (×2)
- `geometry_nodes_essentials.blend` — Blender bundled (×2)
- Internal (relative `//..\`): GN_AttributeFunctions_4.5, GN_GrowSelection, GN_SimpleTransform, SHG_TileableNoise
- ❌ **MISSING texture:** Bark_Color.tif (Work_DistrictGames\Project Ares)
- Image `GridBox_Default.png` — Work_DistrictGames (currently exists, outside repo)

## 4. Recurring external sources — summary

| # | Source | Location | Risk |
|---|---|---|---|
| 1 | Dropbox asset libraries (Character_Bakematerials, Higgsas v10, bend_modifier) | `C:\Users\Stephko\Dropbox\BlenderStartup\...` | Won't resolve on any other machine |
| 2 | bradley_geo_nodes_presets `preset.blend` | AppData extensions, split across 4.5/5.0 paths | User- and version-specific |
| 3 | ND extension `nd_asset_library.blend` | AppData extensions (4.5) | User- and version-specific |
| 4 | Blender bundled `geometry_nodes_essentials.blend` | `Program Files\Blender Foundation\Blender 5.0\...` | Ships with Blender, but linked via absolute versioned path — breaks on version upgrade |
| 5 | Work_DistrictGames / WMH project textures | Sibling project folders | Several already missing on disk |

## 5. Notes

- "Linked library present" means datablocks were linked from it — it may be a leftover
  (e.g. a demo-object material) rather than a dependency of the node group itself.
  Verify actual usage before distributing a file.
- Per the asset-publish checklist, standalone geonode .blends should be self-contained:
  localize (make local) or pack external references before shipping.
- Raw scan script: open each file headless and iterate `bpy.data.libraries`, `bpy.data.images`
  (source FILE/SEQUENCE/MOVIE/TILED, unpacked), fonts, sounds, movieclips, cache_files, volumes.
