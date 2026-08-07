#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
APP_ROOT="$SCRIPT_DIR"
cd "$APP_ROOT"

if [ ! -d "$APP_ROOT/app" ]; then
  echo "Expected app/ directory next to this script." >&2
  exit 1
fi

if [ -z "${VIRTUAL_ENV:-}" ]; then
  echo "Warning: no virtual environment is active." >&2
  echo "Run: source ~/.venvs/aisha/bin/activate" >&2
fi

exec python -m uvicorn app.main:app --host "${AISHA_HOST:-127.0.0.1}" --port "${AISHA_PORT:-8000}" "$@"
