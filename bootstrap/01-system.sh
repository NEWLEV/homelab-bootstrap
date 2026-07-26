#!/usr/bin/env bash
set -Eeuo pipefail

readonly LOG_DIR="/srv/data/logs/bootstrap"
readonly LOG_FILE="${LOG_DIR}/01-system-$(date +%Y%m%d-%H%M%S).log"

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

log "System information"
uname -a
cat /etc/os-release

log "Updating package indexes"
sudo apt-get update

log "Applying available operating-system upgrades"
sudo DEBIAN_FRONTEND=noninteractive apt-get full-upgrade -y

log "Installing baseline administration packages"
sudo DEBIAN_FRONTEND=noninteractive apt-get install -y \
    bash-completion \
    ca-certificates \
    curl \
    fail2ban \
    fd-find \
    file \
    fzf \
    git \
    htop \
    iotop \
    jq \
    less \
    lm-sensors \
    lsof \
    ncdu \
    openssl \
    ripgrep \
    rsync \
    shellcheck \
    smartmontools \
    tmux \
    tree \
    ufw \
    unattended-upgrades \
    unzip \
    vim \
    wget \
    zip

log "Removing unused packages"
sudo DEBIAN_FRONTEND=noninteractive apt-get autoremove -y
sudo apt-get autoclean

log "Enabling time synchronization"
sudo timedatectl set-ntp true

log "Enabling SSD health-monitoring service"
sudo systemctl enable --now smartmontools.service 2>/dev/null || \
    log "smartmontools.service is unavailable; NVMe checks will still work manually."

log "Enabling automatic security upgrades"
sudo systemctl enable --now unattended-upgrades.service

log "Creating convenient command aliases"
ALIASES_FILE="$HOME/.bash_aliases"

touch "$ALIASES_FILE"

add_alias() {
    local line="$1"
    grep -Fxq "$line" "$ALIASES_FILE" || printf '%s\n' "$line" >> "$ALIASES_FILE"
}

add_alias "alias ll='ls -alF'"
add_alias "alias la='ls -A'"
add_alias "alias gs='git status'"
add_alias "alias update='sudo apt update && sudo apt full-upgrade -y'"
add_alias "alias disks='lsblk -o NAME,SIZE,FSTYPE,MOUNTPOINTS,MODEL'"
add_alias "alias temps='vcgencmd measure_temp 2>/dev/null || sensors'"

log "Configuring Git defaults"
git config --global init.defaultBranch main
git config --global pull.ff only

log "Baseline validation"
printf 'Root filesystem: '
findmnt -no SOURCE /
printf 'Data filesystem: '
findmnt -no SOURCE /srv/data
printf 'Architecture: '
dpkg --print-architecture
printf 'Unattended upgrades: '
systemctl is-enabled unattended-upgrades.service || true

log "System baseline completed successfully"
printf '\nLog saved to: %s\n' "$LOG_FILE"
printf 'Reboot after committing the changes.\n'
