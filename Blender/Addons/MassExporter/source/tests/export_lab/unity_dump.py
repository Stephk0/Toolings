"""Import every FBX of a run into Unity (batch mode) and record what Unity makes of it.

    python unity_dump.py <out_dir> <unity_project_dir> [--unity <Unity.exe>]

Creates the throwaway Unity project on first use, copies blobs/*.fbx into Assets/Lab, runs
unity/LabDump.cs and writes <out_dir>/unity.json:

    {"unity": "6000.3.13f1", "variants": {"default": {<blob id>: [node, ...]},
                                          "bake_axis": {...}}}

"default" is Unity's model importer as it comes (Convert Units on, Bake Axis Conversion off),
"bake_axis" the same with Bake Axis Conversion on. Node values are in Unity space
(left-handed, Y up): the page converts them. The page uses unity.json as ground truth for
its Unity import model.
"""
import glob
import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_UNITY = r"C:\Program Files\Unity\Hub\Editor\6000.3.13f1\Editor\Unity.exe"


def run(unity, args, log):
    cmd = [unity, "-batchmode", "-nographics", "-quit", "-logFile", log] + args
    print(" ".join(cmd))
    r = subprocess.run(cmd)
    if r.returncode:
        sys.exit(f"Unity exited with {r.returncode}, see {log}")


def main():
    args = sys.argv[1:]
    unity = DEFAULT_UNITY
    if "--unity" in args:
        i = args.index("--unity")
        unity = args[i + 1]
        del args[i:i + 2]
    out, proj = (os.path.abspath(a) for a in args[:2])

    if not os.path.isdir(os.path.join(proj, "Assets")):
        run(unity, ["-createProject", proj], os.path.join(os.path.dirname(proj), "unity_create.log"))
    editor = os.path.join(proj, "Assets", "Editor")
    lab = os.path.join(proj, "Assets", "Lab")
    os.makedirs(editor, exist_ok=True)
    shutil.rmtree(lab, ignore_errors=True)
    if os.path.exists(lab + ".meta"):
        os.remove(lab + ".meta")
    os.makedirs(lab)
    shutil.copy2(os.path.join(HERE, "unity", "LabDump.cs"), editor)
    fbx = glob.glob(os.path.join(out, "blobs", "*.fbx"))
    for f in fbx:
        shutil.copy2(f, lab)

    os.environ["LAB_OUT"] = os.path.join(out, "unity.json")
    run(unity, ["-projectPath", proj, "-executeMethod", "LabDump.Run"],
        os.path.join(os.path.dirname(proj), "unity_dump.log"))
    print(f"{len(fbx)} FBX files -> {os.environ['LAB_OUT']}")


if __name__ == "__main__":
    main()
