# Continuation Brief — GeoNode Extraction + Crater Variants (GN_Erosion_3D / GN_CellFrac)

## Context
Analyzed `D:\Work_DistrictGames\Assets\Environment\sm_env_masterfile_02.blend` (80 GN trees, 19 local) for library extraction. Extracted two tools into `Blender/Geonodes/` and built a crater-fracture feature set on GN_CellFrac. All work done headlessly (`blender.exe --background --factory-startup --python`, Blender 5.0); masterfile never written.

## Progress
- **`GN_Erosion_3D.blend`** — extracted (renamed from `GN_Erosion_fromtexgen`), self-contained, demo Cube attached. Untouched otherwise: NOT tidied, NOT asset-marked.
- **`GN_CellFrac.blend`** — extracted, localized, crater feature set built, and **criteria cleanup DONE (2026-07-13)**:
  - Main tree `GN_CellFrac` + subgroups `GNG_CraterWeight`, `GNG_CraterIterations`, `GNG_CraterRefine`, `GNG_CraterScatter` (+ localized G_* helpers, `Randomize Transforms`).
  - **User decided to KEEP BOTH crater modes** (no loser deleted). Menu identifiers still **2=Uniform / 3=Per Island Iterations / 4=Recursive Refine** (modifier override = that int).
  - Cleanup applied: 24 dead-end/viewer/broken-chain nodes deleted from main tree (Accumulate Field centroid attempt, Geometry Proximity, Map Range→Reroute, 2 Viewers, and the inverted `Probability × clamp01(dist−0.5) × 0.5` WIP math incl. its Switch.001/Object Info feeders). `Probability` now wires **directly** into the island-pick Random Value; interface + modifier default raised to **1.0** — with that, Uniform output hash is **bit-identical to legacy** (142v/105p, hash 966a545f957f).
  - R9 fixed: seeds renamed by identifier — Socket_3=`Fracture Seed` (feeds G_Cell Fracture math AND both crater subgroups), Socket_9=`Transform Seed`, Socket_12=`Selection Seed` (island pick only). Renames only, no reorder — modifier overrides intact.
  - R10: main-tree panels `Fracture` / `Crater` / `Randomize Pieces` / `Scatter`; all inputs have tooltips.
  - R8/R4: labeled function frames in main tree + all 4 GNG_ subgroups; key math/switch nodes labeled.
  - `run_pipeline.py` tidy+audit on main tree: SAVED, geometry unchanged, all rules pass except advisory R3 (1 backward link Join→Menu Switch, banding artifact). Subgroups tidied via `tidy_and_route` + audited: structurally sound; advisories only R3 zone-internal links (legit) + R10 (internal groups, not modifier-facing).
  - Geometry gate used everywhere: vert-coord md5 per config — mode3 `(50,37,5da24744a5fb)`, mode4 `(1064,790,b61ff06495d8)`, mode3+scatter `(50,37,e65fd1c6fe76)`, uniform `(142,105,966a545f957f)`. All unchanged through every pass.
- **Git**: commit `3573522` pushed (pre-cleanup state). **Cleanup changes to GN_CellFrac.blend are NOT yet committed.** Tree also still has unrelated uncommitted work (LLMGeonodePipeline v1.2.0, MassExporter v13.6.3, other new geonode blends) — deliberately not committed.

## Decisions
- Keep BOTH crater variants permanently (user, 2026-07-13).
- Uniform-mode probability fix is a deliberate behavior fix; with Probability default 1.0 the shipped default output is byte-identical to legacy anyway.
- Center Bias defaults = 1.0, scatter/bounds default OFF, default mode Uniform.

## Next Steps
1. Commit the GN_CellFrac cleanup (when user asks).
2. Criteria pass on **GN_Erosion_3D** (frames exist: Per Object Offset, Erosion Direction Variation, Masking; needs panels check + tidy + audit).
3. Publish checklist for both per `mem:project_geonode_modifier_asset_checklist` (asset mark, ST3E catalog f9ab2fa9…, ST3E tag, is_modifier=True, demo object, full mainfile save).
4. Optionally commit the older pending LLMGeonodePipeline/MassExporter work separately.

## Open Questions
- Masterfile follow-ups (separate task): relink its local `GN_EdgeDestruct` (232 users) and 4× `Smooth by Angle` copies to library/essentials; extract GN_MeshPlacer, primitive family (Grid/Cube/Cylinder/Ico + Fix Pivot + Set Material to Index 0), Ambient Occlusion.002 (needs Fibonacci group localized), GN_Prim_TorusDisc; diff simple `GN_Erosion` (17 nodes) vs library `GN_Erosion.blend`.
- **Gotcha for relinking masterfile objects to the new GN_CellFrac**: existing modifiers zero-init new sockets (Impact Radius/biases read 0 → crater modes silently no-op) — must write interface defaults into each modifier. Also note masterfile modifiers will keep their old stored Probability (likely 0.5) — set to 1.0 for legacy-equivalent behavior.
