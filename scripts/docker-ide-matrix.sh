#!/usr/bin/env bash
set -euo pipefail

ROOT="${KORU_REPO_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
DOCKER="${DOCKER:-docker}"
IMAGE_PREFIX="${KORU_DOCKER_MATRIX_IMAGE_PREFIX:-koru-ide-matrix}"
KEEP_IMAGES="${KORU_DOCKER_MATRIX_KEEP_IMAGES:-0}"

DEFAULT_SYSTEMS=(
    "debian-slim=python:3.12-slim-bookworm"
    "debian-bookworm=python:3.12-bookworm"
    "ubuntu-noble=ubuntu:24.04"
    "fedora=fedora:latest"
    "alpine=python:3.12-alpine"
)
DEFAULT_IDES=("vscode" "vscodium" "cursor" "windsurf" "jetbrains" "zed")

split_words() {
    local raw="$1"
    raw="${raw//,/ }"
    # shellcheck disable=SC2086
    printf '%s\n' ${raw}
}

system_spec_for() {
    local raw="$1"
    if [[ "${raw}" == *"="* ]]; then
        printf '%s\n' "${raw}"
        return 0
    fi
    case "${raw}" in
        debian-slim) printf '%s\n' "debian-slim=python:3.12-slim-bookworm" ;;
        debian|debian-bookworm) printf '%s\n' "debian-bookworm=python:3.12-bookworm" ;;
        ubuntu|ubuntu-noble) printf '%s\n' "ubuntu-noble=ubuntu:24.04" ;;
        fedora) printf '%s\n' "fedora=fedora:latest" ;;
        alpine) printf '%s\n' "alpine=python:3.12-alpine" ;;
        *:*) printf '%s\n' "custom-${raw//[^A-Za-z0-9_.-]/-}=${raw}" ;;
        *)
            echo "unknown KORU_DOCKER_SYSTEMS item: ${raw}" >&2
            echo "use one of: debian-slim debian-bookworm ubuntu-noble fedora alpine, or id=image" >&2
            return 2
            ;;
    esac
}

if [[ -n "${KORU_DOCKER_SYSTEMS:-}" ]]; then
    mapfile -t requested_systems < <(split_words "${KORU_DOCKER_SYSTEMS}")
    system_specs=()
    for item in "${requested_systems[@]}"; do
        [[ -n "${item}" ]] || continue
        system_specs+=("$(system_spec_for "${item}")")
    done
else
    system_specs=("${DEFAULT_SYSTEMS[@]}")
fi

if [[ -n "${KORU_DOCKER_IDES:-}" ]]; then
    mapfile -t ides < <(split_words "${KORU_DOCKER_IDES}")
else
    ides=("${DEFAULT_IDES[@]}")
fi

if [[ "${#system_specs[@]}" -eq 0 || "${#ides[@]}" -eq 0 ]]; then
    echo "empty Docker IDE matrix" >&2
    exit 2
fi

for spec in "${system_specs[@]}"; do
    system_id="${spec%%=*}"
    base_image="${spec#*=}"
    tag="${IMAGE_PREFIX}:${system_id}"
    echo "==> build ${tag} from ${base_image}"
    "${DOCKER}" build \
        --file "${ROOT}/tests/docker/ide-matrix.Dockerfile" \
        --build-arg "BASE_IMAGE=${base_image}" \
        --build-arg "SYSTEM_ID=${system_id}" \
        --tag "${tag}" \
        "${ROOT}"

    for ide in "${ides[@]}"; do
        [[ -n "${ide}" ]] || continue
        echo "==> run ${system_id}/${ide}"
        "${DOCKER}" run --rm \
            --env "KORU_MATRIX_SYSTEM=${system_id}" \
            --env "KORU_MATRIX_IDE=${ide}" \
            "${tag}"
    done

    if [[ "${KEEP_IMAGES}" != "1" ]]; then
        "${DOCKER}" image rm "${tag}" >/dev/null 2>&1 || true
    fi
done
