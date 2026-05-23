"""Regression tests for WUP on-change gate task wiring."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_quality_wup_checks_status_and_respects_topology_gate() -> None:
    taskfile = (ROOT / "Taskfile.yml").read_text(encoding="utf-8")

    assert "quality:wup:" in taskfile
    assert "gate:wup" in taskfile
    assert "wup status" in taskfile
    assert "test -f wup.yaml" in taskfile


def test_operator_pipeline_taskfile_commands_exist() -> None:
    taskfile = (ROOT / "Taskfile.yml").read_text(encoding="utf-8")

    assert "koru:server:" in taskfile
    assert "koru:mcp:bootstrap:" in taskfile
    assert "{{.PYTHON}} -m koru.cli init-ide --project . --ide all" in taskfile
    assert "koru:operator:plugin-probe:" in taskfile
    assert "{{.PYTHON}} -m koru.cli autopilot manage --ide" in taskfile
    assert "koru:operator:setup-host:" in taskfile
    assert "koru:ide-os:calibrate:" in taskfile
    assert "test:docker:ide-matrix:" in taskfile
    assert "scripts/docker-ide-matrix.sh" in taskfile


def test_wup_yaml_is_bootstrapped_for_koru_project() -> None:
    wup_yaml = (ROOT / "wup.yaml").read_text(encoding="utf-8")

    assert 'name: koru' in wup_yaml
    assert "**" in wup_yaml
    assert "tests/**" in wup_yaml
    assert "debounce_s: 2" in wup_yaml
