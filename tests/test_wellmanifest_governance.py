"""Regression tests for the wellmanifest_governance pytest bridge.

``pytest --collect-only`` is a read-only inventory probe (koru scan /
doctor suite-health checks, IDE test discovery). The bridge must not run
the governance-gate subprocess there, while every session that can execute
tests keeps full enforcement (STARTER-675 / ticket-154).
"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from wellmanifest_governance import GovernanceGateError, pytest_sessionstart

FAKE_SHA = "a" * 40


def _session(tmp_path: Path, *, collectonly: bool) -> SimpleNamespace:
    return SimpleNamespace(
        config=SimpleNamespace(
            option=SimpleNamespace(collectonly=collectonly),
            rootpath=tmp_path,
        )
    )


def _install_fake_gate(project: Path) -> Path:
    gate = project / "project" / "governance-check.sh"
    gate.parent.mkdir(parents=True, exist_ok=True)
    gate.write_text(
        '#!/bin/sh\ntouch "$GOVERNANCE_GATE_MARKER"\nexit 0\n',
        encoding="utf-8",
    )
    gate.chmod(0o755)
    return gate


@pytest.fixture
def gate_project(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Project dir with a marker-writing fake gate and stubbed base resolution."""
    project = tmp_path / "repo"
    project.mkdir()
    _install_fake_gate(project)
    monkeypatch.setattr("wellmanifest_governance._resolve_base", lambda root: FAKE_SHA)
    monkeypatch.setattr("wellmanifest_governance._changed_paths", lambda root, base: ["src/demo.py"])
    return project


def test_collect_only_skips_gate_even_when_gate_is_missing(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """A collect-only probe must not fail because no gate script exists."""

    def _no_subprocess(*_args: object, **_kwargs: object) -> None:
        pytest.fail("collect-only session start must not spawn any subprocess")

    monkeypatch.setattr("wellmanifest_governance.subprocess.run", _no_subprocess)
    result = pytest_sessionstart(_session(tmp_path, collectonly=True))
    assert result is None


def test_collect_only_does_not_execute_gate_script(gate_project: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    marker = gate_project / "gate-ran"
    monkeypatch.setenv("GOVERNANCE_GATE_MARKER", str(marker))
    pytest_sessionstart(_session(gate_project, collectonly=True))
    assert not marker.exists()


def test_real_session_runs_gate_once(gate_project: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    marker = gate_project / "gate-ran"
    monkeypatch.setenv("GOVERNANCE_GATE_MARKER", str(marker))
    monkeypatch.delenv("WELLMANIFEST_GOVERNANCE_ACTIVE", raising=False)
    pytest_sessionstart(_session(gate_project, collectonly=False))
    assert marker.exists()


def test_real_session_gate_failure_raises_governance_error(gate_project: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    gate = gate_project / "project" / "governance-check.sh"
    gate.write_text("#!/bin/sh\nexit 1\n", encoding="utf-8")
    monkeypatch.delenv("WELLMANIFEST_GOVERNANCE_ACTIVE", raising=False)
    with pytest.raises(GovernanceGateError, match="exit code 1"):
        pytest_sessionstart(_session(gate_project, collectonly=False))


def test_recursive_invocation_guard(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _install_fake_gate(tmp_path)
    monkeypatch.setenv("WELLMANIFEST_GOVERNANCE_ACTIVE", "1")
    with pytest.raises(GovernanceGateError, match="recursive"):
        pytest_sessionstart(_session(tmp_path, collectonly=False))


def test_missing_gate_fails_for_real_sessions(tmp_path: Path) -> None:
    assert not (tmp_path / "project" / "governance-check.sh").exists()
    with pytest.raises(GovernanceGateError, match="missing"):
        pytest_sessionstart(_session(tmp_path, collectonly=False))
