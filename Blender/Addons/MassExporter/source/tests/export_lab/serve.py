"""Serve an Export Lab run folder:  python serve.py <out_dir> [port]

Plain `python -m http.server` takes MIME types from the Windows registry, which often maps .js
to text/plain; browsers then refuse to run the page's modules. This fixes the types and
declares UTF-8.
"""
import functools
import http.server
import sys

TYPES = {
    ".js": "text/javascript; charset=utf-8", ".html": "text/html; charset=utf-8",
    ".json": "application/json; charset=utf-8", ".glb": "model/gltf-binary",
    ".fbx": "application/octet-stream", ".obj": "text/plain; charset=utf-8",
    ".mtl": "text/plain; charset=utf-8", ".png": "image/png",
}


class Handler(http.server.SimpleHTTPRequestHandler):
    extensions_map = {**http.server.SimpleHTTPRequestHandler.extensions_map, **TYPES}


if __name__ == "__main__":
    root = sys.argv[1] if len(sys.argv) > 1 else "."
    port = int(sys.argv[2]) if len(sys.argv) > 2 else 8000
    print(f"Export Lab: http://localhost:{port}")
    http.server.ThreadingHTTPServer(("", port), functools.partial(Handler, directory=root)).serve_forever()
