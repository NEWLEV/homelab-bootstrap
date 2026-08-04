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
            "Bootstrap phase docker has dependencies; use --with-dependencies." \
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

test_with_dependencies_requires_phase() {
    local output
    local status

    set +e
    output="$(run_installer --with-dependencies)"
    status=$?
    set -e

    if ((status != 0)) &&
        grep -Fq -- \
            "--with-dependencies requires --phase <id>." \
            <<<"$output"; then
        pass "with-dependencies requires phase"
    else
        fail "with-dependencies requires phase"
        printf '%s\n' "$output" >&2
    fi
}

test_transitive_dependencies_list() {
    local output
    local status
    local system_line
    local storage_line
    local docker_line

    set +e
    output="$(
        run_installer \
            --phase docker \
            --with-dependencies \
            --list
    )"
    status=$?
    set -e

    system_line="$(
        grep -nF \
            "system — Base operating system configuration" \
            <<<"$output" |
            head -n 1 |
            cut -d: -f1
    )"

    storage_line="$(
        grep -nF \
            "storage — Storage configuration" \
            <<<"$output" |
            head -n 1 |
            cut -d: -f1
    )"

    docker_line="$(
        grep -nF \
            "docker — Docker and container runtime" \
            <<<"$output" |
            head -n 1 |
            cut -d: -f1
    )"

    if ((status == 0)) &&
        [[ -n "$system_line" ]] &&
        [[ -n "$storage_line" ]] &&
        [[ -n "$docker_line" ]] &&
        ((system_line < storage_line)) &&
        ((storage_line < docker_line)); then
        pass "transitive dependencies list"
    else
        fail "transitive dependencies list"
        printf '%s\n' "$output" >&2
    fi
}

test_transitive_dependencies_dry_run() {
    local output
    local status

    set +e
    output="$(
        run_installer \
            --phase docker \
            --with-dependencies \
            --dry-run
    )"
    status=$?
    set -e

    if ((status == 0)) &&
        grep -Fq \
            "Phases discovered: 3" \
            <<<"$output" &&
        grep -Fq \
            "DRY RUN: would execute scripts/bootstrap.d/01-system.sh" \
            <<<"$output" &&
        grep -Fq \
            "DRY RUN: would execute scripts/bootstrap.d/02-storage.sh" \
            <<<"$output" &&
        grep -Fq \
            "DRY RUN: would execute scripts/bootstrap.d/05-docker.sh" \
            <<<"$output"; then
        pass "transitive dependencies dry run"
    else
        fail "transitive dependencies dry run"
        printf '%s\n' "$output" >&2
    fi
}

test_dependency_free_phase_with_dependencies() {
    local output
    local status

    set +e
    output="$(
        run_installer \
            --phase system \
            --with-dependencies \
            --dry-run
    )"
    status=$?
    set -e

    if ((status == 0)) &&
        grep -Fq \
            "Phases discovered: 1" \
            <<<"$output" &&
        grep -Fq \
            "scripts/bootstrap.d/01-system.sh" \
            <<<"$output" &&
        ! grep -Fq \
            "scripts/bootstrap.d/02-storage.sh" \
            <<<"$output" &&
        ! grep -Fq \
            "scripts/bootstrap.d/05-docker.sh" \
            <<<"$output"; then
        pass "dependency-free phase with dependencies"
    else
        fail "dependency-free phase with dependencies"
        printf '%s\n' "$output" >&2
    fi
}

test_missing_phase_value
test_unknown_phase
test_dependency_phase_rejected
test_single_phase_list
test_single_phase_dry_run
test_with_dependencies_requires_phase
test_transitive_dependencies_list
test_transitive_dependencies_dry_run
test_dependency_free_phase_with_dependencies

printf '\nPassed: %d\n' "$PASS_COUNT"
printf 'Failed: %d\n' "$FAIL_COUNT"

((FAIL_COUNT == 0)) || exit 1

printf '\nBootstrap phase-selection tests passed.\n'
