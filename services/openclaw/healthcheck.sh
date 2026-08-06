#!/usr/bin/env bash
set -Eeuo pipefail

: "${OPENCLAW_SECRETS_FILE:=/run/secrets/openclaw_env}"
: "${OPENCLAW_LOCAL_RAG_URL:=http://local-rag-api:8080}"
: "${OPENCLAW_GATEWAY_BIND:=127.0.0.1}"
: "${OPENCLAW_GATEWAY_PORT:=18789}"

if [[ ! -r "$OPENCLAW_SECRETS_FILE" ]]; then
    printf 'OpenClaw healthcheck missing secrets file: %s\n' "$OPENCLAW_SECRETS_FILE" >&2
    exit 1
fi

python3 - "$OPENCLAW_GATEWAY_BIND" "$OPENCLAW_GATEWAY_PORT" <<'PY'
import json
import sys
import urllib.request

bind = sys.argv[1]
port = sys.argv[2]
url = f'http://{bind}:{port}/health'

try:
    with urllib.request.urlopen(url, timeout=5) as response:
        payload = json.loads(response.read().decode('utf-8'))
except Exception as exc:
    print(f'OpenClaw healthcheck failed: {exc}', file=sys.stderr)
    raise SystemExit(1)

if payload.get('status') != 'ok':
    print('OpenClaw healthcheck reported a non-ok status', file=sys.stderr)
    raise SystemExit(1)

print(f'OpenClaw runtime healthcheck ok: {url}')
PY
