"""Bundle a run folder into an offline app: no CDN, no claude.ai, one folder (and a zip).

    python bundle.py <out_dir> <app_dir> [--three <path to the three npm package>]

Copies the page, its scripts, manifest.json, scene.json, the preview and blobs/ (cases/ is not
needed: every file the page loads is a blob). three.js 0.160.0 is vendored into
vendor/three/ - from --three when given, else downloaded once from cdn.jsdelivr.net - with
only the modules the page imports, followed recursively. The importmap is pointed at the
copy, and the launchers from app/ are added. <app_dir>.zip is written next to the folder.

Browsers do not run module scripts from file://, so the app is opened through a local
server: "Start Export Lab.bat" (Windows; Python if present, else PowerShell) or start.sh.
"""
import os
import re
import shutil
import sys
import urllib.request

THREE_VERSION = "0.160.0"
CDN = f"https://cdn.jsdelivr.net/npm/three@{THREE_VERSION}/"
HERE = os.path.dirname(os.path.abspath(__file__))
ENTRY = ["build/three.module.js"] + [f"examples/jsm/{m}" for m in (
    "controls/OrbitControls.js", "renderers/CSS2DRenderer.js", "loaders/GLTFLoader.js",
    "loaders/FBXLoader.js", "loaders/OBJLoader.js", "loaders/MTLLoader.js")]
IMPORT = re.compile(r"""^\s*(?:import|export)\b[^'"]*?from\s*['"](\.{1,2}/[^'"]+)['"]""", re.M)


def read_three(rel, three):
    if three:
        with open(os.path.join(three, rel), "rb") as f:
            return f.read()
    with urllib.request.urlopen(CDN + rel) as r:
        return r.read()


def vendor_three(app, three):
    """Copy ENTRY and every relative import they reach into app/vendor/three/."""
    todo, done = list(ENTRY), set()
    while todo:
        rel = todo.pop()
        if rel in done:
            continue
        done.add(rel)
        data = read_three(rel, three)
        dest = os.path.join(app, "vendor", "three", rel)
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        with open(dest, "wb") as f:
            f.write(data)
        base = os.path.dirname(rel)
        for dep in IMPORT.findall(data.decode("utf-8", "replace")):
            todo.append(os.path.normpath(os.path.join(base, dep)).replace(os.sep, "/"))
    return len(done)


FONT_LINK = re.compile(r'<link[^>]+href="(https://fonts\.googleapis\.com/[^"]+)"[^>]*>')


def vendor_fonts(app, html):
    """Replace the Google Fonts stylesheet with a local copy (vendor/fonts/). Offline without
    it the page falls back to system fonts, so a failed download only prints a warning."""
    m = FONT_LINK.search(html)
    if not m:
        return html
    url = m.group(1).replace("&amp;", "&")
    # A browser user agent makes Google serve woff2
    ua = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"}
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers=ua)) as r:
            css = r.read().decode("utf-8")
        fonts = os.path.join(app, "vendor", "fonts")
        os.makedirs(fonts, exist_ok=True)
        for i, src in enumerate(sorted(set(re.findall(r"url\((https://[^)]+)\)", css)))):
            name = f"font-{i}{os.path.splitext(src)[1]}"
            with urllib.request.urlopen(src) as r, open(os.path.join(fonts, name), "wb") as f:
                f.write(r.read())
            css = css.replace(src, name)
        open(os.path.join(fonts, "fonts.css"), "w", encoding="utf-8").write(css)
    except OSError as e:
        print(f"warning: fonts not vendored ({e}); offline the page uses system fonts")
        return html
    # The preconnect hints are useless offline
    html = re.sub(r'<link[^>]+rel="preconnect"[^>]*>\s*', "", html)
    return html.replace(m.group(0), '<link rel="stylesheet" href="./vendor/fonts/fonts.css">')


def main():
    args = sys.argv[1:]
    three = None
    if "--three" in args:
        i = args.index("--three")
        three = args[i + 1]
        del args[i:i + 2]
    out, app = (os.path.abspath(a) for a in args[:2])

    # Empty the folder rather than recreate it: Windows refuses to delete a folder that is open
    # in Explorer
    os.makedirs(app, exist_ok=True)
    for name in os.listdir(app):
        full = os.path.join(app, name)
        shutil.rmtree(full) if os.path.isdir(full) else os.remove(full)
    for name in os.listdir(out):
        src = os.path.join(out, name)
        if os.path.isfile(src):
            shutil.copy2(src, app)
    shutil.copytree(os.path.join(out, "blobs"), os.path.join(app, "blobs"))
    for name in os.listdir(os.path.join(HERE, "app")):
        shutil.copy2(os.path.join(HERE, "app", name), app)
    shutil.copy2(os.path.join(HERE, "serve.py"), app)

    index = os.path.join(app, "index.html")
    html = open(index, encoding="utf-8").read()
    html = html.replace(CDN + "build/three.module.js", "./vendor/three/build/three.module.js")
    html = html.replace(CDN + "examples/jsm/", "./vendor/three/examples/jsm/")
    assert "cdn.jsdelivr" not in html, "index.html still points at the CDN"
    html = vendor_fonts(app, html)
    open(index, "w", encoding="utf-8", newline="").write(html)

    n = vendor_three(app, three)
    zip_path = shutil.make_archive(app, "zip", os.path.dirname(app), os.path.basename(app))
    print(f"{app}: page + {len(os.listdir(os.path.join(app, 'blobs')))} files + {n} three.js modules")
    print(f"zip: {zip_path} ({os.path.getsize(zip_path) // 1024} KB)")


if __name__ == "__main__":
    main()
