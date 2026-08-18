"""In-Blender inspection driver for LibraryPublisher criteria checks.

Runs ONE headless Blender session over every .blend the active checks apply to,
opens each file, and emits a single fenced JSON payload of raw facts. All policy
(warn vs block, which rules are blocking) lives in the bpy-free `core/criteria.py`
- this script only gathers, it never judges.

Invoked as:
    blender --background --factory-startup --python blender_inspect.py -- <batch.json>

The batch file is written by `core.publish`; the payload comes back on stdout
between the ST3E_INSPECT markers, because Blender's stdout is full of unrelated
startup chatter.
"""

import json
import os
import sys
import tempfile
import traceback

import bpy

JSON_BEGIN = "<<<ST3E_INSPECT_JSON>>>"
JSON_END = "<<<ST3E_INSPECT_END>>>"

# Datablock collections that can carry asset metadata and that we actually publish.
ASSET_COLLECTIONS = (
    "node_groups",
    "objects",
    "materials",
    "collections",
    "worlds",
    "images",
    "actions",
    "brushes",
    "scenes",
)


def _jsonable(value, _depth=0):
    """Coerce audit output into something json.dumps can handle."""
    if _depth > 6:
        return str(value)
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if isinstance(value, dict):
        return {str(k): _jsonable(v, _depth + 1) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_jsonable(v, _depth + 1) for v in value]
    return str(value)


def _bundled_roots():
    """Directories holding Blender's OWN shipped data.

    Blender 5 auto-links its essentials brush assets into every file. Those are
    absolute paths into the install dir, they exist on every machine, and they
    are not ours - so they must not be mistaken for a broken dependency or for a
    published asset. Everything under these roots is filtered out.
    """
    roots = []
    for getter in (
        lambda: bpy.utils.resource_path("LOCAL"),
        lambda: bpy.utils.resource_path("SYSTEM"),
        lambda: os.path.dirname(bpy.app.binary_path),
    ):
        try:
            path = getter()
        except Exception:
            continue
        if path:
            roots.append(os.path.normcase(os.path.normpath(path)))
    return roots


def _temp_roots():
    """Directories whose contents are never a real dependency.

    Blender writes its Ctrl+C paste buffer to <temp>/copybuffer.blend, and any
    headless session that saved a working copy leaves a weak reference into temp
    behind. Neither is something a published file actually needs, and both would
    otherwise block a perfectly good asset.
    """
    roots = []
    for getter in (tempfile.gettempdir, lambda: getattr(bpy.app, "tempdir", "")):
        try:
            path = getter()
        except Exception:
            continue
        if path:
            roots.append(os.path.normcase(os.path.normpath(path)))
    return roots


def _under_any(path, roots):
    if not path:
        return False
    normalised = os.path.normcase(os.path.normpath(path))
    return any(normalised.startswith(root) for root in roots)


def _is_bundled(path, roots):
    if not path:
        return False
    normalised = os.path.normcase(os.path.normpath(path))
    if any(normalised.startswith(root) for root in roots):
        return True
    # Belt and braces for an unusual install layout.
    return os.path.join("datafiles", "assets") in normalised


def _collect_assets(bundled_roots):
    """Asset-marked datablocks that this file actually owns.

    LINKED datablocks are skipped: an asset linked in from Blender's essentials
    (or from any other library) is not published by this file, so counting it
    would both inflate `asset_marked` and make `catalog_assigned` complain about
    catalogs that belong to somebody else.
    """
    found = []
    for coll_name in ASSET_COLLECTIONS:
        coll = getattr(bpy.data, coll_name, None)
        if coll is None:
            continue
        for datablock in coll:
            asset_data = getattr(datablock, "asset_data", None)
            if asset_data is None:
                continue
            if getattr(datablock, "library", None) is not None:
                continue  # linked in from elsewhere, not ours to publish
            if getattr(datablock, "override_library", None) is not None:
                continue
            try:
                tags = [t.name for t in asset_data.tags]
            except Exception:
                tags = []
            found.append({
                "name": datablock.name,
                "collection": coll_name,
                "catalog_id": getattr(asset_data, "catalog_id", "") or "",
                "catalog_simple_name": getattr(asset_data, "catalog_simple_name", "") or "",
                "tags": tags,
                "description": getattr(asset_data, "description", "") or "",
            })
    return found


def _collect_libraries(bundled_roots):
    """Linked .blend libraries, flagging absolute paths (they break on a share).

    Blender's own bundled asset libraries are reported with `is_bundled` so the
    policy layer can ignore them; they are absolute by nature and harmless.
    """
    out = []
    for lib in bpy.data.libraries:
        raw = lib.filepath or ""
        try:
            resolved = bpy.path.abspath(raw)
        except Exception:
            resolved = raw
        bundled = _is_bundled(resolved, bundled_roots) or _is_bundled(raw, bundled_roots)
        temp_roots = _temp_roots()
        out.append({
            "filepath": raw,
            # A relative link starts with '//'. Anything else is machine-specific.
            "is_absolute": bool(raw) and not raw.startswith("//"),
            "exists": bool(resolved) and os.path.isfile(resolved),
            "is_bundled": bundled,
            "is_temp": _under_any(resolved, temp_roots) or _under_any(raw, temp_roots),
        })
    return out


def _collect_missing_files(bundled_roots):
    """External paths the file references that are not on disk."""
    missing = []
    try:
        paths = bpy.utils.blend_paths(absolute=True, packed=False, local=False)
    except Exception:
        return missing
    temp_roots = _temp_roots()
    for path in paths:
        if not path or _is_bundled(path, bundled_roots):
            continue
        if _under_any(path, temp_roots):
            continue  # paste buffer / scratch copies, never a real dependency
        if not os.path.exists(path):
            missing.append(path)
    return sorted(set(missing))


def _audit_targets(assets, file_stem):
    """Geometry-node trees worth auditing: the asset-marked ones, else the
    file-stem group (the older one-group-per-file convention)."""
    targets = []
    asset_names = {a["name"] for a in assets if a["collection"] == "node_groups"}
    for group in bpy.data.node_groups:
        if getattr(group, "bl_idname", "") != "GeometryNodeTree":
            continue
        if group.name in asset_names:
            targets.append(group)
    if not targets:
        group = bpy.data.node_groups.get(file_stem)
        if group is not None and getattr(group, "bl_idname", "") == "GeometryNodeTree":
            targets.append(group)
    return targets


def _run_layout_audit(audit_module, assets, file_stem):
    """R1-R11 per node group, reusing LLMGeonodePipeline's audit verbatim."""
    audits = {}
    if audit_module is None:
        return audits
    for group in _audit_targets(assets, file_stem):
        try:
            audits[group.name] = _jsonable(audit_module.audit(group))
        except Exception as exc:
            audits[group.name] = {"error": "%s: %s" % (type(exc).__name__, exc)}
    return audits


def _import_audit_module(audit_dir):
    if not audit_dir or not os.path.isdir(audit_dir):
        return None, "audit_module_dir not found: %s" % audit_dir
    if audit_dir not in sys.path:
        sys.path.insert(0, audit_dir)
    try:
        import layout_audit  # noqa: WPS433 - deliberately late, needs sys.path first
        return layout_audit, ""
    except Exception as exc:
        return None, "could not import layout_audit: %s" % exc


def main():
    argv = sys.argv
    if "--" not in argv:
        _emit({"reports": [], "error": "no batch file argument"})
        return
    batch_path = argv[argv.index("--") + 1]
    with open(batch_path, "r", encoding="utf-8") as fh:
        batch = json.load(fh)

    checks = set(batch.get("checks") or [])
    audit_module = None
    audit_error = ""
    if "geonode_layout" in checks:
        audit_module, audit_error = _import_audit_module(batch.get("audit_module_dir", ""))

    reports = []
    for item in batch.get("files") or []:
        src = item.get("src", "")
        report = {"src": src, "dest": item.get("dest", ""), "scope": item.get("scope", "")}
        try:
            bpy.ops.wm.open_mainfile(filepath=src, load_ui=False)
        except Exception as exc:
            report["error"] = "open failed: %s" % exc
            reports.append(report)
            continue

        try:
            bundled_roots = _bundled_roots()
            assets = _collect_assets(bundled_roots)
            report["assets"] = assets
            if "no_external_deps" in checks:
                report["libraries"] = _collect_libraries(bundled_roots)
                report["missing_files"] = _collect_missing_files(bundled_roots)
            if "geonode_layout" in checks:
                stem = os.path.splitext(os.path.basename(src))[0]
                report["audits"] = _run_layout_audit(audit_module, assets, stem)
        except Exception:
            report["error"] = "inspect failed: %s" % traceback.format_exc(limit=3)
        reports.append(report)

    _emit({"reports": reports, "audit_error": audit_error})


def _emit(payload):
    sys.stdout.write("\n" + JSON_BEGIN + "\n")
    sys.stdout.write(json.dumps(payload))
    sys.stdout.write("\n" + JSON_END + "\n")
    sys.stdout.flush()


if __name__ == "__main__":
    try:
        main()
    except Exception:
        _emit({"reports": [], "error": traceback.format_exc(limit=5)})
    # Blender's own teardown can emit noise or a non-zero code after our payload
    # is already written; exit hard so the parent sees a clean result.
    sys.stdout.flush()
    sys.stderr.flush()
    os._exit(0)
