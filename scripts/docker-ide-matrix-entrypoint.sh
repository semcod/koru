#!/usr/bin/env bash
set -euo pipefail

ide="${KORU_MATRIX_IDE:?KORU_MATRIX_IDE is required}"
system_id="${KORU_MATRIX_SYSTEM:-unknown}"

export KORU_AUTOPILOT_IDE="${ide}"
export KORU_AUTOPILOT_INSTANCE="${ide}"
export KORU_HEADLESS=1
export KORU_HEADLESS_ALLOW_AUTOPILOT=1
export KORU_INJECTOR_BACKEND="${KORU_INJECTOR_BACKEND:-wtype}"
export KORU_AUTOPILOT_ALLOW_KEYBOARD_FALLBACK=1
export KORU_FAKE_EXTENSION_VERSION="${KORU_FAKE_EXTENSION_VERSION:-0.1.15}"

echo "koru docker ide matrix: system=${system_id} ide=${ide}"

python -m pytest tests/test_docker_ide_matrix.py -q

python -m koru.cli autopilot drive \
    --direct \
    --dry-run \
    --no-submit \
    --ide "${ide}" \
    --prompt "koru docker matrix smoke: ${system_id}/${ide}" \
    >/tmp/koru-drive-smoke.json

if [[ "${ide}" == "vscode" || "${ide}" == "vscodium" || "${ide}" == "cursor" || "${ide}" == "windsurf" || "${ide}" == "jetbrains" ]]; then
    python -m koru.cli autopilot manage --ide "${ide}" --format json >/tmp/koru-manage-smoke.json
fi

echo "koru docker ide matrix: ok system=${system_id} ide=${ide}"
