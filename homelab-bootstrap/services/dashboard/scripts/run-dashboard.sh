#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(CDPATH= cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../../../.." && pwd)"
cd "$REPO_ROOT"

if [ -z "${VIRTUAL_ENV:-}" ]; then
  echo "Warning: no virtual environment is active." >&2
  echo "Run: source ~/.venvs/aisha/bin/activate" >&2
fi

export CHROMA_PATH="${CHROMA_PATH:-$HOME/.local/share/aisha/chroma}"
exec python -m app --host "${AISHA_HOST:-127.0.0.1}" --port "${AISHA_PORT:-8000}" "$@"
