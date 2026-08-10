#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly SCRIPT_DIR
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
readonly REPO_ROOT

readonly PROFILE="${REPO_ROOT}/docs/system-profile.json"
readonly DRIFT="${REPO_ROOT}/docs/drift-map.json"
readonly EVENT_SCHEMA="${REPO_ROOT}/schemas/mission_control/agent-event.schema.json"
readonly APPROVAL_SCHEMA="${REPO_ROOT}/schemas/mission_control/approval.schema.json"

for document in "$PROFILE" "$DRIFT" "$EVENT_SCHEMA" "$APPROVAL_SCHEMA"; do
    jq empty "$document"
done

jq -e '
    .schema_version == 1 and
    (.host.hostname | type == "string") and
    (.storage | length > 0) and
    (.runtimes | type == "object") and
    (.backup.local.status == "green") and
    (.backup.offsite.status == "green")
' "$PROFILE" >/dev/null

jq -e '
    .schema_version == 1 and
    (.containers | type == "array") and
    (.systemd_services | type == "array") and
    (.listeners | type == "array") and
    (.manual_processes | type == "array") and
    ([.containers[], .systemd_services[], .listeners[], .manual_processes[]]
        | all(.status == "declared" or .status == "mismatch" or
              .status == "unmanaged" or .status == "unverified")) and
    ([.listeners[].audience]
        | all(. == "localhost" or . == "tailnet" or . == "lan" or
              . == "internet")) and
    ([.listeners[] | "\(.protocol):\(.port):\(.bind)"] as $keys
        | ($keys | length) == ($keys | unique | length))
' "$DRIFT" >/dev/null

while IFS= read -r line; do
    jq -e '
        (.agent | type == "string" and length > 0) and
        (.kind | IN("task_started", "task_progress", "task_completed",
                    "task_failed", "action_taken", "approval_requested",
                    "approval_resolved", "alert")) and
        (.title | type == "string" and length > 0)
    ' >/dev/null <<<"$line"
done < "${REPO_ROOT}/docs/mission-events.jsonl"

while IFS= read -r line; do
    jq -e '
        (.requested_by | type == "string" and length > 0) and
        (.title | type == "string" and length > 0) and
        (.status | IN("pending", "approved", "rejected", "expired"))
    ' >/dev/null <<<"$line"
done < "${REPO_ROOT}/docs/mission-approvals.jsonl"

printf 'System profile validation passed.\n'
