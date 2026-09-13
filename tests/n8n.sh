#!/usr/bin/env bash
set -Eeuo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

PASS_COUNT=0
FAIL_COUNT=0

pass() { printf '[PASS] %s\n' "$1"; ((PASS_COUNT += 1)); }
fail() { printf '[FAIL] %s\n' "$1" >&2; ((FAIL_COUNT += 1)); }

assert_contains() {
    local name="$1" expected="$2" file="$3"
    if grep -Fq -- "$expected" "$file"; then pass "$name"; else fail "$name"; fi
}

compose="$REPO_ROOT/compose/automation/n8n.yml"
installer="$REPO_ROOT/scripts/install-n8n-service.sh"

[[ -s "$compose" ]] && pass "n8n compose exists" || fail "n8n compose exists"
[[ -s "$installer" ]] && pass "n8n installer exists" || fail "n8n installer exists"

assert_contains "n8n routes under path prefix" 'PathPrefix(`/n8n`)' "$compose"
assert_contains "n8n sets base path" 'N8N_PATH: /n8n/' "$compose"
assert_contains "n8n persists runtime data" '/srv/data/services/n8n:/home/node/.n8n' "$compose"
assert_contains "n8n can reach Ollama by Docker DNS" 'http://local-rag-ollama:11434' "$compose"
assert_contains "n8n installer generates encryption key" 'N8N_ENCRYPTION_KEY=' "$installer"
assert_contains "n8n installer loads host env" '--env-file "$host_env"' "$installer"
assert_contains "n8n installer grants container group ownership" 'chown "$(id -u):1000"' "$installer"
assert_contains "n8n installer grants container group write access" 'chmod 0770 "$runtime_dir"' "$installer"

if bash -n "$installer"; then
    pass "n8n installer syntax"
else
    fail "n8n installer syntax"
fi

printf '\nPassed: %d\nFailed: %d\n' "$PASS_COUNT" "$FAIL_COUNT"
((FAIL_COUNT == 0))
