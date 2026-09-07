#!/usr/bin/env bash
set -Eeuo pipefail

readonly LOG_DIR="/srv/data/logs/bootstrap"

LOG_FILE="${LOG_DIR}/01-system-$(date +%Y%m%d-%H%M%S).log"
readonly LOG_FILE

PACKAGES_CHANGED=false
ALIASES_CHANGED=false
GIT_CONFIG_CHANGED=false

log() {
    printf '\n[%s] %s\n' "$(date '+%F %T')" "$*"
}

success() {
    printf '  [ OK ] %s\n' "$*"
}

warning() {
    printf '  [WARN] %s\n' "$*" >&2
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

package_is_installed() {
    local package="$1"

    dpkg-query -W -f='${Status}' "$package" 2>/dev/null |
        grep -q "install ok installed"
}

enable_service_if_available() {
    local unit="$1"

    if ! systemctl list-unit-files "$unit" --no-legend 2>/dev/null |
        grep -q "^${unit}"; then
        warning "${unit} is unavailable"
        return
    fi

    if systemctl is-enabled --quiet "$unit"; then
        success "${unit} is enabled"
    else
        sudo systemctl enable "$unit"
        log "Enabled ${unit}"
    fi

    if systemctl is-active --quiet "$unit"; then
        success "${unit} is active"
    else
        sudo systemctl start "$unit"
        log "Started ${unit}"
    fi
}

add_alias() {
    local line="$1"

    if grep -Fxq "$line" "$ALIASES_FILE"; then
        success "Alias already present: ${line}"
        return
    fi

    printf '%s\n' "$line" >> "$ALIASES_FILE"
    ALIASES_CHANGED=true
    log "Added alias: ${line}"
}

set_git_config() {
    local key="$1"
    local desired_value="$2"
    local current_value

    current_value="$(git config --global --get "$key" 2>/dev/null || true)"

    if [[ "$current_value" == "$desired_value" ]]; then
        success "Git ${key}=${desired_value}"
        return
    fi

    git config --global "$key" "$desired_value"
    GIT_CONFIG_CHANGED=true
    log "Configured Git ${key}=${desired_value}"
}

if [[ "$EUID" -eq 0 ]]; then
    die "Run this script as your normal user, not with sudo."
fi

mountpoint -q /srv/data ||
    die "/srv/data is not mounted. Refusing to continue."

require_command dpkg
require_command dpkg-query
require_command findmnt
require_command git
require_command grep
require_command mountpoint
require_command sudo
require_command systemctl
require_command timedatectl
require_command uname

mkdir -p "$LOG_DIR"
exec > >(tee -a "$LOG_FILE") 2>&1

ARCH="$(dpkg --print-architecture)"
readonly ARCH

case "$ARCH" in
    amd64|arm64)
        ;;
    *)
        die "Unsupported Debian architecture: ${ARCH}. Supported: amd64 and arm64."
        ;;
esac

# shellcheck source=/dev/null
source /etc/os-release

log "System information"

printf 'Operating system: %s\n' "${PRETTY_NAME:-unknown}"
printf 'Architecture: %s\n' "$ARCH"
printf 'Kernel: %s\n' "$(uname -r)"
printf 'Root filesystem: %s\n' "$(findmnt -no SOURCE /)"
printf 'Data filesystem: %s\n' "$(findmnt -no SOURCE /srv/data)"

readonly BASELINE_PACKAGES=(
    bash-completion
    ca-certificates
    curl
    fail2ban
    fd-find
    file
    fzf
    git
    htop
    iotop
    jq
    less
    lm-sensors
    lsof
    ncdu
    openssl
    ripgrep
    rsync
    shellcheck
    smartmontools
    tmux
    tree
    ufw
    unattended-upgrades
    unzip
    vim
    wget
    zip
)

missing_packages=()

log "Checking baseline packages"

for package in "${BASELINE_PACKAGES[@]}"; do
    if package_is_installed "$package"; then
        success "Installed: ${package}"
    else
        missing_packages+=("$package")
    fi
done

if ((${#missing_packages[@]} > 0)); then
    log "Installing missing baseline packages"

    printf 'Missing packages:\n'
    printf '  - %s\n' "${missing_packages[@]}"

    sudo apt-get update

    sudo DEBIAN_FRONTEND=noninteractive apt-get install -y \
        "${missing_packages[@]}"

    PACKAGES_CHANGED=true
else
    success "All baseline packages are installed"
fi

log "Configuring time synchronization"

ntp_enabled="$(
    timedatectl show \
        --property=NTP \
        --value \
        2>/dev/null || true
)"

if [[ "$ntp_enabled" == "yes" ]]; then
    success "Network time synchronization is enabled"
else
    sudo timedatectl set-ntp true
    log "Enabled network time synchronization"
fi

log "Configuring system services"

enable_service_if_available unattended-upgrades.service
enable_service_if_available smartmontools.service
enable_service_if_available systemd-timesyncd.service

log "Configuring command aliases"

ALIASES_FILE="${HOME}/.bash_aliases"
readonly ALIASES_FILE

touch "$ALIASES_FILE"
chmod 0644 "$ALIASES_FILE"

add_alias "alias ll='ls -alF'"
add_alias "alias la='ls -A'"
add_alias "alias gs='git status'"
add_alias "alias update='sudo apt update && sudo apt full-upgrade -y'"
add_alias "alias disks='lsblk -o NAME,SIZE,FSTYPE,MOUNTPOINTS,MODEL'"
add_alias "alias temps='vcgencmd measure_temp 2>/dev/null || sensors'"

log "Configuring Git defaults"

set_git_config init.defaultBranch main
set_git_config pull.ff only

log "Final validation"

for package in "${BASELINE_PACKAGES[@]}"; do
    package_is_installed "$package" ||
        die "Package validation failed: ${package}"
done

systemctl is-active --quiet unattended-upgrades.service ||
    die "unattended-upgrades.service is not active."

mountpoint -q /srv/data ||
    die "/srv/data became unavailable during bootstrap."

success "All baseline packages are installed"
success "/srv/data remains mounted"
success "Unattended upgrades are active"

printf '\nSystem phase completed successfully.\n'
printf 'Packages changed: %s\n' "$PACKAGES_CHANGED"
printf 'Aliases changed: %s\n' "$ALIASES_CHANGED"
printf 'Git configuration changed: %s\n' "$GIT_CONFIG_CHANGED"
printf 'Log saved to: %s\n' "$LOG_FILE"

printf '\nRoutine operating-system upgrades are intentionally not run here.\n'
printf 'Use scripts/update or the update alias for maintenance upgrades.\n'
