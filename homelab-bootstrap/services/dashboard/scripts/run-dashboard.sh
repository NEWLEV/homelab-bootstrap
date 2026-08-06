#!/usr/bin/env bash
set -euo pipefail

SERVICE_ROOT="$(CDPATH= cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$SERVICE_ROOT"

if [ -z "${VIRTUAL_ENV:-}" ]; then
  echo "Warning: no virtual environment is active." >&2
  echo "Run: source ~/.venvs/aisha/bin/activate" >&2
fi

exec python -m app --host "${AISHA_HOST:-127.0.0.1}" --port "${AISHA_PORT:-8000}" "$@"
