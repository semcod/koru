"""Probe whether a Python interpreter can use koru's screen capture path."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys

_PROBE_SCRIPT = """\
from koruvision.capture import capture_monitor_png

frame = capture_monitor_png(None)
if not frame.payload:
    raise SystemExit(2)
"""


def python_can_capture(executable: str, *, timeout: float = 20.0) -> bool:
    """Return True if *executable* can run koru's capture backend in this session."""
    try:
        proc = subprocess.run(  # noqa: S603 — probe only, no shell
            [executable, "-c", _PROBE_SCRIPT],
            capture_output=True,
            timeout=timeout,
            env=os.environ.copy(),
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return False
    return proc.returncode == 0


def resolve_observe_python() -> str:
    """Pick a Python that can capture; honors ``KORU_OBSERVE_PYTHON`` when set."""
    override = os.environ.get("KORU_OBSERVE_PYTHON", "").strip()
    if override:
        return override
    candidates: list[str] = [sys.executable]
    path_bin = shutil.which("python3")
    if path_bin:
        candidates.append(path_bin)
    seen: set[str] = set()
    for exe in candidates:
        if not exe or exe in seen:
            continue
        seen.add(exe)
        if python_can_capture(exe):
            return exe
    return sys.executable
