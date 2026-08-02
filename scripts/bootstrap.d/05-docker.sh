#!/usr/bin/env bash
set -Eeuo pipefail

readonly DOCKER_DATA_ROOT="/srv/data/services/docker"
readonly DOCKER_CONFIG="/etc/docker/daemon.json"
readonly KEYRING="/etc/apt/keyrings/docker.asc"
readonly SOURCES_FILE="/etc/apt/sources.list.d/docker.sources"
readonly LOG_DIR="/srv/data/logs/bootstrap"

LOG_FILE="${LOG_DIR}/05-docker-$(date +%Y%m%d-%H%M%S).log"
readonly LOG_FILE

CONFIG_CHANGED=false
DOCKER_WAS_INSTALLED=false

log() {
    printf '\n[%s] %s\n' "$(date '+%F %T')" "$*"
}

success() {
    printf '  [ OK ] %s\n' "$*"
}

die() {
    printf '\nERROR: %s\n' "$*" >&2
    exit 1
}

require_command() {
    local command_name="$1"

    command -v "$command_name" >/dev/null 2>&1 ||
        die "Required command is unavailable: ${command_name}"
}

write_if_changed() {
    local source_file="$1"
    local destination_file="$2"
    local mode="$3"

    if sudo test -f "$destination_file" &&
        sudo cmp --silent "$source_file" "$destination_file"; then
        success "Already current: ${destination_file}"
        return 1
    fi

    if sudo test -f "$destination_file"; then
        local backup_file
        backup_file="${destination_file}.backup.$(date +%Y%m%d-%H%M%S)"

        sudo cp --preserve=all "$destination_file" "$backup_file"
        log "Backed up ${destination_file} to ${backup_file}"
    fi

    sudo install -m "$mode" "$source_file" "$destination_file"
    log "Updated ${destination_file}"
    return 0
}

if [[ "$EUID" -eq 0 ]]; then
    die "Run this script as your normal user, not with sudo."
fi

mountpoint -q /srv/data ||
    die "/srv/data is not mounted. Refusing to continue."

require_command apt-get
require_command cmp
require_command curl
require_command dpkg
require_command dpkg-query
require_command install
require_command python3
require_command sudo
require_command systemctl

mkdir -p "$LOG_DIR"
exec > >(tee -a "$LOG_FILE") 2>&1

ARCH="$(dpkg --print-architecture)"
readonly ARCH

[[ "$ARCH" == "arm64" ]] ||
    die "Expected arm64 architecture; detected ${ARCH}."

# shellcheck source=/dev/null
source /etc/os-release

CODENAME="${VERSION_CODENAME:-}"
readonly CODENAME

[[ -n "$CODENAME" ]] ||
    die "Unable to determine the Debian codename."

log "Detected ${PRETTY_NAME:-Debian}, ${CODENAME}, ${ARCH}"

if command -v docker >/dev/null 2>&1; then
    DOCKER_WAS_INSTALLED=true
    success "Docker is already installed"
fi

log "Checking conflicting container packages"

conflicting_packages=(
    docker.io
    docker-compose
    docker-doc
    podman-docker
    containerd
    runc
)

installed_conflicts=()

for package in "${conflicting_packages[@]}"; do
    if dpkg-query -W -f='${Status}' "$package" 2>/dev/null |
        grep -q "install ok installed"; then
        installed_conflicts+=("$package")
    fi
done

if ((${#installed_conflicts[@]} > 0)); then
    sudo apt-get remove -y "${installed_conflicts[@]}"
else
    success "No conflicting packages are installed"
fi

log "Installing Docker repository prerequisites"

sudo apt-get update
sudo DEBIAN_FRONTEND=noninteractive apt-get install -y \
    ca-certificates \
    curl

log "Configuring Docker repository key"

sudo install -d -m 0755 /etc/apt/keyrings

keyring_temp="$(mktemp)"
sources_temp="$(mktemp)"
daemon_temp="$(mktemp)"

cleanup() {
    rm -f "$keyring_temp" "$sources_temp" "$daemon_temp"
}

trap cleanup EXIT

curl -fsSL https://download.docker.com/linux/debian/gpg \
    -o "$keyring_temp"

chmod 0644 "$keyring_temp"

if write_if_changed "$keyring_temp" "$KEYRING" 0644; then
    CONFIG_CHANGED=true
fi

cat > "$sources_temp" <<EOF
Types: deb
URIs: https://download.docker.com/linux/debian
Suites: ${CODENAME}
Components: stable
Architectures: ${ARCH}
Signed-By: ${KEYRING}
EOF

if write_if_changed "$sources_temp" "$SOURCES_FILE" 0644; then
    CONFIG_CHANGED=true
fi

log "Installing Docker Engine, Buildx, and Compose"

sudo apt-get update
sudo DEBIAN_FRONTEND=noninteractive apt-get install -y \
    docker-ce \
    docker-ce-cli \
    containerd.io \
    docker-buildx-plugin \
    docker-compose-plugin

log "Ensuring Docker data root exists"

sudo install -d -m 0711 -o root -g root "$DOCKER_DATA_ROOT"

cat > "$daemon_temp" <<EOF
{
  "data-root": "${DOCKER_DATA_ROOT}",
  "log-driver": "local",
  "log-opts": {
    "max-size": "20m",
    "max-file": "5"
  }
}
EOF

python3 -m json.tool "$daemon_temp" >/dev/null

if write_if_changed "$daemon_temp" "$DOCKER_CONFIG" 0644; then
    CONFIG_CHANGED=true
fi

log "Ensuring ${USER} belongs to the docker group"

if id -nG "$USER" | tr ' ' '\n' | grep -Fxq docker; then
    success "${USER} is already in the docker group"
else
    sudo usermod -aG docker "$USER"
    log "Added ${USER} to the docker group"
fi

if [[ "$CONFIG_CHANGED" == true ]]; then
    log "Docker configuration changed; restarting services"

    sudo systemctl daemon-reload
    sudo systemctl restart containerd.service
    sudo systemctl restart docker.service
else
    log "Docker configuration is unchanged"

    sudo systemctl enable --now containerd.service
    sudo systemctl enable --now docker.service
fi

sudo systemctl is-active --quiet docker.service ||
    die "Docker did not start successfully."

actual_root="$(sudo docker info --format '{{.DockerRootDir}}')"
readonly actual_root

[[ "$actual_root" == "$DOCKER_DATA_ROOT" ]] ||
    die "Docker root is ${actual_root}; expected ${DOCKER_DATA_ROOT}."

if [[ "$DOCKER_WAS_INSTALLED" == false ]]; then
    log "Running initial Docker test container"
    sudo docker run --rm hello-world
else
    success "Skipping initial test container; Docker was already installed"
fi

log "Docker validation"

sudo docker version
sudo docker compose version

success "Docker data root: ${actual_root}"
success "Docker service is active"

printf '\nDocker phase completed successfully.\n'
printf 'Log saved to: %s\n' "$LOG_FILE"

if ! id -nG "$USER" | tr ' ' '\n' | grep -Fxq docker; then
    printf 'Log out and reconnect before using Docker without sudo.\n'
fi
