"""Publish configuration: schema, defaults, load/save, dotted-path edits.

bpy-free. The config is the single source of truth for *what* gets published,
*where* it goes, *how* the catalog is rewritten, *which* criteria gate the run,
and *which* triggers are live. `/publish-library-config` edits it; every other
component only reads it.
"""

from __future__ import annotations

import copy
import json
import os
from typing import Any

SCHEMA_VERSION = 1

CONFIG_FILENAME = "publish_config.json"

# Delivery backends. rclone talks to a Google Shared Drive directly (service
# account friendly); robocopy/copy write to an already-mounted Drive letter.
BACKENDS = ("rclone", "robocopy", "copy")

# Criteria policy modes, in ascending strictness.
MODES = ("off", "warn", "block")

CATALOG_MODES = ("rename_paths", "off")

# What a `block`-mode criteria failure does to the run.
ON_BLOCK = ("skip_file", "abort_publish", "ignore")


def default_config(repo_root: str = "") -> dict:
    """A complete, valid config seeded for this repo's actual layout."""
    return {
        "schema_version": SCHEMA_VERSION,
        "library_name": "ST3E_Ext",
        "source": {
            # Absolute path to the git repo root. Empty => resolved at runtime.
            "repo_root": repo_root,
            # Asset-library root, relative to repo_root. This is the folder that
            # holds blender_assets.cats.txt and that Blender registers.
            "library_root": "Blender",
            "catalog_file": "blender_assets.cats.txt",
        },
        "scope": {
            "entries": [
                {
                    "name": "geonodes",
                    "enabled": True,
                    "src": "Blender/Geonodes",
                    "dest": "Geonodes",
                    "include": ["*.blend"],
                    "exclude": [
                        "_backup*/**",
                        "*_fixed.blend",
                        "TreeGenDocu/**",
                        "GN_VariousTest.blend",
                    ],
                    "recursive": False,
                    "flatten": False,
                },
                {
                    "name": "shading",
                    "enabled": True,
                    "src": "Blender/Shading",
                    "dest": "Shading",
                    "include": ["*.blend"],
                    "exclude": ["_build/**", "_backup*/**"],
                    "recursive": False,
                    "flatten": False,
                },
                {
                    "name": "addon_zips",
                    "enabled": True,
                    "src": "Blender/Addons/ClaudeVibe_WIPs",
                    "dest": "Addons",
                    # Only the CURRENT zip of each tool; archive/ stays home.
                    "include": ["*/distribution/*.zip"],
                    "exclude": ["*/distribution/archive/**"],
                    "recursive": True,
                    "flatten": True,
                },
            ]
        },
        "catalog": {
            "enabled": True,
            # Variant A: rewrite catalog PATHS + simple names, keep the UUIDs so
            # assets inside the .blend files still resolve untouched.
            "mode": "rename_paths",
            "rename": [{"from": "ST3E", "to": "ST3E_Ext"}],
            "simple_name_separator": "-",
            "keep_uuids": True,
            # Stamped as a comment header in the published cats.txt.
            "stamp_header": True,
        },
        "delivery": {
            "backend": "rclone",
            "rclone": {
                "remote": "",
                "path": "ST3E_Ext",
                # Full path to rclone.exe. Empty => look for it on PATH.
                "executable": "",
                "extra_flags": [],
                # Name of the env var holding the service-account JSON path.
                "service_account_env": "ST3E_GDRIVE_SA_JSON",
                # Shared Drive id (rclone --drive-team-drive). Optional when the
                # remote itself is already scoped to the Shared Drive.
                "team_drive": "",
            },
            "local": {"path": ""},
            # Publish into <dest>.staging then swap, so nobody opens a half-copy.
            "atomic": True,
            "delete_extraneous": True,
            "dry_run": False,
        },
        "criteria": {
            "geonode_layout": {
                "mode": "warn",
                "label": "Geonode layout audit R1-R11",
                "applies_to": ["geonodes"],
                # Blocking rules per LLMGeonodePipeline/layout_audit.py.
                "blocking_rules": [
                    "R1_no_overlaps",
                    "R2_reroutes_clear",
                    "R7_no_frame_overlap",
                ],
                "audit_module_dir": "Blender/Addons/ClaudeVibe_WIPs/LLMGeonodePipeline",
            },
            "asset_marked": {
                "mode": "warn",
                "label": "Contains at least one asset-marked datablock",
                "applies_to": ["geonodes", "shading"],
            },
            "catalog_assigned": {
                "mode": "warn",
                "label": "Assets sit in a known ST3E catalog UUID",
                "applies_to": ["geonodes", "shading"],
            },
            "no_external_deps": {
                "mode": "block",
                "label": "No absolute-path linked libraries or missing files",
                "applies_to": ["geonodes", "shading"],
                # Blender links its own essentials brush libraries into every
                # file with absolute paths. They exist on every install, so they
                # are not a portability problem - ignore them by default.
                "ignore_bundled_libraries": True,
                # Blender's Ctrl+C paste buffer (<temp>/copybuffer.blend) and
                # scratch copies from headless sessions are not dependencies.
                "ignore_temp_paths": True,
            },
        },
        "criteria_policy": {
            # What a `block`-mode failure does:
            #   skip_file     - leave that one file out, publish the rest, exit non-zero
            #   abort_publish - deliver nothing at all
            "on_block": "skip_file",
            # Print passing/skipped checks too, not just problems.
            "verbose": False,
        },
        "triggers": {
            "manual": {"enabled": True},
            "git_hook": {
                "enabled": True,
                "hook": "pre-push",
                "branches": ["main"],
                "background": True,
            },
            "github_action": {
                "enabled": True,
                "branches": ["main"],
                "paths": [
                    "Blender/Geonodes/**",
                    "Blender/Shading/**",
                    "Blender/blender_assets.cats.txt",
                    "Blender/Addons/ClaudeVibe_WIPs/*/distribution/*.zip",
                ],
            },
            "blender_button": {"enabled": True, "refresh_after": True},
        },
        "manifest": {
            "enabled": True,
            "filename": "publish_manifest.json",
            "incremental": True,
            "write_version_txt": True,
            "write_readme": True,
        },
        "blender": {
            # Empty => auto-detect the highest installed Blender.
            "executable": "",
        },
    }


class ConfigError(ValueError):
    """Raised for a config that cannot be used as-is."""


def config_path(tool_root: str) -> str:
    return os.path.join(tool_root, CONFIG_FILENAME)


def load(path: str, *, repo_root: str = "") -> dict:
    """Load a config, filling any missing keys from the defaults.

    A partial/older config on disk is upgraded in memory rather than rejected,
    so adding a key in a new version never breaks an existing install.
    """
    if not os.path.isfile(path):
        raise ConfigError("no config at %s - run /publish-library-config first" % path)
    with open(path, "r", encoding="utf-8") as fh:
        try:
            raw = json.load(fh)
        except json.JSONDecodeError as exc:
            raise ConfigError("%s is not valid JSON: %s" % (path, exc)) from exc
    return merge_defaults(raw, repo_root=repo_root)


def merge_defaults(raw: dict, *, repo_root: str = "") -> dict:
    """Deep-fill `raw` from defaults. Lists are taken verbatim from `raw`."""
    merged = _deep_fill(copy.deepcopy(raw), default_config(repo_root))
    merged["schema_version"] = SCHEMA_VERSION
    return merged


def _deep_fill(target: Any, defaults: Any) -> Any:
    if not isinstance(target, dict) or not isinstance(defaults, dict):
        return target
    for key, dval in defaults.items():
        if key not in target:
            target[key] = copy.deepcopy(dval)
        else:
            target[key] = _deep_fill(target[key], dval)
    return target


def save(path: str, cfg: dict) -> None:
    parent = os.path.dirname(os.path.abspath(path))
    if parent:
        os.makedirs(parent, exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(cfg, fh, indent=2, ensure_ascii=False)
        fh.write("\n")


def validate(cfg: dict) -> list:
    """Return a list of human-readable problems. Empty list == good to publish."""
    problems = []

    if not cfg.get("library_name"):
        problems.append("library_name is empty")

    src = cfg.get("source", {})
    if not src.get("repo_root"):
        problems.append("source.repo_root is empty")
    elif not os.path.isdir(src["repo_root"]):
        problems.append("source.repo_root does not exist: %s" % src["repo_root"])
    if not src.get("library_root"):
        problems.append("source.library_root is empty")

    entries = cfg.get("scope", {}).get("entries", [])
    if not entries:
        problems.append("scope.entries is empty - nothing would be published")
    enabled = [e for e in entries if e.get("enabled")]
    if entries and not enabled:
        problems.append("every scope entry is disabled - nothing would be published")
    seen = set()
    for entry in entries:
        name = entry.get("name") or "<unnamed>"
        if name in seen:
            problems.append("duplicate scope entry name: %s" % name)
        seen.add(name)
        if not entry.get("src"):
            problems.append("scope entry '%s' has no src" % name)
        if not entry.get("include"):
            problems.append("scope entry '%s' has no include patterns" % name)

    cat = cfg.get("catalog", {})
    if cat.get("mode") not in CATALOG_MODES:
        problems.append(
            "catalog.mode must be one of %s, got %r" % (CATALOG_MODES, cat.get("mode"))
        )
    if cat.get("enabled") and cat.get("mode") == "rename_paths":
        renames = cat.get("rename", [])
        if not renames:
            problems.append("catalog.rename is empty but catalog.mode is rename_paths")
        for rule in renames:
            if not rule.get("from") or not rule.get("to"):
                problems.append("catalog.rename entry needs non-empty from/to: %r" % (rule,))

    dely = cfg.get("delivery", {})
    backend = dely.get("backend")
    if backend not in BACKENDS:
        problems.append("delivery.backend must be one of %s, got %r" % (BACKENDS, backend))
    if backend == "rclone" and not dely.get("rclone", {}).get("remote"):
        problems.append("delivery.rclone.remote is empty - run /publish-library-config")
    if backend in ("robocopy", "copy") and not dely.get("local", {}).get("path"):
        problems.append("delivery.local.path is empty but backend is %s" % backend)

    for key, check in cfg.get("criteria", {}).items():
        mode = check.get("mode")
        if mode not in MODES:
            problems.append("criteria.%s.mode must be one of %s, got %r" % (key, MODES, mode))
        for scope_name in check.get("applies_to", []):
            if scope_name not in seen:
                problems.append(
                    "criteria.%s.applies_to references unknown scope entry '%s'"
                    % (key, scope_name)
                )

    on_block = cfg.get("criteria_policy", {}).get("on_block")
    if on_block not in ON_BLOCK:
        problems.append("criteria_policy.on_block must be one of %s, got %r" % (ON_BLOCK, on_block))

    hook = cfg.get("triggers", {}).get("git_hook", {})
    if hook.get("enabled") and hook.get("hook") not in ("pre-push", "post-commit"):
        problems.append("triggers.git_hook.hook must be pre-push or post-commit")

    return problems


# --- dotted-path get/set, so the config slash command can poke single keys ----

def get_path(cfg: dict, dotted: str) -> Any:
    node = cfg
    for part in dotted.split("."):
        if isinstance(node, list):
            node = node[_as_index(part, dotted)]
        elif isinstance(node, dict):
            if part not in node:
                raise KeyError("no such config key: %s" % dotted)
            node = node[part]
        else:
            raise KeyError("no such config key: %s" % dotted)
    return node


def set_path(cfg: dict, dotted: str, value: Any) -> None:
    """Set a value at a dotted path. Refuses to invent new keys, so a typo in
    `/publish-library-config` fails loudly instead of writing dead config."""
    parts = dotted.split(".")
    node = cfg
    for part in parts[:-1]:
        if isinstance(node, list):
            node = node[_as_index(part, dotted)]
        elif isinstance(node, dict):
            if part not in node:
                raise KeyError("no such config key: %s" % dotted)
            node = node[part]
        else:
            raise KeyError("no such config key: %s" % dotted)
    leaf = parts[-1]
    if isinstance(node, list):
        node[_as_index(leaf, dotted)] = value
    elif isinstance(node, dict):
        if leaf not in node:
            raise KeyError("no such config key: %s" % dotted)
        node[leaf] = value
    else:
        raise KeyError("no such config key: %s" % dotted)


def _as_index(part: str, dotted: str) -> int:
    try:
        return int(part)
    except ValueError:
        raise KeyError("%s: '%s' is not a list index" % (dotted, part)) from None


def scope_entry(cfg: dict, name: str) -> dict:
    for entry in cfg.get("scope", {}).get("entries", []):
        if entry.get("name") == name:
            return entry
    raise KeyError("no scope entry named %r" % name)
