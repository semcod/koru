#!/usr/bin/env bash
# Cross-distribution terminal rendering verification test harness for Koru CLI.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

DISTROS=("alpine" "ubuntu" "fedora")
if [[ $# -gt 0 ]]; then
    DISTROS=("$@")
fi

echo "=== Koru Cross-Distribution Terminal Rendering Verification ==="
echo "Target distributions: ${DISTROS[*]}"
echo "Repository root: $REPO_ROOT"
echo ""

TOTAL_TESTS=0
PASSED_TESTS=0
FAILED_TESTS=0

run_check() {
    local desc="$1"
    local cmd="$2"
    local check_type="$3"
    local pattern="$4"

    TOTAL_TESTS=$((TOTAL_TESTS + 1))
    printf "  [TEST] %-55s ... " "$desc"

    local output
    if ! output=$(eval "$cmd" 2>&1); then
        echo "FAIL (command error)"
        echo "    Command: $cmd"
        echo "    Output: $output"
        FAILED_TESTS=$((FAILED_TESTS + 1))
        return 1
    fi

    case "$check_type" in
        contains)
            if echo "$output" | grep -q "$pattern"; then
                echo "PASS"
                PASSED_TESTS=$((PASSED_TESTS + 1))
                return 0
            else
                echo "FAIL (pattern '$pattern' not found)"
                FAILED_TESTS=$((FAILED_TESTS + 1))
                return 1
            fi
            ;;
        not_contains)
            if ! echo "$output" | grep -q "$pattern"; then
                echo "PASS"
                PASSED_TESTS=$((PASSED_TESTS + 1))
                return 0
            else
                echo "FAIL (unexpected pattern '$pattern' found)"
                FAILED_TESTS=$((FAILED_TESTS + 1))
                return 1
            fi
            ;;
        valid_json)
            if echo "$output" | python3 -m json.tool >/dev/null 2>&1; then
                echo "PASS"
                PASSED_TESTS=$((PASSED_TESTS + 1))
                return 0
            else
                echo "FAIL (invalid JSON)"
                FAILED_TESTS=$((FAILED_TESTS + 1))
                return 1
            fi
            ;;
        *)
            echo "FAIL (unknown check type)"
            FAILED_TESTS=$((FAILED_TESTS + 1))
            return 1
            ;;
    esac
}

for distro in "${DISTROS[@]}"; do
    echo "------------------------------------------------------------"
    echo ">> Testing Environment: $distro"
    echo "------------------------------------------------------------"

    dockerfile="$SCRIPT_DIR/Dockerfile.$distro"
    image_tag="koru-test:$distro"

    if [[ ! -f "$dockerfile" ]]; then
        echo "Error: Dockerfile $dockerfile not found. Skipping."
        continue
    fi

    echo "Building container image '$image_tag'..."
    docker build -q -t "$image_tag" -f "$dockerfile" "$REPO_ROOT" >/dev/null

    echo "Running terminal verification matrix..."

    # 1. Interactive TTY: Markdown headers (#, ##) must NOT appear raw
    run_check "[$distro] Interactive TTY formats headers (no raw '# ')" \
        "docker run --rm -t -e TERM=xterm-256color $image_tag python3 -m koru.cli_summary --no-github" \
        not_contains "^# "

    # 2. Interactive TTY: Markdown bold (**text**) must NOT appear raw
    run_check "[$distro] Interactive TTY formats bold (no raw '**')" \
        "docker run --rm -t -e TERM=xterm-256color $image_tag python3 -m koru.cli_summary --no-github" \
        not_contains "\*\*"

    # 3. Non-TTY / Pipe: raw markdown must be preserved for composability
    run_check "[$distro] Pipe/Redirect preserves Markdown header '# '" \
        "docker run --rm $image_tag python3 -m koru.cli_summary --no-github | cat" \
        contains "^# "

    # 4. Explicit --raw flag: outputs pure markdown even when TTY is allocated
    run_check "[$distro] Explicit --raw preserves Markdown header '# '" \
        "docker run --rm -t $image_tag python3 -m koru.cli_summary --raw --no-github" \
        contains "^# "

    # 5. Explicit --plain flag: strips markdown symbols and ANSI escapes
    run_check "[$distro] Explicit --plain removes markdown headers" \
        "docker run --rm -t $image_tag python3 -m koru.cli_summary --plain --no-github" \
        not_contains "^# "

    # 6. Structured JSON output (--json)
    run_check "[$distro] --json produces valid JSON" \
        "docker run --rm $image_tag python3 -m koru.cli_summary --json --no-github" \
        valid_json ""

    # 7. TERM=dumb handling
    run_check "[$distro] TERM=dumb executes cleanly" \
        "docker run --rm -e TERM=dumb $image_tag python3 -m koru.cli_summary --no-github" \
        contains "Daily Execution Summary"

    # 8. NO_COLOR=1 handling
    run_check "[$distro] NO_COLOR=1 executes cleanly" \
        "docker run --rm -t -e NO_COLOR=1 $image_tag python3 -m koru.cli_summary --no-github" \
        not_contains "\*\*"

    echo ""
done

echo "============================================================"
echo "Verification Summary:"
echo "  Total:  $TOTAL_TESTS"
echo "  Passed: $PASSED_TESTS"
echo "  Failed: $FAILED_TESTS"
echo "============================================================"

if [[ $FAILED_TESTS -gt 0 ]]; then
    exit 1
fi
exit 0
