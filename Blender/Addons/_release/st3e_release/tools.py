"""Find the releasable tools under Blender/Addons and read their current state."""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from . import versions
from .spec import Spec, load_spec


@dataclass
class Tool:
    root: Path
    spec: Spec | None

    @property
    def name(self) -> str:
        return self.root.name

    @property
    def source_dir(self) -> Path:
        if self.spec:
            return self.root / self.spec.source_dir
        for name in ("source", "addon"):
            if (self.root / name).is_dir():
                return self.root / name
        return self.root / "source"

    @property
    def distribution(self) -> Path:
        return self.root / "distribution"

    @property
    def archive(self) -> Path:
        return self.distribution / "archive"

    @property
    def manifest(self) -> Path:
        return self.source_dir / "blender_manifest.toml"

    def main_module(self) -> Path | None:
        return versions.find_main_module(self.source_dir)

    def code_version(self) -> versions.Version | None:
        main = self.main_module()
        return versions.read_code_version(main) if main else None

    def manifest_version(self) -> versions.Version | None:
        return versions.read_manifest_version(self.manifest)

    def version(self) -> versions.Version:
        """The released version: bl_info, falling back to the manifest."""
        v = self.code_version() or self.manifest_version()
        if v is None:
            raise versions.VersionError(f"{self.name}: no version in bl_info or the manifest")
        return v

    def current_zips(self) -> list[Path]:
        return sorted(self.distribution.glob("*.zip"))

    def zip_name(self, version: versions.Version) -> str:
        if not self.spec:
            raise versions.VersionError(f"{self.name}: no release.toml")
        return f"{self.spec.zip_stem}_v{versions.fmt(version)}.zip"


def zip_version(path: Path) -> versions.Version | None:
    m = re.search(rf"_v({versions.VERSION_PATTERN})\.zip$", path.name)
    return versions.parse(m.group(1)) if m else None


def discover(addons_dir: Path) -> list[Tool]:
    """Every folder with a distribution/ -- that is what makes it a released tool."""
    return [
        Tool(root=p, spec=load_spec(p))
        for p in sorted(addons_dir.iterdir(), key=lambda p: p.name.lower())
        if p.is_dir() and (p / "distribution").is_dir()
    ]


def _key(text: str) -> str:
    return re.sub(r"[\s_\-]", "", text).lower()


def resolve(tools: list[Tool], query: str) -> Tool:
    """Match by folder name or zip stem, ignoring case, spaces, - and _."""
    key = _key(query)
    hits = [t for t in tools if _key(t.name) == key or (t.spec and _key(t.spec.zip_stem) == key)]
    if not hits:
        hits = [t for t in tools if key in _key(t.name)]
    if len(hits) != 1:
        names = ", ".join(t.name for t in (hits or tools))
        raise LookupError(f"{query!r} matches {'no tool' if not hits else 'several tools'}: {names}")
    return hits[0]
