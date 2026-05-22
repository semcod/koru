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
export KORU_FAKE_EXTENSION_VERSION="${KORU_FAKE_EXTENSION_VERSION:-0.1.28}"
export TERM_PROGRAM="${TERM_PROGRAM:-vscode}"
export XDG_RUNTIME_DIR="${XDG_RUNTIME_DIR:-/tmp/koru-runtime}"
mkdir -p "${XDG_RUNTIME_DIR}"

echo "koru docker ide matrix: system=${system_id} ide=${ide}"

python -m pytest tests/test_docker_ide_matrix.py -q

python -m koru.cli autopilot drive \
    --direct \
    --dry-run \
    --no-submit \
    --ide "${ide}" \
    --prompt "koru docker matrix smoke: ${system_id}/${ide}" \
    >/tmp/koru-drive-smoke.json

python - <<'PY'
from __future__ import annotations

import json
import os
from pathlib import Path

from koruide.socket import default_socket_path

ide = os.environ["KORU_MATRIX_IDE"]
system = os.environ.get("KORU_MATRIX_SYSTEM", "unknown")
payload = json.loads(Path("/tmp/koru-drive-smoke.json").read_text(encoding="utf-8"))
assert payload["dry_run"] is True, payload
assert payload["submitted"] is False, payload
assert payload["backend"] in {"wtype", "ydotool", "xdotool", "profile"}, payload
assert default_socket_path().name == f"koru-autopilot-{ide}.sock"
if ide == "vscodium":
    assert os.environ.get("TERM_PROGRAM") == "vscode"
    assert os.environ.get("KORU_AUTOPILOT_INSTANCE") == "vscodium"
    assert default_socket_path().name == "koru-autopilot-vscodium.sock"
print(f"koru docker drive smoke verified: system={system} ide={ide}")
PY

if [[ "${ide}" == "vscode" || "${ide}" == "vscodium" || "${ide}" == "cursor" || "${ide}" == "windsurf" || "${ide}" == "jetbrains" ]]; then
    python -m koru.cli autopilot manage --ide "${ide}" --format json >/tmp/koru-manage-smoke.json
    python - <<'PY'
from __future__ import annotations

import json
import os
from pathlib import Path

from koruide.plugin_version import EXPECTED_VSCODE_PLUGIN_VERSION

payload = json.loads(Path("/tmp/koru-manage-smoke.json").read_text(encoding="utf-8"))
ide = os.environ["KORU_MATRIX_IDE"]
plugin = payload.get("plugin") or {}
assert plugin.get("ide") == ide, payload
assert plugin.get("installed_version") == EXPECTED_VSCODE_PLUGIN_VERSION, payload
assert payload.get("ok") is True, payload
print(f"koru docker plugin manager verified: ide={ide} version={EXPECTED_VSCODE_PLUGIN_VERSION}")
PY
fi

echo "koru docker ide matrix: ok system=${system_id} ide=${ide}"
