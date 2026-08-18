"""The publish manifest: content hashes, incremental diffing, provenance.

A `publish_manifest.json` sits at the published library root and answers three
questions that are otherwise guesswork:

  * which commit is the shared library at right now?
  * which files actually changed since last publish? (so we upload only those)
  * what was skipped, and why?

bpy-free.
"""

from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from typing import NamedTuple

MANIFEST_SCHEMA_VERSION = 1

_HASH_CHUNK = 1024 * 1024


def hash_file(path: str) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as fh:
        while True:
            chunk = fh.read(_HASH_CHUNK)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def hash_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class Diff(NamedTuple):
    added: list      # dest paths present now, absent before
    changed: list    # dest paths whose hash moved
    removed: list    # dest paths gone from the selection
    unchanged: list  # dest paths with an identical hash

    @property
    def has_changes(self) -> bool:
        return bool(self.added or self.changed or self.removed)

    def summary(self) -> str:
        return "%d added, %d changed, %d removed, %d unchanged" % (
            len(self.added),
            len(self.changed),
            len(self.removed),
            len(self.unchanged),
        )


def build(
    cfg: dict,
    files: list,
    *,
    git_info: dict = None,
    catalog_info: dict = None,
    criteria_summary: dict = None,
    skipped: list = None,
    extra_files: dict = None,
) -> dict:
    """Build a manifest from selected files (hashing each one).

    `extra_files` maps dest path -> hash for content generated rather than copied
    (the rewritten catalog file, README, version stamp).
    """
    entries = {}
    for item in files:
        entries[item.dest] = {
            "sha256": hash_file(item.src),
            "size": item.size,
            "scope": item.scope,
            "source": os.path.relpath(item.src, cfg["source"]["repo_root"]).replace(
                os.sep, "/"
            ),
        }
    for dest, meta in (extra_files or {}).items():
        entries[dest] = dict(meta)

    by_scope = {}
    for meta in entries.values():
        scope = meta.get("scope", "generated")
        by_scope[scope] = by_scope.get(scope, 0) + 1

    return {
        "schema_version": MANIFEST_SCHEMA_VERSION,
        "library_name": cfg.get("library_name", ""),
        # Recorded so a cached manifest from a different destination is not
        # mistaken for this one's baseline (see publish._previous_manifest).
        "destination": destination_of(cfg),
        "generated_utc": utc_stamp(),
        "git": git_info or {},
        "catalog": catalog_info or {},
        "criteria": criteria_summary or {},
        "skipped": skipped or [],
        "counts": {"files": len(entries), "by_scope": by_scope},
        "files": dict(sorted(entries.items(), key=lambda kv: kv[0].lower())),
    }


def destination_of(cfg: dict) -> str:
    """A stable string identifying where a publish goes."""
    dely = cfg.get("delivery", {})
    backend = dely.get("backend", "")
    if backend == "rclone":
        rc = dely.get("rclone", {})
        return "rclone:%s:%s" % (rc.get("remote", ""), (rc.get("path") or "").strip("/"))
    return "%s:%s" % (backend, dely.get("local", {}).get("path", ""))


def diff(old: dict, new: dict) -> Diff:
    """Compare two manifests by content hash."""
    old_files = (old or {}).get("files", {}) or {}
    new_files = (new or {}).get("files", {}) or {}

    added, changed, unchanged = [], [], []
    for dest, meta in sorted(new_files.items()):
        if dest not in old_files:
            added.append(dest)
        elif old_files[dest].get("sha256") != meta.get("sha256"):
            changed.append(dest)
        else:
            unchanged.append(dest)
    removed = sorted(d for d in old_files if d not in new_files)
    return Diff(added, changed, removed, unchanged)


def dumps(man: dict) -> str:
    return json.dumps(man, indent=2, ensure_ascii=False) + "\n"


def load(path: str) -> dict:
    """Load a manifest, or return an empty one if it is absent/unreadable.

    A corrupt manifest must never block a publish - it only costs us the
    incremental optimisation, so we degrade to a full publish.
    """
    if not path or not os.path.isfile(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def version_txt(man: dict) -> str:
    """A human-glanceable stamp for the drive root."""
    git = man.get("git", {})
    lines = [
        "%s asset library" % man.get("library_name", "Published"),
        "",
        "published (UTC) : %s" % man.get("generated_utc", "?"),
        "source commit   : %s" % git.get("commit", "?"),
        "source branch   : %s" % git.get("branch", "?"),
        "files           : %s" % man.get("counts", {}).get("files", "?"),
    ]
    if git.get("dirty"):
        lines.append("")
        lines.append("WARNING: published from a DIRTY working tree.")
    return "\n".join(lines) + "\n"


def readme_txt(man: dict, cfg: dict) -> str:
    """Dropped at the drive root so nobody mistakes the mirror for a source."""
    renamed = man.get("catalog", {}).get("renamed", [])
    rename_lines = ["  %s  ->  %s" % (old, new) for old, new in renamed] or ["  (none)"]
    return "\n".join(
        [
            "%s - PUBLISHED BLENDER ASSET LIBRARY (read-only mirror)" % cfg.get("library_name", ""),
            "=" * 70,
            "",
            "This folder is generated. Do NOT edit anything in here: the next",
            "publish overwrites it. The source of truth is the git repository.",
            "",
            "How to use it in Blender",
            "------------------------",
            "  Preferences > File Paths > Asset Libraries > add this folder.",
            "  Name it '%s'. Its catalogs are renamed on publish, so it sits" % cfg.get("library_name", ""),
            "  beside a local copy of the same library instead of merging with it.",
            "",
            "  Google Drive tip: mark this folder 'Available offline' in Drive for",
            "  Desktop. In streaming mode the first open of each .blend stalls",
            "  while Drive fetches it.",
            "",
            "Catalog renames applied",
            "-----------------------",
        ]
        + rename_lines
        + [
            "",
            "Provenance",
            "----------",
            "  see publish_manifest.json (commit, per-file hashes, skipped files)",
            "",
        ]
    )
