# Unity Model Import Processor

**Version:** 1.0
**Author:** Stephan Viranyi (Stephko)
**Unity Version:** 2019.4+

## Overview

The **Model Import Processor** is a flexible, rule-based system for automating model import settings in Unity. It uses ScriptableObject-based rules that can be configured to apply different import settings to models based on their file paths.

### Key Features

- **ScriptableObject-Based Rules** - Create reusable import configurations as assets
- **Path Pattern Matching** - Use wildcards or regex to target specific models
- **Priority System** - Control the order in which rules are applied
- **Material Remapping** - Full support for Unity's material import and remapping API
- **Collider Setup** - Automatic collider generation based on mesh naming conventions
- **Extensible Architecture** - Easy to add new rule types for other import settings
- **Debug Tools** - Built-in menu items for testing and debugging rules

## Installation

1. Copy the `ModelImportProcessor` folder to your Unity project's `Assets/Editor` directory
2. Unity will automatically compile the scripts
3. The system is now active and will process all model imports

## Quick Start

### 1. Create a Material Remap Rule

1. Right-click in the Project window
2. Navigate to: **Create > Stephko > Model Import Rules > Material Remap Rule**
3. Name your rule (e.g., "Character Material Remap")

### 2. Configure the Rule

Select the newly created rule asset and configure it in the Inspector:

**Rule Settings:**
- **Enabled** - Toggle to enable/disable the rule
- **Priority** - Higher values execute first (0-100)

**Path Matching:**
- **Path Patterns** - Array of path patterns to match
  - Examples:
    - `Assets/Models/Characters/**` - All files in Characters folder and subfolders
    - `Assets/Art/Props/*.fbx` - Only FBX files in Props folder
    - `Assets/**/*_LOD*.fbx` - Any FBX file with "LOD" in the name

**Material Import Settings:**
- **Material Import Mode** - How materials are created
  - `None` - Don't import materials
  - `ImportStandard` - Use standard material import (Legacy)
  - `ImportViaMaterialDescription` - Use material description preprocessing
- **Material Location** - Where materials are stored
  - `External` - Use external materials if found (Legacy)
  - `InPrefab` - Embed materials in the imported asset

**Material Remapping:**
- **Enable Search And Remap** - Automatically remap materials using existing project materials
- **Material Name Mode** - How material names are matched
  - `BasedOnTextureName` (0) - Use texture name or material name as fallback
  - `BasedOnMaterialName` (1) - Use material name from the model
  - `BasedOnModelNameAndMaterialName` (2) - Use model+material name combination
- **Material Search Mode** - Where to search for materials
  - `Local` (0) - Only in the local Materials folder
  - `RecursiveUp` (1) - Search up through parent Materials folders
  - `Everywhere` (2) - Search the entire Assets folder

**Advanced Options:**
- **Import Materials** - Master toggle for material import
- **Verbose Logging** - Enable detailed console output for debugging

### 3. Test the Rule

1. Select a model asset in the Project window
2. Go to: **Tools > Stephko > Model Import Processor > Test Rules on Selected Asset**
3. Check the Console to see which rules match

### 4. Apply the Rule

Simply import or reimport a model that matches the path pattern. The rules will be applied automatically!

## Usage Examples

### Example 1: Character Models with External Materials

**Goal:** Character models should use external materials stored in `Assets/Materials/Characters/`

**Configuration:**
```
Enabled: ✓
Priority: 50
Path Patterns: ["Assets/Models/Characters/**"]

Material Import Mode: ImportViaMaterialDescription
Material Location: External
Enable Search And Remap: ✓
Material Name Mode: BasedOnMaterialName
Material Search Mode: RecursiveUp
```

### Example 2: Environment Props with Embedded Materials

**Goal:** Environment props should have materials embedded in the prefab

**Configuration:**
```
Enabled: ✓
Priority: 50
Path Patterns: ["Assets/Models/Environment/**", "Assets/Art/Props/**"]

Material Import Mode: ImportViaMaterialDescription
Material Location: InPrefab
Enable Search And Remap: ✗
```

### Example 3: LOD Models Without Materials

**Goal:** LOD models should not import materials at all

**Configuration:**
```
Enabled: ✓
Priority: 60 (higher to override other rules)
Path Patterns: ["Assets/**/*_LOD*.fbx"]

Material Import Mode: None
```

### Example 4: Automatic Collider Setup

**Goal:** Automatically add colliders to meshes based on naming suffixes

**Configuration:**
```
Enabled: ✓
Priority: 50
Path Patterns: ["Assets/**"]

Mesh Collider Suffix: "_COL"
Box Collider Suffixes: ["_COLCUBE", "_COLBOX"]
Sphere Collider Suffixes: ["_COLSPHERE"]
Capsule Collider Suffixes: ["_COLCAPSULE"]

Mesh Collider Convex: ✓
Hide Collision Mesh: ✓
Remove Collision Mesh GameObject: ✗
```

**Usage in Blender:**
1. Create visual mesh: `tree`
2. Create collision mesh: `tree_COL` or `platform_COLCUBE`
3. Export FBX with both meshes
4. Unity automatically adds appropriate colliders and hides collision meshes

## Collider Setup Rule

The **Collider Setup Rule** automatically adds Unity colliders to imported models based on mesh naming conventions. This eliminates manual collider setup and integrates seamlessly with DCC workflows.

### Supported Collider Types

| Suffix | Collider Type | Description |
|--------|---------------|-------------|
| `_COL` | MeshCollider | Uses the actual mesh geometry (convex or non-convex) |
| `_COLCUBE` or `_COLBOX` | BoxCollider | Box collider sized to mesh bounds |
| `_COLSPHERE` or `_COLSPH` | SphereCollider | Sphere collider sized to mesh bounds |
| `_COLCAPSULE` or `_COLCAP` | CapsuleCollider | Capsule collider oriented to longest axis |

### Workflow Example

**In Blender/Maya/3DS Max:**
```
MyEnvironment.fbx
├─ floor_visual      (visual mesh)
├─ floor_COLCUBE     (simplified box for collision)
├─ tree_visual       (visual mesh)
├─ tree_COL          (detailed mesh collider)
├─ ball_visual       (visual mesh)
└─ ball_COLSPHERE    (sphere collision)
```

**After Import to Unity:**
- `floor_COLCUBE` → BoxCollider added, mesh hidden
- `tree_COL` → MeshCollider added, mesh hidden
- `ball_COLSPHERE` → SphereCollider added, mesh hidden

### Collider Rule Settings

**Mesh Collider Settings:**
- **Mesh Collider Convex** - Make mesh colliders convex (required for Rigidbody)
- **Mesh Collider Cooking Options** - Enable collision cooking

**Mesh Handling:**
- **Hide Collision Mesh** - Disable MeshRenderer on collision meshes (recommended)
- **Remove Collision Mesh GameObject** - Delete collision mesh GameObject after setup (advanced)

**Advanced Options:**
- **Case Insensitive** - Match suffixes regardless of case (`_COL` = `_col`)
- **Verbose Logging** - Log each collider added to Console

## Path Pattern Syntax

### Wildcard Patterns (Default)

- `*` - Matches any characters except directory separator
  - Example: `*.fbx` matches `model.fbx` but not `folder/model.fbx`
- `**` - Matches any directory recursively
  - Example: `Assets/**/*.fbx` matches all FBX files in Assets and subdirectories
- `?` - Matches a single character
  - Example: `model?.fbx` matches `model1.fbx`, `modelA.fbx`, etc.

### Regex Patterns

Enable "Use Regex" and use standard .NET regex syntax:

```
^Assets/Models/(Characters|Enemies)/.*\.fbx$
```

## Priority System

When multiple rules match the same asset:

1. Rules are sorted by priority (highest first)
2. Each matching rule is applied in order
3. Later rules can override earlier rules' settings

**Best Practices:**
- Use priority 50 for general rules
- Use priority 60-70 for specific overrides
- Use priority 30-40 for fallback rules

## Debug Tools

### Menu: Tools > Stephko > Model Import Processor

**Refresh Rule Cache**
- Manually refresh the internal rule cache
- Useful after creating/modifying rules

**List All Rules**
- Display all rules in the Console
- Shows priority, enabled state, and path patterns

**Test Rules on Selected Asset**
- Test which rules would apply to the selected asset
- Must select a project asset first

## Architecture

### Class Hierarchy

```
ImportRuleBase (abstract ScriptableObject)
├── MaterialRemapRule
└── [Future rule types...]
```

### How It Works

1. **Asset Import** - Unity imports or reimports a 3D model
2. **OnPreprocessModel** - ModelImportProcessor.OnPreprocessModel() is called
3. **Rule Discovery** - System finds all ImportRuleBase assets in the project
4. **Path Matching** - Each rule checks if its path patterns match the asset
5. **Rule Application** - Matching rules are applied in priority order
6. **Import Continues** - Unity continues with the configured import settings

## Extending the System

### Creating Custom Rule Types

1. Create a new class that inherits from `ImportRuleBase`
2. Implement the `ApplyRule()` method
3. Add `[CreateAssetMenu]` attribute for easy asset creation

**Example:**

```csharp
using UnityEngine;
using UnityEditor;

namespace Stephko.ModelImportProcessor
{
    [CreateAssetMenu(fileName = "New Animation Rule", menuName = "Stephko/Model Import Rules/Animation Rule")]
    public class AnimationImportRule : ImportRuleBase
    {
        public ModelImporterAnimationType animationType = ModelImporterAnimationType.Generic;
        public bool importAnimation = true;

        public override void ApplyRule(ModelImporter modelImporter, string assetPath)
        {
            modelImporter.importAnimation = importAnimation;
            modelImporter.animationType = animationType;
        }
    }
}
```

## API Reference

### ImportRuleBase

**Properties:**
- `bool enabled` - Enable/disable this rule
- `int priority` - Execution priority (0-100)
- `string[] pathPatterns` - Array of path patterns to match
- `bool useRegex` - Use regex instead of wildcards

**Methods:**
- `bool MatchesPath(string assetPath)` - Check if rule applies to path
- `abstract void ApplyRule(ModelImporter modelImporter, string assetPath)` - Apply the rule
- `string GetRuleDescription()` - Get debug description

### MaterialRemapRule

**Properties:**
- `ModelImporterMaterialImportMode materialImportMode`
- `ModelImporterMaterialLocation materialLocation`
- `bool enableSearchAndRemap`
- `ModelImporterMaterialName materialNameMode`
- `ModelImporterMaterialSearch materialSearchMode`
- `bool importMaterials`
- `bool verboseLogging`

### ModelImportProcessor

**Menu Items:**
- `Tools/Stephko/Model Import Processor/Refresh Rule Cache`
- `Tools/Stephko/Model Import Processor/List All Rules`
- `Tools/Stephko/Model Import Processor/Test Rules on Selected Asset`

## Troubleshooting

### Rules Not Being Applied

1. Check the rule is **Enabled**
2. Verify **Path Patterns** match your asset path
3. Use **Test Rules on Selected Asset** to debug
4. Check the Console for error messages
5. Try **Refresh Rule Cache** from the menu

### Material Remapping Not Working

1. Ensure `enableSearchAndRemap` is enabled
2. Check material naming matches `materialNameMode`
3. Verify materials exist in the search scope (`materialSearchMode`)
4. Enable `verboseLogging` to see detailed output
5. Check Unity documentation for material search behavior

### Performance Issues

- Rules are cached automatically - no need to worry about performance
- Cache is invalidated when project assets change
- Only matching rules are applied to each asset

## Unity API Documentation

This system is based on Unity's official ModelImporter API:

- [ModelImporter](https://docs.unity3d.com/ScriptReference/ModelImporter.html)
- [ModelImporter.SearchAndRemapMaterials](https://docs.unity3d.com/ScriptReference/ModelImporter.SearchAndRemapMaterials.html)
- [AssetPostprocessor](https://docs.unity3d.com/ScriptReference/AssetPostprocessor.html)
- [ModelImporterMaterialName](https://docs.unity3d.com/ScriptReference/ModelImporterMaterialName.html)
- [ModelImporterMaterialSearch](https://docs.unity3d.com/ScriptReference/ModelImporter-materialSearch.html)

## Future Enhancements

Planned features for future versions:

- **Animation Import Rules** - Configure animation import settings
- **Mesh Import Rules** - Control mesh optimization, normals, tangents
- **LOD Generation Rules** - Automatic LOD generation settings
- **Batch Rule Application** - Apply rules to existing models
- **Rule Templates** - Pre-configured rule templates for common workflows
- **Conditional Logic** - Apply rules based on file size, polygon count, etc.

## License & Credits

**Author:** Stephan Viranyi (Stephko)
**Email:** stephko@viranyi.de
**Portfolio:** https://www.artstation.com/stephko

Created with assistance from Claude AI (Anthropic).

---

**Version History:**

- **v1.0** (2026-01-03)
  - Initial release
  - MaterialRemapRule with full Unity material import API support
  - Path pattern matching with wildcards and regex
  - Priority system for rule ordering
  - Debug menu tools for testing and troubleshooting
