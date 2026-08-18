"""End-to-end publish through the `copy` backend into a temp folder.

Criteria are switched off here, which is also the assertion that a publish needs
no Blender at all when they are: the whole run is file I/O plus one text rewrite.
"""

import json
import os

import pytest

from core import config, delivery, publish, selection

CATS = """# Asset Catalog Definition file
VERSION 1

f9ab2fa9-3a4e-491a-abaa-558cd5c029d0:ST3E:ST3E
bacd112a-8e87-47c2-afbc-818a11c75c08:ST3E/Deform:ST3E-Deform
"""


@pytest.fixture()
def repo(tmp_path):
    root = tmp_path / "repo"
    layout = {
        "Blender/blender_assets.cats.txt": CATS,
        "Blender/Geonodes/GN_Bend.blend": "bend-data",
        "Blender/Geonodes/GN_Twist.blend": "twist-data",
        "Blender/Geonodes/GN_EdgeDestruct_fixed.blend": "junk",
        "Blender/Geonodes/_backup_publish_fix/GN_Old.blend": "junk",
        "Blender/Shading/SH_Cavity.blend": "cavity-data",
        "Blender/Addons/ClaudeVibe_WIPs/MassExporter/distribution/MassExporter_v13.7.0.zip": "zip",
        "Blender/Addons/ClaudeVibe_WIPs/MassExporter/distribution/archive/old.zip": "junk",
    }
    for rel, text in layout.items():
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    return root


@pytest.fixture()
def cfg(repo, tmp_path):
    conf = config.default_config(str(repo))
    conf["delivery"]["backend"] = "copy"
    conf["delivery"]["local"]["path"] = str(tmp_path / "drive" / "ST3E_Ext")
    conf["delivery"]["atomic"] = False
    for check in conf["criteria"].values():
        check["mode"] = "off"
    return conf


@pytest.fixture()
def tool_root(tmp_path):
    root = tmp_path / "tool"
    (root / "source" / "checks").mkdir(parents=True)
    return str(root)


def _target(cfg):
    return cfg["delivery"]["local"]["path"]


def _published(cfg):
    target = _target(cfg)
    out = []
    for base, _dirs, names in os.walk(target):
        for name in names:
            out.append(os.path.relpath(os.path.join(base, name), target).replace(os.sep, "/"))
    return sorted(out)


# --- the happy path ----------------------------------------------------------

def test_publish_delivers_the_curated_tree(cfg, tool_root):
    result = publish.publish(cfg, tool_root)
    assert result.ok, "\n".join(result.lines)
    assert _published(cfg) == [
        "Addons/MassExporter_v13.7.0.zip",
        "Geonodes/GN_Bend.blend",
        "Geonodes/GN_Twist.blend",
        "LIBRARY_VERSION.txt",
        "README_DO_NOT_EDIT.txt",
        "Shading/SH_Cavity.blend",
        "blender_assets.cats.txt",
        "publish_manifest.json",
    ]


def test_junk_never_reaches_the_drive(cfg, tool_root):
    publish.publish(cfg, tool_root)
    published = " ".join(_published(cfg))
    assert "_fixed" not in published
    assert "_backup" not in published
    assert "archive" not in published


def test_published_catalog_is_renamed_but_keeps_uuids(cfg, tool_root):
    publish.publish(cfg, tool_root)
    text = (
        open(os.path.join(_target(cfg), "blender_assets.cats.txt"), encoding="utf-8").read()
    )
    assert "ST3E_Ext:ST3E_Ext" in text
    assert "ST3E_Ext/Deform:ST3E_Ext-Deform" in text
    # UUIDs untouched, so the copied .blend files still resolve.
    assert "f9ab2fa9-3a4e-491a-abaa-558cd5c029d0" in text
    assert "bacd112a-8e87-47c2-afbc-818a11c75c08" in text


def test_published_blend_files_are_byte_identical_copies(cfg, tool_root):
    publish.publish(cfg, tool_root)
    src = open(os.path.join(str(cfg["source"]["repo_root"]),
                            "Blender", "Geonodes", "GN_Bend.blend"), "rb").read()
    dst = open(os.path.join(_target(cfg), "Geonodes", "GN_Bend.blend"), "rb").read()
    assert src == dst


def test_manifest_lands_on_the_drive_with_provenance(cfg, tool_root):
    publish.publish(cfg, tool_root)
    man = json.load(open(os.path.join(_target(cfg), "publish_manifest.json"), encoding="utf-8"))
    assert man["library_name"] == "ST3E_Ext"
    assert man["catalog"]["renamed"] == [["ST3E", "ST3E_Ext"], ["ST3E/Deform", "ST3E_Ext/Deform"]]
    assert "Geonodes/GN_Bend.blend" in man["files"]


def test_first_publish_reports_everything_as_added(cfg, tool_root):
    result = publish.publish(cfg, tool_root)
    assert result.diff.changed == []
    assert "Geonodes/GN_Bend.blend" in result.diff.added


# --- incrementality ----------------------------------------------------------

def test_second_publish_with_no_edits_skips_delivery(cfg, tool_root):
    publish.publish(cfg, tool_root)
    second = publish.publish(cfg, tool_root)
    assert second.ok
    assert second.delivered is False
    assert "nothing changed" in "\n".join(second.lines)


def test_force_delivers_even_when_unchanged(cfg, tool_root):
    publish.publish(cfg, tool_root)
    forced = publish.publish(cfg, tool_root, force=True)
    assert forced.delivered is True


def test_an_edited_asset_shows_up_as_changed(cfg, tool_root):
    publish.publish(cfg, tool_root)
    path = os.path.join(str(cfg["source"]["repo_root"]), "Blender", "Geonodes", "GN_Bend.blend")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("bend-data-v2")
    second = publish.publish(cfg, tool_root)
    assert second.diff.changed == ["Geonodes/GN_Bend.blend"]
    assert second.delivered is True


def test_a_deleted_asset_is_pruned_from_the_drive(cfg, tool_root):
    publish.publish(cfg, tool_root)
    os.remove(os.path.join(str(cfg["source"]["repo_root"]),
                           "Blender", "Geonodes", "GN_Twist.blend"))
    second = publish.publish(cfg, tool_root)
    assert second.diff.removed == ["Geonodes/GN_Twist.blend"]
    assert "Geonodes/GN_Twist.blend" not in _published(cfg)


def test_delete_extraneous_off_leaves_stale_files_alone(cfg, tool_root):
    publish.publish(cfg, tool_root)
    cfg["delivery"]["delete_extraneous"] = False
    os.remove(os.path.join(str(cfg["source"]["repo_root"]),
                           "Blender", "Geonodes", "GN_Twist.blend"))
    publish.publish(cfg, tool_root)
    assert "Geonodes/GN_Twist.blend" in _published(cfg)


# --- dry run and gates -------------------------------------------------------

def test_dry_run_writes_nothing_and_leaves_no_cached_state(cfg, tool_root):
    cfg["delivery"]["dry_run"] = True
    result = publish.publish(cfg, tool_root)
    assert result.ok
    assert not os.path.isdir(_target(cfg))
    # A dry run must not convince the next real run that it already published.
    cfg["delivery"]["dry_run"] = False
    real = publish.publish(cfg, tool_root)
    assert real.delivered is True


def test_branch_gate_skips_a_non_listed_branch(cfg, tool_root):
    cfg["triggers"]["git_hook"]["branches"] = ["main"]
    # tmp_path is not a git repo, so the branch resolves empty and is not "main".
    result = publish.publish(cfg, tool_root, enforce_branch=True)
    assert result.ok
    assert result.delivered is False
    assert "not in ['main']" in "\n".join(result.lines)


def test_branch_gate_is_off_by_default(cfg, tool_root):
    result = publish.publish(cfg, tool_root)
    assert result.delivered is True


def test_invalid_config_stops_before_touching_anything(cfg, tool_root):
    cfg["delivery"]["local"]["path"] = ""
    result = publish.publish(cfg, tool_root)
    assert not result.ok
    assert "config is not usable" in result.reason


def test_missing_catalog_file_is_a_hard_error(cfg, tool_root):
    os.remove(os.path.join(str(cfg["source"]["repo_root"]), "Blender", "blender_assets.cats.txt"))
    result = publish.publish(cfg, tool_root)
    assert not result.ok
    assert "catalog file not found" in result.reason


def test_empty_selection_is_a_hard_error(cfg, tool_root):
    for entry in cfg["scope"]["entries"]:
        entry["include"] = ["*.nothing"]
    result = publish.publish(cfg, tool_root)
    assert not result.ok
    assert "matched no files" in result.reason


def test_catalog_rewrite_disabled_publishes_the_original(cfg, tool_root):
    cfg["catalog"]["enabled"] = False
    publish.publish(cfg, tool_root)
    text = open(os.path.join(_target(cfg), "blender_assets.cats.txt"), encoding="utf-8").read()
    assert ":ST3E:ST3E" in text
    assert "ST3E_Ext" not in text


def test_unrenamed_catalog_is_called_out_as_a_collision_risk(cfg, tool_root):
    path = os.path.join(str(cfg["source"]["repo_root"]), "Blender", "blender_assets.cats.txt")
    with open(path, "a", encoding="utf-8") as fh:
        fh.write("aaaaaaaa-0000-0000-0000-000000000001:Vendor/Kit:Vendor-Kit\n")
    result = publish.publish(cfg, tool_root)
    assert any("will collide with the local library" in line for line in result.lines)


def test_criteria_are_not_run_when_all_are_off(cfg, tool_root):
    result = publish.publish(cfg, tool_root)
    assert result.verdict.ran is False
    assert "all checks off" in "\n".join(result.lines)


# --- staging -----------------------------------------------------------------

def test_staging_hardlinks_rather_than_copying_when_it_can(tmp_path):
    src = tmp_path / "a.blend"
    src.write_text("data", encoding="utf-8")
    item = selection.SelectedFile(str(src), "Geonodes/a.blend", "geonodes", 4, 0.0)
    staged = delivery.build_staging([item], {"note.txt": "hi"}, str(tmp_path / "staging"))
    assert staged.errors == []
    assert staged.linked + staged.copied == 1
    assert os.path.isfile(os.path.join(staged.root, "Geonodes", "a.blend"))
    assert os.path.isfile(os.path.join(staged.root, "note.txt"))


def test_staging_starts_from_a_clean_slate(tmp_path):
    staging = tmp_path / "staging"
    staging.mkdir()
    (staging / "stale.blend").write_text("old", encoding="utf-8")
    src = tmp_path / "a.blend"
    src.write_text("data", encoding="utf-8")
    item = selection.SelectedFile(str(src), "a.blend", "geonodes", 4, 0.0)
    staged = delivery.build_staging([item], {}, str(staging))
    assert not os.path.exists(os.path.join(staged.root, "stale.blend"))


def test_atomic_swap_replaces_the_target_wholesale(cfg, tool_root):
    cfg["delivery"]["atomic"] = True
    publish.publish(cfg, tool_root)
    assert "Geonodes/GN_Bend.blend" in _published(cfg)
    # A stale file present before the swap must be gone after it.
    stale = os.path.join(_target(cfg), "Geonodes", "STALE.blend")
    with open(stale, "w", encoding="utf-8") as fh:
        fh.write("stale")
    publish.publish(cfg, tool_root, force=True)
    assert not os.path.exists(stale)


# --- the cached baseline must belong to the destination being published to ---

def test_switching_destination_invalidates_the_cached_baseline(cfg, tool_root, tmp_path):
    publish.publish(cfg, tool_root)
    second_target = str(tmp_path / "drive2" / "ST3E_Ext")
    cfg["delivery"]["local"]["path"] = second_target
    result = publish.publish(cfg, tool_root)
    # A brand-new destination has seen none of these files, so they are all adds.
    assert result.delivered is True
    assert "Geonodes/GN_Bend.blend" in result.diff.added
    assert result.diff.unchanged == []


def test_same_destination_still_uses_the_cache(cfg, tool_root):
    publish.publish(cfg, tool_root)
    second = publish.publish(cfg, tool_root)
    assert second.delivered is False
    assert second.diff.unchanged


def test_manifest_records_its_destination(cfg, tool_root):
    result = publish.publish(cfg, tool_root)
    assert result.manifest["destination"].startswith("copy:")


def test_withheld_files_are_recorded_in_the_manifest(cfg, tool_root):
    """A smaller library than expected must leave a trace on the drive."""
    result = publish.publish(cfg, tool_root)
    assert "skipped" in result.manifest
    assert result.manifest["skipped"] == []  # nothing blocked with criteria off
