#!/usr/bin/env bash
set -Eeuo pipefail

readonly DATA_MOUNT="/srv/data"
readonly EXPECTED_FILESYSTEM="ext4"
readonly MINIMUM_FREE_GIB=20
readonly LOG_DIR="/srv/data/logs/bootstrap"

LOG_FILE="${LOG_DIR}/02-storage-$(date +%Y%m%d-%H%M%S).log"
readonly LOG_FILE

DIRECTORIES_CHANGED=false

readonly REQUIRED_DIRECTORIES=(
    "/srv/data/backups"
    "/srv/data/git"
    "/srv/data/logs"
    "/srv/data/scratch"
    "/srv/data/services"
)

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

ensure_directory() {
    local directory="$1"

    if [[ -d "$directory" ]]; then
        success "Directory exists: ${directory}"
    else
        mkdir -p "$directory"
        DIRECTORIES_CHANGED=true
        log "Created directory: ${directory}"
    fi

    local owner
    owner="$(stat -c '%U:%G' "$directory")"

    if [[ "$owner" != "${USER}:${USER}" ]]; then
        warning "${directory} is owned by ${owner}; expected ${USER}:${USER}"
        warning "Ownership was not changed automatically."
    fi
}

if [[ "$EUID" -eq 0 ]]; then
    die "Run this script as your normal user, not with sudo."
fi

require_command df
require_command findmnt
require_command grep
require_command lsblk
require_command mountpoint
require_command stat

mountpoint -q "$DATA_MOUNT" ||
    die "${DATA_MOUNT} is not mounted. Refusing to continue."

mkdir -p "$LOG_DIR"
exec > >(tee -a "$LOG_FILE") 2>&1

log "Inspecting storage layout"

root_source="$(findmnt -n -o SOURCE /)"
root_filesystem="$(findmnt -n -o FSTYPE /)"
root_options="$(findmnt -n -o OPTIONS /)"

data_source="$(findmnt -n -o SOURCE "$DATA_MOUNT")"
data_filesystem="$(findmnt -n -o FSTYPE "$DATA_MOUNT")"
data_options="$(findmnt -n -o OPTIONS "$DATA_MOUNT")"

readonly root_source
readonly root_filesystem
readonly root_options
readonly data_source
readonly data_filesystem
readonly data_options

printf 'Root source: %s\n' "$root_source"
printf 'Root filesystem: %s\n' "$root_filesystem"
printf 'Root options: %s\n' "$root_options"
printf 'Data source: %s\n' "$data_source"
printf 'Data filesystem: %s\n' "$data_filesystem"
printf 'Data options: %s\n' "$data_options"

[[ "$root_source" != "$data_source" ]] ||
    die "Root and data filesystems use the same source device."

success "Root and data filesystems use separate devices"

[[ "$data_filesystem" == "$EXPECTED_FILESYSTEM" ]] ||
    die "${DATA_MOUNT} uses ${data_filesystem}; expected ${EXPECTED_FILESYSTEM}."

success "${DATA_MOUNT} uses ${EXPECTED_FILESYSTEM}"

if grep -qw noatime <<<"$data_options"; then
    success "${DATA_MOUNT} uses noatime"
else
    warning "${DATA_MOUNT} is mounted without noatime"
fi

if grep -Eq \
    '^[^#[:space:]]+[[:space:]]+/srv/data[[:space:]]+' \
    /etc/fstab; then
    success "${DATA_MOUNT} is declared in /etc/fstab"
else
    die "${DATA_MOUNT} is not declared in /etc/fstab."
fi

log "Checking available space"

available_kib="$(df --output=avail "$DATA_MOUNT" | tail -n 1 | tr -d ' ')"
available_gib="$((available_kib / 1024 / 1024))"

readonly available_kib
readonly available_gib

printf 'Available space: %s GiB\n' "$available_gib"

((available_gib >= MINIMUM_FREE_GIB)) ||
    die "${DATA_MOUNT} has less than ${MINIMUM_FREE_GIB} GiB free."

success "${DATA_MOUNT} has sufficient free space"

log "Ensuring required directory structure"

for directory in "${REQUIRED_DIRECTORIES[@]}"; do
    ensure_directory "$directory"
done

log "Storage validation summary"

lsblk -o NAME,PATH,SIZE,FSTYPE,LABEL,MOUNTPOINTS,MODEL
df -hT /
df -hT "$DATA_MOUNT"

success "Storage layout validated"
success "Required directories are present"

printf '\nStorage phase completed successfully.\n'
printf 'Directories changed: %s\n' "$DIRECTORIES_CHANGED"
printf 'Log saved to: %s\n' "$LOG_FILE"
printf '\nNo disks were formatted, partitioned, or mounted by this phase.\n'
