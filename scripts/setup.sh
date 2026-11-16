#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

if ! command -v python3.15 >/dev/null 2>&1; then
  echo "python3.15 is required and was not found in PATH." >&2
  exit 1
fi

python3.15 -m venv backend/.venv
backend/.venv/bin/pip install -e "./backend[dev]"

python3.15 -m venv tui/.venv
tui/.venv/bin/pip install -e ./backend -e ./tui

python3.15 -m venv gui/.venv
gui/.venv/bin/pip install -e ./backend -e ./gui
