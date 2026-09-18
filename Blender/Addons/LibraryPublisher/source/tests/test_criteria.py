"""Criteria planning, interpretation and block/warn policy.

These tests never launch Blender: they feed `interpret` the same JSON shape the
in-Blender driver emits, which is exactly why the policy layer lives in bpy-free
code.
"""

import json

import pytest

from core import config, criteria, selection


@pytest.fixture()
def cfg(tmp_path):
    conf = config.default_config(str(tmp_path))
    conf["delivery"]["rclone"]["remote"] = "st3e_gdrive"
    return conf


def _file(dest, scope, name="x.blend"):
    return selection.SelectedFile("D:/repo/%s" % name, dest, scope, 10, 0.0)


def _report(dest="Geonodes/GN_Bend.blend", scope="geonodes", **kwargs):
    base = {"src": "D:/repo/GN_Bend.blend", "dest": dest, "scope": scope, "assets": []}
    base.update(kwargs)
    return base


def _payload(*reports):
    return {"reports": list(reports)}


# --- planning ----------------------------------------------------------------

def test_active_checks_excludes_off(cfg):
    cfg["criteria"]["asset_marked"]["mode"] = "off"
    active = criteria.active_checks(cfg)
    assert "asset_marked" not in active
    assert "geonode_layout" in active


def test_no_files_inspected_when_every_check_is_off(cfg):
    for check in cfg["criteria"].values():
        check["mode"] = "off"
    files = [_file("Geonodes/a.blend", "geonodes")]
    assert criteria.files_to_inspect(cfg, files) == []


def test_only_blend_files_are_inspected(cfg):
    files = [
        _file("Geonodes/a.blend", "geonodes", "a.blend"),
        _file("Geonodes/readme.txt", "geonodes", "readme.txt"),
    ]
    assert [f.dest for f in criteria.files_to_inspect(cfg, files)] == ["Geonodes/a.blend"]


def test_addon_zips_never_reach_blender(cfg):
    files = [_file("Addons/MassExporter_v13.7.0.zip", "addon_zips", "me.zip")]
    assert criteria.files_to_inspect(cfg, files) == []


def test_applies_to_narrows_the_inspection(cfg):
    for key, check in cfg["criteria"].items():
        check["mode"] = "off" if key != "geonode_layout" else "warn"
    files = [
        _file("Geonodes/a.blend", "geonodes", "a.blend"),
        _file("Shading/b.blend", "shading", "b.blend"),
    ]
    # geonode_layout applies only to the geonodes scope.
    assert [f.dest for f in criteria.files_to_inspect(cfg, files)] == ["Geonodes/a.blend"]


def test_build_batch_carries_checks_uuids_and_audit_dir(cfg):
    files = [_file("Geonodes/a.blend", "geonodes", "a.blend")]
    batch = criteria.build_batch(cfg, files, {"uuid-1", "uuid-2"})
    assert batch["checks"] == sorted(criteria.active_checks(cfg))
    assert batch["known_catalog_uuids"] == ["uuid-1", "uuid-2"]
    assert "LLMGeonodePipeline" in batch["audit_module_dir"]
    assert batch["files"][0]["dest"] == "Geonodes/a.blend"


def test_build_command_is_headless_and_factory_startup(cfg):
    cmd = criteria.build_command(cfg, "blender.exe", "driver.py", "batch.json")
    assert "--background" in cmd and "--factory-startup" in cmd
    assert cmd[-2:] == ["--", "batch.json"]


# --- payload extraction ------------------------------------------------------

def test_extract_json_ignores_blender_startup_noise():
    payload = {"reports": [{"dest": "a"}]}
    stdout = "\n".join([
        "Blender 5.0.0", "Read prefs: ...",
        criteria.JSON_BEGIN, json.dumps(payload), criteria.JSON_END,
        "Blender quit",
    ])
    assert criteria.extract_json(stdout) == payload


def test_extract_json_raises_when_the_pass_produced_nothing():
    with pytest.raises(ValueError):
        criteria.extract_json("Blender crashed, no payload here")


# --- interpretation ----------------------------------------------------------

def test_asset_marked_fails_a_file_with_no_assets(cfg):
    cfg["criteria"]["asset_marked"]["mode"] = "block"
    verdict = criteria.interpret(cfg, _payload(_report(assets=[])), set())
    res = [r for r in verdict.results if r.check == "asset_marked"][0]
    assert res.status == criteria.FAIL
    assert "Geonodes/GN_Bend.blend" in verdict.blocked


def test_asset_marked_passes_when_assets_exist(cfg):
    report = _report(assets=[{"name": "GN_Bend", "catalog_id": "u1", "collection": "node_groups"}])
    verdict = criteria.interpret(cfg, _payload(report), {"u1"})
    res = [r for r in verdict.results if r.check == "asset_marked"][0]
    assert res.status == criteria.PASS


def test_warn_mode_downgrades_a_failure_and_blocks_nothing(cfg):
    cfg["criteria"]["asset_marked"]["mode"] = "warn"
    verdict = criteria.interpret(cfg, _payload(_report(assets=[])), set())
    res = [r for r in verdict.results if r.check == "asset_marked"][0]
    assert res.status == criteria.WARN
    assert verdict.blocked == set()


def test_off_mode_produces_no_result_at_all(cfg):
    for check in cfg["criteria"].values():
        check["mode"] = "off"
    verdict = criteria.interpret(cfg, _payload(_report(assets=[])), set())
    assert verdict.results == []


def test_catalog_assigned_flags_an_unknown_uuid(cfg):
    cfg["criteria"]["catalog_assigned"]["mode"] = "block"
    report = _report(assets=[{"name": "GN_X", "catalog_id": "stranger", "collection": "node_groups"}])
    verdict = criteria.interpret(cfg, _payload(report), {"known-uuid"})
    res = [r for r in verdict.results if r.check == "catalog_assigned"][0]
    assert res.status == criteria.FAIL
    assert "not in catalog file" in res.detail


def test_catalog_assigned_flags_the_null_uuid(cfg):
    cfg["criteria"]["catalog_assigned"]["mode"] = "warn"
    report = _report(assets=[{
        "name": "GN_X", "catalog_id": "00000000-0000-0000-0000-000000000000",
        "collection": "node_groups",
    }])
    verdict = criteria.interpret(cfg, _payload(report), {"known-uuid"})
    res = [r for r in verdict.results if r.check == "catalog_assigned"][0]
    assert "unassigned" in res.detail


def test_no_external_deps_flags_absolute_library_links(cfg):
    report = _report(
        assets=[{"name": "a", "catalog_id": "u1", "collection": "objects"}],
        libraries=[{"filepath": "D:/local/only.blend", "is_absolute": True, "exists": True}],
        missing_files=[],
    )
    verdict = criteria.interpret(cfg, _payload(report), {"u1"})
    res = [r for r in verdict.results if r.check == "no_external_deps"][0]
    assert res.status == criteria.FAIL
    assert "absolute library link" in res.detail
    # It defaults to block mode, because such a file is broken on the share.
    assert "Geonodes/GN_Bend.blend" in verdict.blocked


def test_no_external_deps_accepts_relative_links(cfg):
    report = _report(
        assets=[{"name": "a", "catalog_id": "u1", "collection": "objects"}],
        libraries=[{"filepath": "//textures/t.blend", "is_absolute": False, "exists": True}],
        missing_files=[],
    )
    verdict = criteria.interpret(cfg, _payload(report), {"u1"})
    res = [r for r in verdict.results if r.check == "no_external_deps"][0]
    assert res.status == criteria.PASS


def test_no_external_deps_flags_missing_files(cfg):
    report = _report(
        assets=[{"name": "a", "catalog_id": "u1", "collection": "objects"}],
        libraries=[], missing_files=["D:/gone/tex.png"],
    )
    verdict = criteria.interpret(cfg, _payload(report), {"u1"})
    res = [r for r in verdict.results if r.check == "no_external_deps"][0]
    assert "missing file" in res.detail


def test_geonode_layout_blocking_rule_failure(cfg):
    cfg["criteria"]["geonode_layout"]["mode"] = "block"
    report = _report(audits={"GN_Bend": {
        "R1_no_overlaps": {"status": "FAIL", "count": 3},
        "R3_left_to_right": {"status": "PASS"},
    }})
    verdict = criteria.interpret(cfg, _payload(report), set())
    res = [r for r in verdict.results if r.check == "geonode_layout"][0]
    assert res.status == criteria.FAIL
    assert "R1_no_overlaps" in res.detail


def test_geonode_layout_advisory_only_is_a_warning_even_in_block_mode(cfg):
    cfg["criteria"]["geonode_layout"]["mode"] = "block"
    report = _report(audits={"GN_Bend": {
        "R1_no_overlaps": {"status": "PASS"},
        "R8_nodes_framed": {"status": "WARN", "unframed": 4},
    }})
    verdict = criteria.interpret(cfg, _payload(report), set())
    res = [r for r in verdict.results if r.check == "geonode_layout"][0]
    assert res.status == criteria.WARN
    assert verdict.blocked == set()


def test_geonode_layout_all_pass(cfg):
    report = _report(audits={"GN_Bend": {
        "R1_no_overlaps": {"status": "PASS"}, "R8_nodes_framed": {"status": "PASS"},
    }})
    verdict = criteria.interpret(cfg, _payload(report), set())
    res = [r for r in verdict.results if r.check == "geonode_layout"][0]
    assert res.status == criteria.PASS


def test_geonode_layout_audit_error_is_a_warning(cfg):
    report = _report(audits={"GN_Bend": {"error": "boom"}})
    verdict = criteria.interpret(cfg, _payload(report), set())
    res = [r for r in verdict.results if r.check == "geonode_layout"][0]
    assert res.status == criteria.WARN


def test_an_unopenable_file_is_blocked(cfg):
    report = _report(error="open failed: corrupt")
    verdict = criteria.interpret(cfg, _payload(report), set())
    assert verdict.results[0].check == "inspect"
    assert "Geonodes/GN_Bend.blend" in verdict.blocked


def test_checks_do_not_run_outside_their_scope(cfg):
    # geonode_layout applies to geonodes only, so a shading file gets the other
    # checks and no layout verdict.
    report = _report(dest="Shading/SH_Cavity.blend", scope="shading",
                     assets=[{"name": "SH", "catalog_id": "u1", "collection": "materials"}],
                     libraries=[], missing_files=[], audits={"x": {"R1_no_overlaps": {"status": "FAIL"}}})
    verdict = criteria.interpret(cfg, _payload(report), {"u1"})
    assert not [r for r in verdict.results if r.check == "geonode_layout"]
    assert [r for r in verdict.results if r.check == "asset_marked"]


def test_summary_tallies_per_check(cfg):
    good = _report(dest="a.blend", assets=[{"name": "a", "catalog_id": "u1", "collection": "objects"}],
                   libraries=[], missing_files=[])
    bad = _report(dest="b.blend", assets=[], libraries=[], missing_files=[])
    verdict = criteria.interpret(cfg, _payload(good, bad), {"u1"})
    tally = verdict.summary()["asset_marked"]
    assert tally[criteria.PASS] == 1
    assert tally[criteria.WARN] == 1  # asset_marked defaults to warn mode


def test_format_report_hides_passes_unless_asked(cfg):
    good = _report(assets=[{"name": "a", "catalog_id": "u1", "collection": "objects"}],
                   libraries=[], missing_files=[])
    verdict = criteria.interpret(cfg, _payload(good), {"u1"})
    assert "[PASS]" not in criteria.format_report(verdict)
    assert "[PASS]" in criteria.format_report(verdict, show_pass=True)


def test_skipped_verdict_reports_why():
    verdict = criteria.skipped_verdict("no blender found")
    assert verdict.ran is False
    assert "no blender found" in criteria.format_report(verdict)


# --- Blender's own bundled data must never be mistaken for our problem -------
# Blender 5 auto-links its essentials brush libraries into every .blend with
# absolute paths into the install dir. Treating those as broken dependencies
# withheld nearly the whole library on the first real run of this tool.

def test_bundled_libraries_are_not_a_dependency_problem(cfg):
    report = _report(
        assets=[{"name": "a", "catalog_id": "u1", "collection": "objects"}],
        libraries=[{
            "filepath": "C:/Program Files/Blender Foundation/Blender 5.0/5.0/"
                        "datafiles/assets/brushes/essentials_brushes-mesh_sculpt.blend",
            "is_absolute": True, "exists": True, "is_bundled": True,
        }],
        missing_files=[],
    )
    verdict = criteria.interpret(cfg, _payload(report), {"u1"})
    res = [r for r in verdict.results if r.check == "no_external_deps"][0]
    assert res.status == criteria.PASS
    assert verdict.blocked == set()


def test_bundled_libraries_can_be_opted_back_in(cfg):
    cfg["criteria"]["no_external_deps"]["ignore_bundled_libraries"] = False
    report = _report(
        assets=[{"name": "a", "catalog_id": "u1", "collection": "objects"}],
        libraries=[{"filepath": "C:/Blender/datafiles/assets/x.blend",
                    "is_absolute": True, "exists": True, "is_bundled": True}],
        missing_files=[],
    )
    verdict = criteria.interpret(cfg, _payload(report), {"u1"})
    res = [r for r in verdict.results if r.check == "no_external_deps"][0]
    assert res.status == criteria.FAIL


def test_a_real_absolute_link_still_fails_alongside_bundled_ones(cfg):
    report = _report(
        assets=[{"name": "a", "catalog_id": "u1", "collection": "objects"}],
        libraries=[
            {"filepath": "C:/Blender/datafiles/assets/x.blend",
             "is_absolute": True, "exists": True, "is_bundled": True},
            {"filepath": "D:/my/local/only.blend",
             "is_absolute": True, "exists": True, "is_bundled": False},
        ],
        missing_files=[],
    )
    verdict = criteria.interpret(cfg, _payload(report), {"u1"})
    res = [r for r in verdict.results if r.check == "no_external_deps"][0]
    assert res.status == criteria.FAIL
    assert "only.blend" in res.detail
    assert "datafiles" not in res.detail
