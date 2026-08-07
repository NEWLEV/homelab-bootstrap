#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
APP_ROOT="$SCRIPT_DIR/../../../"
cd "$APP_ROOT"

exec python -m mission_control "$@"
