"""release.py -- build, version and check the installable zips of the Blender addons.

  status [tool]           versions everywhere a tool records one, and what is out of date
  check                   same, exit code 1 if anything needs attention (for hooks / CI)
  init <tool>|--all       write release.toml from the tool's current zip
  bump <tool> <part>      set the version (major|minor|patch|X.Y.Z) in code, manifest and docs
  docs <tool>             re-sync README / index / docs-site to the code version
  build <tool>            build the zip, verify it, move the previous one to archive/
  release <tool> <part>   bump + build
"""
from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

from . import docs, versions
from .build import BuildError, build, check_versions, zip_diff
from .spec import SPEC_NAME, SpecError, collect, dump_spec, infer_spec, unclassified
from .tools import Tool, discover, resolve, zip_version

ADDONS_DIR = Path(__file__).resolve().parents[2]
REPO_ROOT = ADDONS_DIR.parents[1]
DOC_SUFFIXES = {".md", ".txt", ".rst"}


# ---------------------------------------------------------------- status

@dataclass
class Report:
    tool: Tool
    cells: dict[str, str] = field(default_factory=dict)
    issues: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)  # worth knowing, never fails `check`


def _v(v) -> str:
    return versions.fmt(v) if v else "-"


def _doc_cell(found: list[str], expected: str, label: str, report: Report) -> str:
    distinct = sorted(set(found))
    if not distinct:
        return "-"
    if distinct != [expected]:
        report.issues.append(f"{label} says {', '.join(distinct)}")
    return ",".join(distinct)


def _is_doc(name: str) -> bool:
    return Path(name).suffix.lower() in DOC_SUFFIXES or Path(name).name.upper().startswith("LICENSE")


def inspect(tool: Tool, repo_root: Path) -> Report:
    r = Report(tool)
    try:
        code_v, man_v = tool.code_version(), tool.manifest_version()
        version = tool.version()
    except versions.VersionError as exc:
        r.issues.append(str(exc))
        return r
    expected = versions.fmt(version)
    r.cells["code"] = _v(code_v)
    r.cells["manifest"] = _v(man_v)
    if code_v and man_v and code_v != man_v:
        r.issues.append("bl_info and manifest disagree")

    zips = tool.current_zips()
    r.cells["zip"] = ",".join(_v(zip_version(z)) for z in zips) or "-"
    if len(zips) != 1:
        r.issues.append(f"{len(zips)} zips in distribution/ (want 1)")
    elif zip_version(zips[0]) != version:
        r.issues.append(f"zip is {_v(zip_version(zips[0]))}, code is {expected} -- build it")

    r.cells["readme"] = _doc_cell(docs.readme(tool)[0], expected, "README", r)
    r.cells["index"] = _doc_cell(docs.index(repo_root, tool)[0], expected, "DOCUMENTATION_INDEX", r)
    r.cells["site"] = _doc_cell(docs.docsite(repo_root, tool)[0], expected, "docs-site", r)

    if not tool.spec:
        r.cells["spec"] = "no"
        r.issues.append(f"no {SPEC_NAME} -- run init")
        return r
    r.cells["spec"] = "yes"
    try:
        files = collect(tool.root, tool.spec)
    except SpecError as exc:
        r.issues.append(str(exc))
        return r
    if len(zips) == 1 and zip_version(zips[0]) == version:
        diff = zip_diff(zips[0], tool.spec.wrapper, files)
        code = [d for d in diff if not _is_doc(d[2:])]
        if code:
            r.issues.append(f"zip is stale, {len(code)} entries differ from source "
                            f"({', '.join(code[:3])}{', ...' if len(code) > 3 else ''}) -- bump + build")
        elif diff:
            r.notes.append(f"zip carries older docs ({', '.join(diff)}); they ship with the next build")
    for rel in unclassified(tool.root, tool.spec):
        r.issues.append(f"not in include/exclude: {rel}")
    return r


def print_reports(reports: list[Report]) -> None:
    cols = ["code", "manifest", "zip", "readme", "index", "site", "spec"]
    name_w = max(len(r.tool.name) for r in reports)
    widths = {c: max(len(c), *(len(r.cells.get(c, "")) for r in reports)) for c in cols}
    print("  ".join(["tool".ljust(name_w)] + [c.ljust(widths[c]) for c in cols]))
    for r in reports:
        mark = "!" if r.issues else " "
        print("  ".join([r.tool.name.ljust(name_w)] + [r.cells.get(c, "?").ljust(widths[c]) for c in cols]) + f"  {mark}")
    flagged = [r for r in reports if r.issues or r.notes]
    if flagged:
        print()
    for r in flagged:
        print(f"{r.tool.name}:")
        for issue in r.issues:
            print(f"  ! {issue}")
        for note in r.notes:
            print(f"  - {note}")


# ---------------------------------------------------------------- commands

def _tools(args) -> list[Tool]:
    return discover(Path(args.addons_dir))


def _repo(args) -> Path:
    return Path(args.addons_dir).resolve().parents[1]


def cmd_status(args) -> int:
    tools = _tools(args)
    if args.tool:
        tools = [resolve(tools, args.tool)]
    reports = [inspect(t, _repo(args)) for t in tools]
    print_reports(reports)
    return 1 if args.command == "check" and any(r.issues for r in reports) else 0


def cmd_init(args) -> int:
    tools = _tools(args)
    targets = tools if args.all else [resolve(tools, args.tool)]
    failed = 0
    for tool in targets:
        path = tool.root / SPEC_NAME
        if path.exists() and not args.force:
            print(f"{tool.name}: {SPEC_NAME} exists, skipped (--force to overwrite)")
            continue
        zips = tool.current_zips()
        if len(zips) != 1:
            print(f"{tool.name}: needs exactly one zip in distribution/ to infer from, found {len(zips)}")
            failed += 1
            continue
        spec, problems = infer_spec(tool.root, zips[0])
        header = (f"Release spec for {tool.name}, read by Blender/Addons/_release/release.py.\n"
                  f"Inferred from {zips[0].name} on {date.today().isoformat()}; edit freely.")
        if problems:
            print(f"{tool.name}: cannot reproduce {zips[0].name}:")
            for p in problems:
                print(f"  - {p}")
            failed += 1
            continue
        versions.write_text(path, dump_spec(spec, header))
        tool.spec = spec
        diff = zip_diff(zips[0], spec.wrapper, collect(tool.root, spec))
        layout = f"wrapped in {spec.wrapper}/" if spec.wrapper else "files at archive root"
        state = "matches the zip" if not diff else f"{len(diff)} entries differ from the zip (source changed since it was built)"
        names = {d[2:] for d in diff if d[0] in "+-"}
        if names:
            state = f"LAYOUT DIFFERS: {sorted(names)}"
            failed += 1
        print(f"{tool.name}: wrote {SPEC_NAME} ({layout}); {state}")
    return 1 if failed else 0


def _print_edits(edits: list[docs.Edit], repo_root: Path) -> None:
    for e in edits:
        rel = e.path.relative_to(repo_root).as_posix()
        print(f"  {rel}:{e.line}\n    - {e.old.strip()}\n    + {e.new.strip()}")


def _bump(tool: Tool, part: str, repo_root: Path, dry_run: bool) -> versions.Version:
    old = check_versions(tool)
    new = versions.bump(old, part)
    edits = docs.all_edits(repo_root, tool, versions.fmt(new))
    verb = "would set" if dry_run else "set"
    print(f"{tool.name}: {verb} {versions.fmt(old)} -> {versions.fmt(new)}")
    main = tool.main_module()
    if not dry_run:
        if main and versions.read_code_version(main):
            versions.write_code_version(main, new)
        if tool.manifest.is_file():
            versions.write_manifest_version(tool.manifest, new)
        docs.apply(edits)
    for path in [main, tool.manifest if tool.manifest.is_file() else None]:
        if path:
            print(f"  {path.relative_to(repo_root).as_posix()}")
    _print_edits(edits, repo_root)
    if docs.changelog_mentions(tool, versions.fmt(new)) is False:
        print(f"  note: CHANGELOG has no entry for {versions.fmt(new)} yet")
    return new


def cmd_bump(args) -> int:
    tool = resolve(_tools(args), args.tool)
    _bump(tool, args.part, _repo(args), args.dry_run)
    return 0


def cmd_docs(args) -> int:
    tool = resolve(_tools(args), args.tool)
    version = versions.fmt(check_versions(tool))
    edits = docs.all_edits(_repo(args), tool, version)
    if not edits:
        print(f"{tool.name}: docs already say {version}")
        return 0
    if not args.dry_run:
        docs.apply(edits)
    print(f"{tool.name}: {'would update' if args.dry_run else 'updated'} docs to {version}")
    _print_edits(edits, _repo(args))
    return 0


def _report_build(tool: Tool, result, repo_root: Path) -> None:
    rel = result.zip_path.relative_to(repo_root).as_posix()
    label = {"built": "built", "up-to-date": "already up to date:", "dry-run": "would build"}[result.status]
    print(f"{tool.name}: {label} {rel}")
    for a in result.archived:
        print(f"  {'would move' if result.status == 'dry-run' else 'moved'} previous zip to {a.relative_to(repo_root).as_posix()}")
    for w in result.warnings:
        print(f"  warning: {w}")
    version = versions.fmt(tool.version())
    if docs.changelog_mentions(tool, version) is False:
        print(f"  warning: CHANGELOG has no entry for {version}")
    stale = [e for e in docs.all_edits(repo_root, tool, version)]
    if stale:
        print(f"  warning: {len(stale)} doc lines don't say {version} -- run `release.py docs {tool.name}`")


def cmd_build(args) -> int:
    tool = resolve(_tools(args), args.tool)
    result = build(tool, force=args.force, dry_run=args.dry_run)
    _report_build(tool, result, _repo(args))
    return 0


def cmd_release(args) -> int:
    tool = resolve(_tools(args), args.tool)
    _bump(tool, args.part, _repo(args), args.dry_run)
    if args.dry_run:
        print(f"{tool.name}: dry run -- build skipped (it needs the bumped version on disk)")
        return 0
    result = build(tool)
    _report_build(tool, result, _repo(args))
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="release.py", description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--addons-dir", default=str(ADDONS_DIR), help=argparse.SUPPRESS)
    sub = parser.add_subparsers(dest="command", required=True)

    for name in ("status", "check"):
        p = sub.add_parser(name)
        p.add_argument("tool", nargs="?")
        p.set_defaults(func=cmd_status)

    p = sub.add_parser("init")
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("tool", nargs="?")
    g.add_argument("--all", action="store_true")
    p.add_argument("--force", action="store_true", help="overwrite an existing release.toml")
    p.set_defaults(func=cmd_init)

    for name, func in (("bump", cmd_bump), ("release", cmd_release)):
        p = sub.add_parser(name)
        p.add_argument("tool")
        p.add_argument("part", help="major | minor | patch | X.Y.Z")
        p.add_argument("--dry-run", action="store_true")
        p.set_defaults(func=func)

    p = sub.add_parser("docs")
    p.add_argument("tool")
    p.add_argument("--dry-run", action="store_true")
    p.set_defaults(func=cmd_docs)

    p = sub.add_parser("build")
    p.add_argument("tool")
    p.add_argument("--force", action="store_true", help="rebuild an existing same-version zip in place")
    p.add_argument("--dry-run", action="store_true")
    p.set_defaults(func=cmd_build)

    args = parser.parse_args(argv)
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")
    try:
        return args.func(args)
    except (BuildError, SpecError, versions.VersionError, LookupError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
