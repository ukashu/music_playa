#!/usr/bin/env bash
# Mutation testing of the backend with mutmut (see [tool.mutmut] in backend/pyproject.toml).
# Extra arguments go to "mutmut run", e.g. a mutant name to rerun just that one.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT/backend"
.venv/bin/mutmut run "$@"
.venv/bin/mutmut results
