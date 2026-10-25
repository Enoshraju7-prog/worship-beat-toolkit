#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"
if [ ! -x .venv/bin/worship-beats ]; then
  echo 'First run: bash scripts/setup_mac.sh'
  read -r -p 'Press Return to close. '
  exit 1
fi
exec .venv/bin/worship-beats app
