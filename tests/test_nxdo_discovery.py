"""Tests for koru.autonomy.nxdo_discovery."""

from __future__ import annotations

import json
import subprocess
from collections.abc import Sequence
from pathlib import Path
from types import SimpleNamespace

import pytest
import yaml

import koru.tasks
from koru.autonomy import nxdo_discovery as nd


def _plan_json(*tasks: dict) -> str:
    return json.dumps(
        {
            "project_name": "demo",
            "summary": "next steps",
            "tasks": list(tasks),
        }
    )


def _task(number: int = 1, title: str = "Add CI pipeline", **extra: object) -> dict:
    base: dict = {
        "number": number,
        "title": title,
        "description": f"Do: {title}",
        "priority": "high",
        "task_type": "chore",
        "acceptance_criteria": ["works"],
        "dependencies": [],
    }
    base.update(extra)
    return base


class _RecordingRunner:
    def __init__(self, stdout: str, returncode: int = 0, stderr: str = "") -> None:
        self.stdout = stdout
        self.returncode = returncode
        self.stderr = stderr
        self.calls: list[list[str]] = []

    def __call__(self, cmd: Sequence[str], cwd: Path) -> subprocess.CompletedProcess[str]:
        self.calls.append(list(cmd))
        return subprocess.CompletedProcess(
            list(cmd), self.returncode, stdout=self.stdout, stderr=self.stderr
        )


def _make_runner(stdout: str, returncode: int = 0, stderr: str = "") -> _RecordingRunner:
    return _RecordingRunner(stdout, returncode, stderr)


@pytest.fixture()
def ready_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.delenv("KORU_NXDO_REPOS", raising=False)
    monkeypatch.delenv("KORU_NXDO_ENABLE", raising=False)
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    monkeypatch.setattr(nd, "_nxdo_executable", lambda *a: "/fake/bin/nxdo")
    return tmp_path


def _capture_created(monkeypatch: pytest.MonkeyPatch) -> list[dict]:
    created: list[dict] = []

    def fake_create_nl_task(project, text, *, sprint="current", priority="normal", scaffold=None, **kw):
        created.append(
            {
                "project": Path(project),
                "text": text,
                "priority": priority,
                "scaffold": scaffold or {},
            }
        )
        return SimpleNamespace(reused=False, id=f"STARTER-{900 + len(created)}")

    monkeypatch.setattr(koru.tasks, "create_nl_task", fake_create_nl_task)
    return created


def test_skipped_when_disabled(ready_env: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("KORU_NXDO_ENABLE", "0")
    outcome = nd.run_nxdo_discovery(ready_env, runner=_make_runner(""))
    assert outcome.ran is False
    assert "disabled" in (outcome.skipped_reason or "")


def test_skipped_when_binary_missing(ready_env: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(nd, "_nxdo_executable", lambda *a: None)
    outcome = nd.run_nxdo_discovery(ready_env, runner=_make_runner(""))
    assert outcome.ran is False
    assert "nxdo not on PATH" in (outcome.skipped_reason or "")


def test_skipped_without_api_key(ready_env: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    outcome = nd.run_nxdo_discovery(ready_env, runner=_make_runner(""))
    assert outcome.ran is False
    assert "API_KEY" in (outcome.skipped_reason or "")


def test_api_key_from_project_env_file(ready_env: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    (ready_env / ".env").write_text("OPENROUTER_API_KEY=sk-x\n", encoding="utf-8")
    created = _capture_created(monkeypatch)
    outcome = nd.run_nxdo_discovery(ready_env, runner=_make_runner(_plan_json(_task())))
    assert outcome.ran is True
    assert len(created) == 1


def test_creates_tickets_from_plan_json(ready_env: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    created = _capture_created(monkeypatch)
    runner = _make_runner(_plan_json(_task(1, "Add CI"), _task(2, "Fix docs", priority="low")))
    outcome = nd.run_nxdo_discovery(ready_env, runner=runner)
    assert outcome.ran is True
    assert outcome.error is None
    assert outcome.applied_titles == ["Add CI", "Fix docs"]
    assert runner.calls[0][:2] == ["/fake/bin/nxdo", "plan"]
    assert "--json" in runner.calls[0]
    assert created[0]["priority"] == "high"
    assert created[1]["priority"] == "low"
    scaffold = created[0]["scaffold"]
    assert scaffold["source_tool"] == nd.DEFAULT_SOURCE
    assert scaffold["source_context"]["dedupe_key"].startswith("nxdo:")
    assert "nxdo" in scaffold["labels"]


def test_model_knob_passes_model_flag(ready_env: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("KORU_NXDO_MODEL", "qwen/qwen3-coder-next")
    _capture_created(monkeypatch)
    runner = _make_runner(_plan_json(_task()))
    nd.run_nxdo_discovery(ready_env, runner=runner)
    cmd = runner.calls[0]
    assert cmd[cmd.index("--model") + 1] == "qwen/qwen3-coder-next"


def test_max_tickets_cap(ready_env: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("KORU_NXDO_MAX_TICKETS", "1")
    created = _capture_created(monkeypatch)
    runner = _make_runner(_plan_json(_task(1, "One"), _task(2, "Two")))
    outcome = nd.run_nxdo_discovery(ready_env, runner=runner)
    assert outcome.applied_titles == ["One"]
    assert len(created) == 1


def test_dedupe_skips_existing_keys(ready_env: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    created = _capture_created(monkeypatch)
    key = nd._dedupe_key(ready_env, {"title": "Add CI"})
    sprint_dir = ready_env / ".planfile" / "sprints"
    sprint_dir.mkdir(parents=True)
    (sprint_dir / "current.yaml").write_text(
        yaml.safe_dump(
            {
                "sprint": {
                    "tickets": {
                        "STARTER-1": {
                            "source": {"tool": nd.DEFAULT_SOURCE, "context": {"dedupe_key": key}},
                        }
                    }
                }
            }
        ),
        encoding="utf-8",
    )
    outcome = nd.run_nxdo_discovery(ready_env, runner=_make_runner(_plan_json(_task(1, "Add CI"))))
    assert outcome.applied_titles == []
    assert outcome.skipped_titles == ["Add CI"]
    assert created == []


def test_cooldown_blocks_second_run(ready_env: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _capture_created(monkeypatch)
    runner = _make_runner(_plan_json(_task()))
    first = nd.run_nxdo_discovery(ready_env, runner=runner)
    assert first.ran is True
    second = nd.run_nxdo_discovery(ready_env, runner=runner)
    assert second.ran is False
    assert "cooldown" in (second.skipped_reason or "")


def test_failure_still_stamps_cooldown(ready_env: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    runner = _make_runner("", returncode=2, stderr="boom")
    first = nd.run_nxdo_discovery(ready_env, runner=runner)
    assert first.ran is True
    assert first.error == "boom"
    second = nd.run_nxdo_discovery(ready_env, runner=runner)
    assert second.ran is False
    assert "cooldown" in (second.skipped_reason or "")


def test_unparseable_output_reports_error(ready_env: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    outcome = nd.run_nxdo_discovery(ready_env, runner=_make_runner("not json at all"))
    assert outcome.ran is True
    assert "no parseable TaskPlan" in (outcome.error or "")


def test_target_repos_glob_expansion(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    project = tmp_path / "koru"
    (project / ".git").mkdir(parents=True)
    sibling = tmp_path / "other"
    (sibling / ".git").mkdir(parents=True)
    plain_dir = tmp_path / "no-repo"
    plain_dir.mkdir()
    monkeypatch.setenv("KORU_NXDO_REPOS", str(tmp_path / "*"))
    repos = nd.nxdo_target_repos(project)
    assert repos[0] == project.resolve()
    assert sibling.resolve() in repos
    assert plain_dir.resolve() not in repos
    assert repos.count(project.resolve()) == 1


def test_cross_repo_rotation_and_ticket_prefix(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    project = tmp_path / "koru"
    (project / ".git").mkdir(parents=True)
    sibling = tmp_path / "other"
    (sibling / ".git").mkdir(parents=True)
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    monkeypatch.setenv("KORU_NXDO_REPOS", str(sibling))
    monkeypatch.setattr(nd, "_nxdo_executable", lambda *a: "/fake/bin/nxdo")
    created = _capture_created(monkeypatch)

    runner = _make_runner(_plan_json(_task(1, "Sibling work")))
    first = nd.run_nxdo_discovery(project, runner=runner)
    assert first.target_repo == str(project.resolve())

    second = nd.run_nxdo_discovery(project, runner=runner)
    assert second.target_repo == str(sibling.resolve())
    assert runner.calls[1][2] == str(sibling.resolve())

    cross = created[-1]
    assert cross["text"].startswith(f"[repo: {sibling.resolve()}]")
    assert "cross-repo" in cross["scaffold"]["labels"]
    assert cross["project"] == project.resolve()

    third = nd.run_nxdo_discovery(project, runner=runner)
    assert third.ran is False
    assert "cooldown" in (third.skipped_reason or "")


def test_format_summary_variants() -> None:
    skipped = nd.NxdoDiscoveryOutcome(skipped_reason="disabled")
    assert "skipped" in nd.format_nxdo_summary(skipped)
    errored = nd.NxdoDiscoveryOutcome(ran=True, error="rc=2")
    assert "error" in nd.format_nxdo_summary(errored)
    ok = nd.NxdoDiscoveryOutcome(ran=True, applied_titles=["a"], target_repo="/x")
    line = nd.format_nxdo_summary(ok)
    assert "applied=1" in line and "repo=/x" in line
