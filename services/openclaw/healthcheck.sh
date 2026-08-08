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

health_host="$OPENCLAW_GATEWAY_BIND"
if [[ "$health_host" == "0.0.0.0" || "$health_host" == "::" ]]; then
    health_host="127.0.0.1"
fi

node - "$health_host" "$OPENCLAW_GATEWAY_PORT" <<'JS'
const [host, port] = process.argv.slice(2);
const url = `http://${host}:${port}/health`;

fetch(url, { signal: AbortSignal.timeout(5000) })
  .then(async (response) => {
    if (!response.ok) {
      throw new Error(`unexpected status ${response.status}`);
    }
    const payload = await response.json();
    if (payload.status !== 'ok') {
      throw new Error('OpenClaw healthcheck reported a non-ok status');
    }
    console.log(`OpenClaw runtime healthcheck ok: ${url}`);
  })
  .catch((error) => {
    console.error(`OpenClaw healthcheck failed: ${error.message}`);
    process.exit(1);
  });
JS
