#!/usr/bin/env bash
set -Eeuo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PASS_COUNT=0
FAIL_COUNT=0
pass() { printf '[PASS] %s\n' "$1"; ((PASS_COUNT += 1)); }
fail() { printf '[FAIL] %s\n' "$1" >&2; ((FAIL_COUNT += 1)); }
contains() { grep -Fq -- "$2" "$3" && pass "$1" || fail "$1"; }

compose="$REPO_ROOT/compose/ai/paperclip.yml"
installer="$REPO_ROOT/scripts/install-paperclip-service.sh"
[[ -s "$compose" ]] && pass "Paperclip compose exists" || fail "Paperclip compose exists"
[[ -x "$installer" || -s "$installer" ]] && pass "Paperclip installer exists" || fail "Paperclip installer exists"
contains "Paperclip uses authenticated private mode" 'PAPERCLIP_DEPLOYMENT_MODE: authenticated' "$compose"
contains "Paperclip exposes the dashboard on tailnet port 3100" 'published: "3100"' "$compose"
contains "Paperclip serves the local aisha hostname" 'host_ip: 127.0.1.1' "$compose"
contains "Paperclip joins Local RAG network" 'name: local-rag_rag-private' "$compose"
contains "Paperclip joins OpenClaw network" 'name: openclaw_openclaw-private' "$compose"
contains "Paperclip joins Hermes network" 'name: hermes_hermes-private' "$compose"
contains "Paperclip allows approved private HTTP adapters" 'PAPERCLIP_HTTP_ADAPTER_PRIVATE_ENDPOINT_ALLOWLIST' "$compose"
contains "Paperclip persists its database" '/srv/data/services/paperclip/postgres:/var/lib/postgresql/data' "$compose"
contains "Installer pins the upstream source commit" '1d5a439e2b0e551f7a5129e414d7bdc8582ddd00' "$installer"
contains "Installer reuses an already-present verified commit" 'git -C "$source_dir" cat-file -e' "$installer"
if bash -n "$installer"; then pass "Paperclip installer syntax"; else fail "Paperclip installer syntax"; fi
printf '\nPassed: %d\nFailed: %d\n' "$PASS_COUNT" "$FAIL_COUNT"
((FAIL_COUNT == 0))
