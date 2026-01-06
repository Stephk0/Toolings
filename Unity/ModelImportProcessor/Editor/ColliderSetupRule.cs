using UnityEngine;
using UnityEditor;

namespace Stephko.ModelImportProcessor
{
    /// <summary>
    /// Collider setup rule for model imports.
    /// Automatically adds colliders to child meshes based on naming conventions (suffixes).
    ///
    /// Supported Patterns:
    /// - _COL: Adds MeshCollider (convex or non-convex)
    /// - _COLCUBE / _COLBOX: Adds BoxCollider matching mesh bounds
    /// - _COLSPHERE: Adds SphereCollider matching mesh bounds
    /// - _COLCAPSULE: Adds CapsuleCollider matching mesh bounds
    ///
    /// Inspired by Unreal Engine naming conventions (UCX_, UBX_, USP_, UCP_)
    ///
    /// Documentation:
    /// - https://docs.unity3d.com/ScriptReference/AssetPostprocessor.OnPostprocessModel.html
    /// - https://bronsonzgeb.com/index.php/2021/11/27/better-collider-generation-with-asset-processors/
    /// </summary>
    [CreateAssetMenu(fileName = "New Collider Setup Rule", menuName = "Stephko/Model Import Rules/Collider Setup Rule", order = 2)]
    public class ColliderSetupRule : ImportRuleBase
    {
        [Header("Collider Suffix Patterns")]
        [Tooltip("Suffix for mesh colliders (e.g., '_COL')")]
        public string meshColliderSuffix = "_COL";

        [Tooltip("Suffix for box colliders (e.g., '_COLCUBE' or '_COLBOX')")]
        public string[] boxColliderSuffixes = new string[] { "_COLCUBE", "_COLBOX" };

        [Tooltip("Suffix for sphere colliders (e.g., '_COLSPHERE')")]
        public string[] sphereColliderSuffixes = new string[] { "_COLSPHERE", "_COLSPH" };

        [Tooltip("Suffix for capsule colliders (e.g., '_COLCAPSULE')")]
        public string[] capsuleColliderSuffixes = new string[] { "_COLCAPSULE", "_COLCAP" };

        [Header("Mesh Collider Settings")]
        [Tooltip("Make mesh colliders convex (required for rigidbody collision)")]
        public bool meshColliderConvex = true;

        [Tooltip("Enable collision cooking for mesh colliders (better performance)")]
        public bool meshColliderCookingOptions = true;

        [Header("Mesh Handling")]
        [Tooltip("Hide the original collision mesh (disable MeshRenderer)")]
        public bool hideCollisionMesh = true;

        [Tooltip("Remove the collision mesh from the hierarchy after setup")]
        public bool removeCollisionMeshGameObject = false;

        [Header("Advanced Options")]
        [Tooltip("Case-insensitive suffix matching")]
        public bool caseInsensitive = true;

        [Tooltip("Log detailed information when colliders are added")]
        public bool verboseLogging = false;

        /// <summary>
        /// Apply rule is called during preprocessing, but collider setup happens in postprocessing.
        /// This method stores configuration that will be used in OnPostprocessModel.
        /// </summary>
        public override void ApplyRule(ModelImporter modelImporter, string assetPath)
        {
            // For collider setup, the actual work happens in ApplyColliders() called from OnPostprocessModel
            // This method can be used to set ModelImporter properties if needed
            if (verboseLogging)
            {
                Debug.Log($"[{name}] Collider setup rule will be applied in post-processing for: {assetPath}");
            }
        }

        /// <summary>
        /// Apply collider setup to the imported GameObject hierarchy.
        /// Called from OnPostprocessModel in the ModelImportProcessor.
        /// </summary>
        /// <param name="root">The root GameObject of the imported model</param>
        /// <param name="assetPath">The asset path being imported</param>
        public void ApplyColliders(GameObject root, string assetPath)
        {
            if (root == null)
            {
                Debug.LogError($"[{name}] Root GameObject is null for asset: {assetPath}");
                return;
            }

            if (verboseLogging)
            {
                Debug.Log($"[{name}] Processing colliders for: {assetPath}");
            }

            int collidersAdded = 0;

            // Recursively process all transforms in the hierarchy
            ProcessTransform(root.transform, assetPath, ref collidersAdded);

            if (verboseLogging || collidersAdded > 0)
            {
                Debug.Log($"[{name}] Added {collidersAdded} collider(s) to: {assetPath}");
            }
        }

        /// <summary>
        /// Recursively process a transform and its children.
        /// </summary>
        private void ProcessTransform(Transform transform, string assetPath, ref int collidersAdded)
        {
            // Check current transform
            ProcessSingleTransform(transform, assetPath, ref collidersAdded);

            // Process children
            foreach (Transform child in transform)
            {
                ProcessTransform(child, assetPath, ref collidersAdded);
            }
        }

        /// <summary>
        /// Process a single transform, checking for collision mesh naming and adding appropriate colliders.
        /// </summary>
        private void ProcessSingleTransform(Transform transform, string assetPath, ref int collidersAdded)
        {
            string objectName = transform.name;
            GameObject gameObject = transform.gameObject;

            // Check for mesh collider suffix
            if (MatchesSuffix(objectName, meshColliderSuffix))
            {
                AddMeshCollider(gameObject, objectName, assetPath);
                collidersAdded++;
                return;
            }

            // Check for box collider suffixes
            foreach (string suffix in boxColliderSuffixes)
            {
                if (MatchesSuffix(objectName, suffix))
                {
                    AddBoxCollider(gameObject, objectName, assetPath);
                    collidersAdded++;
                    return;
                }
            }

            // Check for sphere collider suffixes
            foreach (string suffix in sphereColliderSuffixes)
            {
                if (MatchesSuffix(objectName, suffix))
                {
                    AddSphereCollider(gameObject, objectName, assetPath);
                    collidersAdded++;
                    return;
                }
            }

            // Check for capsule collider suffixes
            foreach (string suffix in capsuleColliderSuffixes)
            {
                if (MatchesSuffix(objectName, suffix))
                {
                    AddCapsuleCollider(gameObject, objectName, assetPath);
                    collidersAdded++;
                    return;
                }
            }
        }

        /// <summary>
        /// Check if object name matches the given suffix.
        /// </summary>
        private bool MatchesSuffix(string objectName, string suffix)
        {
            if (string.IsNullOrEmpty(suffix))
                return false;

            if (caseInsensitive)
            {
                return objectName.ToUpper().EndsWith(suffix.ToUpper());
            }
            else
            {
                return objectName.EndsWith(suffix);
            }
        }

        /// <summary>
        /// Add a MeshCollider to the GameObject.
        /// </summary>
        private void AddMeshCollider(GameObject gameObject, string objectName, string assetPath)
        {
            MeshFilter meshFilter = gameObject.GetComponent<MeshFilter>();
            if (meshFilter == null || meshFilter.sharedMesh == null)
            {
                Debug.LogWarning($"[{name}] Cannot add MeshCollider to '{objectName}' - no MeshFilter found");
                return;
            }

            MeshCollider collider = gameObject.AddComponent<MeshCollider>();
            collider.sharedMesh = meshFilter.sharedMesh;
            collider.convex = meshColliderConvex;

            if (verboseLogging)
            {
                Debug.Log($"[{name}] Added MeshCollider (convex={meshColliderConvex}) to: {objectName}");
            }

            HandleMeshVisibility(gameObject, objectName);
        }

        /// <summary>
        /// Add a BoxCollider to the GameObject, sized to match the mesh bounds.
        /// </summary>
        private void AddBoxCollider(GameObject gameObject, string objectName, string assetPath)
        {
            MeshFilter meshFilter = gameObject.GetComponent<MeshFilter>();
            if (meshFilter == null || meshFilter.sharedMesh == null)
            {
                Debug.LogWarning($"[{name}] Cannot add BoxCollider to '{objectName}' - no MeshFilter found");
                return;
            }

            BoxCollider collider = gameObject.AddComponent<BoxCollider>();

            // Match the box collider to the mesh bounds
            Bounds bounds = meshFilter.sharedMesh.bounds;
            collider.center = bounds.center;
            collider.size = bounds.size;

            if (verboseLogging)
            {
                Debug.Log($"[{name}] Added BoxCollider (size={bounds.size}) to: {objectName}");
            }

            HandleMeshVisibility(gameObject, objectName);
        }

        /// <summary>
        /// Add a SphereCollider to the GameObject, sized to match the mesh bounds.
        /// </summary>
        private void AddSphereCollider(GameObject gameObject, string objectName, string assetPath)
        {
            MeshFilter meshFilter = gameObject.GetComponent<MeshFilter>();
            if (meshFilter == null || meshFilter.sharedMesh == null)
            {
                Debug.LogWarning($"[{name}] Cannot add SphereCollider to '{objectName}' - no MeshFilter found");
                return;
            }

            SphereCollider collider = gameObject.AddComponent<SphereCollider>();

            // Match the sphere collider to the mesh bounds (use max extent as radius)
            Bounds bounds = meshFilter.sharedMesh.bounds;
            collider.center = bounds.center;
            collider.radius = Mathf.Max(bounds.extents.x, bounds.extents.y, bounds.extents.z);

            if (verboseLogging)
            {
                Debug.Log($"[{name}] Added SphereCollider (radius={collider.radius}) to: {objectName}");
            }

            HandleMeshVisibility(gameObject, objectName);
        }

        /// <summary>
        /// Add a CapsuleCollider to the GameObject, sized to match the mesh bounds.
        /// </summary>
        private void AddCapsuleCollider(GameObject gameObject, string objectName, string assetPath)
        {
            MeshFilter meshFilter = gameObject.GetComponent<MeshFilter>();
            if (meshFilter == null || meshFilter.sharedMesh == null)
            {
                Debug.LogWarning($"[{name}] Cannot add CapsuleCollider to '{objectName}' - no MeshFilter found");
                return;
            }

            CapsuleCollider collider = gameObject.AddComponent<CapsuleCollider>();

            // Match the capsule collider to the mesh bounds
            // Use the longest axis as the capsule direction
            Bounds bounds = meshFilter.sharedMesh.bounds;
            collider.center = bounds.center;

            Vector3 size = bounds.size;
            if (size.y >= size.x && size.y >= size.z)
            {
                // Y-axis (default)
                collider.direction = 1;
                collider.height = size.y;
                collider.radius = Mathf.Max(size.x, size.z) * 0.5f;
            }
            else if (size.x >= size.y && size.x >= size.z)
            {
                // X-axis
                collider.direction = 0;
                collider.height = size.x;
                collider.radius = Mathf.Max(size.y, size.z) * 0.5f;
            }
            else
            {
                // Z-axis
                collider.direction = 2;
                collider.height = size.z;
                collider.radius = Mathf.Max(size.x, size.y) * 0.5f;
            }

            if (verboseLogging)
            {
                Debug.Log($"[{name}] Added CapsuleCollider (height={collider.height}, radius={collider.radius}) to: {objectName}");
            }

            HandleMeshVisibility(gameObject, objectName);
        }

        /// <summary>
        /// Handle mesh visibility based on rule settings.
        /// </summary>
        private void HandleMeshVisibility(GameObject gameObject, string objectName)
        {
            if (hideCollisionMesh)
            {
                MeshRenderer meshRenderer = gameObject.GetComponent<MeshRenderer>();
                if (meshRenderer != null)
                {
                    meshRenderer.enabled = false;

                    if (verboseLogging)
                    {
                        Debug.Log($"[{name}] Hidden MeshRenderer for: {objectName}");
                    }
                }
            }

            if (removeCollisionMeshGameObject)
            {
                // Mark for destruction (will be removed after import completes)
                Object.DestroyImmediate(gameObject);

                if (verboseLogging)
                {
                    Debug.Log($"[{name}] Removed GameObject: {objectName}");
                }
            }
        }

        public override string GetRuleDescription()
        {
            string desc = base.GetRuleDescription();
            desc += $"\n  Mesh Suffix: '{meshColliderSuffix}' (Convex: {meshColliderConvex})";
            desc += $"\n  Box Suffixes: {string.Join(", ", boxColliderSuffixes)}";
            desc += $"\n  Sphere Suffixes: {string.Join(", ", sphereColliderSuffixes)}";
            desc += $"\n  Capsule Suffixes: {string.Join(", ", capsuleColliderSuffixes)}";
            desc += $"\n  Hide Mesh: {hideCollisionMesh}, Remove GameObject: {removeCollisionMeshGameObject}";
            return desc;
        }

        private void OnValidate()
        {
            // Ensure at least one path pattern exists
            if (pathPatterns == null || pathPatterns.Length == 0)
            {
                pathPatterns = new string[] { "Assets/**" };
            }

            // Ensure suffixes arrays are initialized
            if (boxColliderSuffixes == null || boxColliderSuffixes.Length == 0)
            {
                boxColliderSuffixes = new string[] { "_COLCUBE", "_COLBOX" };
            }
            if (sphereColliderSuffixes == null || sphereColliderSuffixes.Length == 0)
            {
                sphereColliderSuffixes = new string[] { "_COLSPHERE", "_COLSPH" };
            }
            if (capsuleColliderSuffixes == null || capsuleColliderSuffixes.Length == 0)
            {
                capsuleColliderSuffixes = new string[] { "_COLCAPSULE", "_COLCAP" };
            }
        }
    }
}
