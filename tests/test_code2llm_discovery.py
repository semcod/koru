"""Tests for koru.autonomy.code2llm_discovery."""

from __future__ import annotations

import os
import subprocess
import time
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


def test_default_excludes_skip_plugins_folder() -> None:
    """The ``plugins/`` folder must be excluded from code2llm dup analysis.

    The five ``plugins/koru-autopilot-<ide>/`` plugins each carry their
    own copy of ``AutopilotBridge`` by design — that is the whole point
    of the per-IDE VSIX split (regression isolation). Without this
    exclusion code2llm flags 10 duplicated classes on every discovery
    cycle and re-creates a planfile ticket (STARTER-276) that, if
    "fixed", would re-collapse the plugins and undo the architectural
    split. code2llm's ``--exclude`` matches by directory name, so the
    literal ``plugins`` is what works.
    """
    excludes = cd.DEFAULT_EXCLUDES
    assert "*.md" in excludes
    assert "plugins" in excludes


def test_build_cmd_uses_scoped_source_when_provided(tmp_path: Path) -> None:
    scoped = tmp_path / "src" / "target.py"
    scoped.parent.mkdir(parents=True)
    scoped.write_text("pass\n", encoding="utf-8")
    cmd = cd._build_code2llm_cmd(
        "/usr/bin/code2llm",
        project=tmp_path,
        source=scoped,
        output_dir=tmp_path / "project",
        formats="toon",
        excludes=cd.DEFAULT_EXCLUDES,
        apply_planfile=False,
        planfile_source="koru-test",
        planfile_sprint="current",
        planfile_limit=None,
    )
    assert cmd[1] == str(scoped)


def test_scoped_discovery_skips_fresh_whole_project_artifacts(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(cd, "_code2llm_executable", lambda: "/usr/bin/code2llm")
    analysis = tmp_path / "project" / "analysis.toon.yaml"
    analysis.parent.mkdir(parents=True)
    analysis.write_text("fresh\n", encoding="utf-8")
    scoped = tmp_path / "src" / "mod.py"
    scoped.parent.mkdir(parents=True)
    scoped.write_text("x = 1\n", encoding="utf-8")
    calls: list[list[str]] = []

    def runner(cmd: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
        calls.append(list(cmd))
        return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

    outcome = cd.run_code2llm_discovery(
        tmp_path,
        runner=runner,
        scope_paths=("src/mod.py",),
    )
    assert outcome.ran is True
    assert calls and calls[0][1] == str(scoped.resolve())


def test_build_cmd_passes_excludes_to_code2llm(tmp_path: Path) -> None:
    """``_build_code2llm_cmd`` must forward every exclude pattern via ``--exclude``."""
    cmd = cd._build_code2llm_cmd(
        "/usr/bin/code2llm",
        project=tmp_path,
        output_dir=tmp_path / "project",
        formats="toon",
        excludes=cd.DEFAULT_EXCLUDES,
        apply_planfile=False,
        planfile_source="koru-test",
        planfile_sprint="current",
        planfile_limit=None,
    )
    # Each pattern should appear immediately after a ``--exclude`` flag.
    for pattern in cd.DEFAULT_EXCLUDES:
        positions = [i for i, tok in enumerate(cmd) if tok == "--exclude"]
        assert any(cmd[i + 1] == pattern for i in positions), (
            f"exclude pattern {pattern!r} missing from {cmd!r}"
        )
    # ``plugins`` must be excluded so the per-IDE VSIX split is preserved.
    assert "plugins" in cmd


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


def test_applies_planfile_tickets_with_dedupe_key(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(cd, "_code2llm_executable", lambda: "/usr/bin/code2llm")
    ticket_yaml = {
        "schema": "code2llm.planfile_tickets.v1",
        "source": "koru-project-discovery",
        "tickets": [
            {
                "signal": "code2llm_smell_god_function",
                "title": "Address code smell: God Function: build_parser",
                "description": "Refactor build_parser",
                "priority": "high",
                "labels": ["llm-ready", "code2llm"],
                "files": ["src/koru/autonomous_parser.py"],
                "dedupe_key": (
                    "code2llm:smell:god_function:"
                    "src/koru/autonomous_parser.py:8:God Function: build_parser"
                ),
            }
        ],
    }
    runner = _make_runner(written_yaml=ticket_yaml)

    first = cd.run_code2llm_discovery(tmp_path, runner=runner, force=True)
    second = cd.run_code2llm_discovery(tmp_path, runner=runner, force=True)

    assert first.applied_titles == ["Address code smell: God Function: build_parser"]
    assert first.skipped_titles == []
    assert second.applied_titles == []
    assert second.skipped_titles == ["Address code smell: God Function: build_parser"]

    sprint = yaml.safe_load(
        (tmp_path / ".planfile" / "sprints" / "current.yaml").read_text(encoding="utf-8"),
    )
    tickets = sprint["sprint"]["tickets"]
    assert len(tickets) == 1
    ticket = next(iter(tickets.values()))
    assert ticket["source"]["tool"] == "koru-project-discovery"
    assert ticket["source"]["context"]["dedupe_key"].startswith("code2llm:smell:")
    evidence = ticket["source"]["context"]["evidence"]
    assert evidence["schema"] == "koru.ticket_evidence.v1"
    assert evidence["kind"] == "code2llm_discovery"
    assert evidence["artifact"]["path"] == "project/analysis.toon.yaml"
    assert evidence["artifact"]["size_bytes"] > 0
    assert len(evidence["artifact"]["sha256"]) == 64
    assert evidence["planfile_tickets"]["path"] == "project/planfile-tickets.yaml"
    assert "code2llm" in evidence["regenerate_command"]
    assert "--planfile-apply" in evidence["regenerate_command"]


def test_backfills_existing_project_discovery_ticket_before_reuse(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(cd, "_code2llm_executable", lambda: "/usr/bin/code2llm")
    sprint_dir = tmp_path / ".planfile" / "sprints"
    sprint_dir.mkdir(parents=True)
    (sprint_dir / "current.yaml").write_text(
        yaml.safe_dump(
            {
                "sprint": {
                    "tickets": {
                        "STARTER-249": {
                            "id": "STARTER-249",
                            "name": "Address code smell: God Function: build_parser",
                            "status": "open",
                            "priority": "high",
                            "source": {
                                "tool": "koru-project-discovery",
                                "context": {},
                            },
                            "files": ["src/koru/autonomous_parser.py"],
                        }
                    }
                }
            }
        ),
        encoding="utf-8",
    )
    ticket_yaml = {
        "schema": "code2llm.planfile_tickets.v1",
        "source": "koru-project-discovery",
        "tickets": [
            {
                "signal": "code2llm_smell_god_function",
                "title": "Address code smell: God Function: build_parser",
                "description": "Refactor build_parser",
                "priority": "high",
                "labels": ["llm-ready", "code2llm"],
                "files": ["src/koru/autonomous_parser.py"],
                "dedupe_key": (
                    "code2llm:smell:god_function:"
                    "src/koru/autonomous_parser.py:8:God Function: build_parser"
                ),
            }
        ],
    }

    outcome = cd.run_code2llm_discovery(
        tmp_path,
        runner=_make_runner(written_yaml=ticket_yaml),
        force=True,
    )

    assert outcome.applied_titles == []
    assert outcome.skipped_titles == ["Address code smell: God Function: build_parser"]
    sprint = yaml.safe_load((sprint_dir / "current.yaml").read_text(encoding="utf-8"))
    tickets = sprint["sprint"]["tickets"]
    assert list(tickets) == ["STARTER-249"]
    ctx = tickets["STARTER-249"]["source"]["context"]
    assert ctx["signal"] == "code2llm_smell_god_function"
    assert ctx["dedupe_key"].startswith("code2llm:smell:")
    assert ctx["evidence"]["artifact"]["path"] == "project/analysis.toon.yaml"


def test_applies_planfile_tickets_skips_equivalent_code2llm_symbol(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(cd, "_code2llm_executable", lambda: "/usr/bin/code2llm")
    sprint_dir = tmp_path / ".planfile" / "sprints"
    sprint_dir.mkdir(parents=True)
    (sprint_dir / "current.yaml").write_text(
        yaml.safe_dump(
            {
                "sprint": {
                    "tickets": {
                        "STARTER-1": {
                            "id": "STARTER-1",
                            "name": (
                                "Reduce cyclomatic complexity: "
                                "packages.coru.src.coru.cli._dispatch_command (CC=25)"
                            ),
                            "status": "open",
                            "files": ["packages/coru/src/coru/cli.py"],
                            "source": {
                                "tool": "koru-project-discovery",
                                "context": {
                                    "signal": "code2llm_cc",
                                    "dedupe_key": (
                                        "code2llm:cc:packages/coru/src/coru/cli.py:"
                                        "packages.coru.src.coru.cli._dispatch_command"
                                    ),
                                },
                            },
                        }
                    }
                }
            }
        ),
        encoding="utf-8",
    )
    ticket_yaml = {
        "schema": "code2llm.planfile_tickets.v1",
        "source": "koru-project-discovery",
        "tickets": [
            {
                "signal": "code2llm_cc",
                "title": "Reduce cyclomatic complexity: cli._dispatch_command (CC=25)",
                "description": "Refactor dispatch",
                "priority": "high",
                "labels": ["llm-ready", "code2llm"],
                "files": ["packages/coru/src/coru/cli.py"],
                "dedupe_key": (
                    "code2llm:cc:packages/coru/src/coru/cli.py:"
                    "cli._dispatch_command"
                ),
            }
        ],
    }

    outcome = cd.run_code2llm_discovery(
        tmp_path,
        runner=_make_runner(written_yaml=ticket_yaml),
        force=True,
    )

    assert outcome.applied_titles == []
    assert outcome.skipped_titles == [
        "Reduce cyclomatic complexity: cli._dispatch_command (CC=25)"
    ]
    sprint = yaml.safe_load((sprint_dir / "current.yaml").read_text(encoding="utf-8"))
    assert list(sprint["sprint"]["tickets"]) == ["STARTER-1"]


def test_applies_planfile_tickets_skips_existing_god_module_from_scan(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(cd, "_code2llm_executable", lambda: "/usr/bin/code2llm")
    sprint_dir = tmp_path / ".planfile" / "sprints"
    sprint_dir.mkdir(parents=True)
    (sprint_dir / "current.yaml").write_text(
        yaml.safe_dump(
            {
                "sprint": {
                    "tickets": {
                        "STARTER-1": {
                            "id": "STARTER-1",
                            "name": "Split god module: src/koru/doctor.py",
                            "status": "open",
                            "files": ["src/koru/doctor.py", "project/analysis.toon.yaml"],
                            "source": {
                                "tool": "koru-scan",
                                "context": {
                                    "signal": "code2llm_god",
                                    "dedupe_key": (
                                        "semcod:code2llm:refactor:src/koru/doctor.py"
                                    ),
                                },
                            },
                        }
                    }
                }
            }
        ),
        encoding="utf-8",
    )
    ticket_yaml = {
        "schema": "code2llm.planfile_tickets.v1",
        "source": "koru-project-discovery",
        "tickets": [
            {
                "signal": "code2llm_god",
                "title": "Split god module: src/koru/doctor.py",
                "description": "Split doctor.py",
                "priority": "high",
                "labels": ["llm-ready", "code2llm"],
                "files": ["src/koru/doctor.py"],
                "dedupe_key": "code2llm:god:src/koru/doctor.py",
            }
        ],
    }

    outcome = cd.run_code2llm_discovery(
        tmp_path,
        runner=_make_runner(written_yaml=ticket_yaml),
        force=True,
    )

    assert outcome.applied_titles == []
    assert outcome.skipped_titles == ["Split god module: src/koru/doctor.py"]


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


def test_fresh_artifacts_rerun_when_source_is_newer(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(cd, "_code2llm_executable", lambda: "/usr/bin/code2llm")
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    analysis = project_dir / "analysis.toon.yaml"
    analysis.write_text("old\n", encoding="utf-8")
    source = tmp_path / "src" / "changed.py"
    source.parent.mkdir()
    source.write_text("x = 1\n", encoding="utf-8")

    old = time.time() - 120
    new = time.time()
    (project_dir / "planfile-tickets.yaml").write_text(
        yaml.safe_dump({"applied": [], "skipped": []}),
        encoding="utf-8",
    )
    for path in (analysis, project_dir / "planfile-tickets.yaml"):
        path.touch()
        os.utime(path, (old, old))

    os.utime(source, (new, new))

    runner_calls: list[Sequence[str]] = []

    def runner(cmd, _cwd):
        runner_calls.append(cmd)
        return subprocess.CompletedProcess(list(cmd), 0)

    outcome = cd.run_code2llm_discovery(tmp_path, runner=runner, stale_minutes=999)

    assert runner_calls
    assert outcome.ran is True


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
