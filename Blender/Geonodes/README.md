# ST3E Geometry Nodes Library

> Procedural Geometry Nodes assets for Blender 5.0+ — a library of **38 ST3E modifiers**
> plus supporting node groups, all available from the **Add Modifier → ST3E** quick-pick menu.

**Location:** `Blender/Geonodes/`
**Author:** Stephan Viranyi (Stephko)
**Target:** Blender 5.0+ (most also work on 4.5)

---

## 📥 Installation

These node groups are shipped as **Asset-Browser assets**, tagged `ST3E` and catalogued so
they appear directly in the modifier menu.

1. **Preferences → File Paths → Asset Libraries** → add a library pointing at the
   `Blender/` folder (the asset catalog `blender_assets.cats.txt` lives there).
2. Set the import method to **Link** (or Append, if you want a local copy).
3. In any object's modifier stack: **Add Modifier → ST3E** → pick a modifier.
   - The `ST3E` tag also lets you filter/group them in the Asset Browser.

Each `.blend` ships a **demo object** with the modifier already attached, so you can open the
file directly to inspect a working setup.

> **Note:** the modifier menu only lists groups that are asset-marked **and** have the
> *Modifier* asset trait enabled (`is_modifier = True`) **and** carry the `ST3E` tag. A few
> older library files (`GN_FillBorder`, `GN_MeshFromImage`, `GN_DisplaceByImage`,
> `GN_treeGenerator_*`) are not marked as modifiers and only appear in the Asset Browser.

---

## 🧱 Modifier Reference

### Deformers
Move existing vertices. Pivot-based deformers expose an editable **Center** + **Show Center
Gizmo** (3-axis arrow gizmo, overlay only) and a **Show Deformation Preview** cage toggle.

| Modifier | File | What it does | Key parameters |
|----------|------|--------------|----------------|
| **GN_Inflate** | `GN_Inflate.blend` | Push geometry along its normals | Amount, Selection |
| **GN_Spherify** | `GN_Spherify.blend` | Blend shape toward a sphere | Factor, Radius, Center |
| **GN_Twist** | `GN_Twist.blend` | Twist around an axis | Axis, Angle, Symmetry, Center |
| **GN_Taper** | `GN_Taper.blend` | Scale cross-section along an axis | Axis, Factor, Symmetry, Affect X/Y/Z, Center |
| **GN_Stretch** | `GN_Stretch.blend` | Volume-preserving squash & stretch | Axis, Factor, Affect X/Y/Z, Center |
| **GN_Bend** | `GN_Bend.blend` | Bend a bar into an arc | Angle, Center |
| **GN_Wave** | `GN_Wave.blend` | Concentric/radial sine displacement | Amplitude, Wavelength, Phase, Displace Along, Center |
| **GN_Cast** | `GN_Cast.blend` | Cast toward a sphere / cylinder / box | Shape, Factor, Radius, Axis, Center |
| **GN_Smooth** | `GN_Smooth.blend` | Relax positions (blur) | Iterations, Factor, Selection |
| **GN_Displace** | `GN_Displace.blend` | Coherent noise displacement | Strength, Midlevel, Scale, Detail, Direction |
| **GN_RandomizePosition** | `GN_RandomizePosition.blend` | Per-element jitter via noise | Direction, Noise Type, Amount, Scale, Detail, Roughness, Seed |
| **GN_ShearGeometry** | `GN_ShearGeometry.blend` | Shear along an axis with a mask axis | Shear Factor, Shear Axis, Mask Axis, Symmetry, Center |
| **GN_FlattenByBoundary** | `GN_FlattenByBoundary.blend` | Flatten each face region (walled off by a boundary edge selection) to its own average plane | Boundary Edges, Factor, Selection |
| **GN_SimpleTransformMesh** | `GN_SimpleTransform.blend` | Transform selected geometry (world or local) | Translation, Rotation, Scale, World Space |

### Generators & Topology
Create, replace, or restructure geometry.

| Modifier | File | What it does | Key parameters |
|----------|------|--------------|----------------|
| **GN_Subdivide** | `GN_Subdivide.blend` | Subdivide (Catmull-Clark or simple) | Level, Smooth |
| **GN_Triangulate** | `GN_Triangulate.blend` | Triangulate faces | Selection |
| **GN_Wireframe** | `GN_Wireframe.blend` | Convert edges to a wireframe mesh | Thickness, Resolution, Fill Caps |
| **GN_ConvexHull** | `GN_ConvexHull.blend` | Convex hull of the input | Geometry |
| **GN_BoundingBox** | `GN_BoundingBox.blend` | Axis-aligned bounding-box mesh | Geometry |
| **GN_DualMesh** | `GN_DualMesh.blend` | Dual mesh (faces ↔ vertices) | Keep Boundaries |
| **GN_VoxelRemesh** | `GN_VoxelRemesh.blend` | Volume-based voxel remesh | Voxel Size, Adaptivity |
| **GN_RadialArray** | `GN_RadialArray.blend` | Radial duplicate around a center (realized) | Count, Radius, Axis, Center |
| **GN_PointsToSpheres** | `GN_PointsToSpheres.blend` | Replace vertices with ico-sphere instances | Radius, Subdivisions, Selection |
| **GN_Scatter** | `GN_Scatter.blend` | Scatter an object over the surface | Instance Object, Density, Seed, Scale Min/Max, Align to Normal |
| **GN_MeshBoolean** | `GN_MeshBoolean.blend` | Boolean against a cutter object | Cutter Object, Operation, Self Intersection, Hole Tolerant |
| **GN_CollectionInstancerModel** | `GN_CollectionInstancer.blend` | Advanced grid/collection instancing system | Instance Type, Collection/Object, Grid, Seed, Offset/Rotation/Scale, Material Override |

### Mesh & Attribute Utilities
Edit materials, shading, or attribute data without changing the silhouette.

| Modifier | File | What it does | Key parameters |
|----------|------|--------------|----------------|
| **GN_FlipFaces** | `GN_FlipFaces.blend` | Flip face normals | Selection |
| **GN_AutoSmooth** | `GN_AutoSmooth.blend` | Shade smooth by angle | Angle |
| **GN_SetMaterial** | `GN_SetMaterial.blend` | Assign a material to a selection | Material, Selection |
| **GN_MaterialOverride** | `GN_CollectionInstancer.blend` | Override all materials | On, Invert, Material Override |
| **GN_Weld** | `GN_Weld.blend` | Merge by distance | Mode (All/Connected), Distance, Selection |
| **GN_Delete** | `GN_Delete.blend` | Delete geometry by selection/material/axis filters | Selection Mode, Material ID, Domain, Axis filters |
| **GN_ExtrudeFace** | `GN_ExtrudeSelection.blend` | Full-featured face extrusion (incl. region fill from marked edges) | Selection, Height, Divisions, Smooth, Crease, Material ID, … |
| **GN_MirrorGroup** | `GN_Mirror_Groupable.blend` | Per-axis mirror with UV & merge controls | X/Y/Z Axis, Mirror Object, Merge, UV controls |
| **GN_SplitEdgeByAttribute** | `GN_SplitByAttribute.blend` | Split edges by an attribute / face-group boundary | Attribute Preset, Custom Attribute, Boundary of Face Group |
| **GN_SetAttribute** | `GN_AttributeFunctions_4.5.blend` | Build/write attributes from many selection criteria | Selection sources, Write-to Attribute, Mix Mode, … |
| **GN_AttributeTransfer** | `GN_AttributeFunctions_4.5.blend` | Transfer & remap attributes | From/To Attribute, Domain, Mix Mode, Blur |
| **GN_NormalTransfer** | `GN_NormalTransfer.blend` | Transfer custom normals from a source object, masked to keep originals where wanted | Source Object, Masking Mode (None / Attribute / Open Boundary Edges), Mask Attribute, Invert Mask |

> Several deformers accept their `Selection` (and `GN_FlattenByBoundary` its `Boundary Edges`)
> as a **bindable attribute** via the modifier's *"sets via attribute"* toggle, so you can drive
> them from a stored edge/vertex group.

---

## 🛠 Other assets & helpers in this folder

- **Layout tooling moved** → `../Addons/ClaudeVibe_WIPs/LLMGeonodePipeline/`. The deterministic
  wire-routing / tidy engine (formerly `geonode_route_tidy.py`, now `tidy_layout.py`), the
  `layout_audit.py` rules checker, and the `run_pipeline.py` orchestrator (tidy → verify →
  save) that reframes and re-routes these modifier files all live there now.
- **Node-group utilities** (Asset Browser only, not modifiers): `GN_FillBorder`, `GN_GrowSelection`,
  `GN_InsetFace`, `GN_MeshFromImage`, `GN_DisplaceByImage`, `GN_Solidify2`, `SHG_TileableNoise`.
- **Procedural Tree Generator** — see [`TreeGenDocu/`](TreeGenDocu/README.md) for the full
  Geometry-Nodes tree system and its documentation.
- **`GN_VariousTest.blend`** — scratch/test file (ignore).

---

## ✍️ Authoring notes

New ST3E modifiers are built headlessly against Blender 5.0 and must, to appear in the
**Add Modifier → ST3E** menu:

1. Be **marked as an asset** (`node_group.asset_mark()`).
2. Be assigned to the **ST3E catalog** (`blender_assets.cats.txt`).
3. Have a **Geometry input + Geometry output** socket.
4. Have the **Modifier asset trait** on (`node_group.is_modifier = True`).
5. Carry the **`ST3E` tag** (`asset_data.tags.new("ST3E")`).

Each modifier ships a demo object, has tooltipped sockets, framed/labelled nodes, and is
eval-verified (identity at neutral parameters, no NaN).

---

**Last Updated:** 2026-07-02
**Modifier count:** 38 ST3E modifiers
