"""Planning logic for bulk library relinking. Pure Python, no bpy.

A "plan" classifies every linked library against a destination folder before
anything is touched, so the UI can show a dry-run preview:

  RELINK   - a file with the same name exists in the new folder, path differs
  MISSING  - no file with this name in the new folder (left untouched)
  FILTERED - library lives outside the source-folder filter (left untouched)
  SAME     - already points at the new folder
"""

import os

STATUS_RELINK = "RELINK"
STATUS_MISSING = "MISSING"
STATUS_FILTERED = "FILTERED"
STATUS_SAME = "SAME"

ALL_STATUSES = (STATUS_RELINK, STATUS_MISSING, STATUS_FILTERED, STATUS_SAME)


def normalize(path):
    """Comparable form of a path (separators and case folded per-OS)."""
    return os.path.normcase(os.path.normpath(path))


def is_under(path, directory):
    """True when path sits inside directory (or equals it).

    An empty directory filter matches everything.
    """
    if not directory:
        return True
    d = normalize(directory).rstrip(os.sep)
    p = normalize(path)
    return p == d or p.startswith(d + os.sep)


def plan_relink(libraries, new_dir, available_files, old_dir_filter=""):
    """Build a relink plan.

    libraries: iterable of (name, absolute_filepath) pairs
    new_dir: destination folder the libraries should point to
    available_files: filenames (no directories) present in new_dir
    old_dir_filter: only libraries inside this folder are considered ("" = all)

    Returns a list of dicts: {"name", "current", "target", "status"}.
    Filename matching is case-insensitive; the target keeps the on-disk
    spelling exactly as passed in available_files.
    """
    available = {name.casefold(): name for name in available_files}
    plan = []
    for name, current in libraries:
        base = os.path.basename(current)
        found = base.casefold() in available
        target = os.path.join(new_dir, available.get(base.casefold(), base))
        # SAME wins over FILTERED so freshly relinked libraries read as done
        # even when they now sit outside the source-folder filter.
        if found and normalize(target) == normalize(current):
            status = STATUS_SAME
        elif not is_under(current, old_dir_filter):
            status = STATUS_FILTERED
        elif not found:
            status = STATUS_MISSING
        else:
            status = STATUS_RELINK
        plan.append({
            "name": name,
            "current": current,
            "target": target,
            "status": status,
        })
    return plan


def summarize(plan):
    """Status -> count for a plan; every status key is always present."""
    counts = {status: 0 for status in ALL_STATUSES}
    for item in plan:
        counts[item["status"]] += 1
    return counts
