#!/usr/bin/env bash
set -euo pipefail

ROOT="${KORU_REPO_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
DOCKER="${DOCKER:-docker}"
IMAGE_PREFIX="${KORU_DOCKER_MATRIX_IMAGE_PREFIX:-koru-ide-matrix}"
KEEP_IMAGES="${KORU_DOCKER_MATRIX_KEEP_IMAGES:-0}"

DEFAULT_SYSTEMS=(
    "debian-slim=python:3.12.14-slim-bookworm@sha256:782412e85d0f0984994c290652577d4018aff08145c85b262bb63dc0c7522254"
    "debian-bookworm=python:3.12.14-bookworm@sha256:581429e3df12d76e6af4be5ab7d0e7fc2013eb57dc23d2de691411c8efdbb970"
    "ubuntu-noble=ubuntu:24.04@sha256:33ceb71981b602c1a7443a53469e4dba065f7503eab3078a2d7a57a2ab987517"
    "fedora=fedora:44@sha256:43b29f65a41eb9c35e1cd5323e3bdf3b655c2357a9f4f1ff2f9c2798e5045d80"
    "alpine=python:3.12.14-alpine3.24@sha256:1887c114801a8c82a4ec01daa52cfe7fc3f63573640e2247320289807ac1c3bb"
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
        debian-slim) printf '%s\n' "${DEFAULT_SYSTEMS[0]}" ;;
        debian|debian-bookworm) printf '%s\n' "${DEFAULT_SYSTEMS[1]}" ;;
        ubuntu|ubuntu-noble) printf '%s\n' "${DEFAULT_SYSTEMS[2]}" ;;
        fedora) printf '%s\n' "${DEFAULT_SYSTEMS[3]}" ;;
        alpine) printf '%s\n' "${DEFAULT_SYSTEMS[4]}" ;;
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
    if [[ ! "${base_image}" =~ @sha256:[0-9a-f]{64}$ ]]; then
        echo "mutable Docker base rejected for ${system_id}: ${base_image}" >&2
        echo "supply an image reference ending in @sha256:<64 lowercase hex characters>" >&2
        exit 2
    fi
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
