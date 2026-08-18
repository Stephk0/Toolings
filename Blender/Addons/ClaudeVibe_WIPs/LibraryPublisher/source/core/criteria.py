"""Pluggable publish criteria: plan the inspection, interpret it, apply policy.

Each check is configured with a mode:

    off    - not run at all (and, if every check is off, Blender is never launched
             and a publish is pure file I/O)
    warn   - run, report, publish anyway
    block  - run, report, and act per `criteria_policy.on_block`
             ("skip_file" excludes just that file, "abort_publish" stops the run)

Four checks ship built in. `geonode_layout` deliberately does not reimplement
anything: it drives `LLMGeonodePipeline/layout_audit.py`, the existing R1-R11
audit, so the publish gate and the authoring gate can never drift apart.

This module is bpy-free. It builds the command line, parses the JSON the
in-Blender driver emits, and turns that into verdicts. Adding a check that needs
Blender means adding a collector in `checks/blender_inspect.py` and an
interpreter function here.
"""

from __future__ import annotations

import json
import os
from typing import NamedTuple

# Checks that need a .blend opened in Blender to evaluate.
BLENDER_CHECKS = ("geonode_layout", "asset_marked", "catalog_assigned", "no_external_deps")

JSON_BEGIN = "<<<ST3E_INSPECT_JSON>>>"
JSON_END = "<<<ST3E_INSPECT_END>>>"

PASS = "pass"
WARN = "warn"
FAIL = "fail"
SKIP = "skip"


class CheckResult(NamedTuple):
    check: str     # check key, e.g. "geonode_layout"
    dest: str      # published path this concerns
    status: str    # PASS / WARN / FAIL / SKIP
    detail: str    # one-line human reason

    @property
    def is_problem(self) -> bool:
        return self.status in (WARN, FAIL)


class Verdict(NamedTuple):
    results: list        # list[CheckResult]
    blocked: set         # dest paths a `block`-mode check rejected
    ran: bool            # whether the inspection pass actually ran
    inspect_error: str   # non-empty if the Blender pass itself failed

    def problems(self) -> list:
        return [r for r in self.results if r.is_problem]

    def failures(self) -> list:
        return [r for r in self.results if r.status == FAIL]

    def warnings(self) -> list:
        return [r for r in self.results if r.status == WARN]

    def summary(self) -> dict:
        """Compact per-check tally for the manifest."""
        out = {}
        for res in self.results:
            slot = out.setdefault(res.check, {PASS: 0, WARN: 0, FAIL: 0, SKIP: 0})
            slot[res.status] = slot[res.status] + 1
        return out


def active_checks(cfg: dict) -> dict:
    """check key -> check config, for every check not switched off."""
    return {
        key: conf
        for key, conf in (cfg.get("criteria") or {}).items()
        if conf.get("mode", "off") in ("warn", "block")
    }


def mode_of(cfg: dict, key: str) -> str:
    return (cfg.get("criteria") or {}).get(key, {}).get("mode", "off")


def files_to_inspect(cfg: dict, files: list) -> list:
    """The .blend files any active check applies to, deduped and sorted.

    A check's `applies_to` names scope entries, so addon zips never drag Blender
    into the run.
    """
    checks = active_checks(cfg)
    if not checks:
        return []
    scopes = set()
    for key, conf in checks.items():
        if key in BLENDER_CHECKS:
            scopes.update(conf.get("applies_to") or [])
    if not scopes:
        return []
    wanted = [
        f for f in files
        if f.scope in scopes and f.src.lower().endswith(".blend")
    ]
    seen = set()
    unique = []
    for item in sorted(wanted, key=lambda f: f.src.lower()):
        if item.src.lower() in seen:
            continue
        seen.add(item.src.lower())
        unique.append(item)
    return unique


def build_command(cfg: dict, blender_exe: str, driver: str, batch_file: str) -> list:
    """The headless Blender command line for the inspection pass."""
    return [
        blender_exe,
        "--background",
        "--factory-startup",
        "--python",
        driver,
        "--",
        batch_file,
    ]


def build_batch(cfg: dict, inspect_files: list, known_catalog_uuids: set) -> dict:
    """The job description handed to the in-Blender driver."""
    repo_root = cfg["source"]["repo_root"]
    audit_dir = (
        (cfg.get("criteria") or {})
        .get("geonode_layout", {})
        .get("audit_module_dir", "")
    )
    return {
        "files": [{"src": f.src, "dest": f.dest, "scope": f.scope} for f in inspect_files],
        "checks": sorted(active_checks(cfg)),
        "audit_module_dir": (
            os.path.normpath(os.path.join(repo_root, audit_dir)) if audit_dir else ""
        ),
        "known_catalog_uuids": sorted(known_catalog_uuids),
    }


def extract_json(stdout: str) -> dict:
    """Pull the JSON payload out of Blender's chatty stdout.

    Blender prints splash/version noise and addons print their own lines, so the
    driver fences its payload with explicit markers rather than us trying to
    parse the whole stream.
    """
    start = stdout.find(JSON_BEGIN)
    end = stdout.find(JSON_END, start + 1) if start >= 0 else -1
    if start < 0 or end < 0:
        raise ValueError("no inspection payload found in Blender output")
    blob = stdout[start + len(JSON_BEGIN):end].strip()
    return json.loads(blob)


# --- interpreters: raw per-file facts -> CheckResults ------------------------

def _interpret_asset_marked(report: dict, conf: dict) -> CheckResult:
    dest = report.get("dest", "?")
    assets = report.get("assets") or []
    if assets:
        return CheckResult("asset_marked", dest, PASS, "%d asset(s)" % len(assets))
    return CheckResult(
        "asset_marked", dest, FAIL,
        "no asset-marked datablock - it would be invisible in the Asset Browser",
    )


def _interpret_catalog_assigned(report: dict, conf: dict, known: set) -> CheckResult:
    dest = report.get("dest", "?")
    assets = report.get("assets") or []
    if not assets:
        return CheckResult("catalog_assigned", dest, SKIP, "no assets to check")
    unknown = []
    for asset in assets:
        cat = (asset.get("catalog_id") or "").strip()
        if not cat or cat == "00000000-0000-0000-0000-000000000000":
            unknown.append("%s (unassigned)" % asset.get("name", "?"))
        elif known and cat not in known:
            unknown.append("%s (%s not in catalog file)" % (asset.get("name", "?"), cat[:8]))
    if unknown:
        return CheckResult(
            "catalog_assigned", dest, FAIL,
            "asset(s) outside the published catalogs: %s" % ", ".join(unknown[:4]),
        )
    return CheckResult("catalog_assigned", dest, PASS, "all assets in known catalogs")


def _interpret_no_external_deps(report: dict, conf: dict) -> CheckResult:
    dest = report.get("dest", "?")
    problems = []
    # Blender auto-links its own essentials brush libraries into every file.
    # They are absolute by nature and present on every install, so treating them
    # as broken dependencies would withhold practically the whole library.
    allow_bundled = conf.get("ignore_bundled_libraries", True)
    # Blender's paste buffer and headless scratch copies live in the OS temp dir
    # and are not dependencies of anything.
    allow_temp = conf.get("ignore_temp_paths", True)
    for lib in report.get("libraries") or []:
        if allow_bundled and lib.get("is_bundled"):
            continue
        if allow_temp and lib.get("is_temp"):
            continue
        if lib.get("is_absolute"):
            problems.append("absolute library link: %s" % lib.get("filepath", "?"))
        elif not lib.get("exists", True):
            problems.append("broken library link: %s" % lib.get("filepath", "?"))
    for missing in report.get("missing_files") or []:
        problems.append("missing file: %s" % missing)
    if problems:
        return CheckResult("no_external_deps", dest, FAIL, "; ".join(problems[:4]))
    return CheckResult("no_external_deps", dest, PASS, "self-contained")


def _interpret_geonode_layout(report: dict, conf: dict) -> list:
    dest = report.get("dest", "?")
    audits = report.get("audits") or {}
    if not audits:
        return [CheckResult("geonode_layout", dest, SKIP, "no node group audited")]
    blocking = conf.get("blocking_rules") or []
    out = []
    for group_name, audit in sorted(audits.items()):
        if audit.get("error"):
            out.append(
                CheckResult("geonode_layout", dest, WARN,
                            "%s: audit error: %s" % (group_name, audit["error"]))
            )
            continue
        hard = [
            rule for rule in blocking
            if isinstance(audit.get(rule), dict) and audit[rule].get("status") == "FAIL"
        ]
        soft = [
            rule for rule, val in sorted(audit.items())
            if isinstance(val, dict)
            and val.get("status") in ("FAIL", "WARN")
            and rule not in hard
        ]
        if hard:
            out.append(
                CheckResult("geonode_layout", dest, FAIL,
                            "%s: blocking rule(s) failed: %s" % (group_name, ", ".join(hard)))
            )
        elif soft:
            out.append(
                CheckResult("geonode_layout", dest, WARN,
                            "%s: advisories: %s" % (group_name, ", ".join(soft)))
            )
        else:
            out.append(CheckResult("geonode_layout", dest, PASS, "%s: all rules pass" % group_name))
    return out


def interpret(cfg: dict, payload: dict, known_catalog_uuids: set) -> Verdict:
    """Turn the driver's raw facts into results, then apply block/warn policy."""
    criteria_cfg = cfg.get("criteria") or {}
    on_block = (cfg.get("criteria_policy") or {}).get("on_block", "skip_file")
    results = []
    blocked = set()

    for report in payload.get("reports") or []:
        dest = report.get("dest", "?")
        scope = report.get("scope", "")

        if report.get("error"):
            results.append(
                CheckResult("inspect", dest, FAIL, "could not inspect: %s" % report["error"])
            )
            if on_block != "ignore":
                blocked.add(dest)
            continue

        for key in BLENDER_CHECKS:
            conf = criteria_cfg.get(key, {})
            mode = conf.get("mode", "off")
            if mode == "off":
                continue
            if scope and scope not in (conf.get("applies_to") or []):
                continue

            if key == "asset_marked":
                produced = [_interpret_asset_marked(report, conf)]
            elif key == "catalog_assigned":
                produced = [_interpret_catalog_assigned(report, conf, known_catalog_uuids)]
            elif key == "no_external_deps":
                produced = [_interpret_no_external_deps(report, conf)]
            elif key == "geonode_layout":
                produced = _interpret_geonode_layout(report, conf)
            else:
                continue

            for res in produced:
                # In warn mode a hard failure is still only a warning.
                if mode == "warn" and res.status == FAIL:
                    res = res._replace(status=WARN)
                results.append(res)
                if mode == "block" and res.status == FAIL:
                    blocked.add(dest)

    return Verdict(results, blocked, True, "")


def skipped_verdict(reason: str = "") -> Verdict:
    """The verdict when no check is active, or Blender could not be found."""
    return Verdict([], set(), False, reason)


def format_report(verdict: Verdict, *, show_pass: bool = False) -> str:
    """A compact console report, grouped by check."""
    if not verdict.ran:
        return "criteria: not run%s" % ((" (%s)" % verdict.inspect_error) if verdict.inspect_error else "")
    if not verdict.results:
        return "criteria: nothing to check"

    order = {FAIL: 0, WARN: 1, SKIP: 2, PASS: 3}
    lines = []
    by_check = {}
    for res in verdict.results:
        by_check.setdefault(res.check, []).append(res)

    for check in sorted(by_check):
        items = sorted(by_check[check], key=lambda r: (order[r.status], r.dest.lower()))
        tally = verdict.summary().get(check, {})
        lines.append(
            "  %-18s pass %-3d warn %-3d fail %-3d skip %-3d"
            % (check, tally.get(PASS, 0), tally.get(WARN, 0),
               tally.get(FAIL, 0), tally.get(SKIP, 0))
        )
        for res in items:
            if res.status == PASS and not show_pass:
                continue
            if res.status == SKIP and not show_pass:
                continue
            lines.append("      [%s] %s - %s" % (res.status.upper(), res.dest, res.detail))
    return "\n".join(lines)
