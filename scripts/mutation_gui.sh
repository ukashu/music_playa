#!/usr/bin/env bash
# Mutation testing of the GUI logic modules with mutmut (see [tool.mutmut] in gui/pyproject.toml).
# Extra arguments go to "mutmut run", e.g. a mutant name to rerun just that one.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT/gui"

export QT_QPA_PLATFORM=offscreen
.venv/bin/mutmut run "$@"
.venv/bin/mutmut results
