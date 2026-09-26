"""Focused tests for the split todo2code discovery modules.

Pin the moved behavior at its new homes (todo2code_config,
todo2code_plans, todo2code_tickets) and the
``koru.autonomy.todo2code_discovery`` facade surface: every moved name
must keep resolving through the facade, and the test-facing
``_t2c_executable`` facade patch target must keep steering the pipeline
(late binding through facade globals).
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from types import SimpleNamespace

import pytest
import yaml

import koru.tasks
from koru.autonomy import todo2code_config, todo2code_discovery, todo2code_plans, todo2code_tickets


@pytest.fixture()
def clean_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    for name in (
        "KORU_TODO2CODE_ENABLE",
        "KORU_TODO2CODE_BIN",
        "KORU_TODO2CODE_OUT",
        "KORU_TODO2CODE_MAX_TICKETS",
        "KORU_TODO2CODE_STALE_MINUTES",
        "KORU_TODO2CODE_TIMEOUT_SECONDS",
        "KORU_TODO2CODE_MIN_USEFULNESS",
        "KORU_TODO2CODE_LLM_EXECUTOR",
        "KORU_TODO2CODE_CONTRACT",
    ):
        monkeypatch.delenv(name, raising=False)
    return tmp_path


# ---------------------------------------------------------------- facade


def test_facade_reexports_moved_names() -> None:
    """Every moved name resolves through the facade to its home object."""
    config_names = [
        "DEFAULT_MAX_TICKETS",
        "DEFAULT_MIN_USEFULNESS",
        "DEFAULT_OUT_SUBDIR",
        "DEFAULT_SOURCE",
        "DEFAULT_STALE_MINUTES",
        "DEFAULT_TIMEOUT_SECONDS",
        "_config_value",
        "_discovery_limits",
        "_env_flag",
        "_env_float",
        "_env_int",
        "_out_dir",
        "todo2code_enabled",
    ]
    plans_names = [
        "PLANS_FILENAME",
        "_load_plan_set",
        "_plan_dedupe_key",
        "_plan_paths",
        "_plans_fresh",
        "_slug",
        "_string_list",
        "_truncate",
        "find_latest_plans_path",
    ]
    tickets_names = [
        "_PRIORITY_MAP",
        "_ExistingPlanTickets",
        "_PlanDispatch",
        "_PlanIdentity",
        "_RankedPlans",
        "_apply_plan_tickets",
        "_dispatch_plan_task",
        "_enrich_plan_scaffold",
        "_existing_todo2code_keys",
        "_file_evidence",
        "_file_plan_ticket",
        "_plan_identity",
        "_rank_useful_plans",
        "_read_sprint_tickets",
        "_record_plan_dispatch",
        "_remember_todo2code_ticket",
        "_relative_plans_path",
        "_resolve_plan_priority",
        "_ticket_change_lines",
        "_ticket_plan_lines",
        "_ticket_recovery_lines",
        "_ticket_risk_lines",
        "_ticket_scaffold",
        "_ticket_text",
        "_ticket_title",
    ]
    for home, names in (
        (todo2code_config, config_names),
        (todo2code_plans, plans_names),
        (todo2code_tickets, tickets_names),
    ):
        for name in names:
            assert getattr(todo2code_discovery, name) is getattr(home, name), name


def test_facade_all_unchanged() -> None:
    assert todo2code_discovery.__all__ == [
        "Todo2codeDiscoveryOutcome",
        "Runner",
        "find_latest_plans_path",
        "format_todo2code_summary",
        "run_todo2code_discovery",
        "todo2code_enabled",
    ]


def test_facade_patch_target_still_steers_pipeline(
    clean_env: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Patching _t2c_executable on the facade must keep steering the pipeline."""
    monkeypatch.setattr(todo2code_discovery, "_t2c_executable", lambda *a: None)

    def _boom(cmd, cwd):  # pragma: no cover - must never run
        raise AssertionError("runner must not be reached when binary is missing")

    outcome = todo2code_discovery.run_todo2code_discovery(clean_env, runner=_boom)
    assert outcome.ran is False
    assert "t2c not on PATH" in (outcome.skipped_reason or "")


# --------------------------------------------------------- todo2code_config


@pytest.mark.parametrize("raw,expected", [("1", True), ("true", True), ("yes", True), ("on", True), ("0", False), ("off", False)])
def test_env_flag_truthy_set(clean_env: Path, monkeypatch: pytest.MonkeyPatch, raw: str, expected: bool) -> None:
    monkeypatch.setenv("KORU_TODO2CODE_PROBE_FLAG", raw)
    assert todo2code_config._env_flag("KORU_TODO2CODE_PROBE_FLAG", False) is expected


def test_env_flag_and_numeric_fallbacks(clean_env: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("KORU_TODO2CODE_PROBE_FLAG", raising=False)
    assert todo2code_config._env_flag("KORU_TODO2CODE_PROBE_FLAG", True) is True
    monkeypatch.setenv("KORU_TODO2CODE_PROBE_FLOAT", "not-a-number")
    assert todo2code_config._env_float("KORU_TODO2CODE_PROBE_FLOAT", 12.5) == 12.5
    monkeypatch.setenv("KORU_TODO2CODE_PROBE_INT", "7x")
    assert todo2code_config._env_int("KORU_TODO2CODE_PROBE_INT", 4) == 4
    monkeypatch.setenv("KORU_TODO2CODE_PROBE_FLOAT", "2.5")
    assert todo2code_config._env_float("KORU_TODO2CODE_PROBE_FLOAT", 12.5) == 2.5


def test_todo2code_enabled_default_and_disabled(
    clean_env: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    assert todo2code_config.todo2code_enabled(clean_env) is True
    monkeypatch.setenv("KORU_TODO2CODE_ENABLE", "0")
    assert todo2code_config.todo2code_enabled(clean_env) is False


def test_out_dir_default_env_and_dotenv(clean_env: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    assert todo2code_config._out_dir(clean_env) == clean_env / ".intent"
    monkeypatch.setenv("KORU_TODO2CODE_OUT", "artifacts")
    assert todo2code_config._out_dir(clean_env) == clean_env / "artifacts"
    monkeypatch.delenv("KORU_TODO2CODE_OUT", raising=False)
    (clean_env / ".env").write_text("KORU_TODO2CODE_OUT=from-dotenv\n", encoding="utf-8")
    assert todo2code_config._out_dir(clean_env) == clean_env / "from-dotenv"


def test_out_dir_rejects_escape_outside_project(
    clean_env: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("KORU_TODO2CODE_OUT", "../elsewhere")
    with pytest.raises(ValueError, match="must resolve inside the target project"):
        todo2code_config._out_dir(clean_env)


def test_discovery_limits_defaults_overrides_and_floor(
    clean_env: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    assert todo2code_config._discovery_limits(clean_env, None, None) == (60.0, 10, 8.0)
    assert todo2code_config._discovery_limits(clean_env, 5.0, 2) == (5.0, 2, 8.0)
    monkeypatch.setenv("KORU_TODO2CODE_STALE_MINUTES", "5")
    monkeypatch.setenv("KORU_TODO2CODE_MAX_TICKETS", "0")
    monkeypatch.setenv("KORU_TODO2CODE_MIN_USEFULNESS", "3")
    assert todo2code_config._discovery_limits(clean_env, None, None) == (5.0, 1, 3.0)
    # explicit arguments take precedence over environment knobs
    assert todo2code_config._discovery_limits(clean_env, 9.0, 4) == (9.0, 4, 3.0)


# ---------------------------------------------------------- todo2code_plans


def test_find_latest_plans_path_prefers_newest_run(tmp_path: Path) -> None:
    assert todo2code_plans.find_latest_plans_path(tmp_path) is None
    flat = tmp_path / "code-change-plans.json"
    flat.write_text("{}", encoding="utf-8")
    assert todo2code_plans.find_latest_plans_path(tmp_path) == flat

    older = tmp_path / "runs" / "a" / "code-change-plans.json"
    newer = tmp_path / "runs" / "b" / "code-change-plans.json"
    for path in (older, newer):
        path.parent.mkdir(parents=True)
        path.write_text("{}", encoding="utf-8")
    older_times = (1000.0, 1000.0)
    newer_times = (2000.0, 2000.0)
    os.utime(older, older_times)
    os.utime(newer, newer_times)
    assert todo2code_plans.find_latest_plans_path(tmp_path) == newer


def test_plans_fresh_boundary_and_missing(tmp_path: Path) -> None:
    artifact = tmp_path / "plans.json"
    assert todo2code_plans._plans_fresh(artifact, stale_minutes=60.0) is False
    artifact.write_text("{}", encoding="utf-8")
    assert todo2code_plans._plans_fresh(artifact, stale_minutes=60.0) is True
    old = 7200.0
    os.utime(artifact, (artifact.stat().st_mtime - old, artifact.stat().st_mtime - old))
    assert todo2code_plans._plans_fresh(artifact, stale_minutes=60.0) is False


def test_load_plan_set_rejects_unreadable_and_non_mapping(tmp_path: Path) -> None:
    artifact = tmp_path / "plans.json"
    artifact.write_text("{not json", encoding="utf-8")
    assert todo2code_plans._load_plan_set(artifact) is None
    artifact.write_text('["a list"]', encoding="utf-8")
    assert todo2code_plans._load_plan_set(artifact) is None
    artifact.write_text('{"plans": []}', encoding="utf-8")
    assert todo2code_plans._load_plan_set(artifact) == {"plans": []}


@pytest.mark.parametrize(
    "value,expected",
    [([], []), (None, []), (["a", " ", "b"], ["a", "b"]), ([1, ""], ["1"])],
)
def test_string_list_normalization(value: object, expected: list[str]) -> None:
    assert todo2code_plans._string_list(value) == expected


def test_truncate_collapses_and_elides() -> None:
    assert todo2code_plans._truncate("a  b\n c") == "a b c"
    long = "x" * 300
    out = todo2code_plans._truncate(long, 20)
    assert len(out) == 20
    assert out.endswith("…")


def test_plan_paths_filters_non_useful_targets() -> None:
    plan = {"target": {"paths": ["src/a.py", "logo.png", "venv/x.py"]}}
    paths = todo2code_plans._plan_paths(plan)
    assert "src/a.py" in paths
    assert "logo.png" not in paths


def test_plan_dedupe_key_tiers() -> None:
    assert todo2code_plans._plan_dedupe_key({"id": "CPLAN-1"}) == "todo2code:plan:CPLAN-1"
    assert todo2code_plans._plan_dedupe_key({"planHash": "deadbeef"}) == "todo2code:hash:deadbeef"
    fallback = todo2code_plans._plan_dedupe_key(
        {"title": "Fix Thing", "target": {"paths": ["src/a.py"]}}
    )
    assert fallback.startswith("todo2code:fallback:")
    same_again = todo2code_plans._plan_dedupe_key(
        {"title": "Fix Thing", "target": {"paths": ["src/a.py"]}}
    )
    other = todo2code_plans._plan_dedupe_key(
        {"title": "Other Thing", "target": {"paths": ["src/a.py"]}}
    )
    assert fallback == same_again
    assert fallback != other


def test_slug_normalization() -> None:
    assert todo2code_plans._slug("Hello, World! (v2)") == "hello-world-v2"
    assert todo2code_plans._slug("---") == ""


# -------------------------------------------------------- todo2code_tickets


@pytest.mark.parametrize(
    "raw,expected",
    [("P0", "high"), ("P1", "high"), ("P2", "normal"), ("P3", "low"), ("", "normal"), ("weird", "normal")],
)
def test_resolve_plan_priority_mapping(raw: str, expected: str) -> None:
    assert todo2code_tickets._resolve_plan_priority({"priority": raw}) == expected


def _plan(name: str, priority: str = "P2", path: str | None = None) -> dict:
    path = path or f"src/{name}.py"
    return {
        "id": name,
        "title": name,
        "priority": priority,
        "target": {"paths": [path]},
        "changes": [{"path": path, "action": "create"}],
    }


def test_rank_useful_plans_filters_and_orders(clean_env: Path) -> None:
    plan_set = {"plans": [None, "bad", _plan("low", "P3"), _plan("first", "P1"), _plan("asset", path="logo.png")]}
    ranked = todo2code_tickets._rank_useful_plans(clean_env, plan_set, 8.0)
    assert [p["id"] for p in ranked.useful] == ["first", "low"]
    assert ranked.filtered_out == 1  # asset path filtered; None/"bad" dropped pre-count


def test_apply_plan_tickets_at_new_home(
    clean_env: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls: list[str] = []

    def create(project, text, **kwargs):
        calls.append(kwargs["scaffold"]["title"])
        return SimpleNamespace(reused=False)

    monkeypatch.setattr(koru.tasks, "create_nl_task", create)
    created, skipped, useful, filtered = todo2code_tickets._apply_plan_tickets(
        clean_env,
        {"plans": [_plan("first", "P1"), _plan("second", "P1"), _plan("third", "P1")]},
        plans_path=clean_env / "plans.json",
        source=todo2code_config.DEFAULT_SOURCE,
        limit=2,
    )
    assert created == ["[todo2code] first", "[todo2code] second"]
    assert skipped == []
    assert (useful, filtered) == (3, 0)
    # limit caps creations; the third useful plan is never dispatched
    assert calls == created


def test_ticket_scaffold_executor_stays_human_without_contract(
    clean_env: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("KORU_TODO2CODE_LLM_EXECUTOR", "1")
    scaffold = todo2code_tickets._ticket_scaffold(
        _plan("auth"),
        project=clean_env,
        plans_path=clean_env / "plans.json",
        source=todo2code_config.DEFAULT_SOURCE,
    )
    assert scaffold["executor_kind"] == "human"
    assert scaffold["executor_mode"] == "interactive"
    assert scaffold["max_attempts"] == 1
    assert "contract" not in scaffold["inputs"]

    monkeypatch.setenv("KORU_TODO2CODE_CONTRACT", "change-runner")
    scaffold = todo2code_tickets._ticket_scaffold(
        _plan("auth"),
        project=clean_env,
        plans_path=clean_env / "plans.json",
        source=todo2code_config.DEFAULT_SOURCE,
    )
    assert scaffold["executor_kind"] == "llm"
    assert scaffold["executor_mode"] == "automatic"
    assert scaffold["max_attempts"] == 3
    assert scaffold["inputs"]["contract"] == "change-runner"


def test_plan_identity_from_scaffold() -> None:
    scaffold = {
        "title": "[todo2code] Task",
        "files": ["src/a.py", ""],
        "source_context": {"dedupe_key": "todo2code:plan:1"},
    }
    identity = todo2code_tickets._plan_identity(scaffold)
    assert identity.title == "[todo2code] Task"
    assert identity.key == "todo2code:plan:1"
    assert identity.title_key == ("[todo2code] Task", ("src/a.py",))


def test_existing_todo2code_keys_at_new_home(tmp_path: Path) -> None:
    sprint_dir = tmp_path / ".planfile" / "sprints"
    sprint_dir.mkdir(parents=True)
    (sprint_dir / "current.yaml").write_text(
        yaml.safe_dump(
            {
                "sprint": {
                    "tickets": {
                        "t1": {
                            "name": "[todo2code] Done already",
                            "files": ["src/a.py"],
                            "source": {
                                "tool": todo2code_config.DEFAULT_SOURCE,
                                "context": {"dedupe_key": "todo2code:plan:1"},
                            },
                        }
                    }
                }
            }
        ),
        encoding="utf-8",
    )
    existing = todo2code_tickets._existing_todo2code_keys(tmp_path)
    assert existing.keys == {"todo2code:plan:1"}
    assert existing.title_files == {("[todo2code] Done already", ("src/a.py",))}
