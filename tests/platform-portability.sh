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

assert_contains "README describes portable Linux bootstrap" \
    "supported Debian-family Linux hosts" "$REPO_ROOT/README.md"
assert_contains "README mentions MacBook control machines" \
    "MacBooks are supported as development and control machines" "$REPO_ROOT/README.md"
assert_contains "platform docs exist" \
    "Portable Bootstrap Target" "$REPO_ROOT/docs/platforms.md"
assert_contains "platform docs mention recommendation command" \
    "./install.sh --recommend" "$REPO_ROOT/docs/platforms.md"
assert_contains "host env example documents tailnet bind" \
    "TAILNET_BIND_IP=" "$REPO_ROOT/configs/host.env.example"
assert_contains "host env example documents hostname override" \
    "HOMELAB_HOSTNAME=" "$REPO_ROOT/configs/host.env.example"
assert_contains "installer accepts x86_64" \
    "x86_64|amd64|aarch64|arm64" "$REPO_ROOT/install.sh"
assert_contains "installer documents recommend option" \
    "--recommend" "$REPO_ROOT/install.sh"
assert_contains "installer has MacBook recommendation path" \
    "MacBook development/control machine" "$REPO_ROOT/install.sh"
assert_contains "system phase accepts amd64" \
    "amd64|arm64" "$REPO_ROOT/scripts/bootstrap.d/01-system.sh"
assert_contains "docker phase accepts amd64" \
    "amd64|arm64" "$REPO_ROOT/scripts/bootstrap.d/05-docker.sh"
assert_not_contains "installer no longer requires only ARM64" \
    "Expected ARM64 architecture" "$REPO_ROOT/install.sh"
assert_not_contains "system phase no longer requires only arm64" \
    "Expected arm64 architecture" "$REPO_ROOT/scripts/bootstrap.d/01-system.sh"
assert_not_contains "docker phase no longer requires only arm64" \
    "Expected arm64 architecture" "$REPO_ROOT/scripts/bootstrap.d/05-docker.sh"
assert_contains "homepage direct port bind is configurable" \
    '${TAILNET_BIND_IP:-100.106.201.14}' "$REPO_ROOT/compose/core/homepage.yml"
assert_contains "filebrowser bind IP is configurable" \
    '${TAILNET_BIND_IP:-100.106.201.14}:8080:80' "$REPO_ROOT/compose/core/filebrowser.yml"
assert_contains "portainer bind IP is configurable" \
    '${TAILNET_BIND_IP:-100.106.201.14}:9000:9000' "$REPO_ROOT/compose/core/portainer.yml"
assert_contains "netdata hostname is configurable" \
    '${HOMELAB_HOSTNAME:-aisha}' "$REPO_ROOT/compose/monitoring/netdata.yml"
assert_contains "hermes dashboard bind IP is configurable" \
    'host_ip: ${TAILNET_BIND_IP:-100.106.201.14}' "$REPO_ROOT/compose/ai/hermes.yml"

recommend_output="$(
    AISHA_DETECT_KERNEL=Darwin \
        AISHA_DETECT_OS_PRETTY_NAME='macOS' \
        AISHA_DETECT_ARCH=arm64 \
        AISHA_DETECT_MEMORY_GIB=16 \
        AISHA_DETECT_DATA_MOUNTED=no \
        AISHA_DETECT_HOSTNAME=macbook \
        bash "$REPO_ROOT/install.sh" --recommend
)"

if grep -Fq "Platform: MacBook development/control machine" <<<"$recommend_output" &&
    grep -Fq "Apply bootstrap phases from a Debian-family Linux host or VM" <<<"$recommend_output"; then
    pass "recommendations handle MacBooks"
else
    fail "recommendations handle MacBooks"
fi

printf '\nPassed: %d\nFailed: %d\n' "$PASS_COUNT" "$FAIL_COUNT"
((FAIL_COUNT == 0))
