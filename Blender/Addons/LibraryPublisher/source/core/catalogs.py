"""Blender asset-catalog file parsing and the ST3E_Ext rewrite (Variant A).

A `blender_assets.cats.txt` line is `UUID:catalog/path:simple name`.
Every asset inside a .blend stores the catalog **UUID** (plus a cached simple
name for display). So renaming only the *path* and *simple name* while keeping
the UUID means the published .blend files need no edits at all - the assets
still resolve, they just appear under a differently-named tree.

That is the whole trick behind publishing `ST3E` as `ST3E_Ext`: the transform is
one text file, and the 66 .blend files are byte-identical copies.

bpy-free and pure - given the same input text you always get the same output.
"""

from __future__ import annotations

import uuid as _uuid
from typing import NamedTuple

VERSION_LINE = "VERSION 1"

DEFAULT_SIMPLE_NAME_SEPARATOR = "-"

# Namespace for deriving published catalog UUIDs. Any fixed UUID works; this one
# is uuid5(DNS, "st3e.library-publisher") so it is reproducible from a name
# rather than being a magic constant nobody can regenerate.
DEFAULT_UUID_NAMESPACE = "1b1b9119-7d76-5b04-9d02-a5df6e5f2ab9"


def derive_uuid(original: str, namespace: str = DEFAULT_UUID_NAMESPACE) -> str:
    """A new catalog UUID derived from the original, stably.

    uuid5 is a hash, not a random draw: the same original plus the same namespace
    always yields the same result, on any machine, forever. That matters because
    the published .blend files store this value - a UUID that drifted between
    runs would orphan every asset already on the drive.
    """
    return str(_uuid.uuid5(_uuid.UUID(namespace), original))


class CatalogEntry(NamedTuple):
    uuid: str
    path: str
    simple_name: str


class CatalogFile(NamedTuple):
    """A parsed catalog file, preserving enough to round-trip it."""

    version: str
    entries: list          # list[CatalogEntry], in file order
    header_comments: list  # comment/blank lines seen before the VERSION line


class CatalogRewrite(NamedTuple):
    text: str              # the rewritten file content
    renamed: list          # list[(old_path, new_path)]
    unchanged: list        # catalog paths that matched no rename rule
    uuid_map: dict         # uuid -> (old_path, new_path) for every renamed entry
    id_map: dict           # OLD uuid -> NEW uuid; empty unless UUIDs were remapped

    @property
    def remapped(self) -> bool:
        """True when the published .blend copies must have catalog_id rewritten."""
        return bool(self.id_map)

    def fingerprint(self) -> str:
        """A short stable digest of the id mapping.

        Any change to it invalidates every staged .blend, because their embedded
        catalog_id values were written against the previous mapping.
        """
        import hashlib

        if not self.id_map:
            return "none"
        blob = ";".join("%s>%s" % (k, self.id_map[k]) for k in sorted(self.id_map))
        return hashlib.sha256(blob.encode("utf-8")).hexdigest()[:16]


def parse(text: str) -> CatalogFile:
    """Parse catalog text. Tolerates comments, blank lines and a missing VERSION."""
    version = ""
    entries = []
    header_comments = []
    seen_version = False

    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            if not seen_version:
                header_comments.append(raw_line.rstrip("\n"))
            continue
        if not seen_version and line.upper().startswith("VERSION"):
            version = line
            seen_version = True
            continue
        # Blender splits on the first two colons only: the simple name is free
        # text and the path may contain spaces and ampersands.
        parts = line.split(":", 2)
        if len(parts) != 3:
            continue
        uuid, path, simple = parts
        entries.append(CatalogEntry(uuid.strip(), path.strip(), simple.strip()))

    return CatalogFile(version or VERSION_LINE, entries, header_comments)


def simple_name_for(path: str, separator: str = DEFAULT_SIMPLE_NAME_SEPARATOR) -> str:
    """Blender's own convention: the catalog path with '/' swapped for '-'."""
    return path.replace("/", separator)


def apply_renames(path: str, rules: list) -> str:
    """Rewrite the leading component(s) of a catalog path.

    A rule matches when the path IS `from` or is nested under `from/`, so
    `ST3E` -> `ST3E_Ext` turns `ST3E/Deform` into `ST3E_Ext/Deform` while
    leaving an unrelated `Foo/ST3E` alone. The first matching rule wins, so
    rules never cascade into each other.
    """
    for rule in rules:
        src = (rule.get("from") or "").strip("/")
        dst = (rule.get("to") or "").strip("/")
        if not src or not dst:
            continue
        if path == src:
            return dst
        if path.startswith(src + "/"):
            return dst + path[len(src):]
    return path


def rewrite(
    text: str,
    rules: list,
    *,
    separator: str = DEFAULT_SIMPLE_NAME_SEPARATOR,
    stamp: str = "",
    remap_namespace: str = "",
) -> CatalogRewrite:
    """Produce the published catalog text with paths + simple names renamed.

    With `remap_namespace` empty the UUIDs are carried across untouched, so the
    published .blend files need no rewrite at all (cheap, but both libraries then
    declare the same UUIDs).

    With a namespace given, every renamed entry also gets a NEW deterministic
    UUID. That makes the published catalogs genuinely distinct from the local
    ones - and obliges the caller to rewrite `asset_data.catalog_id` in the
    published .blend copies, because assets key on the UUID. `id_map` carries
    old -> new for exactly that purpose.
    """
    parsed = parse(text)

    renamed = []
    unchanged = []
    uuid_map = {}
    id_map = {}
    out_entries = []

    for entry in parsed.entries:
        new_path = apply_renames(entry.path, rules)
        if new_path == entry.path:
            unchanged.append(entry.path)
            out_entries.append(entry)
            continue
        new_uuid = entry.uuid
        if remap_namespace:
            new_uuid = derive_uuid(entry.uuid, remap_namespace)
            id_map[entry.uuid] = new_uuid
        new_entry = CatalogEntry(new_uuid, new_path, simple_name_for(new_path, separator))
        out_entries.append(new_entry)
        renamed.append((entry.path, new_path))
        uuid_map[entry.uuid] = (entry.path, new_path)

    lines = []
    lines.append("# Blender Asset Catalog Definition file - PUBLISHED COPY.")
    lines.append("# Generated by LibraryPublisher. Do not edit here: edits are")
    lines.append("# overwritten on the next publish. Source of truth is the git repo.")
    if stamp:
        for stamp_line in stamp.splitlines():
            lines.append("# " + stamp_line)
    lines.append("#")
    lines.append("# Catalog paths are renamed on publish so this library sits")
    lines.append("# beside the local one in Blender's Asset Browser.")
    if id_map:
        lines.append("# Catalog UUIDs are REMAPPED - derived deterministically from")
        lines.append("# the originals - so these catalogs are genuinely distinct from")
        lines.append("# the local ones, and the published .blend files carry the new")
        lines.append("# ids. Do not hand-edit a UUID here: it would orphan the assets.")
    else:
        lines.append("# UUIDs are preserved, so the .blend files are untouched copies.")
    lines.append("")
    lines.append(parsed.version)
    lines.append("")
    for entry in out_entries:
        lines.append("%s:%s:%s" % (entry.uuid, entry.path, entry.simple_name))

    return CatalogRewrite("\n".join(lines) + "\n", renamed, unchanged, uuid_map, id_map)


def known_uuids(text: str) -> set:
    """Every catalog UUID defined in the file - used by the catalog_assigned check."""
    return {entry.uuid for entry in parse(text).entries}
