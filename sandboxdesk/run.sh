#!/bin/sh
# Start the virtual desktop on port 8000, reachable from the preview URL.
cd "$(dirname "$0")"
exec python3 desktop.py --port "${PORT:-8000}"
