"""Resolving an rclone binary that lives outside PATH.

rclone ships as a single self-contained .exe and is often just unzipped into a
downloads folder. Requiring it on PATH would mean editing the user's environment
to make the tool work, so an explicit path in the config wins over PATH.
"""

import os

import pytest

from core import config, delivery, shell


@pytest.fixture()
def cfg(tmp_path):
    conf = config.default_config(str(tmp_path))
    conf["delivery"]["rclone"]["remote"] = "st3e_gdrive"
    return conf


@pytest.fixture()
def fake_exe(tmp_path):
    exe = tmp_path / "tools" / ("rclone.exe" if os.name == "nt" else "rclone")
    exe.parent.mkdir(parents=True, exist_ok=True)
    exe.write_text("#!/bin/sh\n", encoding="utf-8")
    return exe


def test_explicit_file_path_is_used(cfg, fake_exe):
    cfg["delivery"]["rclone"]["executable"] = str(fake_exe)
    assert delivery.rclone_exe(cfg) == str(fake_exe)


def test_explicit_directory_is_searched(cfg, fake_exe):
    # Pointing at the unzipped folder is the natural thing to paste in.
    cfg["delivery"]["rclone"]["executable"] = str(fake_exe.parent)
    assert delivery.rclone_exe(cfg) == str(fake_exe)


def test_explicit_path_expands_env_vars_and_user(cfg, fake_exe, monkeypatch):
    monkeypatch.setenv("ST3E_TEST_TOOLS", str(fake_exe.parent))
    cfg["delivery"]["rclone"]["executable"] = "%ST3E_TEST_TOOLS%" if os.name == "nt" else "$ST3E_TEST_TOOLS"
    assert delivery.rclone_exe(cfg) == str(fake_exe)


def test_a_wrong_explicit_path_does_not_silently_fall_back_to_path(cfg, tmp_path):
    # Falling back would run some other rclone than the one that was configured.
    cfg["delivery"]["rclone"]["executable"] = str(tmp_path / "nope" / "rclone.exe")
    assert delivery.rclone_exe(cfg) == ""


def test_empty_executable_falls_back_to_path(cfg):
    cfg["delivery"]["rclone"]["executable"] = ""
    assert delivery.rclone_exe(cfg) == shell.which("rclone")


def test_missing_rclone_reports_the_config_key_to_set(cfg, tmp_path):
    cfg["delivery"]["rclone"]["executable"] = str(tmp_path / "nope.exe")
    result = delivery.deliver(cfg, str(tmp_path))
    assert result.ok is False
    assert "delivery.rclone.executable" in result.detail


def test_the_resolved_exe_is_what_gets_invoked(cfg, fake_exe):
    cfg["delivery"]["rclone"]["executable"] = str(fake_exe)
    cmd = delivery._rclone_command(cfg, "C:/staging")
    assert cmd[0] == str(fake_exe)
    assert cmd[1] == "sync"          # delete_extraneous defaults to True
    assert "--checksum" in cmd and "--delete-after" in cmd


def test_copy_verb_when_not_deleting_extraneous(cfg, fake_exe):
    cfg["delivery"]["rclone"]["executable"] = str(fake_exe)
    cfg["delivery"]["delete_extraneous"] = False
    assert delivery._rclone_command(cfg, "C:/staging")[1] == "copy"


def test_team_drive_and_dry_run_reach_the_command_line(cfg, fake_exe):
    cfg["delivery"]["rclone"]["executable"] = str(fake_exe)
    cfg["delivery"]["rclone"]["team_drive"] = "0ABCdef"
    cfg["delivery"]["dry_run"] = True
    cmd = delivery._rclone_command(cfg, "C:/staging")
    assert "--drive-team-drive" in cmd and "0ABCdef" in cmd
    assert "--dry-run" in cmd


def test_service_account_flag_only_appears_when_the_env_var_is_set(cfg, fake_exe, tmp_path, monkeypatch):
    cfg["delivery"]["rclone"]["executable"] = str(fake_exe)
    monkeypatch.delenv("ST3E_GDRIVE_SA_JSON", raising=False)
    assert "--drive-service-account-file" not in delivery._rclone_command(cfg, "C:/s")
    monkeypatch.setenv("ST3E_GDRIVE_SA_JSON", str(tmp_path / "sa.json"))
    assert "--drive-service-account-file" in delivery._rclone_command(cfg, "C:/s")
