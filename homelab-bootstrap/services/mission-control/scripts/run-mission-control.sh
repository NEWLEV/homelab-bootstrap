#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
APP_ROOT="$SCRIPT_DIR/../../../"
cd "$APP_ROOT"

PYTHON_BIN="${AISHA_PYTHON:-$HOME/.venvs/aisha/bin/python}"
exec "$PYTHON_BIN" -m mission_control "$@"
