# Unity Model Import Processor - System Architecture

## Overview

The Model Import Processor is a **rule-based asset pipeline extension** that automatically configures model import settings based on ScriptableObject rules. It uses Unity's `AssetPostprocessor` system to intercept model imports and apply custom settings.

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                      Unity Asset Pipeline                   │
└───────────────────────┬─────────────────────────────────────┘
                        │
                        ▼
        ┌───────────────────────────────┐
        │   Model File Imported (.fbx)  │
        └───────────────┬───────────────┘
                        │
                        ▼
        ┌───────────────────────────────────────┐
        │   ModelImportProcessor (AssetPP)      │
        │   - OnPreprocessModel() triggered     │
        │   - Scans for applicable rules        │
        └───────────────┬───────────────────────┘
                        │
                        ▼
        ┌───────────────────────────────────────┐
        │   Rule Discovery & Caching            │
        │   - Load all ImportRuleBase assets    │
        │   - Cache for performance             │
        │   - Invalidate on project change      │
        └───────────────┬───────────────────────┘
                        │
                        ▼
        ┌───────────────────────────────────────┐
        │   Path Matching                       │
        │   - Test each rule's pathPatterns     │
        │   - Wildcard or Regex matching        │
        │   - Build list of applicable rules    │
        └───────────────┬───────────────────────┘
                        │
                        ▼
        ┌───────────────────────────────────────┐
        │   Priority Sorting                    │
        │   - Sort by priority (high to low)    │
        │   - Higher priority = executes first  │
        └───────────────┬───────────────────────┘
                        │
                        ▼
        ┌───────────────────────────────────────┐
        │   Rule Application                    │
        │   - Call ApplyRule() on each rule     │
        │   - Configure ModelImporter           │
        │   - Later rules can override earlier  │
        └───────────────┬───────────────────────┘
                        │
                        ▼
        ┌───────────────────────────────────────┐
        │   Unity Continues Import              │
        │   - Uses configured settings          │
        │   - Imports materials, mesh, etc.     │
        └───────────────────────────────────────┘
```

## Class Hierarchy

```
UnityEngine.ScriptableObject
    │
    └─── ImportRuleBase (abstract)
            │
            ├─── MaterialRemapRule
            │
            └─── [Future rule types]
                 ├─── AnimationImportRule (planned)
                 ├─── MeshImportRule (planned)
                 └─── LODGenerationRule (planned)

UnityEditor.AssetPostprocessor
    │
    └─── ModelImportProcessor
```

## Core Components

### 1. ImportRuleBase (Abstract ScriptableObject)

**Responsibility:** Base class for all import rules

**Key Members:**
```csharp
// Configuration
public bool enabled
public int priority (0-100)
public string[] pathPatterns
public bool useRegex

// Methods
public virtual bool MatchesPath(string assetPath)
public abstract void ApplyRule(ModelImporter importer, string assetPath)
public virtual string GetRuleDescription()

// Internal
private bool MatchesWildcard(string path, string pattern)
```

**Pattern Matching Logic:**
- Supports wildcard patterns: `*` (any chars), `**` (recursive), `?` (single char)
- Optional regex mode for advanced patterns
- Normalizes path separators to forward slashes
- Case-insensitive matching

### 2. MaterialRemapRule (ScriptableObject)

**Responsibility:** Configure material import and remapping settings

**Key Members:**
```csharp
// Material Import Settings
public ModelImporterMaterialImportMode materialImportMode
public ModelImporterMaterialLocation materialLocation

// Material Remapping
public bool enableSearchAndRemap
public ModelImporterMaterialName materialNameMode
public ModelImporterMaterialSearch materialSearchMode

// Advanced
public bool importMaterials
public bool verboseLogging
```

**Unity API Mapping:**
```csharp
ApplyRule(ModelImporter importer, string assetPath):
    importer.importMaterials = importMaterials
    importer.materialImportMode = materialImportMode
    importer.materialLocation = materialLocation
    importer.materialName = materialNameMode
    importer.materialSearch = materialSearchMode

    if (enableSearchAndRemap):
        importer.SearchAndRemapMaterials(materialNameMode, materialSearchMode)
```

**Options Reference:**

| Property | Enum Type | Values |
|----------|-----------|--------|
| materialImportMode | ModelImporterMaterialImportMode | None, ImportStandard, ImportViaMaterialDescription |
| materialLocation | ModelImporterMaterialLocation | External, InPrefab |
| materialNameMode | ModelImporterMaterialName | BasedOnTextureName(0), BasedOnMaterialName(1), BasedOnModelNameAndMaterialName(2) |
| materialSearchMode | ModelImporterMaterialSearch | Local(0), RecursiveUp(1), Everywhere(2) |

### 3. ModelImportProcessor (AssetPostprocessor)

**Responsibility:** Intercept model imports and apply rules

**Key Members:**
```csharp
// Lifecycle
private void OnPreprocessModel()
[InitializeOnLoadMethod] private static void Initialize()
private static void OnProjectChanged()

// Rule Management
private static List<ImportRuleBase> _cachedRules
private static bool _cacheValid
private static void RefreshRuleCache()
private List<ImportRuleBase> GetApplicableRules(string assetPath)

// Debug Tools
[MenuItem] private static void RefreshRuleCacheMenuItem()
[MenuItem] private static void ListAllRulesMenuItem()
[MenuItem] private static void TestRulesOnSelectedAsset()
```

**Execution Flow:**
```
OnPreprocessModel()
    │
    ├─ Get ModelImporter from assetImporter
    │
    ├─ GetApplicableRules(assetPath)
    │   │
    │   ├─ RefreshRuleCache() if needed
    │   │   └─ AssetDatabase.FindAssets("t:ImportRuleBase")
    │   │
    │   └─ For each cached rule:
    │       └─ if rule.MatchesPath(assetPath): add to list
    │
    ├─ Sort rules by priority (descending)
    │
    └─ For each applicable rule:
        └─ try: rule.ApplyRule(modelImporter, assetPath)
           catch: log error
```

## Performance Optimization

### Rule Caching
- Rules are loaded once and cached in static memory
- Cache invalidated on:
  - Project asset changes (`EditorApplication.projectChanged`)
  - Manual refresh via menu
- Prevents repeated `AssetDatabase.FindAssets()` calls

### Cache Invalidation Strategy
```csharp
[InitializeOnLoadMethod]
static void Initialize():
    EditorApplication.projectChanged += OnProjectChanged
    RefreshRuleCache()

static void OnProjectChanged():
    _cacheValid = false
    // Cache rebuilt on next import
```

### Path Matching Optimization
- Compiled regex patterns are not cached (could be added in future)
- Wildcard matching converts to regex once per pattern
- Early exit on first match (when checking if rule applies)

## Extension Points

### Creating New Rule Types

**Step 1:** Inherit from ImportRuleBase
```csharp
public class MyCustomRule : ImportRuleBase
{
    public override void ApplyRule(ModelImporter importer, string assetPath)
    {
        // Configure importer settings
    }
}
```

**Step 2:** Add CreateAssetMenu attribute
```csharp
[CreateAssetMenu(fileName = "New Custom Rule",
                 menuName = "Stephko/Model Import Rules/Custom Rule")]
```

**Step 3:** Add custom properties
```csharp
[Header("Custom Settings")]
public bool myCustomSetting = true;
```

**Step 4:** Implement ApplyRule()
```csharp
public override void ApplyRule(ModelImporter importer, string assetPath)
{
    // Access any ModelImporter property:
    importer.importAnimation = myCustomSetting;
    importer.animationType = ModelImporterAnimationType.Generic;
    // ... etc
}
```

### Available ModelImporter Properties

Common properties you can configure in custom rules:

**Meshes:**
- `importBlendShapes`, `importVisibility`, `importCameras`, `importLights`
- `meshCompression`, `isReadable`, `optimizeMesh`, `addCollider`
- `keepQuads`, `weldVertices`, `indexFormat`

**Normals & Tangents:**
- `importNormals`, `normalCalculationMode`, `normalSmoothingAngle`
- `importTangents`, `tangentImportMode`

**Animations:**
- `importAnimation`, `animationType`, `animationCompression`
- `clipAnimations`, `extraExposedTransformPaths`

**LOD:**
- `isUseFileUnitsSupported`, `useFileUnits`, `fileScale`, `globalScale`

See [Unity ModelImporter API](https://docs.unity3d.com/ScriptReference/ModelImporter.html) for complete list.

## Data Flow Example

### Scenario: Import Character Model

**Setup:**
```
File: Assets/Models/Characters/Hero/hero.fbx
Rule: "Character Material Remap"
  - pathPatterns: ["Assets/Models/Characters/**"]
  - priority: 50
  - enabled: true
  - materialNameMode: BasedOnMaterialName
  - materialSearchMode: RecursiveUp
```

**Execution:**
```
1. Unity detects hero.fbx import

2. ModelImportProcessor.OnPreprocessModel() called
   - assetPath = "Assets/Models/Characters/Hero/hero.fbx"
   - assetImporter casted to ModelImporter

3. GetApplicableRules("Assets/Models/Characters/Hero/hero.fbx")
   - Load cached rules (or refresh if needed)
   - Test "Character Material Remap" rule:
     - MatchesPath("Assets/Models/Characters/Hero/hero.fbx")
       - Pattern: "Assets/Models/Characters/**"
       - Regex: "^Assets/Models/Characters/.*$"
       - Match: TRUE ✓
   - Add to applicableRules list

4. Sort applicableRules by priority
   - [0]: "Character Material Remap" (priority: 50)

5. Apply rules
   - ApplyRule(modelImporter, assetPath)
     - modelImporter.materialImportMode = ImportViaMaterialDescription
     - modelImporter.materialLocation = External
     - modelImporter.materialName = BasedOnMaterialName
     - modelImporter.materialSearch = RecursiveUp
     - modelImporter.SearchAndRemapMaterials(
         BasedOnMaterialName,
         RecursiveUp
       )
       - Unity searches:
         - Assets/Models/Characters/Hero/Materials/
         - Assets/Models/Characters/Materials/
         - Assets/Models/Materials/
         - Assets/Materials/
       - Finds and remaps materials

6. Unity continues import with configured settings
```

## Error Handling

### Rule Application Errors
```csharp
try {
    rule.ApplyRule(modelImporter, assetPath);
} catch (Exception e) {
    Debug.LogError($"[ModelImportProcessor] Error applying rule '{rule.name}'
                    to {assetPath}: {e.Message}\n{e.StackTrace}");
}
```
- Errors logged but don't stop processing
- Other rules still execute
- Import continues with default/partial settings

### Invalid Regex Patterns
```csharp
try {
    if (Regex.IsMatch(assetPath, pattern, RegexOptions.IgnoreCase))
        return true;
} catch (Exception e) {
    Debug.LogError($"Invalid regex pattern '{pattern}' in rule '{name}': {e.Message}");
}
```
- Invalid patterns are logged
- Processing continues with other patterns
- Rule can still match via other valid patterns

## Thread Safety

**Not Thread-Safe** - Designed for Unity's single-threaded import pipeline
- `_cachedRules` accessed from main thread only
- `OnPreprocessModel()` called synchronously during import
- No concurrent access to rule cache

**Note:** Unity's parallel import feature imports different assets in parallel, but each asset's import is single-threaded. Multiple ModelImportProcessor instances may run concurrently for different assets, but they all read from the same static `_cachedRules` (read-only access is safe).

## File Structure

```
Unity/ModelImportProcessor/
│
├── Editor/                          # Editor-only scripts
│   ├── ImportRuleBase.cs            # Abstract base class
│   ├── MaterialRemapRule.cs         # Material remapping rule
│   └── ModelImportProcessor.cs      # AssetPostprocessor
│
├── ExampleRules/                    # Example configurations
│   └── CharacterMaterialRemapRule_TEMPLATE.txt
│
├── README.md                        # Full documentation
├── QUICK_REFERENCE.md               # Quick reference guide
├── CHANGELOG.md                     # Version history
└── SYSTEM_ARCHITECTURE.md           # This file
```

## Unity Integration

### Menu Structure
```
Tools/
└── Stephko/
    └── Model Import Processor/
        ├── Refresh Rule Cache
        ├── List All Rules
        └── Test Rules on Selected Asset
```

### Asset Creation Menu
```
Assets/
└── Create/
    └── Stephko/
        └── Model Import Rules/
            └── Material Remap Rule
```

## Dependencies

**Unity APIs:**
- `UnityEngine.ScriptableObject`
- `UnityEditor.AssetPostprocessor`
- `UnityEditor.ModelImporter`
- `UnityEditor.AssetDatabase`
- `UnityEditor.EditorApplication`

**System APIs:**
- `System.Text.RegularExpressions.Regex`
- `System.Linq`
- `System.Collections.Generic`

**No External Dependencies** - Pure Unity/C# implementation

## References

- [Unity ModelImporter](https://docs.unity3d.com/ScriptReference/ModelImporter.html)
- [Unity AssetPostprocessor](https://docs.unity3d.com/ScriptReference/AssetPostprocessor.html)
- [Unity SearchAndRemapMaterials](https://docs.unity3d.com/ScriptReference/ModelImporter.SearchAndRemapMaterials.html)
- [Unity ScriptableObject](https://docs.unity3d.com/Manual/class-ScriptableObject.html)

---

**Author:** Stephan Viranyi (Stephko)
**Version:** 1.0.0
**Date:** 2026-01-03
