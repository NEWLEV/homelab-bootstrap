#!/usr/bin/env bash
set -Eeuo pipefail

# Installs and starts the Hermes runtime with isolated state and generated
# local secrets. This keeps Hermes separate from OpenClaw while still reusing
# the approved Local RAG backend.

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
readonly repo_root

compose_file="$repo_root/compose/ai/hermes.yml"
runtime_dir="${HERMES_RUNTIME_DIR:-/srv/data/services/hermes}"
env_file="${HERMES_ENV_FILE:-$runtime_dir/hermes.env}"
local_rag_token_file="${LOCAL_RAG_API_TOKEN_FILE:-/srv/data/services/local-rag/secrets/api-token}"

if [[ ! -s "$compose_file" ]]; then
    printf 'Hermes compose file is missing: %s\n' "$compose_file" >&2
    exit 1
fi

mkdir -p \
    "$runtime_dir" \
    "$runtime_dir/logs" \
    "$runtime_dir/memories" \
    "$runtime_dir/sessions" \
    "$runtime_dir/skills" \
    "$runtime_dir/workspace"

if [[ ! -s "$env_file" ]]; then
    if ! command -v openssl >/dev/null 2>&1; then
        printf 'openssl is required to generate Hermes secrets.\n' >&2
        exit 1
    fi

    umask 077
    cat >"$env_file" <<EOF
# Hermes runtime secrets and dashboard auth.
API_SERVER_KEY=$(openssl rand -hex 32)
HERMES_DASHBOARD_BASIC_AUTH_USERNAME=hermes
HERMES_DASHBOARD_BASIC_AUTH_PASSWORD=$(openssl rand -hex 16)
HERMES_DASHBOARD_BASIC_AUTH_SECRET=$(openssl rand -hex 32)
EOF
    chmod 600 "$env_file"
    printf 'Installed Hermes env file: %s\n' "$env_file"
else
    chmod 600 "$env_file"
    printf 'Already configured Hermes env file: %s\n' "$env_file"
fi

export HERMES_ENV_FILE="$env_file"
export LOCAL_RAG_API_TOKEN_FILE="$local_rag_token_file"

docker compose -f "$compose_file" config --quiet
docker compose -f "$compose_file" up -d

printf 'Hermes runtime is ready.\n'
printf 'Dashboard: http://aisha:9119/\n'
printf 'API: http://aisha:8642/\n'
