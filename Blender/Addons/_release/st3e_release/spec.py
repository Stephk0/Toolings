"""release.toml: which files a tool's zip contains and how they are laid out.

    zip_stem   = "CenterEdges"   # zip name is <zip_stem>_v<version>.zip
    wrapper    = "CenterEdges"   # folder inside the zip; "" = files at the archive root
    source_dir = "source"
    include    = ["*.py", "blender/**"]   # globs relative to source_dir
    exclude    = ["tests/**"]
    [files]                      # published path = source path relative to the tool folder
    "__init__.py" = "source/center_loops_addon.py"

`infer_spec` writes this from the tool's current zip, so a new build reproduces the
previous layout exactly.
"""
from __future__ import annotations

import json
import re
import tomllib
import zipfile
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath

from . import versions

SPEC_NAME = "release.toml"
SKIP_DIRS = {"__pycache__", ".pytest_cache", ".git"}
SKIP_SUFFIXES = {".pyc", ".pyo", ".blend1"}


class SpecError(Exception):
    pass


@dataclass
class Spec:
    zip_stem: str
    wrapper: str = ""
    source_dir: str = "source"
    include: list[str] = field(default_factory=list)
    exclude: list[str] = field(default_factory=list)
    files: dict[str, str] = field(default_factory=dict)


# ---------------------------------------------------------------- load / dump

def load_spec(tool_root: Path) -> Spec | None:
    path = tool_root / SPEC_NAME
    if not path.is_file():
        return None
    try:
        data = tomllib.loads(versions.read_text(path))
    except tomllib.TOMLDecodeError as exc:
        raise SpecError(f"{path}: {exc}") from exc
    unknown = set(data) - set(Spec.__dataclass_fields__)
    if unknown:
        raise SpecError(f"{path}: unknown keys {sorted(unknown)}")
    if "zip_stem" not in data:
        raise SpecError(f"{path}: zip_stem is required")
    return Spec(**data)


def _q(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


def dump_spec(spec: Spec, header: str = "") -> str:
    lines = [f"# {line}" if line else "#" for line in header.splitlines()]
    lines += [
        f"zip_stem = {_q(spec.zip_stem)}",
        f"wrapper = {_q(spec.wrapper)}  # folder inside the zip; \"\" = files at the archive root",
        f"source_dir = {_q(spec.source_dir)}",
        "include = [" + ", ".join(_q(p) for p in spec.include) + "]  # globs relative to source_dir",
        "exclude = [" + ", ".join(_q(p) for p in spec.exclude) + "]",
    ]
    if spec.files:
        lines += ["", "[files]  # published path = source path relative to the tool folder"]
        lines += [f"{_q(k)} = {_q(v)}" for k, v in sorted(spec.files.items())]
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------- globbing

def glob_regex(pattern: str) -> re.Pattern:
    """`*` stays inside one path segment, `**` crosses segments, `**/` may match nothing."""
    out, i = [], 0
    while i < len(pattern):
        if pattern.startswith("**/", i):
            out.append("(?:.*/)?")
            i += 3
        elif pattern.startswith("**", i):
            out.append(".*")
            i += 2
        elif pattern[i] == "*":
            out.append("[^/]*")
            i += 1
        elif pattern[i] == "?":
            out.append("[^/]")
            i += 1
        else:
            out.append(re.escape(pattern[i]))
            i += 1
    return re.compile("".join(out) + r"\Z")


def matches_any(patterns: list[str], rel: str) -> bool:
    return any(glob_regex(p).match(rel) for p in patterns)


# ---------------------------------------------------------------- collecting

def source_files(source_dir: Path) -> list[str]:
    """Every file under source_dir as a posix path, minus caches and backups."""
    if not source_dir.is_dir():
        return []
    out = []
    for path in source_dir.rglob("*"):
        rel = path.relative_to(source_dir)
        if not path.is_file() or SKIP_DIRS.intersection(rel.parts[:-1]):
            continue
        if path.suffix in SKIP_SUFFIXES:
            continue
        out.append(rel.as_posix())
    return sorted(out)


def _mapped_source_rels(tool_root: Path, spec: Spec) -> set[str]:
    """Source-dir-relative paths of files that [files] publishes under another name."""
    rels = set()
    prefix = spec.source_dir.rstrip("/") + "/"
    for src in spec.files.values():
        if src.startswith(prefix):
            rels.add(src[len(prefix):])
    return rels


def collect(tool_root: Path, spec: Spec) -> dict[str, Path]:
    """Published path (without the wrapper) -> source file."""
    source_dir = tool_root / spec.source_dir
    mapped = _mapped_source_rels(tool_root, spec)
    out: dict[str, Path] = {}
    for rel in source_files(source_dir):
        if rel in mapped or not matches_any(spec.include, rel) or matches_any(spec.exclude, rel):
            continue
        out[rel] = source_dir / rel
    for published, src in spec.files.items():
        path = tool_root / src
        if not path.is_file():
            raise SpecError(f"{tool_root.name}: [files] {published} -> {src} does not exist")
        out[published] = path
    return out


def unclassified(tool_root: Path, spec: Spec) -> list[str]:
    """Source files that neither include, exclude nor [files] mention -- usually a new
    module that needs a decision."""
    mapped = _mapped_source_rels(tool_root, spec)
    return [
        rel for rel in source_files(tool_root / spec.source_dir)
        if rel not in mapped
        and not matches_any(spec.include, rel)
        and not matches_any(spec.exclude, rel)
    ]


def archive_name(wrapper: str, published: str) -> str:
    return f"{wrapper}/{published}" if wrapper else published


# ---------------------------------------------------------------- inference

def zip_file_names(zip_path: Path) -> list[str]:
    with zipfile.ZipFile(zip_path) as zf:
        return [n for n in zf.namelist() if not n.endswith("/")]


def stem_from_zip_name(name: str) -> str:
    return re.sub(rf"(_v{versions.VERSION_PATTERN})?\.zip$", "", name)


def _patterns(chosen: set[str], others: set[str]) -> list[str]:
    """Short glob list matching every path in `chosen` and none in `others`."""
    pats: list[str] = []
    by_dir: dict[str, list[str]] = defaultdict(list)
    top_level: list[str] = []
    for rel in sorted(chosen):
        if "/" in rel:
            by_dir[rel.split("/", 1)[0]].append(rel)
        else:
            top_level.append(rel)
    for top, rels in sorted(by_dir.items()):
        if any(o.startswith(top + "/") for o in others):
            pats.extend(rels)
        else:
            pats.append(f"{top}/**")
    by_suffix: dict[str, list[str]] = defaultdict(list)
    for rel in top_level:
        by_suffix[PurePosixPath(rel).suffix].append(rel)
    for suffix, rels in sorted(by_suffix.items()):
        clash = any("/" not in o and PurePosixPath(o).suffix == suffix for o in others)
        if suffix and len(rels) > 1 and not clash:
            pats.append(f"*{suffix}")
        else:
            pats.extend(rels)
    return pats


def infer_spec(tool_root: Path, zip_path: Path) -> tuple[Spec, list[str]]:
    """A spec that reproduces `zip_path` from the tool's sources, plus any zip entries
    no source file could be found for."""
    names = zip_file_names(zip_path)
    tops = {n.split("/", 1)[0] for n in names}
    wrapper = tops.pop() if len(tops) == 1 and all("/" in n for n in names) else ""
    published = [n[len(wrapper) + 1:] if wrapper else n for n in names]

    source_dir_name = "source" if (tool_root / "source").is_dir() else "addon"
    source_dir = tool_root / source_dir_name
    all_src = set(source_files(source_dir))

    shipped: set[str] = set()
    files: dict[str, str] = {}
    problems: list[str] = []
    for pub in published:
        if pub in all_src:
            shipped.add(pub)
        elif (tool_root / pub).is_file():
            files[pub] = pub
        elif pub == "__init__.py" and (main := versions.find_main_module(source_dir)):
            files[pub] = f"{source_dir_name}/{main.name}"
        else:
            problems.append(f"{pub}: no matching file in the tool folder")

    spec = Spec(zip_stem=stem_from_zip_name(zip_path.name), wrapper=wrapper,
                source_dir=source_dir_name, files=files)
    unshipped = all_src - shipped - _mapped_source_rels(tool_root, spec)
    spec.include = _patterns(shipped, unshipped)
    spec.exclude = _patterns(unshipped, shipped)
    return spec, problems
