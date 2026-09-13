#!/usr/bin/env bash
set -Eeuo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
compose_file="$repo_root/compose/automation/n8n.yml"
runtime_dir="${N8N_RUNTIME_DIR:-/srv/data/services/n8n}"
env_file="${N8N_ENV_FILE:-$runtime_dir/n8n.env}"
host_env="${HOST_ENV_FILE:-/srv/data/services/host.env}"

compose_args=(-f "$compose_file")
if [[ -f "$host_env" ]]; then
    compose_args=(--env-file "$host_env" "${compose_args[@]}")
fi

generate_key() {
    if command -v openssl >/dev/null 2>&1; then
        openssl rand -hex 32
    else
        python3 - <<'PY'
import secrets
print(secrets.token_hex(32))
PY
    fi
}

mkdir -p "$runtime_dir"
chmod 700 "$runtime_dir"

if [[ ! -s "$env_file" ]]; then
    umask 077
    {
        printf 'N8N_ENCRYPTION_KEY=%s\n' "$(generate_key)"
    } >"$env_file"
    printf 'Generated n8n runtime env at %s.\n' "$env_file"
else
    chmod 600 "$env_file"
    printf 'Using existing n8n runtime env at %s.\n' "$env_file"
fi

docker network inspect proxy >/dev/null 2>&1 || docker network create proxy >/dev/null

docker compose "${compose_args[@]}" up -d --force-recreate --remove-orphans

printf 'n8n: https://%s/n8n/\n' "${TAILSCALE_SERVE_HOST:-aisha.tail4553c9.ts.net}"
