"""Regression tests for regix command names in local task templates."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_quality_regix_uses_current_regix_gates_command() -> None:
    taskfile = (ROOT / "Taskfile.yml").read_text(encoding="utf-8")
    workflow_template = (ROOT / "templates/github-workflows/code-quality.yml.template").read_text(
        encoding="utf-8"
    )

    assert "regix gates" in taskfile
    assert "regix gate\n" not in taskfile
    assert "quality:regix:local:" in taskfile
    assert "regix compare HEAD --local" in taskfile
    assert "regix gates --fail-on error" in workflow_template
    assert "--fail-on-regression" not in workflow_template
