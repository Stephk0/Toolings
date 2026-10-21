# Mass Collection Exporter — development

User docs: [README](../README.md). Export pipeline and settings priority: [EXPORT_FLOW](../EXPORT_FLOW.md).

## Tests

Both suites run headless and are excluded from the release zip (`release.toml`).

**Behaviour tests** — 54 checks, one small scene per test:

```bash
blender --background --factory-startup --python source/tests/headless_export_test.py -- source/__init__.py <out_dir>
```

**Export Lab** — a fixed stone / plant / tree scene exported through every mode combination
(64 switch combinations x 3 formats x 2 row layouts, plus one-option-at-a-time cases), then
checked in a three.js page against an oracle written from the spec. Spec and rules:
[`source/tests/export_lab/SPEC.md`](tests/export_lab/SPEC.md).

```bash
cd source/tests/export_lab
blender -b --factory-startup --python build_scene.py -- ../../__init__.py ../../../assets/export_lab/MassExporter_ExportLab.blend [preview.png]
blender -b --factory-startup --python run_matrix.py  -- ../../__init__.py ../../../assets/export_lab/MassExporter_ExportLab.blend <out_dir>
python serve.py <out_dir> 8000          # open http://localhost:8000, press "Run all checks"
python pack.py <out_dir> <pub_dir>      # only for hosts that serve web types only (artifact)
python unity_dump.py <out_dir> <unity_project_dir> [--unity <Unity.exe>]   # optional, after run_matrix
python bundle.py <out_dir> ../../../assets/export_lab/ExportLab_App [--three <node_modules/three>]
```

`unity_dump.py` imports every FBX of the run into a throwaway Unity project (batch mode,
`unity/LabDump.cs`, default Unity 6000.3.13f1) and writes `<out_dir>/unity.json`. With it the
page's Unity importer (`viewer/unity-fbx.js`) is checked against Unity's real import (R-UNITY).
First run creates the project (a few minutes); later runs reuse it.

`bundle.py` makes the offline app: page, data, vendored three.js 0.160.0 and fonts, launchers
from `app/` (`Start Export Lab.bat` uses Python or falls back to a PowerShell server;
`start.sh`), plus `ExportLab_App.zip`. Both are git-ignored — rebuild after each run.

`assets/export_lab/MassExporter_ExportLab.blend` is the review scene: the house setup (one row
per asset, Group by Suffix, FBX) is saved in it. Lighting is the geonode icon rig from
`Blender/Geonodes/_icons/stage.py`.
