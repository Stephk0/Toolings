"""Subprocess and git helpers. bpy-free.

Every external process the publisher runs (Blender, rclone, robocopy, git) goes
through `run` so that dry-run, logging and error handling behave identically.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
from typing import NamedTuple


class Completed(NamedTuple):
    code: int
    out: str
    err: str
    cmd: list

    @property
    def ok(self) -> bool:
        return self.code == 0


def run(cmd: list, *, cwd: str = None, env: dict = None, timeout: int = None) -> Completed:
    """Run a command, capturing output. Never raises on a non-zero exit."""
    try:
        proc = subprocess.run(
            cmd,
            cwd=cwd,
            env=env,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
        )
    except FileNotFoundError as exc:
        return Completed(127, "", "executable not found: %s (%s)" % (cmd[0], exc), list(cmd))
    except subprocess.TimeoutExpired as exc:
        return Completed(124, exc.stdout or "", "timed out after %ss" % timeout, list(cmd))
    return Completed(proc.returncode, proc.stdout or "", proc.stderr or "", list(cmd))


def which(name: str) -> str:
    return shutil.which(name) or ""


def resolve_exe(explicit: str, name: str) -> str:
    """An explicitly configured executable wins over PATH; "" if neither works.

    Lets a tool that lives outside PATH (a downloaded rclone.exe, say) be used
    without touching the user's environment. An explicit path that points at a
    directory is accepted too, and the executable is looked up inside it.
    """
    if explicit:
        path = os.path.expandvars(os.path.expanduser(explicit))
        if os.path.isfile(path):
            return path
        if os.path.isdir(path):
            for candidate in (name, name + ".exe"):
                inside = os.path.join(path, candidate)
                if os.path.isfile(inside):
                    return inside
        return ""
    return which(name)


# --- git provenance ----------------------------------------------------------

def git_info(repo_root: str) -> dict:
    """Commit / branch / dirty state, for the manifest. Degrades to blanks."""
    info = {"commit": "", "short": "", "branch": "", "dirty": False, "subject": ""}
    if not os.path.isdir(os.path.join(repo_root, ".git")):
        return info

    head = run(["git", "rev-parse", "HEAD"], cwd=repo_root)
    if head.ok:
        info["commit"] = head.out.strip()
        info["short"] = info["commit"][:9]

    branch = run(["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=repo_root)
    if branch.ok:
        info["branch"] = branch.out.strip()

    subject = run(["git", "log", "-1", "--pretty=%s"], cwd=repo_root)
    if subject.ok:
        info["subject"] = subject.out.strip()

    status = run(["git", "status", "--porcelain"], cwd=repo_root)
    if status.ok:
        info["dirty"] = bool(status.out.strip())

    return info


def current_branch(repo_root: str) -> str:
    res = run(["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=repo_root)
    return res.out.strip() if res.ok else ""


def repo_root_of(start: str) -> str:
    """Walk up to the git root, so the tool works from any cwd."""
    res = run(["git", "rev-parse", "--show-toplevel"], cwd=start)
    if res.ok and res.out.strip():
        return os.path.normpath(res.out.strip())
    path = os.path.abspath(start)
    while True:
        if os.path.isdir(os.path.join(path, ".git")):
            return path
        parent = os.path.dirname(path)
        if parent == path:
            return ""
        path = parent


# --- Blender discovery -------------------------------------------------------

_WIN_BLENDER_ROOTS = (
    r"C:\Program Files\Blender Foundation",
    r"C:\Program Files (x86)\Blender Foundation",
)

_VER_RE = re.compile(r"(\d+)\.(\d+)")


def find_blender(explicit: str = "") -> str:
    """Locate a Blender executable: explicit config > PATH > highest installed."""
    if explicit:
        return explicit if os.path.isfile(explicit) else ""

    on_path = which("blender")
    if on_path:
        return on_path

    candidates = []
    for root in _WIN_BLENDER_ROOTS:
        if not os.path.isdir(root):
            continue
        for name in os.listdir(root):
            match = _VER_RE.search(name)
            exe = os.path.join(root, name, "blender.exe")
            if match and os.path.isfile(exe):
                candidates.append(((int(match.group(1)), int(match.group(2))), exe))
    if not candidates:
        return ""
    candidates.sort()
    return candidates[-1][1]
