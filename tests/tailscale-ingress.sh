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

script="$REPO_ROOT/scripts/configure-tailscale-ingress"
reconfigure="$REPO_ROOT/scripts/reconfigure-ai-ingress"
assert_contains "ingress installer uses Tailscale Serve" 'tailscale serve' "$script"
assert_contains "ingress installer uses background mode" '--bg' "$script"
assert_contains "ingress installer clears stale handlers" 'tailscale serve reset' "$script"
assert_contains "ingress installer uses loopback backend" \
    'http://127.0.0.1:18080' "$script"
assert_contains "ingress installer preserves optional n8n" \
    '--set-path=/n8n' "$script"
assert_contains "ingress installer checks native OpenClaw" \
    '"$OPENCLAW_BACKEND/openclaw/"' "$script"
assert_contains "ingress installer publishes native OpenClaw" \
    '--set-path=/openclaw' "$script"
assert_contains "ingress installer preserves native base path" \
    '"$OPENCLAW_BACKEND/openclaw"' "$script"
assert_contains "ingress installer checks Traefik first" \
    'Traefik is not ready' "$script"
assert_contains "AI reconfigure script manages Traefik" \
    'compose/networking/traefik.yml' "$reconfigure"
assert_contains "AI reconfigure script verifies OpenClaw" \
    'https://aisha.tail4553c9.ts.net/openclaw/' "$reconfigure"
assert_contains "AI reconfigure script verifies native Control UI" \
    'data-openclaw-control-ui-base-path="/openclaw"' "$reconfigure"
assert_contains "AI reconfigure script verifies Aisha readiness" \
    'https://aisha.tail4553c9.ts.net/aisha/api/health' "$reconfigure"

if bash -n "$script"; then
    pass "ingress installer syntax"
else
    fail "ingress installer syntax"
fi

if bash -n "$reconfigure"; then
    pass "AI reconfigure script syntax"
else
    fail "AI reconfigure script syntax"
fi

printf '\nPassed: %d\n' "$PASS_COUNT"
printf 'Failed: %d\n' "$FAIL_COUNT"
((FAIL_COUNT == 0)) || exit 1
