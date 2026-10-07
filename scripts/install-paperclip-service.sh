#!/usr/bin/env bash
set -Eeuo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
compose_file="$repo_root/compose/ai/paperclip.yml"
runtime_dir="${PAPERCLIP_RUNTIME_DIR:-/srv/data/services/paperclip}"
source_dir="${PAPERCLIP_SOURCE_DIR:-$runtime_dir/source}"
env_file="${PAPERCLIP_ENV_FILE:-$runtime_dir/paperclip.env}"
host_env="${HOST_ENV_FILE:-/srv/data/services/host.env}"
git_repo="${PAPERCLIP_GIT_REPOSITORY:-https://github.com/paperclipai/paperclip.git}"
git_commit="${PAPERCLIP_GIT_COMMIT:-1d5a439e2b0e551f7a5129e414d7bdc8582ddd00}"
image="${PAPERCLIP_IMAGE:-paperclip:local-${git_commit:0:12}}"

run_privileged() {
    if "$@" 2>/dev/null; then return 0; fi
    if command -v sudo >/dev/null 2>&1; then sudo "$@"; else "$@"; fi
}

generate_secret() { openssl rand -hex 32; }

mkdir -p "$runtime_dir" "$runtime_dir/data" "$runtime_dir/postgres"

if [[ ! -d "$source_dir/.git" ]]; then
    git clone --filter=blob:none "$git_repo" "$source_dir"
fi
if ! git -C "$source_dir" cat-file -e "${git_commit}^{commit}" 2>/dev/null; then
    git -C "$source_dir" fetch --quiet --depth 1 origin "$git_commit"
fi
git -C "$source_dir" checkout --detach --quiet "$git_commit"
[[ "$(git -C "$source_dir" rev-parse HEAD)" == "$git_commit" ]] || {
    printf 'Paperclip source verification failed.\n' >&2
    exit 1
}

if [[ ! -s "$env_file" ]]; then
    umask 077
    cat >"$env_file" <<EOF
POSTGRES_PASSWORD=$(generate_secret)
DATABASE_URL=postgres://paperclip:$(sed -n 's/^POSTGRES_PASSWORD=//p' "$env_file" 2>/dev/null || true)@db:5432/paperclip
BETTER_AUTH_SECRET=$(generate_secret)
PAPERCLIP_TOOL_ACTION_SIGNING_SECRET=$(generate_secret)
PAPERCLIP_PUBLIC_URL=http://aisha:3100
PAPERCLIP_ALLOWED_HOSTNAMES=aisha,localhost,127.0.0.1,100.106.201.14
EOF
    # The password is generated before the file is written; replace the URL
    # placeholder deterministically without exposing any secret in output.
    password="$(sed -n 's/^POSTGRES_PASSWORD=//p' "$env_file")"
    sed -i "s#^DATABASE_URL=.*#DATABASE_URL=postgres://paperclip:${password}@db:5432/paperclip#" "$env_file"
    chmod 600 "$env_file"
else
    chmod 600 "$env_file"
fi

[[ -s "$env_file" ]] || {
    printf 'Paperclip runtime env is missing: %s\n' "$env_file" >&2
    exit 1
}

compose_args=(-f "$compose_file")
[[ -r "$host_env" ]] && compose_args=(--env-file "$host_env" "${compose_args[@]}")
export PAPERCLIP_ENV_FILE="$env_file" PAPERCLIP_IMAGE="$image"

docker build --pull --build-arg PAPERCLIP_BUILD_COMMIT="$git_commit" -t "$image" "$source_dir"
docker compose "${compose_args[@]}" config --quiet
docker compose "${compose_args[@]}" up -d --force-recreate --remove-orphans

printf 'Paperclip is ready at http://aisha:3100/ (tailnet: http://100.106.201.14:3100/, Homepage: http://aisha:8000/).\n'
printf 'Source commit: %s\n' "$git_commit"
