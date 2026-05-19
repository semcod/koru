from __future__ import annotations

import importlib.util
from pathlib import Path

SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "koru-gate-capture.py"
_SPEC = importlib.util.spec_from_file_location("koru_gate_capture", SCRIPT_PATH)
assert _SPEC and _SPEC.loader
koru_gate_capture = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(koru_gate_capture)


def test_first_meaningful_line_skips_cloud_init_noise() -> None:
    text = "\n".join(
        [
            "**************************************************************************",
            "# A new feature in cloud-init identified possible datasources for        #",
            "Disable the warnings above by:",
            "REAL_FAILURE_LINE",
        ],
    )
    assert koru_gate_capture._first_meaningful_line(text) == "REAL_FAILURE_LINE"


def test_first_meaningful_line_falls_back_to_nonempty_when_only_noise() -> None:
    text = "\n".join(
        [
            "",
            "********",
            "Disable the warnings above by:",
        ],
    )
    assert koru_gate_capture._first_meaningful_line(text) == "********"
