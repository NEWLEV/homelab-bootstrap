#!/usr/bin/env bash
set -Eeuo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
readonly REPO_ROOT

PASS_COUNT=0
FAIL_COUNT=0

pass() { printf '[PASS] %s
' "$1"; ((PASS_COUNT += 1)); }
fail() { printf '[FAIL] %s
' "$1" >&2; ((FAIL_COUNT += 1)); }

assert_contains() {
    local name="$1"
    local expected="$2"
    local output="$3"

    if grep -Fq -- "$expected" <<<"$output"; then
        pass "$name"
    else
        fail "$name"
        printf 'Expected to find:
%s
' "$expected" >&2
        printf 'Output:
%s
' "$output" >&2
    fi
}

test_openclaw_readme_exists() {
    if [[ -s "$REPO_ROOT/services/openclaw/README.md" ]]; then
        pass "openclaw service readme exists"
    else
        fail "openclaw service readme exists"
    fi
}

test_openclaw_compose_exists() {
    if [[ -s "$REPO_ROOT/compose/ai/openclaw.yml" ]]; then
        pass "openclaw compose scaffold exists"
    else
        fail "openclaw compose scaffold exists"
    fi
}

test_openclaw_compose_contract() {
    local output
    output="$(cat "$REPO_ROOT/compose/ai/openclaw.yml")"
    assert_contains "openclaw compose names service" "name: openclaw" "$output"
    assert_contains "openclaw compose builds runtime" "build:" "$output"
    assert_contains "openclaw compose mounts state" "/srv/data/services/openclaw:/state" "$output"
    assert_contains "openclaw compose mounts secrets" "openclaw_env" "$output"
    assert_contains "openclaw compose references rag" "rag-private" "$output"
}

test_openclaw_dockerfile_contract() {
    local output
    output="$(cat "$REPO_ROOT/services/openclaw/Dockerfile")"
    assert_contains "openclaw dockerfile copies start script" "COPY start.sh /usr/local/bin/openclaw-start" "$output"
    assert_contains "openclaw dockerfile sets entrypoint" 'ENTRYPOINT ["/usr/local/bin/openclaw-start"]' "$output"
}

test_openclaw_secret_restore_contract() {
    local output
    output="$(cat "$REPO_ROOT/scripts/secrets-restore")"
    assert_contains "openclaw secret restore mentions env" ".config/openclaw/secrets.env" "$output"
    assert_contains "openclaw secret restore validates keys" "OPENCLAW_GATEWAY_TOKEN" "$output"
}

test_openclaw_runtime_contract() {
    local output
    output="$(cat "$REPO_ROOT/services/openclaw/start.sh")"
    assert_contains "openclaw runtime validates secrets file" 'OPENCLAW_SECRETS_FILE' "$output"
    assert_contains "openclaw runtime reports gateway bind" 'OPENCLAW_GATEWAY_BIND' "$output"
    assert_contains "openclaw runtime reports gateway port" 'OPENCLAW_GATEWAY_PORT' "$output"
}

test_openclaw_readme_exists
test_openclaw_compose_exists
test_openclaw_compose_contract
test_openclaw_dockerfile_contract
test_openclaw_secret_restore_contract
test_openclaw_runtime_contract

printf '
Passed: %d
' "$PASS_COUNT"
printf 'Failed: %d
' "$FAIL_COUNT"

((FAIL_COUNT == 0)) || exit 1
