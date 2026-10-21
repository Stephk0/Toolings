// Export Lab: Unity ground truth for the FBX files of a run.
//
// Run by unity_dump.py:  Unity.exe -batchmode -projectPath <proj> -executeMethod LabDump.Run -quit
// Environment: LAB_OUT = output json path.
//
// Every .fbx under Assets/Lab is imported twice - Bake Axis Conversion off (the importer
// default) and on - and every node of the imported model is written out: Unity-space local
// TRS, world matrix, and the world-space bounds of its own mesh. Unity is left-handed; the
// numbers are written as Unity reports them (unity_dump.py does not convert them).
using System.Globalization;
using System.IO;
using System.Text;
using UnityEditor;
using UnityEngine;

public static class LabDump
{
    static readonly CultureInfo Inv = CultureInfo.InvariantCulture;

    static string F(float v) => v.ToString("0.#####", Inv);
    static string V(Vector3 v) => $"[{F(v.x)},{F(v.y)},{F(v.z)}]";
    static string Q(Quaternion q) => $"[{F(q.x)},{F(q.y)},{F(q.z)},{F(q.w)}]";
    static string Esc(string s) => s.Replace("\\", "\\\\").Replace("\"", "\\\"");

    public static void Run()
    {
        string outPath = System.Environment.GetEnvironmentVariable("LAB_OUT") ?? "lab_unity.json";
        string[] guids = AssetDatabase.FindAssets("t:Model", new[] { "Assets/Lab" });
        var sb = new StringBuilder();
        sb.Append("{\"unity\":\"").Append(Application.unityVersion).Append("\",\"variants\":{");
        bool firstVariant = true;
        foreach (bool bake in new[] { false, true })
        {
            foreach (string g in guids)
            {
                var imp = (ModelImporter)AssetImporter.GetAtPath(AssetDatabase.GUIDToAssetPath(g));
                if (imp.bakeAxisConversion != bake)
                {
                    imp.bakeAxisConversion = bake;
                    imp.SaveAndReimport();
                }
            }
            if (!firstVariant) sb.Append(',');
            firstVariant = false;
            sb.Append('"').Append(bake ? "bake_axis" : "default").Append("\":{");
            bool firstFile = true;
            foreach (string g in guids)
            {
                string path = AssetDatabase.GUIDToAssetPath(g);
                var root = AssetDatabase.LoadAssetAtPath<GameObject>(path);
                if (root == null) continue;
                if (!firstFile) sb.Append(',');
                firstFile = false;
                sb.Append('"').Append(Path.GetFileNameWithoutExtension(path)).Append("\":[");
                bool firstNode = true;
                foreach (var t in root.GetComponentsInChildren<Transform>(true))
                {
                    if (!firstNode) sb.Append(',');
                    firstNode = false;
                    sb.Append("{\"name\":\"").Append(Esc(t.name)).Append('"');
                    sb.Append(",\"parent\":").Append(t.parent ? "\"" + Esc(t.parent.name) + "\"" : "null");
                    sb.Append(",\"lp\":").Append(V(t.localPosition));
                    sb.Append(",\"lr\":").Append(Q(t.localRotation));
                    sb.Append(",\"ls\":").Append(V(t.localScale));
                    sb.Append(",\"wp\":").Append(V(t.position));
                    var mf = t.GetComponent<MeshFilter>();
                    if (mf && mf.sharedMesh)
                    {
                        var m = mf.sharedMesh;
                        var b = m.bounds;
                        var lo = new Vector3(float.MaxValue, float.MaxValue, float.MaxValue);
                        var hi = -lo;
                        for (int i = 0; i < 8; i++)
                        {
                            var c = b.center + Vector3.Scale(b.extents,
                                new Vector3((i & 1) == 0 ? -1 : 1, (i & 2) == 0 ? -1 : 1, (i & 4) == 0 ? -1 : 1));
                            var w = t.localToWorldMatrix.MultiplyPoint3x4(c);
                            lo = Vector3.Min(lo, w);
                            hi = Vector3.Max(hi, w);
                        }
                        sb.Append(",\"tris\":").Append(m.triangles.Length / 3);
                        sb.Append(",\"box\":[").Append(V(lo)).Append(',').Append(V(hi)).Append(']');
                        var r = t.GetComponent<Renderer>();
                        if (r)
                        {
                            sb.Append(",\"mats\":[");
                            for (int i = 0; i < r.sharedMaterials.Length; i++)
                            {
                                if (i > 0) sb.Append(',');
                                var mat = r.sharedMaterials[i];
                                sb.Append('"').Append(mat ? Esc(mat.name) : "").Append('"');
                            }
                            sb.Append(']');
                        }
                    }
                    sb.Append('}');
                }
                sb.Append(']');
            }
            sb.Append('}');
        }
        sb.Append("}}");
        File.WriteAllText(outPath, sb.ToString());
        Debug.Log($"[LabDump] {guids.Length} models x 2 variants -> {outPath}");
    }
}
