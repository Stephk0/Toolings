"""Add (or refresh) an Icon column in the ../README.md reference tables.

    python readme_tables.py [--check]

Plain Python, no Blender needed. Finds every table whose header starts
`| Modifier | File |`, and rewrites its first column to the modifier's preview
icon. Idempotent: run it again after build_icons.py whenever the roster or a
recipe changes.

Rows are matched on (modifier, file), not on the name alone — two different
groups can share a name across files, so the name by itself is ambiguous.
A modifier with no icon simply gets an empty cell.
"""
import os
import re
import sys
from urllib.parse import quote

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import recipes      # noqa: E402

README = os.path.join(os.path.dirname(HERE), "README.md")
OUT = os.path.join(HERE, "out")
ICON_W = 64
HEADER_RE = re.compile(r"^\|\s*(Icon\s*\|\s*)?Modifier\s*\|\s*File\s*\|")
SEP_RE = re.compile(r"^\|[\s:-]+\|[\s:-]+\|")


def cells(line):
    """The cells of a markdown table row, without the outer pipes."""
    return [c.strip() for c in line.strip().strip("|").split("|")]


def icon_cell(modifier, blend, covered):
    key = covered.get((modifier, blend))
    if key is None:
        return ""
    png = key + ".png"
    if not os.path.exists(os.path.join(OUT, png)):
        return ""
    return ('<img src="_icons/out/%s" width="%d" alt="%s">'
            % (quote(png), ICON_W, modifier))


def main():
    check = "--check" in sys.argv
    covered = recipes.covered()
    lines = open(README, encoding="utf8").read().split("\n")

    out, i, tables, iconed, missing = [], 0, 0, 0, []
    while i < len(lines):
        line = lines[i]
        if not HEADER_RE.match(line) or i + 1 >= len(lines) \
                or not SEP_RE.match(lines[i + 1]):
            out.append(line)
            i += 1
            continue

        tables += 1
        had_icon = cells(line)[0] == "Icon"
        head = cells(line)[1:] if had_icon else cells(line)
        sep = cells(lines[i + 1])[1:] if had_icon else cells(lines[i + 1])
        out.append("| Icon | " + " | ".join(head) + " |")
        out.append("|:---:|" + "|".join(sep) + "|")
        i += 2

        while i < len(lines) and lines[i].startswith("|"):
            row = cells(lines[i])
            if had_icon:
                row = row[1:]
            modifier = row[0].strip().strip("*").strip()
            blend = row[1].strip().strip("`").strip() if len(row) > 1 else ""
            cell = icon_cell(modifier, blend, covered)
            if cell:
                iconed += 1
            elif modifier:
                missing.append("%s (%s)" % (modifier, blend))
            out.append("| " + cell + " | " + " | ".join(row) + " |")
            i += 1

    text = "\n".join(out)
    same = text == open(README, encoding="utf8").read()
    if not check and not same:
        open(README, "w", encoding="utf8").write(text)

    print("%d reference tables, %d rows given an icon" % (tables, iconed))
    if missing:
        print("no icon for: " + ", ".join(missing))
    print("README %s" % ("unchanged" if same else
                         ("would change" if check else "updated")))
    return 1 if (check and not same) else 0


if __name__ == "__main__":
    sys.exit(main())
