#!/usr/bin/env bash
# Build and run the koru capture smoke containers.
#
# Usage:
#   docker/capture/run.sh                 # all targets
#   docker/capture/run.sh headless        # just one target
#   docker/capture/run.sh x11 headless    # explicit list
#
# Each target produces one JSON line on stdout; the runner counts
# non-zero exits and prints a final summary.

set -euo pipefail

cd "$(dirname "$0")/../.."

targets=("$@")
if [[ ${#targets[@]} -eq 0 ]]; then
    targets=(headless x11)
fi

declare -A status

for target in "${targets[@]}"; do
    case "$target" in
        headless|x11) ;;
        *)
            echo "[run.sh] unknown target: $target (expected: headless|x11)" >&2
            exit 64
            ;;
    esac
    image="koru-capture-$target:smoke"
    echo "==> build $image"
    DOCKER_BUILDKIT=1 docker build \
        --target "capture-$target" \
        --tag "$image" \
        --file docker/capture/Dockerfile \
        . >&2

    echo "==> run $image"
    if output=$(docker run --rm "$image" 2>&1); then
        status["$target"]="ok"
    else
        status["$target"]="fail"
    fi
    echo "$output"
done

echo
echo "==> summary"
exit_code=0
for target in "${targets[@]}"; do
    result="${status[$target]}"
    echo "  $target: $result"
    if [[ "$result" != "ok" ]]; then
        exit_code=1
    fi
done
exit "$exit_code"
