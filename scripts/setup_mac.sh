#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/.."
command -v brew >/dev/null || { echo 'Install Homebrew from https://brew.sh, then run this script again.'; exit 1; }
if [ "$(uname -m)" = "arm64" ]; then
  PYTHON_FORMULA=python@3.13
  PYTHON_VERSION=3.13
  CONSTRAINTS=requirements/macos-arm64-py313.txt
else
  PYTHON_FORMULA=python@3.11
  PYTHON_VERSION=3.11
  CONSTRAINTS=requirements/macos-intel-py311.txt
fi
brew list "$PYTHON_FORMULA" >/dev/null 2>&1 || brew install "$PYTHON_FORMULA"
brew list ffmpeg >/dev/null 2>&1 || brew install ffmpeg
PYTHON_BIN="$(brew --prefix "$PYTHON_FORMULA")/bin/python$PYTHON_VERSION"
if [ -x .venv/bin/python ]; then
  CURRENT_VERSION=$(.venv/bin/python -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
  if [ "$CURRENT_VERSION" != "$PYTHON_VERSION" ]; then
    echo "Existing .venv uses Python $CURRENT_VERSION; expected $PYTHON_VERSION. Rename it and rerun setup."
    exit 1
  fi
fi
"$PYTHON_BIN" -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -c "$CONSTRAINTS" '.[app,separation,dev]'
.venv/bin/worship-beats doctor
echo 'Ready. Double-click Launch.command or run .venv/bin/worship-beats app'
