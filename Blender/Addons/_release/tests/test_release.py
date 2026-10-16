"""Headless tests for the release CLI: fake tools in tmp_path, no Blender, no repo files."""
from __future__ import annotations

import sys
import zipfile
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from st3e_release import docs, versions  # noqa: E402
from st3e_release.build import BuildError, build, write_zip, zip_diff  # noqa: E402
from st3e_release.cli import main  # noqa: E402
from st3e_release.spec import (  # noqa: E402
    Spec, collect, dump_spec, glob_regex, infer_spec, load_spec, unclassified)
from st3e_release.tools import discover, resolve  # noqa: E402

LEGACY_MODULE = '''bl_info = {
    "name": "Center Loops",
    "version": (1, 5, 1),
    "blender": (4, 5, 0),
}
'''

EXTENSION_INIT = '''VERSION = (2, 0, 0)

bl_info = {
    "name": "Render Sets",
    "version": VERSION,
    "blender": (4, 2, 0),
}
'''

MANIFEST = 'schema_version = "1.0.0"\nid = "render_sets"\nversion = "2.0.0"\n'


def write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def make_zip(path: Path, entries: dict[str, str]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(path, "w") as zf:
        for name, text in entries.items():
            zf.writestr(name, text)
    return path


@pytest.fixture
def repo(tmp_path):
    """A repo with one legacy single-file addon (wrapped zip, renamed module) and one
    WMH extension (files at the archive root)."""
    addons = tmp_path / "Blender" / "Addons"

    legacy = addons / "Center Edges"
    write(legacy / "README.md", "# Center Edges\n\n**Version:** 1.5.1\n\nGrab `CenterEdges_v1.5.1.zip`.\nSince v1.2.0 it is faster.\n")
    write(legacy / "source" / "center_loops_addon.py", LEGACY_MODULE)
    write(legacy / "source" / "CHANGELOG.md", "## v1.5.1\n- fix\n")
    make_zip(legacy / "distribution" / "CenterEdges_v1.5.1.zip", {
        "CenterEdges/__init__.py": LEGACY_MODULE,
        "CenterEdges/README.md": (legacy / "README.md").read_text(encoding="utf-8"),
    })

    ext = addons / "Render Sets"
    write(ext / "README.md", "# Render Sets v2.0.0\n\n![Version](https://img.shields.io/badge/version-2.0.0-blue)\n")
    src = ext / "source"
    write(src / "__init__.py", EXTENSION_INIT)
    write(src / "blender_manifest.toml", MANIFEST)
    write(src / "core" / "__init__.py", "")
    write(src / "core" / "naming.py", "def name():\n    return 1\n")
    write(src / "tests" / "test_naming.py", "def test():\n    pass\n")
    write(src / "DEVELOPMENT.md", "dev notes\n")
    write(src / "core" / "__pycache__" / "naming.cpython-313.pyc", "junk")
    make_zip(ext / "distribution" / "RenderSets_v2.0.0.zip", {
        "__init__.py": EXTENSION_INIT,
        "blender_manifest.toml": MANIFEST,
        "core/__init__.py": "",
        "core/naming.py": "def name():\n    return 1\n",
    })

    write(tmp_path / "DOCUMENTATION_INDEX.md",
          "| Tool | Ver |\n|---|---|\n"
          "| **Center Edges/Loops** | 1.5.0 | Centers loops | [README](Blender/Addons/Center%20Edges/README.md) |\n"
          "| **Render Sets** | 2.0.0 | Sets | [README](Blender/Addons/Render%20Sets/README.md) |\n")
    write(tmp_path / "docs-site" / "src" / "content" / "docs" / "tools" / "render-sets.mdx",
          "---\ntool:\n  version: 2.0.0\n  downloadUrl: https://x/RenderSets_v2.0.0.zip\n"
          "  sourcePath: Blender/Addons/Render Sets/source/\n---\n")
    return tmp_path


def addons(repo: Path) -> Path:
    return repo / "Blender" / "Addons"


def tool(repo: Path, name: str):
    return resolve(discover(addons(repo)), name)


def init_all(repo: Path) -> None:
    assert main(["--addons-dir", str(addons(repo)), "init", "--all"]) == 0


# ---------------------------------------------------------------- versions

def test_bump_parts():
    assert versions.bump((1, 2, 3), "patch") == (1, 2, 4)
    assert versions.bump((1, 2, 3), "minor") == (1, 3, 0)
    assert versions.bump((1, 2, 3), "major") == (2, 0, 0)
    assert versions.bump((1, 9), "patch") == (1, 9, 1)
    assert versions.bump((1, 2, 3), "v1.10.0") == (1, 10, 0)
    with pytest.raises(versions.VersionError):
        versions.bump((1, 2, 3), "next")


def test_code_version_literal_and_constant(tmp_path):
    legacy = write(tmp_path / "a.py", LEGACY_MODULE)
    assert versions.read_code_version(legacy) == (1, 5, 1)
    versions.write_code_version(legacy, (1, 6, 0))
    text = legacy.read_text(encoding="utf-8")
    assert '"version": (1, 6, 0)' in text and '"blender": (4, 5, 0)' in text

    ext = write(tmp_path / "b.py", EXTENSION_INIT)
    assert versions.read_code_version(ext) == (2, 0, 0)
    versions.write_code_version(ext, (2, 1, 0))
    assert "VERSION = (2, 1, 0)" in ext.read_text(encoding="utf-8")


def test_write_keeps_crlf(tmp_path):
    path = tmp_path / "m.toml"
    path.write_bytes(MANIFEST.replace("\n", "\r\n").encode())
    versions.write_manifest_version(path, (3, 0, 0))
    data = path.read_bytes()
    assert b'version = "3.0.0"\r\n' in data and b"\n" not in data.replace(b"\r\n", b"")


def test_find_main_module_single_file(repo):
    src = addons(repo) / "Center Edges" / "source"
    assert versions.find_main_module(src).name == "center_loops_addon.py"


# ---------------------------------------------------------------- spec

def test_glob_semantics():
    assert glob_regex("*.py").match("a.py") and not glob_regex("*.py").match("core/a.py")
    assert glob_regex("core/**").match("core/x/y.py")
    assert glob_regex("**/*.py").match("a.py") and glob_regex("**/*.py").match("a/b/c.py")


def test_infer_reproduces_both_layouts(repo):
    legacy = addons(repo) / "Center Edges"
    spec, problems = infer_spec(legacy, legacy / "distribution" / "CenterEdges_v1.5.1.zip")
    assert not problems
    assert spec.wrapper == "CenterEdges" and spec.zip_stem == "CenterEdges"
    assert spec.files == {"__init__.py": "source/center_loops_addon.py", "README.md": "README.md"}

    ext = addons(repo) / "Render Sets"
    spec, problems = infer_spec(ext, ext / "distribution" / "RenderSets_v2.0.0.zip")
    assert not problems and spec.wrapper == ""
    assert "core/**" in spec.include and "tests/**" in spec.exclude
    assert set(collect(ext, spec)) == {"__init__.py", "blender_manifest.toml", "core/__init__.py", "core/naming.py"}


def test_spec_round_trips_through_toml(repo):
    spec = Spec(zip_stem="X", wrapper="X", include=["*.py"], exclude=["tests/**"],
                files={"__init__.py": "source/x.py"})
    root = repo / "spec_rt"
    write(root / "release.toml", dump_spec(spec, "header line"))
    assert load_spec(root) == spec


def test_new_module_is_unclassified(repo):
    init_all(repo)
    t = tool(repo, "Render Sets")
    write(t.source_dir / "new_module.py", "x = 1\n")
    assert unclassified(t.root, t.spec) == ["new_module.py"]


def test_init_does_not_overwrite(repo, capsys):
    init_all(repo)
    path = addons(repo) / "Center Edges" / "release.toml"
    path.write_text(path.read_text(encoding="utf-8") + "# mine\n", encoding="utf-8")
    init_all(repo)
    assert "# mine" in path.read_text(encoding="utf-8")


# ---------------------------------------------------------------- build

def test_rebuild_of_unchanged_source_is_up_to_date(repo):
    init_all(repo)
    result = build(tool(repo, "Render Sets"))
    assert result.status == "up-to-date"


def test_bumped_build_archives_previous_and_verifies(repo):
    init_all(repo)
    t = tool(repo, "Center Edges")
    assert main(["--addons-dir", str(addons(repo)), "release", "Center Edges", "minor"]) == 0
    assert [z.name for z in t.current_zips()] == ["CenterEdges_v1.6.0.zip"]
    assert (t.archive / "CenterEdges_v1.5.1.zip").is_file()
    with zipfile.ZipFile(t.distribution / "CenterEdges_v1.6.0.zip") as zf:
        assert sorted(zf.namelist()) == ["CenterEdges/README.md", "CenterEdges/__init__.py"]
        assert '"version": (1, 6, 0)' in zf.read("CenterEdges/__init__.py").decode()


def test_build_is_deterministic(repo, tmp_path):
    init_all(repo)
    t = tool(repo, "Render Sets")
    files = collect(t.root, t.spec)
    write_zip(tmp_path / "a.zip", "", files)
    write_zip(tmp_path / "b.zip", "", files)
    assert (tmp_path / "a.zip").read_bytes() == (tmp_path / "b.zip").read_bytes()


def test_changed_source_at_same_version_is_refused(repo):
    init_all(repo)
    t = tool(repo, "Render Sets")
    write(t.source_dir / "core" / "naming.py", "def name():\n    return 2\n")
    with pytest.raises(BuildError, match="bump the version"):
        build(t)
    assert build(t, force=True).status == "built"
    assert zip_diff(t.current_zips()[0], "", collect(t.root, t.spec)) == []


def test_archived_version_is_refused(repo):
    init_all(repo)
    t = tool(repo, "Render Sets")
    make_zip(t.archive / "RenderSets_v2.0.0.zip", {"x": "y"})
    with pytest.raises(BuildError, match="already in archive"):
        build(t)


def test_manifest_mismatch_is_refused(repo):
    init_all(repo)
    t = tool(repo, "Render Sets")
    versions.write_manifest_version(t.manifest, (2, 0, 1))
    with pytest.raises(BuildError, match="manifest"):
        build(t)


def test_syntax_error_fails_verification_and_leaves_distribution_alone(repo):
    init_all(repo)
    t = tool(repo, "Render Sets")
    write(t.source_dir / "core" / "naming.py", "def broken(:\n")
    versions.write_code_version(t.main_module(), (2, 0, 1))
    versions.write_manifest_version(t.manifest, (2, 0, 1))
    with pytest.raises(BuildError, match="does not compile"):
        build(t)
    assert [z.name for z in t.current_zips()] == ["RenderSets_v2.0.0.zip"]
    assert not t.archive.exists()


def test_dry_run_writes_nothing(repo):
    init_all(repo)
    t = tool(repo, "Center Edges")
    before = sorted(p.as_posix() for p in t.root.rglob("*"))
    assert main(["--addons-dir", str(addons(repo)), "bump", "Center Edges", "patch", "--dry-run"]) == 0
    assert main(["--addons-dir", str(addons(repo)), "build", "Center Edges", "--dry-run"]) == 0
    assert sorted(p.as_posix() for p in t.root.rglob("*")) == before


# ---------------------------------------------------------------- docs

def test_bump_updates_only_version_slots(repo):
    init_all(repo)
    assert main(["--addons-dir", str(addons(repo)), "bump", "Render Sets", "patch"]) == 0
    readme = (addons(repo) / "Render Sets" / "README.md").read_text(encoding="utf-8")
    assert "# Render Sets v2.0.1" in readme and "version-2.0.1-blue" in readme
    index = (repo / "DOCUMENTATION_INDEX.md").read_text(encoding="utf-8")
    assert "| **Render Sets** | 2.0.1 |" in index
    assert "| **Center Edges/Loops** | 1.5.0 |" in index  # other rows untouched
    page = next((repo / "docs-site").rglob("render-sets.mdx")).read_text(encoding="utf-8")
    assert "version: 2.0.1" in page and "RenderSets_v2.0.1.zip" in page


def test_history_mentions_are_left_alone(repo):
    init_all(repo)
    t = tool(repo, "Center Edges")
    docs.apply(docs.all_edits(repo, t, "1.6.0"))
    readme = (t.root / "README.md").read_text(encoding="utf-8")
    assert "**Version:** 1.6.0" in readme and "CenterEdges_v1.6.0.zip" in readme
    assert "Since v1.2.0" in readme


def test_check_flags_index_drift_and_stale_code(repo, capsys):
    init_all(repo)
    assert main(["--addons-dir", str(addons(repo)), "check", "Center Edges"]) == 1
    assert "DOCUMENTATION_INDEX says 1.5.0" in capsys.readouterr().out
    assert main(["--addons-dir", str(addons(repo)), "docs", "Center Edges"]) == 0
    assert main(["--addons-dir", str(addons(repo)), "check", "Center Edges"]) == 0

    write(addons(repo) / "Center Edges" / "source" / "center_loops_addon.py", LEGACY_MODULE + "x = 1\n")
    assert main(["--addons-dir", str(addons(repo)), "check", "Center Edges"]) == 1
    assert "zip is stale" in capsys.readouterr().out


def test_readme_only_drift_is_a_note(repo, capsys):
    init_all(repo)
    readme = addons(repo) / "Render Sets" / "README.md"
    t = tool(repo, "Render Sets")
    # Render Sets does not ship its README; make it ship one that then changes.
    t.spec.files["README.md"] = "README.md"
    (t.root / "release.toml").write_text(dump_spec(t.spec), encoding="utf-8")
    build(t, force=True)
    readme.write_text(readme.read_text(encoding="utf-8") + "More words.\n", encoding="utf-8")
    assert main(["--addons-dir", str(addons(repo)), "check", "Render Sets"]) == 0
    assert "zip carries older docs" in capsys.readouterr().out
