#!/usr/bin/env bash
set -Eeuo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

PASS_COUNT=0
FAIL_COUNT=0

pass() { printf '[PASS] %s\n' "$1"; ((PASS_COUNT += 1)); }
fail() { printf '[FAIL] %s\n' "$1" >&2; ((FAIL_COUNT += 1)); }

assert_contains() {
    local name="$1"
    local expected="$2"
    local output="$3"

    if grep -Fq -- "$expected" <<<"$output"; then
        pass "$name"
    else
        fail "$name"
        printf 'Expected to find:\n%s\n' "$expected" >&2
        printf 'Output:\n%s\n' "$output" >&2
    fi
}

test_hermes_docs_exist() {
    if [[ -s "$REPO_ROOT/docs/hermes.md" ]]; then
        pass "hermes docs exist"
    else
        fail "hermes docs exist"
    fi
}

test_hermes_readme_exists() {
    if [[ -s "$REPO_ROOT/services/hermes/README.md" ]]; then
        pass "hermes service readme exists"
    else
        fail "hermes service readme exists"
    fi
}

test_hermes_compose_contract() {
    local output
    output="$(cat "$REPO_ROOT/compose/ai/hermes.yml")"
    assert_contains "hermes compose names service" "name: hermes" "$output"
    assert_contains "hermes compose uses isolated state" "/srv/data/services/hermes/home:/home/hermes" "$output"
    assert_contains "hermes compose references local rag" "LOCAL_RAG_URL: http://local-rag-api:8080" "$output"
    assert_contains "hermes compose keeps api disabled by default" 'API_SERVER_ENABLED: "false"' "$output"
}

test_hermes_docs_exist
test_hermes_readme_exists
test_hermes_compose_contract

printf '\nPassed: %d\n' "$PASS_COUNT"
printf 'Failed: %d\n' "$FAIL_COUNT"

((FAIL_COUNT == 0)) || exit 1
