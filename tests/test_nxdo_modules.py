"""Focused tests for the split nxdo discovery modules.

Pin the moved behavior at its new homes (nxdo_config, nxdo_cooldown,
nxdo_tickets) and the koru.autonomy.nxdo_discovery facade surface:
every moved name must keep resolving through the facade, and the
test-facing ``_nxdo_executable`` facade patch target must keep steering
the pipeline (late binding through facade globals).
"""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest
import yaml

import koru.tasks
from koru.autonomy import nxdo_config, nxdo_cooldown, nxdo_discovery, nxdo_tickets


@pytest.fixture()
def clean_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    for name in (
        "KORU_NXDO_ENABLE",
        "KORU_NXDO_BIN",
        "KORU_NXDO_REPOS",
        "KORU_NXDO_MODEL",
        "KORU_NXDO_EXTRA_CONTEXT",
        "KORU_NXDO_MAX_TICKETS",
        "KORU_NXDO_COOLDOWN_SECONDS",
        "KORU_NXDO_TIMEOUT_SECONDS",
        "OPENROUTER_API_KEY",
        "OPENAI_API_KEY",
    ):
        monkeypatch.delenv(name, raising=False)
    return tmp_path


# ---------------------------------------------------------------- facade


def test_facade_reexports_moved_names() -> None:
    """Every moved name resolves through the facade to its home object."""
    config_names = [
        "DEFAULT_TIMEOUT_SECONDS",
        "Runner",
        "_api_key_available",
        "_config_value",
        "_default_runner",
        "_dotenv_value",
        "_env_flag",
        "_env_float",
        "_env_int",
        "_nxdo_executable",
        "nxdo_enabled",
        "nxdo_target_repos",
    ]
    cooldown_names = [
        "DEFAULT_COOLDOWN_SECONDS",
        "STAMP_RELPATH",
        "_CooldownSelection",
        "_load_stamps",
        "_save_stamps",
        "_select_target_repo",
        "_stamp_path",
    ]
    tickets_names = [
        "DEFAULT_MAX_TICKETS",
        "DEFAULT_SOURCE",
        "_PlanFiling",
        "_PRIORITY_MAP",
        "_apply_plan_tickets",
        "_dedupe_key",
        "_existing_nxdo_dedupe_keys",
        "_plan_from_output",
        "_slug",
        "_ticket_scaffold",
        "_ticket_text",
    ]
    for home, names in (
        (nxdo_config, config_names),
        (nxdo_cooldown, cooldown_names),
        (nxdo_tickets, tickets_names),
    ):
        for name in names:
            assert getattr(nxdo_discovery, name) is getattr(home, name), name


def test_facade_all_unchanged() -> None:
    assert nxdo_discovery.__all__ == [
        "NxdoDiscoveryOutcome",
        "Runner",
        "format_nxdo_summary",
        "nxdo_enabled",
        "nxdo_target_repos",
        "run_nxdo_discovery",
    ]


def test_facade_patch_target_still_steers_pipeline(clean_env: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Patching _nxdo_executable on the facade must keep affecting _preflight."""
    monkeypatch.setattr(nxdo_discovery, "_nxdo_executable", lambda *a: None)
    outcome = nxdo_discovery.run_nxdo_discovery(clean_env, runner=lambda *a: None / 0)
    assert outcome.ran is False
    assert "nxdo not on PATH" in (outcome.skipped_reason or "")


# ----------------------------------------------------------- nxdo_config


def test_dotenv_value_parsing(clean_env: Path) -> None:
    (clean_env / ".env").write_text(
        "  PLAIN = hello \nQUOTED=\"quoted value\"\nSINGLE='single'\n# comment\nBROKEN\n",
        encoding="utf-8",
    )
    assert nxdo_config._dotenv_value(clean_env, "PLAIN") == "hello"
    assert nxdo_config._dotenv_value(clean_env, "QUOTED") == "quoted value"
    assert nxdo_config._dotenv_value(clean_env, "SINGLE") == "single"
    assert nxdo_config._dotenv_value(clean_env, "MISSING") == ""
    assert nxdo_config._dotenv_value(None, "PLAIN") == ""
    assert nxdo_config._dotenv_value(clean_env / "nowhere", "PLAIN") == ""


def test_config_value_env_wins_over_dotenv(clean_env: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    (clean_env / ".env").write_text("KORU_NXDO_MODEL=from-file\n", encoding="utf-8")
    assert nxdo_config._config_value("KORU_NXDO_MODEL", clean_env) == "from-file"
    monkeypatch.setenv("KORU_NXDO_MODEL", " from-env ")
    assert nxdo_config._config_value("KORU_NXDO_MODEL", clean_env) == "from-env"


def test_env_accessors_defaults_and_garbage(clean_env: Path) -> None:
    assert nxdo_config._env_flag("KORU_NXDO_ENABLE", True, clean_env) is True
    assert nxdo_config._env_flag("KORU_NXDO_ENABLE", False, clean_env) is False
    (clean_env / ".env").write_text(
        "KORU_NXDO_ENABLE=1\nKORU_NXDO_TIMEOUT_SECONDS=oops\nKORU_NXDO_MAX_TICKETS=nan\n",
        encoding="utf-8",
    )
    assert nxdo_config._env_flag("KORU_NXDO_ENABLE", False, clean_env) is True
    assert nxdo_config._env_float("KORU_NXDO_TIMEOUT_SECONDS", 300.0, clean_env) == 300.0
    assert nxdo_config._env_int("KORU_NXDO_MAX_TICKETS", 5, clean_env) == 5


def test_nxdo_enabled_knob(clean_env: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    assert nxdo_config.nxdo_enabled(clean_env) is True
    monkeypatch.setenv("KORU_NXDO_ENABLE", "0")
    assert nxdo_config.nxdo_enabled(clean_env) is False
    monkeypatch.delenv("KORU_NXDO_ENABLE")
    (clean_env / ".env").write_text("KORU_NXDO_ENABLE=false\n", encoding="utf-8")
    assert nxdo_config.nxdo_enabled(clean_env) is False


def test_nxdo_executable_override_must_be_a_file(clean_env: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    binary = clean_env / "nxdo-bin"
    binary.write_text("", encoding="utf-8")
    monkeypatch.setenv("KORU_NXDO_BIN", str(binary))
    assert nxdo_config._nxdo_executable(clean_env) == str(binary)
    monkeypatch.setenv("KORU_NXDO_BIN", str(clean_env / "missing"))
    assert nxdo_config._nxdo_executable(clean_env) is None


def test_api_key_available_sources(clean_env: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    assert nxdo_config._api_key_available(clean_env) is False
    monkeypatch.setenv("OPENAI_API_KEY", "sk-1")
    assert nxdo_config._api_key_available(clean_env) is True
    monkeypatch.delenv("OPENAI_API_KEY")
    (clean_env / ".env").write_text("OPENROUTER_API_KEY=sk-2\n", encoding="utf-8")
    assert nxdo_config._api_key_available(clean_env) is True


def test_target_repos_only_git_dirs(clean_env: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    project = clean_env / "koru"
    (project / ".git").mkdir(parents=True)
    sibling = clean_env / "other"
    (sibling / ".git").mkdir(parents=True)
    (clean_env / "plain").mkdir()
    monkeypatch.setenv("KORU_NXDO_REPOS", str(clean_env / "*"))
    repos = nxdo_config.nxdo_target_repos(project)
    assert repos == [project.resolve(), sibling.resolve()]


# --------------------------------------------------------- nxdo_cooldown


def test_load_stamps_tolerates_bad_state(clean_env: Path) -> None:
    assert nxdo_cooldown._load_stamps(clean_env) == {}
    (clean_env / ".planfile" / ".koru").mkdir(parents=True)
    stamp_file = clean_env / ".planfile" / ".koru" / "nxdo-discovery.json"
    stamp_file.write_text("not json", encoding="utf-8")
    assert nxdo_cooldown._load_stamps(clean_env) == {}
    stamp_file.write_text("[1, 2]", encoding="utf-8")
    assert nxdo_cooldown._load_stamps(clean_env) == {}
    stamp_file.write_text('{"a": 1, "b": "x", "c": 2.5}', encoding="utf-8")
    assert nxdo_cooldown._load_stamps(clean_env) == {"a": 1.0, "c": 2.5}


def test_save_stamps_roundtrip_creates_parents(clean_env: Path) -> None:
    stamps = {"/repo/a": 123.5}
    nxdo_cooldown._save_stamps(clean_env, stamps)
    assert nxdo_cooldown._load_stamps(clean_env) == stamps
    raw = json.loads((clean_env / ".planfile" / ".koru" / "nxdo-discovery.json").read_text(encoding="utf-8"))
    assert raw == {"/repo/a": 123.5}


def test_select_target_repo_cooldown_window(clean_env: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    project = clean_env / "koru"
    (project / ".git").mkdir(parents=True)
    monkeypatch.delenv("KORU_NXDO_REPOS", raising=False)
    nxdo_cooldown._save_stamps(project, {str(project.resolve()): 1000.0})
    # A repo is eligible only once the full cooldown has elapsed since its stamp.
    selection = nxdo_cooldown._select_target_repo(project, now=2800.0)
    assert selection.repo is None
    assert 1799.0 < selection.remaining <= 1800.0
    selection = nxdo_cooldown._select_target_repo(project, now=4600.0)
    assert selection.repo == project.resolve()
    assert selection.remaining == 0.0
    monkeypatch.setenv("KORU_NXDO_COOLDOWN_SECONDS", "0")
    selection = nxdo_cooldown._select_target_repo(project, now=1000.0)
    assert selection.repo == project.resolve()


# ---------------------------------------------------------- nxdo_tickets


def test_plan_from_output_variants() -> None:
    plan = {"tasks": [{"title": "t"}]}
    assert nxdo_tickets._plan_from_output(json.dumps(plan)) == plan
    assert nxdo_tickets._plan_from_output(f"noise\n{json.dumps(plan)}\nmore") == plan
    assert nxdo_tickets._plan_from_output("") is None
    assert nxdo_tickets._plan_from_output("no braces") is None
    assert nxdo_tickets._plan_from_output("[1, 2]") is None


def test_slug_and_dedupe_key(clean_env: Path) -> None:
    assert nxdo_tickets._slug("Fix: the *Bug* NOW!") == "fix-the-bug-now"
    assert len(nxdo_tickets._slug("a" * 200)) == 80
    key = nxdo_tickets._dedupe_key(clean_env, {"title": "Add CI pipeline"})
    assert key == f"nxdo:{clean_env.name}:add-ci-pipeline"
    assert nxdo_tickets._dedupe_key(clean_env, {}) == f"nxdo:{clean_env.name}:"


def test_existing_nxdo_dedupe_keys(clean_env: Path) -> None:
    assert nxdo_tickets._existing_nxdo_dedupe_keys(clean_env) == set()
    sprints = clean_env / ".planfile" / "sprints"
    sprints.mkdir(parents=True)
    (sprints / "current.yaml").write_text(
        yaml.safe_dump(
            {
                "sprint": {
                    "tickets": {
                        "STARTER-1": {
                            "source": {
                                "tool": "koru-nxdo-discovery",
                                "context": {"dedupe_key": "nxdo:koru:add-ci"},
                            }
                        },
                        "STARTER-2": {
                            "source": {
                                "tool": "other",
                                "context": {"dedupe_key": "code2llm:god:x"},
                            }
                        },
                        "STARTER-3": {"source": {"context": {"dedupe_key": "nxdo:koru:docs"}}},
                    }
                }
            }
        ),
        encoding="utf-8",
    )
    assert nxdo_tickets._existing_nxdo_dedupe_keys(clean_env) == {
        "nxdo:koru:add-ci",
        "nxdo:koru:docs",
    }


def test_ticket_text_and_scaffold(clean_env: Path) -> None:
    task = {
        "title": "Add CI",
        "description": "Do CI",
        "acceptance_criteria": ["works", " "],
        "task_type": "chore",
    }
    text = nxdo_tickets._ticket_text(task, repo=clean_env, project=clean_env)
    assert text == "Do CI\nAcceptance criteria:\n- works"
    other = clean_env / "sibling"
    text = nxdo_tickets._ticket_text(task, repo=other, project=clean_env)
    assert text.startswith(f"[repo: {other}]")
    scaffold = nxdo_tickets._ticket_scaffold(task, repo=other, project=clean_env)
    assert scaffold["labels"] == ["nxdo", "discovery", "chore", "cross-repo"]
    assert scaffold["source_tool"] == nxdo_tickets.DEFAULT_SOURCE
    assert scaffold["source_context"]["dedupe_key"].startswith("nxdo:")
    assert scaffold["executor_kind"] == "human" and scaffold["executor_mode"] == "interactive"
    bare = nxdo_tickets._ticket_scaffold({}, repo=clean_env, project=clean_env)
    assert bare["labels"] == ["nxdo", "discovery"]
    assert bare["title"] == "nxdo discovery ticket"


@pytest.fixture()
def capture_created(monkeypatch: pytest.MonkeyPatch) -> list[dict]:
    created: list[dict] = []

    def fake_create_nl_task(project, text, *, sprint="current", priority="normal", scaffold=None, **kw):
        created.append({"text": text, "priority": priority, "scaffold": scaffold or {}})
        return SimpleNamespace(reused=False, id=f"STARTER-{900 + len(created)}")

    monkeypatch.setattr(koru.tasks, "create_nl_task", fake_create_nl_task)
    return created


def _task(title: str, **extra: object) -> dict:
    base: dict = {"title": title, "description": f"Do {title}", "priority": "high"}
    base.update(extra)
    return base


def test_apply_plan_tickets_limit_and_inplan_dedupe(clean_env: Path, capture_created: list[dict]) -> None:
    plan = {"tasks": [_task("One"), _task("One"), _task("Two"), _task("Three")]}
    filed = nxdo_tickets._apply_plan_tickets(clean_env, clean_env, plan, limit=2)
    # The duplicate "One" hits the in-plan dedupe key; "Three" hits the limit
    # break before its dedupe check, so it lands in neither list.
    assert filed.applied == ["One", "Two"]
    assert filed.skipped == ["One"]
    assert [c["priority"] for c in capture_created] == ["high", "high"]


def test_apply_plan_tickets_create_errors_are_skipped(clean_env: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    def boom(*a, **kw):
        raise ValueError("no planfile")

    monkeypatch.setattr(koru.tasks, "create_nl_task", boom)
    filed = nxdo_tickets._apply_plan_tickets(clean_env, clean_env, {"tasks": [_task("One")]}, limit=5)
    assert filed.applied == []
    assert filed.skipped == ["One: no planfile"]


def test_apply_plan_tickets_reused_tickets_are_skipped(clean_env: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(koru.tasks, "create_nl_task", lambda *a, **kw: SimpleNamespace(reused=True))
    filed = nxdo_tickets._apply_plan_tickets(clean_env, clean_env, {"tasks": [_task("One")]}, limit=5)
    assert filed.applied == []
    assert filed.skipped == ["One"]


def test_apply_plan_tickets_skips_existing_sprint_keys(clean_env: Path, capture_created: list[dict]) -> None:
    key = nxdo_tickets._dedupe_key(clean_env, {"title": "One"})
    sprints = clean_env / ".planfile" / "sprints"
    sprints.mkdir(parents=True)
    (sprints / "current.yaml").write_text(
        yaml.safe_dump({"sprint": {"tickets": {"STARTER-1": {"source": {"context": {"dedupe_key": key}}}}}}),
        encoding="utf-8",
    )
    filed = nxdo_tickets._apply_plan_tickets(clean_env, clean_env, {"tasks": [_task("One")]}, limit=5)
    assert filed.applied == []
    assert filed.skipped == ["One"]
    assert capture_created == []
