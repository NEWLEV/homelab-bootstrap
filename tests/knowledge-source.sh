#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly SCRIPT_DIR
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
readonly REPO_ROOT

TEST_ROOT="$(mktemp -d)"
readonly TEST_ROOT
trap 'rm -rf "$TEST_ROOT"' EXIT

SOURCE_REPOSITORY="${TEST_ROOT}/repository"
KNOWLEDGE_SOURCE="${TEST_ROOT}/knowledge-source"
mkdir -p "$SOURCE_REPOSITORY"

git -C "$SOURCE_REPOSITORY" init --quiet
git -C "$SOURCE_REPOSITORY" config user.name "Aisha Test"
git -C "$SOURCE_REPOSITORY" config user.email "aisha-test@localhost"
printf 'first\n' > "${SOURCE_REPOSITORY}/README.md"
git -C "$SOURCE_REPOSITORY" add README.md
git -C "$SOURCE_REPOSITORY" commit --quiet -m first
first_revision="$(git -C "$SOURCE_REPOSITORY" rev-parse HEAD)"

if AISHA_REPOSITORY_ROOT="$SOURCE_REPOSITORY" \
    AISHA_KNOWLEDGE_SOURCE="$KNOWLEDGE_SOURCE" \
    "${REPO_ROOT}/scripts/sync-knowledge-source" >/dev/null 2>&1; then
    printf 'sync accepted a missing revision\n' >&2
    exit 1
fi

if AISHA_REPOSITORY_ROOT="$SOURCE_REPOSITORY" \
    AISHA_KNOWLEDGE_SOURCE="$KNOWLEDGE_SOURCE" \
    "${REPO_ROOT}/scripts/sync-knowledge-source" HEAD >/dev/null 2>&1; then
    printf 'sync accepted a symbolic revision\n' >&2
    exit 1
fi

AISHA_REPOSITORY_ROOT="$SOURCE_REPOSITORY" \
AISHA_KNOWLEDGE_SOURCE="$KNOWLEDGE_SOURCE" \
    "${REPO_ROOT}/scripts/sync-knowledge-source" "$first_revision" >/dev/null

[[ "$(git -C "$KNOWLEDGE_SOURCE" rev-parse HEAD)" == "$first_revision" ]]
[[ -z "$(git -C "$KNOWLEDGE_SOURCE" status --porcelain)" ]]

printf 'dirty\n' > "${KNOWLEDGE_SOURCE}/untracked.txt"
if AISHA_REPOSITORY_ROOT="$SOURCE_REPOSITORY" \
    AISHA_KNOWLEDGE_SOURCE="$KNOWLEDGE_SOURCE" \
    "${REPO_ROOT}/scripts/sync-knowledge-source" "$first_revision" \
        >/dev/null 2>&1; then
    printf 'sync accepted a dirty knowledge source\n' >&2
    exit 1
fi
rm "${KNOWLEDGE_SOURCE}/untracked.txt"

FAKE_BIN="${TEST_ROOT}/bin"
mkdir -p "$FAKE_BIN"
cat > "${FAKE_BIN}/curl" <<'CURL'
#!/usr/bin/env bash
set -Eeuo pipefail
printf '%s\n' "$*" >> "${CURL_ARGS_LOG}"
config="$(cat)"
if [[ "$config" == *'/index?rebuild=true'* ]]; then
    printf '{"status":"indexed","job":{"last_run_status":"succeeded"}}\n'
elif [[ "$config" == *'/index/status'* ]]; then
    printf '{"status":"idle","last_run_status":"succeeded"}\n'
elif [[ "$config" == *'/index/integrity'* ]]; then
    printf '{"valid":true,"reindex_required":false}\n'
else
    exit 1
fi
CURL
chmod +x "${FAKE_BIN}/curl"

TOKEN_FILE="${TEST_ROOT}/token"
CURL_ARGS_LOG="${TEST_ROOT}/curl-args"
printf 'test-token-value\n' > "$TOKEN_FILE"
: > "$CURL_ARGS_LOG"

PATH="${FAKE_BIN}:${PATH}" \
CURL_ARGS_LOG="$CURL_ARGS_LOG" \
AISHA_KNOWLEDGE_SOURCE="$KNOWLEDGE_SOURCE" \
LOCAL_RAG_API_TOKEN_FILE="$TOKEN_FILE" \
LOCAL_RAG_API_URL="http://127.0.0.1:1" \
    "${REPO_ROOT}/scripts/index-knowledge" >/dev/null

if rg -q 'test-token-value' "$CURL_ARGS_LOG"; then
    printf 'indexing token leaked into curl arguments\n' >&2
    exit 1
fi

rg -q 'AISHA_KNOWLEDGE_SOURCE:-/srv/data/git/homelab-bootstrap-index' \
    "${REPO_ROOT}/compose/ai/local-rag.yml"

printf 'Knowledge source validation passed.\n'
