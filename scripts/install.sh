#!/usr/bin/env bash
set -euo pipefail
project_root="$(cd "$(dirname "$0")/.." && pwd)"
cd "$project_root"
python3 -m venv .venv
.venv/bin/python -m pip install -e '.[linux,web,test]'
if command -v pnpm >/dev/null; then
  pnpm --dir frontend install --frozen-lockfile
  pnpm --dir frontend build
elif command -v npm >/dev/null; then
  (cd frontend && npm install && npm run build)
else
  echo 'Install Node.js 20.19+ with npm or pnpm, then run this installer again.' >&2
  exit 1
fi
.venv/bin/python scripts/install_desktop.py
printf '\nInstalled. Launch Chopin Studio from the applications menu.\n'
