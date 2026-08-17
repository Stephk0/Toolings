# ST3E Geometry Nodes Library

> Procedural Geometry Nodes assets for Blender 5.0+ — a library of **40 ST3E modifiers**
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

**Effect direction — quick axis _or_ an empty.** Every deformer with a direction/axis lets you
pick it fast (X / Y / Z) **or** choose **`Object`** on the same menu and point a **Direction
Object** (an empty) — the effect then follows the empty's local **+Z** axis, so you aim it just by
rotating the empty. Center-based deformers also add **Use Object As Center** (default off) to make
the empty's location the pivot. The manual X/Y/Z + Center controls stay fully first-class.

| Modifier | File | What it does | Key parameters |
|----------|------|--------------|----------------|
| **GN_Inflate** | `GN_Inflate.blend` | Push geometry along its normals | Amount, Selection |
| **GN_Spherify** | `GN_Spherify.blend` | Blend shape toward a sphere | Factor, Radius, Center |
| **GN_Twist** | `GN_Twist.blend` | Twist around an axis | Axis (X/Y/Z/**Object**), Angle, Symmetry, Center, Direction Object, Use Object As Center |
| **GN_Taper** | `GN_Taper.blend` | Scale cross-section along an axis | Axis (X/Y/Z/**Object**), Factor, Symmetry, Affect X/Y/Z, Center, Direction Object, Use Object As Center |
| **GN_Stretch** | `GN_Stretch.blend` | Volume-preserving squash & stretch | Axis (X/Y/Z/**Object**), Factor, Affect X/Y/Z, Center, Direction Object, Use Object As Center |
| **GN_Bend** | `GN_Bend.blend` | Bend a bar into an arc, in any direction | **Bend Axis** (length, X/Y/Z/Object), **Bend Direction** (deflection, X/Y/Z/Object), Angle, Center, Direction Object, Use Object As Center |
| **GN_Wave** | `GN_Wave.blend` | Concentric/radial sine displacement | Amplitude, Wavelength, Phase, Displace Along (X/Y/Z/Normal/**Object**), Center, Direction Object, Use Object As Center |
| **GN_Cast** | `GN_Cast.blend` | Cast toward a sphere / cylinder / box | Shape, Factor, Radius, Axis (X/Y/Z/**Object**), Center, Direction Object, Use Object As Center |
| **GN_Smooth** | `GN_Smooth.blend` | Relax positions (blur) | Iterations, Factor, Selection |
| **GN_Displace** | `GN_Displace.blend` | Coherent noise displacement | Strength, Midlevel, Scale, Detail, Direction (Normal/X/Y/Z/**Object**), Direction Object |
| **GN_RandomizePosition** | `GN_RandomizePosition.blend` | Per-element jitter via noise | Direction, Noise Type, Amount, Scale, Detail, Roughness, Seed |
| **GN_RandomizeMeshElements** | `GN_RandomizeMeshElements.blend` | Give every mesh element (island / face / material / attribute group) its own random offset, rotation, scale and axis mirroring | Group By, Group Attribute, Seed, Affect Chance, Position Amount, Rotation Amount, Uniform Scale, Scale Min/Max, Flip X/Y/Z Chance, Flip Faces On Mirror, Pivot Point |
| **GN_ShearGeometry** | `GN_ShearGeometry.blend` | Shear along an axis with a mask axis | Shear Factor, Shear Axis (X/Y/Z/**Object**), Mask Axis (X/Y/Z/**Object**), Symmetry, Center, Direction Object |
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
| **GN_Mosaic** | `GN_Mosaic.blend` | Fills the areas of a surface with mosaic tesserae. Two generators via **Tiling Mode**, each with its own parameter panel: *Grid* lays a rotated lattice and keeps the cells that fit; ***Shatter*** instead SUBDIVIDES each region itself, so the tiles **partition the shape exactly** — verified 100.00% coverage at zero grout, every outline, corner and hole formed by real tile edges, nothing clipped and no strip left over. **Max Corners** (3-6) picks the break-up: all-triangle, quads, or the loose polygonal paving of opus palladianum with pentagons and hexagons. Grout is exact per edge, so **Boundary Gap** can hold the tiles off the walls while their shared edges keep the ordinary Gap — and **Tileable** + **Tile Bounds** make a patch repeat seamlessly: edges on a bounds face take half the interior Gap, so two copies laid side by side meet with exactly one Gap, indistinguishable from any other joint, and cuts never add a vertex to a seam so the two faces stay divided identically at any Split Jitter (verified on a 3×3 array, 0 unmatched cuts). **Sizes and grout are ranges, not single numbers.** **Tile Size Max**, **Gap Max** and **Boundary Gap Max** each turn their base value into a `min .. max` band that every tessera or joint draws from — the quickest way to stop a mosaic reading as a manufactured sheet. All three are 0 by default, which means *no range* and byte-identical output to before. Grid mode spaces its lattice for the largest tile and lets the smaller draws sit in correspondingly more grout; Shatter splits each piece down to its own target, so the range changes the break-up itself. In Shatter the grout is drawn per **edge** from the edge's own midpoint, so both tiles sharing a joint agree on its width and it stays even along its length — and stays in register across a Tileable seam. Keep the maxima in proportion to the tile: a grout approaching the size of the tesserae simply eats the ones it touches, and those get dropped rather than folded inside out. Shattered tiles can also take the same hand-laid wobble the grid tiles get — **Shatter Position / Rotation / Scale Jitter** slide, turn and shrink each tessera about its own centroid. All three default to 0. Position Jitter is scaled by the grout the tile just opened, so it can never make tiles collide and does nothing at Gap 0 — the exact partition survives whatever you dial in. Rotation gives you exactly the angle you ask for at any Gap, which does mean the bigger tesserae start to overlap past a few degrees; widen the Gap to buy room, or keep the angle small. Tiles touching a seam sit the wobble out when **Tileable** is on, since the tile on the far face is a different shape and no rigid nudge could keep both in register. **Adaptive sizing** lets tiles earn their size from the room they have — cells that crowd a wall split, so open ground keeps full-size tesserae while necks and corners get halves and quarters. Contour rows have their own **Length / Width / Spacing / Triangle Ratio**, and **Boundary Gap** + **Fit Tiles To Boundary** reshape border tiles onto the outline and then hold everything back by that grout. Edges you mark (and/or the mesh's own open edges) are the walls; each closed loop becomes its own **region** with its own `region_id`, however organic its outline. Square **and** triangular tiles (ratio-controlled), an irregular lattice, per-tile size/rotation/position jitter, and optional **contour rows** that follow the outline (opus vermiculatum). Fit modes decide how border tiles are judged (note *Fully Inside* keeps whole tiles only, so it leaves a tile-wide strip along every wall — that strip is what the contour rows fill; with rows ≥ 1 the three modes agree), and **Cut Tiles At Boundary** clips tiles flush to the outline *and* to interior walls. Every tile carries a unique `tile_id` plus `region_id` / `tile_random` / `tile_color` for material work | Boundary Edges, Use Open Edges, Tile Size, Gap, Triangle Ratio, Seed, Grid Rotation, Irregularity, Position/Rotation Jitter, Scale Variation, Region Rotation, Fit Mode (Center Inside / Fully Inside / Any Overlap), Edge Margin, Cut Tiles At Boundary, Tile Size Max, Gap Max, Boundary Gap Max, Shatter Position/Rotation/Scale Jitter, Contour Rows, Contour Spacing, Projection Axis (Auto/X/Y/Z/Object), Direction Object, Conform To Surface, Surface Offset, Material, Thickness, Keep Source Mesh, attribute names |
| **GN_TileableMeshNoise** | `GN_TileableMeshNoise.blend` | Seamlessly tileable cell mesh (tile = input bounds, or an explicit Bounds Size): noise-warped quad grid, Voronoi cell polygons, or the input mesh's own faces as cells; switchable distortion algorithms (Perlin value noise / Voronoi feature-pull / per-cell Swirl vortices); multi-pass sub-cell refinement with per-parent-cell probability; optional cell isolation with a gap (border verts slide along the tile edge so gaps stay open at seams and tiling stays continuous); per-cell `cell_id`/`cell_random` face attributes + `cell_color` debug color | Cell Type (Perlin Grid 4 / Voronoi ~6 / Input Mesh / Triangles 3 / Pentagons 5 / Octagons 8+4), Bounds Size (0 = auto from input bounds; per-axis override), Cells X/Y, Cell Subdivision, Distortion Type (Perlin / Voronoi / Swirl), Distortion, Seed, Passes, Pass Falloff, Pass Probability, Isolate Cells, Preserve Tile Border, Cell Gap |

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
| **GN_PolygonTileableNoise** | `GN_PolygonTileableNoise.blend` | Store a tileable piecewise-linear (triangulated) Perlin/Voronoi noise value as a face-corner attribute, keyed on UVs (Position.xy fallback) | Noise Type, Noise Scale, Seed, UV Map, Tile Size, Output Attribute |
| **GN_VertexDataComposer** | `GN_VertexDataComposer.blend` | Author every channel an FBX mesh can carry — 4 colour attributes (RGBA) + 8 UV maps (U/V) = 32 independently writable channels, each with its own source and processing chain. Channels left off are untouched; unused slots are never created | Per channel: Write, Source (30 of them), Attribute, Component, Constant, Auto Range, From/To Min-Max, Clamp, Invert, Gamma, Quantize Steps, Blur, Encode sRGB. Per colour slot: Name, Domain (Vertex/Face Corner), Data Type (Byte/Float). Shared: Source Object, Seed, Compute Ambient Occlusion (+Distance, Spread), Compute Boundary Distance (+Boundary Edges), Compute Object Distance |

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
2. Be assigned to a **leaf ST3E sub-catalog** (`blender_assets.cats.txt`) — `ST3E/Deform`,
   `ST3E/Generate`, `ST3E/Modify` or `ST3E/Scatter & Instancing`. The flat `ST3E` root
   holds no direct assets since the sub-catalog split, so a group left on it lands
   outside every group in the browser.
3. Have a **Geometry input + Geometry output** socket.
4. Have the **Modifier asset trait** on (`node_group.is_modifier = True`).
5. Carry the **`ST3E` tag** (`asset_data.tags.new("ST3E")`).

Each modifier ships a demo object, has tooltipped sockets, framed/labelled nodes, and is
eval-verified (identity at neutral parameters, no NaN).

---

**Last Updated:** 2026-08-09
**Modifier count:** 40 ST3E modifiers
