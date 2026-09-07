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
    local file
    for file in "$REPO_ROOT/docs/hermes.md" "$REPO_ROOT/services/hermes/README.md"; do
        if [[ -s "$file" ]]; then
            pass "$(basename "$file") exists"
        else
            fail "$(basename "$file") exists"
        fi
    done
}

test_hermes_docs_contract() {
    local docs readme
    docs="$(cat "$REPO_ROOT/docs/hermes.md")"
    readme="$(cat "$REPO_ROOT/services/hermes/README.md")"
    assert_contains "hermes docs mention openclaw mount" '/workspace/openclaw' "$docs"
    assert_contains "hermes docs mention local rag" 'Local RAG' "$docs"
    assert_contains "hermes docs mention skills" 'skills and approved MCP servers' "$docs"
    assert_contains "hermes readme mentions backups" 'normal service-data backup and restore flow applies' "$readme"
}

test_hermes_compose_contract() {
    local output
    output="$(cat "$REPO_ROOT/compose/ai/hermes.yml")"
    assert_contains "hermes compose names service" "name: hermes" "$output"
    assert_contains "hermes compose uses isolated state" "/srv/data/services/hermes:/opt/data" "$output"
    assert_contains "hermes compose exposes openclaw repo" "/srv/data/git/homelab-bootstrap/workspaces/development/repo:/workspace/openclaw:ro" "$output"
    assert_contains "hermes compose references local rag" "LOCAL_RAG_URL: http://local-rag-api:8080" "$output"
    assert_contains "hermes compose exposes openclaw repo path" 'OPENCLAW_REPO_PATH: /workspace/openclaw' "$output"
    assert_contains "hermes compose enables api server" 'API_SERVER_ENABLED: "true"' "$output"
    assert_contains "hermes compose enables dashboard" 'HERMES_DASHBOARD: "1"' "$output"
    assert_contains "hermes compose publishes dashboard port" 'published: "9119"' "$output"
    assert_contains "hermes dashboard binds to tailnet" 'host_ip: 100.106.201.14' "$output"
    assert_contains "hermes compose publishes api port" 'published: "8642"' "$output"
    assert_contains "hermes compose loads env file" 'HERMES_ENV_FILE' "$output"
    assert_contains "hermes healthcheck has a request timeout" 'req.setTimeout(5000' "$output"
}

test_hermes_installer_exists() {
    if [[ -x "$REPO_ROOT/scripts/install-hermes-service.sh" ]] || [[ -s "$REPO_ROOT/scripts/install-hermes-service.sh" ]]; then
        pass "hermes installer exists"
    else
        fail "hermes installer exists"
    fi
}

test_hermes_installer_forces_recreate() {
    local output
    output="$(cat "$REPO_ROOT/scripts/install-hermes-service.sh")"
    assert_contains "hermes installer forces recreate" '--force-recreate --remove-orphans' "$output"
}

test_hermes_docs_exist
test_hermes_docs_contract
test_hermes_compose_contract
test_hermes_installer_exists
test_hermes_installer_forces_recreate

printf '\nPassed: %d\n' "$PASS_COUNT"
printf 'Failed: %d\n' "$FAIL_COUNT"

((FAIL_COUNT == 0)) || exit 1
