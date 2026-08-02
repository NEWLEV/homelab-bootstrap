#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_NAME="$(basename "$0")"
readonly SCRIPT_NAME
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly REPO_ROOT
readonly BOOTSTRAP_DIR="${REPO_ROOT}/bootstrap"
readonly LOG_DIR="/srv/data/logs/bootstrap"

DRY_RUN=true
ASSUME_YES=false
LIST_ONLY=false
VERBOSE=false
RESTORE_SECRETS=false
CURRENT_PHASE="preflight"

declare -a PHASES=()
declare -a COMPLETED_PHASES=()
declare -a SKIPPED_PHASES=()

usage() {
    cat <<EOF
Aisha Homelab Bootstrap Installer

Usage:
  ./${SCRIPT_NAME} [options]

Options:
  --dry-run    Show which bootstrap phases would run without changing the host.
               This is the default behavior.
  --apply      Execute the discovered bootstrap phases.
  --yes        Skip the final confirmation prompt when used with --apply.
  --list       List discovered bootstrap phases and exit.
  --verbose    Enable Bash command tracing.
  --restore-secrets
               Restore runtime secrets from the encrypted SOPS bundle.
  -h, --help   Show this help message.

Examples:
  ./${SCRIPT_NAME}
  ./${SCRIPT_NAME} --list
  ./${SCRIPT_NAME} --apply
  ./${SCRIPT_NAME} --apply --yes

Safety:
  The installer must run as a normal user, not root.
  Individual phases may request sudo access.
  The installer refuses to continue unless /srv/data is mounted.
EOF
}

timestamp() {
    date '+%F %T'
}

log() {
    printf '\n[%s] %s\n' "$(timestamp)" "$*"
}

info() {
    printf '  [INFO] %s\n' "$*"
}

success() {
    printf '  [ OK ] %s\n' "$*"
}

warning() {
    printf '  [WARN] %s\n' "$*" >&2
}

die() {
    printf '\n  [FAIL] %s\n' "$*" >&2
    exit 1
}

on_error() {
    local exit_code=$?
    local line_number=${1:-unknown}

    printf '\n  [FAIL] Phase "%s" failed at line %s with exit code %s.\n' \
        "$CURRENT_PHASE" \
        "$line_number" \
        "$exit_code" >&2

    printf '  Review the bootstrap log for details.\n' >&2
    exit "$exit_code"
}

trap 'on_error "$LINENO"' ERR

parse_arguments() {
    while (($# > 0)); do
        case "$1" in
            --dry-run)
                DRY_RUN=true
                ;;
            --apply)
                DRY_RUN=false
                ;;
            --yes)
                ASSUME_YES=true
                ;;
            --list)
                LIST_ONLY=true
                ;;
            --verbose)
                VERBOSE=true
                ;;
            --restore-secrets)
                RESTORE_SECRETS=true
                DRY_RUN=false
                ;;
            -h|--help)
                usage
                exit 0
                ;;
            *)
                die "Unknown option: $1"
                ;;
        esac

        shift
    done
}

require_command() {
    local command_name="$1"

    command -v "$command_name" >/dev/null 2>&1 ||
        die "Required command is unavailable: ${command_name}"
}

preflight() {
    CURRENT_PHASE="preflight"

    log "Running installer preflight checks"

    [[ "$EUID" -ne 0 ]] ||
        die "Run this installer as your normal user, not with sudo."

    [[ "$(uname -s)" == "Linux" ]] ||
        die "This installer requires Linux."

    local architecture
    architecture="$(uname -m)"

    case "$architecture" in
        aarch64|arm64)
            success "Architecture: ${architecture}"
            ;;
        *)
            die "Expected ARM64 architecture; detected ${architecture}."
            ;;
    esac

    require_command bash
    require_command find
    require_command git
    require_command mountpoint
    require_command sort
    require_command sudo

    [[ -d "$BOOTSTRAP_DIR" ]] ||
        die "Bootstrap directory does not exist: ${BOOTSTRAP_DIR}"

    mountpoint -q /srv/data ||
        die "/srv/data is not mounted. Refusing to continue."

    [[ -w "$REPO_ROOT" ]] ||
        die "Repository is not writable by the current user."

    success "Repository root: ${REPO_ROOT}"
    success "/srv/data is mounted"
    success "Running as user: ${USER:-$(id -un)}"

    if git -C "$REPO_ROOT" diff --quiet &&
        git -C "$REPO_ROOT" diff --cached --quiet; then
        success "Tracked repository files are clean"
    else
        warning "The repository contains uncommitted tracked changes."
        warning "The installer will not modify or discard those changes."
    fi
}

discover_phases() {
    CURRENT_PHASE="phase discovery"
    PHASES=()

    while IFS= read -r script; do
        PHASES+=("$script")
    done < <(
        find "$BOOTSTRAP_DIR" \
            -maxdepth 1 \
            -type f \
            -name '[0-9][0-9]-*.sh' \
            -size +0c \
            -print |
            sort
    )

    # Temporary compatibility for the existing Docker bootstrap script.
    # Remove this block after docker.sh is renamed to a numbered phase.
    local legacy_docker="${BOOTSTRAP_DIR}/docker.sh"

    if [[ -s "$legacy_docker" ]]; then
        local already_present=false
        local phase

        for phase in "${PHASES[@]}"; do
            if [[ "$phase" == "$legacy_docker" ]]; then
                already_present=true
                break
            fi
        done

        if [[ "$already_present" == false ]]; then
            PHASES+=("$legacy_docker")
        fi
    fi

    ((${#PHASES[@]} > 0)) ||
        die "No non-empty bootstrap phases were discovered."

    local phase
    for phase in "${PHASES[@]}"; do
        [[ -r "$phase" ]] ||
            die "Bootstrap phase is not readable: ${phase}"

        bash -n "$phase" ||
            die "Bootstrap phase failed syntax validation: ${phase}"
    done
}

print_phases() {
    printf '\nDiscovered bootstrap phases:\n\n'

    local index=1
    local phase

    for phase in "${PHASES[@]}"; do
        printf '  %d. %s\n' "$index" "${phase#"$REPO_ROOT"/}"
        ((index += 1))
    done

    printf '\n'
}

confirm_apply() {
    if [[ "$DRY_RUN" == true || "$ASSUME_YES" == true ]]; then
        return
    fi

    printf '\nWARNING: --apply will execute bootstrap scripts that may:\n'
    printf '  - update operating-system packages\n'
    printf '  - install or remove packages\n'
    printf '  - modify Docker configuration\n'
    printf '  - restart or enable system services\n'
    printf '  - request sudo authentication\n\n'

    read -r -p "Continue with bootstrap execution? [y/N] " response

    case "$response" in
        y|Y|yes|YES)
            ;;
        *)
            printf 'Bootstrap cancelled.\n'
            exit 0
            ;;
    esac
}

prepare_logging() {
    mkdir -p "$LOG_DIR"

    local log_file
    log_file="${LOG_DIR}/install-$(date +%Y%m%d-%H%M%S).log"
    exec > >(tee -a "$log_file") 2>&1

    readonly INSTALL_LOG_FILE="$log_file"
    info "Installer log: ${INSTALL_LOG_FILE}"
}

restore_secrets() {
    CURRENT_PHASE="secret restoration"

    log "Restoring encrypted runtime secrets"

    [[ -x "${REPO_ROOT}/scripts/secrets-restore" ]] ||
        die "scripts/secrets-restore is missing or not executable."

    [[ -n "${SOPS_AGE_KEY_FILE:-}" ]] ||
        die "SOPS_AGE_KEY_FILE is not set."

    "${REPO_ROOT}/scripts/secrets-restore" --apply

    success "Runtime secrets restored"
}

run_phase() {
    local phase="$1"
    local relative_phase="${phase#"$REPO_ROOT"/}"

    CURRENT_PHASE="$relative_phase"

    log "Starting phase: ${relative_phase}"

    if [[ "$DRY_RUN" == true ]]; then
        info "DRY RUN: would execute ${phase}"
        SKIPPED_PHASES+=("$relative_phase")
        return
    fi

    bash "$phase"

    COMPLETED_PHASES+=("$relative_phase")
    success "Completed phase: ${relative_phase}"
}

print_summary() {
    printf '\n============================================================\n'
    printf 'Aisha bootstrap summary\n'
    printf '============================================================\n'

    if [[ "$DRY_RUN" == true ]]; then
        printf 'Mode: dry run\n'
        printf 'Phases discovered: %d\n' "${#PHASES[@]}"
        printf 'Phases executed: 0\n'
    else
        printf 'Mode: apply\n'
        printf 'Phases discovered: %d\n' "${#PHASES[@]}"
        printf 'Phases completed: %d\n' "${#COMPLETED_PHASES[@]}"
    fi

    if ((${#COMPLETED_PHASES[@]} > 0)); then
        printf '\nCompleted:\n'

        local phase
        for phase in "${COMPLETED_PHASES[@]}"; do
            printf '  ✔ %s\n' "$phase"
        done
    fi

    if [[ "$DRY_RUN" == true ]]; then
        printf '\nPlanned:\n'

        local phase
        for phase in "${SKIPPED_PHASES[@]}"; do
            printf '  • %s\n' "$phase"
        done
    fi

    if [[ -n "${INSTALL_LOG_FILE:-}" ]]; then
        printf '\nLog: %s\n' "$INSTALL_LOG_FILE"
    fi

    printf '============================================================\n'

    if [[ "$DRY_RUN" == true ]]; then
        printf '\nDry run completed. No bootstrap phases were executed.\n'
        printf 'Run ./%s --apply to perform the installation.\n' "$SCRIPT_NAME"
    else
        printf '\nBootstrap completed successfully.\n'
        printf 'Review phase output for any recommended reboot or re-login.\n'
    fi
}

main() {
    parse_arguments "$@"

    if [[ "$VERBOSE" == true ]]; then
        set -x
    fi

    preflight
    discover_phases
    print_phases

    if [[ "$LIST_ONLY" == true ]]; then
        exit 0
    fi

    if [[ "$RESTORE_SECRETS" == true ]]; then
        prepare_logging
        restore_secrets
        exit 0
    fi

    confirm_apply

    if [[ "$DRY_RUN" == false ]]; then
        prepare_logging
    fi

    local phase
    for phase in "${PHASES[@]}"; do
        run_phase "$phase"
    done

    CURRENT_PHASE="summary"
    print_summary
}

main "$@"
