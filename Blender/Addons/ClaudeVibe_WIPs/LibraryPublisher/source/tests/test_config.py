"""Config schema, validation and the dotted-path editing the config slash
command relies on."""

import json

import pytest

from core import config


@pytest.fixture()
def cfg(tmp_path):
    conf = config.default_config(str(tmp_path))
    conf["delivery"]["rclone"]["remote"] = "st3e_gdrive"
    return conf


def test_default_config_validates_once_a_remote_is_set(cfg):
    assert config.validate(cfg) == []


def test_default_config_without_a_remote_is_flagged(tmp_path):
    problems = config.validate(config.default_config(str(tmp_path)))
    assert any("rclone.remote" in p for p in problems)


def test_defaults_ship_the_st3e_ext_rename(tmp_path):
    rule = config.default_config(str(tmp_path))["catalog"]["rename"][0]
    assert rule == {"from": "ST3E", "to": "ST3E_Ext"}


def test_defaults_keep_uuids(tmp_path):
    cat = config.default_config(str(tmp_path))["catalog"]
    assert cat["mode"] == "rename_paths"
    assert cat["keep_uuids"] is True


def test_missing_repo_root_is_flagged(cfg):
    cfg["source"]["repo_root"] = ""
    assert any("repo_root is empty" in p for p in config.validate(cfg))


def test_nonexistent_repo_root_is_flagged(cfg):
    cfg["source"]["repo_root"] = "Z:/nope/nope"
    assert any("does not exist" in p for p in config.validate(cfg))


def test_all_scopes_disabled_is_flagged(cfg):
    for entry in cfg["scope"]["entries"]:
        entry["enabled"] = False
    assert any("every scope entry is disabled" in p for p in config.validate(cfg))


def test_duplicate_scope_names_flagged(cfg):
    cfg["scope"]["entries"].append(dict(cfg["scope"]["entries"][0]))
    assert any("duplicate scope entry name" in p for p in config.validate(cfg))


def test_bad_criteria_mode_is_flagged(cfg):
    cfg["criteria"]["asset_marked"]["mode"] = "maybe"
    assert any("criteria.asset_marked.mode" in p for p in config.validate(cfg))


def test_criteria_pointing_at_an_unknown_scope_is_flagged(cfg):
    cfg["criteria"]["asset_marked"]["applies_to"] = ["typo_scope"]
    assert any("unknown scope entry" in p for p in config.validate(cfg))


def test_bad_on_block_is_flagged(cfg):
    cfg["criteria_policy"]["on_block"] = "explode"
    assert any("on_block" in p for p in config.validate(cfg))


def test_local_backend_requires_a_path(cfg):
    cfg["delivery"]["backend"] = "robocopy"
    assert any("local.path is empty" in p for p in config.validate(cfg))
    cfg["delivery"]["local"]["path"] = "G:/Shared drives/ST3E"
    assert config.validate(cfg) == []


def test_rename_mode_without_rules_is_flagged(cfg):
    cfg["catalog"]["rename"] = []
    assert any("catalog.rename is empty" in p for p in config.validate(cfg))


def test_bad_hook_name_is_flagged(cfg):
    cfg["triggers"]["git_hook"]["hook"] = "post-receive"
    assert any("pre-push or post-commit" in p for p in config.validate(cfg))


# --- round-trip and dotted paths --------------------------------------------

def test_save_load_round_trip(tmp_path, cfg):
    path = str(tmp_path / "publish_config.json")
    config.save(path, cfg)
    assert config.load(path) == cfg


def test_load_of_a_partial_config_fills_defaults(tmp_path):
    path = tmp_path / "publish_config.json"
    path.write_text(json.dumps({"library_name": "Custom"}), encoding="utf-8")
    loaded = config.load(str(path), repo_root=str(tmp_path))
    assert loaded["library_name"] == "Custom"
    # Keys added in a later version must appear rather than KeyError later on.
    assert loaded["criteria_policy"]["on_block"] == "skip_file"
    assert loaded["delivery"]["backend"] == "rclone"


def test_load_missing_file_raises_config_error(tmp_path):
    with pytest.raises(config.ConfigError):
        config.load(str(tmp_path / "nope.json"))


def test_load_invalid_json_raises_config_error(tmp_path):
    path = tmp_path / "publish_config.json"
    path.write_text("{not json", encoding="utf-8")
    with pytest.raises(config.ConfigError):
        config.load(str(path))


def test_set_path_nested(cfg):
    config.set_path(cfg, "delivery.rclone.path", "ST3E_Ext/live")
    assert cfg["delivery"]["rclone"]["path"] == "ST3E_Ext/live"


def test_set_path_into_a_list_index(cfg):
    config.set_path(cfg, "scope.entries.0.enabled", False)
    assert cfg["scope"]["entries"][0]["enabled"] is False


def test_set_path_rejects_unknown_keys(cfg):
    # A typo in the config command must fail loudly, not write dead config.
    with pytest.raises(KeyError):
        config.set_path(cfg, "delivery.rclone.remotte", "x")
    with pytest.raises(KeyError):
        config.set_path(cfg, "nonsense.key", 1)


def test_get_path(cfg):
    assert config.get_path(cfg, "criteria.geonode_layout.mode") == "warn"
    assert config.get_path(cfg, "scope.entries.1.name") == "shading"


def test_get_path_unknown_raises(cfg):
    with pytest.raises(KeyError):
        config.get_path(cfg, "criteria.nope.mode")


def test_scope_entry_lookup(cfg):
    assert config.scope_entry(cfg, "shading")["src"] == "Blender/Shading"
    with pytest.raises(KeyError):
        config.scope_entry(cfg, "nope")


def test_criteria_defaults_cover_the_asset_scopes(tmp_path):
    crit = config.default_config(str(tmp_path))["criteria"]
    assert crit["geonode_layout"]["applies_to"] == ["geonodes"]
    assert "shading" in crit["asset_marked"]["applies_to"]
    # Addon zips must never pull Blender into a publish.
    for check in crit.values():
        assert "addon_zips" not in check["applies_to"]
