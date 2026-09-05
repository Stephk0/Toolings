"""Staging and delivery to the Google Shared Drive. bpy-free.

Two steps, deliberately separate:

1. **Stage** - assemble the complete published tree on local disk. Hardlinked
   where the filesystem allows it, so staging 66 .blend files costs no bytes and
   no time. Staging the *whole* tree (not just changed files) is what lets the
   transfer step use a mirroring sync without deleting everything it cannot see.

2. **Deliver** - hand the staging tree to a backend:
     rclone   - straight to a Shared Drive, service-account friendly, works in CI
     robocopy - to an already-mounted Drive-for-Desktop letter
     copy     - pure Python, no external tool, for tests and odd cases

   Incrementality lives here: rclone/robocopy compare and skip unchanged files.
   The manifest diff decides whether to bother calling a backend at all.
"""

from __future__ import annotations

import json
import os
import shutil
from typing import NamedTuple

from . import shell


STAGE_STATE_FILE = ".staging_state.json"


class StagingResult(NamedTuple):
    root: str
    copied: int
    linked: int
    generated: int
    errors: list
    needs_remap: list = []   # staged absolute paths that must be rewritten
    reused: int = 0          # staged files carried over from the last run
    pruned: int = 0          # staged files dropped because they left the selection


class DeliveryResult(NamedTuple):
    backend: str
    ok: bool
    detail: str
    command: list
    out: str


def _link_or_copy(src: str, dst: str) -> str:
    """Hardlink into staging when possible; fall back to a real copy."""
    try:
        os.link(src, dst)
        return "linked"
    except (OSError, NotImplementedError, AttributeError):
        shutil.copy2(src, dst)
        return "copied"


def _load_state(staging_root: str) -> dict:
    path = os.path.join(staging_root, STAGE_STATE_FILE)
    if not os.path.isfile(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def _save_state(staging_root: str, state: dict) -> None:
    path = os.path.join(staging_root, STAGE_STATE_FILE)
    try:
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(state, fh, indent=2, sort_keys=True)
    except OSError:
        pass  # a lost cache only costs speed on the next run


def build_staging(
    files: list,
    generated: dict,
    staging_root: str,
    *,
    source_hashes: dict = None,
    fingerprint: str = "none",
    rewrite_exts: tuple = (),
    protect: tuple = (),
) -> StagingResult:
    """Assemble the published tree at `staging_root`, incrementally.

    The tree persists between runs. A staged file is reused when its source
    content hash AND the catalog fingerprint both match what was recorded last
    time; otherwise it is re-staged and, if it is a rewritable type, flagged for
    the remap pass. That is what stops every publish from paying a multi-minute
    Blender pass over files nobody touched.

    Files whose extension is in `rewrite_exts` are always *copied*, never
    hardlinked: the remap pass writes to them, and a hardlink would put the
    repository's own asset one careless write away from being modified.
    """
    os.makedirs(staging_root, exist_ok=True)
    state = _load_state(staging_root)
    source_hashes = source_hashes or {}

    copied = linked = reused = 0
    errors = []
    needs_remap = []
    new_state = {}
    wanted = set()

    for item in files:
        rel = item.dest.replace("/", os.sep)
        dst = os.path.join(staging_root, rel)
        wanted.add(rel)
        src_hash = source_hashes.get(item.dest, "")
        prior = state.get(item.dest) or {}
        rewritable = item.dest.lower().endswith(tuple(rewrite_exts)) if rewrite_exts else False

        fresh = (
            os.path.isfile(dst)
            and src_hash
            and prior.get("source_sha256") == src_hash
            and prior.get("fingerprint") == fingerprint
        )
        if fresh:
            reused += 1
            new_state[item.dest] = dict(prior)
            continue

        os.makedirs(os.path.dirname(dst), exist_ok=True)
        if os.path.exists(dst):
            try:
                os.remove(dst)
            except OSError as exc:
                errors.append("replacing staged %s: %s" % (item.dest, exc))
                continue
        try:
            if rewritable:
                shutil.copy2(item.src, dst)
                how = "copied"
            else:
                how = _link_or_copy(item.src, dst)
        except OSError as exc:
            errors.append("staging %s: %s" % (item.dest, exc))
            continue
        if how == "linked":
            linked += 1
        else:
            copied += 1
        if rewritable:
            needs_remap.append(dst)
        new_state[item.dest] = {"source_sha256": src_hash, "fingerprint": fingerprint}

    for dest, content in sorted((generated or {}).items()):
        rel = dest.replace("/", os.sep)
        wanted.add(rel)
        dst = os.path.join(staging_root, rel)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        try:
            with open(dst, "w", encoding="utf-8", newline="\n") as fh:
                fh.write(content)
        except OSError as exc:
            errors.append("writing %s: %s" % (dest, exc))

    # These are regenerated after the manifest exists; pruning them here would
    # only delete something we are about to rewrite.
    wanted.update(name.replace("/", os.sep) for name in protect)
    pruned = _prune_staging(staging_root, wanted)
    _save_state(staging_root, new_state)

    return StagingResult(
        staging_root, copied, linked, len(generated or {}), errors,
        needs_remap, reused, pruned,
    )


def write_generated(staging_root: str, mapping: dict) -> list:
    """Write generated text files into an existing staging tree."""
    errors = []
    for dest, content in sorted((mapping or {}).items()):
        dst = os.path.join(staging_root, dest.replace("/", os.sep))
        os.makedirs(os.path.dirname(dst) or staging_root, exist_ok=True)
        try:
            with open(dst, "w", encoding="utf-8", newline="\n") as fh:
                fh.write(content)
        except OSError as exc:
            errors.append("writing %s: %s" % (dest, exc))
    return errors


def _prune_staging(staging_root: str, wanted: set) -> int:
    """Drop staged files that are no longer selected, so the tree mirrors intent."""
    pruned = 0
    for root, _dirs, names in os.walk(staging_root, topdown=False):
        for name in names:
            if name == STAGE_STATE_FILE and root == staging_root:
                continue
            abs_path = os.path.join(root, name)
            rel = os.path.relpath(abs_path, staging_root)
            if rel not in wanted:
                try:
                    os.remove(abs_path)
                    pruned += 1
                except OSError:
                    pass
        if root != staging_root and not os.listdir(root):
            try:
                os.rmdir(root)
            except OSError:
                pass
    return pruned


# --- backends ----------------------------------------------------------------

def rclone_exe(cfg: dict) -> str:
    """The rclone binary to use: config path first, then PATH."""
    rc = cfg.get("delivery", {}).get("rclone", {})
    return shell.resolve_exe(rc.get("executable", ""), "rclone")


def _rclone_target(cfg: dict) -> str:
    rc = cfg["delivery"]["rclone"]
    path = (rc.get("path") or "").strip("/")
    return "%s:%s" % (rc["remote"], path) if path else "%s:" % rc["remote"]


def _rclone_command(cfg: dict, staging_root: str) -> list:
    dely = cfg["delivery"]
    rc = dely["rclone"]
    verb = "sync" if dely.get("delete_extraneous") else "copy"
    cmd = [
        rclone_exe(cfg) or "rclone",
        verb,
        staging_root,
        _rclone_target(cfg),
        # Checksums, not timestamps: Drive rewrites mtimes and .blend files are
        # binary, so a size+time comparison re-uploads far too much.
        "--checksum",
        # Removals happen only after every upload succeeded, so a failed run can
        # never leave the shared library with holes in it.
        "--delete-after",
        "--stats-one-line",
        "--stats", "10s",
        "--transfers", "6",
        "--checkers", "12",
        # Staging bookkeeping, not part of the library.
        "--exclude", "/" + STAGE_STATE_FILE,
    ]
    if dely.get("dry_run"):
        cmd.append("--dry-run")
    if rc.get("team_drive"):
        cmd += ["--drive-team-drive", rc["team_drive"]]
    sa_env = rc.get("service_account_env") or ""
    sa_path = os.environ.get(sa_env, "") if sa_env else ""
    if sa_path:
        cmd += ["--drive-service-account-file", sa_path]
    cmd += list(rc.get("extra_flags") or [])
    return cmd


def _robocopy_command(cfg: dict, staging_root: str, target: str) -> list:
    dely = cfg["delivery"]
    cmd = [
        "robocopy",
        staging_root,
        target,
        "/MIR" if dely.get("delete_extraneous") else "/E",
        "/NJH", "/NJS", "/NDL", "/NP",
        "/R:2", "/W:2",
        # Drive-for-Desktop virtual filesystems reject attribute/ACL copies.
        "/COPY:DAT",
        "/XF", STAGE_STATE_FILE,
    ]
    if dely.get("dry_run"):
        cmd.append("/L")
    return cmd


def _python_copy(cfg: dict, staging_root: str, target: str) -> DeliveryResult:
    """Backend of last resort: shutil, with optional pruning."""
    dry = bool(cfg["delivery"].get("dry_run"))
    prune = bool(cfg["delivery"].get("delete_extraneous"))
    moved = 0
    removed = 0

    wanted = set()
    for root, _dirs, names in os.walk(staging_root):
        for name in names:
            if name == STAGE_STATE_FILE and root == staging_root:
                continue
            src = os.path.join(root, name)
            rel = os.path.relpath(src, staging_root)
            wanted.add(rel)
            dst = os.path.join(target, rel)
            if dry:
                moved += 1
                continue
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.copy2(src, dst)
            moved += 1

    if prune and os.path.isdir(target):
        for root, _dirs, names in os.walk(target):
            for name in names:
                dst = os.path.join(root, name)
                rel = os.path.relpath(dst, target)
                if rel not in wanted:
                    removed += 1
                    if not dry:
                        try:
                            os.remove(dst)
                        except OSError:
                            pass

    verb = "would copy" if dry else "copied"
    return DeliveryResult(
        "copy", True,
        "%s %d file(s), %s %d extraneous" % (verb, moved, "would remove" if dry else "removed", removed),
        [], "",
    )


def _swap_in(staging_root: str, target: str, dry_run: bool) -> DeliveryResult:
    """Atomic-ish local publish: move the new tree into place, then bin the old.

    Only used for local backends. On a mounted Google Drive the rename is
    server-side, so the visible window where the library is incomplete is
    milliseconds instead of the length of an upload.
    """
    parent = os.path.dirname(os.path.abspath(target))
    incoming = target + ".incoming"
    retiring = target + ".retiring"
    if dry_run:
        return DeliveryResult("swap", True, "would swap %s into %s" % (incoming, target), [], "")
    os.makedirs(parent, exist_ok=True)
    for scratch in (incoming, retiring):
        if os.path.isdir(scratch):
            shutil.rmtree(scratch, ignore_errors=True)
    shutil.copytree(staging_root, incoming,
                    ignore=shutil.ignore_patterns(STAGE_STATE_FILE))
    if os.path.isdir(target):
        os.replace(target, retiring)
    os.replace(incoming, target)
    shutil.rmtree(retiring, ignore_errors=True)
    return DeliveryResult("swap", True, "swapped new tree into %s" % target, [], "")


def deliver(cfg: dict, staging_root: str) -> DeliveryResult:
    """Push the staging tree to the configured destination."""
    dely = cfg["delivery"]
    backend = dely.get("backend")

    if backend == "rclone":
        if not rclone_exe(cfg):
            return DeliveryResult(
                "rclone", False,
                "rclone not found - set delivery.rclone.executable to rclone.exe, "
                "or put it on PATH",
                [], "",
            )
        cmd = _rclone_command(cfg, staging_root)
        res = shell.run(cmd, timeout=3600)
        detail = "rclone %s -> %s" % (
            "dry-run" if dely.get("dry_run") else "sync",
            _rclone_target(cfg),
        )
        if not res.ok:
            detail += " FAILED (exit %d): %s" % (res.code, (res.err or res.out).strip()[:400])
        return DeliveryResult("rclone", res.ok, detail, cmd, (res.out + res.err).strip())

    target = dely.get("local", {}).get("path", "")
    if not target:
        return DeliveryResult(backend or "?", False, "delivery.local.path is empty", [], "")

    if dely.get("atomic"):
        return _swap_in(staging_root, target, bool(dely.get("dry_run")))

    if backend == "robocopy":
        cmd = _robocopy_command(cfg, staging_root, target)
        res = shell.run(cmd, timeout=3600)
        # robocopy exit codes below 8 are success (0-7 encode what it did).
        ok = res.code < 8
        detail = "robocopy -> %s (exit %d)" % (target, res.code)
        if not ok:
            detail += " FAILED: %s" % (res.err or res.out).strip()[:400]
        return DeliveryResult("robocopy", ok, detail, cmd, (res.out + res.err).strip())

    return _python_copy(cfg, staging_root, target)
