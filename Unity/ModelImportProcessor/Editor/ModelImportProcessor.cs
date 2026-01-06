using UnityEngine;
using UnityEditor;
using System.Collections.Generic;
using System.Linq;

namespace Stephko.ModelImportProcessor
{
    /// <summary>
    /// AssetPostprocessor that automatically applies import rules to 3D models based on ScriptableObject configurations.
    ///
    /// This processor scans the project for ImportRuleBase assets and applies matching rules to imported models
    /// during the preprocessing phase. Rules are applied in priority order (highest first).
    ///
    /// Usage:
    /// 1. Create rule assets (e.g., MaterialRemapRule) via Assets > Create > Stephko > Model Import Rules
    /// 2. Configure path patterns and settings for each rule
    /// 3. Rules are automatically applied when models are imported or reimported
    ///
    /// Documentation: https://docs.unity3d.com/ScriptReference/AssetPostprocessor.html
    /// </summary>
    public class ModelImportProcessor : AssetPostprocessor
    {
        // Cache for rule assets to avoid searching the AssetDatabase on every import
        private static List<ImportRuleBase> _cachedRules = null;
        private static bool _cacheValid = false;

        /// <summary>
        /// Enable/disable debug logging for the import processor.
        /// Toggle via: Tools > Stephko > Model Import Processor > Toggle Debug Logging
        /// </summary>
        private static bool _debugLogging = false;

        /// <summary>
        /// Called before the model is imported. This is where we apply our custom import rules.
        /// </summary>
        private void OnPreprocessModel()
        {
            // Get the ModelImporter for this asset
            ModelImporter modelImporter = assetImporter as ModelImporter;
            if (modelImporter == null)
            {
                Debug.LogWarning($"[ModelImportProcessor] AssetImporter is not a ModelImporter for: {assetPath}");
                return;
            }

            // Get all applicable rules for this asset
            List<ImportRuleBase> applicableRules = GetApplicableRules(assetPath);

            if (applicableRules.Count == 0)
            {
                if (_debugLogging)
                {
                    Debug.Log($"[ModelImportProcessor] No applicable rules found for: {assetPath}");
                }
                return;
            }

            // Apply rules in priority order (highest priority first)
            applicableRules = applicableRules.OrderByDescending(r => r.priority).ToList();

            if (_debugLogging)
            {
                Debug.Log($"[ModelImportProcessor] Applying {applicableRules.Count} rule(s) to: {assetPath}");
            }

            foreach (ImportRuleBase rule in applicableRules)
            {
                try
                {
                    if (_debugLogging)
                    {
                        Debug.Log($"[ModelImportProcessor] Applying rule '{rule.name}' (Priority: {rule.priority})");
                    }

                    rule.ApplyRule(modelImporter, assetPath);
                }
                catch (System.Exception e)
                {
                    Debug.LogError($"[ModelImportProcessor] Error applying rule '{rule.name}' to {assetPath}: {e.Message}\n{e.StackTrace}");
                }
            }
        }

        /// <summary>
        /// Called after the model is imported and the GameObject is created.
        /// This is where we apply collider setup rules that need to modify the imported GameObject hierarchy.
        /// </summary>
        private void OnPostprocessModel(GameObject root)
        {
            // Get all applicable rules for this asset
            List<ImportRuleBase> applicableRules = GetApplicableRules(assetPath);

            if (applicableRules.Count == 0)
                return;

            // Filter for ColliderSetupRule types and sort by priority
            List<ColliderSetupRule> colliderRules = applicableRules
                .OfType<ColliderSetupRule>()
                .OrderByDescending(r => r.priority)
                .ToList();

            if (colliderRules.Count == 0)
                return;

            if (_debugLogging)
            {
                Debug.Log($"[ModelImportProcessor] Applying {colliderRules.Count} collider rule(s) to: {assetPath}");
            }

            foreach (ColliderSetupRule rule in colliderRules)
            {
                try
                {
                    if (_debugLogging)
                    {
                        Debug.Log($"[ModelImportProcessor] Applying collider rule '{rule.name}' (Priority: {rule.priority})");
                    }

                    rule.ApplyColliders(root, assetPath);
                }
                catch (System.Exception e)
                {
                    Debug.LogError($"[ModelImportProcessor] Error applying collider rule '{rule.name}' to {assetPath}: {e.Message}\n{e.StackTrace}");
                }
            }
        }

        /// <summary>
        /// Get all import rules that match the given asset path.
        /// </summary>
        private List<ImportRuleBase> GetApplicableRules(string assetPath)
        {
            // Refresh rule cache if needed
            if (!_cacheValid || _cachedRules == null)
            {
                RefreshRuleCache();
            }

            // Find all rules that match this path
            List<ImportRuleBase> applicableRules = new List<ImportRuleBase>();

            foreach (ImportRuleBase rule in _cachedRules)
            {
                if (rule != null && rule.MatchesPath(assetPath))
                {
                    applicableRules.Add(rule);
                }
            }

            return applicableRules;
        }

        /// <summary>
        /// Refresh the cache of all ImportRuleBase assets in the project.
        /// </summary>
        private static void RefreshRuleCache()
        {
            _cachedRules = new List<ImportRuleBase>();

            // Find all ImportRuleBase assets in the project
            string[] guids = AssetDatabase.FindAssets($"t:{nameof(ImportRuleBase)}");

            foreach (string guid in guids)
            {
                string path = AssetDatabase.GUIDToAssetPath(guid);
                ImportRuleBase rule = AssetDatabase.LoadAssetAtPath<ImportRuleBase>(path);

                if (rule != null)
                {
                    _cachedRules.Add(rule);
                }
            }

            _cacheValid = true;

            if (_debugLogging)
            {
                Debug.Log($"[ModelImportProcessor] Refreshed rule cache: {_cachedRules.Count} rule(s) found");
            }
        }

        /// <summary>
        /// Invalidate the rule cache when assets are modified.
        /// This ensures we pick up newly created or modified rules.
        /// </summary>
        [InitializeOnLoadMethod]
        private static void Initialize()
        {
            // Invalidate cache when assets change
            EditorApplication.projectChanged += OnProjectChanged;

            // Initial cache refresh
            RefreshRuleCache();
        }

        private static void OnProjectChanged()
        {
            _cacheValid = false;
        }

        /// <summary>
        /// Menu item to manually refresh the rule cache (useful for debugging).
        /// </summary>
        [MenuItem("Tools/Stephko/Model Import Processor/Refresh Rule Cache")]
        private static void RefreshRuleCacheMenuItem()
        {
            RefreshRuleCache();
            Debug.Log($"[ModelImportProcessor] Rule cache refreshed: {_cachedRules.Count} rule(s) loaded");
        }

        /// <summary>
        /// Menu item to list all registered rules (useful for debugging).
        /// </summary>
        [MenuItem("Tools/Stephko/Model Import Processor/List All Rules")]
        private static void ListAllRulesMenuItem()
        {
            RefreshRuleCache();

            if (_cachedRules.Count == 0)
            {
                Debug.Log("[ModelImportProcessor] No import rules found in project");
                return;
            }

            Debug.Log($"[ModelImportProcessor] Found {_cachedRules.Count} import rule(s):");

            var sortedRules = _cachedRules.OrderByDescending(r => r.priority);

            foreach (ImportRuleBase rule in sortedRules)
            {
                if (rule != null)
                {
                    Debug.Log($"\n{rule.GetRuleDescription()}\n  Patterns: {string.Join(", ", rule.pathPatterns)}");
                }
            }
        }

        /// <summary>
        /// Menu item to test rules against a selected model asset.
        /// </summary>
        [MenuItem("Tools/Stephko/Model Import Processor/Test Rules on Selected Asset")]
        private static void TestRulesOnSelectedAsset()
        {
            if (Selection.activeObject == null)
            {
                Debug.LogWarning("[ModelImportProcessor] No asset selected. Please select a model asset in the Project window.");
                return;
            }

            string assetPath = AssetDatabase.GetAssetPath(Selection.activeObject);

            if (string.IsNullOrEmpty(assetPath))
            {
                Debug.LogWarning("[ModelImportProcessor] Selected object is not a project asset.");
                return;
            }

            RefreshRuleCache();

            List<ImportRuleBase> applicableRules = new List<ImportRuleBase>();

            foreach (ImportRuleBase rule in _cachedRules)
            {
                if (rule != null && rule.MatchesPath(assetPath))
                {
                    applicableRules.Add(rule);
                }
            }

            if (applicableRules.Count == 0)
            {
                Debug.Log($"[ModelImportProcessor] No rules match the selected asset: {assetPath}");
                return;
            }

            Debug.Log($"[ModelImportProcessor] Found {applicableRules.Count} matching rule(s) for: {assetPath}");

            var sortedRules = applicableRules.OrderByDescending(r => r.priority);

            foreach (ImportRuleBase rule in sortedRules)
            {
                Debug.Log($"\n{rule.GetRuleDescription()}");
            }
        }

        /// <summary>
        /// Menu item to toggle debug logging.
        /// </summary>
        [MenuItem("Tools/Stephko/Model Import Processor/Toggle Debug Logging")]
        private static void ToggleDebugLogging()
        {
            _debugLogging = !_debugLogging;
            Debug.Log($"[ModelImportProcessor] Debug logging {(_debugLogging ? "ENABLED" : "DISABLED")}");
        }

        /// <summary>
        /// Menu item validation to show current debug logging state.
        /// </summary>
        [MenuItem("Tools/Stephko/Model Import Processor/Toggle Debug Logging", true)]
        private static bool ToggleDebugLoggingValidate()
        {
            Menu.SetChecked("Tools/Stephko/Model Import Processor/Toggle Debug Logging", _debugLogging);
            return true;
        }
    }
}
