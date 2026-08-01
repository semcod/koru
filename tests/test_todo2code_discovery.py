"""Tests for koru.autonomy.todo2code_discovery."""

from __future__ import annotations

import json
import subprocess
from collections.abc import Sequence
from pathlib import Path
from types import SimpleNamespace

import pytest

import koru.tasks
from koru.autonomy import todo2code_discovery as td


def _sample_plan(
    *,
    plan_id: str = "CPLAN-aaaaaaaaaaaaaaaaaaaa",
    title: str = "Implement auth middleware",
    path: str = "src/auth.py",
    priority: str = "P1",
) -> dict:
    return {
        "schemaVersion": "t2c.code-change-plan/v1",
        "id": plan_id,
        "planHash": "a" * 64,
        "status": "proposed",
        "createdAt": "2026-07-30T00:00:00.000Z",
        "title": title,
        "description": f"Do: {title}",
        "priority": priority,
        "target": {"paths": [path], "symbols": [], "tickets": [], "versions": []},
        "acceptanceCriteria": ["Clear diagnostic", f"Touch only {path}"],
        "changes": [
            {
                "path": path,
                "action": "modify",
                "symbols": [],
                "rationale": "Implement planned work",
            }
        ],
        "risk": {"level": "medium", "reasons": ["review_required diagnostic"]},
        "rollback": f"Revert {path}",
        "evidence": {
            "graphFingerprint": "b" * 64,
            "recordIds": ["INT-TODO-cccccccccccccccccccc"],
            "diagnosticIds": ["DIAG-dddddddddddddddddddd"],
            "conclusionIds": [],
            "proposalIds": [],
        },
        "confidence": 0.8,
        "generation": {
            "generator": "t2c/code-change-plan",
            "generatorVersion": "1",
            "runtimeVersion": "0.5.0",
            "generatedAt": "2026-07-30T00:00:00.000Z",
            "requestedMode": "deterministic",
            "effectiveMode": "deterministic",
            "degraded": False,
            "model": None,
            "provider": None,
            "responseId": None,
            "configurationFingerprint": "c" * 64,
            "reason": None,
        },
    }


def _plan_set(*plans: dict) -> dict:
    return {
        "schemaVersion": "t2c.code-change-plan-set/v1",
        "plans": list(plans),
        "generatedAt": "2026-07-30T00:00:00.000Z",
        "graphFingerprint": "d" * 64,
        "sourceDiagnosticCount": len(plans),
        "generation": {
            "generator": "t2c/code-change-plan-set",
            "generatorVersion": "1",
            "runtimeVersion": "0.5.0",
            "generatedAt": "2026-07-30T00:00:00.000Z",
            "requestedMode": "deterministic",
            "effectiveMode": "deterministic",
            "degraded": False,
            "model": None,
            "provider": None,
            "responseId": None,
            "configurationFingerprint": "e" * 64,
            "reason": None,
        },
    }


class _RecordingRunner:
    def __init__(
        self,
        *,
        plan_set: dict | None = None,
        returncode: int = 0,
        stderr: str = "",
    ) -> None:
        self.plan_set = plan_set
        self.returncode = returncode
        self.stderr = stderr
        self.calls: list[list[str]] = []

    def __call__(self, cmd: Sequence[str], cwd: Path) -> subprocess.CompletedProcess[str]:
        self.calls.append(list(cmd))
        if self.plan_set is not None:
            out_idx = list(cmd).index("--out")
            out_dir = Path(list(cmd)[out_idx + 1])
            run_dir = out_dir / "runs" / "20260730T000000Z-deadbeef"
            run_dir.mkdir(parents=True, exist_ok=True)
            (run_dir / "code-change-plans.json").write_text(
                json.dumps(self.plan_set),
                encoding="utf-8",
            )
        return subprocess.CompletedProcess(
            list(cmd),
            self.returncode,
            stdout="",
            stderr=self.stderr,
        )


def _capture_created(monkeypatch: pytest.MonkeyPatch) -> list[dict]:
    created: list[dict] = []

    def fake_create_nl_task(
        project,
        text,
        *,
        sprint="current",
        priority="normal",
        scaffold=None,
        **kw,
    ):
        created.append(
            {
                "project": Path(project),
                "text": text,
                "priority": priority,
                "scaffold": scaffold or {},
            }
        )
        return SimpleNamespace(reused=False, id=f"STARTER-{800 + len(created)}")

    monkeypatch.setattr(koru.tasks, "create_nl_task", fake_create_nl_task)
    return created


@pytest.fixture()
def ready_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.delenv("KORU_TODO2CODE_ENABLE", raising=False)
    monkeypatch.delenv("KORU_TODO2CODE_BIN", raising=False)
    monkeypatch.delenv("KORU_TODO2CODE_MAX_TICKETS", raising=False)
    monkeypatch.delenv("KORU_TODO2CODE_LLM_EXECUTOR", raising=False)
    monkeypatch.delenv("KORU_TODO2CODE_CONTRACT", raising=False)
    monkeypatch.setattr(td, "_t2c_executable", lambda *a: "/fake/bin/t2c")
    for relative in ("src/auth.py", "src/rate.py", "docs/api.md"):
        target = tmp_path / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("# fixture\n", encoding="utf-8")
    return tmp_path


def test_skipped_when_disabled(ready_env: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("KORU_TODO2CODE_ENABLE", "0")
    outcome = td.run_todo2code_discovery(ready_env, runner=_RecordingRunner())
    assert outcome.ran is False
    assert "disabled" in (outcome.skipped_reason or "")


def test_skipped_when_binary_missing(ready_env: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(td, "_t2c_executable", lambda *a: None)
    outcome = td.run_todo2code_discovery(ready_env, runner=_RecordingRunner())
    assert outcome.ran is False
    assert "t2c not on PATH" in (outcome.skipped_reason or "")


def test_creates_tickets_from_pipeline_plans(
    ready_env: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    created = _capture_created(monkeypatch)
    runner = _RecordingRunner(
        plan_set=_plan_set(
            _sample_plan(title="Add rate limiter", path="src/rate.py", priority="P0"),
            _sample_plan(
                plan_id="CPLAN-bbbbbbbbbbbbbbbbbbbb",
                title="Document API",
                path="docs/api.md",
                priority="P3",
            ),
        ),
    )
    outcome = td.run_todo2code_discovery(ready_env, runner=runner, force=True)
    assert outcome.ran is True
    assert outcome.error is None
    assert outcome.plans_count == 2
    assert len(created) == 2
    assert created[0]["priority"] == "high"
    assert created[1]["priority"] == "low"
    assert created[0]["scaffold"]["files"] == ["src/rate.py"]
    assert created[0]["scaffold"]["inputs"]["expect_files_changed"] is True
    assert created[0]["scaffold"]["source_context"]["dedupe_key"].startswith("todo2code:plan:")
    assert "[todo2code]" in created[0]["scaffold"]["title"]
    assert "src/rate.py" in created[0]["text"]
    assert any("--nl-mode" in call and "deterministic" in call for call in runner.calls)


def test_skips_plans_without_paths(ready_env: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    created = _capture_created(monkeypatch)
    plan = _sample_plan()
    plan["target"] = {"paths": [], "symbols": [], "tickets": [], "versions": []}
    plan["changes"] = []
    runner = _RecordingRunner(plan_set=_plan_set(plan))
    outcome = td.run_todo2code_discovery(ready_env, runner=runner, force=True)
    assert outcome.ran is True
    assert outcome.plans_count == 1
    assert outcome.useful_plans_count == 0
    assert outcome.filtered_out_count == 1
    assert created == []

def test_reuses_fresh_artifact_without_rerun(
    ready_env: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    created = _capture_created(monkeypatch)
    out = ready_env / ".intent" / "runs" / "20260730T010101Z-cafe"
    out.mkdir(parents=True)
    plans_path = out / "code-change-plans.json"
    plans_path.write_text(json.dumps(_plan_set(_sample_plan())), encoding="utf-8")
    runner = _RecordingRunner(plan_set=_plan_set(_sample_plan(title="should-not-run")))
    outcome = td.run_todo2code_discovery(
        ready_env,
        runner=runner,
        force=False,
        stale_minutes=60.0,
    )
    assert outcome.ran is False
    assert outcome.skipped_reason and "younger" in outcome.skipped_reason
    assert len(created) == 1
    assert runner.calls == []


def test_dedupe_against_existing_sprint_ticket(
    ready_env: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import yaml

    created = _capture_created(monkeypatch)
    sprint_dir = ready_env / ".planfile" / "sprints"
    sprint_dir.mkdir(parents=True)
    plan = _sample_plan()
    dedupe = td._plan_dedupe_key(plan)
    (sprint_dir / "current.yaml").write_text(
        yaml.safe_dump(
            {
                "sprint": {
                    "tickets": {
                        "STARTER-1": {
                            "name": "old",
                            "source": {
                                "tool": "koru-todo2code-discovery",
                                "context": {"dedupe_key": dedupe},
                            },
                        }
                    }
                }
            }
        ),
        encoding="utf-8",
    )
    runner = _RecordingRunner(plan_set=_plan_set(plan))
    outcome = td.run_todo2code_discovery(ready_env, runner=runner, force=True)
    assert outcome.ran is True
    assert created == []
    assert len(outcome.skipped_titles) == 1


def test_dedupe_by_title_and_files_when_plan_id_changes(
    ready_env: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import yaml

    created = _capture_created(monkeypatch)
    sprint_dir = ready_env / ".planfile" / "sprints"
    sprint_dir.mkdir(parents=True)
    title = "[todo2code] Implement auth middleware"
    (sprint_dir / "current.yaml").write_text(
        yaml.safe_dump(
            {
                "sprint": {
                    "tickets": {
                        "STARTER-1": {
                            "name": title,
                            "files": ["src/auth.py"],
                            "source": {
                                "tool": "koru-todo2code-discovery",
                                "context": {"dedupe_key": "todo2code:plan:old-id"},
                            },
                        }
                    }
                }
            }
        ),
        encoding="utf-8",
    )
    # Fresh plan id, same title + path — must not create a second ticket.
    plan = _sample_plan(plan_id="CPLAN-ffffffffffffffffffff", title="Implement auth middleware")
    runner = _RecordingRunner(plan_set=_plan_set(plan))
    outcome = td.run_todo2code_discovery(ready_env, runner=runner, force=True)
    assert outcome.ran is True
    assert created == []
    assert len(outcome.skipped_titles) == 1


def test_pipeline_failure_records_error(
    ready_env: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _capture_created(monkeypatch)
    runner = _RecordingRunner(returncode=1, stderr="boom\n")
    outcome = td.run_todo2code_discovery(ready_env, runner=runner, force=True)
    assert outcome.ran is True
    assert outcome.error == "boom"


def test_build_cmd_includes_todo_and_changelog(tmp_path: Path) -> None:
    (tmp_path / "TODO.md").write_text("# TODO\n", encoding="utf-8")
    (tmp_path / "CHANGELOG.md").write_text("# Changelog\n", encoding="utf-8")
    cmd = td._build_pipeline_cmd("/usr/bin/t2c", tmp_path, out_dir=tmp_path / ".intent")
    assert cmd[0:3] == ["/usr/bin/t2c", "pipeline", str(tmp_path)]
    assert "--todo" in cmd
    assert "--changelog" in cmd
    assert "--no-docs-llm" in cmd
    assert "--no-communication" not in cmd
    assert cmd[cmd.index("--project-dir") + 1] == "project"


def test_output_directory_must_stay_inside_project(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("KORU_TODO2CODE_OUT", "../escaped")
    outcome = td.run_todo2code_discovery(tmp_path, runner=_RecordingRunner(), force=True)
    assert outcome.ran is False
    assert outcome.error and "inside the target project" in outcome.error


def test_node_entrypoint_for_cli_js(tmp_path: Path) -> None:
    cli = tmp_path / "cli.js"
    cli.write_text("// stub\n", encoding="utf-8")
    cmd = td._build_pipeline_cmd(
        str(cli),
        tmp_path,
        out_dir=tmp_path / ".intent",
    )
    assert cmd[0:3] == ["node", str(cli.resolve()), "pipeline"]


def test_symlink_t2c_resolved_to_node_cli(tmp_path: Path) -> None:
    """PATH-style symlink must become ``node <real cli.js>`` so main() runs."""
    real = tmp_path / "dist" / "src" / "cli.js"
    real.parent.mkdir(parents=True)
    real.write_text("// stub\n", encoding="utf-8")
    link = tmp_path / "bin" / "t2c"
    link.parent.mkdir(parents=True)
    link.symlink_to(real)
    cmd = td._build_pipeline_cmd(str(link), tmp_path, out_dir=tmp_path / ".intent")
    assert cmd[0] == "node"
    assert cmd[1] == str(real.resolve())
    assert cmd[2] == "pipeline"


def test_scan_adapter_reads_plans(tmp_path: Path) -> None:
    from koru.scan import _scan_todo2code_plans

    run = tmp_path / ".intent" / "runs" / "20260730T000000Z-feed"
    run.mkdir(parents=True)
    source = tmp_path / "src" / "koru" / "x.py"
    source.parent.mkdir(parents=True)
    source.write_text("def run(): pass\n", encoding="utf-8")
    (run / "code-change-plans.json").write_text(
        json.dumps(_plan_set(_sample_plan(title="Wire todo2code", path="src/koru/x.py"))),
        encoding="utf-8",
    )
    suggestions = _scan_todo2code_plans(tmp_path)
    assert len(suggestions) == 1
    assert suggestions[0].signal == "todo2code_plan"
    assert "todo2code" in suggestions[0].title
    assert suggestions[0].files == ("src/koru/x.py",)
    assert suggestions[0].source_context["dedupe_key"].startswith("todo2code:plan:")


def test_filters_junk_paths_and_prefers_source(
    ready_env: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    created = _capture_created(monkeypatch)
    junk = _sample_plan(
        plan_id="CPLAN-junkjunkjunkjunkjunk",
        title="Refactor vendored helper",
        path=".testvenv/lib/python3.13/site-packages/pip/auth.py",
    )
    good = _sample_plan(
        plan_id="CPLAN-goodgoodgoodgoodgood",
        title="Implement rate limiter",
        path="src/rate.py",
        priority="P0",
    )
    runner = _RecordingRunner(plan_set=_plan_set(junk, good))
    outcome = td.run_todo2code_discovery(ready_env, runner=runner, force=True)
    assert outcome.ran is True
    assert outcome.filtered_out_count >= 1
    assert outcome.useful_plans_count == 1
    assert len(created) == 1
    assert created[0]["scaffold"]["files"] == ["src/rate.py"]
    assert "useful-code-change" in created[0]["scaffold"]["labels"]
    assert created[0]["scaffold"]["executor_kind"] == "human"
    assert created[0]["scaffold"]["executor_mode"] == "interactive"
    assert created[0]["scaffold"]["inputs"]["patch_mode"] is True
    assert created[0]["scaffold"]["inputs"]["llm_max_tokens"] == 4000
    assert created[0]["scaffold"]["inputs"]["llm_timeout_seconds"] == 300


def test_llm_executor_requires_named_project_contract(
    ready_env: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    created = _capture_created(monkeypatch)
    monkeypatch.setenv("KORU_TODO2CODE_LLM_EXECUTOR", "1")
    runner = _RecordingRunner(plan_set=_plan_set(_sample_plan()))
    td.run_todo2code_discovery(ready_env, runner=runner, force=True)
    assert created[0]["scaffold"]["executor_kind"] == "human"

    created.clear()
    monkeypatch.setenv("KORU_TODO2CODE_CONTRACT", "todo2code-r1")
    td.run_todo2code_discovery(ready_env, runner=runner, force=True)
    assert created[0]["scaffold"]["executor_kind"] == "llm"
    assert created[0]["scaffold"]["inputs"]["contract"] == "todo2code-r1"
