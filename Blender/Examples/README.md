# Examples

Production scenes that show the ST3E geonode library in use. The `.blend` files are stored
with Git LFS — run `git lfs pull` after cloning.

## ST3E_Examples_Character.blend

A stylized character: jacket, backpack, crocs, head and hair, rigged with Rigify. Almost every
part is a low-poly base mesh with a stack of ST3E modifiers (`GN_Delete`,
`GN_SplitEdgeByAttribute`, `GN_ExtrudeFace`, `GN_InsetFaces`, `GN_CurveFromSurface`,
`GN_SetAttribute`, `GN_AttributeTransfer`, …) followed by Solidify and Subdivision.

### Collections

| Collection | Contents |
|---|---|
| `Character/Head` | Head retopo, eyes, brows, hair curves. `Original_Sculpt` holds the ZBrush head that the retopo shrinkwraps to. The `Junk_*` collections are old sculpt passes |
| `Character/Jacket` | Jacket, its trims, zipper, strings, eyelets, pins, and two design variants (`_VarA`, `_VarB`) placed beside the character |
| `Character/Backpack` | Backpack, seams, zipper, straps |
| `Character/Shoes` | Croc (with a studded copy), sneaker (hidden), shoe charm |
| `Character/Body` | Legs / feet (one mesh, two modifier stacks) and the skinned arms |
| `Character/Elements` | Standalone copies of the zipper buckle and base (hidden) |
| `Character/Sources` | Objects that only feed modifiers — profiles, instance sources, mirror plane. Not rendered |
| `Character/Sources/Tests` | Leftover experiments with no users |
| `Character/Rig` | Rigify metarig + rig; `WGTS_rig` holds the bone widgets (not rendered) |
| `Character/ML_Gizmo Objects` | Lattices and empties the Modifier List add-on created for gizmos |
| `Props_WIP` | Hidden: gun kitbash props, stripe decal |

### One base mesh, several parts

Several parts are the same mesh with a different modifier stack. Editing the mesh changes
all of them:

| Mesh | Objects that share it |
|---|---|
| `ME_Jacket_Base` | `SM_Char_Jacket`, `SM_Char_Jacket_Trim`, `SM_Char_Jacket_PocketTrim`, `SM_Char_Jacket_Zipper`, `SM_Jacket_Torsos` |
| `ME_Backpack_Base` | `SM_Backpack`, `SM_Backpack_Seams`, `SM_Backpack_Zipper` |
| `CU_Backpack_Straps` | `SM_Backpack_Straps`, `SM_Backpack_Straps_Piping` |
| `ME_ShoeCroc` | `SM_ShoeCroc`, `SM_ShoeCroc.001` (studs) |
| `ME_Body_Legs` | `SkinBase_Body_Pants`, `SkinBase_Body_Feet` |
| `ME_Zipper_Buckle` / `ME_Zipper_Base` | the jacket zipper parts and their copies in `Elements` |

### Objects that feed other objects

| Source | Used by | How |
|---|---|---|
| `SRC_ZipperTooth` | `SM_Char_Jacket_Zipper`, `SM_Backpack_Zipper` | `GN_SpawnObjectsAlong` → Object |
| `SRC_StrapProfile` | `SM_Backpack_Straps_Piping` | `GN_CurveFromSurface` → Custom Profile Shape |
| `SRC_StringEyelet` | `SM_Jacket_Torsos` | `GN_DistributeObjectOnSurface` → Distribution Object |
| `SRC_ShoeStud` | `SM_ShoeCroc.001` | `GN_DistributeObjectOnSurface` → Distribution Object |
| `SRC_ShoeMirrorPlane` | all three shoes | Mirror → Mirror Object |
| `SM_Char_Jacket` | strings, eyelets, string beads | Mirror → Mirror Object (they follow the jacket) |
| `SM_Char_Jacket` | `Skin_Body_Arms` | UV Project projector |
| `ZB_Head` | `Head_Retopo`, `ZB_Head.003` | Shrinkwrap + Data Transfer |
| `face_sculpttest8.003` (in `Junk_Face`) | `Curve_Brows` | Mirror → Mirror Object — do not delete the junk collection |
| `Curve_Profile_Hair.*` | hair curves, brows | Curve bevel object |
| `Lattice`, `Lattice_Gizmo*` | head sculpts, brows, shoes | Lattice modifier |
| `rig` | `Skin_Body_Arms`, `Skin_Body_Arms.001` | Armature + parent |

### Linked node groups

The ST3E modifiers are linked from `../Geonodes/`. A few groups are still linked from
third-party libraries that only exist on the author's machine (Higgsas `Mesh Ambient
Occlusion` / `Taper`, `Solidify Plus`, Bradley's `G_Curve Deformer`); those modifiers show as
missing elsewhere.
