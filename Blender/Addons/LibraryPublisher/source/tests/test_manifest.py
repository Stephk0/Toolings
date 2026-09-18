"""Manifest hashing, incremental diffing and the provenance stamps."""

import json

from core import manifest, selection


def _mk(tmp_path, rel, text):
    path = tmp_path / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def _sel(tmp_path, rel, dest, scope="geonodes"):
    path = tmp_path / rel
    stat = path.stat()
    return selection.SelectedFile(str(path), dest, scope, stat.st_size, stat.st_mtime)


def _cfg(tmp_path):
    return {"source": {"repo_root": str(tmp_path)}, "library_name": "ST3E_Ext"}


def test_hash_file_is_content_addressed(tmp_path):
    a = _mk(tmp_path, "a.blend", "same")
    b = _mk(tmp_path, "b.blend", "same")
    c = _mk(tmp_path, "c.blend", "different")
    assert manifest.hash_file(str(a)) == manifest.hash_file(str(b))
    assert manifest.hash_file(str(a)) != manifest.hash_file(str(c))


def test_build_records_hash_size_scope_and_source(tmp_path):
    _mk(tmp_path, "Blender/Geonodes/GN_Bend.blend", "geometry")
    files = [_sel(tmp_path, "Blender/Geonodes/GN_Bend.blend", "Geonodes/GN_Bend.blend")]
    man = manifest.build(_cfg(tmp_path), files)
    entry = man["files"]["Geonodes/GN_Bend.blend"]
    assert entry["sha256"] == manifest.hash_text("geometry")
    assert entry["size"] == len("geometry")
    assert entry["scope"] == "geonodes"
    assert entry["source"] == "Blender/Geonodes/GN_Bend.blend"


def test_build_counts_by_scope_and_includes_generated_files(tmp_path):
    _mk(tmp_path, "a.blend", "x")
    files = [_sel(tmp_path, "a.blend", "Geonodes/a.blend")]
    man = manifest.build(
        _cfg(tmp_path), files,
        extra_files={"blender_assets.cats.txt": {"sha256": "abc", "size": 3, "scope": "generated"}},
    )
    assert man["counts"]["files"] == 2
    assert man["counts"]["by_scope"] == {"geonodes": 1, "generated": 1}


def test_build_carries_provenance_and_catalog_info(tmp_path):
    man = manifest.build(
        _cfg(tmp_path), [],
        git_info={"commit": "deadbeef", "branch": "main", "dirty": False},
        catalog_info={"renamed": [["ST3E", "ST3E_Ext"]]},
        criteria_summary={"asset_marked": {"pass": 3}},
        skipped=[{"dest": "Geonodes/bad.blend", "reason": "blocking criteria failure"}],
    )
    assert man["git"]["commit"] == "deadbeef"
    assert man["catalog"]["renamed"] == [["ST3E", "ST3E_Ext"]]
    assert man["criteria"]["asset_marked"]["pass"] == 3
    assert man["skipped"][0]["dest"] == "Geonodes/bad.blend"


def test_files_are_sorted_for_a_stable_diffable_manifest(tmp_path):
    for name in ("c.blend", "a.blend", "b.blend"):
        _mk(tmp_path, name, name)
    files = [_sel(tmp_path, n, "Geonodes/" + n) for n in ("c.blend", "a.blend", "b.blend")]
    man = manifest.build(_cfg(tmp_path), files)
    assert list(man["files"]) == [
        "Geonodes/a.blend", "Geonodes/b.blend", "Geonodes/c.blend"
    ]


# --- diffing -----------------------------------------------------------------

def _man(files):
    return {"files": {dest: {"sha256": h} for dest, h in files.items()}}


def test_diff_classifies_every_case():
    old = _man({"keep.blend": "h1", "edit.blend": "h2", "gone.blend": "h3"})
    new = _man({"keep.blend": "h1", "edit.blend": "CHANGED", "fresh.blend": "h4"})
    diff = manifest.diff(old, new)
    assert diff.unchanged == ["keep.blend"]
    assert diff.changed == ["edit.blend"]
    assert diff.added == ["fresh.blend"]
    assert diff.removed == ["gone.blend"]
    assert diff.has_changes is True


def test_diff_of_identical_manifests_has_no_changes():
    same = _man({"a.blend": "h"})
    diff = manifest.diff(same, same)
    assert diff.has_changes is False
    assert "0 added, 0 changed, 0 removed, 1 unchanged" == diff.summary()


def test_diff_against_no_previous_manifest_is_all_added():
    diff = manifest.diff({}, _man({"a.blend": "h", "b.blend": "h"}))
    assert diff.added == ["a.blend", "b.blend"]
    assert diff.has_changes is True


# --- loading -----------------------------------------------------------------

def test_load_missing_manifest_returns_empty(tmp_path):
    assert manifest.load(str(tmp_path / "nope.json")) == {}


def test_load_corrupt_manifest_degrades_to_full_publish(tmp_path):
    path = _mk(tmp_path, "publish_manifest.json", "{{{ truncated")
    # A corrupt manifest must cost only the incremental optimisation.
    assert manifest.load(str(path)) == {}


def test_load_round_trip(tmp_path):
    man = manifest.build(_cfg(tmp_path), [])
    path = tmp_path / "publish_manifest.json"
    path.write_text(manifest.dumps(man), encoding="utf-8")
    assert manifest.load(str(path)) == man


def test_dumps_is_valid_json(tmp_path):
    assert json.loads(manifest.dumps(manifest.build(_cfg(tmp_path), [])))


# --- human-facing stamps -----------------------------------------------------

def test_version_txt_carries_commit_and_branch(tmp_path):
    man = manifest.build(
        _cfg(tmp_path), [], git_info={"commit": "abc123", "branch": "main", "dirty": False}
    )
    text = manifest.version_txt(man)
    assert "abc123" in text and "main" in text
    assert "DIRTY" not in text


def test_version_txt_shouts_about_a_dirty_tree(tmp_path):
    man = manifest.build(_cfg(tmp_path), [], git_info={"dirty": True})
    assert "DIRTY" in manifest.version_txt(man)


def test_readme_lists_the_renames_and_warns_off_editing(tmp_path):
    cfg = _cfg(tmp_path)
    man = manifest.build(cfg, [], catalog_info={"renamed": [["ST3E", "ST3E_Ext"]]})
    text = manifest.readme_txt(man, cfg)
    assert "ST3E  ->  ST3E_Ext" in text
    assert "Do NOT edit" in text
    assert "Available offline" in text


def test_utc_stamp_shape():
    stamp = manifest.utc_stamp()
    assert stamp.endswith("Z") and len(stamp) == 20
