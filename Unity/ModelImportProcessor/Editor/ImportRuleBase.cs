using UnityEngine;
using System.Text.RegularExpressions;

namespace Stephko.ModelImportProcessor
{
    /// <summary>
    /// Base class for all model import rules.
    /// Import rules are ScriptableObjects that define processing logic for imported models based on path patterns.
    /// </summary>
    public abstract class ImportRuleBase : ScriptableObject
    {
        [Header("Rule Settings")]
        [Tooltip("Enable or disable this rule")]
        public bool enabled = true;

        [Tooltip("Priority order (higher values execute first)")]
        [Range(0, 100)]
        public int priority = 50;

        [Header("Path Matching")]
        [Tooltip("Path patterns to match (supports wildcards: * for any characters, ** for recursive directory matching)\nExamples:\n- Assets/Models/Characters/**\n- Assets/Art/Props/*.fbx\n- Assets/**/*_LOD*.fbx")]
        public string[] pathPatterns = new string[] { "Assets/**" };

        [Tooltip("Use regex instead of wildcard patterns")]
        public bool useRegex = false;

        /// <summary>
        /// Check if this rule applies to the given asset path.
        /// </summary>
        /// <param name="assetPath">The asset path to check</param>
        /// <returns>True if the rule should be applied to this asset</returns>
        public virtual bool MatchesPath(string assetPath)
        {
            if (!enabled || pathPatterns == null || pathPatterns.Length == 0)
                return false;

            // Normalize path separators to forward slashes
            assetPath = assetPath.Replace('\\', '/');

            foreach (string pattern in pathPatterns)
            {
                if (string.IsNullOrWhiteSpace(pattern))
                    continue;

                if (useRegex)
                {
                    try
                    {
                        if (Regex.IsMatch(assetPath, pattern, RegexOptions.IgnoreCase))
                            return true;
                    }
                    catch (System.Exception e)
                    {
                        Debug.LogError($"Invalid regex pattern '{pattern}' in rule '{name}': {e.Message}");
                    }
                }
                else
                {
                    if (MatchesWildcard(assetPath, pattern))
                        return true;
                }
            }

            return false;
        }

        /// <summary>
        /// Apply this rule to the model importer.
        /// Override this method in derived classes to implement specific rule logic.
        /// </summary>
        /// <param name="modelImporter">The ModelImporter to configure</param>
        /// <param name="assetPath">The path of the asset being imported</param>
        public abstract void ApplyRule(UnityEditor.ModelImporter modelImporter, string assetPath);

        /// <summary>
        /// Wildcard pattern matching with support for * and ** (recursive directory matching).
        /// </summary>
        private bool MatchesWildcard(string path, string pattern)
        {
            // Normalize pattern separators
            pattern = pattern.Replace('\\', '/');

            // Convert wildcard pattern to regex
            string regexPattern = "^" + Regex.Escape(pattern)
                .Replace("\\*\\*/", ".*?/")  // ** matches any directory recursively
                .Replace("\\*\\*", ".*")      // ** at end matches everything
                .Replace("\\*", "[^/]*")      // * matches anything except directory separator
                .Replace("\\?", ".")          // ? matches single character
                + "$";

            return Regex.IsMatch(path, regexPattern, RegexOptions.IgnoreCase);
        }

        /// <summary>
        /// Get a description of this rule for debugging purposes.
        /// </summary>
        public virtual string GetRuleDescription()
        {
            return $"{GetType().Name} (Priority: {priority}, Enabled: {enabled})";
        }
    }
}
