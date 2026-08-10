#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly SCRIPT_DIR

REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
readonly REPO_ROOT

readonly MANIFEST="${REPO_ROOT}/configs/services.json"
readonly DATA_MOUNT="/srv/data"
readonly MINIMUM_FREE_GIB=20

PASS_COUNT=0
WARN_COUNT=0
FAIL_COUNT=0
SKIP_COUNT=0

pass() {
    PASS_COUNT=$((PASS_COUNT + 1))
    printf '  [PASS] %s\n' "$*"
}

warn() {
    WARN_COUNT=$((WARN_COUNT + 1))
    printf '  [WARN] %s\n' "$*" >&2
}

fail() {
    FAIL_COUNT=$((FAIL_COUNT + 1))
    printf '  [FAIL] %s\n' "$*" >&2
}

skip() {
    SKIP_COUNT=$((SKIP_COUNT + 1))
    printf '  [SKIP] %s\n' "$*"
}

section() {
    printf '\n============================================================\n'
    printf '%s\n' "$*"
    printf '============================================================\n'
}

require_command() {
    local command_name="$1"

    if command -v "$command_name" >/dev/null 2>&1; then
        pass "Command available: ${command_name}"
    else
        fail "Required command unavailable: ${command_name}"
    fi
}

record_result() {
    local required="$1"
    local success_message="$2"
    local failure_message="$3"
    local result="$4"

    if [[ "$result" == "true" ]]; then
        pass "$success_message"
    elif [[ "$required" == "true" ]]; then
        fail "$failure_message"
    else
        warn "$failure_message"
    fi
}

validate_manifest() {
    section "Manifest"

    if [[ ! -f "$MANIFEST" ]]; then
        fail "Service manifest does not exist: ${MANIFEST}"
        return
    fi

    if jq empty "$MANIFEST" >/dev/null 2>&1; then
        pass "Service manifest contains valid JSON"
    else
        fail "Service manifest contains invalid JSON"
        return
    fi

    local schema_version
    schema_version="$(jq -r '.schema_version // empty' "$MANIFEST")"

    if [[ "$schema_version" == "1" ]]; then
        pass "Manifest schema version: 1"
    else
        fail "Unsupported manifest schema version: ${schema_version:-missing}"
    fi
}

validate_system_profile() {
    section "System profile"

    if "${REPO_ROOT}/tests/system-profile.sh"; then
        pass "System profile and drift map are valid"
    else
        fail "System profile or drift map validation failed"
    fi
}

validate_knowledge_source_contract() {
    section "Knowledge source contract"

    if "${REPO_ROOT}/tests/knowledge-source.sh"; then
        pass "Knowledge source and indexing contract are valid"
    else
        fail "Knowledge source or indexing contract validation failed"
    fi
}

validate_network_policy() {
    section "Network exposure policy"

    if "${REPO_ROOT}/tests/network.sh"; then
        pass "Network exposure policy is valid"
    else
        fail "Network exposure policy validation failed"
    fi
}

validate_openclaw_consolidation() {
    section "OpenClaw consolidation contract"

    if "${REPO_ROOT}/tests/openclaw-consolidation.sh"; then
        pass "OpenClaw consolidation contract is valid"
    else
        fail "OpenClaw consolidation contract validation failed"
    fi
}

validate_homepage_shortcuts() {
    section "Homepage shortcuts"

    if "${REPO_ROOT}/tests/homepage-shortcuts.sh"; then
        pass "Homepage shortcut contract is valid"
    else
        fail "Homepage shortcut contract validation failed"
    fi
}

validate_storage() {
    section "Storage"

    if mountpoint -q "$DATA_MOUNT"; then
        pass "${DATA_MOUNT} is mounted"
    else
        fail "${DATA_MOUNT} is not mounted"
        return
    fi

    local available_kib
    local available_gib

    available_kib="$(
        df --output=avail "$DATA_MOUNT" |
            tail -n 1 |
            tr -d ' '
    )"

    available_gib="$((available_kib / 1024 / 1024))"

    if ((available_gib >= MINIMUM_FREE_GIB)); then
        pass "${DATA_MOUNT} has ${available_gib} GiB available"
    else
        fail \
            "${DATA_MOUNT} has ${available_gib} GiB available; " \
            "${MINIMUM_FREE_GIB} GiB required"
    fi

    local required_directories=(
        "/srv/data/backups"
        "/srv/data/git"
        "/srv/data/logs"
        "/srv/data/scratch"
        "/srv/data/services"
    )

    local directory

    for directory in "${required_directories[@]}"; do
        if [[ -d "$directory" ]]; then
            pass "Directory exists: ${directory}"
        else
            fail "Required directory missing: ${directory}"
        fi
    done
}

validate_compose_files() {
    section "Compose configuration"

    local compose_file
    local required
    local deferred
    local service_name
    local -A checked_files=()

    while IFS= read -r service; do
        service_name="$(jq -r '.name' <<<"$service")"
        compose_file="$(jq -r '.compose_file // empty' <<<"$service")"
        required="$(jq -r '.required // false' <<<"$service")"
        deferred="$(jq -r '.deferred // false' <<<"$service")"

        if [[ "$deferred" == "true" ]]; then
            skip "${service_name}: deferred"
            continue
        fi

        if [[ -z "$compose_file" ]]; then
            record_result \
                "$required" \
                "${service_name}: no Compose file required" \
                "${service_name}: Compose file is missing from manifest" \
                "false"
            continue
        fi

        if [[ -n "${checked_files[$compose_file]:-}" ]]; then
            continue
        fi

        checked_files["$compose_file"]=1

        local absolute_file="${REPO_ROOT}/${compose_file}"

        if [[ ! -f "$absolute_file" ]]; then
            fail "Compose file missing: ${compose_file}"
            continue
        fi

        if docker compose \
            -f "$absolute_file" \
            config --quiet >/dev/null 2>&1; then
            pass "Compose configuration valid: ${compose_file}"
        else
            fail "Compose configuration invalid: ${compose_file}"
        fi
    done < <(jq -c '.services[]' "$MANIFEST")
}

container_state() {
    local container="$1"

    docker inspect \
        --format '{{.State.Status}}' \
        "$container" 2>/dev/null || true
}

container_health() {
    local container="$1"

    docker inspect \
        --format \
        '{{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}}' \
        "$container" 2>/dev/null || true
}

expected_http_status() {
    local actual="$1"
    local service_json="$2"

    jq -e \
        --argjson actual "$actual" \
        '.expected_status | index($actual) != null' \
        <<<"$service_json" >/dev/null 2>&1
}

validate_service() {
    local service="$1"

    local name
    local required
    local deferred
    local validation
    local container

    name="$(jq -r '.name' <<<"$service")"
    required="$(jq -r '.required // false' <<<"$service")"
    deferred="$(jq -r '.deferred // false' <<<"$service")"
    validation="$(jq -r '.validation // "none"' <<<"$service")"
    container="$(jq -r '.container // empty' <<<"$service")"

    if [[ "$deferred" == "true" ]]; then
        skip "${name}: deferred"
        return
    fi

    if [[ "$validation" == "none" ]]; then
        skip "${name}: no runtime validation configured"
        return
    fi

    if [[ -z "$container" ]]; then
        record_result \
            "$required" \
            "${name}: container is not required" \
            "${name}: container name missing from manifest" \
            "false"
        return
    fi

    local state
    state="$(container_state "$container")"

    if [[ "$state" != "running" ]]; then
        if [[ "$required" == "true" ]]; then
            fail "${name}: container state is ${state:-missing}"
        else
            skip "${name}: optional container state is ${state:-missing}"
        fi
        return
    fi

    case "$validation" in
        running)
            pass "${name}: container is running"
            ;;

        docker-health)
            local health
            health="$(container_health "$container")"

            record_result \
                "$required" \
                "${name}: container health is healthy" \
                "${name}: container health is ${health:-unknown}" \
                "$([[ "$health" == "healthy" ]] && echo true || echo false)"
            ;;

        http)
            local url
            local insecure_tls
            local http_code
            local -a curl_options

            url="$(jq -r '.url // empty' <<<"$service")"
            insecure_tls="$(jq -r '.insecure_tls // false' <<<"$service")"

            if [[ -z "$url" ]]; then
                record_result \
                    "$required" \
                    "${name}: HTTP validation configured" \
                    "${name}: HTTP URL missing from manifest" \
                    "false"
                return
            fi

            curl_options=(
                --silent
                --show-error
                --output /dev/null
                --write-out '%{http_code}'
                --connect-timeout 3
                --max-time 10
            )

            if [[ "$insecure_tls" == "true" ]]; then
                curl_options+=(--insecure)
            fi

            http_code="$(
                curl "${curl_options[@]}" "$url" 2>/dev/null || true
            )"

            if [[ "$http_code" =~ ^[0-9]{3}$ ]] &&
                expected_http_status "$http_code" "$service"; then
                pass "${name}: ${url} returned HTTP ${http_code}"
            else
                record_result \
                    "$required" \
                    "${name}: HTTP endpoint is available" \
                    "${name}: ${url} returned HTTP ${http_code:-000}" \
                    "false"
            fi
            ;;

        *)
            record_result \
                "$required" \
                "${name}: validation method is supported" \
                "${name}: unsupported validation method ${validation}" \
                "false"
            ;;
    esac
}

validate_services() {
    section "Managed services"

    while IFS= read -r service; do
        validate_service "$service"
    done < <(jq -c '.services[]' "$MANIFEST")
}

validate_systemd_units() {
    section "Systemd services"

    local unit
    local name
    local required
    local expected_state
    local actual_state

    while IFS= read -r unit; do
        name="$(jq -r '.name' <<<"$unit")"
        required="$(jq -r '.required // false' <<<"$unit")"
        expected_state="$(jq -r '.state // "active"' <<<"$unit")"

        actual_state="$(systemctl is-active "$name" 2>/dev/null || true)"

        record_result \
            "$required" \
            "${name}: ${actual_state}" \
            "${name}: expected ${expected_state}, found ${actual_state}" \
            "$(
                [[ "$actual_state" == "$expected_state" ]] &&
                    echo true ||
                    echo false
            )"
    done < <(jq -c '.systemd_units[]' "$MANIFEST")
}

validate_systemd_timers() {
    section "Systemd timers"

    local timer
    local name
    local required
    local enabled_state
    local active_state
    local valid

    while IFS= read -r timer; do
        name="$(jq -r '.name' <<<"$timer")"
        required="$(jq -r '.required // false' <<<"$timer")"

        enabled_state="$(systemctl is-enabled "$name" 2>/dev/null || true)"
        active_state="$(systemctl is-active "$name" 2>/dev/null || true)"

        valid=false

        if [[ "$enabled_state" == "enabled" &&
            "$active_state" == "active" ]]; then
            valid=true
        fi

        record_result \
            "$required" \
            "${name}: enabled and active" \
            "${name}: enabled=${enabled_state}, active=${active_state}" \
            "$valid"
    done < <(jq -c '.systemd_timers[]' "$MANIFEST")
}

print_summary() {
    section "Validation summary"

    printf 'Passed:  %d\n' "$PASS_COUNT"
    printf 'Warnings: %d\n' "$WARN_COUNT"
    printf 'Skipped: %d\n' "$SKIP_COUNT"
    printf 'Failed:  %d\n' "$FAIL_COUNT"

    if ((FAIL_COUNT > 0)); then
        printf '\nAisha validation FAILED.\n' >&2
        return 1
    fi

    printf '\nAisha validation PASSED.\n'
}

main() {
    section "Aisha system validation"

    require_command curl
    require_command df
    require_command docker
    require_command jq
    require_command mountpoint
    require_command systemctl

    if ((FAIL_COUNT > 0)); then
        print_summary
        exit 1
    fi

    validate_manifest
    validate_system_profile
    validate_knowledge_source_contract
    validate_network_policy
    validate_openclaw_consolidation
    validate_homepage_shortcuts

    if ((FAIL_COUNT > 0)); then
        print_summary
        exit 1
    fi

    validate_storage
    validate_compose_files
    validate_services
    validate_systemd_units
    validate_systemd_timers

    print_summary
}

main "$@"
