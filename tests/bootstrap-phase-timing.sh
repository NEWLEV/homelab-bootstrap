#!/usr/bin/env bash
# shellcheck disable=SC1091,SC2034

set -Eeuo pipefail

TEST_REPO_ROOT="$(
    cd "$(dirname "${BASH_SOURCE[0]}")/.." &&
        pwd
)"
readonly TEST_REPO_ROOT

PASS_COUNT=0
FAIL_COUNT=0

pass() {
    printf '[PASS] %s\n' "$1"
    ((PASS_COUNT += 1))
}

fail() {
    printf '[FAIL] %s\n' "$1" >&2
    ((FAIL_COUNT += 1))
}

assert_equal() {
    local name="$1"
    local expected="$2"
    local actual="$3"

    if [[ "$actual" == "$expected" ]]; then
        pass "$name"
    else
        fail "$name"
        printf '  Expected: %s\n' "$expected" >&2
        printf '  Actual:   %s\n' "$actual" >&2
    fi
}

assert_contains() {
    local name="$1"
    local expected="$2"
    local output="$3"

    if grep -Fq -- "$expected" <<<"$output"; then
        pass "$name"
    else
        fail "$name"
        printf '  Expected output to contain:\n' >&2
        printf '    %s\n' "$expected" >&2
        printf '  Actual output:\n%s\n' "$output" >&2
    fi
}

assert_not_contains() {
    local name="$1"
    local unexpected="$2"
    local output="$3"

    if ! grep -Fq -- "$unexpected" <<<"$output"; then
        pass "$name"
    else
        fail "$name"
        printf '  Output unexpectedly contained:\n' >&2
        printf '    %s\n' "$unexpected" >&2
        printf '  Actual output:\n%s\n' "$output" >&2
    fi
}

load_installer() {
    source "$TEST_REPO_ROOT/install.sh"
}

test_format_zero_seconds() {
    local output

    output="$(
        load_installer
        format_duration 0
    )"

    assert_equal \
        "format zero seconds" \
        "0s" \
        "$output"
}

test_format_seconds() {
    local output

    output="$(
        load_installer
        format_duration 59
    )"

    assert_equal \
        "format seconds" \
        "59s" \
        "$output"
}

test_format_minutes() {
    local output

    output="$(
        load_installer
        format_duration 61
    )"

    assert_equal \
        "format minutes" \
        "1m 1s" \
        "$output"
}

test_format_hours() {
    local output

    output="$(
        load_installer
        format_duration 3661
    )"

    assert_equal \
        "format hours" \
        "1h 1m 1s" \
        "$output"
}

test_dry_run_omits_timing() {
    local output

    output="$(
        load_installer

        DRY_RUN=true
        PHASES=(
            "$TEST_REPO_ROOT/scripts/bootstrap.d/01-system.sh"
        )
        PHASE_IDS=("system")
        PHASE_DESCRIPTIONS=(
            "Base operating system configuration"
        )
        COMPLETED_PHASES=()
        SKIPPED_PHASES=(
            "system — Base operating system configuration"
        )
        PHASE_DURATIONS=("0")
        INSTALL_STARTED_AT=100
        INSTALL_FINISHED_AT=100

        print_summary
    )"

    assert_contains \
        "dry run shows planned phase" \
        "• system — Base operating system configuration" \
        "$output"

    assert_not_contains \
        "dry run omits total elapsed" \
        "Total elapsed:" \
        "$output"
}

test_apply_summary_timing() {
    local output

    output="$(
        load_installer

        DRY_RUN=false
        PHASES=(
            "$TEST_REPO_ROOT/scripts/bootstrap.d/01-system.sh"
        )
        PHASE_IDS=("system")
        PHASE_DESCRIPTIONS=(
            "Base operating system configuration"
        )
        COMPLETED_PHASES=(
            "system — Base operating system configuration"
        )
        SKIPPED_PHASES=()
        PHASE_DURATIONS=("61")
        INSTALL_STARTED_AT=100
        INSTALL_FINISHED_AT=161
        INSTALL_LOG_FILE=""

        print_summary
    )"

    assert_contains \
        "apply summary shows phase duration" \
        "✔ system — Base operating system configuration — 1m 1s" \
        "$output"

    assert_contains \
        "apply summary shows total elapsed" \
        "Total elapsed: 1m 1s" \
        "$output"
}

test_run_phase_records_duration() {
    local fixture
    local output
    local duration

    fixture="$(mktemp -d)"

    cat >"$fixture/timed.sh" <<'SCRIPT'
#!/usr/bin/env bash
set -Eeuo pipefail

sleep 1
SCRIPT

    chmod +x "$fixture/timed.sh"

    output="$(
        load_installer

        DRY_RUN=false
        COMPLETED_PHASES=()
        PHASE_DURATIONS=()

        run_phase \
            "$fixture/timed.sh" \
            "timed" \
            "Timed test phase"

        printf 'recorded-duration=%s\n' \
            "${PHASE_DURATIONS[0]}"
    )"

    rm -rf "$fixture"

    duration="$(
        sed -n \
            's/^recorded-duration=//p' \
            <<<"$output"
    )"

    if [[ "$duration" =~ ^[1-9][0-9]*$ ]]; then
        pass "run phase records duration"
    else
        fail "run phase records duration"
        printf '  Expected positive integer duration.\n' >&2
        printf '  Actual duration: %s\n' "${duration:-missing}" >&2
        printf '  Full output:\n%s\n' "$output" >&2
    fi

    assert_contains \
        "run phase reports duration" \
        "Completed phase: timed (" \
        "$output"
}

test_format_zero_seconds
test_format_seconds
test_format_minutes
test_format_hours
test_dry_run_omits_timing
test_apply_summary_timing
test_run_phase_records_duration

printf '\nPassed: %d\n' "$PASS_COUNT"
printf 'Failed: %d\n' "$FAIL_COUNT"

((FAIL_COUNT == 0)) || exit 1

printf '\nBootstrap phase-timing tests passed.\n'
