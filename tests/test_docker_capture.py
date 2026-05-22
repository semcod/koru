"""Cross-OS capture smoke tests via docker/capture/*.

The tests build minimal Linux containers and exercise the
:mod:`koruvision.providers` stack end-to-end. They are skipped when
docker is not available (CI without docker-in-docker, or developer
laptops without docker installed).

These tests intentionally stay close to the smoke entry-point that
``docker/capture/smoke.py`` runs so a failure points at the same JSON
payload regardless of whether you reproduce inside docker or via
pytest. Build times dominate the runtime (~10 s headless, ~70 s X11
with cold cache), so the suite is gated behind the ``KORU_DOCKER_TESTS``
environment variable in addition to docker availability.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]
DOCKERFILE = REPO_ROOT / "docker" / "capture" / "Dockerfile"
RUN_TESTS = os.environ.get("KORU_DOCKER_TESTS", "").strip().lower() in {"1", "true", "yes", "on"}


def _docker_available() -> bool:
    if not shutil.which("docker"):
        return False
    try:
        proc = subprocess.run(  # noqa: S603,S607
            ["docker", "info", "--format", "{{.ServerVersion}}"],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return False
    return proc.returncode == 0


pytestmark = [
    pytest.mark.skipif(not RUN_TESTS, reason="set KORU_DOCKER_TESTS=1 to run docker capture tests"),
    pytest.mark.skipif(not DOCKERFILE.is_file(), reason="docker/capture/Dockerfile missing"),
    pytest.mark.skipif(not _docker_available(), reason="docker is not available"),
]


def _build(target: str) -> str:
    image = f"koru-capture-{target}:pytest"
    subprocess.run(  # noqa: S603,S607
        [
            "docker",
            "build",
            "--target",
            f"capture-{target}",
            "--tag",
            image,
            "--file",
            str(DOCKERFILE),
            str(REPO_ROOT),
        ],
        check=True,
        timeout=600,
    )
    return image


def _run(image: str) -> tuple[int, dict, str]:
    proc = subprocess.run(  # noqa: S603,S607
        ["docker", "run", "--rm", image],
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    stdout = (proc.stdout or "").strip()
    parsed: dict = {}
    last_json = ""
    for line in reversed(stdout.splitlines()):
        if line.startswith("{"):
            last_json = line
            break
    if last_json:
        try:
            parsed = json.loads(last_json)
        except json.JSONDecodeError:
            parsed = {}
    return proc.returncode, parsed, (proc.stderr or "")


def test_docker_capture_headless() -> None:
    image = _build("headless")
    rc, payload, stderr = _run(image)
    assert rc == 0, f"smoke exit={rc}; stderr={stderr[-500:]}"
    assert payload.get("mode") == "headless"
    assert payload.get("expectation_ok") is True
    providers = payload.get("providers", {}).get("providers", [])
    assert providers, "providers payload missing"
    assert all(not p["available"] for p in providers if p["name"] != "cli_tools"), \
        "headless container reported a non-cli_tools provider as available"
    capture = payload.get("capture") or {}
    assert capture.get("ok") is False, "headless container unexpectedly captured a frame"


def test_docker_capture_x11() -> None:
    image = _build("x11")
    rc, payload, stderr = _run(image)
    assert rc == 0, f"smoke exit={rc}; stderr={stderr[-500:]}"
    assert payload.get("mode") == "x11"
    assert payload.get("expectation_ok") is True
    capture = payload.get("capture") or {}
    assert capture.get("ok") is True
    assert capture.get("payload_bytes", 0) > 100
    assert capture.get("png_width", 0) > 0
    assert capture.get("png_height", 0) > 0
    capture_all = payload.get("capture_all") or {}
    assert capture_all.get("count", 0) >= 1
    diagnostics = payload.get("diagnostics") or {}
    assert diagnostics.get("session_type") == "x11"
    provider_rows = {p["name"]: p for p in diagnostics.get("providers", [])}
    assert provider_rows.get("mss", {}).get("available") is True, \
        "mss should be reported as available in the X11 container"
    assert provider_rows.get("cli_tools", {}).get("available") is True, \
        "cli_tools (scrot) should be reported as available in the X11 container"
