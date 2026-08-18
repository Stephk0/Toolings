"""Scope selection: the curation layer that keeps backups, WIP iterations and
addon source out of the published library."""

import os

import pytest

from core import selection


@pytest.fixture()
def repo(tmp_path):
    """A miniature of the real repo layout, including the junk we must exclude."""
    files = [
        "Blender/Geonodes/GN_Bend.blend",
        "Blender/Geonodes/GN_Mosaic.blend",
        "Blender/Geonodes/GN_EdgeDestruct_fixed.blend",
        "Blender/Geonodes/GN_VariousTest.blend",
        "Blender/Geonodes/notes.txt",
        "Blender/Geonodes/_backup_publish_fix/GN_CellFrac.blend",
        "Blender/Geonodes/TreeGenDocu/GN_treeGenerator_02.blend",
        "Blender/Shading/SH_Cavity.blend",
        "Blender/Shading/_build/build_sh.py",
        "Blender/Addons/ClaudeVibe_WIPs/MassExporter/distribution/MassExporter_v13.7.0.zip",
        "Blender/Addons/ClaudeVibe_WIPs/MassExporter/distribution/archive/old_v1.zip",
        "Blender/Addons/ClaudeVibe_WIPs/TileUVProjector/distribution/TileUVProjector_v1.4.4.zip",
        "Blender/Addons/ClaudeVibe_WIPs/MassExporter/source/__init__.py",
    ]
    for rel in files:
        path = tmp_path / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("x", encoding="utf-8")
    return tmp_path


def _cfg(repo, entries):
    return {"source": {"repo_root": str(repo)}, "scope": {"entries": entries}}


GEONODES = {
    "name": "geonodes",
    "enabled": True,
    "src": "Blender/Geonodes",
    "dest": "Geonodes",
    "include": ["*.blend"],
    "exclude": ["_backup*/**", "*_fixed.blend", "TreeGenDocu/**", "GN_VariousTest.blend"],
    "recursive": False,
    "flatten": False,
}

ADDON_ZIPS = {
    "name": "addon_zips",
    "enabled": True,
    "src": "Blender/Addons/ClaudeVibe_WIPs",
    "dest": "Addons",
    "include": ["*/distribution/*.zip"],
    "exclude": ["*/distribution/archive/**"],
    "recursive": True,
    "flatten": True,
}


def _dests(result):
    return sorted(f.dest for f in result.files)


def test_geonodes_scope_keeps_only_the_real_assets(repo):
    result = selection.select(_cfg(repo, [GEONODES]))
    assert _dests(result) == ["Geonodes/GN_Bend.blend", "Geonodes/GN_Mosaic.blend"]


def test_non_recursive_scope_ignores_subfolders(repo):
    # TreeGenDocu and _backup_* are excluded anyway, but a non-recursive walk
    # must not even look at them.
    result = selection.select(_cfg(repo, [dict(GEONODES, exclude=[])]))
    assert all("/" not in f.dest[len("Geonodes/"):] for f in result.files)


def test_include_filters_by_extension(repo):
    result = selection.select(_cfg(repo, [GEONODES]))
    assert not any(f.dest.endswith(".txt") for f in result.files)


def test_addon_zips_take_current_builds_and_skip_archive(repo):
    result = selection.select(_cfg(repo, [ADDON_ZIPS]))
    assert _dests(result) == [
        "Addons/MassExporter_v13.7.0.zip",
        "Addons/TileUVProjector_v1.4.4.zip",
    ]


def test_flatten_drops_the_intermediate_folders(repo):
    result = selection.select(_cfg(repo, [ADDON_ZIPS]))
    assert all(f.dest.count("/") == 1 for f in result.files)


def test_non_flatten_preserves_relative_structure(repo):
    entry = dict(ADDON_ZIPS, flatten=False)
    result = selection.select(_cfg(repo, [entry]))
    assert "Addons/MassExporter/distribution/MassExporter_v13.7.0.zip" in _dests(result)


def test_disabled_entry_contributes_nothing(repo):
    result = selection.select(_cfg(repo, [dict(GEONODES, enabled=False)]))
    assert result.files == []


def test_missing_src_warns_instead_of_raising(repo):
    entry = dict(GEONODES, src="Blender/DoesNotExist")
    result = selection.select(_cfg(repo, [entry]))
    assert result.files == []
    assert any("does not exist" in w for w in result.warnings)


def test_zero_matches_warns(repo):
    entry = dict(GEONODES, include=["*.nope"])
    result = selection.select(_cfg(repo, [entry]))
    assert any("matched 0 files" in w for w in result.warnings)


def test_flatten_collision_is_reported(repo):
    # Two tools shipping an identically named zip would silently overwrite.
    dup = repo / "Blender/Addons/ClaudeVibe_WIPs/OtherTool/distribution/MassExporter_v13.7.0.zip"
    dup.parent.mkdir(parents=True, exist_ok=True)
    dup.write_text("y", encoding="utf-8")
    result = selection.select(_cfg(repo, [ADDON_ZIPS]))
    assert any("destination collision" in w for w in result.warnings)


def test_results_are_sorted_and_stable(repo):
    cfg = _cfg(repo, [GEONODES, ADDON_ZIPS])
    first = selection.select(cfg)
    second = selection.select(cfg)
    assert [f.dest for f in first.files] == [f.dest for f in second.files]
    assert [f.dest for f in first.files] == sorted(
        (f.dest for f in first.files), key=str.lower
    )


def test_per_scope_counts(repo):
    result = selection.select(_cfg(repo, [GEONODES, ADDON_ZIPS]))
    assert result.per_scope == {"geonodes": 2, "addon_zips": 2}


def test_selected_files_carry_real_size_and_source(repo):
    result = selection.select(_cfg(repo, [GEONODES]))
    item = result.files[0]
    assert item.size == 1
    assert os.path.isfile(item.src)
    assert item.scope == "geonodes"


# --- the pattern matcher itself ---------------------------------------------

@pytest.mark.parametrize(
    "rel,pattern,expected",
    [
        ("GN_Bend.blend", "*.blend", True),
        ("GN_Bend.txt", "*.blend", False),
        ("sub/GN_Bend.blend", "*.blend", True),          # bare pattern -> basename
        ("sub/GN_Bend.blend", "*/*.blend", True),
        ("GN_Bend.blend", "*/*.blend", False),
        ("_backup_x/GN.blend", "_backup*/**", True),
        ("TreeGenDocu/GN.blend", "TreeGenDocu/**", True),
        ("TreeGenDocu/deep/GN.blend", "TreeGenDocu/**", True),
        ("Tool/distribution/a.zip", "*/distribution/*.zip", True),
        ("Tool/distribution/archive/a.zip", "*/distribution/*.zip", False),
        ("Tool/distribution/archive/a.zip", "*/distribution/archive/**", True),
        ("a/b/c.blend", "**/c.blend", True),
        ("c.blend", "**/c.blend", True),
    ],
)
def test_glob_matching(rel, pattern, expected):
    assert selection.matches(rel, pattern) is expected
