#!/usr/bin/env bash
set -Eeuo pipefail

readonly DOCKER_DATA_ROOT="/srv/data/services/docker"
readonly DOCKER_CONFIG="/etc/docker/daemon.json"
readonly KEYRING="/etc/apt/keyrings/docker.asc"
readonly SOURCES_FILE="/etc/apt/sources.list.d/docker.sources"

LOG_DIR="/srv/data/logs/bootstrap"
LOG_FILE="${LOG_DIR}/docker-$(date +%Y%m%d-%H%M%S).log"
readonly LOG_DIR LOG_FILE

mkdir -p "$LOG_DIR"
exec > >(tee -a "$LOG_FILE") 2>&1

log() {
    printf '\n[%s] %s\n' "$(date '+%F %T')" "$*"
}

die() {
    printf '\nERROR: %s\n' "$*" >&2
    exit 1
}

if [[ "$EUID" -eq 0 ]]; then
    die "Run this script as your normal user, not with sudo."
fi

if ! mountpoint -q /srv/data; then
    die "/srv/data is not mounted. Refusing to continue."
fi

ARCH="$(dpkg --print-architecture)"
readonly ARCH

[[ "$ARCH" == "arm64" ]] || die "Expected arm64; detected ${ARCH}."

# shellcheck source=/dev/null
source /etc/os-release

CODENAME="${VERSION_CODENAME:-}"
readonly CODENAME

[[ -n "$CODENAME" ]] || die "Unable to determine Debian codename."

log "Detected ${PRETTY_NAME:-Debian}, codename ${CODENAME}, architecture ${ARCH}"

log "Removing conflicting container packages if installed"
packages=(
    docker.io
    docker-compose
    docker-doc
    podman-docker
    containerd
    runc
)

installed=()
for package in "${packages[@]}"; do
    if dpkg-query -W -f='${Status}' "$package" 2>/dev/null |
        grep -q "install ok installed"; then
        installed+=("$package")
    fi
done

if ((${#installed[@]})); then
    sudo apt-get remove -y "${installed[@]}"
else
    log "No conflicting packages found"
fi

log "Installing repository prerequisites"
sudo apt-get update
sudo apt-get install -y ca-certificates curl

log "Installing Docker repository key"
sudo install -m 0755 -d /etc/apt/keyrings
sudo curl -fsSL https://download.docker.com/linux/debian/gpg \
    -o "$KEYRING"
sudo chmod a+r "$KEYRING"

log "Configuring Docker repository"
sudo tee "$SOURCES_FILE" >/dev/null <<EOF_REPO
Types: deb
URIs: https://download.docker.com/linux/debian
Suites: ${CODENAME}
Components: stable
Architectures: ${ARCH}
Signed-By: ${KEYRING}
EOF_REPO

log "Installing Docker Engine, Buildx, and Compose"
sudo apt-get update
sudo apt-get install -y \
    docker-ce \
    docker-ce-cli \
    containerd.io \
    docker-buildx-plugin \
    docker-compose-plugin

log "Stopping Docker before configuring its storage"
sudo systemctl stop docker.service docker.socket containerd.service || true

log "Creating Docker data root"
sudo install -d -m 0711 -o root -g root "$DOCKER_DATA_ROOT"

log "Backing up an existing Docker daemon configuration"
if [[ -f "$DOCKER_CONFIG" ]]; then
    sudo cp --preserve=all \
        "$DOCKER_CONFIG" \
        "${DOCKER_CONFIG}.backup.$(date +%Y%m%d-%H%M%S)"
fi

log "Writing Docker daemon configuration"
sudo install -d -m 0755 /etc/docker

sudo tee "$DOCKER_CONFIG" >/dev/null <<EOF_JSON
{
  "data-root": "${DOCKER_DATA_ROOT}",
  "log-driver": "local",
  "log-opts": {
    "max-size": "20m",
    "max-file": "5"
  }
}
EOF_JSON

log "Validating daemon.json"
python3 -m json.tool "$DOCKER_CONFIG" >/dev/null

log "Adding ${USER} to the docker group"
sudo usermod -aG docker "$USER"

log "Starting Docker"
sudo systemctl daemon-reload
sudo systemctl enable --now containerd.service
sudo systemctl enable --now docker.service

log "Checking Docker service"
sudo systemctl is-active --quiet docker.service ||
    die "Docker did not start successfully."

log "Verifying Docker data root"
actual_root="$(sudo docker info --format '{{.DockerRootDir}}')"
readonly actual_root

[[ "$actual_root" == "$DOCKER_DATA_ROOT" ]] ||
    die "Docker root is ${actual_root}, expected ${DOCKER_DATA_ROOT}."

log "Running Docker test container"
sudo docker run --rm hello-world

log "Docker installation completed successfully"
sudo docker version
sudo docker compose version

printf '\nDocker data root: %s\n' "$actual_root"
printf 'Log saved to: %s\n' "$LOG_FILE"
printf '\nLog out and reconnect before using Docker without sudo.\n'
