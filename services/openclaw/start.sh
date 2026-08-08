#!/usr/bin/env bash
set -Eeuo pipefail

: "${OPENCLAW_CONFIG_DIR:=/config}"
: "${OPENCLAW_STATE_DIR:=/state}"
: "${OPENCLAW_SECRETS_FILE:=/run/secrets/openclaw_env}"
: "${OPENCLAW_LOCAL_RAG_URL:=http://local-rag-api:8080}"
: "${OPENCLAW_GATEWAY_BIND:=127.0.0.1}"
: "${OPENCLAW_GATEWAY_PORT:=18789}"
: "${OPENCLAW_LOCAL_RAG_TOKEN_FILE:=/run/secrets/local_rag_api_token}"
: "${NODE_COMPILE_CACHE:=/var/tmp/openclaw-compile-cache}"
: "${OPENCLAW_NO_RESPAWN:=1}"

mkdir -p     "$OPENCLAW_CONFIG_DIR"     "$OPENCLAW_STATE_DIR"     "$OPENCLAW_STATE_DIR/conversations"     "$NODE_COMPILE_CACHE"

if [[ ! -r "$OPENCLAW_SECRETS_FILE" ]]; then
    printf 'OpenClaw secrets file is missing: %s\n' "$OPENCLAW_SECRETS_FILE" >&2
    exit 1
fi

if [[ ! -r "$OPENCLAW_LOCAL_RAG_TOKEN_FILE" ]]; then
    printf 'Warning: Local RAG API token file is missing: %s\n' "$OPENCLAW_LOCAL_RAG_TOKEN_FILE" >&2
    printf 'Warning: Aisha chat will report itself unavailable until the token is provisioned.\n' >&2
fi

printf 'OpenClaw deployment runtime ready.\n'
printf 'Config: %s\n' "$OPENCLAW_CONFIG_DIR"
printf 'State: %s\n' "$OPENCLAW_STATE_DIR"
printf 'Secrets: %s\n' "$OPENCLAW_SECRETS_FILE"
printf 'Local RAG: %s\n' "$OPENCLAW_LOCAL_RAG_URL"
printf 'Gateway: %s:%s\n' "$OPENCLAW_GATEWAY_BIND" "$OPENCLAW_GATEWAY_PORT"

exec node /usr/local/bin/openclaw-server.js
