#!/bin/bash
# One-time setup for the stick-figure video pipeline (run as root inside the agent).
set -e
cd "$(dirname "$0")"

# ffmpeg (frame -> MP4 assembly)
if ! command -v ffmpeg >/dev/null 2>&1; then
  echo "installing ffmpeg..."
  (apt-get update && apt-get install -y --no-install-recommends ffmpeg) || true
fi

# Python deps (Pillow + numpy) in a local venv
if command -v uv >/dev/null 2>&1; then
  uv venv .venv
  uv pip install --python .venv/bin/python pillow numpy
else
  python3 -m venv .venv
  .venv/bin/pip install pillow numpy
fi

echo "setup done. Run: .venv/bin/python pipeline.py \"Your topic\""
