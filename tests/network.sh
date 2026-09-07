#!/usr/bin/env bash
set -Eeuo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
readonly REPO_ROOT

PASS_COUNT=0
FAIL_COUNT=0

pass() { printf '[PASS] %s\n' "$1"; ((PASS_COUNT += 1)); }
fail() { printf '[FAIL] %s\n' "$1" >&2; ((FAIL_COUNT += 1)); }

assert_contains() {
    local name="$1" expected="$2" file="$3"
    if grep -Fq -- "$expected" "$file"; then pass "$name"; else fail "$name"; fi
}

assert_not_contains() {
    local name="$1" rejected="$2" file="$3"
    if grep -Fq -- "$rejected" "$file"; then fail "$name"; else pass "$name"; fi
}

assert_contains "Traefik has a private tailnet entrypoint" \
    '--entrypoints.tailnet.address=:18080' \
    "$REPO_ROOT/compose/networking/traefik.yml"
assert_contains "Traefik tailnet entrypoint is loopback bound" \
    '127.0.0.1:18080:18080' \
    "$REPO_ROOT/compose/networking/traefik.yml"
assert_contains "Traefik LAN HTTPS avoids the Tailscale bind" \
    'TRAEFIK_LAN_IP:-192.168.1.97' \
    "$REPO_ROOT/compose/networking/traefik.yml"
assert_contains "OpenClaw uses the private tailnet entrypoint" \
    'traefik.http.routers.aisha-chat.entrypoints: "tailnet"' \
    "$REPO_ROOT/compose/ai/openclaw.yml"
assert_not_contains "OpenClaw has no host-published gateway port" \
    'published: "18789"' "$REPO_ROOT/compose/ai/openclaw.yml"
assert_contains "Homepage direct port is tailnet bound" \
    'host_ip: ${TAILNET_BIND_IP:-100.106.201.14}' "$REPO_ROOT/compose/core/homepage.yml"
assert_contains "Homepage allows the tailnet hostname" \
    'aisha.tail4553c9.ts.net' "$REPO_ROOT/compose/core/homepage.yml"

for mapping in \
    'compose/core/filebrowser.yml:${TAILNET_BIND_IP:-100.106.201.14}:8080:80' \
    'compose/core/portainer.yml:${TAILNET_BIND_IP:-100.106.201.14}:9000:9000' \
    'compose/core/portainer.yml:${TAILNET_BIND_IP:-100.106.201.14}:9443:9443' \
    'compose/monitoring/netdata.yml:${TAILNET_BIND_IP:-100.106.201.14}:19999:19999' \
    'compose/monitoring/uptime-kuma.yml:${TAILNET_BIND_IP:-100.106.201.14}:3001:3001'; do
    file="${mapping%%:*}"
    expected="${mapping#*:}"
    assert_contains "${file} is tailnet bound" "$expected" "$REPO_ROOT/$file"
done

assert_contains "Firewall defaults incoming traffic to deny" \
    'ufw default deny incoming' "$REPO_ROOT/security/firewall.sh"
assert_contains "Firewall protects Docker forwarding" \
    'ensure_jump "$tool"' "$REPO_ROOT/security/firewall.sh"
assert_contains "Firewall permits only Traefik broadly through Docker" \
    '--dports 80,443 -j RETURN' "$REPO_ROOT/security/firewall.sh"
assert_contains "Firewall ends its Docker policy with drop" \
    '-j DROP' "$REPO_ROOT/security/firewall.sh"
assert_contains "OpenClaw trusts only the declared proxy network" \
    '172.23.0.0/16' "$REPO_ROOT/configs/openclaw/openclaw.redacted.json"
assert_not_contains "Tailnet services are not monitored over loopback" \
    '127.0.0.1:3001' "$REPO_ROOT/configs/services.json"
assert_contains "Tailnet service monitoring uses the declared address" \
    '100.106.201.14:19999' "$REPO_ROOT/configs/services.json"

if bash -n "$REPO_ROOT/security/firewall.sh"; then
    pass "Firewall script syntax"
else
    fail "Firewall script syntax"
fi

printf '\nPassed: %d\nFailed: %d\n' "$PASS_COUNT" "$FAIL_COUNT"
((FAIL_COUNT == 0))
