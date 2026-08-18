"""LibraryPublisher CLI - the single entry point every trigger funnels through.

    python source/cli.py status
    python source/cli.py publish [--force] [--dry-run] [--enforce-branch]
    python source/cli.py check
    python source/cli.py config init | show | set | validate | doctor
    python source/cli.py install-hooks | uninstall-hooks

The slash commands, the git hook, the GitHub Action and the Blender button all
call this, so there is exactly one code path to reason about.
"""

from __future__ import annotations

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core import config, criteria, publish, selection, shell  # noqa: E402

TOOL_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _load(args) -> dict:
    path = args.config or config.config_path(TOOL_ROOT)
    repo_root = shell.repo_root_of(TOOL_ROOT)
    cfg = config.load(path, repo_root=repo_root)
    if not cfg["source"].get("repo_root"):
        cfg["source"]["repo_root"] = repo_root
    if args.dry_run:
        cfg["delivery"]["dry_run"] = True
    return cfg


# --- commands ----------------------------------------------------------------

def cmd_config_init(args) -> int:
    path = args.config or config.config_path(TOOL_ROOT)
    if os.path.isfile(path) and not args.force:
        print("config already exists: %s  (use --force to overwrite)" % path)
        return 1
    repo_root = args.repo_root or shell.repo_root_of(TOOL_ROOT)
    cfg = config.default_config(repo_root)
    config.save(path, cfg)
    print("wrote %s" % path)
    print("repo_root: %s" % repo_root)
    print("\nNext: set the Shared Drive destination, e.g.")
    print("  python source/cli.py config set delivery.rclone.remote=st3e_gdrive")
    print("  python source/cli.py config set delivery.rclone.path=ST3E_Ext")
    return 0


def cmd_config_show(args) -> int:
    cfg = _load(args)
    if args.key:
        try:
            print(json.dumps(config.get_path(cfg, args.key), indent=2))
        except KeyError as exc:
            print(exc)
            return 1
        return 0
    if args.json:
        print(json.dumps(cfg, indent=2))
        return 0
    _print_summary(cfg)
    return 0


def _print_summary(cfg: dict) -> None:
    src = cfg["source"]
    dely = cfg["delivery"]
    print("library name    : %s" % cfg["library_name"])
    print("repo root       : %s" % src["repo_root"])
    print("library root    : %s  (catalog: %s)" % (src["library_root"], src["catalog_file"]))
    print("")
    print("scope")
    for entry in cfg["scope"]["entries"]:
        mark = "on " if entry.get("enabled") else "OFF"
        print("  [%s] %-12s %s -> %s/" % (mark, entry["name"], entry["src"], entry["dest"]))
        print("       include %s" % (entry.get("include") or []))
        if entry.get("exclude"):
            print("       exclude %s" % entry["exclude"])
    print("")
    cat = cfg["catalog"]
    print("catalog rewrite : %s (%s)" % (
        "on" if cat.get("enabled") else "off", cat.get("mode")
    ))
    for rule in cat.get("rename") or []:
        print("  %s -> %s   (UUIDs preserved: %s)" % (
            rule.get("from"), rule.get("to"), cat.get("keep_uuids")
        ))
    print("")
    print("delivery        : %s%s" % (dely.get("backend"), "  [DRY RUN]" if dely.get("dry_run") else ""))
    if dely.get("backend") == "rclone":
        rc = dely["rclone"]
        print("  remote        : %s:%s" % (rc.get("remote") or "<unset>", rc.get("path") or ""))
        print("  team drive    : %s" % (rc.get("team_drive") or "<remote default>"))
        print("  SA env var    : %s" % rc.get("service_account_env"))
        from core import delivery
        resolved = delivery.rclone_exe(cfg)
        configured = rc.get("executable") or ""
        print("  rclone exe    : %s" % (
            resolved or ("NOT FOUND at %s" % configured if configured else "<not on PATH>")
        ))
    else:
        print("  local path    : %s" % (dely.get("local", {}).get("path") or "<unset>"))
    print("  atomic swap   : %s   delete extraneous: %s" % (
        dely.get("atomic"), dely.get("delete_extraneous")
    ))
    print("")
    print("criteria        (on_block: %s)" % cfg.get("criteria_policy", {}).get("on_block"))
    for key, check in sorted(cfg["criteria"].items()):
        print("  %-6s %-18s %s" % (check.get("mode"), key, check.get("label", "")))
        print("         applies to: %s" % (check.get("applies_to") or []))
    print("")
    print("triggers")
    trig = cfg["triggers"]
    print("  manual        : %s" % _onoff(trig["manual"].get("enabled")))
    print("  git hook      : %s  (%s, branches %s, background %s)" % (
        _onoff(trig["git_hook"].get("enabled")), trig["git_hook"].get("hook"),
        trig["git_hook"].get("branches"), trig["git_hook"].get("background"),
    ))
    print("  github action : %s  (branches %s)" % (
        _onoff(trig["github_action"].get("enabled")), trig["github_action"].get("branches")
    ))
    print("  blender button: %s  (refresh after: %s)" % (
        _onoff(trig["blender_button"].get("enabled")),
        trig["blender_button"].get("refresh_after"),
    ))
    problems = config.validate(cfg)
    print("")
    if problems:
        print("NOT READY:")
        for problem in problems:
            print("  - %s" % problem)
    else:
        print("config validates - ready to publish")


def _onoff(value) -> str:
    return "on" if value else "off"


def cmd_config_set(args) -> int:
    path = args.config or config.config_path(TOOL_ROOT)
    cfg = config.load(path, repo_root=shell.repo_root_of(TOOL_ROOT))
    for assignment in args.assignments:
        if "=" not in assignment:
            print("expected key=value, got: %s" % assignment)
            return 1
        key, raw = assignment.split("=", 1)
        try:
            value = json.loads(raw)
        except json.JSONDecodeError:
            value = raw  # bare strings need no quoting
        try:
            config.set_path(cfg, key.strip(), value)
        except KeyError as exc:
            print(exc)
            return 1
        print("set %s = %s" % (key.strip(), json.dumps(value)))
    problems = config.validate(cfg)
    config.save(path, cfg)
    print("saved %s" % path)
    if problems:
        print("\nheads up, config still has problems:")
        for problem in problems:
            print("  - %s" % problem)
    return 0


def cmd_config_validate(args) -> int:
    cfg = _load(args)
    problems = config.validate(cfg)
    if not problems:
        print("config OK")
        return 0
    print("config problems:")
    for problem in problems:
        print("  - %s" % problem)
    return 1


def cmd_config_doctor(args) -> int:
    """Check the *environment* rather than the config file: tools, creds, paths."""
    cfg = _load(args)
    rows = []

    repo_root = cfg["source"]["repo_root"]
    rows.append(("repo root", os.path.isdir(repo_root), repo_root))

    cat = publish.catalog_source_path(cfg)
    rows.append(("catalog file", os.path.isfile(cat), cat))

    git_exe = shell.which("git")
    rows.append(("git", bool(git_exe), git_exe or "not on PATH"))

    backend = cfg["delivery"]["backend"]
    if backend == "rclone":
        from core import delivery
        rc_exe = delivery.rclone_exe(cfg)
        rows.append((
            "rclone", bool(rc_exe),
            rc_exe or "not found - set delivery.rclone.executable, or use PATH",
        ))
        remote = cfg["delivery"]["rclone"].get("remote")
        if rc_exe and remote:
            res = shell.run([rc_exe, "listremotes"], timeout=60)
            configured = [r.strip().rstrip(":") for r in res.out.splitlines() if r.strip()]
            rows.append((
                "rclone remote '%s'" % remote,
                remote in configured,
                "configured remotes: %s" % (", ".join(configured) or "none"),
            ))
        sa_env = cfg["delivery"]["rclone"].get("service_account_env") or ""
        sa_path = os.environ.get(sa_env, "")
        rows.append((
            "service account (%s)" % sa_env,
            bool(sa_path) and os.path.isfile(sa_path),
            sa_path or "unset - interactive rclone auth will be used",
        ))
    else:
        target = cfg["delivery"].get("local", {}).get("path", "")
        rows.append(("local target", bool(target) and os.path.isdir(target), target or "<unset>"))

    if criteria.active_checks(cfg):
        exe = shell.find_blender(cfg.get("blender", {}).get("executable", ""))
        rows.append(("blender (criteria are on)", bool(exe), exe or "not found"))
        audit_dir = cfg["criteria"]["geonode_layout"].get("audit_module_dir", "")
        audit_path = os.path.join(repo_root, audit_dir, "layout_audit.py")
        rows.append((
            "layout_audit.py",
            os.path.isfile(audit_path),
            audit_path,
        ))
    else:
        rows.append(("blender", True, "not needed - every criteria check is off"))

    bad = 0
    for label, ok, detail in rows:
        print("  [%s] %-28s %s" % ("ok" if ok else "!!", label, detail))
        if not ok:
            bad += 1
    print("")
    print("%d problem(s)" % bad if bad else "environment looks good")
    return 1 if bad else 0


def cmd_status(args) -> int:
    """What *would* be published, plus the diff - never delivers anything."""
    cfg = _load(args)
    cfg["delivery"]["dry_run"] = True
    result = publish.publish(cfg, TOOL_ROOT, force=False, reason="status")
    print("\n".join(result.lines))
    return 0 if result.ok else 1


def cmd_check(args) -> int:
    """Run the criteria checks alone and report."""
    cfg = _load(args)
    if not criteria.active_checks(cfg):
        print("every criteria check is off - nothing to run")
        print("enable one, e.g.: config set criteria.geonode_layout.mode=warn")
        return 0
    problems = config.validate(cfg)
    if problems:
        print("config problems:")
        for problem in problems:
            print("  - %s" % problem)
        return 1

    sel = selection.select(cfg)
    cat_path = publish.catalog_source_path(cfg)
    known = set()
    if os.path.isfile(cat_path):
        from core import catalogs
        with open(cat_path, "r", encoding="utf-8") as fh:
            known = catalogs.known_uuids(fh.read())

    verdict, inspected = publish.run_criteria(cfg, TOOL_ROOT, sel.files, known)
    if not verdict.ran:
        print("criteria did not run: %s" % verdict.inspect_error)
        return 1
    print("inspected %d file(s)" % len(inspected))
    print(criteria.format_report(verdict, show_pass=args.verbose))
    print("")
    print("%d failure(s), %d warning(s)" % (len(verdict.failures()), len(verdict.warnings())))
    return 1 if verdict.failures() else 0


def cmd_publish(args) -> int:
    cfg = _load(args)
    result = publish.publish(
        cfg, TOOL_ROOT,
        force=args.force,
        enforce_branch=args.enforce_branch,
        reason=args.reason,
    )
    print("\n".join(result.lines))
    if not result.ok:
        return 1
    if result.skipped_files:
        # The publish succeeded but delivered LESS than was asked for. Exiting 0
        # would let a CI run go green while the shared library quietly shrank.
        print("\nWITHHELD %d file(s) by a blocking check - exiting non-zero so "
              "this cannot pass silently" % len(result.skipped_files))
        return 3
    return 0


def cmd_hook(args) -> int:
    """Entry point for the git hooks. Never fails a push.

    A publish problem must not stand between the user and their remote, so this
    reports and returns 0 for anything short of a config error - the log and the
    next `status` call carry the detail.
    """
    cfg = _load(args)
    hook_cfg = cfg["triggers"]["git_hook"]

    if not hook_cfg.get("enabled"):
        print("[library-publisher] git hook trigger is disabled - skipping")
        return 0
    if hook_cfg.get("hook") != args.event:
        print("[library-publisher] configured for %s, not %s - skipping"
              % (hook_cfg.get("hook"), args.event))
        return 0

    branches = hook_cfg.get("branches") or []
    branch = shell.current_branch(cfg["source"]["repo_root"])
    if branches and branch not in branches:
        print("[library-publisher] branch '%s' is not published (%s) - skipping"
              % (branch, ", ".join(branches)))
        return 0

    log_dir = os.path.join(TOOL_ROOT, ".last_publish")
    os.makedirs(log_dir, exist_ok=True)
    log_path = os.path.join(log_dir, "hook.log")

    if hook_cfg.get("background") and not args.foreground:
        _spawn_detached(
            [sys.executable, os.path.abspath(__file__), "publish",
             "--enforce-branch", "--reason", args.event],
            log_path,
        )
        print("[library-publisher] publishing '%s' in the background -> %s"
              % (cfg["library_name"], log_path))
        return 0

    result = publish.publish(
        cfg, TOOL_ROOT, enforce_branch=True, reason=args.event
    )
    text = "\n".join(result.lines)
    print(text)
    with open(log_path, "w", encoding="utf-8") as fh:
        fh.write(text + "\n")
    if not result.ok:
        print("[library-publisher] publish failed - the push itself was NOT blocked")
    return 0


def _spawn_detached(cmd: list, log_path: str) -> None:
    """Fire and forget, so a slow Drive upload never holds up a git push."""
    import subprocess

    kwargs = {}
    if os.name == "nt":
        kwargs["creationflags"] = (
            getattr(subprocess, "DETACHED_PROCESS", 0)
            | getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
        )
    else:
        kwargs["start_new_session"] = True
    with open(log_path, "w", encoding="utf-8") as log:
        subprocess.Popen(cmd, stdout=log, stderr=subprocess.STDOUT, **kwargs)


def cmd_install_hooks(args) -> int:
    return _hooks(install=True)


def cmd_uninstall_hooks(args) -> int:
    return _hooks(install=False)


def _hooks(install: bool) -> int:
    """Point git at the tracked hooks dir, so the hook is versioned with the repo."""
    repo_root = shell.repo_root_of(TOOL_ROOT)
    if not repo_root:
        print("not inside a git repo")
        return 1
    hooks_dir = os.path.join(TOOL_ROOT, "hooks")
    rel = os.path.relpath(hooks_dir, repo_root).replace(os.sep, "/")
    if install:
        res = shell.run(["git", "config", "core.hooksPath", rel], cwd=repo_root)
        if not res.ok:
            print("failed: %s" % (res.err or res.out))
            return 1
        print("core.hooksPath -> %s" % rel)
        print("hooks in that folder are now live for this clone.")
        return 0
    res = shell.run(["git", "config", "--unset", "core.hooksPath"], cwd=repo_root)
    # exit 5 == the key was not set, which is the desired end state anyway.
    if not res.ok and res.code != 5:
        print("failed: %s" % (res.err or res.out))
        return 1
    print("core.hooksPath cleared - back to .git/hooks")
    return 0


# --- argument wiring ---------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="library-publisher", description=__doc__)
    parser.add_argument("--config", default="", help="path to publish_config.json")
    parser.add_argument("--dry-run", action="store_true", help="never write to the destination")
    sub = parser.add_subparsers(dest="command", required=True)

    pub = sub.add_parser("publish", help="run a publish")
    pub.add_argument("--force", action="store_true", help="deliver even if nothing changed")
    pub.add_argument("--enforce-branch", action="store_true",
                     help="honour triggers.git_hook.branches and skip on other branches")
    pub.add_argument("--reason", default="manual", help="what triggered this run")
    pub.set_defaults(func=cmd_publish)

    sta = sub.add_parser("status", help="show what would be published, with the diff")
    sta.set_defaults(func=cmd_status)

    chk = sub.add_parser("check", help="run the criteria checks only")
    chk.add_argument("--verbose", action="store_true", help="list passing files too")
    chk.set_defaults(func=cmd_check)

    cfg_p = sub.add_parser("config", help="inspect or edit the config")
    cfg_sub = cfg_p.add_subparsers(dest="config_command", required=True)

    init = cfg_sub.add_parser("init", help="write a default config")
    init.add_argument("--repo-root", default="")
    init.add_argument("--force", action="store_true")
    init.set_defaults(func=cmd_config_init)

    show = cfg_sub.add_parser("show", help="print the config")
    show.add_argument("key", nargs="?", default="", help="dotted key to print")
    show.add_argument("--json", action="store_true")
    show.set_defaults(func=cmd_config_show)

    setp = cfg_sub.add_parser("set", help="set one or more key=value pairs")
    setp.add_argument("assignments", nargs="+")
    setp.set_defaults(func=cmd_config_set)

    val = cfg_sub.add_parser("validate", help="validate the config file")
    val.set_defaults(func=cmd_config_validate)

    doc = cfg_sub.add_parser("doctor", help="check tools, credentials and paths")
    doc.set_defaults(func=cmd_config_doctor)

    hk = sub.add_parser("hook", help="git hook entry point (never fails a push)")
    hk.add_argument("--event", required=True, choices=["pre-push", "post-commit"])
    hk.add_argument("--foreground", action="store_true",
                    help="ignore triggers.git_hook.background and run inline")
    hk.set_defaults(func=cmd_hook)

    ins = sub.add_parser("install-hooks", help="activate the tracked git hooks")
    ins.set_defaults(func=cmd_install_hooks)

    uns = sub.add_parser("uninstall-hooks", help="deactivate the tracked git hooks")
    uns.set_defaults(func=cmd_uninstall_hooks)

    return parser


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return args.func(args)
    except config.ConfigError as exc:
        print("config error: %s" % exc)
        return 2


if __name__ == "__main__":
    sys.exit(main())
