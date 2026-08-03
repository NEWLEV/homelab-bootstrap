#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_NAME="$(basename "$0")"
readonly SCRIPT_NAME
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly REPO_ROOT
readonly BOOTSTRAP_DIR="${REPO_ROOT}/scripts/bootstrap.d"
readonly BOOTSTRAP_MANIFEST="${REPO_ROOT}/configs/bootstrap.json"
readonly LOG_DIR="/srv/data/logs/bootstrap"

INSTALLER_TEST_MODE="${AISHA_INSTALLER_TEST_MODE:-false}"

DRY_RUN=true
ASSUME_YES=false
LIST_ONLY=false
VERBOSE=false
RESTORE_SECRETS=false
CURRENT_PHASE="preflight"

declare -a PHASES=()
declare -a PHASE_IDS=()
declare -a PHASE_DESCRIPTIONS=()
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

    if [[ "$INSTALLER_TEST_MODE" == true ]]; then
        info "Test mode: skipping ARM64 architecture requirement"
    else
        case "$architecture" in
            aarch64|arm64)
                success "Architecture: ${architecture}"
                ;;
            *)
                die "Expected ARM64 architecture; detected ${architecture}."
                ;;
        esac
    fi

    require_command bash
    require_command git
    require_command jq
    require_command mountpoint
    require_command sudo

    [[ -d "$BOOTSTRAP_DIR" ]] ||
        die "Bootstrap directory does not exist: ${BOOTSTRAP_DIR}"

    [[ -r "$BOOTSTRAP_MANIFEST" ]] ||
        die "Bootstrap manifest is not readable: ${BOOTSTRAP_MANIFEST}"

    if [[ "$INSTALLER_TEST_MODE" == true ]]; then
        info "Test mode: skipping /srv/data mount requirement"
    else
        mountpoint -q /srv/data ||
            die "/srv/data is not mounted. Refusing to continue."
    fi

    [[ -w "$REPO_ROOT" ]] ||
        die "Repository is not writable by the current user."

    success "Repository root: ${REPO_ROOT}"

    if [[ "$INSTALLER_TEST_MODE" == true ]]; then
        info "Test mode: /srv/data mount was not required"
    else
        success "/srv/data is mounted"
    fi

    success "Running as user: ${USER:-$(id -un)}"

    if git -C "$REPO_ROOT" diff --quiet &&
        git -C "$REPO_ROOT" diff --cached --quiet; then
        success "Tracked repository files are clean"
    else
        warning "The repository contains uncommitted tracked changes."
        warning "The installer will not modify or discard those changes."
    fi
}

validate_dependencies() {
    local index
    local dependency
    local dependency_index
    local step_id
    local candidate_index

    for index in "${!PHASE_IDS[@]}"; do
        step_id="${PHASE_IDS[$index]}"

        while IFS= read -r dependency; do
            [[ -n "$dependency" ]] || continue

            if [[ "$dependency" == "$step_id" ]]; then
                die "Bootstrap step ${step_id} cannot depend on itself."
            fi

            dependency_index=-1

            for candidate_index in "${!PHASE_IDS[@]}"; do
                if [[ "${PHASE_IDS[$candidate_index]}" == "$dependency" ]]; then
                    dependency_index="$candidate_index"
                    break
                fi
            done

            ((dependency_index >= 0)) ||
                die "Bootstrap step ${step_id} depends on unknown step ${dependency}."

            ((dependency_index < index)) ||
                die "Bootstrap step ${step_id} dependency ${dependency} must appear earlier in the manifest."
        done < <(
            jq -r \
                --arg id "$step_id" \
                '.steps[] |
                 select(.enabled != false and .id == $id) |
                 (.depends_on // [])[]' \
                "$BOOTSTRAP_MANIFEST"
        )
    done
}

discover_phases() {
    CURRENT_PHASE="phase discovery"
    PHASES=()
    PHASE_IDS=()
    PHASE_DESCRIPTIONS=()

    jq empty "$BOOTSTRAP_MANIFEST" >/dev/null 2>&1 ||
        die "Bootstrap manifest contains invalid JSON."

    local schema_version
    schema_version="$(
        jq -r '.schema_version // empty' "$BOOTSTRAP_MANIFEST"
    )"

    [[ "$schema_version" == "1" ]] ||
        die "Unsupported bootstrap manifest schema: ${schema_version:-missing}"

    local step_count
    step_count="$(
        jq \
            '[.steps[]? | select(.enabled != false)] | length' \
            "$BOOTSTRAP_MANIFEST"
    )"

    ((step_count > 0)) ||
        die "Bootstrap manifest contains no enabled steps."

    local step
    local step_id
    local script_path
    local description
    local absolute_script

    while IFS= read -r step; do
        step_id="$(jq -r '.id // empty' <<<"$step")"
        script_path="$(jq -r '.script // empty' <<<"$step")"
        description="$(jq -r '.description // empty' <<<"$step")"

        [[ -n "$step_id" ]] ||
            die "Bootstrap manifest contains a step without an id."

        [[ -n "$script_path" ]] ||
            die "Bootstrap step ${step_id} has no script path."

        [[ -n "$description" ]] ||
            die "Bootstrap step ${step_id} has no description."

        [[ "$script_path" != /* ]] ||
            die "Bootstrap step ${step_id} must use a repository-relative script path."

        absolute_script="${REPO_ROOT}/${script_path}"

        [[ -f "$absolute_script" ]] ||
            die "Bootstrap step ${step_id} script does not exist: ${script_path}"

        [[ -s "$absolute_script" ]] ||
            die "Bootstrap step ${step_id} script is empty: ${script_path}"

        [[ -r "$absolute_script" ]] ||
            die "Bootstrap step ${step_id} script is not readable: ${script_path}"

        bash -n "$absolute_script" ||
            die "Bootstrap step ${step_id} failed syntax validation: ${script_path}"

        PHASES+=("$absolute_script")
        PHASE_IDS+=("$step_id")
        PHASE_DESCRIPTIONS+=("$description")
    done < <(
        jq -c \
            '.steps[] | select(.enabled != false)' \
            "$BOOTSTRAP_MANIFEST"
    )

    ((${#PHASES[@]} == step_count)) ||
        die "Bootstrap manifest step count did not match discovered phases."

    ((${#PHASE_IDS[@]} == step_count)) ||
        die "Bootstrap manifest ID count did not match discovered phases."

    ((${#PHASE_DESCRIPTIONS[@]} == step_count)) ||
        die "Bootstrap manifest description count did not match discovered phases."

    validate_dependencies
}

print_phases() {
    printf '\nDiscovered bootstrap phases:\n\n'

    local index

    for index in "${!PHASES[@]}"; do
        printf '  %d. %s — %s\n' \
            "$((index + 1))" \
            "${PHASE_IDS[$index]}" \
            "${PHASE_DESCRIPTIONS[$index]}"

        printf '     %s\n' \
            "${PHASES[$index]#"$REPO_ROOT"/}"
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
    local step_id="$2"
    local description="$3"
    local relative_phase="${phase#"$REPO_ROOT"/}"

    CURRENT_PHASE="$relative_phase"

    log "Starting phase: ${step_id} — ${description}"

    if [[ "$DRY_RUN" == true ]]; then
        info "DRY RUN: would execute ${relative_phase}"
        SKIPPED_PHASES+=("${step_id} — ${description}")
        return
    fi

    bash "$phase"

    COMPLETED_PHASES+=("${step_id} — ${description}")
    success "Completed phase: ${step_id}"
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

    local index

    for index in "${!PHASES[@]}"; do
        run_phase \
            "${PHASES[$index]}" \
            "${PHASE_IDS[$index]}" \
            "${PHASE_DESCRIPTIONS[$index]}"
    done

    CURRENT_PHASE="summary"
    print_summary
}

main "$@"
