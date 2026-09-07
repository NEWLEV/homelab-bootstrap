#!/usr/bin/env bash
set -Eeuo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
readonly REPO_ROOT

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
    fi
}

assert_file() {
    local name="$1"
    local file="$2"

    if [[ -s "$file" ]]; then
        pass "$name"
    else
        fail "$name"
    fi
}

test_chat_ui_files() {
    assert_file "aisha ui index exists" "$REPO_ROOT/services/openclaw/ui/index.html"
    assert_file "aisha ui app exists" "$REPO_ROOT/services/openclaw/ui/app.js"
    assert_file "aisha ui styles exist" "$REPO_ROOT/services/openclaw/ui/styles.css"
}

test_gateway_contract() {
    local output
    output="$(cat "$REPO_ROOT/services/openclaw/server.js")"
    assert_contains "gateway exposes conversation api" "/api/conversations" "$output"
    assert_contains "gateway proxies the streaming endpoint" "/ask/stream" "$output"
    assert_contains "gateway reads the token from a secret file" "local_rag_api_token" "$output"
    assert_contains "gateway sends the bearer token upstream" "authorization: \`Bearer \${token}\`" "$output"
    assert_contains "gateway keeps idempotent retries" "client_message_id" "$output"
    assert_contains "gateway forwards the selected model" "model: generationModel" "$output"
}

test_compose_contract() {
    local output
    output="$(cat "$REPO_ROOT/compose/ai/openclaw.yml")"
    local local_rag_output
    local_rag_output="$(cat "$REPO_ROOT/compose/ai/local-rag.yml")"
    assert_contains "compose routes the aisha chat path" "PathPrefix(\`/aisha\`)" "$output"
    if grep -Fq "PathPrefix(\`/openclaw\`)" <<<"$output"; then
        fail "compose leaves native openclaw path to the host gateway"
    else
        pass "compose leaves native openclaw path to the host gateway"
    fi
    assert_contains "compose uses the private tailnet entrypoint" \
        'traefik.http.routers.aisha-chat.entrypoints: "tailnet"' "$output"
    assert_contains "compose joins the proxy network" "proxy" "$output"
    assert_contains "compose mounts the local rag token secret" "local_rag_api_token" "$output"
    assert_contains "compose pins the real rag network name" "name: local-rag_rag-private" "$output"
    assert_contains "compose configures embed origins" "OPENCLAW_EMBED_ORIGINS" "$output"
    assert_contains "local rag documents qwen model baseline" "qwen3:4b" "$local_rag_output"
    if grep -Fq 'published: "18789"' <<<"$output"; then
        fail "compose does not publish the gateway port"
    else
        pass "compose does not publish the gateway port"
    fi
}

test_dockerfile_contract() {
    local output
    output="$(cat "$REPO_ROOT/services/openclaw/Dockerfile")"
    assert_contains "dockerfile ships the chat ui" "COPY ui /usr/local/share/openclaw-ui" "$output"
}

test_launcher_contract() {
    assert_file "homepage launcher script exists" "$REPO_ROOT/configs/homepage/custom.js"
    assert_file "homepage launcher styles exist" "$REPO_ROOT/configs/homepage/custom.css"
    assert_file "launcher install script exists" "$REPO_ROOT/scripts/install-homepage-aisha-launcher"
    assert_file "local rag model install script exists" "$REPO_ROOT/scripts/install-local-rag-models"

    local output
    output="$(cat "$REPO_ROOT/configs/homepage/custom.js")"
    assert_contains "launcher probes the tailnet chat gateway" "https://aisha.tail4553c9.ts.net/aisha" "$output"
    assert_contains "launcher uses the tailnet gateway origin" "origin: 'https://aisha.tail4553c9.ts.net'" "$output"
    assert_contains "launcher has an accessible label" "Chat with Aisha" "$output"

    local ui_output
    ui_output="$(cat "$REPO_ROOT/services/openclaw/ui/app.js")"
    assert_contains "chat UI exposes a model picker" "modelPicker" "$ui_output"
    assert_contains "chat UI reads nested model health" "health.knowledge_service" "$ui_output"
    local ui_markup
    ui_markup="$(cat "$REPO_ROOT/services/openclaw/ui/index.html")"
    assert_contains "chat UI labels the model picker" 'id="model-picker"' \
        "$ui_markup"
    local panel_styles
    panel_styles="$(cat "$REPO_ROOT/configs/homepage/custom.css")"
    assert_contains "homepage panel has responsive sizing" '#aisha-panel' \
        "$panel_styles"

    if [[ -x "$REPO_ROOT/scripts/install-homepage-aisha-launcher" ]]; then
        pass "launcher install script is executable"
    else
        fail "launcher install script is executable"
    fi

    if [[ -x "$REPO_ROOT/scripts/install-local-rag-models" ]]; then
        pass "local rag model install script is executable"
    else
        fail "local rag model install script is executable"
    fi
}

test_javascript_syntax() {
    if ! command -v node >/dev/null 2>&1; then
        printf '[SKIP] node is not available; skipping JavaScript checks\n'
        return 0
    fi

    local file
    for file in \
        "$REPO_ROOT/services/openclaw/server.js" \
        "$REPO_ROOT/services/openclaw/ui/app.js" \
        "$REPO_ROOT/configs/homepage/custom.js"; do
        if node --check "$file" 2>/dev/null; then
            pass "javascript syntax: ${file#"$REPO_ROOT"/}"
        else
            fail "javascript syntax: ${file#"$REPO_ROOT"/}"
        fi
    done
}

test_gateway_integration() {
    if ! command -v node >/dev/null 2>&1; then
        printf '[SKIP] node is not available; skipping gateway integration tests\n'
        return 0
    fi

    if node --test "$REPO_ROOT/services/openclaw/test/gateway.test.js"; then
        pass "gateway integration test suite"
    else
        fail "gateway integration test suite"
    fi
}

test_chat_ui_files
test_gateway_contract
test_compose_contract
test_dockerfile_contract
test_launcher_contract
test_javascript_syntax
test_gateway_integration

printf '\nPassed: %d\n' "$PASS_COUNT"
printf 'Failed: %d\n' "$FAIL_COUNT"

((FAIL_COUNT == 0)) || exit 1
