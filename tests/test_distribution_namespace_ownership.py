"""Distribution checks for dependency namespaces that Koru does not own."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
FOREIGN_NAMESPACES = ("env2llm", "imgl", "nlp2imgl")
REMOVED_RUNTIME_MODULES = (
    "koruvision/scaling.py",
    "koruvision/capture_mss.py",
    "koruvision/portal_capture.py",
    "koruvision/providers/cli_tools.py",
    "koruvision/providers/grim.py",
    "koruvision/providers/mss.py",
    "koruvision/providers/portal_screencast.py",
    "koruvision/providers/portal_screenshot.py",
    "koruvision/providers/screencast_session.py",
)


def test_foreign_dependency_namespaces_are_absent_from_runtime_source() -> None:
    for namespace in FOREIGN_NAMESPACES:
        assert not (ROOT / "src" / namespace).exists()
        assert (ROOT / "tests" / "fakes" / namespace).is_dir()


def test_isolated_import_discovery_never_resolves_koru_runtime_shadows(tmp_path: Path) -> None:
    script = """
import importlib.util
import json
import pathlib
import sys

root = pathlib.Path(sys.argv[1]).resolve()
resolved = {}
for name in ("env2llm", "imgl", "nlp2imgl"):
    spec = importlib.util.find_spec(name)
    resolved[name] = None if spec is None else str(pathlib.Path(spec.origin or "").resolve())
print(json.dumps(resolved, sort_keys=True))
"""
    proc = subprocess.run(
        [sys.executable, "-I", "-c", script, str(ROOT)],
        cwd=tmp_path,
        check=True,
        capture_output=True,
        text=True,
    )
    resolved = json.loads(proc.stdout)
    runtime_src = (ROOT / "src").resolve()
    for origin in resolved.values():
        if origin is not None:
            assert not Path(origin).is_relative_to(runtime_src)


def test_built_wheel_contains_no_foreign_dependency_namespace(tmp_path: Path) -> None:
    uv = shutil.which("uv")
    if uv is None:
        pytest.skip("uv is required for the wheel ownership smoke test")

    subprocess.run(
        [uv, "build", "--wheel", "--out-dir", str(tmp_path)],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    wheels = list(tmp_path.glob("*.whl"))
    assert len(wheels) == 1
    with zipfile.ZipFile(wheels[0]) as archive:
        members = archive.namelist()
    for namespace in FOREIGN_NAMESPACES:
        assert not any(member == namespace or member.startswith(f"{namespace}/") for member in members)
    for module in REMOVED_RUNTIME_MODULES:
        assert module not in members, f"stale build artifact leaked into wheel: {module}"
