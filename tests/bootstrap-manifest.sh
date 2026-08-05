#!/usr/bin/env bash
set -Eeuo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
readonly REPO_ROOT

PASS_COUNT=0
FAIL_COUNT=0

pass() {
    printf '[PASS] %s\n' "$1"
    ((PASS_COUNT += 1))
}

fail() {
    printf '[FAIL] %s\n' "$1" >&2
    ((FAIL_COUNT += 1))
}

create_fixture() {
    local fixture="$1"

    mkdir -p \
        "$fixture/configs" \
        "$fixture/scripts/bootstrap.d"

    cp "$REPO_ROOT/install.sh" "$fixture/install.sh"
    chmod +x "$fixture/install.sh"

    git -C "$fixture" init -q
}

create_script() {
    local fixture="$1"
    local path="$2"
    local content="${3:-:}"

    mkdir -p "$(dirname "$fixture/$path")"

    cat >"$fixture/$path" <<EOF
#!/usr/bin/env bash
set -Eeuo pipefail
${content}
EOF

    chmod +x "$fixture/$path"
}

run_failure_case() {
    local name="$1"
    local manifest="$2"
    local expected_message="$3"
    local script_path="${4:-}"

    local fixture
    fixture="$(mktemp -d)"

    create_fixture "$fixture"
    if [[ -n "$script_path" ]]; then
        create_script "$fixture" "$script_path"
    fi
    printf '%s\n' "$manifest" >"$fixture/configs/bootstrap.json"

    local output
    local status

    set +e
    output="$(
        cd "$fixture" &&
            AISHA_INSTALLER_TEST_MODE=true \
                ./install.sh --list 2>&1
    )"
    status=$?
    set -e

    rm -rf "$fixture"

    if ((status == 0)); then
        fail "${name}: unexpectedly succeeded"
        return
    fi

    if grep -Fq "$expected_message" <<<"$output"; then
        pass "$name"
    else
        fail "${name}: expected message not found"
        printf '%s\n' "$output" >&2
    fi
}

run_validate_case() {
    local name="$1"
    local manifest="$2"
    local expected_message="$3"
    local script_path="${4:-}"

    local fixture
    fixture="$(mktemp -d)"

    create_fixture "$fixture"
    if [[ -n "$script_path" ]]; then
        create_script "$fixture" "$script_path"
    fi
    printf '%s
' "$manifest" >"$fixture/configs/bootstrap.json"

    local output
    local status

    set +e
    output="$(
        cd "$fixture" &&
            AISHA_INSTALLER_TEST_MODE=true                 ./install.sh --validate-manifest 2>&1
    )"
    status=$?
    set -e

    rm -rf "$fixture"

    if grep -Fq "$expected_message" <<<"$output"; then
        pass "$name"
        return
    fi

    if ((status == 0)); then
        fail "${name}: unexpectedly succeeded"
    else
        fail "$name: expected message not found"
    fi

    printf '%s
' "$output" >&2
}

test_missing_script_file() {
    local fixture
    fixture="$(mktemp -d)"

    create_fixture "$fixture"

    cat >"$fixture/configs/bootstrap.json" <<'JSON'
{
  "schema_version": 1,
  "steps": [
    {
      "id": "missing",
      "script": "scripts/bootstrap.d/missing.sh",
      "enabled": true,
      "description": "Missing script"
    }
  ]
}
JSON

    local output
    local status

    set +e
    output="$(
        cd "$fixture" &&
            AISHA_INSTALLER_TEST_MODE=true \
                ./install.sh --list 2>&1
    )"
    status=$?
    set -e

    rm -rf "$fixture"

    if ((status != 0)) &&
        grep -Fq \
            "Bootstrap step missing script does not exist" \
            <<<"$output"; then
        pass "missing script file"
    else
        fail "missing script file"
        printf '%s\n' "$output" >&2
    fi
}

test_empty_script() {
    local fixture
    fixture="$(mktemp -d)"

    create_fixture "$fixture"
    : >"$fixture/scripts/bootstrap.d/empty.sh"

    cat >"$fixture/configs/bootstrap.json" <<'JSON'
{
  "schema_version": 1,
  "steps": [
    {
      "id": "empty",
      "script": "scripts/bootstrap.d/empty.sh",
      "enabled": true,
      "description": "Empty script"
    }
  ]
}
JSON

    local output
    local status

    set +e
    output="$(
        cd "$fixture" &&
            AISHA_INSTALLER_TEST_MODE=true \
                ./install.sh --list 2>&1
    )"
    status=$?
    set -e

    rm -rf "$fixture"

    if ((status != 0)) &&
        grep -Fq \
            "Bootstrap step empty script is empty" \
            <<<"$output"; then
        pass "empty script"
    else
        fail "empty script"
        printf '%s\n' "$output" >&2
    fi
}


run_validate_case \
    "validate manifest succeeds" \
    '{"schema_version":1,"steps":[{"id":"system","script":"scripts/bootstrap.d/01-system.sh","enabled":true,"description":"Base operating system configuration"}]}' \
    "Manifest validation completed successfully." \
    "scripts/bootstrap.d/01-system.sh"

run_validate_case \
    "validate manifest invalid JSON" \
    '{invalid' \
    "Bootstrap manifest contains invalid JSON."

test_unknown_dependency() {
    local fixture
    local output
    local status

    fixture="$(mktemp -d)"
    create_fixture "$fixture"
    create_script "$fixture" "scripts/bootstrap.d/test.sh"

    cat >"$fixture/configs/bootstrap.json" <<'JSON'
{
  "schema_version": 1,
  "steps": [
    {
      "id": "test",
      "script": "scripts/bootstrap.d/test.sh",
      "description": "Test step",
      "depends_on": [
        "missing"
      ]
    }
  ]
}
JSON

    set +e
    output="$(
        cd "$fixture" &&
            AISHA_INSTALLER_TEST_MODE=true \
                ./install.sh --list 2>&1
    )"
    status=$?
    set -e

    rm -rf "$fixture"

    if ((status != 0)) &&
        grep -Fq \
            "Bootstrap step test depends on unknown step missing." \
            <<<"$output"; then
        pass "unknown dependency"
    else
        fail "unknown dependency"
        printf '%s\n' "$output" >&2
    fi
}

test_self_dependency() {
    local fixture
    local output
    local status

    fixture="$(mktemp -d)"
    create_fixture "$fixture"
    create_script "$fixture" "scripts/bootstrap.d/test.sh"

    cat >"$fixture/configs/bootstrap.json" <<'JSON'
{
  "schema_version": 1,
  "steps": [
    {
      "id": "test",
      "script": "scripts/bootstrap.d/test.sh",
      "description": "Test step",
      "depends_on": [
        "test"
      ]
    }
  ]
}
JSON

    set +e
    output="$(
        cd "$fixture" &&
            AISHA_INSTALLER_TEST_MODE=true \
                ./install.sh --list 2>&1
    )"
    status=$?
    set -e

    rm -rf "$fixture"

    if ((status != 0)) &&
        grep -Fq \
            "Bootstrap step test cannot depend on itself." \
            <<<"$output"; then
        pass "self dependency"
    else
        fail "self dependency"
        printf '%s\n' "$output" >&2
    fi
}

test_dependency_appears_later() {
    local fixture
    local output
    local status

    fixture="$(mktemp -d)"
    create_fixture "$fixture"
    create_script "$fixture" "scripts/bootstrap.d/first.sh"
    create_script "$fixture" "scripts/bootstrap.d/second.sh"

    cat >"$fixture/configs/bootstrap.json" <<'JSON'
{
  "schema_version": 1,
  "steps": [
    {
      "id": "first",
      "script": "scripts/bootstrap.d/first.sh",
      "description": "First step",
      "depends_on": [
        "second"
      ]
    },
    {
      "id": "second",
      "script": "scripts/bootstrap.d/second.sh",
      "description": "Second step"
    }
  ]
}
JSON

    set +e
    output="$(
        cd "$fixture" &&
            AISHA_INSTALLER_TEST_MODE=true \
                ./install.sh --list 2>&1
    )"
    status=$?
    set -e

    rm -rf "$fixture"

    if ((status != 0)) &&
        grep -Fq \
            "Bootstrap step first dependency second must appear earlier in the manifest." \
            <<<"$output"; then
        pass "dependency appears later"
    else
        fail "dependency appears later"
        printf '%s\n' "$output" >&2
    fi
}

test_duplicate_step_id() {
    local fixture
    local output
    local status

    fixture="$(mktemp -d)"
    create_fixture "$fixture"

    create_script \
        "$fixture" \
        "scripts/bootstrap.d/first.sh"

    create_script \
        "$fixture" \
        "scripts/bootstrap.d/second.sh"

    cat >"$fixture/configs/bootstrap.json" <<'JSON'
{
  "schema_version": 1,
  "steps": [
    {
      "id": "duplicate",
      "script": "scripts/bootstrap.d/first.sh",
      "description": "First duplicate step"
    },
    {
      "id": "duplicate",
      "script": "scripts/bootstrap.d/second.sh",
      "description": "Second duplicate step"
    }
  ]
}
JSON

    set +e
    output="$(
        cd "$fixture" &&
            AISHA_INSTALLER_TEST_MODE=true \
                ./install.sh --list 2>&1
    )"
    status=$?
    set -e

    rm -rf "$fixture"

    if ((status != 0)) &&
        grep -Fq \
            "Bootstrap manifest contains duplicate step ID: duplicate." \
            <<<"$output"; then
        pass "duplicate step ID"
    else
        fail "duplicate step ID"
        printf '%s\n' "$output" >&2
    fi
}

test_duplicate_script_path() {
    local fixture
    local output
    local status

    fixture="$(mktemp -d)"
    create_fixture "$fixture"

    create_script \
        "$fixture" \
        "scripts/bootstrap.d/shared.sh"

    cat >"$fixture/configs/bootstrap.json" <<'JSON'
{
  "schema_version": 1,
  "steps": [
    {
      "id": "first",
      "script": "scripts/bootstrap.d/shared.sh",
      "description": "First shared-script step"
    },
    {
      "id": "second",
      "script": "scripts/bootstrap.d/shared.sh",
      "description": "Second shared-script step"
    }
  ]
}
JSON

    set +e
    output="$(
        cd "$fixture" &&
            AISHA_INSTALLER_TEST_MODE=true \
                ./install.sh --list 2>&1
    )"
    status=$?
    set -e

    rm -rf "$fixture"

    if ((status != 0)) &&
        grep -Fq \
            "Bootstrap manifest contains duplicate script path: scripts/bootstrap.d/shared.sh." \
            <<<"$output"; then
        pass "duplicate script path"
    else
        fail "duplicate script path"
        printf '%s\n' "$output" >&2
    fi
}

test_valid_order() {
    local fixture
    fixture="$(mktemp -d)"

    create_fixture "$fixture"

    create_script "$fixture" "scripts/bootstrap.d/first.sh"
    create_script "$fixture" "scripts/bootstrap.d/second.sh"

    cat >"$fixture/configs/bootstrap.json" <<'JSON'
{
  "schema_version": 1,
  "steps": [
    {
      "id": "second",
      "script": "scripts/bootstrap.d/second.sh",
      "enabled": true,
      "description": "Second filesystem name, first manifest entry"
    },
    {
      "id": "first",
      "script": "scripts/bootstrap.d/first.sh",
      "enabled": true,
      "description": "First filesystem name, second manifest entry"
    }
  ]
}
JSON

    local output
    local status

    set +e
    output="$(
        cd "$fixture" &&
            AISHA_INSTALLER_TEST_MODE=true \
                ./install.sh --list 2>&1
    )"
    status=$?
    set -e

    rm -rf "$fixture"

    if ((status != 0)); then
        fail "valid ordered steps: installer failed"
        printf '%s\n' "$output" >&2
        return
    fi

    local second_line
    local first_line

    second_line="$(
        grep -nF 'scripts/bootstrap.d/second.sh' <<<"$output" |
            head -n 1 |
            cut -d: -f1
    )"

    first_line="$(
        grep -nF 'scripts/bootstrap.d/first.sh' <<<"$output" |
            head -n 1 |
            cut -d: -f1
    )"

    if [[ -n "$second_line" &&
        -n "$first_line" &&
        "$second_line" -lt "$first_line" ]]; then
        pass "valid ordered steps"
    else
        fail "valid ordered steps: manifest order was not preserved"
        printf '%s\n' "$output" >&2
    fi
}

run_failure_case \
    "invalid JSON" \
    '{invalid' \
    "Bootstrap manifest contains invalid JSON."

run_failure_case \
    "unsupported schema" \
    '{"schema_version":2,"steps":[]}' \
    "Unsupported bootstrap manifest schema: 2"

run_failure_case \
    "no enabled steps" \
    '{"schema_version":1,"steps":[{"id":"disabled","script":"disabled.sh","enabled":false}]}' \
    "Bootstrap manifest contains no enabled steps."

run_failure_case \
    "missing step ID" \
    '{"schema_version":1,"steps":[{"script":"scripts/bootstrap.d/test.sh","enabled":true}]}' \
    "Bootstrap manifest contains a step without an id."

run_failure_case \
    "missing script path" \
    '{"schema_version":1,"steps":[{"id":"test","enabled":true}]}' \
    "Bootstrap step test has no script path."

run_failure_case \
    "absolute script path" \
    '{"schema_version":1,"steps":[{"id":"absolute","script":"/tmp/test.sh","enabled":true,"description":"Absolute path test"}]}' \
    "Bootstrap step absolute must use a repository-relative script path."

run_failure_case \
    "missing description" \
    '{"schema_version":1,"steps":[{"id":"test","script":"scripts/bootstrap.d/test.sh","enabled":true}]}' \
    "Bootstrap step test has no description."


test_unknown_dependency
test_self_dependency
test_dependency_appears_later
test_missing_script_file
test_empty_script
test_valid_order
test_duplicate_step_id
test_duplicate_script_path

printf '\nPassed: %d\n' "$PASS_COUNT"
printf 'Failed: %d\n' "$FAIL_COUNT"

if ((FAIL_COUNT > 0)); then
    exit 1
fi

printf '\nBootstrap manifest tests passed.\n'
