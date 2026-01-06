using UnityEngine;
using UnityEditor;

namespace Stephko.ModelImportProcessor
{
    /// <summary>
    /// Material remapping rule for model imports.
    /// Controls how materials are imported, named, searched, and remapped based on Unity's ModelImporter material settings.
    ///
    /// Documentation: https://docs.unity3d.com/ScriptReference/ModelImporter.SearchAndRemapMaterials.html
    /// </summary>
    [CreateAssetMenu(fileName = "New Material Remap Rule", menuName = "Stephko/Model Import Rules/Material Remap Rule", order = 1)]
    public class MaterialRemapRule : ImportRuleBase
    {
        [Header("Material Import Settings")]
        [Tooltip("Material creation mode:\n" +
                 "- None: Do not import materials\n" +
                 "- ImportStandard: Use standard material import (Legacy)\n" +
                 "- ImportViaMaterialDescription: Use MaterialDescription preprocessing")]
        public ModelImporterMaterialImportMode materialImportMode = ModelImporterMaterialImportMode.ImportViaMaterialDescription;

        [Tooltip("Material storage location:\n" +
                 "- External: Use external materials if found in project (Legacy)\n" +
                 "- InPrefab: Embed materials inside the imported asset")]
        public ModelImporterMaterialLocation materialLocation = ModelImporterMaterialLocation.InPrefab;

        [Header("Material Remapping")]
        [Tooltip("Enable automatic material remapping using SearchAndRemapMaterials()")]
        public bool enableSearchAndRemap = true;

        [Tooltip("Material naming convention:\n" +
                 "- BasedOnTextureName (0): <textureName>.mat or <materialName>.mat if no diffuse texture\n" +
                 "- BasedOnMaterialName (1): <materialName>.mat\n" +
                 "- BasedOnModelNameAndMaterialName (2): <modelName>-<materialName>.mat\n" +
                 "- BasedOnTextureName_Or_ModelNameAndMaterialName (3): Obsolete, fallback option")]
        public ModelImporterMaterialName materialNameMode = ModelImporterMaterialName.BasedOnMaterialName;

        [Tooltip("Material search scope:\n" +
                 "- Local (0): Search only in local Materials folder\n" +
                 "- RecursiveUp (1): Search recursively up through Materials folders to Assets root\n" +
                 "- Everywhere (2): Search anywhere inside the Assets folder")]
        public ModelImporterMaterialSearch materialSearchMode = ModelImporterMaterialSearch.RecursiveUp;

        [Header("Advanced Options")]
        [Tooltip("Log detailed information when this rule is applied")]
        public bool verboseLogging = false;

        public override void ApplyRule(ModelImporter modelImporter, string assetPath)
        {
            if (modelImporter == null)
            {
                Debug.LogError($"[{name}] ModelImporter is null for asset: {assetPath}");
                return;
            }

            if (verboseLogging)
            {
                Debug.Log($"[{name}] Applying material remap rule to: {assetPath}\n" +
                         $"  Import Mode: {materialImportMode}\n" +
                         $"  Location: {materialLocation}\n" +
                         $"  Name Mode: {materialNameMode}\n" +
                         $"  Search Mode: {materialSearchMode}\n" +
                         $"  Search & Remap: {enableSearchAndRemap}");
            }

            // Apply material import settings
            modelImporter.materialImportMode = materialImportMode;
            modelImporter.materialLocation = materialLocation;
            modelImporter.materialName = materialNameMode;
            modelImporter.materialSearch = materialSearchMode;

            // Apply SearchAndRemapMaterials if enabled and not in None mode
            if (enableSearchAndRemap && materialImportMode != ModelImporterMaterialImportMode.None)
            {
                bool success = modelImporter.SearchAndRemapMaterials(materialNameMode, materialSearchMode);

                if (verboseLogging)
                {
                    if (success)
                    {
                        Debug.Log($"[{name}] Successfully remapped materials for: {assetPath}");
                    }
                    else
                    {
                        Debug.LogWarning($"[{name}] Failed to remap materials for: {assetPath} (source file may be invalid or corrupted)");
                    }
                }
            }
            else if (verboseLogging && materialImportMode == ModelImporterMaterialImportMode.None)
            {
                Debug.Log($"[{name}] Material import disabled (mode = None) for: {assetPath}");
            }
        }

        public override string GetRuleDescription()
        {
            string desc = base.GetRuleDescription();
            desc += $"\n  Mode: {materialImportMode}";

            if (materialImportMode != ModelImporterMaterialImportMode.None)
            {
                desc += $"\n  Location: {materialLocation}";
                desc += $"\n  Name: {materialNameMode}";
                desc += $"\n  Search: {materialSearchMode}";
                desc += $"\n  Auto-Remap: {enableSearchAndRemap}";
            }
            return desc;
        }

        private void OnValidate()
        {
            // Ensure at least one path pattern exists
            if (pathPatterns == null || pathPatterns.Length == 0)
            {
                pathPatterns = new string[] { "Assets/**" };
            }
        }
    }
}
