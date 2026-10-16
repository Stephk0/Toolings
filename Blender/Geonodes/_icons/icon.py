"""One entry point for the icon pipeline. Plain Python; it launches Blender itself.

    python icon.py coverage                  which modifiers still need an icon
    python icon.py probe GN_X [GN_Y ...]     dump the real interface (before a recipe)
    python icon.py build GN_X [GN_Y ...]     STAGE A: render out/<key>.png - then LOOK at it
    python icon.py ship  GN_X [GN_Y ...]     STAGE B: embed -> cold verify -> README refresh
    python icon.py frames                    regenerate frames/*.png after a frame edit

`build` never touches a .blend. `ship` is the only command that writes the
library, and it refuses a key whose PNG is missing. It is deliberately a
separate step: the effect check proves something changed, not that the icon
reads, so a human (or agent) looks at the PNG between the two.

Blender: $ST3E_BLENDER, else the default Blender 5.0 install path.
"""
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "out")
BLENDER = os.environ.get(
    "ST3E_BLENDER", r"C:\Program Files\Blender Foundation\Blender 5.0\blender.exe")

# Blender's startup chatter; everything else is passed through.
NOISE = ("Blender 5", "Read prefs", "Read blend", "Blender quit")


def blender(script, *args):
    cmd = [BLENDER, "--background", "--factory-startup", "--python",
           os.path.join(HERE, script)]
    if args:
        cmd += ["--"] + list(args)
    print(">> %s %s" % (script, " ".join(args)), flush=True)
    proc = subprocess.Popen(cmd, cwd=HERE, stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT, text=True,
                            encoding="utf8", errors="replace")
    for line in proc.stdout:
        if not line.startswith(NOISE):
            sys.stdout.write(line)
    return proc.wait()


def python(script, *args):
    print(">> %s %s" % (script, " ".join(args)), flush=True)
    return subprocess.call([sys.executable, os.path.join(HERE, script)] + list(args),
                           cwd=HERE)


def need_keys(keys):
    if not keys:
        raise SystemExit("name at least one recipe key, e.g. GN_Twist")


def ship(keys):
    missing = [k for k in keys if not os.path.exists(os.path.join(OUT, k + ".png"))]
    if missing:
        raise SystemExit("no PNG for %s - run `icon.py build` first (and look at it)"
                         % missing)
    for step in (lambda: blender("embed_icons.py", *keys, "--dry-run"),
                 lambda: blender("embed_icons.py", *keys),
                 lambda: blender("verify_embed.py"),
                 lambda: python("gallery.py"),
                 lambda: python("readme_tables.py")):
        code = step()
        if code:
            return code
    print("\nshipped %s. Commit the .blend(s), out/, recipes.py and ../README.md."
          % ", ".join(keys))
    return 0


def main(argv):
    if not argv or argv[0] in ("-h", "--help", "help"):
        print(__doc__)
        return 0
    cmd, keys = argv[0], argv[1:]
    if not os.path.exists(BLENDER):
        raise SystemExit("Blender not found at %s - set ST3E_BLENDER" % BLENDER)
    if cmd == "coverage":
        return blender("coverage.py")
    if cmd == "frames":
        return blender("make_frames.py")
    if cmd == "probe":
        need_keys(keys)
        return blender("probe.py", *keys)
    if cmd == "build":
        need_keys(keys)
        code = blender("build_icons.py", *keys)
        for k in keys:
            png = os.path.join(OUT, k + ".png")
            if os.path.exists(png):
                print("LOOK AT: " + png)
        return code
    if cmd == "ship":
        need_keys(keys)
        return ship(keys)
    raise SystemExit("unknown command %r - see `python icon.py help`" % cmd)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
