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
    if grep -Fq -- "$expected" "$file"; then
        pass "$name"
    else
        fail "$name"
    fi
}

assert_not_contains() {
    local name="$1" rejected="$2" file="$3"
    if grep -Fq -- "$rejected" "$file"; then fail "$name"; else pass "$name"; fi
}

assert_contains "OpenClaw shortcut points to the tailnet Control UI" \
    "https://aisha.tail4553c9.ts.net/openclaw/" \
    "$REPO_ROOT/configs/homepage/services.yaml"
assert_contains "Aisha launcher points to the tailnet chat gateway" \
    "https://aisha.tail4553c9.ts.net/aisha" \
    "$REPO_ROOT/configs/homepage/custom.js"
assert_not_contains "Aisha launcher does not treat native OpenClaw as chat" \
    "https://aisha.tail4553c9.ts.net/openclaw" \
    "$REPO_ROOT/configs/homepage/custom.js"
assert_contains "Hermes shortcut is present" \
    "http://aisha:9119/" \
    "$REPO_ROOT/configs/homepage/custom.js"
assert_contains "n8n shortcut points to secure automation UI" \
    "https://aisha.tail4553c9.ts.net/n8n/" \
    "$REPO_ROOT/configs/homepage/services.yaml"
assert_contains "Kuma shortcut is present" \
    "http://100.106.201.14:3001" \
    "$REPO_ROOT/configs/homepage/custom.js"
assert_contains "File Browser shortcut is present" \
    "http://100.106.201.14:8080" \
    "$REPO_ROOT/configs/homepage/custom.js"
assert_contains "Portainer shortcut uses the live HTTP page" \
    "http://100.106.201.14:9000" \
    "$REPO_ROOT/configs/homepage/custom.js"
assert_contains "Netdata shortcut is present" \
    "http://100.106.201.14:19999" \
    "$REPO_ROOT/configs/homepage/custom.js"
assert_contains "Pironman shortcut points to the live dashboard" \
    "http://aisha:34001" \
    "$REPO_ROOT/configs/homepage/custom.js"

assert_contains "Hermes dashboard card is present" \
    "Live Hermes dashboard" \
    "$REPO_ROOT/configs/homepage/services.yaml"
assert_contains "Hermes dashboard card links to the live runtime" \
    "http://aisha:9119/" \
    "$REPO_ROOT/configs/homepage/services.yaml"

assert_contains "Homepage launcher no longer injects the duplicate shortcut panel" \
    "document.body.appendChild(button);" \
    "$REPO_ROOT/configs/homepage/custom.js"

if node --check "$REPO_ROOT/configs/homepage/custom.js"; then
    pass "homepage launcher syntax"
else
    fail "homepage launcher syntax"
fi

if [[ -s "$REPO_ROOT/configs/homepage/custom.css" ]]; then
    pass "homepage styles exist"
else
    fail "homepage styles exist"
fi

printf '\nPassed: %d\nFailed: %d\n' "$PASS_COUNT" "$FAIL_COUNT"
((FAIL_COUNT == 0))


