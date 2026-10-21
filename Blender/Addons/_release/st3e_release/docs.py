"""Version references outside the code: the tool README and DOCUMENTATION_INDEX.md.
Only known slots are touched (a "**Version:**" line, a version badge, the
title, the current zip's file name) -- history such as "since v1.2.0" is left alone."""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import quote

from . import versions
from .tools import Tool

V = versions.VERSION_PATTERN

_README_SLOTS = [
    re.compile(rf"(\*\*Version:?\*\*:?\s*)({V})"),
    re.compile(rf"(badge/version-)({V})(?=-)"),
    re.compile(rf"^(#\s.*\bv)({V})(?=\s*$)"),
]
_INDEX_SLOT = re.compile(rf"^(\|[^|]*\|\s*)({V})(?=\s*\|)")


@dataclass
class Edit:
    path: Path
    line: int  # 1-based
    old: str
    new: str


def _zip_slot(stem: str) -> re.Pattern:
    return re.compile(rf"({re.escape(stem)}_v)({V})(?=\.zip)")


def _scan(path: Path, slots: list[re.Pattern], line_filter=None,
          new_version: str | None = None) -> tuple[list[str], list[Edit]]:
    """Versions found in the slots, and the edits that would set them to new_version."""
    if not path.is_file():
        return [], []
    found, edits = [], []
    for no, line in enumerate(versions.read_text(path).splitlines(keepends=True), 1):
        if line_filter and not line_filter(line):
            continue
        new_line = line
        for slot in slots:
            found += [m.group(2) for m in slot.finditer(line)]
            if new_version:
                new_line = slot.sub(lambda m: m.group(1) + new_version, new_line)
        if new_line != line:
            edits.append(Edit(path, no, line, new_line))
    return found, edits


def readme(tool: Tool, new_version: str | None = None):
    slots = list(_README_SLOTS)
    if tool.spec:
        slots.append(_zip_slot(tool.spec.zip_stem))
    return _scan(tool.root / "README.md", slots, new_version=new_version)


def index(repo_root: Path, tool: Tool, new_version: str | None = None):
    rel = tool.root.relative_to(repo_root).as_posix()
    link = f"({quote(rel)}/README.md)"
    return _scan(repo_root / "DOCUMENTATION_INDEX.md", [_INDEX_SLOT],
                 lambda line: line.startswith("| **") and link in line, new_version)


def all_edits(repo_root: Path, tool: Tool, new_version: str) -> list[Edit]:
    return readme(tool, new_version)[1] + index(repo_root, tool, new_version)[1]


def apply(edits: list[Edit]) -> None:
    by_path: dict[Path, list[Edit]] = {}
    for e in edits:
        by_path.setdefault(e.path, []).append(e)
    for path, file_edits in by_path.items():
        lines = versions.read_text(path).splitlines(keepends=True)
        for e in file_edits:
            if lines[e.line - 1] != e.old:
                raise RuntimeError(f"{path}:{e.line} changed since it was read")
            lines[e.line - 1] = e.new
        versions.write_text(path, "".join(lines))


def changelog_mentions(tool: Tool, version: str) -> bool | None:
    """None when the tool has no changelog."""
    for path in (tool.source_dir / "CHANGELOG.md", tool.root / "CHANGELOG.md"):
        if path.is_file():
            return re.search(rf"(?<![\d.]){re.escape(version)}(?![\d.])",
                             versions.read_text(path)) is not None
    return None
