"""Tests for koru.autonomy.code2llm_discovery."""

from __future__ import annotations

import subprocess
from collections.abc import Sequence
from pathlib import Path

import pytest
import yaml

from koru.autonomy import code2llm_discovery as cd


def _make_runner(
    *,
    written_yaml: dict | None = None,
    returncode: int = 0,
    stderr: str = "",
):
    """Build a fake runner that writes planfile-tickets.yaml and returns rc."""
    def runner(cmd: Sequence[str], cwd: Path) -> subprocess.CompletedProcess[str]:
        if written_yaml is not None:
            out_index = list(cmd).index("-o")
            output_dir = Path(list(cmd)[out_index + 1])
            output_dir.mkdir(parents=True, exist_ok=True)
            (output_dir / "analysis.toon.yaml").write_text("OK\n", encoding="utf-8")
            (output_dir / "planfile-tickets.yaml").write_text(
                yaml.safe_dump(written_yaml), encoding="utf-8",
            )
        return subprocess.CompletedProcess(list(cmd), returncode, stdout="", stderr=stderr)

    return runner


def test_skipped_when_binary_missing(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(cd, "_code2llm_executable", lambda: None)
    outcome = cd.run_code2llm_discovery(tmp_path, runner=_make_runner())
    assert outcome.ran is False
    assert outcome.skipped_reason == "code2llm not on PATH"


def test_runs_and_parses_applied(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(cd, "_code2llm_executable", lambda: "/usr/bin/code2llm")
    runner = _make_runner(
        written_yaml={
            "schema": "code2llm.planfile_tickets.v1",
            "applied": ["Split god module: src/a.py", "Reduce cyclomatic complexity: foo"],
            "skipped": ["Already exists: bar"],
        },
    )
    outcome = cd.run_code2llm_discovery(tmp_path, runner=runner, force=True)
    assert outcome.ran is True
    assert outcome.code2llm_returncode == 0
    assert outcome.applied_titles == [
        "Split god module: src/a.py",
        "Reduce cyclomatic complexity: foo",
    ]
    assert outcome.skipped_titles == ["Already exists: bar"]
    assert outcome.error is None


def test_runner_failure_records_error(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(cd, "_code2llm_executable", lambda: "/usr/bin/code2llm")
    runner = _make_runner(returncode=2, stderr="boom\n")
    outcome = cd.run_code2llm_discovery(tmp_path, runner=runner, force=True)
    assert outcome.ran is True
    assert outcome.code2llm_returncode == 2
    assert outcome.error and "boom" in outcome.error


def test_fresh_artifacts_skip_run(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(cd, "_code2llm_executable", lambda: "/usr/bin/code2llm")
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    (project_dir / "analysis.toon.yaml").write_text("OK\n", encoding="utf-8")
    (project_dir / "planfile-tickets.yaml").write_text(
        yaml.safe_dump({"applied": ["X"], "skipped": []}), encoding="utf-8",
    )
    runner_calls: list[Sequence[str]] = []

    def runner(cmd, _cwd):
        runner_calls.append(cmd)
        return subprocess.CompletedProcess(list(cmd), 0)

    outcome = cd.run_code2llm_discovery(tmp_path, runner=runner, stale_minutes=999)
    assert runner_calls == []
    assert outcome.ran is False
    assert outcome.applied_titles == ["X"]
    assert outcome.skipped_reason and "artifacts younger" in outcome.skipped_reason


def test_format_summary_for_skip_and_success() -> None:
    skipped = cd.DiscoveryOutcome(skipped_reason="no binary")
    assert "skipped" in cd.format_discovery_summary(skipped)
    success = cd.DiscoveryOutcome(
        ran=True,
        code2llm_returncode=0,
        code2llm_duration_s=2.5,
        applied_titles=["a", "b"],
        skipped_titles=["c"],
        artifacts_dir="/tmp/p",
    )
    text = cd.format_discovery_summary(success)
    assert "applied=2" in text
    assert "skipped=1" in text
