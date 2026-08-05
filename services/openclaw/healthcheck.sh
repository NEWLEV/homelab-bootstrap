#!/usr/bin/env bash
set -Eeuo pipefail

: "${OPENCLAW_SECRETS_FILE:=/run/secrets/openclaw_env}"
: "${OPENCLAW_LOCAL_RAG_URL:=http://local-rag-api:8080}"
: "${OPENCLAW_GATEWAY_BIND:=127.0.0.1}"
: "${OPENCLAW_GATEWAY_PORT:=18789}"

if [[ ! -r "$OPENCLAW_SECRETS_FILE" ]]; then
    printf 'OpenClaw healthcheck missing secrets file: %s
' "$OPENCLAW_SECRETS_FILE" >&2
    exit 1
fi

printf 'OpenClaw healthcheck ok: %s -> %s:%s
'     "$OPENCLAW_SECRETS_FILE"     "$OPENCLAW_GATEWAY_BIND"     "$OPENCLAW_GATEWAY_PORT"
