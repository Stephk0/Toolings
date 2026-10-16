"""Read and write an addon's version: bl_info / VERSION in the main module, and
blender_manifest.toml. Text in, text out -- files keep their own line endings."""
from __future__ import annotations

import re
from pathlib import Path

VERSION_PATTERN = r"\d+(?:\.\d+)+"

_BL_INFO_VERSION = re.compile(r"""(["']version["']\s*:\s*)(\([^)]*\)|[A-Za-z_]\w*)""")
_MANIFEST_VERSION = re.compile(r'(?m)^(version\s*=\s*")([^"]*)(")')

Version = tuple[int, ...]


class VersionError(Exception):
    pass


def parse(text: str) -> Version:
    text = text.strip()
    if text[:1] in "vV":
        text = text[1:]
    if not re.fullmatch(VERSION_PATTERN, text):
        raise VersionError(f"not a version: {text!r}")
    return tuple(int(p) for p in text.split("."))


def fmt(version: Version) -> str:
    return ".".join(str(p) for p in version)


def bump(version: Version, part: str) -> Version:
    """`part` is major / minor / patch, or an explicit version like 1.4.0."""
    index = {"major": 0, "minor": 1, "patch": 2}.get(part)
    if index is None:
        return parse(part)
    parts = list(version) + [0] * (3 - len(version))
    parts[index] += 1
    for i in range(index + 1, len(parts)):
        parts[i] = 0
    return tuple(parts)


# ---------------------------------------------------------------- file helpers

def read_text(path: Path) -> str:
    with open(path, encoding="utf-8", newline="") as f:
        return f.read()


def write_text(path: Path, text: str) -> None:
    with open(path, "w", encoding="utf-8", newline="") as f:
        f.write(text)


# ---------------------------------------------------------------- bl_info

def _tuple_text(version: Version) -> str:
    return "(" + ", ".join(str(p) for p in version) + ")"


def _parse_tuple(text: str) -> Version:
    inner = text.strip()[1:-1]
    try:
        return tuple(int(p) for p in inner.split(",") if p.strip())
    except ValueError as exc:
        raise VersionError(f"version tuple is not all integers: {text}") from exc


def _code_version_span(text: str) -> tuple[int, int] | None:
    """Span of the version tuple literal that bl_info["version"] resolves to."""
    start = text.find("bl_info")
    if start < 0:
        return None
    m = _BL_INFO_VERSION.search(text, start)
    if not m:
        return None
    value = m.group(2)
    if value.startswith("("):
        return m.start(2), m.end(2)
    const = re.search(rf"(?m)^{re.escape(value)}\s*=\s*(\([^)]*\))", text)
    if not const:
        raise VersionError(f'bl_info "version" refers to {value}, which is not a tuple literal')
    return const.start(1), const.end(1)


def code_version_from_text(text: str) -> Version | None:
    span = _code_version_span(text)
    return _parse_tuple(text[span[0]:span[1]]) if span else None


def find_main_module(source_dir: Path) -> Path | None:
    """The module that holds bl_info: __init__.py, or the single .py of a one-file addon."""
    init = source_dir / "__init__.py"
    if init.is_file() and "bl_info" in read_text(init):
        return init
    found = [p for p in sorted(source_dir.glob("*.py")) if "bl_info" in read_text(p)]
    if len(found) > 1:
        names = ", ".join(p.name for p in found)
        raise VersionError(f"{source_dir}: several modules define bl_info ({names})")
    return found[0] if found else None


def read_code_version(path: Path) -> Version | None:
    return code_version_from_text(read_text(path))


def write_code_version(path: Path, version: Version) -> None:
    text = read_text(path)
    span = _code_version_span(text)
    if not span:
        raise VersionError(f"{path}: no bl_info version to update")
    write_text(path, text[:span[0]] + _tuple_text(version) + text[span[1]:])


# ---------------------------------------------------------------- manifest

def manifest_version_from_text(text: str) -> Version | None:
    m = _MANIFEST_VERSION.search(text)
    return parse(m.group(2)) if m else None


def read_manifest_version(path: Path) -> Version | None:
    return manifest_version_from_text(read_text(path)) if path.is_file() else None


def write_manifest_version(path: Path, version: Version) -> None:
    text = read_text(path)
    new, count = _MANIFEST_VERSION.subn(lambda m: m.group(1) + fmt(version) + m.group(3), text, 1)
    if not count:
        raise VersionError(f"{path}: no version line to update")
    write_text(path, new)
