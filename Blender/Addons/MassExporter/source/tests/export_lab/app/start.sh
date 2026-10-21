#!/bin/sh
# Opens the Export Lab through a local server (macOS / Linux, needs python3).
cd "$(dirname "$0")"
PORT=8791
(sleep 1; (open "http://localhost:$PORT/" || xdg-open "http://localhost:$PORT/") >/dev/null 2>&1) &
python3 serve.py . "$PORT"
