"""Unit tests for extracted koru.context_rules module."""

from __future__ import annotations

from koru.context_rules import (
    _build_instructions,
    _build_policy_rules,
    _build_self_service,
    _build_setup_instructions,
    _build_shared_rules,
    _build_ticket_rules,
)
from koru.policy import Policy


def test_build_setup_instructions() -> None:
    instructions = _build_setup_instructions()
    assert len(instructions) == 3
    assert any("not been initialised" in s for s in instructions)
    assert any("koru --init" in s for s in instructions)


def test_build_shared_rules() -> None:
    policy = Policy(notes=("custom note",))
    rules = _build_shared_rules(policy, None)
    assert any("Co-authored-by" in r for r in rules)
    assert "custom note" in rules


def test_build_instructions_uninitialised() -> None:
    policy = Policy()
    rules = _build_instructions(policy, None, planfile_initialised=False)
    assert any("You MUST obey" in r for r in rules)
    assert any("not been initialised" in r for r in rules)


def test_build_instructions_initialised() -> None:
    policy = Policy(allow_commit=False, allow_push=False)
    rules = _build_instructions(policy, None, planfile_initialised=True)
    assert any("DO NOT run raw `git commit`" in r for r in rules)
    assert any("DO NOT run raw `git push`" in r for r in rules)
    assert any("Immediately run `koru scan --apply`" in r for r in rules)


def test_build_policy_rules() -> None:
    policy = Policy(
        allow_commit=False,
        allow_push=False,
        allow_branch_create=False,
        allow_tag=False,
        allow_destructive_shell=False,
        require_ci_pass_before_complete=True,
        ci_command="pytest",
    )
    rules = _build_policy_rules(policy)
    assert any("git commit" in r for r in rules)
    assert any("git push" in r for r in rules)
    assert any("switch branches" in r for r in rules)
    assert any("git tags" in r for r in rules)
    assert any("destructive shell" in r for r in rules)
    assert any("run `pytest`" in r for r in rules)


def test_build_ticket_rules_scoped_and_critical() -> None:
    ticket = {
        "id": "PLF-100",
        "priority": "critical",
        "files": ["src/a.py", "src/b.py"],
    }
    rules = _build_ticket_rules(ticket)
    assert any("Limit edits to the ticket's declared files: src/a.py, src/b.py" in r for r in rules)
    assert any("CRITICAL PRIORITY: This ticket is blocking other work" in r for r in rules)
    assert any("AUTO-REPAIR MODE" in r for r in rules)


def test_build_self_service_uninitialised() -> None:
    policy = Policy()
    commands = _build_self_service(policy, None, planfile_initialised=False)
    assert "init_project" in commands
    assert "init_from_pipeline" in commands
    assert "refresh_brief" in commands
    assert "start_this" not in commands


def test_build_self_service_with_ticket() -> None:
    policy = Policy(ci_command="uv run pytest")
    ticket = {"id": "PLF-200"}
    commands = _build_self_service(policy, ticket, planfile_initialised=True)
    assert commands["start_this"] == "planfile ticket start PLF-200"
    assert commands["done_this"] == "planfile ticket done PLF-200"
    assert "planfile ticket block PLF-200" in commands["block_this"]
    assert commands["verify_ci"] == "uv run pytest"
