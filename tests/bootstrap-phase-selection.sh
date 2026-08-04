#!/usr/bin/env bash
set -Eeuo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
readonly REPO_ROOT

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

run_installer() {
    AISHA_INSTALLER_TEST_MODE=true \
        "$REPO_ROOT/install.sh" "$@" 2>&1
}

test_missing_phase_value() {
    local output
    local status

    set +e
    output="$(run_installer --phase)"
    status=$?
    set -e

    if ((status != 0)) &&
        grep -Fq -- \
            "--phase requires a bootstrap step ID." \
            <<<"$output"; then
        pass "missing phase value"
    else
        fail "missing phase value"
        printf '%s\n' "$output" >&2
    fi
}

test_unknown_phase() {
    local output
    local status

    set +e
    output="$(run_installer --phase missing --list)"
    status=$?
    set -e

    if ((status != 0)) &&
        grep -Fq \
            "Bootstrap phase not found or disabled: missing." \
            <<<"$output"; then
        pass "unknown phase"
    else
        fail "unknown phase"
        printf '%s\n' "$output" >&2
    fi
}

test_dependency_phase_rejected() {
    local output
    local status

    set +e
    output="$(run_installer --phase docker --dry-run)"
    status=$?
    set -e

    if ((status != 0)) &&
        grep -Fq \
            "Bootstrap phase docker has dependencies; targeted execution is not supported yet." \
            <<<"$output"; then
        pass "dependent phase rejected"
    else
        fail "dependent phase rejected"
        printf '%s\n' "$output" >&2
    fi
}

test_single_phase_list() {
    local output
    local status

    set +e
    output="$(run_installer --phase system --list)"
    status=$?
    set -e

    if ((status == 0)) &&
        grep -Fq \
            "system — Base operating system configuration" \
            <<<"$output" &&
        ! grep -Fq \
            "storage — Storage configuration" \
            <<<"$output" &&
        ! grep -Fq \
            "docker — Docker and container runtime" \
            <<<"$output"; then
        pass "single phase list"
    else
        fail "single phase list"
        printf '%s\n' "$output" >&2
    fi
}

test_single_phase_dry_run() {
    local output
    local status

    set +e
    output="$(run_installer --phase system --dry-run)"
    status=$?
    set -e

    if ((status == 0)) &&
        grep -Fq \
            "Phases discovered: 1" \
            <<<"$output" &&
        grep -Fq \
            "DRY RUN: would execute scripts/bootstrap.d/01-system.sh" \
            <<<"$output" &&
        ! grep -Fq \
            "scripts/bootstrap.d/02-storage.sh" \
            <<<"$output" &&
        ! grep -Fq \
            "scripts/bootstrap.d/05-docker.sh" \
            <<<"$output"; then
        pass "single phase dry run"
    else
        fail "single phase dry run"
        printf '%s\n' "$output" >&2
    fi
}

test_missing_phase_value
test_unknown_phase
test_dependency_phase_rejected
test_single_phase_list
test_single_phase_dry_run

printf '\nPassed: %d\n' "$PASS_COUNT"
printf 'Failed: %d\n' "$FAIL_COUNT"

((FAIL_COUNT == 0)) || exit 1

printf '\nBootstrap phase-selection tests passed.\n'
