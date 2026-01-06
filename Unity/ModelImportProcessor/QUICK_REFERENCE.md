# Model Import Processor - Quick Reference

## Create a Rule

### Material Remap Rule
1. **Right-click** in Project window
2. **Create > Stephko > Model Import Rules > Material Remap Rule**
3. Configure in Inspector

### Collider Setup Rule
1. **Right-click** in Project window
2. **Create > Stephko > Model Import Rules > Collider Setup Rule**
3. Configure suffixes and collider types

## Path Pattern Examples

```
Assets/**                           # All assets
Assets/Models/Characters/**         # All files in Characters (recursive)
Assets/Art/Props/*.fbx              # Only FBX in Props folder
Assets/**/*_LOD*.fbx               # Any FBX with "LOD" in name
```

## Material Import Modes

| Mode | Description | Use When |
|------|-------------|----------|
| `None` | Don't import materials | Using custom material assignment |
| `ImportStandard` | Legacy standard import | Compatibility with old projects |
| `ImportViaMaterialDescription` | Modern preprocessing | New projects (recommended) |

## Material Location

| Location | Description | Materials Stored |
|----------|-------------|------------------|
| `External` | Use project materials | In Assets/Materials folders |
| `InPrefab` | Embed in asset | Inside the imported model file |

## Material Name Modes

| Mode | Format | Example |
|------|--------|---------|
| `BasedOnTextureName` | `<texture>.mat` | `wood_diffuse.mat` |
| `BasedOnMaterialName` | `<material>.mat` | `Wood.mat` |
| `BasedOnModelNameAndMaterialName` | `<model>-<material>.mat` | `tree-Wood.mat` |

## Material Search Modes

| Mode | Search Scope | Example |
|------|--------------|---------|
| `Local` | Same folder only | `Assets/Models/tree/Materials/` |
| `RecursiveUp` | Up to Assets root | `Assets/Models/Materials/`, `Assets/Materials/` |
| `Everywhere` | Entire project | Anywhere in `Assets/` |

## Debug Menu

**Tools > Stephko > Model Import Processor >**

- **Refresh Rule Cache** - Reload all rules
- **List All Rules** - Show all rules in Console
- **Test Rules on Selected Asset** - See which rules match

## Common Workflows

### External Materials (Recommended)

```
Material Import Mode: ImportViaMaterialDescription
Material Location: External
Enable Search And Remap: ✓
Material Name Mode: BasedOnMaterialName
Material Search Mode: RecursiveUp
```

**Folder Structure:**
```
Assets/Models/hero/hero.fbx
Assets/Models/hero/Materials/Body.mat
```

### Embedded Materials

```
Material Import Mode: ImportViaMaterialDescription
Material Location: InPrefab
Enable Search And Remap: ✗
```

**Result:** Materials stored inside the .fbx asset

### No Materials (Custom Assignment)

```
Material Import Mode: None
```

**Result:** No materials imported, assign manually

### Auto Colliders

```
Mesh Collider Suffix: "_COL"
Box Collider Suffixes: ["_COLCUBE", "_COLBOX"]
Mesh Collider Convex: ✓
Hide Collision Mesh: ✓
```

**Result:** Meshes with suffixes get colliders automatically

## Collider Naming Conventions

| Suffix | Collider | Example |
|--------|----------|---------|
| `_COL` | MeshCollider | `tree_COL` |
| `_COLCUBE` / `_COLBOX` | BoxCollider | `platform_COLBOX` |
| `_COLSPHERE` / `_COLSPH` | SphereCollider | `ball_COLSPHERE` |
| `_COLCAPSULE` / `_COLCAP` | CapsuleCollider | `pillar_COLCAPSULE` |

**Workflow:**
1. In Blender: Create mesh named `wall_COLCUBE`
2. Export FBX
3. Unity adds BoxCollider automatically

## Priority Tips

- **30-40** - Fallback/default rules
- **50** - Standard rules
- **60-70** - Override rules
- **Higher runs first!**

## Troubleshooting

❌ **Rules not applying**
- Check rule is Enabled
- Verify path pattern matches
- Use "Test Rules on Selected Asset"

❌ **Materials not remapping**
- Enable "Verbose Logging"
- Check material names match
- Verify materials exist in search path

❌ **Wrong materials applied**
- Check Material Name Mode
- Check Material Search Mode
- Higher priority rules override lower

## Quick Test

1. Create rule
2. Set path: `Assets/**/*.fbx`
3. Enable verbose logging
4. Import any FBX file
5. Check Console output

---

For full documentation, see [README.md](README.md)
