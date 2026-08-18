"""The publish orchestrator: select -> transform -> check -> stage -> deliver.

bpy-free, so the whole pipeline is exercisable from pytest and from CI without
Blender running. Blender is only ever launched as a subprocess, and only when at
least one criteria check is switched on.
"""

from __future__ import annotations

import json
import os
import shutil
from typing import NamedTuple

from . import catalogs, config, criteria, delivery, manifest, selection, shell

STAGING_DIRNAME = ".staging"
CACHE_DIRNAME = ".last_publish"


class PublishResult(NamedTuple):
    ok: bool
    reason: str            # why it stopped, when ok is False
    lines: list            # the console report, in order
    manifest: dict
    diff: manifest.Diff
    verdict: criteria.Verdict
    selection: selection.Selection
    delivered: bool
    delivery: object       # DeliveryResult or None
    skipped_files: list    # dest paths dropped by a blocking check


def _fail(reason: str, lines: list, sel=None, verdict=None) -> PublishResult:
    empty_diff = manifest.Diff([], [], [], [])
    return PublishResult(
        False, reason, lines + ["ERROR: " + reason], {}, empty_diff,
        verdict or criteria.skipped_verdict(), sel or selection.Selection([], [], {}),
        False, None, [],
    )


def catalog_source_path(cfg: dict) -> str:
    src = cfg["source"]
    return os.path.normpath(
        os.path.join(src["repo_root"], src["library_root"], src["catalog_file"])
    )


def run_criteria(cfg: dict, tool_root: str, files: list, known_uuids: set):
    """Launch the single headless Blender inspection pass, if any check is on."""
    # No active check at all is the common, cheap case: Blender is never
    # launched and the publish stays pure file I/O. Reported as "all checks off"
    # rather than as a reason it could not run.
    if not criteria.active_checks(cfg):
        return criteria.skipped_verdict(""), []

    targets = criteria.files_to_inspect(cfg, files)
    if not targets:
        return criteria.skipped_verdict("no selected file is in scope for any active check"), []

    blender_exe = shell.find_blender(cfg.get("blender", {}).get("executable", ""))
    if not blender_exe:
        return criteria.skipped_verdict(
            "no Blender executable found - set blender.executable in the config"
        ), []

    driver = os.path.join(tool_root, "source", "checks", "blender_inspect.py")
    if not os.path.isfile(driver):
        return criteria.skipped_verdict("inspection driver missing: %s" % driver), []

    scratch = os.path.join(tool_root, STAGING_DIRNAME + "_batch")
    os.makedirs(scratch, exist_ok=True)
    batch_path = os.path.join(scratch, "inspect_batch.json")
    batch = criteria.build_batch(cfg, targets, known_uuids)
    with open(batch_path, "w", encoding="utf-8") as fh:
        json.dump(batch, fh, indent=2)

    cmd = criteria.build_command(cfg, blender_exe, driver, batch_path)
    res = shell.run(cmd, timeout=3600)
    try:
        payload = criteria.extract_json(res.out)
    except (ValueError, json.JSONDecodeError) as exc:
        tail = (res.err or res.out).strip()[-600:]
        return criteria.skipped_verdict(
            "inspection pass produced no usable output (%s). Tail: %s" % (exc, tail)
        ), targets

    verdict = criteria.interpret(cfg, payload, known_uuids)
    if payload.get("audit_error"):
        verdict = verdict._replace(inspect_error=payload["audit_error"])
    return verdict, targets


def publish(
    cfg: dict,
    tool_root: str,
    *,
    force: bool = False,
    enforce_branch: bool = False,
    reason: str = "manual",
) -> PublishResult:
    """Run one publish. `force` delivers even when nothing changed."""
    lines = []
    add = lines.append

    problems = config.validate(cfg)
    if problems:
        return _fail("config is not usable:\n  - " + "\n  - ".join(problems), lines)

    repo_root = cfg["source"]["repo_root"]
    lib_name = cfg.get("library_name", "")
    dry = bool(cfg["delivery"].get("dry_run"))

    add("publish '%s'  (trigger: %s%s)" % (lib_name, reason, ", DRY RUN" if dry else ""))
    add("  repo: %s" % repo_root)

    git = shell.git_info(repo_root)
    if git.get("branch"):
        add("  branch %s @ %s%s" % (
            git["branch"], git.get("short", "?"), "  [DIRTY]" if git.get("dirty") else ""
        ))

    # --- branch gate ---------------------------------------------------------
    if enforce_branch:
        allowed = cfg["triggers"]["git_hook"].get("branches") or []
        if allowed and git.get("branch") not in allowed:
            add("  skipped: branch '%s' is not in %s" % (git.get("branch"), allowed))
            empty = manifest.Diff([], [], [], [])
            return PublishResult(
                True, "branch not published", lines, {}, empty,
                criteria.skipped_verdict("branch gate"), selection.Selection([], [], {}),
                False, None, [],
            )

    # --- select --------------------------------------------------------------
    sel = selection.select(cfg)
    for warn in sel.warnings:
        add("  ! %s" % warn)
    if not sel.files:
        return _fail("selection matched no files - nothing to publish", lines, sel)
    add("  selected %d file(s): %s" % (
        len(sel.files),
        ", ".join("%s=%d" % (k, v) for k, v in sorted(sel.per_scope.items())),
    ))

    # --- catalog transform (Variant A) ---------------------------------------
    cat_path = catalog_source_path(cfg)
    generated = {}
    catalog_info = {}
    known_uuids = set()

    if cfg["catalog"].get("enabled") and cfg["catalog"].get("mode") == "rename_paths":
        if not os.path.isfile(cat_path):
            return _fail("catalog file not found: %s" % cat_path, lines, sel)
        with open(cat_path, "r", encoding="utf-8") as fh:
            cat_text = fh.read()
        known_uuids = catalogs.known_uuids(cat_text)
        stamp = "source commit %s (%s)" % (git.get("short", "?"), git.get("branch", "?"))
        rewritten = catalogs.rewrite(
            cat_text,
            cfg["catalog"].get("rename") or [],
            separator=cfg["catalog"].get("simple_name_separator", "-"),
            stamp=stamp if cfg["catalog"].get("stamp_header") else "",
        )
        generated[cfg["source"]["catalog_file"]] = rewritten.text
        catalog_info = {
            "renamed": [list(pair) for pair in rewritten.renamed],
            "unchanged": rewritten.unchanged,
            "uuids_preserved": True,
        }
        add("  catalog: %d renamed, %d untouched" % (
            len(rewritten.renamed), len(rewritten.unchanged)
        ))
        for old, new in rewritten.renamed:
            add("      %s  ->  %s" % (old, new))
        # An unrenamed catalog keeps its original path, so its assets would land
        # in the *local* library's tree and defeat the whole side-by-side point.
        for path in rewritten.unchanged:
            add("  ! catalog '%s' matched no rename rule - it will collide with "
                "the local library" % path)
    else:
        add("  catalog: rewrite disabled (published as-is)")
        if os.path.isfile(cat_path):
            with open(cat_path, "r", encoding="utf-8") as fh:
                text = fh.read()
            known_uuids = catalogs.known_uuids(text)
            generated[cfg["source"]["catalog_file"]] = text

    # --- criteria ------------------------------------------------------------
    verdict, inspected = run_criteria(cfg, tool_root, sel.files, known_uuids)
    if verdict.ran:
        add("  criteria: inspected %d file(s)" % len(inspected))
        report = criteria.format_report(
            verdict, show_pass=bool(cfg.get("criteria_policy", {}).get("verbose"))
        )
        if report:
            lines.extend(report.splitlines())
    elif verdict.inspect_error:
        add("  criteria: not run (%s)" % verdict.inspect_error)
        # A check set to `block` is a gate the user asked for. Publishing without
        # having actually run it would be a silent downgrade to no gate at all.
        blocking = sorted(
            key for key in criteria.active_checks(cfg)
            if criteria.mode_of(cfg, key) == "block"
        )
        if blocking:
            return _fail(
                "cannot verify block-mode check(s) %s: %s"
                % (", ".join(blocking), verdict.inspect_error),
                lines, sel, verdict,
            )
    else:
        add("  criteria: all checks off")

    on_block = cfg.get("criteria_policy", {}).get("on_block", "skip_file")
    files = list(sel.files)
    skipped = []
    if verdict.blocked:
        if on_block == "abort_publish":
            return _fail(
                "%d file(s) failed a blocking check and criteria_policy.on_block "
                "is abort_publish" % len(verdict.blocked),
                lines, sel, verdict,
            )
        if on_block == "skip_file":
            skipped = sorted(verdict.blocked)
            files = [f for f in files if f.dest not in verdict.blocked]
            add("  ! withholding %d file(s) that failed a blocking check:" % len(skipped))
            for dest in skipped:
                add("      - %s" % dest)
            if not files:
                return _fail("every selected file failed a blocking check", lines, sel, verdict)

    # --- manifest + diff -----------------------------------------------------
    man = manifest.build(
        cfg, files,
        git_info=git,
        catalog_info=catalog_info,
        criteria_summary=verdict.summary(),
        skipped=[{"dest": d, "reason": "blocking criteria failure"} for d in skipped],
        extra_files={
            dest: {"sha256": manifest.hash_text(text), "size": len(text.encode("utf-8")),
                   "scope": "generated"}
            for dest, text in generated.items()
        },
    )

    cache_dir = os.path.join(tool_root, CACHE_DIRNAME)
    cache_path = os.path.join(cache_dir, cfg["manifest"]["filename"])
    previous = _previous_manifest(cfg, cache_path)
    if not previous and cfg["delivery"]["backend"] == "rclone":
        previous = _fetch_remote_manifest(cfg)
    change = manifest.diff(previous, man)
    add("  changes: %s" % change.summary())
    for dest in change.added:
        add("      + %s" % dest)
    for dest in change.changed:
        add("      ~ %s" % dest)
    for dest in change.removed:
        add("      - %s" % dest)

    if cfg["manifest"].get("enabled"):
        generated[cfg["manifest"]["filename"]] = manifest.dumps(man)
    if cfg["manifest"].get("write_version_txt"):
        generated["LIBRARY_VERSION.txt"] = manifest.version_txt(man)
    if cfg["manifest"].get("write_readme"):
        generated["README_DO_NOT_EDIT.txt"] = manifest.readme_txt(man, cfg)

    if not change.has_changes and not force:
        add("  nothing changed - delivery skipped (use --force to publish anyway)")
        return PublishResult(
            True, "up to date", lines, man, change, verdict, sel, False, None, skipped
        )

    # --- stage + deliver -----------------------------------------------------
    staging_root = os.path.join(tool_root, STAGING_DIRNAME)
    staged = delivery.build_staging(files, generated, staging_root)
    for err in staged.errors:
        add("  ! %s" % err)
    if staged.errors:
        return _fail("staging failed - nothing was delivered", lines, sel, verdict)
    add("  staged %d file(s) (%d hardlinked, %d copied, %d generated) at %s" % (
        staged.copied + staged.linked + staged.generated,
        staged.linked, staged.copied, staged.generated, staging_root,
    ))

    result = delivery.deliver(cfg, staging_root)
    add("  delivery: %s" % result.detail)
    if not result.ok:
        return _fail("delivery failed", lines, sel, verdict)

    if not dry:
        os.makedirs(cache_dir, exist_ok=True)
        with open(cache_path, "w", encoding="utf-8") as fh:
            fh.write(manifest.dumps(man))
        shutil.rmtree(staging_root, ignore_errors=True)

    add("  done: %d file(s) published as '%s'" % (man["counts"]["files"], lib_name))
    return PublishResult(
        True, "", lines, man, change, verdict, sel, True, result, skipped
    )


def _previous_manifest(cfg: dict, cache_path: str) -> dict:
    """The cached manifest, but only if it describes the SAME destination.

    Publishing to a new target must not diff against the old target's baseline,
    or an unchanged file would be reported as already delivered when the new
    destination has never seen it.
    """
    cached = manifest.load(cache_path)
    if not cached:
        return {}
    here = manifest.destination_of(cfg)
    there = cached.get("destination", "")
    if there and there != here:
        return {}
    return cached


def _fetch_remote_manifest(cfg: dict) -> dict:
    """Best-effort read of the manifest already on the Shared Drive.

    Only used when the local cache is missing (fresh clone, CI runner). A failure
    here just means a full re-upload comparison, never a broken publish.
    """
    rc = cfg["delivery"]["rclone"]
    exe = delivery.rclone_exe(cfg)
    if not exe or not rc.get("remote"):
        return {}
    path = (rc.get("path") or "").strip("/")
    remote = "%s:%s/%s" % (rc["remote"], path, cfg["manifest"]["filename"])
    cmd = [exe, "cat", remote]
    if rc.get("team_drive"):
        cmd += ["--drive-team-drive", rc["team_drive"]]
    sa_path = os.environ.get(rc.get("service_account_env") or "", "")
    if sa_path:
        cmd += ["--drive-service-account-file", sa_path]
    res = shell.run(cmd, timeout=120)
    if not res.ok:
        return {}
    try:
        data = json.loads(res.out)
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}
