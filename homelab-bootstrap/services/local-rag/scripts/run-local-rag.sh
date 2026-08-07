#!/usr/bin/env bash
set -euo pipefail

SERVICE_ROOT="$(CDPATH= cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$SERVICE_ROOT"

source ~/.venvs/aisha/bin/activate
exec python -m uvicorn app.main:app --host "${AISHA_HOST:-127.0.0.1}" --port "${AISHA_PORT:-8080}" "$@"
