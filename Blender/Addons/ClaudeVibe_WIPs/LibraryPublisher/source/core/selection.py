"""Turn scope config into a concrete, deterministic file list.

The published library is *curated*, not mirrored: a raw copy of `Blender/` would
ship `_backup_publish_fix/`, `*_fixed.blend`, `TreeGenDocu/` iteration files and
the whole addon source tree. Every publish therefore goes through include/exclude
patterns per scope entry.

bpy-free and filesystem-read-only.
"""

from __future__ import annotations

import os
import re
from typing import NamedTuple


class SelectedFile(NamedTuple):
    src: str        # absolute source path
    dest: str       # destination path relative to the published library root
    scope: str      # scope entry name that claimed it
    size: int       # bytes
    mtime: float    # source mtime, for reporting only (hashes decide freshness)


class Selection(NamedTuple):
    files: list      # list[SelectedFile], sorted by dest
    warnings: list   # human-readable, non-fatal
    per_scope: dict  # scope name -> file count


def _glob_to_regex(pattern: str) -> re.Pattern:
    """Compile a glob with `**` support into a regex matched against a posix path.

    `**` crosses directory separators, `*` and `?` do not - the usual gitignore
    reading, which is what the config patterns are written against.
    """
    out = ["^"]
    i = 0
    n = len(pattern)
    while i < n:
        ch = pattern[i]
        if ch == "*":
            if pattern.startswith("**/", i):
                out.append("(?:.*/)?")
                i += 3
                continue
            if pattern.startswith("**", i):
                out.append(".*")
                i += 2
                continue
            out.append("[^/]*")
            i += 1
            continue
        if ch == "?":
            out.append("[^/]")
            i += 1
            continue
        out.append(re.escape(ch))
        i += 1
    out.append("$")
    return re.compile("".join(out), re.IGNORECASE if os.name == "nt" else 0)


def matches(rel_posix: str, pattern: str) -> bool:
    """Match a relative posix path against one glob pattern.

    A pattern with no `/` is matched against the *basename* (so `*_fixed.blend`
    excludes that file at any depth); a pattern with `/` is matched against the
    full relative path.
    """
    target = rel_posix if "/" in pattern else rel_posix.rsplit("/", 1)[-1]
    return _glob_to_regex(pattern).match(target) is not None


def matches_any(rel_posix: str, patterns: list) -> bool:
    return any(matches(rel_posix, p) for p in patterns or [])


def _walk_files(base: str, recursive: bool) -> list:
    """Relative posix paths of every file under `base`."""
    found = []
    if not os.path.isdir(base):
        return found
    if not recursive:
        for name in sorted(os.listdir(base)):
            if os.path.isfile(os.path.join(base, name)):
                found.append(name)
        return found
    for root, dirnames, filenames in os.walk(base):
        dirnames.sort()
        for name in sorted(filenames):
            abs_path = os.path.join(root, name)
            rel = os.path.relpath(abs_path, base).replace(os.sep, "/")
            found.append(rel)
    return found


def select(cfg: dict) -> Selection:
    """Resolve every enabled scope entry into concrete source->dest pairs."""
    repo_root = cfg["source"]["repo_root"]
    files = []
    warnings = []
    per_scope = {}

    for entry in cfg.get("scope", {}).get("entries", []):
        name = entry.get("name") or "<unnamed>"
        if not entry.get("enabled"):
            continue
        base = os.path.normpath(os.path.join(repo_root, entry.get("src", "")))
        if not os.path.isdir(base):
            warnings.append("scope '%s': src does not exist, skipped: %s" % (name, base))
            per_scope[name] = 0
            continue

        include = entry.get("include") or []
        exclude = entry.get("exclude") or []
        dest_root = (entry.get("dest") or "").strip("/")
        flatten = bool(entry.get("flatten"))

        count = 0
        for rel in _walk_files(base, bool(entry.get("recursive"))):
            if not matches_any(rel, include):
                continue
            if matches_any(rel, exclude):
                continue
            src_abs = os.path.join(base, rel.replace("/", os.sep))
            leaf = rel.rsplit("/", 1)[-1] if flatten else rel
            dest_rel = "%s/%s" % (dest_root, leaf) if dest_root else leaf
            try:
                stat = os.stat(src_abs)
            except OSError as exc:
                warnings.append("scope '%s': cannot stat %s (%s)" % (name, src_abs, exc))
                continue
            files.append(
                SelectedFile(src_abs, dest_rel, name, stat.st_size, stat.st_mtime)
            )
            count += 1

        if count == 0:
            warnings.append(
                "scope '%s': matched 0 files under %s - check include/exclude patterns"
                % (name, base)
            )
        per_scope[name] = count

    files.sort(key=lambda f: f.dest.lower())

    # Flatten can silently collapse two sources onto one destination; that would
    # publish whichever copied last. Surface it instead.
    by_dest = {}
    for item in files:
        by_dest.setdefault(item.dest.lower(), []).append(item)
    for dest, group in sorted(by_dest.items()):
        if len(group) > 1:
            warnings.append(
                "destination collision on '%s': %s"
                % (group[0].dest, ", ".join(g.src for g in group))
            )

    return Selection(files, warnings, per_scope)
