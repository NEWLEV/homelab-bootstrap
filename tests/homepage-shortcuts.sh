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

assert_contains "OpenClaw shortcut points to the tailnet Control UI" \
    "https://aisha.tail4553c9.ts.net/openclaw/" \
    "$REPO_ROOT/configs/homepage/custom.js"
assert_contains "n8n shortcut points to secure automation UI" \
    "https://aisha.tail4553c9.ts.net/n8n/" \
    "$REPO_ROOT/configs/homepage/custom.js"
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
    "Planned second runtime blueprint, not live yet" \
    "$REPO_ROOT/configs/homepage/services.yaml"
assert_contains "Hermes dashboard card links to its blueprint" \
    "https://github.com/NousResearch/hermes-agent" \
    "$REPO_ROOT/configs/homepage/services.yaml"

assert_contains "Dashboard shortcuts are placed inline after the hero" \
    "dashboardHero.insertAdjacentElement('afterend', quickLinks)" \
    "$REPO_ROOT/configs/homepage/custom.js"
assert_contains "Inline dashboard shortcuts do not cover content" \
    "#aisha-quick-links.aisha-quick-links-inline" \
    "$REPO_ROOT/configs/homepage/custom.css"

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


