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
host_env="${AISHA_HOST_ENV:-/srv/data/services/host.env}"
local_rag_token_file="${LOCAL_RAG_API_TOKEN_FILE:-/srv/data/services/local-rag/secrets/api-token}"
compose_args=()

require_sudo() {
    if ! command -v sudo >/dev/null 2>&1; then
        printf 'sudo is required to update container-owned Hermes runtime paths.\n' >&2
        exit 1
    fi
}

mkdir_runtime_paths() {
    if mkdir -p "$@" 2>/dev/null; then
        return 0
    fi

    require_sudo
    sudo mkdir -p "$@"
}

chmod_path() {
    local mode="$1"
    local path="$2"

    if chmod "$mode" "$path" 2>/dev/null; then
        return 0
    fi

    require_sudo
    sudo chmod "$mode" "$path"
}

repair_failed_gateway_state() {
    local state_file="$runtime_dir/gateway_state.json"
    local backup_file

    if [[ ! -s "$state_file" ]] && ! sudo test -s "$state_file" 2>/dev/null; then
        return 0
    fi

    if ! grep -Eq '"(gateway_state|desired_state)"[[:space:]]*:[[:space:]]*"(starting|startup_failed)"' "$state_file" 2>/dev/null; then
        require_sudo
        if ! sudo grep -Eq '"(gateway_state|desired_state)"[[:space:]]*:[[:space:]]*"(starting|startup_failed)"' "$state_file"; then
            return 0
        fi
    fi

    backup_file="${state_file}.$(date -u +%Y%m%dT%H%M%SZ).bak"
    if cp -p "$state_file" "$backup_file" 2>/dev/null && cat >"$state_file" <<EOF
{"gateway_state":"running","desired_state":"running","timestamp":$(date +%s),"kind":"hermes-gateway","repaired_from":"transient-startup-failure","backup":"$backup_file"}
EOF
    then
        chmod_path 600 "$state_file"
        printf 'Repaired transient Hermes gateway startup state: %s\n' "$backup_file"
        return 0
    fi

    require_sudo
    sudo cp -p "$state_file" "$backup_file"
    printf '{"gateway_state":"running","desired_state":"running","timestamp":%s,"kind":"hermes-gateway","repaired_from":"transient-startup-failure","backup":"%s"}\n' \
        "$(date +%s)" "$backup_file" |
        sudo tee "$state_file" >/dev/null
    sudo chmod 600 "$state_file"
    printf 'Repaired transient Hermes gateway startup state: %s\n' "$backup_file"
}

if [[ -r "$host_env" ]]; then
    compose_args+=(--env-file "$host_env")
fi

if [[ ! -s "$compose_file" ]]; then
    printf 'Hermes compose file is missing: %s\n' "$compose_file" >&2
    exit 1
fi

mkdir_runtime_paths \
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
    chmod_path 600 "$env_file"
    printf 'Installed Hermes env file: %s\n' "$env_file"
else
    chmod_path 600 "$env_file"
    printf 'Already configured Hermes env file: %s\n' "$env_file"
fi

repair_failed_gateway_state

export HERMES_ENV_FILE="$env_file"
export LOCAL_RAG_API_TOKEN_FILE="$local_rag_token_file"

docker compose "${compose_args[@]}" -f "$compose_file" config --quiet
docker compose "${compose_args[@]}" -f "$compose_file" up -d --force-recreate --remove-orphans

printf 'Hermes runtime is ready.\n'
printf 'Dashboard: http://aisha:9119/\n'
printf 'API: http://aisha:8642/\n'
