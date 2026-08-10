#!/usr/bin/env bash
set -Eeuo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
readonly REPO_ROOT
readonly SCRIPT="${REPO_ROOT}/scripts/consolidate-openclaw"

PASS_COUNT=0
FAIL_COUNT=0

pass() { printf '[PASS] %s\n' "$1"; ((PASS_COUNT += 1)); }
fail() { printf '[FAIL] %s\n' "$1" >&2; ((FAIL_COUNT += 1)); }

assert_contains() {
    local name="$1" expected="$2"
    if grep -Fq -- "$expected" "$SCRIPT"; then pass "$name"; else fail "$name"; fi
}

assert_not_contains() {
    local name="$1" rejected="$2"
    if grep -Fq -- "$rejected" "$SCRIPT"; then fail "$name"; else pass "$name"; fi
}

assert_contains "requires a healthy container" 'container_is_healthy ||'
assert_contains "requires a ready tailnet route" 'tailnet_is_ready ||'
assert_contains "matches the native CLI exactly" '[[ "${args[1]}" == "$NATIVE_CLI" ]]'
assert_contains "uses graceful termination" 'kill -TERM "$pid"'
assert_contains "disables native restart ownership" 'systemctl --user disable --now'
assert_not_contains "does not reset healthy Tailscale Serve" 'tailscale serve reset'
assert_contains "verifies closed legacy host ports" 'host_gateway_ports_are_closed'
assert_contains "verifies tailnet after retirement" 'serve_is_ready'
assert_not_contains "does not force-kill the gateway" 'kill -KILL'
assert_not_contains "does not publish the legacy gateway port" 'published: "18789"'
assert_contains "uses secure OpenClaw serve URL" 'https://aisha.tail4553c9.ts.net/openclaw/api/health'

if bash -n "$SCRIPT"; then pass "script syntax"; else fail "script syntax"; fi
if "$SCRIPT" --dry-run >/dev/null; then pass "dry-run is side-effect free"; else fail "dry-run"; fi

printf '\nPassed: %d\nFailed: %d\n' "$PASS_COUNT" "$FAIL_COUNT"
((FAIL_COUNT == 0))
