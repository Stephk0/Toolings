"""Build, verify and archive a tool's installable zip. Never deletes a zip: the previous
one moves to distribution/archive/, and a version that is already archived is refused."""
from __future__ import annotations

import os
import shutil
import zipfile
from dataclasses import dataclass, field
from pathlib import Path

from . import versions
from .spec import archive_name, collect, unclassified
from .tools import Tool

# Fixed timestamp: the same sources always give a byte-identical zip.
_ZIP_TIME = (2020, 1, 1, 0, 0, 0)


class BuildError(Exception):
    pass


@dataclass
class BuildResult:
    zip_path: Path
    status: str  # "built" | "up-to-date" | "dry-run"
    archived: list[Path] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def _normalized(data: bytes) -> bytes:
    """Text files compare without regard to CRLF vs LF (git autocrlf rewrites them)."""
    return data if b"\0" in data else data.replace(b"\r\n", b"\n")


def zip_diff(zip_path: Path, wrapper: str, files: dict[str, Path]) -> list[str]:
    """How the zip differs from what a build would produce now; empty means identical."""
    wanted = {archive_name(wrapper, pub): src for pub, src in files.items()}
    out = []
    with zipfile.ZipFile(zip_path) as zf:
        have = {n for n in zf.namelist() if not n.endswith("/")}
        out += [f"+ {n}" for n in sorted(wanted.keys() - have)]
        out += [f"- {n}" for n in sorted(have - wanted.keys())]
        for name in sorted(wanted.keys() & have):
            if _normalized(zf.read(name)) != _normalized(wanted[name].read_bytes()):
                out.append(f"~ {name}")
    return out


def write_zip(zip_path: Path, wrapper: str, files: dict[str, Path]) -> None:
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for pub in sorted(files):
            info = zipfile.ZipInfo(archive_name(wrapper, pub), date_time=_ZIP_TIME)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            zf.writestr(info, files[pub].read_bytes())


def verify_zip(zip_path: Path, wrapper: str, version: versions.Version) -> list[str]:
    """Problems with a built zip: it must install as an addon of exactly `version`."""
    problems = []
    init_name = archive_name(wrapper, "__init__.py")
    manifest_name = archive_name(wrapper, "blender_manifest.toml")
    with zipfile.ZipFile(zip_path) as zf:
        names = set(zf.namelist())
        if init_name not in names:
            problems.append(f"no {init_name} -- Blender cannot install this")
        for name in sorted(n for n in names if n.endswith(".py")):
            try:
                compile(zf.read(name), name, "exec")
            except (SyntaxError, ValueError) as exc:
                problems.append(f"{name}: does not compile: {exc}")
        if init_name in names:
            code_v = versions.code_version_from_text(zf.read(init_name).decode("utf-8"))
            if code_v is not None and code_v != version:
                problems.append(f"bl_info version {versions.fmt(code_v)} != {versions.fmt(version)}")
        if manifest_name in names:
            man_v = versions.manifest_version_from_text(zf.read(manifest_name).decode("utf-8"))
            if man_v != version:
                problems.append(f"manifest version {man_v and versions.fmt(man_v)} != {versions.fmt(version)}")
    return problems


def check_versions(tool: Tool) -> versions.Version:
    code_v, man_v = tool.code_version(), tool.manifest_version()
    if code_v and man_v and code_v != man_v:
        raise BuildError(f"{tool.name}: bl_info says {versions.fmt(code_v)}, "
                         f"blender_manifest.toml says {versions.fmt(man_v)}")
    return tool.version()


def build(tool: Tool, *, force: bool = False, dry_run: bool = False) -> BuildResult:
    if not tool.spec:
        raise BuildError(f"{tool.name}: no release.toml -- run `release.py init {tool.name}` first")
    version = check_versions(tool)
    files = collect(tool.root, tool.spec)
    if "__init__.py" not in files:
        raise BuildError(f"{tool.name}: the spec publishes no __init__.py")

    target = tool.distribution / tool.zip_name(version)
    if (tool.archive / target.name).exists():
        raise BuildError(f"{target.name} is already in archive/ -- bump the version first")

    warnings = [f"not in include/exclude: {rel}" for rel in unclassified(tool.root, tool.spec)]
    result = BuildResult(target, "dry-run", warnings=warnings)

    if target.exists():
        diff = zip_diff(target, tool.spec.wrapper, files)
        if not diff:
            result.status = "up-to-date"
            return result
        if not force:
            raise BuildError(
                f"{target.name} exists and differs from the source ({len(diff)} entries) -- "
                "bump the version, or pass --force to rebuild it in place")

    others = [z for z in tool.current_zips() if z != target]
    for z in others:
        if (tool.archive / z.name).exists():
            raise BuildError(f"cannot archive {z.name}: archive/ already has a file of that name")
    result.archived = [tool.archive / z.name for z in others]
    if dry_run:
        return result

    tmp = target.with_name(target.name + ".tmp")
    try:
        write_zip(tmp, tool.spec.wrapper, files)
        problems = verify_zip(tmp, tool.spec.wrapper, version)
        if problems:
            raise BuildError(f"{tool.name}: built zip failed verification:\n  " + "\n  ".join(problems))
        if others:
            tool.archive.mkdir(exist_ok=True)
        for z in others:
            shutil.move(z, tool.archive / z.name)
        os.replace(tmp, target)
    finally:
        tmp.unlink(missing_ok=True)
    result.status = "built"
    return result
